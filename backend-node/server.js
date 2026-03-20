/**
 * server.js
 * Main Express server for CryptoSignal.
 * Handles auth, portfolio, real-time prices via Socket.io,
 * and proxies ML predictions from the Python Flask service.
 *
 * Port: 5000
 * ML Service: http://localhost:5001
 */

const express    = require("express");
const mongoose   = require("mongoose");
const cors       = require("cors");
const dotenv     = require("dotenv");
const http       = require("http");
const { Server } = require("socket.io");
const axios      = require("axios");

// ── Load environment variables ─────────────────────────────────────────────
dotenv.config();

// ── Route imports ──────────────────────────────────────────────────────────
const authRoutes      = require("./routes/auth");
const portfolioRoutes = require("./routes/portfolio");
const proxyRoutes     = require("./routes/proxy");

// ── App + HTTP server setup ────────────────────────────────────────────────
const app    = express();
const server = http.createServer(app);

// ── Socket.io setup ────────────────────────────────────────────────────────
const io = new Server(server, {
  cors: {
    origin:  process.env.FRONTEND_URL || "http://localhost:5173",
    methods: ["GET", "POST"],
  },
});

// ── Middleware ─────────────────────────────────────────────────────────────
app.use(cors({
  origin: process.env.FRONTEND_URL || "http://localhost:5173",
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
app.use("/api/auth",      authRoutes);
app.use("/api/portfolio", portfolioRoutes);
app.use("/api/ml",        proxyRoutes);

// ── Health check ───────────────────────────────────────────────────────────
app.get("/", (_req, res) => {
  res.json({
    service:  "CryptoSignal Node API",
    status:   "running",
    port:     process.env.PORT || 5000,
    endpoints: [
      "/api/auth/register",
      "/api/auth/login",
      "/api/auth/me",
      "/api/portfolio",
      "/api/ml/predict",
      "/api/ml/indicators",
      "/api/ml/sentiment",
      "/api/ml/coins",
      "/api/ml/price",
    ],
  });
});

app.get("/health", (_req, res) => {
  res.json({ status: "ok", db: mongoose.connection.readyState === 1 });
});

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

// ── MongoDB connection ─────────────────────────────────────────────────────
const MONGO_URI = process.env.MONGO_URI || "mongodb://localhost:27017/cryptosignal";

mongoose
  .connect(MONGO_URI)
  .then(() => console.log("✅  MongoDB connected"))
  .catch((err) => {
    console.error("❌  MongoDB connection failed:", err.message);
    process.exit(1);
  });

// ══════════════════════════════════════════════════════════════════════════
// Socket.io — Real-time price feed
// Fetches prices from ML service every 30 seconds and
// broadcasts to all connected frontend clients
// ══════════════════════════════════════════════════════════════════════════
const ML_BASE = process.env.ML_SERVICE_URL || "http://localhost:5001";

// Track which symbols clients are watching
const watchedSymbols = new Set(["BTC-USD", "ETH-USD", "SOL-USD"]);

io.on("connection", (socket) => {
  console.log(`[Socket] Client connected: ${socket.id}`);

  // Client can subscribe to a specific coin
  socket.on("subscribe", (symbol) => {
    const sym = symbol.toUpperCase();
    watchedSymbols.add(sym);
    console.log(`[Socket] ${socket.id} subscribed to ${sym}`);
    socket.join(sym);
  });

  // Client can unsubscribe
  socket.on("unsubscribe", (symbol) => {
    const sym = symbol.toUpperCase();
    socket.leave(sym);
    console.log(`[Socket] ${socket.id} unsubscribed from ${sym}`);
  });

  socket.on("disconnect", () => {
    console.log(`[Socket] Client disconnected: ${socket.id}`);
  });
});

// Broadcast prices to all clients every 30 seconds
const PRICE_INTERVAL_MS = 30_000;

async function broadcastPrices() {
  for (const symbol of watchedSymbols) {
    try {
      const { data } = await axios.get(`${ML_BASE}/price`, {
        params:  { symbol },
        timeout: 8000,
      });
      io.to(symbol).emit("price_update", data);
    } catch (err) {
      console.warn(`[Socket] Price fetch failed for ${symbol}:`, err.message);
    }
  }
}

// Start broadcasting after 5s delay (let ML service warm up)
setTimeout(() => {
  broadcastPrices();
  setInterval(broadcastPrices, PRICE_INTERVAL_MS);
}, 5000);

// ── Start server ───────────────────────────────────────────────────────────
const PORT = process.env.PORT || 5000;

server.listen(PORT, () => {
  console.log(`\n🚀  CryptoSignal Node server running on port ${PORT}`);
  console.log(`📡  ML service expected at ${ML_BASE}`);
  console.log(`🌐  Frontend expected at ${process.env.FRONTEND_URL || "http://localhost:5173"}\n`);
});