import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. Page Configuration
st.set_page_config(page_title="CipherStream Terminal", page_icon="📈", layout="wide")
st.title("📈 CipherStream: Live Crypto Terminal")
st.markdown("Enterprise Compute Pushdown Architecture with Self-Serve Analytics.")

# 2. Secure Connection
conn = st.connection("snowflake")

# 3. Dynamic UI Controls (Sidebar)
st.sidebar.header("Terminal Controls")

@st.cache_data(ttl=300)
def get_symbols():
    df = conn.query("SELECT DISTINCT SYMBOL FROM CIPHERSTREAM_DB.SILVER.CRYPTO_TICK_DATA")
    return df['SYMBOL'].tolist()

available_symbols = get_symbols()
selected_symbol = st.sidebar.selectbox("Select Asset", available_symbols if available_symbols else ["BTCUSDT"])

# DATE FILTERS: Default to the last 7 days
today = datetime.now()
seven_days_ago = today - timedelta(days=7)

col1, col2 = st.sidebar.columns(2)
with col1:
    start_date = st.date_input("Start Date", seven_days_ago)
with col2:
    end_date = st.date_input("End Date", today)

min_volume = st.sidebar.slider("Minimum Volume", min_value=0.0, max_value=50.0, value=0.0, step=0.5)
row_limit = st.sidebar.number_input("Max Rows to Fetch", min_value=10, max_value=5000, value=100, step=50)

# 4. COMPUTE PUSHDOWN: Now includes Date Filtering
@st.cache_data(ttl=60)
def fetch_filtered_data(symbol, min_vol, limit, start, end):
    # We format the dates so Snowflake understands them
    start_str = start.strftime("%Y-%m-%d 00:00:00")
    end_str = end.strftime("%Y-%m-%d 23:59:59")
    
    query = f"""
    SELECT * FROM CIPHERSTREAM_DB.SILVER.CRYPTO_TICK_DATA
    WHERE SYMBOL = '{symbol}' 
      AND VOLUME >= {min_vol}
      AND TIMESTAMP >= '{start_str}'
      AND TIMESTAMP <= '{end_str}'
    ORDER BY TIMESTAMP DESC
    LIMIT {limit}
    """
    df = conn.query(query)
    if not df.empty:
        df['TIMESTAMP'] = pd.to_datetime(df['TIMESTAMP'])
    return df

df = fetch_filtered_data(selected_symbol, min_volume, row_limit, start_date, end_date)

# 5. Build the UI using Tabs to keep it clean
tab1, tab2 = st.tabs(["Market Visualizer", "Admin SQL Sandbox"])

with tab1:
    if df.empty:
        st.warning("No data found for these filters. Try expanding your date range or lowering the volume filter.")
    else:
        chart_df = df.sort_values(by='TIMESTAMP', ascending=True)
        st.subheader(f"{selected_symbol} Price Action")

        fig = go.Figure(data=[go.Candlestick(
            x=chart_df['TIMESTAMP'],
            open=chart_df['OPEN'],
            high=chart_df['HIGH'],
            low=chart_df['LOW'],
            close=chart_df['CLOSE'],
            name="Market Data"
        )])

        fig.update_layout(
            xaxis_rangeslider_visible=False,
            height=600,
            template="plotly_dark",
            margin=dict(l=0, r=0, t=30, b=0)
        )
        st.plotly_chart(fig, width='stretch')

        st.subheader("Filtered Gold Layer Data")
        st.dataframe(df, width='stretch', hide_index=True)

with tab2:
    st.subheader("Direct Snowflake SQL Access")
    st.warning("⚠️ SECURITY NOTICE: In a production environment, raw text-to-SQL inputs are a massive SQL Injection risk. This is restricted to local Admin use only.")
    
    # Pre-fill with a helpful template
    default_query = f"SELECT \n    SYMBOL,\n    AVG(CLOSE) as AVERAGE_PRICE\nFROM CIPHERSTREAM_DB.SILVER.CRYPTO_TICK_DATA \nGROUP BY SYMBOL;"
    
    custom_query = st.text_area("Write your custom query here:", value=default_query, height=150)
    
    if st.button("🚀 Execute Custom Query"):
        with st.spinner("Executing against Snowflake..."):
            try:
                custom_df = conn.query(custom_query)
                st.success("Query Executed Successfully!")
                st.dataframe(custom_df, width='stretch', hide_index=True)
            except Exception as e:
                st.error(f"Snowflake Compilation Error:\n{e}")