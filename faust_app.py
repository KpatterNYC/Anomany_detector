import faust
import time
import numpy as np
from datetime import datetime
from src.config import (
    KAFKA_BOOTSTRAP_SERVERS, RAW_BETS_TOPIC, ALERTS_TOPIC,
    BET_RATE_WINDOW
)
from src.redis_client import rolling_bet_rate, add_bet_timestamp, distinct_devices_last_10min
from src.anomaly_models import rule_based_check, anomaly_score, load_or_train_model

app = faust.App(
    'anomaly_engine',
    broker=KAFKA_BOOTSTRAP_SERVERS,
    value_serializer='json',
)

# Topics
raw_bets_topic = app.topic(RAW_BETS_TOPIC, value_type=dict)
alerts_topic = app.topic(ALERTS_TOPIC, value_type=dict)

# Load ML model once at startup
@app.on_startup
async def init():
    load_or_train_model()

def extract_features(bet: dict) -> dict:
    user_id = bet['user_id']
    now = time.time()

    # 1. Bet rate (bets/sec over last 60s)
    rate = rolling_bet_rate(user_id, BET_RATE_WINDOW)

    # 2. Promo ratio – we need to track promo bets per user.
    # For demo, we'll read from bet['is_promo'] and use a simple Redis counter.
    # We'll implement a placeholder.
    promo_ratio = 0.5   # TODO: implement real counter

    # 3. Stake std dev – placeholder
    stake_std = 0.05

    # 4. Arb score – placeholder (in real life, call odds API)
    arb_score = 0.01

    # 5. Device count last 10 min
    device_count = distinct_devices_last_10min(user_id)

    # 6. Session velocity – time since last bet (from Redis last timestamp)
    # Placeholder
    last_bet_gap = 0.1   # seconds

    features = {
        'bet_rate': rate,
        'promo_bet_ratio': promo_ratio,
        'stake_std': stake_std,
        'arb_score': arb_score,
        'device_count': device_count,
        'last_bet_gap': last_bet_gap,
    }
    return features

@app.agent(raw_bets_topic)
async def detect_anomalies(stream):
    async for bet in stream:
        user_id = bet['user_id']
        timestamp = bet.get('timestamp', time.time())

        # 1. Store raw bet timestamp for rate calculation
        add_bet_timestamp(user_id, timestamp)

        # 2. Extract features
        feats = extract_features(bet)

        # 3. Rule-based check (fast)
        is_rule_anomaly, reason = rule_based_check(feats)

        # 4. ML score (if needed)
        feature_vector = np.array([
            feats['bet_rate'],
            feats['promo_bet_ratio'],
            feats['stake_std'],
            feats['arb_score'],
            feats['device_count'],
            feats['last_bet_gap']
        ])
        ml_score = anomaly_score(feature_vector)

        # 5. Decision (rule OR ml_score > 0.9)
        if is_rule_anomaly or ml_score > 0.9:
            alert = {
                'timestamp': datetime.utcnow().isoformat(),
                'user_id': user_id,
                'bet_id': bet.get('bet_id'),
                'features': feats,
                'rule_triggered': is_rule_anomaly,
                'rule_reason': reason if is_rule_anomaly else '',
                'ml_score': float(ml_score),
                'raw_bet': bet,
            }
            await alerts_topic.send(value=alert)
            print(f"ALERT: {alert['user_id']} | ml={ml_score:.3f} | {reason}")

if __name__ == '__main__':
    app.main()