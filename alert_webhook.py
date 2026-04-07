from kafka import KafkaConsumer
import json
import requests
from src.config import KAFKA_BOOTSTRAP_SERVERS, ALERTS_TOPIC, SLACK_WEBHOOK_URL

consumer = KafkaConsumer(
    ALERTS_TOPIC,
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
    auto_offset_reset='latest',
    enable_auto_commit=True,
)

def send_slack(alert):
    text = f"🚨 *Anomaly Detected* 🚨\nUser: `{alert['user_id']}`\nML Score: {alert['ml_score']:.3f}\nRule: {alert['rule_reason']}\nFeatures: {alert['features']}"
    requests.post(SLACK_WEBHOOK_URL, json={'text': text})

print("Listening for alerts...")
for msg in consumer:
    alert = msg.value
    send_slack(alert)
    print(f"Alert sent: {alert['user_id']}")