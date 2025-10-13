


import { useEffect, useRef, useState } from "react";

const DEV_KEY = import.meta.env.VITE_DEV_PRO_KEY;
const IS_LOCAL = (typeof window !== "undefined") && /^(localhost|127\.0\.0\.1)(:\d+)?$/.test(window.location.host);

// Rolls‑Royce key modal — in‑memory only, CSP‑safe, accessible.
// Props: open:boolean, onClose:() => void, onSet:(key:string)=>void
export default function KeyModal({ open = false, onClose = () => {}, onSet = () => {} }) {
  const [k, setK] = useState("");
  const inputRef = useRef(null);
  const firstBtnRef = useRef(null);

  // Reset field and focus when opening
  useEffect(() => {
    if (open) {
      setK("");
      const t = setTimeout(() => {
        inputRef.current?.focus();
      }, 0);
      return () => clearTimeout(t);
    }
  }, [open]);

  // Escape to close; lock body scroll while open
  useEffect(() => {
    if (!open) return;
    const onKey = (e) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [open, onClose]);

  if (!open) return null;

  const save = () => {
    const val = (k || "").trim();
    // In‑memory only; no persistence
    if (typeof window !== "undefined") window.__DHK_API_KEY = val;
    try { onSet(val); } catch (_) {}
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      {/* Click outside to close */}
      <div className="absolute inset-0" onClick={onClose} aria-hidden="true" />

      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="dhk-key-title"
        className="relative z-10 w-[90%] max-w-md rounded-lg border border-white/10 bg-black/85 p-5 shadow-2xl backdrop-blur"
      >
        <h2 id="dhk-key-title" className="text-lg font-semibold tracking-tight">
          Enter Pro API Key
        </h2>
        <p className="mt-1 text-sm opacity-70">
          Stored in memory only for this tab. Refresh clears it. {IS_LOCAL && DEV_KEY ? "Dev key detected." : ""}
        </p>

        <div className="mt-4">
          <input
            ref={inputRef}
            type="password"
            inputMode="text"
            autoComplete="off"
            spellCheck="false"
            className="w-full px-3 py-2 rounded bg-white/5 border border-white/10 focus:outline-none"
            placeholder="paste your key…"
            value={k}
            onChange={(e) => setK(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && save()}
            aria-label="Pro API Key"
          />
        </div>

        <div className="mt-4 flex justify-end gap-2">
          <button
            ref={firstBtnRef}
            type="button"
            className="px-3 py-1.5 rounded bg-white/10 hover:bg-white/20 focus:outline-none"
            onClick={onClose}
          >
            Cancel
          </button>
          {IS_LOCAL && DEV_KEY ? (
            <button
              type="button"
              className="px-3 py-1.5 rounded bg-white/10 hover:bg-white/20 focus:outline-none"
              title="Load the local dev key (in-memory only)"
              onClick={() => { setK(String(DEV_KEY || "")); setTimeout(() => save(), 0); }}
            >
              Use Dev Key
            </button>
          ) : null}
          <button
            type="button"
            className="px-3 py-1.5 rounded bg-white text-black focus:outline-none disabled:opacity-60"
            disabled={!k.trim()}
            onClick={save}
          >
            Save
          </button>
        </div>
      </div>
    </div>
  );
}