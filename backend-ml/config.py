import os
from dotenv import load_dotenv

load_dotenv()

FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.getenv("FLASK_PORT", 5001))
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"

NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")

CACHE_TYPE = "SimpleCache"
CACHE_DEFAULT_TIMEOUT = 300
COINS_CACHE_TIMEOUT = 3600
NEWS_CACHE_TIMEOUT = 600