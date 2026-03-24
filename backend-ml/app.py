from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_caching import Cache
import requests
import pandas as pd
import yfinance as yf
import ta
import os
from datetime import datetime, timezone

from config import (
    FLASK_HOST,
    FLASK_PORT,
    FLASK_DEBUG,
    CACHE_TYPE,
    CACHE_DEFAULT_TIMEOUT,
    NEWS_API_KEY,
    COINS_CACHE_TIMEOUT,
    NEWS_CACHE_TIMEOUT,
)

app = Flask(__name__)

app.config["JSON_SORT_KEYS"] = False
app.config["CACHE_TYPE"] = CACHE_TYPE
app.config["CACHE_DEFAULT_TIMEOUT"] = CACHE_DEFAULT_TIMEOUT

CORS(app, resources={r"/*": {"origins": "*"}})
cache = Cache(app)


# ── Helpers ────────────────────────────────────────────────────────────────

BINANCE_EXCHANGE_INFO_URL = "https://api.binance.com/api/v3/exchangeInfo"


def safe_float(value, default=0.0):
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def normalize_symbol(symbol: str) -> str:
    symbol = (symbol or "BTC-USD").upper().strip()
    if "-" not in symbol:
        return f"{symbol}-USD"
    return symbol


def symbol_to_coin(symbol: str) -> str:
    return normalize_symbol(symbol).split("-")[0]


def get_news_query(symbol: str) -> str:
    coin = symbol_to_coin(symbol)

    keyword_map = {
        "BTC": "Bitcoin OR BTC crypto",
        "ETH": "Ethereum OR ETH crypto",
        "SOL": "Solana OR SOL crypto",
        "BNB": "BNB OR Binance Coin crypto",
        "XRP": "XRP OR Ripple crypto",
        "DOGE": "Dogecoin OR DOGE crypto",
        "ADA": "Cardano OR ADA crypto",
        "AVAX": "Avalanche OR AVAX crypto",
        "LINK": "Chainlink OR LINK crypto",
        "MATIC": "Polygon OR MATIC crypto",
        "LTC": "Litecoin OR LTC crypto",
        "DOT": "Polkadot OR DOT crypto",
        "TRX": "TRON OR TRX crypto",
        "ATOM": "Cosmos OR ATOM crypto",
        "NEAR": "NEAR Protocol crypto",
        "APT": "Aptos crypto",
        "ARB": "Arbitrum crypto",
        "OP": "Optimism crypto",
    }

    return keyword_map.get(coin, f"{coin} crypto")


def get_ticker_history(symbol: str, period="3mo", interval="1d"):
    symbol = normalize_symbol(symbol)
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period, interval=interval, auto_adjust=False)

    if df is None or df.empty:
        raise ValueError(f"No market data found for {symbol}")

    df = df.reset_index()

    # Standardize columns
    rename_map = {}
    for col in df.columns:
        lower = str(col).lower()
        if "date" in lower or "datetime" in lower:
            rename_map[col] = "Date"
        elif lower == "open":
            rename_map[col] = "Open"
        elif lower == "high":
            rename_map[col] = "High"
        elif lower == "low":
            rename_map[col] = "Low"
        elif lower == "close":
            rename_map[col] = "Close"
        elif lower == "volume":
            rename_map[col] = "Volume"

    df = df.rename(columns=rename_map)

    required = ["Date", "Open", "High", "Low", "Close", "Volume"]
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    return df


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    out["rsi"] = ta.momentum.RSIIndicator(close=out["Close"], window=14).rsi()

    macd_obj = ta.trend.MACD(close=out["Close"])
    out["macd"] = macd_obj.macd()

    out["ema"] = ta.trend.EMAIndicator(close=out["Close"], window=20).ema_indicator()
    out["sma"] = ta.trend.SMAIndicator(close=out["Close"], window=20).sma_indicator()

    bb = ta.volatility.BollingerBands(close=out["Close"], window=20, window_dev=2)
    out["bb_high"] = bb.bollinger_hband()
    out["bb_low"] = bb.bollinger_lband()

    out["return"] = out["Close"].pct_change()
    out["volume_change"] = out["Volume"].pct_change()

    return out


def latest_snapshot(symbol: str):
    df = get_ticker_history(symbol, period="3mo", interval="1d")
    df = compute_indicators(df)
    latest = df.iloc[-1]

    close_price = safe_float(latest["Close"])
    prev_close = safe_float(df.iloc[-2]["Close"]) if len(df) > 1 else close_price
    change_24h = ((close_price - prev_close) / prev_close * 100) if prev_close else 0.0

    return {
        "symbol": normalize_symbol(symbol),
        "price": round(close_price, 6),
        "change_24h": round(change_24h, 4),
        "rsi": round(safe_float(latest["rsi"]), 4),
        "macd": round(safe_float(latest["macd"]), 6),
        "ema": round(safe_float(latest["ema"]), 6),
        "sma": round(safe_float(latest["sma"]), 6),
        "bb_high": round(safe_float(latest["bb_high"]), 6),
        "bb_low": round(safe_float(latest["bb_low"]), 6),
        "return": round(safe_float(latest["return"]), 6),
        "volume_change": round(safe_float(latest["volume_change"]), 6),
    }


def score_market_signal(snapshot: dict):
    score = 0
    reasons = []

    price = snapshot["price"]
    rsi = snapshot["rsi"]
    macd = snapshot["macd"]
    ema = snapshot["ema"]
    sma = snapshot["sma"]
    bb_high = snapshot["bb_high"]
    bb_low = snapshot["bb_low"]
    day_return = snapshot["return"]
    volume_change = snapshot["volume_change"]

    if rsi < 35:
        score += 2
        reasons.append("RSI indicates oversold momentum")
    elif rsi > 70:
        score -= 2
        reasons.append("RSI indicates overbought momentum")

    if macd > 0:
        score += 1
        reasons.append("MACD is positive")
    else:
        score -= 1
        reasons.append("MACD is negative")

    if price > ema:
        score += 1
        reasons.append("Price is above EMA")
    else:
        score -= 1
        reasons.append("Price is below EMA")

    if price > sma:
        score += 1
        reasons.append("Price is above SMA")
    else:
        score -= 1
        reasons.append("Price is below SMA")

    if bb_low and price < bb_low:
        score += 1
        reasons.append("Price is below lower Bollinger band")
    elif bb_high and price > bb_high:
        score -= 1
        reasons.append("Price is above upper Bollinger band")

    if day_return > 0:
        score += 1
        reasons.append("Recent return is positive")
    elif day_return < 0:
        score -= 1
        reasons.append("Recent return is negative")

    if volume_change > 0.10:
        score += 1
        reasons.append("Volume is increasing")
    elif volume_change < -0.10:
        score -= 1
        reasons.append("Volume is decreasing")

    if score >= 3:
        signal = "BUY"
        prediction = "Bullish"
    elif score <= -3:
        signal = "SELL"
        prediction = "Bearish"
    else:
        signal = "HOLD"
        prediction = "Neutral"

    confidence = min(95.0, max(55.0, 60.0 + abs(score) * 6.5))

    return {
        "signal": signal,
        "prediction": prediction,
        "confidence": round(confidence, 2),
        "score": score,
        "reasons": reasons,
    }


def analyze_articles_sentiment(articles):
    positive_words = [
        "surge", "rise", "bullish", "gain", "growth", "up", "breakout", "strong",
        "rally", "record", "adoption", "approval", "profit", "positive", "boom"
    ]
    negative_words = [
        "drop", "fall", "bearish", "loss", "down", "crash", "weak", "decline",
        "ban", "hack", "lawsuit", "selloff", "negative", "collapse", "risk"
    ]

    raw_score = 0.0

    for article in articles:
        title = (article.get("title") or "").lower()
        description = (article.get("description") or "").lower()
        text = f"{title} {description}"

        pos_hits = sum(1 for word in positive_words if word in text)
        neg_hits = sum(1 for word in negative_words if word in text)
        raw_score += (pos_hits - neg_hits)

    if not articles:
        return "neutral", 0.0

    normalized_score = round(raw_score / len(articles), 2)

    if normalized_score > 0.3:
        return "positive", normalized_score
    if normalized_score < -0.3:
        return "negative", normalized_score
    return "neutral", normalized_score


@cache.memoize(timeout=NEWS_CACHE_TIMEOUT)
def fetch_news(symbol: str):
    if not NEWS_API_KEY:
        return {
            "symbol": symbol,
            "sentiment": "neutral",
            "score": 0.0,
            "articles": [],
            "message": "NEWS_API_KEY is missing"
        }

    query = get_news_query(symbol)

    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 6,
        "apiKey": NEWS_API_KEY,
    }

    response = requests.get(url, params=params, timeout=12)
    data = response.json()

    if response.status_code != 200:
        return {
            "symbol": symbol,
            "sentiment": "neutral",
            "score": 0.0,
            "articles": [],
            "message": data.get("message", "News API request failed")
        }

    raw_articles = data.get("articles", [])
    articles = []

    for article in raw_articles:
        articles.append({
            "title": article.get("title"),
            "description": article.get("description"),
            "url": article.get("url"),
            "source": (article.get("source") or {}).get("name"),
            "publishedAt": article.get("publishedAt")
        })

    sentiment_label, sentiment_score = analyze_articles_sentiment(articles)

    return {
        "symbol": symbol,
        "sentiment": sentiment_label,
        "score": sentiment_score,
        "articles": articles
    }


@cache.cached(timeout=COINS_CACHE_TIMEOUT, key_prefix="binance_coins")
def fetch_binance_coins():
    response = requests.get(BINANCE_EXCHANGE_INFO_URL, timeout=15)
    response.raise_for_status()
    data = response.json()

    symbols = data.get("symbols", [])
    coins = []

    seen = set()
    for item in symbols:
        if item.get("status") != "TRADING":
            continue
        if item.get("quoteAsset") != "USDT":
            continue

        base = item.get("baseAsset")
        if not base or base in seen:
            continue

        seen.add(base)
        coins.append({
            "symbol": base,
            "name": base,
            "pair": f"{base}-USD"
        })

    priority = [
        "BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "ADA", "AVAX",
        "LINK", "MATIC", "LTC", "DOT", "TRX", "ATOM", "NEAR",
        "APT", "ARB", "OP"
    ]

    coins.sort(key=lambda x: (priority.index(x["symbol"]) if x["symbol"] in priority else 9999, x["symbol"]))
    return coins


# ── Routes ────────────────────────────────────────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "service": "backend-ml",
        "time": datetime.now(timezone.utc).isoformat()
    }), 200


@app.route("/model/info", methods=["GET"])
def model_info():
    return jsonify({
        "status": "ok",
        "model": "real-time rules engine",
        "source": "yfinance + ta + NewsAPI",
        "message": "Prediction uses live market data and indicator scoring"
    }), 200


@app.route("/coins", methods=["GET"])
def coins():
    try:
        return jsonify(fetch_binance_coins()[:50]), 200
    except Exception as e:
        return jsonify({
            "error": "Failed to fetch coins",
            "message": str(e)
        }), 500


@app.route("/binance/coins", methods=["GET"])
def binance_coins():
    try:
        return jsonify(fetch_binance_coins()), 200
    except Exception as e:
        return jsonify({
            "error": "Failed to fetch Binance coins",
            "message": str(e)
        }), 500


@app.route("/price", methods=["GET"])
def price():
    try:
        symbol = normalize_symbol(request.args.get("symbol", "BTC-USD"))
        snapshot = latest_snapshot(symbol)
        return jsonify({
            "symbol": snapshot["symbol"],
            "price": snapshot["price"],
            "change_24h": snapshot["change_24h"]
        }), 200
    except Exception as e:
        return jsonify({
            "error": "Failed to fetch price",
            "message": str(e)
        }), 500


@app.route("/indicators", methods=["GET"])
def indicators():
    try:
        symbol = normalize_symbol(request.args.get("symbol", "BTC-USD"))
        snapshot = latest_snapshot(symbol)
        return jsonify({
            "symbol": snapshot["symbol"],
            "rsi": snapshot["rsi"],
            "macd": snapshot["macd"],
            "ema": snapshot["ema"],
            "sma": snapshot["sma"],
            "bb_high": snapshot["bb_high"],
            "bb_low": snapshot["bb_low"],
            "return": snapshot["return"],
            "volume_change": snapshot["volume_change"]
        }), 200
    except Exception as e:
        return jsonify({
            "error": "Failed to compute indicators",
            "message": str(e)
        }), 500


@app.route("/sentiment", methods=["GET"])
def sentiment():
    try:
        symbol = normalize_symbol(request.args.get("symbol", "BTC-USD"))
        result = fetch_news(symbol)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            "symbol": normalize_symbol(request.args.get("symbol", "BTC-USD")),
            "sentiment": "neutral",
            "score": 0.0,
            "articles": [],
            "message": str(e)
        }), 200


@app.route("/predict", methods=["GET"])
def predict():
    try:
        symbol = normalize_symbol(request.args.get("symbol", "BTC-USD"))
        snapshot = latest_snapshot(symbol)
        signal_data = score_market_signal(snapshot)

        return jsonify({
            "symbol": symbol,
            "prediction": signal_data["prediction"],
            "confidence": signal_data["confidence"],
            "signal": signal_data["signal"],
            "price": snapshot["price"],
            "change_24h": snapshot["change_24h"],
            "indicators": {
                "rsi": snapshot["rsi"],
                "macd": snapshot["macd"],
                "ema": snapshot["ema"],
                "sma": snapshot["sma"],
                "bb_high": snapshot["bb_high"],
                "bb_low": snapshot["bb_low"],
                "return": snapshot["return"],
                "volume_change": snapshot["volume_change"]
            },
            "score": signal_data["score"],
            "reasons": signal_data["reasons"],
            "message": "Prediction generated from live market data"
        }), 200

    except Exception as e:
        return jsonify({
            "error": "Failed to generate prediction",
            "message": str(e)
        }), 500


@app.route("/predict/batch", methods=["POST"])
def predict_batch():
    try:
        body = request.get_json(silent=True) or {}
        symbols = body.get("symbols", [])

        if not isinstance(symbols, list) or not symbols:
            return jsonify({
                "error": "symbols must be a non-empty list"
            }), 400

        results = []
        for raw_symbol in symbols[:20]:
            try:
                symbol = normalize_symbol(raw_symbol)
                snapshot = latest_snapshot(symbol)
                signal_data = score_market_signal(snapshot)

                results.append({
                    "symbol": symbol,
                    "prediction": signal_data["prediction"],
                    "confidence": signal_data["confidence"],
                    "signal": signal_data["signal"],
                    "price": snapshot["price"],
                    "change_24h": snapshot["change_24h"]
                })
            except Exception as inner_e:
                results.append({
                    "symbol": normalize_symbol(raw_symbol),
                    "error": str(inner_e)
                })

        return jsonify({
            "count": len(results),
            "results": results
        }), 200

    except Exception as e:
        return jsonify({
            "error": "Batch prediction failed",
            "message": str(e)
        }), 500


@app.errorhandler(404)
def not_found(_e):
    return jsonify({
        "error": "Not found",
        "message": "Endpoint does not exist"
    }), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({
        "error": "Internal server error",
        "message": str(e)
    }), 500


if __name__ == "__main__":
    print(f"Starting ML service on {FLASK_HOST}:{FLASK_PORT}")
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)