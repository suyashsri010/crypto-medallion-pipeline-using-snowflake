# Start with the official Airflow computer
FROM apache/airflow:2.9.1

# Copy our shopping list into that computer
COPY requirements.txt /requirements.txt

# Tell the computer to install the shopping list
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r /requirements.txt