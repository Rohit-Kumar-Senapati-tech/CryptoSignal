/**
 * utils/api.js
 * Central Axios instance — all API calls go through here.
 * Automatically attaches JWT token to every request.
 */
import axios from "axios";

const api = axios.create({
  baseURL: "https://cryptosignal-node.onrender.com/api",
  timeout: 120000, // 2 minutes — handles Render cold start
});

// Attach token automatically to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Handle errors globally
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem("token");
      localStorage.removeItem("user");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

export default api;