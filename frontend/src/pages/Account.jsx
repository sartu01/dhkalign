

import React, { useEffect, useState } from "react";

const BACKEND = "https://backend.dhkalign.com";

export default function Account({ success = false }) {
  const [me, setMe] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState(null);

  async function load() {
    setLoading(true); setErr(null);
    try {
      const res = await fetch(`${BACKEND}/api/me`, {
        method: "GET",
        headers: { accept: "application/json" },
        // include credentials here if you later add auth cookies:
        // credentials: "include",
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json?.detail || "Failed to load account");
      setMe(json);
    } catch (ex) {
      setErr(ex?.message || "Network error");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  return (
    <section className="card">
      <h3 style={{ marginTop: 0 }}>Account</h3>

      {success && (
        <p className="mono" style={{ color: "#00e0d1" }}>
          Payment success — Pro will activate after webhook confirmation.
        </p>
      )}

      <div className="row" style={{ marginTop: 8 }}>
        <button type="button" onClick={load} disabled={loading}>
          {loading ? "Refreshing…" : "Refresh"}
        </button>
      </div>

      {err && (
        <p className="mono" style={{ color: "#ff7b7b", marginTop: 10 }}>
          Error: {err}
        </p>
      )}

      {me && (
        <div style={{ marginTop: 12 }}>
          <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
            <span className="badge">Plan</span>
            <strong className="mono">{me.plan || "free"}</strong>
          </div>
          <pre
            className="mono"
            style={{
              whiteSpace: "pre-wrap",
              marginTop: 12,
              background: "#0f0f15",
              padding: 12,
              borderRadius: 8,
              border: "1px solid #1f1f2a",
            }}
          >
{JSON.stringify(me, null, 2)}
          </pre>
        </div>
      )}

      {!me && !err && !loading && (
        <p className="muted" style={{ marginTop: 10 }}>
          No account data available.
        </p>
      )}
    </section>
  );
}