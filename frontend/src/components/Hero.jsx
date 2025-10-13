import { useState } from "react";

// Real translator: Free uses DB via /api/translate; Pro uses GPT fallback via /translate/pro (x-api-key).
const EDGE_BASE = (import.meta.env.VITE_EDGE_BASE || "https://edge.dhkalign.com").replace(/\/+$/, "");

async function translateReal(q) {
  const key = (typeof window !== "undefined" && window.__DHK_API_KEY) ? String(window.__DHK_API_KEY) : "";
  const t0 = (typeof performance !== "undefined" && performance.now) ? performance.now() : Date.now();

  let resp;
  if (key) {
    // Pro path
    resp = await fetch(`${EDGE_BASE}/translate/pro`, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        "x-api-key": key
      },
      body: JSON.stringify({ text: q, src_lang: "bn-rom", tgt_lang: "en" })
    });
  } else {
    // Free path
    resp = await fetch(`${EDGE_BASE}/api/translate?q=${encodeURIComponent(q)}`, {
      headers: { "accept": "application/json" }
    });
  }

  const ms = Math.round(((typeof performance !== "undefined" && performance.now) ? performance.now() : Date.now()) - t0);
  let data = {};
  try { data = await resp.json(); } catch (_) {}
  return { status: resp.status, ms, data };
}

function pickResult(payload) {
  const d = payload?.data ?? payload ?? {};
  return d.result ?? d.translation ?? d.data?.result ?? d.data?.translation ?? "";
}

function pickCache(payload) {
  const d = payload?.data ?? payload ?? {};
  const v = (d.cache_hit ?? d.data?.cache_hit);
  return (v === true || v === "true");
}

export default function Hero() {
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [out, setOut] = useState(null); // {text, ms, cache, status, q}
  const [err, setErr] = useState("");

  const run = async (seed) => {
    const query = (typeof seed === "string" ? seed : q).trim();
    if (!query) return;
    setBusy(true); setErr(""); setOut(null);
    try {
      const r = await translateReal(query);
      const text = pickResult(r?.data);
      const cache = pickCache(r?.data);
      if (!text) setErr("No result returned. Try a different phrase.");
      else setOut({ text, ms: r.ms, cache, status: r.status, q: query });
    } catch (_) {
      setErr("Network error. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  const copy = async () => {
    if (!out?.text) return;
    try { await navigator.clipboard.writeText(out.text); } catch (_) {}
  };

  const samples = ["Rickshaw pabo na", "Bujhlam na", "Cholo bari jai", "Abar dekha hobe"];

  return (
    <section className="mx-auto max-w-5xl px-4 pt-10">
      <h1 className="text-3xl md:text-4xl font-semibold tracking-tight">Banglish ↔ English, distilled.</h1>
      <p className="mt-2 opacity-80 max-w-2xl">Real API. Free = DB. Pro = GPT fallback on miss.</p>

      <div className="mt-6 flex flex-col md:flex-row gap-3" role="group" aria-label="Translator">
        <input
          id="demo-input"
          className="flex-1 px-3 py-2 rounded bg-white/5 border border-white/10 focus:outline-none"
          placeholder="Type Banglish — e.g., ‘Rickshaw pabo na’"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && run()}
          aria-label="Enter phrase to translate"
        />
        <button
          type="button"
          disabled={busy}
          onClick={() => run()}
          className="px-4 py-2 rounded bg-white text-black disabled:opacity-60"
          aria-busy={busy}
        >
          {busy ? "Translating…" : "Translate"}
        </button>
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        {samples.map((s) => (
          <button key={s} type="button" onClick={() => run(s)}
            className="text-xs px-2 py-1 rounded bg-white/5 hover:bg-white/10 border border-white/10"
            aria-label={`Use sample: ${s}`}>
            {s}
          </button>
        ))}
      </div>

      {err && (
        <div className="mt-5 rounded border border-red-500/30 bg-red-500/10 p-3 text-sm">{err}</div>
      )}

      {out && (
        <div className="mt-5 rounded border border-white/10 bg-white/5 p-4">
          <div className="flex items-center justify-between">
            <div className="text-sm opacity-70">
              {out.cache ? "cache • fast" : "live • learning"} · {out.ms} ms · {out.status}
            </div>
            <button type="button" onClick={copy}
              className="text-xs px-2 py-1 rounded bg-white/10 hover:bg-white/20"
              aria-label="Copy translation">
              Copy
            </button>
          </div>
          <div className="mt-2 text-base leading-relaxed">{out.text}</div>
          <div className="mt-2 text-xs opacity-60">Query: <span className="opacity-80">{out.q}</span></div>
        </div>
      )}

      <div className="mt-6 text-xs opacity-60">
        Free mode uses DB. Enter a Pro key (session-only) to enable GPT fallback on misses.
      </div>
    </section>
  );
}