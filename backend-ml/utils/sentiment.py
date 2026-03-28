from collections import Counter
import requests
from config import Config

POSITIVE = {'surge', 'bull', 'breakout', 'rally', 'gain', 'adoption', 'partnership'}
NEGATIVE = {'dump', 'bear', 'hack', 'selloff', 'ban', 'lawsuit', 'decline'}


def _score_text(text: str) -> int:
    words = text.lower().split()
    c = Counter(words)
    return sum(c[w] for w in POSITIVE) - sum(c[w] for w in NEGATIVE)


def sentiment_for_symbol(symbol: str) -> dict:
    params = {'lang': 'EN', 'categories': 'BTC,Blockchain', 'excludeCategories': 'Sponsored'}
    response = requests.get(Config.NEWS_ENDPOINT, params=params, timeout=10)
    response.raise_for_status()

    rows = response.json().get('Data', [])[:20]
    filtered = [r for r in rows if symbol.upper() in (r.get('title', '') + ' ' + r.get('body', '')).upper()]
    sample = filtered if filtered else rows

    score = sum(_score_text((r.get('title', '') + ' ' + r.get('body', ''))) for r in sample)
    label = 'neutral'
    if score > 3:
        label = 'positive'
    elif score < -3:
        label = 'negative'

    return {'symbol': symbol.upper(), 'score': score, 'label': label, 'articles_scanned': len(sample)}
