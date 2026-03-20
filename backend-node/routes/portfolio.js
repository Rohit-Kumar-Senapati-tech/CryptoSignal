/**
 * routes/portfolio.js
 * Handles user portfolio CRUD operations.
 * All routes are protected — requires JWT token.
 *
 * GET    /api/portfolio          — get user's portfolio
 * POST   /api/portfolio/add      — add a coin holding
 * PUT    /api/portfolio/:id      — update a holding
 * DELETE /api/portfolio/:id      — remove a holding
 * PUT    /api/portfolio/prices   — update current prices
 */

const router    = require("express").Router();
const protect   = require("../middleware/auth");
const Portfolio = require("../models/Portfolio");

// All portfolio routes require login
router.use(protect);


// ══════════════════════════════════════════════════════════════════════════
// GET /api/portfolio
// ══════════════════════════════════════════════════════════════════════════
router.get("/", async (req, res) => {
  try {
    let portfolio = await Portfolio.findOne({ user: req.user.id });

    // Create empty portfolio if first time
    if (!portfolio) {
      portfolio = await Portfolio.create({
        user:     req.user.id,
        holdings: [],
      });
    }

    res.json({ success: true, portfolio });

  } catch (err) {
    console.error("[Portfolio GET]", err.message);
    res.status(500).json({ success: false, error: "Server error" });
  }
});


// ══════════════════════════════════════════════════════════════════════════
// POST /api/portfolio/add
// ══════════════════════════════════════════════════════════════════════════
router.post("/add", async (req, res) => {
  const { symbol, name, quantity, buyPrice, notes } = req.body;

  if (!symbol || !quantity || !buyPrice) {
    return res.status(400).json({
      success: false,
      error:   "symbol, quantity and buyPrice are required",
    });
  }

  if (quantity <= 0 || buyPrice <= 0) {
    return res.status(400).json({
      success: false,
      error:   "quantity and buyPrice must be greater than 0",
    });
  }

  try {
    let portfolio = await Portfolio.findOne({ user: req.user.id });

    if (!portfolio) {
      portfolio = await Portfolio.create({
        user:     req.user.id,
        holdings: [],
      });
    }

    // Add new holding
    portfolio.holdings.push({
      symbol:       symbol.toUpperCase(),
      name:         name || "",
      quantity:     parseFloat(quantity),
      buyPrice:     parseFloat(buyPrice),
      currentPrice: parseFloat(buyPrice),  // default to buy price
      notes:        notes || "",
    });

    portfolio.recalculate();
    await portfolio.save();

    res.status(201).json({ success: true, portfolio });

  } catch (err) {
    console.error("[Portfolio ADD]", err.message);
    res.status(500).json({ success: false, error: "Server error" });
  }
});


// ══════════════════════════════════════════════════════════════════════════
// PUT /api/portfolio/:holdingId  — update a holding
// ══════════════════════════════════════════════════════════════════════════
router.put("/:holdingId", async (req, res) => {
  const { quantity, buyPrice, notes } = req.body;

  try {
    const portfolio = await Portfolio.findOne({ user: req.user.id });
    if (!portfolio) {
      return res.status(404).json({ success: false, error: "Portfolio not found" });
    }

    const holding = portfolio.holdings.id(req.params.holdingId);
    if (!holding) {
      return res.status(404).json({ success: false, error: "Holding not found" });
    }

    if (quantity !== undefined) holding.quantity  = parseFloat(quantity);
    if (buyPrice !== undefined) holding.buyPrice  = parseFloat(buyPrice);
    if (notes    !== undefined) holding.notes     = notes;

    portfolio.recalculate();
    await portfolio.save();

    res.json({ success: true, portfolio });

  } catch (err) {
    console.error("[Portfolio UPDATE]", err.message);
    res.status(500).json({ success: false, error: "Server error" });
  }
});


// ══════════════════════════════════════════════════════════════════════════
// DELETE /api/portfolio/:holdingId
// ══════════════════════════════════════════════════════════════════════════
router.delete("/:holdingId", async (req, res) => {
  try {
    const portfolio = await Portfolio.findOne({ user: req.user.id });
    if (!portfolio) {
      return res.status(404).json({ success: false, error: "Portfolio not found" });
    }

    portfolio.holdings = portfolio.holdings.filter(
      (h) => h._id.toString() !== req.params.holdingId
    );

    portfolio.recalculate();
    await portfolio.save();

    res.json({ success: true, portfolio });

  } catch (err) {
    console.error("[Portfolio DELETE]", err.message);
    res.status(500).json({ success: false, error: "Server error" });
  }
});


// ══════════════════════════════════════════════════════════════════════════
// PUT /api/portfolio/prices  — bulk update current prices
// Called by Socket.io price feed
// ══════════════════════════════════════════════════════════════════════════
router.put("/update/prices", async (req, res) => {
  const { prices } = req.body;
  // prices = [{ symbol: "BTC-USD", price: 65000 }, ...]

  if (!prices || !Array.isArray(prices)) {
    return res.status(400).json({ success: false, error: "prices array required" });
  }

  try {
    const portfolio = await Portfolio.findOne({ user: req.user.id });
    if (!portfolio) {
      return res.status(404).json({ success: false, error: "Portfolio not found" });
    }

    // Update current price for each holding
    portfolio.holdings.forEach((holding) => {
      const update = prices.find((p) => p.symbol === holding.symbol);
      if (update) {
        holding.currentPrice = update.price;
      }
    });

    portfolio.recalculate();
    await portfolio.save();

    res.json({ success: true, portfolio });

  } catch (err) {
    console.error("[Portfolio PRICES]", err.message);
    res.status(500).json({ success: false, error: "Server error" });
  }
});


module.exports = router;