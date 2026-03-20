"""
data_fetcher.py
Fetches live OHLCV crypto data from Yahoo Finance with
retries, validation, and simple in-memory caching.
"""
import logging
import time
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import yfinance as yf

log = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────
DEFAULT_PERIOD   = "2y"      # 2 years of daily data for training
DEFAULT_INTERVAL = "1d"      # daily candles
MIN_ROWS         = 60        # minimum rows needed to calculate indicators
MAX_RETRIES      = 3         # retry attempts on network failure
RETRY_DELAY      = 2         # seconds between retries

# ── Simple in-memory cache ─────────────────────────────────────────────────────
_cache: dict = {}
CACHE_TTL = 300  # seconds (5 minutes)


def _is_cache_valid(symbol: str) -> bool:
    """Check if cached data for symbol is still fresh."""
    if symbol not in _cache:
        return False
    cached_time = _cache[symbol]["timestamp"]
    return (datetime.utcnow() - cached_time).seconds < CACHE_TTL


def _get_cached(symbol: str) -> Optional[pd.DataFrame]:
    """Return cached DataFrame if valid, else None."""
    if _is_cache_valid(symbol):
        log.info("Cache hit for %s", symbol)
        return _cache[symbol]["data"].copy()
    return None


def _set_cache(symbol: str, df: pd.DataFrame) -> None:
    """Store DataFrame in cache with current timestamp."""
    _cache[symbol] = {
        "data": df.copy(),
        "timestamp": datetime.utcnow()
    }


# ── Main fetch function ────────────────────────────────────────────────────────
def fetch_crypto_data(
    symbol: str = "BTC-USD",
    period: str = DEFAULT_PERIOD,
    interval: str = DEFAULT_INTERVAL,
) -> pd.DataFrame:
    """
    Fetch OHLCV data for a crypto symbol from Yahoo Finance.

    Args:
        symbol:   Yahoo Finance ticker e.g. 'BTC-USD', 'ETH-USD', 'SOL-USD'
        period:   How much history to pull e.g. '1y', '2y', '6mo'
        interval: Candle size e.g. '1d', '1h'

    Returns:
        Cleaned DataFrame with columns: Open, High, Low, Close, Volume

    Raises:
        ValueError: if symbol is invalid or not enough data returned
    """
    symbol = symbol.upper().strip()

    # ── Check cache first ──────────────────────────────────────────────────────
    cached = _get_cached(symbol)
    if cached is not None:
        return cached

    # ── Fetch with retries ─────────────────────────────────────────────────────
    df = None
    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            log.info("Fetching %s (attempt %d/%d)…", symbol, attempt, MAX_RETRIES)
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)

            if df is not None and not df.empty:
                break  # success

            log.warning("Empty response for %s on attempt %d", symbol, attempt)

        except Exception as exc:
            last_error = exc
            log.warning("Attempt %d failed for %s: %s", attempt, symbol, exc)

        if attempt < MAX_RETRIES:
            time.sleep(RETRY_DELAY)

    # ── Validate result ────────────────────────────────────────────────────────
    if df is None or df.empty:
        raise ValueError(
            f"No data returned for '{symbol}'. "
            f"Check the symbol is valid (e.g. BTC-USD, ETH-USD, SOL-USD). "
            f"Last error: {last_error}"
        )

    if len(df) < MIN_ROWS:
        raise ValueError(
            f"Not enough data for '{symbol}': got {len(df)} rows, "
            f"need at least {MIN_ROWS}."
        )

    # ── Clean up ───────────────────────────────────────────────────────────────
    df = _clean_dataframe(df)

    # ── Cache and return ───────────────────────────────────────────────────────
    _set_cache(symbol, df)
    log.info("Fetched %d rows for %s", len(df), symbol)
    return df


def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and standardise the raw yfinance DataFrame.
    - Keep only OHLCV columns
    - Drop rows with any NaN
    - Remove timezone from index
    - Sort by date ascending
    """
    # Keep only needed columns
    keep = ["Open", "High", "Low", "Close", "Volume"]
    df = df[[c for c in keep if c in df.columns]].copy()

    # Drop NaN rows
    df.dropna(inplace=True)

    # Remove timezone info from index (makes sklearn happy)
    if hasattr(df.index, "tz") and df.index.tz is not None:
        df.index = df.index.tz_localize(None)

    # Sort ascending (oldest → newest)
    df.sort_index(inplace=True)

    return df


# ── Utility: get latest price only ────────────────────────────────────────────
def get_latest_price(symbol: str = "BTC-USD") -> dict:
    """
    Return the latest closing price and volume for a symbol.

    Returns:
        dict with keys: symbol, price, volume, date
    """
    df = fetch_crypto_data(symbol=symbol, period="5d")
    latest = df.iloc[-1]
    return {
        "symbol": symbol,
        "price":  round(float(latest["Close"]), 4),
        "volume": int(latest["Volume"]),
        "date":   str(df.index[-1].date()),
    }


# ── Utility: validate symbol ───────────────────────────────────────────────────
def is_valid_symbol(symbol: str) -> bool:
    """
    Quick check whether a symbol returns valid data.
    Used by the API to validate user input before heavy processing.
    """
    try:
        df = fetch_crypto_data(symbol=symbol, period="5d")
        return df is not None and not df.empty
    except ValueError:
        return False