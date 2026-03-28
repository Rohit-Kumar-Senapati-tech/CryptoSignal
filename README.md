# CryptoSignal (Teammate split)

## Teammate 1 (Mac) — MERN + Frontend

### 1) Node backend (`backend-node`)
```bash
cd CryptoSignal/backend-node
cp .env.example .env
npm install
npm run dev
```

### 2) React frontend (`frontend`)
```bash
cd CryptoSignal/frontend
npm install
cat > .env <<'EOT'
VITE_NODE_API=http://localhost:5000
EOT
npm run dev
```

## Teammate 2 (Windows) — Python ML service

### PowerShell steps
```powershell
cd CryptoSignal\backend-ml
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

## API contract
- Node proxy calls ML service:
  - `GET /api/proxy/signal/:symbol`
  - `GET /api/proxy/sentiment/:symbol`
- ML service endpoints:
  - `GET /predict/<symbol>`
  - `GET /sentiment/<symbol>`
