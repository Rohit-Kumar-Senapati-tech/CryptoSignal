import numpy as np
import pandas as pd


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out['EMA_12'] = out['Close'].ewm(span=12, adjust=False).mean()
    out['EMA_26'] = out['Close'].ewm(span=26, adjust=False).mean()
    out['MACD'] = out['EMA_12'] - out['EMA_26']

    delta = out['Close'].diff()
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    avg_gain = pd.Series(gain, index=out.index).rolling(14).mean()
    avg_loss = pd.Series(loss, index=out.index).rolling(14).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out['RSI'] = 100 - (100 / (1 + rs))

    sma = out['Close'].rolling(20).mean()
    std = out['Close'].rolling(20).std()
    out['BB_UPPER'] = sma + 2 * std
    out['BB_LOWER'] = sma - 2 * std

    out['RET_1D'] = out['Close'].pct_change()
    out['TARGET'] = (out['Close'].shift(-1) > out['Close']).astype(int)
    return out.dropna()
