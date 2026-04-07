# Kafka
KAFKA_BOOTSTRAP_SERVERS = 'localhost:9092'
RAW_BETS_TOPIC = 'raw_bets'
ALERTS_TOPIC = 'anomaly_alerts'

# Redis
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0

# Feature windows (seconds)
BET_RATE_WINDOW = 60
PROMO_WINDOW = 300          # 5 min
SESSION_VELOCITY_THRESH_MS = 200

# Anomaly thresholds
RULE_BET_RATE_MAX = 5.0
RULE_PROMO_RATIO_MIN = 0.8
RULE_STAKE_STD_MAX = 0.1
RULE_ARB_SCORE_MIN = 0.03

# ML model path
ISOLATION_FOREST_MODEL_PATH = 'isolation_forest_v1.joblib'

# Slack webhook (replace with your own)
SLACK_WEBHOOK_URL = 'https://hooks.slack.com/services/XXXX/YYYY/ZZZZ'