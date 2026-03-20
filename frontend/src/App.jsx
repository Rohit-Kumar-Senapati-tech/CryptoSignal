import { Routes, Route, Navigate } from "react-router-dom";
import { useState } from "react";
import Navbar    from "./components/Navbar";
import Dashboard from "./pages/Dashboard";
import Portfolio from "./pages/Portfolio";
import Login     from "./pages/Login";
import Register  from "./pages/Register";

function getInitialUser() {
  try {
    const token = localStorage.getItem("token");
    const saved = localStorage.getItem("user");
    if (token && saved) return JSON.parse(saved);
  } catch (err) {
  console.error("Auth parse error:", err);
  }
  return null;
}

export default function App() {
  const [user, setUser] = useState(getInitialUser);

  const handleLogin = (userData) => setUser(userData);

  const handleLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    setUser(null);
  };

  return (
    <>
      <Navbar user={user} onLogout={handleLogout} />
      <Routes>
        <Route path="/"          element={<Dashboard />} />
        <Route path="/portfolio" element={user ? <Portfolio /> : <Navigate to="/login" />} />
        <Route path="/login"     element={user ? <Navigate to="/" /> : <Login    onLogin={handleLogin} />} />
        <Route path="/register"  element={user ? <Navigate to="/" /> : <Register onLogin={handleLogin} />} />
        <Route path="*"          element={<Navigate to="/" />} />
      </Routes>
    </>
  );
}