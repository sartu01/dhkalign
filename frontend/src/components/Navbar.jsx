

import React from "react";
import { NavLink } from "react-router-dom";

const linkStyle = ({ isActive }) => ({
  padding: "8px 12px",
  borderRadius: 8,
  textDecoration: "none",
  display: "inline-block",
  color: isActive ? "#0b0b0f" : "var(--ink)",
  background: isActive ? "linear-gradient(135deg,var(--accent),var(--accent2))" : "transparent",
  fontWeight: 600
});

export default function Navbar() {
  return (
    <header style={{ padding: "16px 0", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <span className="badge">DHK Align</span>
      </div>
      <nav style={{ display: "flex", gap: 8 }}>
        <NavLink to="/" style={linkStyle} end>Home</NavLink>
        <NavLink to="/translate" style={linkStyle}>Translate</NavLink>
        <NavLink to="/pricing" style={linkStyle}>Pricing</NavLink>
        <NavLink to="/account" style={linkStyle}>Account</NavLink>
      </nav>
    </header>
  );
}