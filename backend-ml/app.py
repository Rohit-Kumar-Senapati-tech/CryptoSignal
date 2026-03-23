from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_caching import Cache
import requests

from config import (
    FLASK_HOST,
    FLASK_PORT,
    FLASK_DEBUG,
    CACHE_TYPE,
    CACHE_DEFAULT_TIMEOUT,
    NEWS_API_KEY,
)

app = Flask(__name__)

# ── Basic config ────────────────────────────────────────────────────────────
app.config["JSON_SORT_KEYS"] = False
app.config["CACHE_TYPE"] = CACHE_TYPE
app.config["CACHE_DEFAULT_TIMEOUT"] = CACHE_DEFAULT_TIMEOUT

# ── CORS ────────────────────────────────────────────────────────────────────
CORS(app, resources={r"/*": {"origins": "*"}})

# ── Cache ───────────────────────────────────────────────────────────────────
cache = Cache(app)

# ── Helper: map symbol to search keywords ───────────────────────────────────
def get_news_query(symbol: str) -> str:
    coin = symbol.split("-")[0].upper()

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
    }

    return keyword_map.get(coin, f"{coin} crypto")


# ── Helper: simple sentiment scoring ────────────────────────────────────────
def analyze_articles_sentiment(articles):
    positive_words = [
        "surge", "rise", "bullish", "gain", "growth", "up",
        "breakout", "strong", "rally", "record", "adoption",
        "approval", "profit", "positive", "boom"
    ]

    negative_words = [
        "drop", "fall", "bearish", "loss", "down",
        "crash", "weak", "decline", "ban", "hack",
        "lawsuit", "selloff", "negative", "collapse", "risk"
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
    elif normalized_score < -0.3:
        return "negative", normalized_score
    else:
        return "neutral", normalized_score


# ── Health route ────────────────────────────────────────────────────────────
@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "service": "backend-ml",
        "message": "ML service is running"
    }), 200


# ── Model info route ────────────────────────────────────────────────────────
@app.route("/model/info", methods=["GET"])
def model_info():
    return jsonify({
        "status": "ok",
        "model": "crypto_model",
        "message": "Model info endpoint working"
    }), 200


# ── Coins route ─────────────────────────────────────────────────────────────
@app.route("/coins", methods=["GET"])
def coins():
    return jsonify([
        {"symbol": "BTC", "name": "Bitcoin", "pair": "BTC-USD"},
        {"symbol": "ETH", "name": "Ethereum", "pair": "ETH-USD"},
        {"symbol": "SOL", "name": "Solana", "pair": "SOL-USD"},
        {"symbol": "BNB", "name": "BNB", "pair": "BNB-USD"},
        {"symbol": "XRP", "name": "XRP", "pair": "XRP-USD"},
        {"symbol": "DOGE", "name": "Dogecoin", "pair": "DOGE-USD"},
        {"symbol": "ADA", "name": "Cardano", "pair": "ADA-USD"},
        {"symbol": "AVAX", "name": "Avalanche", "pair": "AVAX-USD"},
        {"symbol": "LINK", "name": "Chainlink", "pair": "LINK-USD"},
        {"symbol": "MATIC", "name": "Polygon", "pair": "MATIC-USD"},
        {"symbol": "LTC", "name": "Litecoin", "pair": "LTC-USD"},
        {"symbol": "DOT", "name": "Polkadot", "pair": "DOT-USD"}
    ]), 200


# ── Binance coins route ─────────────────────────────────────────────────────
@app.route("/binance/coins", methods=["GET"])
def binance_coins():
    return jsonify([
        {"symbol": "BTC", "name": "Bitcoin", "pair": "BTC-USD"},
        {"symbol": "ETH", "name": "Ethereum", "pair": "ETH-USD"},
        {"symbol": "SOL", "name": "Solana", "pair": "SOL-USD"},
        {"symbol": "BNB", "name": "BNB", "pair": "BNB-USD"},
        {"symbol": "XRP", "name": "XRP", "pair": "XRP-USD"},
        {"symbol": "DOGE", "name": "Dogecoin", "pair": "DOGE-USD"},
        {"symbol": "ADA", "name": "Cardano", "pair": "ADA-USD"},
        {"symbol": "AVAX", "name": "Avalanche", "pair": "AVAX-USD"},
        {"symbol": "LINK", "name": "Chainlink", "pair": "LINK-USD"},
        {"symbol": "MATIC", "name": "Polygon", "pair": "MATIC-USD"},
        {"symbol": "LTC", "name": "Litecoin", "pair": "LTC-USD"},
        {"symbol": "DOT", "name": "Polkadot", "pair": "DOT-USD"}
    ]), 200


# ── Price route ─────────────────────────────────────────────────────────────
@app.route("/price", methods=["GET"])
def price():
    symbol = request.args.get("symbol", "BTC-USD")
    return jsonify({
        "symbol": symbol,
        "price": 68500.25,
        "change_24h": 1.45
    }), 200


# ── Indicators route ────────────────────────────────────────────────────────
@app.route("/indicators", methods=["GET"])
def indicators():
    symbol = request.args.get("symbol", "BTC-USD")
    return jsonify({
        "symbol": symbol,
        "rsi": 52.4,
        "macd": 1.2,
        "ema": 68000.0,
        "sma": 67850.0,
        "bb_high": 69200.0,
        "bb_low": 67100.0,
        "return": 0.018,
        "volume_change": 0.11
    }), 200


# ── Sentiment route ─────────────────────────────────────────────────────────
@app.route("/sentiment", methods=["GET"])
def sentiment():
    symbol = request.args.get("symbol", "BTC-USD")
    query = get_news_query(symbol)

    if not NEWS_API_KEY:
        return jsonify({
            "symbol": symbol,
            "sentiment": "neutral",
            "score": 0.0,
            "articles": [],
            "message": "NEWS_API_KEY is missing"
        }), 200

    try:
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": query,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 5,
            "apiKey": NEWS_API_KEY
        }

        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if response.status_code != 200:
            return jsonify({
                "symbol": symbol,
                "sentiment": "neutral",
                "score": 0.0,
                "articles": [],
                "message": data.get("message", "News API request failed")
            }), 200

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

        return jsonify({
            "symbol": symbol,
            "sentiment": sentiment_label,
            "score": sentiment_score,
            "articles": articles
        }), 200

    except Exception as e:
        return jsonify({
            "symbol": symbol,
            "sentiment": "neutral",
            "score": 0.0,
            "articles": [],
            "message": str(e)
        }), 200


# ── Predict route ───────────────────────────────────────────────────────────
@app.route("/predict", methods=["GET"])
def predict():
    symbol = request.args.get("symbol", "BTC-USD")
    return jsonify({
        "symbol": symbol,
        "prediction": "Bullish",
        "confidence": 72.5,
        "signal": "BUY",
        "message": "Prediction generated successfully"
    }), 200


# ── Batch predict route ─────────────────────────────────────────────────────
@app.route("/predict/batch", methods=["POST"])
def predict_batch():
    body = request.get_json(silent=True) or {}
    symbols = body.get("symbols", [])

    results = []
    for symbol in symbols:
        results.append({
            "symbol": symbol,
            "prediction": "Bullish",
            "confidence": 72.5,
            "signal": "BUY"
        })

    return jsonify({
        "count": len(results),
        "results": results
    }), 200


# ── Error handlers ──────────────────────────────────────────────────────────
@app.errorhandler(404)
def not_found(e):
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


# ── Main ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"Starting ML service on {FLASK_HOST}:{FLASK_PORT}")
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)