/**
 * middleware/auth.js
 * Protects routes by verifying JWT token.
 * Add this to any route that requires login.
 */

const jwt  = require("jsonwebtoken");
const User = require("../models/User");

const protect = async (req, res, next) => {
  let token;

  // Check for token in Authorization header
  if (
    req.headers.authorization &&
    req.headers.authorization.startsWith("Bearer ")
  ) {
    token = req.headers.authorization.split(" ")[1];
  }

  if (!token) {
    return res.status(401).json({
      success: false,
      error:   "Not authorised — no token provided",
    });
  }

  try {
    // Verify token
    const decoded = jwt.verify(token, process.env.JWT_SECRET);

    // Attach user to request
    req.user = await User.findById(decoded.id).select("-password");

    if (!req.user) {
      return res.status(401).json({
        success: false,
        error:   "User no longer exists",
      });
    }

    next();

  } catch (err) {
    return res.status(401).json({
      success: false,
      error:   "Not authorised — invalid token",
    });
  }
};

module.exports = protect;