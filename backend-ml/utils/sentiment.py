"""
sentiment.py
Fetches crypto news from NewsAPI and scores each headline
using a simple but effective keyword-based sentiment approach.
Falls back gracefully if the API key is missing or rate-limited.
"""
import logging
import time
from datetime import datetime, timedelta
from typing import Optional

import requests

log = logging.getLogger(__name__)

# ── Cache ──────────────────────────────────────────────────────────────────────
_news_cache: dict = {}
NEWS_CACHE_TTL = 600  # 10 minutes

# ── Sentiment keyword lists ────────────────────────────────────────────────────
BULLISH_KEYWORDS = [
    "surge", "soar", "rally", "bull", "breakout", "gain", "rise",
    "jump", "spike", "pump", "recover", "high", "record", "adopt",
    "partnership", "launch", "upgrade", "buy", "accumulate", "positive",
    "growth", "profit", "win", "approval", "listing", "integration",
    "milestone", "institutional", "etf", "inflow", "demand", "bullish"
]

BEARISH_KEYWORDS = [
    "crash", "plunge", "drop", "fall", "bear", "dump", "sell",
    "decline", "loss", "low", "hack", "ban", "regulation", "fear",
    "warning", "risk", "concern", "fraud", "scam", "liquidation",
    "outflow", "correction", "panic", "fear", "negative", "bearish",
    "lawsuit", "fine", "penalty", "collapse", "fail", "trouble"
]


# ── News fetcher ───────────────────────────────────────────────────────────────
def fetch_crypto_news(
    symbol: str = "BTC",
    api_key: str = "",
    max_articles: int = 20
) -> list[dict]:
    """
    Fetch latest crypto news headlines for a symbol.

    Args:
        symbol:       Coin symbol e.g. 'BTC', 'ETH', 'SOL'
        api_key:      NewsAPI key from .env
        max_articles: Max number of articles to fetch

    Returns:
        List of article dicts with keys: title, description, url,
        publishedAt, source, sentiment_score, sentiment_label
    """
    # Clean symbol — remove -USD suffix if present
    clean_symbol = symbol.replace("-USD", "").replace("-USDT", "").upper()

    # Map symbol to full coin name for better search results
    coin_names = {
        "BTC": "Bitcoin",
        "ETH": "Ethereum",
        "SOL": "Solana",
        "BNB": "Binance",
        "XRP": "Ripple",
        "ADA": "Cardano",
        "DOGE": "Dogecoin",
        "AVAX": "Avalanche",
        "DOT": "Polkadot",
        "MATIC": "Polygon",
        "LINK": "Chainlink",
        "LTC": "Litecoin",
    }
    coin_name = coin_names.get(clean_symbol, clean_symbol)

    # ── Check cache ────────────────────────────────────────────────────────────
    cache_key = clean_symbol
    if cache_key in _news_cache:
        cached_time = _news_cache[cache_key]["timestamp"]
        if (datetime.utcnow() - cached_time).seconds < NEWS_CACHE_TTL:
            log.info("News cache hit for %s", clean_symbol)
            return _news_cache[cache_key]["data"]

    # ── No API key — return empty gracefully ───────────────────────────────────
    if not api_key:
        log.warning("No NEWS_API_KEY set — skipping news fetch")
        return []

    # ── Fetch from NewsAPI ─────────────────────────────────────────────────────
    query    = f"{coin_name} OR {clean_symbol} crypto"
    from_date = (datetime.utcnow() - timedelta(days=3)).strftime("%Y-%m-%d")

    url = "https://newsapi.org/v2/everything"
    params = {
        "q":          query,
        "from":       from_date,
        "sortBy":     "publishedAt",
        "language":   "en",
        "pageSize":   max_articles,
        "apiKey":     api_key,
    }

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") != "ok":
            log.error("NewsAPI error: %s", data.get("message", "unknown"))
            return []

        articles = data.get("articles", [])

    except requests.exceptions.Timeout:
        log.error("NewsAPI request timed out")
        return []
    except requests.exceptions.HTTPError as exc:
        log.error("NewsAPI HTTP error: %s", exc)
        return []
    except Exception as exc:
        log.exception("Unexpected error fetching news: %s", exc)
        return []

    # ── Score each article ─────────────────────────────────────────────────────
    scored_articles = []
    for article in articles:
        title       = article.get("title", "") or ""
        description = article.get("description", "") or ""
        text        = (title + " " + description).lower()

        score, label = _score_sentiment(text)

        scored_articles.append({
            "title":           title,
            "description":     description,
            "url":             article.get("url", ""),
            "publishedAt":     article.get("publishedAt", ""),
            "source":          article.get("source", {}).get("name", "Unknown"),
            "sentiment_score": score,
            "sentiment_label": label,
        })

    # ── Sort: most recent first ────────────────────────────────────────────────
    scored_articles.sort(
        key=lambda x: x["publishedAt"],
        reverse=True
    )

    # ── Cache result ───────────────────────────────────────────────────────────
    _news_cache[cache_key] = {
        "data":      scored_articles,
        "timestamp": datetime.utcnow()
    }

    log.info("Fetched %d news articles for %s", len(scored_articles), clean_symbol)
    return scored_articles


# ── Sentiment scoring ──────────────────────────────────────────────────────────
def _score_sentiment(text: str) -> tuple[float, str]:
    """
    Score text sentiment using keyword matching.

    Returns:
        (score, label) where:
          score  = float between -1.0 (very bearish) and +1.0 (very bullish)
          label  = 'bullish', 'bearish', or 'neutral'
    """
    text = text.lower()

    bullish_hits = sum(1 for kw in BULLISH_KEYWORDS if kw in text)
    bearish_hits = sum(1 for kw in BEARISH_KEYWORDS if kw in text)

    total = bullish_hits + bearish_hits
    if total == 0:
        return 0.0, "neutral"

    # Score from -1 to +1
    score = (bullish_hits - bearish_hits) / total

    if score > 0.1:
        label = "bullish"
    elif score < -0.1:
        label = "bearish"
    else:
        label = "neutral"

    return round(score, 4), label


# ── Aggregate sentiment ────────────────────────────────────────────────────────
def get_sentiment_summary(
    symbol: str,
    api_key: str = "",
) -> dict:
    """
    Return aggregated sentiment summary for a coin symbol.
    Used by the Flask API to send one clean object to the frontend.

    Returns:
        dict with keys:
          overall_score   - average sentiment score (-1 to +1)
          overall_label   - 'bullish', 'bearish', or 'neutral'
          bullish_count   - number of bullish articles
          bearish_count   - number of bearish articles
          neutral_count   - number of neutral articles
          total_articles  - total articles analysed
          articles        - list of top 5 most recent articles
    """
    articles = fetch_crypto_news(symbol=symbol, api_key=api_key)

    if not articles:
        return {
            "overall_score":  0.0,
            "overall_label":  "neutral",
            "bullish_count":  0,
            "bearish_count":  0,
            "neutral_count":  0,
            "total_articles": 0,
            "articles":       [],
        }

    scores         = [a["sentiment_score"] for a in articles]
    overall_score  = round(sum(scores) / len(scores), 4)

    bullish_count  = sum(1 for a in articles if a["sentiment_label"] == "bullish")
    bearish_count  = sum(1 for a in articles if a["sentiment_label"] == "bearish")
    neutral_count  = sum(1 for a in articles if a["sentiment_label"] == "neutral")

    if overall_score > 0.1:
        overall_label = "bullish"
    elif overall_score < -0.1:
        overall_label = "bearish"
    else:
        overall_label = "neutral"

    return {
        "overall_score":  overall_score,
        "overall_label":  overall_label,
        "bullish_count":  bullish_count,
        "bearish_count":  bearish_count,
        "neutral_count":  neutral_count,
        "total_articles": len(articles),
        "articles":       articles[:5],   # top 5 for frontend display
    }