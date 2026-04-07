import json
import random
import time
from kafka import KafkaProducer
from src.config import KAFKA_BOOTSTRAP_SERVERS, RAW_BETS_TOPIC

producer = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

USER_IDS = [f"user_{i}" for i in range(1, 101)]   # 100 normal users
ANOMALY_USERS = ["bot_alice", "arb_bob"]          # will generate scripted behaviour

def generate_normal_bet(user_id):
    return {
        'bet_id': f"{user_id}_{int(time.time()*1000)}",
        'user_id': user_id,
        'timestamp': time.time(),
        'stake': round(random.uniform(0.5, 50.0), 2),
        'odds': round(random.uniform(1.5, 5.0), 2),
        'is_promo': random.random() < 0.1,
        'arb_score': random.uniform(0, 0.02),
    }

def generate_anomaly_bet(user_id):
    # high rate, high promo, low stake std
    return {
        'bet_id': f"{user_id}_{int(time.time()*1000)}",
        'user_id': user_id,
        'timestamp': time.time(),
        'stake': 10.0,   # identical stakes
        'odds': 2.0,
        'is_promo': random.random() < 0.9,
        'arb_score': random.uniform(0.04, 0.06),
    }

print("Sending bets to Kafka. Press Ctrl+C to stop.")
while True:
    # 80% normal, 20% anomaly users
    if random.random() < 0.2:
        user = random.choice(ANOMALY_USERS)
        bet = generate_anomaly_bet(user)
    else:
        user = random.choice(USER_IDS)
        bet = generate_normal_bet(user)

    producer.send(RAW_BETS_TOPIC, value=bet)
    # Simulate micro-bet speed: 10-200 ms between bets
    time.sleep(random.uniform(0.01, 0.2))