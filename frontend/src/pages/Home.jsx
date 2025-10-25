import React from "react";
import { Link } from "react-router-dom";

export default function Home() {
  return (
    <section className="hero">
      <div style={{ flex: 1 }}>
        <span className="badge">Banglish ↔ English</span>
        <h1 className="title">Translation that respects tone and culture.</h1>
        <p className="kicker">
          Roman Bangla to English — and back — with natural phrasing. Free tier is fast DB lookup; Pro adds GPT fallback and priority routing.
        </p>
        <div style={{ display: "flex", gap: 10, marginTop: 18 }}>
          <Link to="/translate">
            <button type="button" aria-label="Open translator">Open Translator</button>
          </Link>
          <Link to="/pricing">
            <button type="button" aria-label="See pricing" style={{ background: "var(--panel)", color: "var(--ink)", border: "1px solid #1f1f2a" }}>
              See Pricing
            </button>
          </Link>
        </div>
      </div>
      <div style={{ flex: 1 }}>
        <div className="card">
          <h3 style={{ marginTop: 0 }}>What makes this different</h3>
          <ul className="muted" style={{ margin: 0, paddingLeft: 18 }}>
            <li>Emotion-aware phrasing (not literal word maps).</li>
            <li>Banglish (Roman Bangla) first — diaspora friendly.</li>
            <li>Edge-shielded API with quotas, HMAC, Turnstile.</li>
          </ul>
        </div>
      </div>
    </section>
  );
}
