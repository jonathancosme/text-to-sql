import os
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Load environment variables
load_dotenv('db_config.env')

PG_USER = os.getenv('PG_USER')
PG_PASSWORD = os.getenv('PG_PASSWORD')
PG_HOST = os.getenv('PG_HOST')
PG_PORT = os.getenv('PG_PORT')
PG_DATABASE = os.getenv('PG_DATABASE')

# SQLAlchemy engine connection string
conn_str = f'postgresql+psycopg2://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DATABASE}'
engine = create_engine(conn_str)

csv_folder = 'table_csvs'

for csv_file in os.listdir(csv_folder):
    if csv_file.endswith('.csv'):
        table_name = os.path.splitext(csv_file)[0]
        df = pd.read_csv(os.path.join(csv_folder, csv_file))
        df.to_sql(table_name, engine, if_exists='replace', index=False)
        print(f"Loaded {csv_file} into table '{table_name}'.")

print("Database population complete.")
