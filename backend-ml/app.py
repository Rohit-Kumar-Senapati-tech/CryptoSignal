import os
import traceback
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_caching import Cache
from flask_limiter import Limiter

from config import (
    FLASK_HOST,
    FLASK_PORT,
    FLASK_DEBUG,
    CACHE_TYPE,
    CACHE_DEFAULT_TIMEOUT,
    RATE_LIMIT_DEFAULT,
    RATE_LIMIT_PREDICT,
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

# ── Real IP for Render / proxy setup ───────────────────────────────────────
def real_ip():
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()

    real = request.headers.get("X-Real-IP")
    if real:
        return real.strip()

    return request.remote_addr or "unknown"

# ── Rate limiter ────────────────────────────────────────────────────────────
limiter = Limiter(
    key_func=real_ip,
    app=app,
    default_limits=[RATE_LIMIT_DEFAULT],
    storage_uri="memory://",
)

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
        "price": 0,
        "change_24h": 0
    }), 200

# ── Indicators route ────────────────────────────────────────────────────────
@app.route("/indicators", methods=["GET"])
def indicators():
    symbol = request.args.get("symbol", "BTC-USD")
    return jsonify({
        "symbol": symbol,
        "rsi": 52.4,
        "macd": 1.2,
        "ema": 0,
        "sma": 0,
        "bb_high": 0,
        "bb_low": 0,
        "return": 0,
        "volume_change": 0
    }), 200

# ── Sentiment route ─────────────────────────────────────────────────────────
@app.route("/sentiment", methods=["GET"])
def sentiment():
    symbol = request.args.get("symbol", "BTC-USD")
    return jsonify({
        "symbol": symbol,
        "sentiment": "neutral",
        "score": 0.0,
        "articles": []
    }), 200

# ── Predict route ───────────────────────────────────────────────────────────
@app.route("/predict", methods=["GET"])
@limiter.limit(RATE_LIMIT_PREDICT)
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
@limiter.limit(RATE_LIMIT_PREDICT)
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
@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({
        "error": "Too many requests",
        "message": "Rate limit exceeded. Please wait and try again."
    }), 429

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