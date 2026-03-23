import os
from dotenv import load_dotenv

load_dotenv()

FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.getenv("FLASK_PORT", 5001))
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "models", "crypto_model.pkl")
META_PATH = os.path.join(BASE_DIR, "models", "model_meta.json")

FEATURES = [
    "rsi", "macd", "ema", "sma",
    "bb_high", "bb_low", "return", "volume_change"
]

CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", 65.0))

COINGECKO_BASE = "https://api.coingecko.com/api/v3"
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY", "")
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")

CACHE_TYPE = "SimpleCache"
CACHE_DEFAULT_TIMEOUT = 300
COINS_CACHE_TIMEOUT = 3600
NEWS_CACHE_TIMEOUT = 600