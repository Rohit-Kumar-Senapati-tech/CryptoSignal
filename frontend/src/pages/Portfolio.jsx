/**
 * pages/Portfolio.jsx
 * User portfolio tracker — add/remove/view coin holdings.
 */
import { useState, useEffect } from "react";
import api from "../utils/api";
import { formatPrice, formatPct } from "../utils/format";

export default function Portfolio() {
  const [portfolio, setPortfolio] = useState(null);
  const [loading,   setLoading]   = useState(true);
  const [adding,    setAdding]    = useState(false);
  const [error,     setError]     = useState(null);
  const [form, setForm] = useState({ symbol:"", name:"", quantity:"", buyPrice:"", notes:"" });

  useEffect(() => { fetchPortfolio(); }, []);

  const fetchPortfolio = async () => {
    try {
      const { data } = await api.get("/portfolio");
      setPortfolio(data.portfolio);
    } catch  {
      setError("Failed to load portfolio");
    } finally {
      setLoading(false);
    }
  };

  const addHolding = async () => {
    if (!form.symbol || !form.quantity || !form.buyPrice)
      return setError("Symbol, quantity and buy price are required");
    setAdding(true); setError(null);
    try {
      const { data } = await api.post("/portfolio/add", form);
      setPortfolio(data.portfolio);
      setForm({ symbol:"", name:"", quantity:"", buyPrice:"", notes:"" });
    } catch (e) {
      setError(e.response?.data?.error || "Failed to add holding");
    } finally { setAdding(false); }
  };

  const removeHolding = async (id) => {
    try {
      const { data } = await api.delete(`/portfolio/${id}`);
      setPortfolio(data.portfolio);
    } catch { setError("Failed to remove"); }
  };

  const totalPL = portfolio?.holdings?.reduce((s, h) =>
    s + h.quantity * (h.currentPrice - h.buyPrice), 0) || 0;
  const totalInvested = portfolio?.holdings?.reduce((s, h) =>
    s + h.quantity * h.buyPrice, 0) || 0;
  const totalValue = portfolio?.holdings?.reduce((s, h) =>
    s + h.quantity * h.currentPrice, 0) || 0;

  const inputStyle = {
    background: "#0a0e17", border: "1px solid #1e2d45",
    borderRadius: 8, padding: "10px 14px",
    color: "#e2e8f0", fontFamily: "JetBrains Mono,monospace",
    fontSize: 13, outline: "none", width: "100%",
  };

  if (loading) return (
    <div style={{ maxWidth:1100, margin:"0 auto", padding:"40px 20px", color:"#64748b" }}>
      Loading portfolio…
    </div>
  );

  return (
    <div style={{ maxWidth:1100, margin:"0 auto", padding:"28px 20px 80px" }}>

      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize:26, fontWeight:700, letterSpacing:-0.5, marginBottom:4 }}>My Portfolio</h1>
        <p style={{ color:"#64748b", fontSize:14 }}>Track your crypto holdings and P&L</p>
      </div>

      {/* Stats */}
      <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(180px,1fr))", gap:10, marginBottom:20 }}>
        {[
          { label:"Total Invested", value: formatPrice(totalInvested), color:"#e2e8f0" },
          { label:"Current Value",  value: formatPrice(totalValue),    color:"#3b82f6"  },
          { label:"Total P&L",      value: `${totalPL>=0?"+":""}${formatPrice(Math.abs(totalPL))}`, color: totalPL>=0?"#22d3a5":"#f43f5e" },
          { label:"Holdings",       value: portfolio?.holdings?.length||0, color:"#e2e8f0" },
        ].map(s => (
          <div key={s.label} style={{ background:"#0f1623", border:"1px solid #1e2d45", borderRadius:12, padding:18 }}>
            <div style={{ fontSize:9, letterSpacing:2, textTransform:"uppercase", color:"#64748b", marginBottom:6, fontWeight:600 }}>{s.label}</div>
            <div style={{ fontFamily:"JetBrains Mono,monospace", fontSize:20, fontWeight:700, color:s.color }}>{s.value}</div>
          </div>
        ))}
      </div>

      {/* Add form */}
      <div style={{ background:"#0f1623", border:"1px solid #1e2d45", borderRadius:18, padding:24, marginBottom:16 }}>
        <div style={{ fontSize:11, letterSpacing:2, textTransform:"uppercase", color:"#64748b", marginBottom:14, fontWeight:600 }}>
          Add Holding
        </div>
        {error && <div style={{ color:"#f43f5e", fontSize:13, marginBottom:10 }}>{error}</div>}
        <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(160px,1fr))", gap:10, marginBottom:12 }}>
          <div>
            <div style={{ fontSize:11, color:"#64748b", marginBottom:4 }}>Symbol *</div>
            <input style={inputStyle} placeholder="BTC-USD"
              value={form.symbol} onChange={e => setForm({...form, symbol:e.target.value.toUpperCase()})} />
          </div>
          <div>
            <div style={{ fontSize:11, color:"#64748b", marginBottom:4 }}>Name</div>
            <input style={inputStyle} placeholder="Bitcoin"
              value={form.name} onChange={e => setForm({...form, name:e.target.value})} />
          </div>
          <div>
            <div style={{ fontSize:11, color:"#64748b", marginBottom:4 }}>Quantity *</div>
            <input style={inputStyle} placeholder="0.5" type="number"
              value={form.quantity} onChange={e => setForm({...form, quantity:e.target.value})} />
          </div>
          <div>
            <div style={{ fontSize:11, color:"#64748b", marginBottom:4 }}>Buy Price (USD) *</div>
            <input style={inputStyle} placeholder="65000" type="number"
              value={form.buyPrice} onChange={e => setForm({...form, buyPrice:e.target.value})} />
          </div>
        </div>
        <button onClick={addHolding} disabled={adding} style={{
          background: adding ? "#1e2d45" : "linear-gradient(135deg,#3b82f6,#6366f1)",
          color: adding ? "#64748b" : "#fff",
          border:"none", borderRadius:10, padding:"11px 24px",
          fontFamily:"Space Grotesk,sans-serif", fontWeight:700,
          fontSize:14, cursor: adding ? "not-allowed" : "pointer",
        }}>
          {adding ? "Adding…" : "+ Add Holding"}
        </button>
      </div>

      {/* Holdings table */}
      <div style={{ background:"#0f1623", border:"1px solid #1e2d45", borderRadius:18, padding:24 }}>
        <div style={{ fontSize:11, letterSpacing:2, textTransform:"uppercase", color:"#64748b", marginBottom:16, fontWeight:600 }}>
          Holdings
        </div>
        {!portfolio?.holdings?.length ? (
          <p style={{ color:"#475569", fontSize:14 }}>No holdings yet. Add your first coin above!</p>
        ) : (
          <div style={{ overflowX:"auto" }}>
            <table style={{ width:"100%", borderCollapse:"collapse" }}>
              <thead>
                <tr>
                  {["Asset","Qty","Buy Price","Current","Invested","Value","P&L",""].map(h => (
                    <th key={h} style={{ textAlign:"left", padding:"8px 12px", fontSize:9,
                      letterSpacing:2, textTransform:"uppercase", color:"#475569",
                      borderBottom:"1px solid #1e2d45", fontWeight:600 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {portfolio.holdings.map(h => {
                  const invested = h.quantity * h.buyPrice;
                  const value    = h.quantity * h.currentPrice;
                  const pl       = value - invested;
                  const plPct    = invested > 0 ? (pl/invested)*100 : 0;
                  const up       = pl >= 0;
                  return (
                    <tr key={h._id} style={{ borderBottom:"1px solid #0a0e17" }}>
                      <td style={{ padding:"14px 12px" }}>
                        <div style={{ fontWeight:600, fontSize:14 }}>{h.symbol}</div>
                        <div style={{ fontSize:11, color:"#475569" }}>{h.name}</div>
                      </td>
                      <td style={{ padding:"14px 12px", fontFamily:"JetBrains Mono,monospace", fontSize:13 }}>{h.quantity}</td>
                      <td style={{ padding:"14px 12px", fontFamily:"JetBrains Mono,monospace", fontSize:13 }}>{formatPrice(h.buyPrice)}</td>
                      <td style={{ padding:"14px 12px", fontFamily:"JetBrains Mono,monospace", fontSize:13 }}>{formatPrice(h.currentPrice)}</td>
                      <td style={{ padding:"14px 12px", fontFamily:"JetBrains Mono,monospace", fontSize:13 }}>{formatPrice(invested)}</td>
                      <td style={{ padding:"14px 12px", fontFamily:"JetBrains Mono,monospace", fontSize:13 }}>{formatPrice(value)}</td>
                      <td style={{ padding:"14px 12px", fontFamily:"JetBrains Mono,monospace", fontSize:13, color: up?"#22d3a5":"#f43f5e" }}>
                        {up?"+":""}{formatPrice(Math.abs(pl))}<br/>
                        <span style={{ fontSize:10 }}>({formatPct(plPct)})</span>
                      </td>
                      <td style={{ padding:"14px 12px" }}>
                        <button onClick={() => removeHolding(h._id)} style={{
                          background:"rgba(244,63,94,0.1)", border:"1px solid rgba(244,63,94,0.25)",
                          borderRadius:6, padding:"5px 10px", color:"#f43f5e",
                          fontSize:11, cursor:"pointer", fontFamily:"Space Grotesk,sans-serif",
                        }}>Remove</button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}