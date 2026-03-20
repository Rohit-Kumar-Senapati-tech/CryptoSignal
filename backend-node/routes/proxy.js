/**
 * routes/proxy.js
 * Forwards all ML requests from the frontend to the
 * Python Flask service running on port 5001.
 *
 * GET /api/ml/predict?symbol=BTC-USD
 * GET /api/ml/indicators?symbol=BTC-USD
 * GET /api/ml/sentiment?symbol=BTC-USD
 * GET /api/ml/price?symbol=BTC-USD
 * GET /api/ml/coins
 * GET /api/ml/health
 * GET /api/ml/model/info
 * POST /api/ml/predict/batch
 */

const router = require("express").Router();
const axios  = require("axios");

const ML_BASE = process.env.ML_SERVICE_URL || "http://localhost:5001";

// ── Helper: forward GET request to ML service ──────────────────────────────
const forwardGet = (mlPath) => async (req, res) => {
  try {
    const { data } = await axios.get(`${ML_BASE}${mlPath}`, {
      params:  req.query,
      timeout: 15000,
    });
    res.json(data);
  } catch (err) {
    if (err.code === "ECONNREFUSED") {
      return res.status(503).json({
        error: "ML service is not running. Start it with: python app.py",
      });
    }
    if (err.response) {
      return res.status(err.response.status).json(err.response.data);
    }
    res.status(500).json({ error: "ML service error: " + err.message });
  }
};

// ── Helper: forward POST request to ML service ─────────────────────────────
const forwardPost = (mlPath) => async (req, res) => {
  try {
    const { data } = await axios.post(`${ML_BASE}${mlPath}`, req.body, {
      timeout: 30000,
    });
    res.json(data);
  } catch (err) {
    if (err.code === "ECONNREFUSED") {
      return res.status(503).json({
        error: "ML service is not running. Start it with: python app.py",
      });
    }
    if (err.response) {
      return res.status(err.response.status).json(err.response.data);
    }
    res.status(500).json({ error: "ML service error: " + err.message });
  }
};


// ── Routes ─────────────────────────────────────────────────────────────────
router.get("/health",        forwardGet("/health"));
router.get("/model/info",    forwardGet("/model/info"));
router.get("/predict",       forwardGet("/predict"));
router.get("/indicators",    forwardGet("/indicators"));
router.get("/sentiment",     forwardGet("/sentiment"));
router.get("/price",         forwardGet("/price"));
router.get("/coins",         forwardGet("/coins"));
router.post("/predict/batch", forwardPost("/predict/batch"));


module.exports = router;