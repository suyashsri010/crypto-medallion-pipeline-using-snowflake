import pandas as pd
import glob
import os

# 1. Combine all JSONs and FORCE a fresh, unique index
files = glob.glob('data/bronze/*.json')

if not files:
    print("No files found in data/bronze/. Make sure your Airflow DAG has run.")
else:
    # Added ignore_index=True to fix the ValueError
    df = pd.concat([pd.read_json(f) for f in files], ignore_index=True)

    # 2. Export to compare
    df.to_json('combined_test.json')
    df.to_parquet('combined_test.parquet')

    # 3. Calculate metrics
    json_size = os.path.getsize('combined_test.json') / 1024
    parquet_size = os.path.getsize('combined_test.parquet') / 1024

    print(f"--- Operational Metrics ---")
    print(f"Total Records: {len(df)}")
    print(f"Combined JSON: {json_size:.2f} KB")
    print(f"Combined Parquet: {parquet_size:.2f} KB")
    print(f"Compression Ratio: {json_size / parquet_size:.2f}x")