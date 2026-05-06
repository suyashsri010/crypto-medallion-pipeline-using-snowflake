import json
import requests
import os
import pandas as pd
from datetime import datetime
from snowflake.connector.pandas_tools import write_pandas
from airflow.decorators import dag, task
from airflow.providers.snowflake.hooks.snowflake import SnowflakeHook

@dag(
    dag_id="binance_medallion_pipeline",
    start_date=datetime(2026, 5, 1),
    schedule_interval="*/5 * * * *", 
    catchup=False,
    tags=["finance", "crypto", "medallion"]
)
def binance_pipeline():

    @task()
    def extract_bronze_data(**context):
        symbols = ["BTCUSDT", "ETHUSDT"]
        base_url = "https://api.binance.com/api/v3/klines"
        logical_date = context["logical_date"].strftime("%Y%m%d_%H%M")
        saved_file_paths = []
        
        for symbol in symbols:
            params = {"symbol": symbol, "interval": "1m", "limit": 5}
            response = requests.get(base_url, params=params)
            file_path = f"/opt/airflow/data/bronze/{symbol}_raw_{logical_date}.json"
            with open(file_path, "w") as f:
                json.dump(response.json(), f)
            saved_file_paths.append(file_path)
        return saved_file_paths

    @task()
    def transform_silver_data(bronze_files_list):
        silver_paths = []
        for file_path in bronze_files_list:
            df = pd.DataFrame(pd.read_json(file_path))
            columns = ["timestamp", "open", "high", "low", "close", "volume"]
            df = df.iloc[:, 0:6]
            df.columns = columns
            # Convert to datetime, then immediately format it as a clean string
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms').dt.strftime('%Y-%m-%d %H:%M:%S')
            
            symbol = file_path.split('/')[-1].split('_')[0]
            df['symbol'] = symbol
            
            silver_path = file_path.replace("bronze", "silver").replace("raw", "clean").replace(".json", ".parquet")
            df.to_parquet(silver_path, index=False)
            silver_paths.append(silver_path)
        return silver_paths

    # --- THE NEW GOLD TASK ---
    # ==========================================
    # GOLD LAYER: Load to Snowflake
    # ==========================================
    @task()
    def load_to_snowflake(silver_files):
        # 1. Unlock the door
        hook = SnowflakeHook(snowflake_conn_id='snowflake_conn')
        conn = hook.get_conn() # Extract the raw connection
        
        for file_path in silver_files:
            df = pd.read_parquet(file_path)
            symbol = file_path.split('/')[-1].split('_')[0]
            
            # 2. Snowflake strongly prefers uppercase column names to match its tables
            df.columns = [col.upper() for col in df.columns]
            
            # 3. Use the dedicated Snowflake pandas tool to push the data
            success, nchunks, nrows, _ = write_pandas(
                conn=conn,
                df=df,
                table_name="CRYPTO_TICK_DATA",
                database="CIPHERSTREAM_DB",
                schema="SILVER"
            )
            print(f"Successfully pushed {nrows} rows of {symbol} data to Snowflake Gold layer.")

    # Setting the flow: Bronze -> Silver -> Gold
    bronze_files = extract_bronze_data()
    silver_files = transform_silver_data(bronze_files)
    load_to_snowflake(silver_files)

dag_instance = binance_pipeline()