/**
 * routes/auth.js
 * Handles user registration, login, and profile.
 *
 * POST /api/auth/register  — create new account
 * POST /api/auth/login     — login + get JWT token
 * GET  /api/auth/me        — get logged in user info
 */

const router  = require("express").Router();
const jwt     = require("jsonwebtoken");
const User    = require("../models/User");
const protect = require("../middleware/auth");

// ── Helper: generate JWT token ─────────────────────────────────────────────
const generateToken = (userId) => {
  return jwt.sign(
    { id: userId },
    process.env.JWT_SECRET,
    { expiresIn: "7d" }
  );
};

// ── Helper: send token response ────────────────────────────────────────────
const sendTokenResponse = (user, statusCode, res) => {
  const token = generateToken(user._id);
  res.status(statusCode).json({
    success: true,
    token,
    user: {
      id:    user._id,
      name:  user.name,
      email: user.email,
    },
  });
};


// ══════════════════════════════════════════════════════════════════════════
// POST /api/auth/register
// ══════════════════════════════════════════════════════════════════════════
router.post("/register", async (req, res) => {
  const { name, email, password } = req.body;

  // ── Validate input ─────────────────────────────────────────────────────
  if (!name || !email || !password) {
    return res.status(400).json({
      success: false,
      error:   "Please provide name, email and password",
    });
  }

  if (password.length < 6) {
    return res.status(400).json({
      success: false,
      error:   "Password must be at least 6 characters",
    });
  }

  try {
    // ── Check if email already exists ──────────────────────────────────
    const existingUser = await User.findOne({ email: email.toLowerCase() });
    if (existingUser) {
      return res.status(400).json({
        success: false,
        error:   "Email already registered",
      });
    }

    // ── Create user (password auto-hashed by User model) ───────────────
    const user = await User.create({ name, email, password });

    sendTokenResponse(user, 201, res);

  } catch (err) {
    console.error("[Register Error]", err.message);
    res.status(500).json({
      success: false,
      error:   "Server error during registration",
    });
  }
});


// ══════════════════════════════════════════════════════════════════════════
// POST /api/auth/login
// ══════════════════════════════════════════════════════════════════════════
router.post("/login", async (req, res) => {
  const { email, password } = req.body;

  // ── Validate input ─────────────────────────────────────────────────────
  if (!email || !password) {
    return res.status(400).json({
      success: false,
      error:   "Please provide email and password",
    });
  }

  try {
    // ── Find user ──────────────────────────────────────────────────────
    const user = await User.findOne({ email: email.toLowerCase() }).select("+password");
    if (!user) {
      return res.status(401).json({
        success: false,
        error:   "Invalid email or password",
      });
    }

    // ── Check password ─────────────────────────────────────────────────
    const isMatch = await user.matchPassword(password);
    if (!isMatch) {
      return res.status(401).json({
        success: false,
        error:   "Invalid email or password",
      });
    }

    sendTokenResponse(user, 200, res);

  } catch (err) {
    console.error("[Login Error]", err.message);
    res.status(500).json({
      success: false,
      error:   "Server error during login",
    });
  }
});


// ══════════════════════════════════════════════════════════════════════════
// GET /api/auth/me  (protected)
// ══════════════════════════════════════════════════════════════════════════
router.get("/me", protect, async (req, res) => {
  try {
    const user = await User.findById(req.user.id);
    res.json({
      success: true,
      user: {
        id:        user._id,
        name:      user.name,
        email:     user.email,
        createdAt: user.createdAt,
      },
    });
  } catch (err) {
    res.status(500).json({ success: false, error: "Server error" });
  }
});


module.exports = router;