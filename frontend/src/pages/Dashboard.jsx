import { useState, useEffect } from "react";
import CoinSelector from "../components/CoinSelector";
import SignalCard   from "../components/SignalCard";
import NewsFeed     from "../components/NewsFeed";
import usePredict   from "../hooks/usePredict";
import api          from "../utils/api";

export default function Dashboard() {
  const [selected, setSelected] = useState("BTC-USD");
  const { prediction, sentiment, loading, error, predict } = usePredict();

  // Wake up Render ML service on page load
  useEffect(() => {
    api.get("/ml/health").catch(() => {});
  }, []);

  // Auto-predict when coin changes
  useEffect(() => {
    predict(selected);
  }, [selected]); // eslint-disable-line

  const handleSelect = (val) => setSelected(val);
  const handlePredict = (sym) => predict(sym || selected);

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto", padding: "28px 20px 80px" }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 26, fontWeight: 700, letterSpacing: -0.5, marginBottom: 4 }}>
          Signal Dashboard
        </h1>
        <p style={{ color: "#64748b", fontSize: 14 }}>
          AI-powered crypto price predictions with technical analysis
        </p>
      </div>
      <CoinSelector selected={selected} onSelect={handleSelect} onPredict={handlePredict} loading={loading} />
      {loading && (
        <div style={{ display:"flex", alignItems:"center", gap:10, color:"#64748b", padding:"12px 0", fontSize:13 }}>
          <div style={{ width:18, height:18, border:"2px solid #1e2d45", borderTopColor:"#3b82f6", borderRadius:"50%", animation:"spin 0.7s linear infinite" }} />
          <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
          Fetching {selected} data — please wait up to 60 seconds on first load…
        </div>
      )}
      {error && !loading && (
        <div style={{ background:"rgba(244,63,94,0.08)", border:"1px solid rgba(244,63,94,0.25)", borderRadius:12, padding:"14px 18px", color:"#f43f5e", fontSize:13, marginBottom:16 }}>
          ⚠ {error}
        </div>
      )}
      {prediction && !loading && <SignalCard data={prediction} />}
      <NewsFeed sentiment={sentiment} loading={loading} symbol={selected} />
    </div>
  );
}