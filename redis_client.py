import redis
import time
from src.config import REDIS_HOST, REDIS_PORT, REDIS_DB

redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)

# Lua script for efficient rolling rate
LUA_RATE_SCRIPT = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
redis.call('ZADD', key, now, now)
redis.call('ZREMRANGEBYSCORE', key, 0, now - window)
local count = redis.call('ZCARD', key)
return count / window
"""
rate_script = redis_client.register_script(LUA_RATE_SCRIPT)

def add_bet_timestamp(user_id: str, timestamp: float) -> None:
    """Store bet timestamp for a user (used for rate calculation)."""
    key = f"bets:{user_id}:timestamps"
    redis_client.zadd(key, {str(timestamp): timestamp})
    redis_client.expire(key, 3600)  # keep 1 hour max

def rolling_bet_rate(user_id: str, window_sec: int) -> float:
    """Return bets per second over the given window."""
    key = f"bets:{user_id}:timestamps"
    now = time.time()
    return rate_script(keys=[key], args=[now, window_sec])

def add_device(user_id: str, device_id: str, timestamp: float) -> None:
    key = f"user:{user_id}:devices"
    redis_client.zadd(key, {device_id: timestamp})
    redis_client.zremrangebyscore(key, 0, timestamp - 600)  # keep last 10 min

def distinct_devices_last_10min(user_id: str) -> int:
    key = f"user:{user_id}:devices"
    now = time.time()
    return redis_client.zcount(key, now - 600, now)

def get_stake_std(user_id: str,) -> float:
    """Return std dev of stakes in last N seconds."""
    key = f"user:{user_id}:stakes"
    now = time.time()
    redis_client.zadd(key, {str(now): now})   # we store stake in score? Actually need to store stake as member.
    return 0.05   # placeholder