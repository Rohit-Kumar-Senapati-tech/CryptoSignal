/**
 * components/NewsFeed.jsx
 * Shows news headlines with sentiment scores.
 */
import { formatDate } from "../utils/format";

const LABEL_STYLE = {
  bullish: { bg: "rgba(34,211,165,0.12)", color: "#22d3a5" },
  bearish: { bg: "rgba(244,63,94,0.12)",  color: "#f43f5e" },
  neutral: { bg: "rgba(71,85,105,0.2)",   color: "#94a3b8" },
};

export default function NewsFeed({ sentiment, loading, symbol }) {
  const cfg = LABEL_STYLE[sentiment?.overall_label] || LABEL_STYLE.neutral;

  return (
    <div style={{
      background: "#0f1623", border: "1px solid #1e2d45",
      borderRadius: 18, padding: 24,
    }}>
      {/* Header */}
      <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom: 16 }}>
        <div style={{ fontSize: 11, letterSpacing: 2, textTransform: "uppercase", color: "#64748b", fontWeight: 600 }}>
          News Sentiment — {symbol?.replace("-USD","")}
        </div>
        {sentiment && (
          <div style={{ display:"flex", alignItems:"center", gap: 8 }}>
            <span style={{
              background: cfg.bg, color: cfg.color,
              padding: "3px 10px", borderRadius: 6,
              fontSize: 11, fontWeight: 700, textTransform: "uppercase",
            }}>
              {sentiment.overall_label}
            </span>
            <span style={{ fontFamily:"JetBrains Mono,monospace", fontSize:12, color:"#64748b" }}>
              {sentiment.overall_score > 0 ? "+" : ""}{sentiment.overall_score}
            </span>
          </div>
        )}
      </div>

      {/* Sentiment counts */}
      {sentiment && sentiment.total_articles > 0 && (
        <div style={{ display:"flex", gap:16, marginBottom:16, padding:"10px 14px", background:"#0a0e17", borderRadius:10 }}>
          <Stat label="Total" value={sentiment.total_articles} color="#94a3b8" />
          <Stat label="Bullish" value={sentiment.bullish_count} color="#22d3a5" />
          <Stat label="Bearish" value={sentiment.bearish_count} color="#f43f5e" />
          <Stat label="Neutral" value={sentiment.neutral_count} color="#64748b" />
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div style={{ display:"flex", gap:8, alignItems:"center", color:"#64748b", fontSize:13, padding:"8px 0" }}>
          <div style={{ width:14, height:14, border:"2px solid #1e2d45", borderTopColor:"#3b82f6", borderRadius:"50%", animation:"spin 0.7s linear infinite" }} />
          Fetching latest news…
          <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
        </div>
      )}

      {/* Articles */}
      {sentiment?.articles?.length > 0 ? (
        <div>
          {sentiment.articles.map((a, i) => {
            const lCfg = LABEL_STYLE[a.sentiment_label] || LABEL_STYLE.neutral;
            return (
              <div key={i} style={{
                borderBottom: i < sentiment.articles.length - 1 ? "1px solid #1e2d45" : "none",
                padding: "14px 0",
              }}>
                <a href={a.url} target="_blank" rel="noreferrer" style={{
                  fontSize: 14, fontWeight: 500, color: "#e2e8f0",
                  textDecoration: "none", lineHeight: 1.5, display: "block", marginBottom: 6,
                }}>
                  {a.title}
                </a>
                <div style={{ display:"flex", gap:8, alignItems:"center" }}>
                  <span style={{
                    background: lCfg.bg, color: lCfg.color,
                    padding: "2px 8px", borderRadius: 4, fontSize: 10, fontWeight: 700,
                  }}>
                    {a.sentiment_label}
                  </span>
                  <span style={{ fontSize:11, color:"#475569" }}>{a.source}</span>
                  <span style={{ fontSize:11, color:"#475569" }}>{formatDate(a.publishedAt)}</span>
                </div>
              </div>
            );
          })}
        </div>
      ) : !loading && (
        <p style={{ color:"#475569", fontSize:13 }}>
          No news found. Check your NEWS_API_KEY in backend-ml/.env
        </p>
      )}
    </div>
  );
}

function Stat({ label, value, color }) {
  return (
    <div>
      <div style={{ fontSize:9, letterSpacing:1, textTransform:"uppercase", color:"#475569", marginBottom:2 }}>{label}</div>
      <div style={{ fontFamily:"JetBrains Mono,monospace", fontSize:18, fontWeight:700, color }}>{value}</div>
    </div>
  );
}