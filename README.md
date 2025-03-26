# Text-to-SQL chat app
This app was originally made with a fake Education dataset, but any dataset will work.

## **NOTE:**
+ This tool is inteded to be a tool for **local** environments, in order to easily and quickly demonstrate the power of text-to-SQL agentic GenAI.
+ It is **NOT indended for production environments**
+ There are **no GenAI guardrails**
+ There are **no SQL insert/update prevention guardrails**

## features
- will return SQL query text
- will run SQL query text, and return the results
- Can plot bar, line, and scatter plots

## run app
+ activate environment
```bash
conda activate text-to-sql
```
+ start database server
```bash
bash start_db_server.sh
```
+ run streamlit app
```bash
streamlit run app.py
```
+ navigate to localhost:8501 in your browswer
+ enter OpenAI API key into app
+ select prompt template from the drop down (db-sql-prompt.md is for the default fake Education dataset)
+ start chatting!
+ when finished, stop the app with Ctrl + C
+ stop the database server
```bash
bash stop_db_server.sh
```

## first time setup
+ create conda environment 
```bash
mamba env create --file env.yml
```
+ activate environment
```bash
conda activate text-to-sql
```
+ create local postgreSQL database, server, create fake data, and populate the database with fake data
```bash
bash setup.sh
```

## delete fake data and local database
+ activate environment
```bash
conda activate text-to-sql
```
+ create local postgreSQL database, server, create fake data, and populate the database with fake data
```bash
bash delete_db.sh
```

### use custom data
+ delete fake data and local database
+ within the ./tables_csv folder, put csv files representing the data to load into the database. 
    + each csv file should represent a table. 
    + the name of the csv file will be the table name
    + there must be columns for primary key and foreign keys (if any) for each csv file
+ create the local postgreSQL database
```bash
bash setup_postgres.sh
```
+ start the server
```bash
bash start_db_server.sh
```
+ populate the database
```bash
python populate_db.py
```
+ make a copy the prompt_template.md file and rename it to whatever you'd like. 
    + update your template with your database information (see db-sql-prompt.md for example)
+ continue the run app steps

## UI Customization
+ add a favicon.png and logo.png file to ./customizations/logos (app favicon and logo)
+ update ./customizations/title.txt (app title)
+ update ./.streamlit/config.toml (app colors)