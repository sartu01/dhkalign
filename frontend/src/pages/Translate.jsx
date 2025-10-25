import React, { useState } from "react";

const EDGE = "https://edge.dhkalign.com";       // free path: DB lookup
const BACKEND = "https://backend.dhkalign.com"; // pro path: server adds x-api-key
const MAX_Q_LEN = 256;

export default function Translate() {
  const [q, setQ] = useState("Rickshaw pabo na");
  const [loading, setLoading] = useState(false);
  const [out, setOut] = useState(null);
  const [err, setErr] = useState(null);
  const [pro, setPro] = useState(false);
  const [result, setResult] = useState("");
  const abortRef = React.useRef(null);

  async function run(e) {
    e?.preventDefault?.();
    const text = (q || "").trim().slice(0, MAX_Q_LEN);
    if (!text) return;

    // cancel any in‑flight request when a new one starts
    if (abortRef.current) {
      try { abortRef.current.abort(); } catch {}
    }
    abortRef.current = new AbortController();
    const signal = abortRef.current.signal;

    const pickAnswer = (j) => j?.tgt_text || j?.translation || j?.data || "";

    setLoading(true);
    setErr(null);
    setOut(null);

    try {
      if (pro) {
        // PRO path: call backend proxy; backend injects x-api-key + optional Turnstile
        const headers = {
          accept: "application/json",
          "content-type": "application/json",
        };
        // if you later wire a Turnstile widget, forward its token
        if (typeof window !== "undefined" && window.__DHK_TURNSTILE) {
          headers["x-turnstile"] = window.__DHK_TURNSTILE;
        }
        const res = await fetch(`${BACKEND}/api/pro-translate`, {
          method: "POST",
          headers,
          body: JSON.stringify({ q: text }),
          signal,
        });
        const json = await res.json().catch(() => ({ detail: "bad_json" }));
        if (!res.ok) throw new Error(json?.detail || `PRO request failed (${res.status})`);
        const ans = pickAnswer(json);
        if (typeof ans === "string") {
          setResult(ans);
        } else if (ans && typeof ans === "object") {
          // best effort stringify for nested structures
          try { setResult(JSON.stringify(ans)); } catch { setResult(""); }
        } else {
          setResult("");
        }
        setOut(json);
      } else {
        // FREE path: fast DB lookup via Edge
        const url = new URL(`${EDGE}/api/translate`);
        url.searchParams.set("q", text);
        const res = await fetch(url.toString(), { headers: { accept: "application/json" }, signal });
        const json = await res.json().catch(() => ({ detail: "bad_json" }));
        if (!res.ok) throw new Error(json?.detail || `FREE request failed (${res.status})`);
        const ans = pickAnswer(json);
        if (typeof ans === "string") {
          setResult(ans);
        } else if (ans && typeof ans === "object") {
          // best effort stringify for nested structures
          try { setResult(JSON.stringify(ans)); } catch { setResult(""); }
        } else {
          setResult("");
        }
        setOut(json);
      }
    } catch (ex) {
      setErr(ex?.message || "Network error");
      setResult("");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="card">
      <h3 style={{ marginTop: 0 }}>Translate</h3>
      <form onSubmit={run}>
        <div className="row">
          <input
            type="text"
            value={q}
            onChange={(e) => { setQ(e.target.value); if (err) setErr(null); }}
            placeholder="Type Banglish or English…"
            aria-label="Phrase"
            maxLength={MAX_Q_LEN}
          />
          <button disabled={loading || !q.trim()} type="submit">
            {loading ? "Translating…" : "Translate"}
          </button>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 10 }}>
          <label className="muted" style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
            <input
              type="checkbox"
              checked={pro}
              onChange={(e) => setPro(e.target.checked)}
              aria-label="Use Pro route"
            />
            Use Pro route (server‑side key)
          </label>
          {!pro ? (
            <span className="muted">Free path: Edge DB lookup</span>
          ) : (
            <span className="muted">Pro path: Backend → Edge (GPT fallback)</span>
          )}
        </div>
      </form>

      {err && (
        <p className="mono" style={{ color: "#ff7b7b", marginTop: 10 }}>
          Error: {err}
        </p>
      )}

      {result && (
        <div className="card" style={{ marginTop: 12 }}>
          <div className="muted" style={{ fontSize: 12, marginBottom: 6 }}>Result</div>
          <div style={{ fontSize: 18 }}>{result}</div>
        </div>
      )}

      {out && (
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
{JSON.stringify(out, null, 2)}
        </pre>
      )}

      {!out && !err && (
        <p className="muted" style={{ marginTop: 10 }}>
          Calls <span className="mono">/api/translate</span> (free via Edge) or
          <span className="mono"> /api/pro-translate</span> (Pro via Backend → Edge).
        </p>
      )}

      {q.length > MAX_Q_LEN && (
        <p className="muted" style={{ marginTop: 8 }}>Query truncated to {MAX_Q_LEN} characters.</p>
      )}
    </section>
  );
}