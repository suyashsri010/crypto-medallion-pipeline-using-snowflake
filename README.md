# CipherStream: Real-Time Market Data Pipeline

An automated ELT pipeline implementing a Medallion architecture for high-frequency cryptocurrency tick data. The system extracts OHLCV data via REST APIs, transforms it locally, and loads it into a cloud data warehouse for real-time visualization.

## Architecture

![CipherStream Architecture](assets/cipherstream_diagram.png)

The pipeline follows a standard Bronze/Silver/Gold data progression:

1. **Bronze (Ingestion):** Python workers poll the Binance REST API (1-minute intervals). Raw JSON payloads are persisted locally to guarantee initial state preservation.
2. **Silver (Processing):** Pandas processes the raw JSON, resolves epoch timestamp scaling (ms to ns) incompatibilities, and serializes the output to Apache Parquet.
3. **Gold (Serving):** Parquet files are bulk-loaded into Snowflake (`CIPHERSTREAM_DB.SILVER.CRYPTO_TICK_DATA`) using the Snowflake Python Connector.
4. **Presentation:** A Streamlit application serves as the frontend, utilizing dynamic SQL for real-time charting and data exploration.

## Tech Stack
* **Orchestration:** Apache Airflow 2.x
* **Infrastructure:** Docker / Docker Compose
* **Data Engine:** Python 3.12, Pandas, Apache Parquet
* **Cloud Warehouse:** Snowflake
* **Frontend:** Streamlit, Plotly

## Key Engineering Decisions

* **Compute Pushdown:** The Streamlit dashboard does not pull data into client memory. It injects user parameters (date ranges, volume floors) into dynamic SQL queries, forcing Snowflake to handle the compute and returning only the aggregated result sets.
* **Storage Optimization:** Transitioning data from JSON to columnar Parquet format in the Silver layer drastically reduces payload size and optimizes Snowflake's bulk `COPY INTO` operations.
* **Epoch Normalization:** Addressed cross-system timestamp incompatibility by forcing a standard datetime string format during the Silver transformation, preventing Snowflake `TIMESTAMP_NTZ` overflow errors.
* **Credential Isolation:** All API keys and database credentials are fully isolated using Docker `.env` files, Airflow Connections, and Streamlit `secrets.toml`.

## Local Setup

### Prerequisites
* Docker & docker-compose
* Python 3.12+
* Active Snowflake account

### Deployment

1. **Clone & Spin up Airflow:**
```bash
git clone [https://github.com/YOUR_USERNAME/crypto-medallion-pipeline.git](https://github.com/YOUR_USERNAME/crypto-medallion-pipeline.git)
cd crypto-medallion-pipeline
docker-compose up -d
```
2. **Configure Snowflake:**
Execute the following in a Snowflake worksheet to provision the backend:
```
SQL
USE ROLE ACCOUNTADMIN;
CREATE DATABASE CIPHERSTREAM_DB;
CREATE SCHEMA CIPHERSTREAM_DB.SILVER;
CREATE TABLE CRYPTO_TICK_DATA (
    TIMESTAMP TIMESTAMP_NTZ,
    OPEN FLOAT, HIGH FLOAT, LOW FLOAT, CLOSE FLOAT, VOLUME FLOAT,
    SYMBOL VARCHAR
);
```
3. **Launch the Application:**
Configure your .streamlit/secrets.toml, then boot the UI:

```Bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```
