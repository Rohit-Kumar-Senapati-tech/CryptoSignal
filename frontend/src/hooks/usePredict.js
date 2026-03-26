/**
 * hooks/usePredict.js
 * Custom hook — fetches prediction for a symbol.
 * Sentiment is disabled in the main predict flow to avoid repeated API hits.
 */
import { useState, useCallback } from "react";
import api from "../utils/api";

export default function usePredict() {
  const [prediction, setPrediction] = useState(null);
  const [sentiment, setSentiment] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const predict = useCallback(async (symbol) => {
    if (!symbol || loading) return;

    setLoading(true);
    setError(null);
    setPrediction(null);
    setSentiment(null);

    try {
      const { data } = await api.get("/ml/predict", {
        params: { symbol },
        timeout: 120000,
      });

      setPrediction(data);

      // Keep sentiment empty here to avoid extra rate-limited requests
      setSentiment({
        symbol,
        sentiment: "neutral",
        score: 0,
        articles: [],
      });
    } catch (e) {
      const raw =
        e.response?.data?.message ||
        e.response?.data?.error ||
        e.message ||
        "Prediction failed";

      const msg = String(raw);

      if (
        msg.toLowerCase().includes("timeout") ||
        msg.toLowerCase().includes("exceeded")
      ) {
        setError("Server is waking up — please try again in 30 seconds");
      } else if (
        msg.includes("ECONNREFUSED") ||
        msg.includes("503")
      ) {
        setError("ML service is starting up — please wait 60 seconds and try again");
      } else if (msg.includes("429") || msg.toLowerCase().includes("rate limit")) {
        setError("Too many requests right now — wait a few seconds and try again");
      } else if (msg.includes("Network Error")) {
        setError("Network error — check your internet connection");
      } else {
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  }, [loading]);

  return { prediction, sentiment, loading, error, predict };
}