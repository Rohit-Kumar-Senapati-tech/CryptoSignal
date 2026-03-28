from flask import Flask, jsonify
from flask_cors import CORS
from config import Config
from utils.data_fetcher import fetch_ohlcv
from utils.feature_engineering import add_indicators
from utils.sentiment import sentiment_for_symbol
from models.train_model import train_classifier, FEATURES

app = Flask(__name__)
CORS(app)


@app.get('/health')
def health():
    return jsonify({'ok': True})


@app.get('/predict/<symbol>')
def predict(symbol: str):
    try:
        raw = fetch_ohlcv(symbol)
        fe = add_indicators(raw)
        model = train_classifier(fe)
        latest = fe.iloc[[-1]][FEATURES]
        pred = int(model.predict(latest)[0])

        signal = 'BUY' if pred == 1 else 'SELL'
        if 45 <= fe.iloc[-1]['RSI'] <= 55:
            signal = 'HOLD'

        return jsonify(
            {
                'symbol': symbol.upper(),
                'signal': signal,
                'close': float(fe.iloc[-1]['Close']),
                'rsi': float(fe.iloc[-1]['RSI']),
                'macd': float(fe.iloc[-1]['MACD'])
            }
        )
    except Exception as exc:
        return jsonify({'error': str(exc)}), 400


@app.get('/sentiment/<symbol>')
def sentiment(symbol: str):
    try:
        return jsonify(sentiment_for_symbol(symbol))
    except Exception as exc:
        return jsonify({'error': str(exc)}), 400


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=Config.PORT, debug=True)
