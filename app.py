import streamlit as st
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, AIMessage
from langchain.memory import ConversationSummaryBufferMemory
from langchain.callbacks.base import BaseCallbackHandler
from langchain.utilities import SQLDatabase
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import glob
import os
import re
import json
from pathlib import Path
import shutil
import toml

# --- Paths ---
CUSTOM_DIR = Path("customizations")
LOGO_DIR = CUSTOM_DIR / "logos"
TITLE_FILE = CUSTOM_DIR / "title.txt"
THEME_FILE = Path("custom_theme.toml")
STREAMLIT_CONFIG = Path(".streamlit/config.toml")
STREAMLIT_CONFIG.parent.mkdir(exist_ok=True)

# --- Load title ---
default_title = "Text-to-SQL Agentic AI Chatbot"
if TITLE_FILE.exists():
    page_title = TITLE_FILE.read_text(encoding="utf-8").strip()
else:
    page_title = default_title

# --------------------------- #
#     STREAMLIT CONFIG
# --------------------------- #

# --- Handle favicon ---
favicon_path = LOGO_DIR / "favicon.png"
if favicon_path.exists():
    st.set_page_config(page_title=page_title, page_icon=str(favicon_path), layout="wide")
    st.logo(str(favicon_path), size='large')
else:
    st.set_page_config(page_title=page_title, page_icon="✨", layout="wide")

# --- Show logo if exists ---
logo_path = LOGO_DIR / "logo.png"
if logo_path.exists():
    st.image(str(logo_path), width=500)

# --- Page Title Heading ---
st.title(page_title)

# --- Apply custom theme if present ---
if THEME_FILE.exists():
    theme_dict = toml.load(THEME_FILE)
    toml.dump(theme_dict, STREAMLIT_CONFIG)

# --------------------------- #
#     SIDEBAR
# --------------------------- #
st.sidebar.title("Settings")
api_key = st.sidebar.text_input("🔑 OpenAI API key", type="password")

if st.sidebar.button("🧹 Clear Conversation"):
    st.session_state.clear()
    st.rerun()

# Prompt templates in ./prompts/*.md (optional)
prompt_files = glob.glob("./prompts/*.md")
prompt_options = ["None"] + [os.path.basename(f) for f in prompt_files]
selected_prompt = st.sidebar.selectbox("Select Prompt Template", prompt_options)
display_formatted_prompt_in_chat = st.sidebar.checkbox("Display prompt in chat", value=False)

# --------------------------- #
#   SESSION STATE INIT
# --------------------------- #
if "messages" not in st.session_state:
    st.session_state.messages = []
if "memory" not in st.session_state:
    st.session_state.memory = None
if "llm" not in st.session_state:
    st.session_state.llm = None
if "db" not in st.session_state:
    st.session_state.db = None
if "engine" not in st.session_state:
    st.session_state.engine = None

# --------------------------- #
#     UTILITIES
# --------------------------- #
def load_prompt(filepath: str) -> str:
    """Load a .md prompt template from disk."""
    with open(filepath, "r") as file:
        return file.read()

def extract_sql(response_text: str) -> str:
    """
    Extract SQL code from triple-backtick ```sql ... ``` blocks.
    Returns the first match or None if no block found.
    """
    pattern = r"```sql\s*(.*?)\s*```"
    matches = re.findall(pattern, response_text, flags=re.DOTALL | re.IGNORECASE)
    return matches[0].strip() if matches else None

def run_query(sql_query: str) -> pd.DataFrame:
    """Run a SQL query and return a Pandas DataFrame."""
    with st.session_state.engine.connect() as conn:
        df = pd.read_sql(text(sql_query), conn)
    return df

def extract_chart_instruction(response_text: str):
    """
    Look for a JSON object of the form:
      {
         "chart_type": "bar" / "line" / "scatter",
         "x": "Month",
         "y": "Revenue"
      }
    Returns a dict or None if not found/invalid.
    """
    try:
        match = re.search(r"{\s*\"chart_type\".*?}", response_text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception:
        return None
    return None

def get_last_dataframe() -> pd.DataFrame:
    """
    Return the most recent DataFrame from conversation history,
    or None if not found.
    """
    for msg in reversed(st.session_state.messages):
        if isinstance(msg, AIMessage):
            if msg.metadata and "df_result" in msg.metadata:
                df = msg.metadata["df_result"]
                if isinstance(df, pd.DataFrame):
                    return df
    return None


# --------------------------- #
#  STREAM HANDLER (for LLM)
# --------------------------- #
class StreamHandler(BaseCallbackHandler):
    """
    Streams tokens from ChatOpenAI to a Streamlit container as they arrive.
    """
    def __init__(self, container):
        self.container = container
        self.text = ""

    def on_llm_new_token(self, token: str, **kwargs):
        self.text += token
        self.container.markdown(self.text + "▌")


# --------------------------- #
#  CLASSIFICATION LOGIC
# --------------------------- #
def classify_user_request(user_input: str, classification_llm: ChatOpenAI) -> str:
    """
    Decide if the user wants:
      - "SQL"  => run a new query
      - "PLOT" => plot the last DataFrame
      - "CHAT" => normal conversation only
    Returns one of ["SQL", "PLOT", "CHAT"].
    """
    classification_prompt = f"""
You are a text classifier that must categorize the user's request as one of these three categories only:
1) SQL  - The user wants a new SQL query or fresh data from the DB or has SQL query they want to run.
2) PLOT - The user wants to plot or visualize the last known data.
3) CHAT - The user is simply chatting or clarifying, with no need for SQL or plotting.

User's request: {user_input}

Return ONLY one word, either 'SQL', 'PLOT', or 'CHAT'.
"""
    result = classification_llm.predict(classification_prompt).strip().upper()
    if "SQL" in result:
        return "SQL"
    elif "PLOT" in result:
        return "PLOT"
    else:
        return "CHAT"


# --------------------------- #
#          MAIN APP
# --------------------------- #
def main():
    if api_key:

        # 1) Initialize LLM + Memory
        if st.session_state.memory is None:
            # Main LLM for conversation
            llm = ChatOpenAI(
                # temperature=0.7,
                openai_api_key=api_key,
                model_name="gpt-4o",
                streaming=True
            )
            memory = ConversationSummaryBufferMemory(
                llm=llm,
                max_token_limit=6000,
                return_messages=True
            )
            st.session_state.llm = llm
            st.session_state.memory = memory

        # We'll also define a classification LLM (non-streaming) for short text classification
        classification_llm = ChatOpenAI(
            # temperature=0.0,
            openai_api_key=api_key,
            model_name="gpt-4o",
            streaming=False
        )

        # 2) Initialize DB if not set
        if st.session_state.engine is None:
            load_dotenv("db_config.env")
            conn_str = (
                f'postgresql+psycopg2://{os.getenv("PG_USER")}:'
                f'{os.getenv("PG_PASSWORD")}@{os.getenv("PG_HOST")}:'
                f'{os.getenv("PG_PORT")}/{os.getenv("PG_DATABASE")}'
            )
            engine = create_engine(conn_str)
            st.session_state.engine = engine
            st.session_state.db = SQLDatabase.from_uri(conn_str)

        llm = st.session_state.llm
        memory = st.session_state.memory

        # --------------------------- #
        # Display Chat History
        # --------------------------- #
        for msg in st.session_state.messages:
            role = "user" if isinstance(msg, HumanMessage) else "assistant"
            with st.chat_message(role):
                st.markdown(msg.content)

                if isinstance(msg, AIMessage) and hasattr(msg, "metadata") and msg.metadata:
                    df = msg.metadata.get("df_result")
                    plot_spec = msg.metadata.get("plot")

                    if isinstance(df, pd.DataFrame):
                        st.dataframe(df)

                    if isinstance(plot_spec, dict):
                        with st.expander("📊 Previous Chart", expanded=False):
                            try:
                                chart_type = plot_spec["chart_type"]
                                x_col = plot_spec["x"]
                                y_col = plot_spec["y"]
                                if chart_type == "bar":
                                    st.bar_chart(df, x=x_col, y=y_col)
                                elif chart_type == "line":
                                    st.line_chart(df, x=x_col, y=y_col)
                                elif chart_type == "scatter":
                                    st.scatter_chart(df, x=x_col, y=y_col)
                            except Exception as e:
                                st.error(f"❌ Failed to plot chart: {e}")

        # --------------------------- #
        #     User Input
        # --------------------------- #
        user_input = st.chat_input("Type your message here...")

        if user_input:
            # 0) Decide action (SQL, PLOT, or CHAT)
            action = classify_user_request(user_input, classification_llm)

            # 1) Add user's message to conversation
            # Build or load prompt template:
            if selected_prompt != "None":
                prompt_template = load_prompt(os.path.join("./prompts", selected_prompt))
            else:
                prompt_template = """{conversation_summary}

User says: {user_input}

Assistant:"""

            conversation_summary = memory.load_memory_variables({}).get("history", "NONE")
            formatted_prompt = prompt_template.format(
                conversation_summary=conversation_summary or "NONE",
                user_input=user_input
            )
            # If the user wants to see the entire "formatted prompt" in the chat:
            display_user_content = formatted_prompt if display_formatted_prompt_in_chat else user_input

            st.session_state.messages.append(HumanMessage(content=display_user_content))
            with st.chat_message("user"):
                st.markdown(display_user_content)

            # 2) Branch logic
            if action == "SQL":
                # (A) We run multi-attempt SQL generation
                with st.chat_message("assistant"):
                    response_container = st.empty()

                stream_handler = StreamHandler(response_container)
                llm.callbacks = [stream_handler]

                MAX_SQL_RETRIES = 5
                agent_prompt = formatted_prompt
                final_response = ""
                sql_df = None

                for attempt in range(MAX_SQL_RETRIES):
                    response = llm.predict(agent_prompt)
                    response_text = stream_handler.text
                    stream_handler.text = ""  # reset so next attempt won't keep appending

                    extracted = extract_sql(response_text)
                    if extracted:
                        # Attempt to run SQL
                        try:
                            sql_df = run_query(extracted)
                            final_response = (
                                f"{response_text}\n\n**SQL Results:**\n\nData retrieved successfully."
                            )
                            response_container.markdown(final_response)
                            st.dataframe(sql_df)
                            break
                        except Exception as e:
                            error_msg = (
                                f"The SQL query caused an error:\n```\n{str(e)}\n```\n"
                                f"Please provide a corrected SQL query."
                            )
                            agent_prompt = error_msg
                            response_container.markdown(
                                f"**SQL Error**: {e}\n\nAttempt {attempt+1} of {MAX_SQL_RETRIES}..."
                            )
                    else:
                        # No SQL found => normal chat
                        final_response = response_text
                        response_container.markdown(final_response)
                        break
                else:
                    final_response = (
                        f"❌ Unable to produce a working SQL query after {MAX_SQL_RETRIES} attempts."
                    )
                    response_container.error(final_response)

                # Save the assistant message
                ai_msg = AIMessage(
                    content=final_response,
                    metadata={"df_result": sql_df}
                )
                st.session_state.messages.append(ai_msg)

                # Update memory
                memory.save_context({"input": user_input}, {"output": f"{final_response} {sql_df}"})

            elif action == "PLOT":
                # (B) Plot the last known DataFrame
                df_to_plot = get_last_dataframe()
                with st.chat_message("assistant"):
                    if df_to_plot is None or df_to_plot.empty:
                        msg = "No recent data found to plot. Please run a query first."
                        st.markdown(msg)
                        final_response = msg
                        ai_msg = AIMessage(content=final_response)
                        st.session_state.messages.append(ai_msg)
                        memory.save_context({"input": user_input}, {"output": final_response})
                    else:
                        # We'll do a second LLM pass to request a JSON snippet for chart instructions
                        st.markdown("Let me figure out how to plot that data...")
                        second_container = st.empty()
                        plot_stream_handler = StreamHandler(second_container)
                        llm.callbacks = [plot_stream_handler]

                        # We can attempt multiple times to parse chart instructions
                        MAX_PLOT_ATTEMPTS = 5
                        final_plot_text = ""

                        for attempt in range(MAX_PLOT_ATTEMPTS):
                            # Basic prompt for plot specs
                            chart_prompt = f"""
You must return a JSON object specifying how to plot the DataFrame below. 

DataFrame columns: {list(df_to_plot.columns)}

Return a JSON object with this format:
{{
  "chart_type": "bar" | "line" | "scatter",
  "x": "<column name for x-axis>",
  "y": "<column name or list of columns for y-axis>"
}}

No additional text, only JSON. If you can't produce a valid specification, say so.

here is the user input: {user_input}
"""
                            chart_llm_response = llm.predict(chart_prompt)
                            chart_response_text = plot_stream_handler.text
                            plot_stream_handler.text = ""  # reset for next iteration

                            chart_instruction = extract_chart_instruction(chart_response_text)
                            if chart_instruction:
                                chart_type = chart_instruction.get("chart_type", "bar")
                                x_col = chart_instruction.get("x", None)
                                y_col = chart_instruction.get("y", None)

                                final_plot_text = f"Plotting a {chart_type} chart with x={x_col}, y={y_col}."
                                st.markdown(final_plot_text)

                                # Display the chart:
                                try:
                                    if chart_type == "line":
                                        st.line_chart(df_to_plot, x=x_col, y=y_col)
                                    elif chart_type == "scatter":
                                        st.scatter_chart(df_to_plot, x=x_col, y=y_col)
                                    else:
                                        st.bar_chart(df_to_plot, x=x_col, y=y_col)

                                    # We'll store the instructions in metadata
                                    ai_msg = AIMessage(
                                        content=final_plot_text,
                                        metadata={
                                            "df_result": df_to_plot,
                                            "plot": {
                                                "chart_type": chart_type,
                                                "x": x_col,
                                                "y": y_col
                                            }
                                        }
                                    )
                                    st.session_state.messages.append(ai_msg)
                                    memory.save_context({"input": user_input}, {"output": final_plot_text})
                                    break
                                except Exception as e:
                                    st.warning(f"⚠️ Chart plotting failed: {e}")
                            else:
                                st.info(
                                    f"Could not parse chart instructions on attempt {attempt+1}. Retrying..."
                                )
                        else:
                            final_plot_text = "⚠️ Plotting instructions could not be determined."
                            st.warning(final_plot_text)
                            ai_msg = AIMessage(content=final_plot_text)
                            st.session_state.messages.append(ai_msg)
                            memory.save_context({"input": user_input}, {"output": final_plot_text})

            else:
                # (C) Normal CHAT, no SQL or plotting
                with st.chat_message("assistant"):
                    response_container = st.empty()
                stream_handler = StreamHandler(response_container)
                llm.callbacks = [stream_handler]

                # Single pass for normal chat
                response = llm.predict(formatted_prompt)
                response_text = stream_handler.text

                # Save in conversation
                ai_msg = AIMessage(content=response_text)
                st.session_state.messages.append(ai_msg)
                memory.save_context({"input": user_input}, {"output": response_text})

    else:
        st.warning("🔑 Please enter your OpenAI API key in the sidebar to start.")


# --------------------------- #
#   LAUNCH THE APP
# --------------------------- #
if __name__ == "__main__":
    main()




# import streamlit as st
# from langchain.chat_models import ChatOpenAI
# from langchain.schema import HumanMessage, AIMessage
# from langchain.memory import ConversationSummaryBufferMemory
# from langchain.callbacks.base import BaseCallbackHandler

# import glob
# import os
# import re

# import pandas as pd
# from sqlalchemy import create_engine, text
# from dotenv import load_dotenv

# from langchain.agents import AgentType
# from langchain.utilities import SQLDatabase

# # --------------------------- #
# #     STREAMLIT CONFIG
# # --------------------------- #
# st.set_page_config(page_title="🧠 GPT-4o Chatbot", layout="centered")

# # --------------------------- #
# #     SIDEBAR
# # --------------------------- #
# st.sidebar.title("⚙️ Settings")
# api_key = st.sidebar.text_input("🔑 OpenAI API key", type="password")

# if st.sidebar.button("🧹 Clear Conversation"):
#     st.session_state.clear()
#     st.rerun()

# # Load prompt templates
# prompt_files = glob.glob("./prompts/*.md")
# prompt_options = ["None"] + [os.path.basename(f) for f in prompt_files]
# selected_prompt = st.sidebar.selectbox("📑 Select Prompt Template", prompt_options)
# display_formatted_prompt_in_chat = st.sidebar.checkbox("📝 Display prompt in chat", value=False)

# # --------------------------- #
# #     SESSION STATE INIT
# # --------------------------- #
# if "messages" not in st.session_state:
#     st.session_state.messages = []
# if "memory" not in st.session_state:
#     st.session_state.memory = None
# if "llm" not in st.session_state:
#     st.session_state.llm = None
# if "db" not in st.session_state:
#     st.session_state.db = None
# if "engine" not in st.session_state:
#     st.session_state.engine = None

# # --------------------------- #
# #     UTILITIES
# # --------------------------- #
# def load_prompt(filepath):
#     """Load a .md prompt template from disk."""
#     with open(filepath, 'r') as file:
#         content = file.read()
#     return content

# def extract_sql(response_text):
#     """
#     Extract SQL code from triple-backtick ```sql ... ```
#     blocks in the LLM response.
#     """
#     pattern = r"```sql\s*(.*?)\s*```"
#     matches = re.findall(pattern, response_text, flags=re.DOTALL | re.IGNORECASE)
#     return matches[0].strip() if matches else None

# def run_query(sql_query):
#     """Run SQL query and return a Pandas DataFrame."""
#     with st.session_state.engine.connect() as conn:
#         result = pd.read_sql(text(sql_query), conn)
#     return result

# # --------------------------- #
# #  CUSTOM STREAMING HANDLER
# # --------------------------- #
# class StreamHandler(BaseCallbackHandler):
#     """
#     When used as a callback in ChatOpenAI, 
#     it will stream tokens to a Streamlit container.
#     """
#     def __init__(self, container):
#         self.container = container
#         self.text = ""

#     def on_llm_new_token(self, token: str, **kwargs):
#         self.text += token
#         self.container.markdown(self.text + "▌")

# # --------------------------- #
# #      MAIN APP LOGIC
# # --------------------------- #
# def main():
#     if api_key:
#         st.title("🧠 GPT-4o Chatbot with SQL")

#         # --------------------------- #
#         #   Initialize LLM + Memory
#         # --------------------------- #
#         if st.session_state.memory is None:
#             llm = ChatOpenAI(
#                 temperature=0.7,
#                 openai_api_key=api_key,
#                 model_name="gpt-4o",
#                 streaming=True
#             )
#             memory = ConversationSummaryBufferMemory(
#                 llm=llm,
#                 max_token_limit=6000,
#                 return_messages=True  # store messages for summarization
#             )

#             st.session_state.llm = llm
#             st.session_state.memory = memory

#         # --------------------------- #
#         #   Initialize DB Connection
#         # --------------------------- #
#         if st.session_state.db is None or st.session_state.engine is None:
#             load_dotenv('db_config.env')
#             PG_USER = os.getenv('PG_USER')
#             PG_PASSWORD = os.getenv('PG_PASSWORD')
#             PG_HOST = os.getenv('PG_HOST')
#             PG_PORT = os.getenv('PG_PORT')
#             PG_DATABASE = os.getenv('PG_DATABASE')

#             conn_str = f'postgresql+psycopg2://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DATABASE}'
#             engine = create_engine(conn_str)
#             st.session_state.engine = engine

#             db = SQLDatabase.from_uri(conn_str)
#             st.session_state.db = db

#         llm = st.session_state.llm
#         memory = st.session_state.memory

#         # --------------------------- #
#         #   Display Chat History
#         # --------------------------- #
#         # Here is where we re-display older messages, including any stored DataFrame
#         for msg in st.session_state.messages:
#             role = "user" if isinstance(msg, HumanMessage) else "assistant"
#             with st.chat_message(role):
#                 # The "content" is plain text markdown
#                 st.markdown(msg.content)

#                 # If there's a DataFrame in metadata, display it
#                 if hasattr(msg, "metadata") and msg.metadata is not None:
#                     df = msg.metadata.get("df_result")
#                     if isinstance(df, pd.DataFrame):
#                         st.dataframe(df)

#         # --------------------------- #
#         #   Chat Input
#         # --------------------------- #
#         user_input = st.chat_input("Type your message here...")

#         if user_input:
#             # 1) Prepare the user message
#             if selected_prompt != "None":
#                 prompt_template = load_prompt(os.path.join("./prompts", selected_prompt))
#             else:
#                 # Default fallback prompt
#                 prompt_template = """{conversation_summary}

# User says: {user_input}

# Assistant:"""

#             conversation_summary = memory.load_memory_variables({}).get('history', 'NONE')
#             formatted_prompt = prompt_template.format(
#                 conversation_summary=conversation_summary or "NONE",
#                 user_input=user_input
#             )

#             display_user_content = formatted_prompt if display_formatted_prompt_in_chat else user_input
#             user_msg = HumanMessage(content=display_user_content)
#             st.session_state.messages.append(user_msg)

#             with st.chat_message("user"):
#                 st.markdown(display_user_content)

#             # 2) Container to stream LLM response
#             with st.chat_message("assistant"):
#                 response_container = st.empty()

#             stream_handler = StreamHandler(response_container)
#             llm.callbacks = [stream_handler]

#             # We'll allow up to 3 attempts to produce a valid SQL query
#             MAX_SQL_RETRIES = 3
#             agent_prompt = formatted_prompt
#             final_response = ""
#             sql_df = None  # store DataFrame if query runs

#             for attempt in range(MAX_SQL_RETRIES):
#                 # 2A) Get a response from the LLM
#                 response = llm.predict(agent_prompt)
#                 response_text = stream_handler.text

#                 # Reset so next attempt won't keep appending
#                 stream_handler.text = ""

#                 extracted_sql = extract_sql(response_text)

#                 if extracted_sql:
#                     try:
#                         sql_df = run_query(extracted_sql)
#                         final_response = (
#                             f"{response_text}\n\n**SQL Results:**\n\n"
#                             "Below is the DataFrame containing your requested data."
#                         )
#                         # Display response text so far
#                         response_container.markdown(final_response)
#                         # Display the DataFrame for the *current* turn
#                         st.dataframe(sql_df)
#                         break

#                     except Exception as e:
#                         # On error, we feed the error back into the next attempt
#                         error_message = f"""
# The SQL query you generated caused an error:
# {str(e)}
# Please provide an updated SQL query only or clarify further.
# """
#                         agent_prompt = error_message
#                         response_container.markdown(
#                             f"**SQL Error**: {e}\n\nAttempt {attempt+1} of {MAX_SQL_RETRIES}... retrying."
#                         )
#                 else:
#                     # No SQL found => normal chat response
#                     final_response = response_text
#                     response_container.markdown(final_response)
#                     break
#             else:
#                 # If we exit the for-loop without a break => all attempts failed
#                 final_response = (
#                     f"Unable to produce a working SQL query after {MAX_SQL_RETRIES} attempts."
#                 )
#                 response_container.error(final_response)

#             # 3) Save the assistant message with any SQL DataFrame in metadata
#             ai_msg = AIMessage(content=final_response, metadata={"df_result": sql_df})
#             st.session_state.messages.append(ai_msg)

#             # 4) Update memory with the raw user input and the final response
#             memory.save_context({"input": user_input}, {"output": f"{final_response} {sql_df}"})

#     else:
#         st.warning("🔑 Please enter your OpenAI API key in the sidebar to start.")


# # --------------------------- #
# #   LAUNCH THE APP
# # --------------------------- #
# if __name__ == "__main__":
#     main()

