import { useEffect, useRef, useState } from "react";
const DEV_KEY = import.meta.env.VITE_DEV_PRO_KEY;
const IS_LOCAL = (typeof window !== "undefined") && /^(localhost|127\.0\.0\.1)(:\d+)?$/.test(window.location.host);

// Rolls‑Royce key modal — in‑memory only, CSP‑safe, accessible.
// Props: open:boolean, onClose:() => void, onSet:(key:string)=>void
export default function KeyModal({ open = false, onClose = () => {}, onSet = () => {} }) {
  const [k, setK] = useState(""); const inputRef = useRef(null);

  useEffect(() => {
    if (open) {
      setK("");
      const t = setTimeout(() => { inputRef.current?.focus(); }, 0);
      return () => clearTimeout(t);
    }
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow; document.body.style.overflow = "hidden";
    return () => { document.removeEventListener("keydown", onKey); document.body.style.overflow = prev; };
  }, [open, onClose]);

  if (!open) return null;
  const save = () => { const val = (k || "").trim(); if (typeof window !== "undefined") window.__DHK_API_KEY = val; try { onSet(val); } catch(_) {} onClose(); };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="absolute inset-0" onClick={onClose} aria-hidden="true" />
      <div role="dialog" aria-modal="true" aria-labelledby="dhk-key-title"
           className="relative z-10 w-[90%] max-w-md rounded-lg border border-white/10 bg-black/85 p-5 shadow-2xl backdrop-blur">
        <h2 id="dhk-key-title" className="text-lg font-semibold tracking-tight">Enter Pro API Key</h2>
        <p className="mt-1 text-sm opacity-70">
          Stored in memory only for this tab. Refresh clears it. {IS_LOCAL && DEV_KEY ? "Dev key detected." : ""}
        </p>
        <div className="mt-4">
          <input ref={inputRef} type="password" inputMode="text" autoComplete="off" spellCheck="false"
                 className="w-full px-3 py-2 rounded bg-white/5 border border-white/10 focus:outline-none"
                 placeholder={IS_LOCAL && DEV_KEY ? `Dev key: ${DEV_KEY}` : "Enter your Pro API key"}
                 value={k}
                 onChange={(e) => setK(e.target.value)}
                 aria-label="Pro API key input"
          />
        </div>
        <div className="mt-5 flex justify-end gap-3">
          <button type="button" onClick={onClose}
                  className="px-4 py-2 rounded border border-white/20 hover:border-white/40 focus:outline-none">
            Cancel
          </button>
          <button type="button" onClick={save} disabled={!k.trim()}
                  className="px-4 py-2 rounded bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 focus:outline-none">
            Save
          </button>
        </div>
      </div>
    </div>
  );
}