/**
 * Portfolio.js
 * MongoDB schema for user crypto portfolio.
 * Each user has one portfolio with multiple coin holdings.
 */

const mongoose = require("mongoose");

// ── Single coin holding ────────────────────────────────────────────────────
const holdingSchema = new mongoose.Schema(
  {
    symbol: {
      type:     String,
      required: true,
      uppercase: true,
      trim:     true,
      // e.g. "BTC-USD"
    },

    name: {
      type:    String,
      default: "",
      // e.g. "Bitcoin"
    },

    quantity: {
      type:     Number,
      required: true,
      min:      [0, "Quantity cannot be negative"],
    },

    buyPrice: {
      type:     Number,
      required: true,
      min:      [0, "Buy price cannot be negative"],
      // Average buy price in USD
    },

    currentPrice: {
      type:    Number,
      default: 0,
      // Updated by the real-time price feed
    },

    notes: {
      type:    String,
      default: "",
      maxLength: 200,
    },

    addedAt: {
      type:    Date,
      default: Date.now,
    },
  }
);

// ── Virtual: total invested ────────────────────────────────────────────────
holdingSchema.virtual("totalInvested").get(function () {
  return parseFloat((this.quantity * this.buyPrice).toFixed(2));
});

// ── Virtual: current value ─────────────────────────────────────────────────
holdingSchema.virtual("currentValue").get(function () {
  return parseFloat((this.quantity * this.currentPrice).toFixed(2));
});

// ── Virtual: profit/loss ───────────────────────────────────────────────────
holdingSchema.virtual("profitLoss").get(function () {
  return parseFloat(
    (this.quantity * (this.currentPrice - this.buyPrice)).toFixed(2)
  );
});

// ── Virtual: profit/loss percentage ───────────────────────────────────────
holdingSchema.virtual("profitLossPct").get(function () {
  if (this.buyPrice === 0) return 0;
  return parseFloat(
    (((this.currentPrice - this.buyPrice) / this.buyPrice) * 100).toFixed(2)
  );
});

// ── Portfolio schema ───────────────────────────────────────────────────────
const portfolioSchema = new mongoose.Schema(
  {
    user: {
      type:     mongoose.Schema.Types.ObjectId,
      ref:      "User",
      required: true,
      unique:   true,   // one portfolio per user
    },

    holdings: [holdingSchema],

    // Total portfolio value (updated periodically)
    totalValue: {
      type:    Number,
      default: 0,
    },

    totalInvested: {
      type:    Number,
      default: 0,
    },
  },
  {
    timestamps: true,
    toJSON:     { virtuals: true },
    toObject:   { virtuals: true },
  }
);

// ── Method: recalculate totals ─────────────────────────────────────────────
portfolioSchema.methods.recalculate = function () {
  this.totalInvested = parseFloat(
    this.holdings
      .reduce((sum, h) => sum + h.quantity * h.buyPrice, 0)
      .toFixed(2)
  );
  this.totalValue = parseFloat(
    this.holdings
      .reduce((sum, h) => sum + h.quantity * h.currentPrice, 0)
      .toFixed(2)
  );
};

module.exports = mongoose.model("Portfolio", portfolioSchema);