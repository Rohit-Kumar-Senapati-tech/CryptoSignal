import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    PORT = int(os.getenv('ML_PORT', 8000))
    COINGECKO_BASE = 'https://api.coingecko.com/api/v3'
    NEWS_ENDPOINT = 'https://min-api.cryptocompare.com/data/v2/news/'
