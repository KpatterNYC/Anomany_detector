import joblib
import numpy as np
from sklearn.ensemble import IsolationForest
from src.config import ISOLATION_FOREST_MODEL_PATH

# Global model (trained offline, loaded at startup)
model = None

def load_or_train_model():
    global model
    try:
        model = joblib.load(ISOLATION_FOREST_MODEL_PATH)
        print("Loaded existing Isolation Forest model.")
    except FileNotFoundError:
        print("No model found. Training a dummy one...")
        # Dummy training on random normal data
        X_train = np.random.randn(1000, 5)
        model = IsolationForest(contamination=0.05, random_state=42)
        model.fit(X_train)
        joblib.dump(model, ISOLATION_FOREST_MODEL_PATH)
        print("Model trained and saved.")

def anomaly_score(features: np.ndarray) -> float:
    """
    Returns anomaly score in [0,1], where higher = more anomalous.
    features: 1D array of feature values.
    """
    global model
    if model is None:
        load_or_train_model()
    # decision_function: more negative = more anomalous
    decision = model.decision_function([features])[0]   # range roughly [-0.5, 0.5]
    # Normalize to 0-1, where 1 = most anomalous
    score = 1.0 / (1.0 + np.exp(decision * 5))   # sigmoid, inverted
    return score

def rule_based_check(features_dict: dict) -> tuple[bool, str]:
    """
    Returns (is_anomaly, reason)
    features_dict expected keys: bet_rate, promo_bet_ratio, stake_std, arb_score
    """
    rate = features_dict.get('bet_rate', 0)
    promo_ratio = features_dict.get('promo_bet_ratio', 0)
    stake_std = features_dict.get('stake_std', 1)
    arb = features_dict.get('arb_score', 0)

    if rate > 5.0 and promo_ratio > 0.8:
        return True, f"High rate ({rate:.2f}) + promo abuse ({promo_ratio:.2f})"
    if stake_std < 0.1 and arb > 0.03:
        return True, f"Too consistent stakes ({stake_std:.3f}) + arbitrage ({arb:.3f})"
    if rate > 10.0:
        return True, f"Extreme bet rate ({rate:.2f})"
    return False, ""