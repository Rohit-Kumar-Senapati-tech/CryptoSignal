/**
 * utils/format.js
 * Helper functions for formatting numbers and dates.
 */

export const formatPrice = (n) => {
  if (n === undefined || n === null) return "—";
  if (n >= 1000) return `$${Number(n).toLocaleString("en-US", { maximumFractionDigits: 2 })}`;
  return `$${Number(n).toFixed(4)}`;
};

export const formatPct = (n) => {
  if (n === undefined || n === null) return "—";
  const sign = n >= 0 ? "+" : "";
  return `${sign}${Number(n).toFixed(2)}%`;
};

export const formatDate = (str) => {
  if (!str) return "";
  return new Date(str).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
};

export const formatNum = (n, decimals = 4) => {
  if (n === undefined || n === null) return "—";
  return Number(n).toFixed(decimals);
};