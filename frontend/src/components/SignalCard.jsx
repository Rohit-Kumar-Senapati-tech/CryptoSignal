/**
 * components/SignalCard.jsx
 * Shows the UP / DOWN / NO TRADE prediction with confidence.
 */
import { formatNum } from "../utils/format";

const SIGNAL_CONFIG = {
  UP:       { color: "#22d3a5", bg: "rgba(34,211,165,0.08)",  border: "rgba(34,211,165,0.25)", emoji: "↑" },
  DOWN:     { color: "#f43f5e", bg: "rgba(244,63,94,0.08)",   border: "rgba(244,63,94,0.25)",  emoji: "↓" },
  "NO TRADE":{ color: "#f59e0b", bg: "rgba(245,158,11,0.08)", border: "rgba(245,158,11,0.25)", emoji: "–" },
};

export default function SignalCard({ data }) {
  if (!data) return null;
  const cfg = SIGNAL_CONFIG[data.signal] || SIGNAL_CONFIG["NO TRADE"];

  return (
    <div className="fade-up" style={{
      background: cfg.bg,
      border: `1px solid ${cfg.border}`,
      borderRadius: 18, padding: "28px 28px 24px",
      marginBottom: 16,
    }}>
      {/* Top row */}
      <div style={{ display:"flex", alignItems:"flex-start", justifyContent:"space-between", marginBottom: 20 }}>
        <div>
          <div style={{ fontSize: 11, letterSpacing: 2, textTransform: "uppercase", color: "#64748b", marginBottom: 8, fontWeight: 600 }}>
            {data.coin}
          </div>
          <div style={{ fontSize: 52, fontWeight: 700, color: cfg.color, lineHeight: 1, letterSpacing: -2 }}>
            {cfg.emoji} {data.signal}
          </div>
          {data.reason && (
            <div style={{ fontSize: 13, color: "#64748b", marginTop: 8 }}>{data.reason}</div>
          )}
        </div>

        {/* Confidence dial */}
        <div style={{ textAlign: "center" }}>
          <ConfidenceDial value={data.confidence} color={cfg.color} />
        </div>
      </div>

      {/* Indicators grid */}
      {data.indicators && (
        <>
          <div style={{ fontSize: 10, letterSpacing: 2, textTransform: "uppercase", color: "#64748b", marginBottom: 10, fontWeight: 600 }}>
            Technical Indicators
          </div>
          <div style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))",
            gap: 8,
          }}>
            {Object.entries(data.indicators).map(([key, val]) => (
              <IndicatorTile
                key={key}
                name={key}
                value={val}
                interpretation={data.interpretations?.[key]}
              />
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function ConfidenceDial({ value, color }) {
  const r = 36;
  const circ = 2 * Math.PI * r;
  const offset = circ - (value / 100) * circ;

  return (
    <div style={{ position: "relative", width: 90, height: 90 }}>
      <svg width="90" height="90" viewBox="0 0 90 90" style={{ transform: "rotate(-90deg)" }}>
        <circle cx="45" cy="45" r={r} fill="none" stroke="#1e2d45" strokeWidth="5" />
        <circle
          cx="45" cy="45" r={r} fill="none"
          stroke={color} strokeWidth="5"
          strokeLinecap="round"
          strokeDasharray={circ}
          strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 0.8s ease" }}
        />
      </svg>
      <div style={{
        position: "absolute", inset: 0,
        display: "flex", flexDirection: "column",
        alignItems: "center", justifyContent: "center",
      }}>
        <span style={{ fontFamily: "JetBrains Mono,monospace", fontSize: 17, fontWeight: 700, color }}>{value}%</span>
        <span style={{ fontSize: 9, letterSpacing: 1, color: "#475569", textTransform: "uppercase" }}>conf</span>
      </div>
    </div>
  );
}

function IndicatorTile({ name, value, interpretation }) {
  return (
    <div style={{
      background: "rgba(5,7,9,0.5)",
      border: "1px solid #1e2d45",
      borderRadius: 10, padding: "12px 14px",
    }}>
      <div style={{ fontSize: 9, letterSpacing: 1.5, textTransform: "uppercase", color: "#475569", marginBottom: 5, fontWeight: 600 }}>
        {name.replace(/_/g, " ")}
      </div>
      <div style={{ fontFamily: "JetBrains Mono,monospace", fontSize: 15, fontWeight: 600, color: "#e2e8f0" }}>
        {typeof value === "number" ? formatNum(value, 4) : value}
      </div>
      {interpretation && (
        <div style={{ fontSize: 10, color: "#475569", marginTop: 4, lineHeight: 1.4 }}>
          {interpretation}
        </div>
      )}
    </div>
  );
}