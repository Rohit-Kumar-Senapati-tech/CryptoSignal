import yfinance as yf
import pandas as pd


def fetch_ohlcv(symbol: str, period: str = '3mo', interval: str = '1d') -> pd.DataFrame:
    ticker = yf.Ticker(f'{symbol}-USD')
    df = ticker.history(period=period, interval=interval)
    if df.empty:
        raise ValueError(f'No market data for {symbol}')
    return df[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
