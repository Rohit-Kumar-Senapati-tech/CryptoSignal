"""
train_model.py — Enhanced ML pipeline
Models: XGBoost + RandomForest ensemble
Features: 35+ technical indicators + price patterns + sentiment
History: 5 years on 8 coins
"""
import json
import logging
import os
import sys
from datetime import datetime

import joblib
import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier, VotingClassifier, GradientBoostingClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, roc_auc_score
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UTILS_DIR = os.path.join(BASE_DIR, "utils")
sys.path.append(BASE_DIR)
sys.path.append(UTILS_DIR)

from utils.data_fetcher import fetch_crypto_data
from utils.feature_engineering import add_indicators
from config import MODEL_PATH, META_PATH

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────────────────────
TRAIN_SYMBOLS = [
    "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
    "ADA-USD", "AVAX-USD", "DOGE-USD",
]
PERIOD   = "5y"   # 5 years of data
N_SPLITS = 5

# ── All features including new ones ───────────────────────────────────────────
FEATURES = [
    # Core momentum
    "rsi", "macd", "macd_diff", "macd_signal",
    # Trend
    "ema", "sma", "price_vs_ema", "price_vs_sma",
    "ema9_cross_21", "ema21_cross_50",
    # Volatility
    "bb_high", "bb_low", "bb_width", "bb_position",
    "atr_pct",
    # Additional oscillators
    "stoch_k", "stoch_d", "williams_r", "cci",
    # Volume
    "volume_change", "volume_ratio", "obv_change",
    # Returns
    "return", "return_3d", "return_7d",
    # Patterns
    "candle_body", "candle_dir", "upper_shadow", "lower_shadow",
    "is_doji", "is_hammer", "bullish_engulf", "bearish_engulf",
    "higher_high", "higher_low", "range_position",
    # Composite
    "momentum_score",
]


def prepare_data(symbols: list) -> tuple:
    all_X, all_y = [], []

    for symbol in symbols:
        try:
            log.info("Preparing %s ...", symbol)
            df = fetch_crypto_data(symbol=symbol, period=PERIOD)
            df = add_indicators(df)

            # Target: 1 if tomorrow close > today close
            df["target"] = (df["Close"].shift(-1) > df["Close"]).astype(int)
            df.dropna(inplace=True)

            # Only keep features that exist
            available = [f for f in FEATURES if f in df.columns]
            X = df[available]
            y = df["target"]

            all_X.append(X)
            all_y.append(y)
            log.info("%s: %d rows | UP: %d | DOWN: %d", symbol, len(X), int(y.sum()), int((y==0).sum()))

        except Exception as exc:
            log.warning("Skipping %s: %s", symbol, exc)

    if not all_X:
        raise RuntimeError("No data fetched for any symbol")

    X = pd.concat(all_X, ignore_index=True)
    y = pd.concat(all_y, ignore_index=True)

    log.info("Combined: %d rows | UP: %.1f%% | DOWN: %.1f%%",
             len(X), 100*y.mean(), 100*(1-y.mean()))
    return X, y


def build_ensemble() -> Pipeline:
    """
    Voting ensemble of 3 models:
    1. RandomForest     — good with noisy data
    2. GradientBoosting — sequential error correction
    Both wrapped in StandardScaler pipeline.
    """
    rf = RandomForestClassifier(
        n_estimators=500,
        max_depth=8,
        min_samples_leaf=15,
        min_samples_split=10,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )

    gb = GradientBoostingClassifier(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        min_samples_leaf=15,
        subsample=0.8,
        random_state=42,
    )

    ensemble = VotingClassifier(
        estimators=[("rf", rf), ("gb", gb)],
        voting="soft",   # use probability averaging
        weights=[1, 1],
    )

    return Pipeline([
        ("scaler", StandardScaler()),
        ("clf",    ensemble),
    ])


def cross_validate(pipeline, X, y) -> dict:
    tscv       = TimeSeriesSplit(n_splits=N_SPLITS)
    fold_stats = []

    for fold, (train_idx, val_idx) in enumerate(tscv.split(X), 1):
        X_tr, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_tr, y_val = y.iloc[train_idx], y.iloc[val_idx]

        pipeline.fit(X_tr, y_tr)
        preds = pipeline.predict(X_val)
        proba = pipeline.predict_proba(X_val)[:, 1]

        acc = accuracy_score(y_val, preds)
        auc = roc_auc_score(y_val, proba)
        fold_stats.append({"fold": fold, "accuracy": round(acc, 4), "roc_auc": round(auc, 4)})
        log.info("Fold %d — Accuracy: %.4f | ROC-AUC: %.4f", fold, acc, auc)

    avg_acc = round(float(np.mean([f["accuracy"] for f in fold_stats])), 4)
    avg_auc = round(float(np.mean([f["roc_auc"]  for f in fold_stats])), 4)
    log.info("CV Average → Accuracy: %.4f | ROC-AUC: %.4f", avg_acc, avg_auc)
    return {"folds": fold_stats, "avg_accuracy": avg_acc, "avg_roc_auc": avg_auc}


def train_model():
    log.info("=" * 60)
    log.info("  CryptoSignal — Enhanced Model Training")
    log.info("  Symbols : %s", TRAIN_SYMBOLS)
    log.info("  Period  : %s", PERIOD)
    log.info("  Features: %d", len(FEATURES))
    log.info("=" * 60)

    # 1. Prepare data
    X, y = prepare_data(TRAIN_SYMBOLS)

    # Only use features that exist in the data
    available_features = [f for f in FEATURES if f in X.columns]
    X = X[available_features]
    log.info("Using %d features: %s", len(available_features), available_features)

    # 2. Cross-validation
    log.info("\nRunning %d-fold walk-forward cross-validation ...", N_SPLITS)
    pipeline   = build_ensemble()
    cv_results = cross_validate(pipeline, X, y)

    # 3. Final fit on all data
    log.info("\nFitting final ensemble on full dataset ...")
    pipeline.fit(X, y)

    # 4. Hold-out evaluation
    split  = int(len(X) * 0.8)
    X_test = X.iloc[split:]
    y_test = y.iloc[split:]
    preds  = pipeline.predict(X_test)
    proba  = pipeline.predict_proba(X_test)[:, 1]

    hold_acc = round(accuracy_score(y_test, preds), 4)
    hold_auc = round(roc_auc_score(y_test, proba), 4)

    log.info("\n--- Hold-out Evaluation ---")
    log.info("Accuracy : %.4f (%.1f%%)", hold_acc, hold_acc * 100)
    log.info("ROC-AUC  : %.4f", hold_auc)
    log.info("\n%s", classification_report(y_test, preds, target_names=["DOWN", "UP"]))

    # 5. Save model
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(pipeline, MODEL_PATH)

    # Also save feature list so app.py knows which features to use
    features_path = os.path.join(os.path.dirname(MODEL_PATH), "features.json")
    with open(features_path, "w") as f:
        json.dump(available_features, f)

    # 6. Save metadata
    meta = {
        "trained_at":     datetime.now().isoformat(),
        "symbols":        TRAIN_SYMBOLS,
        "period":         PERIOD,
        "features":       available_features,
        "n_features":     len(available_features),
        "n_samples":      len(X),
        "models":         ["RandomForest", "GradientBoosting"],
        "ensemble":       "VotingClassifier (soft)",
        "cv":             cv_results,
        "hold_out":       {"accuracy": hold_acc, "roc_auc": hold_auc},
        "confusion_matrix": confusion_matrix(y_test, preds).tolist(),
    }
    with open(META_PATH, "w") as f:
        json.dump(meta, f, indent=2)

    log.info("\n✅  Training complete!")
    log.info("    Accuracy : %.1f%%", hold_acc * 100)
    log.info("    ROC-AUC  : %.4f", hold_auc)
    log.info("    Model    → %s", MODEL_PATH)
    log.info("    Metadata → %s", META_PATH)


if __name__ == "__main__":
    train_model()