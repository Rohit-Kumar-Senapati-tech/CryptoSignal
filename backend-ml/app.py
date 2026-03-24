from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_caching import Cache
import requests
import pandas as pd
import ta
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

BINANCE_EXCHANGE_INFO_URL = "https://api.binance.com/api/v3/exchangeInfo"
BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"


def normalize_symbol(symbol: str) -> str:
    symbol = (symbol or "BTC-USD").upper().strip()
    if "-" not in symbol:
        return f"{symbol}-USD"
    return symbol


def base_asset(symbol: str) -> str:
    return normalize_symbol(symbol).split("-")[0]


def binance_pair(symbol: str) -> str:
    return f"{base_asset(symbol)}USDT"


def safe_float(value, default=0.0):
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def get_news_query(symbol: str) -> str:
    coin = base_asset(symbol)
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


@cache.cached(timeout=COINS_CACHE_TIMEOUT, key_prefix="binance_coins_v2")
def fetch_binance_coins():
    resp = requests.get(BINANCE_EXCHANGE_INFO_URL, timeout=15)
    resp.raise_for_status()
    data = resp.json()

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


@cache.memoize(timeout=60)
def fetch_klines(symbol: str, interval: str = "1h", limit: int = 200):
    pair = binance_pair(symbol)
    params = {
        "symbol": pair,
        "interval": interval,
        "limit": limit,
    }

    resp = requests.get(BINANCE_KLINES_URL, params=params, timeout=15)

    if resp.status_code == 429:
        raise ValueError("Binance rate limit hit. Please retry shortly.")

    resp.raise_for_status()
    raw = resp.json()

    if not raw:
        raise ValueError(f"No kline data found for {pair}")

    rows = []
    for k in raw:
        rows.append({
            "Date": pd.to_datetime(k[0], unit="ms", utc=True),
            "Open": float(k[1]),
            "High": float(k[2]),
            "Low": float(k[3]),
            "Close": float(k[4]),
            "Volume": float(k[5]),
        })

    df = pd.DataFrame(rows)
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


@cache.memoize(timeout=60)
def latest_snapshot(symbol: str):
    df = fetch_klines(symbol, interval="1h", limit=200)
    df = compute_indicators(df)

    latest = df.iloc[-1]
    prev_close = safe_float(df.iloc[-2]["Close"]) if len(df) > 1 else safe_float(latest["Close"])
    close_price = safe_float(latest["Close"])

    change_24h = ((close_price - prev_close) / prev_close * 100) if prev_close else 0.0

    return {
        "symbol": normalize_symbol(symbol),
        "price": round(close_price, 8),
        "change_24h": round(change_24h, 4),
        "rsi": round(safe_float(latest["rsi"]), 4),
        "macd": round(safe_float(latest["macd"]), 8),
        "ema": round(safe_float(latest["ema"]), 8),
        "sma": round(safe_float(latest["sma"]), 8),
        "bb_high": round(safe_float(latest["bb_high"]), 8),
        "bb_low": round(safe_float(latest["bb_low"]), 8),
        "return": round(safe_float(latest["return"]), 8),
        "volume_change": round(safe_float(latest["volume_change"]), 8),
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

    score = 0.0

    for article in articles:
        title = (article.get("title") or "").lower()
        description = (article.get("description") or "").lower()
        text = f"{title} {description}"

        pos_hits = sum(1 for word in positive_words if word in text)
        neg_hits = sum(1 for word in negative_words if word in text)
        score += (pos_hits - neg_hits)

    if not articles:
        return "neutral", 0.0

    normalized_score = round(score / len(articles), 2)

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

    # GNews is usually more reliable than NewsAPI on hosted apps
    url = "https://gnews.io/api/v4/search"
    params = {
        "q": query,
        "lang": "en",
        "max": 6,
        "apikey": NEWS_API_KEY
    }

    resp = requests.get(url, params=params, timeout=12)
    data = resp.json()

    if resp.status_code != 200:
        return {
            "symbol": symbol,
            "sentiment": "neutral",
            "score": 0.0,
            "articles": [],
            "message": data.get("errors") or data.get("message", "News request failed")
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
        "source": "Binance klines + ta + GNews",
        "message": "Prediction uses live crypto market data"
    }), 200


@app.route("/coins", methods=["GET"])
def coins():
    try:
        return jsonify(fetch_binance_coins()[:80]), 200
    except Exception as e:
        return jsonify({"error": "Failed to fetch coins", "message": str(e)}), 500


@app.route("/binance/coins", methods=["GET"])
def binance_coins():
    try:
        return jsonify(fetch_binance_coins()), 200
    except Exception as e:
        return jsonify({"error": "Failed to fetch Binance coins", "message": str(e)}), 500


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
        return jsonify({"error": "Failed to fetch price", "message": str(e)}), 500


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
        return jsonify({"error": "Failed to compute indicators", "message": str(e)}), 500


@app.route("/sentiment", methods=["GET"])
def sentiment():
    try:
        symbol = normalize_symbol(request.args.get("symbol", "BTC-USD"))
        return jsonify(fetch_news(symbol)), 200
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
            "message": "Prediction generated from live crypto market data"
        }), 200

    except Exception as e:
        return jsonify({"error": "Failed to generate prediction", "message": str(e)}), 500


@app.route("/predict/batch", methods=["POST"])
def predict_batch():
    try:
        body = request.get_json(silent=True) or {}
        symbols = body.get("symbols", [])

        if not isinstance(symbols, list) or not symbols:
            return jsonify({"error": "symbols must be a non-empty list"}), 400

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

        return jsonify({"count": len(results), "results": results}), 200

    except Exception as e:
        return jsonify({"error": "Batch prediction failed", "message": str(e)}), 500


@app.errorhandler(404)
def not_found(_e):
    return jsonify({"error": "Not found", "message": "Endpoint does not exist"}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error", "message": str(e)}), 500


if __name__ == "__main__":
    print(f"Starting ML service on {FLASK_HOST}:{FLASK_PORT}")
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)