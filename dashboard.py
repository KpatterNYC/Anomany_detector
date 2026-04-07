import streamlit as st
import pandas as pd
from kafka import KafkaConsumer
import json
import threading
from collections import deque
from src.config import KAFKA_BOOTSTRAP_SERVERS, ALERTS_TOPIC

st.set_page_config(page_title="Fraud Alert Dashboard", layout="wide")
st.title("🚨 Real‑Time Anomaly Alerts")

# Store last 100 alerts in a deque
alert_queue = deque(maxlen=100)

def consume_alerts():
    consumer = KafkaConsumer(
        ALERTS_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        auto_offset_reset='latest'
    )
    for msg in consumer:
        alert_queue.appendleft(msg.value)

# Start consumer in background thread
thread = threading.Thread(target=consume_alerts, daemon=True)
thread.start()

# Auto-refresh every 2 seconds
placeholder = st.empty()
while True:
    if alert_queue:
        df = pd.DataFrame(alert_queue)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        placeholder.dataframe(df[['timestamp', 'user_id', 'ml_score', 'rule_reason']], use_container_width=True)
    else:
        placeholder.info("Waiting for alerts...")
    import time; time.sleep(2)