/**
 * CoinSelector.jsx
 * Shows popular coins as quick buttons +
 * a searchable dropdown of ALL Binance USDT pairs.
 */
import { useState, useEffect, useRef } from "react";
import api from "../utils/api";

const POPULAR = [
  { label: "Bitcoin",   short: "BTC",  value: "BTC-USD"  },
  { label: "Ethereum",  short: "ETH",  value: "ETH-USD"  },
  { label: "Solana",    short: "SOL",  value: "SOL-USD"  },
  { label: "BNB",       short: "BNB",  value: "BNB-USD"  },
  { label: "XRP",       short: "XRP",  value: "XRP-USD"  },
  { label: "Dogecoin",  short: "DOGE", value: "DOGE-USD" },
  { label: "Cardano",   short: "ADA",  value: "ADA-USD"  },
  { label: "Avalanche", short: "AVAX", value: "AVAX-USD" },
  { label: "Chainlink", short: "LINK", value: "LINK-USD" },
  { label: "Polygon",   short: "MATIC",value: "MATIC-USD"},
  { label: "Litecoin",  short: "LTC",  value: "LTC-USD"  },
  { label: "Polkadot",  short: "DOT",  value: "DOT-USD"  },
];

export default function CoinSelector({ selected, onSelect, onPredict, loading }) {
  const [allCoins,    setAllCoins]    = useState([]);
  const [search,      setSearch]      = useState("");
  const [showDropdown,setShowDropdown]= useState(false);
  const [fetching,    setFetching]    = useState(false);
  const [customSymbol,setCustomSymbol]= useState("");
  const dropdownRef = useRef(null);

  // Fetch all Binance coins on mount
  useEffect(() => {
    fetchBinanceCoins();
  }, []);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handler = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const fetchBinanceCoins = async () => {
    setFetching(true);
    try {
      const { data } = await api.get("/ml/binance/coins");
      setAllCoins(data.coins || []);
    } catch {
      // fallback to popular coins if Binance fetch fails
      setAllCoins(POPULAR.map(c => ({ label: c.label, value: c.value, symbol: c.short })));
    } finally {
      setFetching(false);
    }
  };

  // Filter coins by search
  const filtered = allCoins.filter(c =>
    c.symbol?.toLowerCase().includes(search.toLowerCase()) ||
    c.label?.toLowerCase().includes(search.toLowerCase())
  ).slice(0, 50); // show max 50 results

  const handleSelect = (value) => {
    onSelect(value);
    setSearch("");
    setShowDropdown(false);
    setCustomSymbol("");
  };

  const handlePredict = () => {
    if (customSymbol.trim()) {
      const sym = customSymbol.includes("-")
        ? customSymbol.toUpperCase()
        : `${customSymbol.toUpperCase()}-USD`;
      onSelect(sym);
      onPredict(sym);
    } else {
      onPredict(selected);
    }
  };

  return (
    <div style={{
      background: "#0f1623",
      border: "1px solid #1e2d45",
      borderRadius: 18, padding: 24, marginBottom: 16,
    }}>
      <div style={{ fontSize: 11, letterSpacing: 2, textTransform: "uppercase", color: "#64748b", marginBottom: 14, fontWeight: 600 }}>
        Select Asset
      </div>

      {/* Popular coins grid */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fill, minmax(100px, 1fr))",
        gap: 8, marginBottom: 16,
      }}>
        {POPULAR.map(coin => {
          const active = selected === coin.value;
          return (
            <button key={coin.value}
              onClick={() => handleSelect(coin.value)}
              style={{
                background: active ? "rgba(59,130,246,0.1)" : "transparent",
                border: `1px solid ${active ? "rgba(59,130,246,0.4)" : "#1e2d45"}`,
                borderRadius: 10, padding: "10px 12px",
                color: active ? "#93c5fd" : "#64748b",
                fontFamily: "Space Grotesk, sans-serif",
                fontSize: 13, fontWeight: 600,
                cursor: "pointer", transition: "all 0.18s",
                textAlign: "left",
              }}
            >
              <div style={{ fontSize: 11, color: active ? "#3b82f6" : "#475569", marginBottom: 2 }}>
                {coin.short}
              </div>
              {coin.label}
            </button>
          );
        })}
      </div>

      {/* Divider */}
      <div style={{ borderTop: "1px solid #1e2d45", margin: "16px 0" }} />

      {/* Binance coins search dropdown */}
      <div style={{ marginBottom: 14 }}>
        <div style={{ fontSize: 11, letterSpacing: 2, textTransform: "uppercase", color: "#64748b", marginBottom: 10, fontWeight: 600 }}>
          All Binance Coins {allCoins.length > 0 && (
            <span style={{ color: "#3b82f6" }}>({allCoins.length} coins)</span>
          )}
        </div>

        <div ref={dropdownRef} style={{ position: "relative" }}>
          <input
            value={search}
            onChange={e => { setSearch(e.target.value); setShowDropdown(true); }}
            onFocus={() => setShowDropdown(true)}
            placeholder={fetching ? "Loading Binance coins…" : "Search any coin — e.g. SHIB, PEPE, ARB…"}
            style={{
              width: "100%",
              background: "#0a0e17",
              border: `1px solid ${showDropdown ? "rgba(59,130,246,0.4)" : "#1e2d45"}`,
              borderRadius: showDropdown && filtered.length > 0 ? "10px 10px 0 0" : 10,
              padding: "11px 16px",
              color: "#e2e8f0",
              fontFamily: "JetBrains Mono, monospace",
              fontSize: 13, outline: "none",
              transition: "border-color 0.18s",
            }}
          />

          {/* Dropdown list */}
          {showDropdown && search && filtered.length > 0 && (
            <div style={{
              position: "absolute", top: "100%", left: 0, right: 0,
              background: "#0f1623",
              border: "1px solid rgba(59,130,246,0.4)",
              borderTop: "none",
              borderRadius: "0 0 10px 10px",
              maxHeight: 280, overflowY: "auto",
              zIndex: 50,
            }}>
              {filtered.map((coin, i) => (
                <div
                  key={coin.value}
                  onClick={() => handleSelect(coin.value)}
                  style={{
                    padding: "10px 16px",
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    borderBottom: i < filtered.length - 1 ? "1px solid #1e2d45" : "none",
                    background: selected === coin.value ? "rgba(59,130,246,0.08)" : "transparent",
                    transition: "background 0.15s",
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = "rgba(59,130,246,0.06)"}
                  onMouseLeave={e => e.currentTarget.style.background = selected === coin.value ? "rgba(59,130,246,0.08)" : "transparent"}
                >
                  <span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 13, fontWeight: 600, color: "#e2e8f0" }}>
                    {coin.symbol}
                  </span>
                  <span style={{ fontSize: 11, color: "#475569" }}>
                    {coin.value}
                  </span>
                </div>
              ))}
              {filtered.length === 50 && (
                <div style={{ padding: "8px 16px", fontSize: 11, color: "#475569", textAlign: "center" }}>
                  Showing top 50 — type more to narrow results
                </div>
              )}
            </div>
          )}

          {showDropdown && search && filtered.length === 0 && (
            <div style={{
              position: "absolute", top: "100%", left: 0, right: 0,
              background: "#0f1623",
              border: "1px solid #1e2d45",
              borderTop: "none", borderRadius: "0 0 10px 10px",
              padding: "12px 16px", zIndex: 50,
              fontSize: 13, color: "#475569",
            }}>
              No coins found for "{search}"
            </div>
          )}
        </div>
      </div>

      {/* Currently selected + predict button */}
      <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
        <div style={{
          flex: 1, background: "#0a0e17",
          border: "1px solid #1e2d45", borderRadius: 10,
          padding: "11px 16px",
          display: "flex", alignItems: "center", justifyContent: "space-between",
        }}>
          <span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 13, color: "#94a3b8" }}>
            Selected:
          </span>
          <span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 14, fontWeight: 700, color: "#3b82f6" }}>
            {selected}
          </span>
        </div>

        <button
          onClick={handlePredict}
          disabled={loading}
          style={{
            background: loading ? "#1e2d45" : "linear-gradient(135deg,#3b82f6,#6366f1)",
            color: loading ? "#64748b" : "#fff",
            border: "none", borderRadius: 10,
            padding: "11px 28px",
            fontFamily: "Space Grotesk, sans-serif",
            fontWeight: 700, fontSize: 14,
            cursor: loading ? "not-allowed" : "pointer",
            transition: "all 0.18s", whiteSpace: "nowrap",
          }}
        >
          {loading ? "Loading…" : "Predict →"}
        </button>
      </div>
    </div>
  );
}