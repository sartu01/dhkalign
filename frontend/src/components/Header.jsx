import { useEffect, useState } from "react";

// DHK Align — Header (Rolls‑Royce, CSP‑safe)
// Props: onOpenKey?: () => void
export default function Header({ onOpenKey = () => {} }) {
  const [hasKey, setHasKey] = useState(false);

  // Optional: preload a DEV key on localhost only (never use real prod keys here).
  useEffect(() => {
    try {
      const isLocal =
        typeof window !== "undefined" &&
        /^(localhost|127\.0\.0\.1)(:\d+)?$/.test(window.location.host);
      const devKey = import.meta.env.VITE_DEV_PRO_KEY;
      if (isLocal && devKey && !window.__DHK_API_KEY) {
        window.__DHK_API_KEY = String(devKey);
      }
    } catch (_) {}
  }, []);

  // Track in‑memory key presence
  useEffect(() => {
    const read = () =>
      (typeof window !== "undefined" && window.__DHK_API_KEY && String(window.__DHK_API_KEY).trim().length > 0) ||
      false;
    setHasKey(read());
    // Poll lightly to catch changes from the modal without wiring global events
    const t = setInterval(() => setHasKey(read()), 800);
    return () => clearInterval(t);
  }, []);

  return (
    <header className="w-full border-b border-white/10">
      <div className="mx-auto max-w-5xl px-4 py-3 flex items-center justify-between">
        <a href="/" className="text-xl font-semibold tracking-tight">DHK Align</a>
        <nav className="flex items-center gap-3">
          <span
            className={
              "text-xs px-2 py-1 rounded border " +
              (hasKey
                ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
                : "border-white/10 bg-white/5 text-white/80")
            }
            title={hasKey ? "Pro key loaded in memory" : "Free mode (no key)"}
          >
            {hasKey ? "Pro" : "Free"}
          </span>
          <button
            type="button"
            onClick={onOpenKey}
            className="text-sm px-3 py-1.5 rounded bg-white/10 hover:bg-white/20 focus:outline-none"
            title="Enter or replace your Pro API key (session‑only)"
          >
            Enter Pro Key
          </button>
        </nav>
      </div>
    </header>
  );
}