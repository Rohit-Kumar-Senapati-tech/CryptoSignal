#!/bin/bash
echo "Starting CryptoSignal ML Service..."

# Train model if it doesn't exist
if [ ! -f "models/crypto_model.pkl" ]; then
    echo "Model not found — training now (this takes 3-5 minutes)..."
    python models/train_model.py
fi

# Start Flask
echo "Starting Flask server..."
python app.py
```

---

Then update the **Start Command** on Render:

1. Go to Render → `cryptosignal-ml` → **Settings**
2. Find **Start Command**
3. Change from `python app.py` to:
```
bash start.sh