/**
 * hooks/usePredict.js
 * Custom hook — fetches prediction + sentiment for a symbol.
 * Handles loading, error, and caching states.
 */
import { useState, useCallback } from "react";
import api from "../utils/api";

export default function usePredict() {
  const [prediction, setPrediction] = useState(null);
  const [sentiment,  setSentiment]  = useState(null);
  const [loading,    setLoading]    = useState(false);
  const [error,      setError]      = useState(null);

  const predict = useCallback(async (symbol) => {
    setLoading(true);
    setError(null);
    setPrediction(null);
    setSentiment(null);

    // Fetch prediction
    try {
      const { data } = await api.get("/ml/predict", { params: { symbol } });
      setPrediction(data);
    } catch (e) {
      const msg = e.response?.data?.error || e.message;
      if (msg.includes("ECONNREFUSED") || msg.includes("not running")) {
        setError("Python ML service is not running. Run: python app.py in backend-ml");
      } else {
        setError(msg || "Prediction failed");
      }
      setLoading(false);
      return;
    }

    // Fetch sentiment (non-blocking — doesn't show error if fails)
    try {
      const { data } = await api.get("/ml/sentiment", { params: { symbol } });
      setSentiment(data);
    } catch {
      // sentiment is optional
    }

    setLoading(false);
  }, []);

  return { prediction, sentiment, loading, error, predict };
}