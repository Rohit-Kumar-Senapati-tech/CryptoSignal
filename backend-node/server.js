/**
 * server.js
 * Main Express server for CryptoSignal.
 * Handles auth, portfolio, real-time prices via Socket.io,
 * and proxies ML predictions from the Python Flask service.
 */

const express = require("express");
const mongoose = require("mongoose");
const cors = require("cors");
const dotenv = require("dotenv");
const http = require("http");
const { Server } = require("socket.io");
const axios = require("axios");

// ── Load environment variables ─────────────────────────────────────────────
dotenv.config();

// ── Route imports ──────────────────────────────────────────────────────────
const authRoutes = require("./routes/auth");
const portfolioRoutes = require("./routes/portfolio");
const proxyRoutes = require("./routes/proxy");

// ── App + HTTP server setup ────────────────────────────────────────────────
const app = express();
const server = http.createServer(app);

// ── Environment values ─────────────────────────────────────────────────────
const PORT = process.env.PORT || 5000;
const ML_BASE = process.env.ML_SERVICE_URL || "http://localhost:5001";

const allowedOrigins = [
  "http://localhost:5173",
  "https://cryptosignal-frontend-phi.vercel.app",
  process.env.FRONTEND_URL,
].filter(Boolean);

// ── Socket.io setup ────────────────────────────────────────────────────────
const io = new Server(server, {
  cors: {
    origin: allowedOrigins,
    methods: ["GET", "POST"],
    credentials: true,
  },
});

// ── Middleware ─────────────────────────────────────────────────────────────
app.use(cors({
  origin: allowedOrigins,
  credentials: true,
}));

app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// ── Request logger (dev only) ──────────────────────────────────────────────
if (process.env.NODE_ENV !== "production") {
  app.use((req, _res, next) => {
    console.log(`[${new Date().toISOString()}] ${req.method} ${req.url}`);
    next();
  });
}

// ── Routes ─────────────────────────────────────────────────────────────────
app.use("/api/auth", authRoutes);
app.use("/api/portfolio", portfolioRoutes);
app.use("/api/ml", proxyRoutes);

// ── Health check ───────────────────────────────────────────────────────────
app.get("/", (_req, res) => {
  res.json({
    service: "CryptoSignal Node API",
    status: "running",
    port: PORT,
    mlService: ML_BASE,
    endpoints: [
      "/api/auth/register",
      "/api/auth/login",
      "/api/auth/me",
      "/api/portfolio",
      "/api/ml/predict",
      "/api/ml/indicators",
      "/api/ml/sentiment",
      "/api/ml/coins",
      "/api/ml/binance/coins",
      "/api/ml/price",
    ],
  });
});

app.get("/health", (_req, res) => {
  res.json({
    status: "ok",
    db: mongoose.connection.readyState === 1,
    port: PORT,
  });
});

// ── MongoDB connection ─────────────────────────────────────────────────────
const MONGO_URI = process.env.MONGO_URI || "mongodb://localhost:27017/cryptosignal";

mongoose
  .connect(MONGO_URI)
  .then(() => console.log("✅ MongoDB connected"))
  .catch((err) => {
    console.error("❌ MongoDB connection failed:", err.message);
    process.exit(1);
  });

// ══════════════════════════════════════════════════════════════════════════
// Socket.io — Real-time price feed
// Reduced polling to avoid rate-limit issues
// ══════════════════════════════════════════════════════════════════════════

// Track which symbols clients are watching
const watchedSymbols = new Set(["BTC-USD"]);

// Keep track of how many sockets are subscribed to each symbol
const subscriptionCounts = new Map();

// Cache latest prices briefly to avoid repeated upstream hits
const latestPriceCache = new Map();
const PRICE_CACHE_TTL_MS = 45_000;

// Broadcast prices less aggressively
const PRICE_INTERVAL_MS = 60_000;

// Small delay between upstream requests to prevent burst traffic
const REQUEST_SPACING_MS = 1200;

function normalizeSymbol(symbol) {
  return String(symbol || "BTC-USD").trim().toUpperCase();
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function getCachedPrice(symbol) {
  const entry = latestPriceCache.get(symbol);
  if (!entry) return null;

  const isExpired = Date.now() - entry.timestamp > PRICE_CACHE_TTL_MS;
  if (isExpired) {
    latestPriceCache.delete(symbol);
    return null;
  }

  return entry.data;
}

function setCachedPrice(symbol, data) {
  latestPriceCache.set(symbol, {
    data,
    timestamp: Date.now(),
  });
}

async function fetchPrice(symbol) {
  const cached = getCachedPrice(symbol);
  if (cached) return cached;

  const { data } = await axios.get(`${ML_BASE}/price`, {
    params: { symbol },
    timeout: 8000,
  });

  setCachedPrice(symbol, data);
  return data;
}

function incrementSubscription(symbol) {
  const current = subscriptionCounts.get(symbol) || 0;
  subscriptionCounts.set(symbol, current + 1);
  watchedSymbols.add(symbol);
}

function decrementSubscription(symbol) {
  const current = subscriptionCounts.get(symbol) || 0;

  if (current <= 1) {
    subscriptionCounts.delete(symbol);

    // Keep BTC-USD as default baseline symbol
    if (symbol !== "BTC-USD") {
      watchedSymbols.delete(symbol);
    }
  } else {
    subscriptionCounts.set(symbol, current - 1);
  }
}

io.on("connection", (socket) => {
  console.log(`[Socket] Client connected: ${socket.id}`);

  socket.on("subscribe", (symbol) => {
    const sym = normalizeSymbol(symbol);
    socket.join(sym);
    incrementSubscription(sym);
    console.log(`[Socket] ${socket.id} subscribed to ${sym}`);
  });

  socket.on("unsubscribe", (symbol) => {
    const sym = normalizeSymbol(symbol);
    socket.leave(sym);
    decrementSubscription(sym);
    console.log(`[Socket] ${socket.id} unsubscribed from ${sym}`);
  });

  socket.on("disconnect", () => {
    console.log(`[Socket] Client disconnected: ${socket.id}`);
  });
});

async function broadcastPrices() {
  for (const symbol of watchedSymbols) {
    try {
      const data = await fetchPrice(symbol);
      io.to(symbol).emit("price_update", data);

      // avoid burst requests against ML service / external APIs
      await sleep(REQUEST_SPACING_MS);
    } catch (err) {
      const status = err.response?.status;
      const message = err.response?.data?.message || err.message;

      console.warn(`[Socket] Price fetch failed for ${symbol}:`, status || "", message);

      // If upstream is rate-limited, stop hammering it in this cycle
      if (status === 429) {
        break;
      }
    }
  }
}

// Start broadcasting after warmup delay
setTimeout(() => {
  broadcastPrices();
  setInterval(broadcastPrices, PRICE_INTERVAL_MS);
}, 5000);

// ── 404 handler ────────────────────────────────────────────────────────────
app.use((_req, res) => {
  res.status(404).json({ error: "Route not found" });
});

// ── Global error handler ───────────────────────────────────────────────────
app.use((err, _req, res, _next) => {
  console.error("[ERROR]", err.message);
  res.status(err.status || 500).json({
    error: err.message || "Internal server error",
  });
});

// ── Start server ───────────────────────────────────────────────────────────
server.listen(PORT, () => {
  console.log(`\n🚀 CryptoSignal Node server running on port ${PORT}`);
  console.log(`📡 ML service expected at ${ML_BASE}`);
  console.log(`🌐 Allowed frontend origins: ${allowedOrigins.join(", ")}\n`);
});