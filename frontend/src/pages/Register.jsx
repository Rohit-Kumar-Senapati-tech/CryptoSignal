import { useState } from "react";
import { Link } from "react-router-dom";
import useAuth from "../hooks/useAuth";

export default function Register({ onLogin }) {
  const [form,    setForm]    = useState({ name:"", email:"", password:"" });
  const [error,   setError]   = useState(null);
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();

  const handle = async () => {
    if (!form.name || !form.email || !form.password) return setError("Please fill in all fields");
    if (form.password.length < 6) return setError("Password must be at least 6 characters");
    setLoading(true); setError(null);
    try {
      const data = await register(form.name, form.email, form.password);
      onLogin(data.user, data.token);
    } catch (e) {
      setError(e.response?.data?.error || "Registration failed");
    } finally { setLoading(false); }
  };

  const f = (key) => ({
    value: form[key],
    onChange: (v) => setForm({...form, [key]:v}),
  });

  return (
    <div style={{ minHeight:"calc(100vh - 60px)", display:"flex", alignItems:"center", justifyContent:"center", padding:20 }}>
      <div style={{ background:"#0f1623", border:"1px solid #1e2d45", borderRadius:20, padding:"40px 36px", width:"100%", maxWidth:400 }}>
        <div style={{ textAlign:"center", marginBottom:32 }}>
          <div style={{ fontSize:32, marginBottom:10 }}>🚀</div>
          <h1 style={{ fontSize:24, fontWeight:700, marginBottom:6 }}>Create account</h1>
          <p style={{ color:"#64748b", fontSize:14 }}>Start tracking crypto signals for free</p>
        </div>

        {error && (
          <div style={{ background:"rgba(244,63,94,0.08)", border:"1px solid rgba(244,63,94,0.25)", borderRadius:8, padding:"10px 14px", color:"#f43f5e", fontSize:13, marginBottom:16 }}>
            {error}
          </div>
        )}

        <Field label="Full Name"  type="text"     placeholder="Rohit"          {...f("name")}     />
        <Field label="Email"      type="email"    placeholder="you@example.com" {...f("email")}    />
        <Field label="Password"   type="password" placeholder="Min 6 characters" {...f("password")} onEnter={handle} />

        <button onClick={handle} disabled={loading} style={{
          width:"100%", background: loading?"#1e2d45":"linear-gradient(135deg,#3b82f6,#6366f1)",
          color: loading?"#64748b":"#fff", border:"none", borderRadius:10,
          padding:14, fontFamily:"Space Grotesk,sans-serif",
          fontWeight:700, fontSize:15, cursor: loading?"not-allowed":"pointer", marginTop:8,
        }}>
          {loading ? "Creating…" : "Create Account →"}
        </button>

        <p style={{ textAlign:"center", marginTop:24, fontSize:14, color:"#64748b" }}>
          Already have an account?{" "}
          <Link to="/login" style={{ color:"#3b82f6", textDecoration:"none", fontWeight:600 }}>Sign in</Link>
        </p>
      </div>
    </div>
  );
}

function Field({ label, type, value, onChange, placeholder, onEnter }) {
  return (
    <div style={{ marginBottom:16 }}>
      <label style={{ fontSize:12, color:"#94a3b8", marginBottom:6, display:"block", fontWeight:600 }}>{label}</label>
      <input
        type={type} value={value} placeholder={placeholder}
        onChange={e => onChange(e.target.value)}
        onKeyDown={e => e.key==="Enter" && onEnter?.()}
        style={{
          width:"100%", background:"#0a0e17", border:"1px solid #1e2d45",
          borderRadius:10, padding:"12px 16px", color:"#e2e8f0",
          fontFamily:"JetBrains Mono,monospace", fontSize:13, outline:"none",
        }}
      />
    </div>
  );
}