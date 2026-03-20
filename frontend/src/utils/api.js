/**
 * utils/api.js
 * Central Axios instance — all API calls go through here.
 * Automatically attaches JWT token to every request.
 */
import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:5000/api",
  timeout: 20000,
});

// Attach token automatically
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Handle 401 globally — log user out if token expired
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