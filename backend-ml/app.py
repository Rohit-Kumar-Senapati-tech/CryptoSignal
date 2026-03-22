"""
app.py - Flask ML service for CryptoSignal
Port: 5001 — loads features dynamically from features.json
"""
import json
import logging
import os
import sys

import joblib
import pandas as pd
import requests
from flask import Flask, jsonify, request
from flask_caching import Cache
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
UTILS_DIR = os.path.join(BASE_DIR, "utils")
sys.path.append(BASE_DIR)
sys.path.append(UTILS_DIR)

from config import (
    CACHE_DEFAULT_TIMEOUT, CACHE_TYPE, COINGECKO_API_KEY, COINGECKO_BASE,
    COINS_CACHE_TIMEOUT, CONFIDENCE_THRESHOLD, FEATURES, FLASK_DEBUG,
    FLASK_HOST, FLASK_PORT, META_PATH, MODEL_PATH, NEWS_API_KEY,
    NEWS_CACHE_TIMEOUT, RATE_LIMIT_DEFAULT, RATE_LIMIT_PREDICT,
)
from utils.data_fetcher import fetch_crypto_data, get_latest_price
from utils.feature_engineering import add_indicators, get_feature_summary, get_signal_interpretation
from utils.sentiment import get_sentiment_summary

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s — %(message)s")
log = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
app.config["CACHE_TYPE"]            = CACHE_TYPE
app.config["CACHE_DEFAULT_TIMEOUT"] = CACHE_DEFAULT_TIMEOUT
cache   = Cache(app)
limiter = Limiter(get_remote_address, app=app, default_limits=[RATE_LIMIT_DEFAULT], storage_uri="memory://")

# ── Load model ─────────────────────────────────────────────────────────────────
# ── Load or train model ────────────────────────────────────────────────────────
def load_or_train_model():
    if os.path.exists(MODEL_PATH):
        log.info("Loading existing model from %s", MODEL_PATH)
        return joblib.load(MODEL_PATH)
    log.warning("No model found — training now (takes 5-10 mins)...")
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    import subprocess
    result = subprocess.run(
        ["python", "models/train_model.py"],
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
        timeout=900,  # 15 min max
    )
    log.info(result.stdout[-2000:] if result.stdout else "")
    if result.returncode != 0:
        log.error("Training failed: %s", result.stderr[-1000:])
        return None
    if os.path.exists(MODEL_PATH):
        log.info("✅ Model trained and saved!")
        return joblib.load(MODEL_PATH)
    return None

model = load_or_train_model()
log.info("Model ready: %s", model is not None)
# ── Load feature list (dynamic — set by train_model.py) ───────────────────────
FEATURES_PATH = os.path.join(BASE_DIR, "models", "features.json")
try:
    with open(FEATURES_PATH) as f:
        MODEL_FEATURES = json.load(f)
    log.info("Loaded %d features from features.json", len(MODEL_FEATURES))
except FileNotFoundError:
    MODEL_FEATURES = FEATURES  # fallback to config.py defaults
    log.warning("features.json not found — using default features from config.py")


# ── Helpers ────────────────────────────────────────────────────────────────────
def model_required():
    if model is None:
        return jsonify({"error": "Model not loaded. Run: python models/train_model.py"}), 503
    return None

def parse_symbol(default="BTC-USD"):
    symbol = request.args.get("symbol", default).upper().strip()
    if "-" not in symbol:
        symbol = f"{symbol}-USD"
    return symbol

def build_feature_row(row: pd.Series) -> pd.DataFrame:
    """Build feature row using only features the model was trained on."""
    available = [f for f in MODEL_FEATURES if f in row.index]
    return pd.DataFrame([[row[f] for f in available]], columns=available)


# ── Routes ─────────────────────────────────────────────────────────────────────
@app.route("/")
def home():
    return jsonify({
        "service":      "CryptoSignal ML API",
        "status":       "running",
        "model_loaded": model is not None,
        "n_features":   len(MODEL_FEATURES),
    })

@app.route("/health")
def health():
    return jsonify({"status": "ok", "model_loaded": model is not None}), 200

@app.route("/model/info")
def model_info():
    if not os.path.exists(META_PATH):
        return jsonify({"error": "No metadata found. Train the model first."}), 404
    with open(META_PATH) as f:
        meta = json.load(f)
    return jsonify(meta)

@app.route("/predict")
@limiter.limit(RATE_LIMIT_PREDICT)
def predict():
    err = model_required()
    if err:
        return err
    symbol = parse_symbol()
    try:
        df         = fetch_crypto_data(symbol=symbol)
        df         = add_indicators(df)
        if df.empty:
            return jsonify({"error": f"No data for {symbol}"}), 422
        latest     = df.iloc[-1]
        X          = build_feature_row(latest)
        prediction = int(model.predict(X)[0])
        prob       = model.predict_proba(X)[0][prediction]
        confidence = round(float(prob) * 100, 2)
        base = {
            "coin":            symbol,
            "confidence":      confidence,
            "indicators":      get_feature_summary(df),
            "interpretations": get_signal_interpretation(get_feature_summary(df)),
        }
        if confidence < CONFIDENCE_THRESHOLD:
            return jsonify({**base, "signal": "NO TRADE", "reason": f"Confidence {confidence}% below threshold {CONFIDENCE_THRESHOLD}%"})
        base["signal"] = "UP" if prediction == 1 else "DOWN"
        return jsonify(base)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 422
    except Exception:
        log.exception("Error in /predict for %s", symbol)
        return jsonify({"error": "Internal server error"}), 500

@app.route("/predict/batch", methods=["POST"])
@limiter.limit("10 per minute")
def predict_batch():
    err = model_required()
    if err:
        return err
    data    = request.get_json(silent=True) or {}
    symbols = data.get("symbols", [])
    if not symbols or not isinstance(symbols, list):
        return jsonify({"error": "'symbols' must be a non-empty list"}), 400
    if len(symbols) > 15:
        return jsonify({"error": "Max 15 symbols per batch"}), 400
    results = []
    for symbol in symbols:
        symbol = symbol.upper().strip()
        if "-" not in symbol:
            symbol = f"{symbol}-USD"
        try:
            df         = fetch_crypto_data(symbol=symbol)
            df         = add_indicators(df)
            latest     = df.iloc[-1]
            X          = build_feature_row(latest)
            prediction = int(model.predict(X)[0])
            prob       = model.predict_proba(X)[0][prediction]
            confidence = round(float(prob) * 100, 2)
            signal     = ("UP" if prediction == 1 else "DOWN") if confidence >= CONFIDENCE_THRESHOLD else "NO TRADE"
            results.append({"coin": symbol, "signal": signal, "confidence": confidence, "rsi": round(float(latest.get("rsi", 0)), 2)})
        except Exception as exc:
            results.append({"coin": symbol, "error": str(exc)})
    return jsonify({"results": results})

@app.route("/indicators")
@cache.cached(timeout=CACHE_DEFAULT_TIMEOUT, query_string=True)
def indicators():
    symbol = parse_symbol()
    try:
        df      = fetch_crypto_data(symbol=symbol)
        df      = add_indicators(df)
        summary = get_feature_summary(df)
        return jsonify({"coin": symbol, "indicators": summary, "interpretations": get_signal_interpretation(summary)})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 422
    except Exception:
        log.exception("Error in /indicators for %s", symbol)
        return jsonify({"error": "Internal server error"}), 500

@app.route("/sentiment")
@cache.cached(timeout=NEWS_CACHE_TIMEOUT, query_string=True)
def sentiment():
    symbol = parse_symbol()
    try:
        return jsonify({"coin": symbol, **get_sentiment_summary(symbol=symbol, api_key=NEWS_API_KEY)})
    except Exception:
        log.exception("Error in /sentiment for %s", symbol)
        return jsonify({"error": "Internal server error"}), 500

@app.route("/price")
@cache.cached(timeout=60, query_string=True)
def price():
    symbol = parse_symbol()
    try:
        return jsonify(get_latest_price(symbol=symbol))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 422
    except Exception:
        log.exception("Error in /price for %s", symbol)
        return jsonify({"error": "Internal server error"}), 500

@app.route("/coins")
@cache.cached(timeout=COINS_CACHE_TIMEOUT)
def get_coins():
    headers = {"x-cg-pro-api-key": COINGECKO_API_KEY} if COINGECKO_API_KEY else {}
    try:
        resp = requests.get(f"{COINGECKO_BASE}/coins/list", headers=headers, timeout=10)
        resp.raise_for_status()
        coins = resp.json()
        formatted = [{"label": f"{c['name']} ({c['symbol'].upper()})", "value": f"{c['symbol'].upper()}-USD"} for c in coins if c.get("symbol") and c.get("name")]
        return jsonify({"count": len(formatted), "coins": formatted})
    except Exception:
        log.exception("Error fetching coins list")
        return jsonify({"error": "Failed to fetch coins list"}), 500

@app.route("/binance/coins")
@cache.cached(timeout=COINS_CACHE_TIMEOUT)
def get_binance_coins():
    try:
        resp = requests.get("https://api.binance.com/api/v3/exchangeInfo", timeout=15)
        resp.raise_for_status()
        coins = []
        for symbol in resp.json()["symbols"]:
            if symbol["quoteAsset"] == "USDT" and symbol["status"] == "TRADING":
                base = symbol["baseAsset"]
                coins.append({"label": f"{base} (USDT)", "value": f"{base}-USD", "symbol": base})
        coins.sort(key=lambda x: x["symbol"])
        log.info("Fetched %d Binance USDT pairs", len(coins))
        return jsonify({"count": len(coins), "coins": coins})
    except Exception:
        log.exception("Error fetching Binance coins")
        return jsonify({"error": "Failed to fetch Binance coins"}), 500

@app.errorhandler(404)
def not_found(_):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(429)
def rate_limited(_):
    return jsonify({"error": "Rate limit exceeded"}), 429

@app.errorhandler(500)
def internal_error(_):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    app.run(debug=FLASK_DEBUG, host=FLASK_HOST, port=FLASK_PORT)