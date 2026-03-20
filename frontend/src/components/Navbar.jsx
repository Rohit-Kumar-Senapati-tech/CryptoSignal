import { Link, useLocation } from "react-router-dom";

export default function Navbar({ user, onLogout }) {
  const { pathname } = useLocation();

  const linkStyle = (path) => ({
    display: "flex", alignItems: "center", gap: 6,
    padding: "7px 14px", borderRadius: 8, fontSize: 14, fontWeight: 500,
    textDecoration: "none", transition: "all 0.18s",
    color: pathname === path ? "#e2e8f0" : "#64748b",
    background: pathname === path ? "#141d2e" : "transparent",
    border: `1px solid ${pathname === path ? "#1e2d45" : "transparent"}`,
  });

  return (
    <nav style={{
      display: "flex", alignItems: "center", justifyContent: "space-between",
      padding: "0 28px", height: 60,
      borderBottom: "1px solid #1e2d45",
      background: "rgba(5,7,9,0.85)",
      backdropFilter: "blur(12px)",
      position: "sticky", top: 0, zIndex: 100,
    }}>
      {/* Logo */}
      <Link to="/" style={{ display:"flex", alignItems:"center", gap:10, textDecoration:"none" }}>
        <div style={{
          width: 32, height: 32, borderRadius: 8,
          background: "linear-gradient(135deg,#3b82f6,#6366f1)",
          display: "grid", placeItems: "center", fontSize: 16,
        }}>📈</div>
        <span style={{ fontSize: 17, fontWeight: 700, color: "#e2e8f0", letterSpacing: -0.3 }}>
          Crypto<span style={{ color: "#3b82f6" }}>Signal</span>
        </span>
      </Link>

      {/* Nav links */}
      <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
        <Link to="/"          style={linkStyle("/")}>Dashboard</Link>
        <Link to="/portfolio" style={linkStyle("/portfolio")}>Portfolio</Link>
      </div>

      {/* Auth */}
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        {user ? (
          <>
            <div style={{
              width: 30, height: 30, borderRadius: "50%",
              background: "linear-gradient(135deg,#3b82f6,#6366f1)",
              display: "grid", placeItems: "center",
              fontSize: 13, fontWeight: 700, color: "#fff",
            }}>
              {user.name?.[0]?.toUpperCase()}
            </div>
            <span style={{ fontSize: 13, color: "#64748b" }}>{user.name}</span>
            <button onClick={onLogout} style={{
              background: "transparent", border: "1px solid #1e2d45",
              borderRadius: 8, padding: "6px 14px", color: "#94a3b8",
              fontSize: 13, cursor: "pointer", fontFamily: "Space Grotesk,sans-serif",
              transition: "all 0.18s",
            }}>Logout</button>
          </>
        ) : (
          <>
            <Link to="/login" style={{
              padding: "7px 16px", borderRadius: 8, fontSize: 13, fontWeight: 500,
              textDecoration: "none", color: "#94a3b8", border: "1px solid #1e2d45",
              transition: "all 0.18s",
            }}>Login</Link>
            <Link to="/register" style={{
              padding: "7px 16px", borderRadius: 8, fontSize: 13, fontWeight: 600,
              textDecoration: "none", color: "#fff",
              background: "linear-gradient(135deg,#3b82f6,#6366f1)",
            }}>Sign Up</Link>
          </>
        )}
      </div>
    </nav>
  );
}