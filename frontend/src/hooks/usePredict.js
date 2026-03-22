/**
 * hooks/usePredict.js
 * Custom hook — fetches prediction + sentiment for a symbol.
 * Handles loading, error, and cold start states.
 */
import { useState, useCallback } from "react";
import api from "../utils/api";

export default function usePredict() {
  const [prediction, setPrediction] = useState(null);
  const [sentiment,  setSentiment]  = useState(null);
  const [loading,    setLoading]    = useState(false);
  const [error,      setError]      = useState(null);

  const predict = useCallback(async (symbol) => {
    if (!symbol) return;

    setLoading(true);
    setError(null);
    setPrediction(null);
    setSentiment(null);

    // Fetch prediction — 2 minute timeout for Render cold start
    try {
      const { data } = await api.get("/ml/predict", {
        params:  { symbol },
        timeout: 120000,
      });
      setPrediction(data);
    } catch (e) {
      const msg = e.response?.data?.error || e.message || "Prediction failed";

      if (msg.includes("timeout") || msg.includes("exceeded")) {
        setError("Server is waking up — please try again in 30 seconds");
      } else if (msg.includes("ECONNREFUSED") || msg.includes("503")) {
        setError("ML service is starting up — please wait 60 seconds and try again");
      } else if (msg.includes("Network Error")) {
        setError("Network error — check your internet connection");
      } else {
        setError(msg);
      }

      setLoading(false);
      return;
    }

    // Fetch sentiment — non-blocking, optional
    try {
      const { data } = await api.get("/ml/sentiment", {
        params:  { symbol },
        timeout: 30000,
      });
      setSentiment(data);
    } catch {
      // sentiment is optional — silently fail
    }

    setLoading(false);
  }, []);

  return { prediction, sentiment, loading, error, predict };
}