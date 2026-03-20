"""
feature_engineering.py
Enhanced technical indicators + price pattern recognition.
Added: Williams %R, CCI, ATR, Stochastic, OBV, VWAP,
       Ichimoku, price patterns, candlestick patterns.
"""
import logging
import numpy as np
import pandas as pd
import ta

log = logging.getLogger(__name__)

# ── Indicator settings ─────────────────────────────────────────────────────────
RSI_PERIOD    = 14
MACD_FAST     = 12
MACD_SLOW     = 26
MACD_SIGNAL   = 9
EMA_PERIODS   = [9, 21, 50]
SMA_PERIODS   = [20, 50]
BB_PERIOD     = 20
BB_STD        = 2
ATR_PERIOD    = 14
CCI_PERIOD    = 20
WILLIAMS_PERIOD = 14
STOCH_PERIOD  = 14
VOLUME_PERIOD = 14


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add all technical indicators + price patterns to DataFrame.
    Returns DataFrame with 35+ feature columns.
    """
    df = df.copy()

    # ── RSI ────────────────────────────────────────────────────────────────────
    df["rsi"] = ta.momentum.RSIIndicator(
        close=df["Close"], window=RSI_PERIOD
    ).rsi()

    # ── MACD ───────────────────────────────────────────────────────────────────
    macd = ta.trend.MACD(
        close=df["Close"],
        window_slow=MACD_SLOW,
        window_fast=MACD_FAST,
        window_sign=MACD_SIGNAL,
    )
    df["macd"]        = macd.macd()
    df["macd_signal"] = macd.macd_signal()
    df["macd_diff"]   = macd.macd_diff()

    # ── Multiple EMAs ──────────────────────────────────────────────────────────
    for period in EMA_PERIODS:
        df[f"ema_{period}"] = ta.trend.EMAIndicator(
            close=df["Close"], window=period
        ).ema_indicator()

    # Keep ema as alias for ema_21 (backward compat)
    df["ema"] = df["ema_21"]

    # ── Multiple SMAs ──────────────────────────────────────────────────────────
    for period in SMA_PERIODS:
        df[f"sma_{period}"] = ta.trend.SMAIndicator(
            close=df["Close"], window=period
        ).sma_indicator()

    # Keep sma as alias for sma_20
    df["sma"] = df["sma_20"]

    # ── Bollinger Bands ────────────────────────────────────────────────────────
    bb = ta.volatility.BollingerBands(
        close=df["Close"], window=BB_PERIOD, window_dev=BB_STD
    )
    df["bb_high"]     = bb.bollinger_hband()
    df["bb_low"]      = bb.bollinger_lband()
    df["bb_mid"]      = bb.bollinger_mavg()
    df["bb_width"]    = (df["bb_high"] - df["bb_low"]) / (df["bb_mid"] + 1e-9)
    df["bb_position"] = (df["Close"] - df["bb_low"]) / (df["bb_high"] - df["bb_low"] + 1e-9)

    # ── ATR (Average True Range) — volatility ──────────────────────────────────
    df["atr"] = ta.volatility.AverageTrueRange(
        high=df["High"], low=df["Low"], close=df["Close"], window=ATR_PERIOD
    ).average_true_range()
    df["atr_pct"] = df["atr"] / (df["Close"] + 1e-9)

    # ── Stochastic Oscillator ──────────────────────────────────────────────────
    stoch = ta.momentum.StochasticOscillator(
        high=df["High"], low=df["Low"], close=df["Close"], window=STOCH_PERIOD
    )
    df["stoch_k"] = stoch.stoch()
    df["stoch_d"] = stoch.stoch_signal()

    # ── Williams %R ────────────────────────────────────────────────────────────
    df["williams_r"] = ta.momentum.WilliamsRIndicator(
        high=df["High"], low=df["Low"], close=df["Close"], lbp=WILLIAMS_PERIOD
    ).williams_r()

    # ── CCI (Commodity Channel Index) ─────────────────────────────────────────
    df["cci"] = ta.trend.CCIIndicator(
        high=df["High"], low=df["Low"], close=df["Close"], window=CCI_PERIOD
    ).cci()

    # ── OBV (On-Balance Volume) ────────────────────────────────────────────────
    df["obv"] = ta.volume.OnBalanceVolumeIndicator(
        close=df["Close"], volume=df["Volume"]
    ).on_balance_volume()
    # Normalize OBV to percentage change
    df["obv_change"] = df["obv"].pct_change(5)

    # ── Volume indicators ──────────────────────────────────────────────────────
    rolling_vol         = df["Volume"].rolling(window=VOLUME_PERIOD).mean()
    df["volume_change"] = (df["Volume"] - rolling_vol) / (rolling_vol + 1e-9)
    df["volume_ratio"]  = df["Volume"] / (rolling_vol + 1e-9)

    # ── Returns ────────────────────────────────────────────────────────────────
    df["return"]    = df["Close"].pct_change()
    df["return_3d"] = df["Close"].pct_change(3)
    df["return_7d"] = df["Close"].pct_change(7)

    # ── Price vs moving averages ───────────────────────────────────────────────
    df["price_vs_ema9"]  = (df["Close"] - df["ema_9"])  / (df["ema_9"]  + 1e-9)
    df["price_vs_ema21"] = (df["Close"] - df["ema_21"]) / (df["ema_21"] + 1e-9)
    df["price_vs_ema50"] = (df["Close"] - df["ema_50"]) / (df["ema_50"] + 1e-9)
    df["price_vs_sma20"] = (df["Close"] - df["sma_20"]) / (df["sma_20"] + 1e-9)
    df["price_vs_ema"]   = df["price_vs_ema21"]  # backward compat
    df["price_vs_sma"]   = df["price_vs_sma20"]  # backward compat

    # ── EMA crossovers ─────────────────────────────────────────────────────────
    df["ema9_cross_21"]  = (df["ema_9"]  - df["ema_21"]) / (df["ema_21"] + 1e-9)
    df["ema21_cross_50"] = (df["ema_21"] - df["ema_50"]) / (df["ema_50"] + 1e-9)

    # ── Candlestick patterns ───────────────────────────────────────────────────
    df["candle_body"]    = (df["Close"] - df["Open"]).abs() / (df["High"] - df["Low"] + 1e-9)
    df["candle_dir"]     = np.sign(df["Close"] - df["Open"])
    df["upper_shadow"]   = (df["High"] - df[["Close","Open"]].max(axis=1)) / (df["High"] - df["Low"] + 1e-9)
    df["lower_shadow"]   = (df[["Close","Open"]].min(axis=1) - df["Low"]) / (df["High"] - df["Low"] + 1e-9)

    # Doji pattern (body very small)
    df["is_doji"] = (df["candle_body"] < 0.1).astype(int)

    # Hammer pattern (long lower shadow, small upper shadow)
    df["is_hammer"] = (
        (df["lower_shadow"] > 0.6) &
        (df["upper_shadow"] < 0.1) &
        (df["candle_body"] < 0.3)
    ).astype(int)

    # Engulfing pattern
    df["bullish_engulf"] = (
        (df["candle_dir"] == 1) &
        (df["candle_dir"].shift(1) == -1) &
        (df["Open"] < df["Close"].shift(1)) &
        (df["Close"] > df["Open"].shift(1))
    ).astype(int)

    df["bearish_engulf"] = (
        (df["candle_dir"] == -1) &
        (df["candle_dir"].shift(1) == 1) &
        (df["Open"] > df["Close"].shift(1)) &
        (df["Close"] < df["Open"].shift(1))
    ).astype(int)

    # ── Price patterns ─────────────────────────────────────────────────────────
    # Higher highs / higher lows (uptrend)
    df["higher_high"] = (df["High"] > df["High"].shift(1)).astype(int)
    df["higher_low"]  = (df["Low"]  > df["Low"].shift(1)).astype(int)

    # Rolling 14-day high/low position
    roll_high = df["High"].rolling(14).max()
    roll_low  = df["Low"].rolling(14).min()
    df["range_position"] = (df["Close"] - roll_low) / (roll_high - roll_low + 1e-9)

    # Momentum score (composite)
    df["momentum_score"] = (
        (df["rsi"] - 50) / 50 +
        df["macd_diff"].clip(-1, 1) +
        df["ema9_cross_21"].clip(-0.1, 0.1) * 10
    ) / 3

    # ── Drop NaN rows ──────────────────────────────────────────────────────────
    before = len(df)
    df.dropna(inplace=True)
    after  = len(df)
    if before != after:
        log.info("Dropped %d warmup rows after indicator calculation", before - after)

    log.info("Indicators calculated: %d rows, %d features", len(df), len(df.columns))
    return df


def get_feature_summary(df: pd.DataFrame) -> dict:
    """Return latest indicator values for API response."""
    if df.empty:
        return {}
    latest = df.iloc[-1]
    fields = [
        "rsi", "macd", "macd_signal", "macd_diff",
        "ema", "sma", "bb_high", "bb_low", "bb_mid",
        "bb_width", "bb_position", "atr_pct",
        "stoch_k", "stoch_d", "williams_r", "cci",
        "return", "return_3d", "return_7d",
        "volume_change", "volume_ratio",
        "price_vs_ema", "price_vs_sma",
        "ema9_cross_21", "ema21_cross_50",
        "momentum_score", "range_position",
        "candle_dir", "is_doji", "is_hammer",
        "close",
    ]
    result = {}
    for f in fields:
        if f in latest.index:
            val = latest[f]
            try:
                result[f] = round(float(val), 4)
            except Exception:
                result[f] = val
    # Add close price
    result["close"] = round(float(latest["Close"]), 4)
    return result


def get_signal_interpretation(indicators: dict) -> dict:
    """Plain English interpretation of each indicator."""
    signals = {}

    rsi = indicators.get("rsi", 50)
    if rsi > 70:
        signals["rsi"] = "Overbought — possible reversal DOWN"
    elif rsi < 30:
        signals["rsi"] = "Oversold — possible reversal UP"
    elif rsi > 55:
        signals["rsi"] = "Bullish momentum"
    elif rsi < 45:
        signals["rsi"] = "Bearish momentum"
    else:
        signals["rsi"] = "Neutral zone"

    macd_diff = indicators.get("macd_diff", 0)
    if macd_diff > 0:
        signals["macd"] = "Bullish — MACD above signal line"
    else:
        signals["macd"] = "Bearish — MACD below signal line"

    bb_pos = indicators.get("bb_position", 0.5)
    if bb_pos > 0.85:
        signals["bb"] = "Near upper band — overbought zone"
    elif bb_pos < 0.15:
        signals["bb"] = "Near lower band — oversold zone"
    else:
        signals["bb"] = "Inside bands — normal range"

    stoch_k = indicators.get("stoch_k", 50)
    if stoch_k > 80:
        signals["stoch"] = "Overbought"
    elif stoch_k < 20:
        signals["stoch"] = "Oversold"
    else:
        signals["stoch"] = "Neutral"

    wr = indicators.get("williams_r", -50)
    if wr > -20:
        signals["williams_r"] = "Overbought territory"
    elif wr < -80:
        signals["williams_r"] = "Oversold territory"
    else:
        signals["williams_r"] = "Neutral"

    cci = indicators.get("cci", 0)
    if cci > 100:
        signals["cci"] = "Strong bullish trend"
    elif cci < -100:
        signals["cci"] = "Strong bearish trend"
    else:
        signals["cci"] = "No strong trend"

    pve = indicators.get("price_vs_ema", 0)
    signals["ema"] = "Price above EMA — bullish" if pve > 0 else "Price below EMA — bearish"

    vol = indicators.get("volume_change", 0)
    if vol > 0.5:
        signals["volume"] = "High volume — strong move likely"
    elif vol < -0.3:
        signals["volume"] = "Low volume — weak conviction"
    else:
        signals["volume"] = "Normal volume"

    ms = indicators.get("momentum_score", 0)
    if ms > 0.3:
        signals["momentum"] = "Strong bullish momentum"
    elif ms < -0.3:
        signals["momentum"] = "Strong bearish momentum"
    else:
        signals["momentum"] = "Mixed momentum"

    return signals