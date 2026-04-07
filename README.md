# FanDuel Real-Time Anomaly Detection Engine – Fraud Analyst Angle

**Stop scripted betting, arbitrage abuse, and promo fraud before the bet settles.**

At FanDuel, millions of micro-bets arrive every minute. Fraudsters use bots and syndicates to instantly exploit arbitrage opportunities or drain promotions. A GRC analyst looking at a spreadsheet is too slow. This project builds the **tripwire** – a low-latency, streaming anomaly detection engine that scores every bet in real time and alerts the fraud team.

> **This is the first of two FanDuel fraud projects.** The second focuses on **Identity Resolution & Device Fingerprinting** to link multi-accounts (banned users creating new accounts with relatives’ identities).

## Problem Statement

FanDuel faces two massive fraud vectors:

1. **Promo / Arb abuse** – Scripts place hundreds of micro-bets per second, using free bets or boosted odds, or exploiting price differences across sportsbooks.
2. **Multi-accounting** – A user banned for problem gambling creates a new account using a relative’s identity. Legacy GRC tools can’t link these accounts fast enough.

This engine solves **#1** in real time. It complements a separate identity resolution engine (project two) that solves **#2** using graph-based device fingerprinting.

## Architecture Overview

```text
FanDuel Betting API → Kafka (raw_bets) → Faust Stream Processor → Redis Feature Store
                                                                     ↓
                                                      Rule Engine + Isolation Forest
                                                                     ↓
                                                         Kafka (anomaly_alerts)
                                                                     ↓
                                            ┌────────────────────────┼────────────────────────┐
                                            ↓                                                 ↓
                                Slack (Fraud Channel)                    Streamlit Dashboard (Future: Case Manager)
```

- **Kafka** – Handles the high throughput of micro-bets (partitioned by `user_id`).
- **Redis** – Stores rolling time-windows per user: bet timestamps, stake values, device IDs, promo flags.
- **Faust** – Python stream processor that extracts features and scores each bet in <200ms.
- **Isolation Forest** – Unsupervised ML model, trained offline on FanDuel’s historical normal behaviour, to catch non-linear anomalies.
- **Alerts** – Delivered to the fraud analyst’s Slack channel and a live dashboard.

## Key Anomalies Detected

| Fraud Type | Indicators (Tripwires) |
|------------|------------------------|
| **Scripted high-frequency betting** | Bet rate >5/sec, identical stakes (std <0.1), inter-bet delay <200ms |
| **Promo abuse** | >80% of bets use a promotion + rate >5/sec |
| **Arbitrage (arb) betting** | Odds difference vs. competitors >3% AND stake standard deviation <0.1 |
| **Syndicate behaviour** | Multiple users sharing the same device fingerprint (handled by identity resolution, but can feed features like `device_count_last_10min`) |

## Tech Stack

- **Python 3.10+**
- **Apache Kafka** (broker, topics: `raw_bets`, `anomaly_alerts`)
- **Redis** (in-memory feature store with Lua scripts for atomic rolling windows)
- **Faust** (stream processing, integrates with Kafka)
- **scikit-learn** (Isolation Forest model)
- **Streamlit** (real-time dashboard for fraud analysts)
- **Docker Compose** (local Kafka + Redis for development)
- **Slack Webhook** (alert destination)

## Project Structure

```text
fanduel_anomaly_engine/
├── docker-compose.yml       # Kafka, Zookeeper, Redis
├── requirements.txt
├── config.py                # All FanDuel-specific thresholds & endpoints
├── redis_client.py          # Rolling bet rate, stake std, device count (Lua)
├── anomaly_models.py        # Rule tripwires + Isolation Forest wrapper
├── faust_app.py             # Main stream processor (the tripwire)
├── data_simulator.py        # Generates synthetic FanDuel-like bets
├── alert_webhook.py         # Consumes alerts → Slack (#fraud-alerts)
├── dashboard.py             # Streamlit dashboard for fraud team
└── README.md
```

## Prerequisites

- Docker & Docker Compose (for local Kafka/Redis)
- Python 3.10+
- A Slack webhook URL for your FanDuel fraud channel (optional but recommended)

## Installation & Setup

### 1. Clone / create the project

```bash
mkdir fanduel_anomaly_engine && cd fanduel_anomaly_engine
# Copy all the files above into this directory
```

### 2. Start infrastructure (Kafka + Redis)

```bash
docker-compose up -d
```
Wait 30 seconds for Kafka to fully initialise.

### 3. Create Python virtual environment

```bash
python3.10 -m venv venv
source venv/bin/activate   # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
```

### 4. (Optional) Configure Slack

Edit `config.py` and set:

```python
SLACK_WEBHOOK_URL = 'https://hooks.slack.com/services/FANDUEL/...'
```
If you skip this, alerts still print to the console and appear in the dashboard.

## Running the System

You need three terminals (or run as background services).

### Terminal 1 – Faust Tripwire (stream processor)
```bash
python faust_app.py worker -l info
```

### Terminal 2 – Data Simulator (generates fake bets)
```bash
python data_simulator.py
```

### Terminal 3 – Alert Consumer (choose one)
Slack notifier:
```bash
python alert_webhook.py
```
Streamlit dashboard:
```bash
streamlit run dashboard.py
```
*(then open http://localhost:8501)*

## Configuration (FanDuel-Specific)

All tunable parameters live in `config.py`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `BET_RATE_WINDOW` | 60 sec | Rolling window for bet frequency |
| `RULE_BET_RATE_MAX` | 5.0 | Bets/sec threshold (rule) |
| `RULE_STAKE_STD_MAX` | 0.1 | Maximum stake std dev allowed |
| `RULE_ARB_SCORE_MIN` | 0.03 | Minimum arbitrage opportunity % |
| `ISOLATION_FOREST_MODEL_PATH` | `isolation_forest_v1.joblib` | Model file |
| `SLACK_WEBHOOK_URL` | (empty) | Set to enable Slack alerts |

*Adjust thresholds based on FanDuel’s historical data. For example, if normal bet rate peaks at 3/sec during March Madness, raise `RULE_BET_RATE_MAX` to 6.*

## How the Tripwire Works (Detailed)

### Step 1 – Feature Extraction (per bet)
When a bet arrives, the Faust agent:
- Fetches rolling features from Redis:
  - `bet_rate` – number of bets in last 60s / 60
  - `promo_bet_ratio` – fraction of promo bets in last 5min
  - `stake_std` – standard deviation of stakes in last 60s
  - `device_count` – distinct device IDs used by user in last 10min
  - `last_bet_gap` – time since previous bet (ms)
- Stores new data (timestamp, stake, promo flag, device ID) for future windows.

### Step 2 – Anomaly Scoring
Two parallel detectors:
- **Rule engine (fast, interpretable)**: E.g., if `bet_rate` > 5 and `promo_ratio` > 0.8 → alert
- **Isolation Forest (trained offline on normal behaviour)**: Returns a score in `[0,1]` where >0.9 is anomalous.

### Step 3 – Alert Decision
If either detector triggers, an alert JSON is sent to `anomaly_alerts` topic.
Alert contains: `user_id`, `timestamp`, feature values, rule reason, ML score, and the original bet.

### Step 4 – Alert Delivery
- **Slack webhook** posts a formatted message to your FanDuel fraud channel.
- **Streamlit dashboard** shows a live table of the last 100 alerts.

## Fraud Analyst Dashboard

The Streamlit dashboard auto-refreshes every 2 seconds and displays:

| timestamp | user_id | ml_score | rule_reason |
|-----------|---------|----------|-------------|
| 2025-03-22 10:23:45 | `bot_alice` | 0.97 | High rate (6.2) + promo abuse (0.9) |
| 2025-03-22 10:23:47 | `arb_bob` | 0.88 | Too consistent stakes (0.03) + arbitrage (0.04) |

It’s built for fraud analysts to triage quickly. Clicking a row can trigger a deeper lookup into the user’s identity resolution graph (project two).

## Production Deployment at FanDuel

For real FanDuel scale (millions of bets/minute):
- **Kafka** – Increase partitions to match concurrency (e.g., 64 partitions for `raw_bets`).
- **Faust** – Run multiple workers behind a consumer group.
- **Redis** – Use Redis Cluster with persistence (RDB/AOF) and shard by `user_id`.
- **Models** – Retrain Isolation Forest every hour on the last 24h of normal bets; hot-reload with `joblib`.
- **Feature placeholders** – Replace `promo_ratio`, `stake_std`, `arb_score` with real Redis aggregations (use Lua scripts for atomic updates) and an external odds API (e.g., The Odds API) for arbitrage detection.
- **Monitoring** – Prometheus + Grafana to track latency, alert throughput, and model drift.

## Next Steps: Identity Resolution & Device Fingerprinting

This engine catches behavioural anomalies. But what if a banned user creates a new account using a relative’s identity? That’s where project two comes in.

Identity Resolution Engine will:
1. Collect device fingerprints (canvas, WebGL, fonts, etc.) via a JavaScript agent.
2. Hash and store fingerprints per user in a graph database (Neo4j) or Redis with edges: `(user)-[:USED_DEVICE]->(fingerprint)`.
3. Run connected-components (or label propagation) to link multiple accounts sharing the same fingerprint, IP subnet, or similar name.
4. Expose a REST API that the anomaly engine can call to enrich alerts with a `multi_account_risk_score`.

The two engines together form a complete FanDuel fraud detection system.
