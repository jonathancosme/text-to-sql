import os
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv('db_config.env')

PG_USER = os.getenv('PG_USER')
PG_PASSWORD = os.getenv('PG_PASSWORD')
PG_HOST = os.getenv('PG_HOST')
PG_PORT = os.getenv('PG_PORT')
PG_DATABASE = os.getenv('PG_DATABASE')

# Connect to database
conn_str = f'postgresql+psycopg2://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DATABASE}'
engine = create_engine(conn_str)

# Example query execution function
def run_query(sql_query):
    with engine.connect() as conn:
        result = pd.read_sql(text(sql_query), conn)
    return result

# Example usage:
if __name__ == "__main__":
    query = 'SELECT * FROM "Enrollments" LIMIT 5;'
    df_result = run_query(query)
    print(df_result)

# import os
# import pandas as pd
# from sqlalchemy import create_engine, text
# from dotenv import load_dotenv

# # Load environment variables
# load_dotenv('db_config.env')

# PG_USER = os.getenv('PG_USER')
# PG_PASSWORD = os.getenv('PG_PASSWORD')
# PG_HOST = os.getenv('PG_HOST')
# PG_PORT = os.getenv('PG_PORT')
# PG_DATABASE = os.getenv('PG_DATABASE')

# # Connect to database
# conn_str = f'postgresql+psycopg2://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DATABASE}'
# engine = create_engine(conn_str)

# # Function to get all table names
# def get_all_table_names():
#     query = """
#     SELECT table_name 
#     FROM information_schema.tables 
#     WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
#     """
#     with engine.connect() as conn:
#         result = pd.read_sql(text(query), conn)
#     return result

# # Example usage:
# if __name__ == "__main__":
#     tables_df = get_all_table_names()
#     print("Tables in the database:")
#     print(tables_df)
