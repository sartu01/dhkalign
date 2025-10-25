import React, { useState } from "react";

// Backend origin (server-side only secrets). Stripe sessions are created on the server.
const BACKEND = "https://backend.dhkalign.com";

export default function Pricing({ canceled = false, openKeyModal }) {
  const [loading, setLoading] = useState(null); // 'everyday' | 'slang' | 'bundle' | null
  const [err, setErr] = useState(null);

  async function buy(pack) {
    setErr(null);
    setLoading(pack);
    try {
      const res = await fetch(`${BACKEND}/api/billing/create-checkout-session`, {
        method: "POST",
        headers: {
          "content-type": "application/json",
          "accept": "application/json",
          // If you add Turnstile later, include: "x-turnstile": tsToken
        },
        body: JSON.stringify({
          pack,                                       // ← per-pack, one-time
          success_url: "https://dhkalign.com/billing/success",
          cancel_url: "https://dhkalign.com/billing/cancel",
        }),
      });
      const json = await res.json();
      if (!res.ok || !json?.url) throw new Error(json?.detail || "Checkout failed");
      window.location.href = json.url; // Stripe Checkout URL
    } catch (ex) {
      setErr(ex?.message || "Network error");
    } finally {
      setLoading(null);
    }
  }

  return (
    <section className="grid">
      <div className="card">
        <h3 style={{ marginTop: 0 }}>Everyday Pack — $3 (one-time)</h3>
        <ul className="muted">
          <li>Daily Banglish phrases</li>
          <li>DB lookup (fast)</li>
        </ul>
        <button onClick={() => buy("everyday")} disabled={loading === "everyday"}>
          {loading === "everyday" ? "Redirecting…" : "Buy Everyday"}
        </button>
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Slang Pack — $4 (one-time)</h3>
        <ul className="muted">
          <li>Youth slang & banter</li>
          <li>Server GPT fallback on miss</li>
        </ul>
        <button onClick={() => buy("slang")} disabled={loading === "slang"}>
          {loading === "slang" ? "Redirecting…" : "Buy Slang"}
        </button>
        {typeof openKeyModal === "function" && (
          <p className="muted" style={{ marginTop: 12 }}>
            Using Pro translate?{" "}
            <a href="#setkey" onClick={(e) => { e.preventDefault(); openKeyModal(); }}>
              Set your Pro Edge key
            </a>
            .
          </p>
        )}
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>All‑in Bundle — $6 (one-time)</h3>
        <ul className="muted">
          <li>Everyday + Slang + priority path</li>
          <li>Future add‑ons discounted</li>
        </ul>
        <button onClick={() => buy("pro_bundle")} disabled={loading === "pro_bundle"}>
          {loading === "pro_bundle" ? "Redirecting…" : "Buy Bundle"}
        </button>
      </div>

      {canceled && (
        <p className="mono" style={{ color: "#ff7b7b", marginTop: 10 }}>
          Checkout canceled.
        </p>
      )}
      {err && (
        <p className="mono" style={{ color: "#ff7b7b", marginTop: 10 }}>
          Error: {err}
        </p>
      )}

      {/* BTC path (disabled until BTCPay is wired)
      <div className="card">
        <h3 style={{ marginTop: 0 }}>Bitcoin (BTCPay) — one‑time</h3>
        <p className="muted">Coming soon.</p>
      </div>
      */}
    </section>
  );
}
