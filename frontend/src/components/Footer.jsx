

// DHK Align — Footer (Rolls‑Royce calm, CSP‑safe)
export default function Footer() {
  const y = new Date().getFullYear();
  return (
    <footer className="w-full border-t border-white/10 mt-12">
      <div className="mx-auto max-w-5xl px-4 py-6 text-sm opacity-80 flex flex-col md:flex-row items-start md:items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="font-medium">DHK Align</span>
          <span className="opacity-60">© {y}</span>
        </div>
        <nav className="flex items-center gap-4" aria-label="Footer navigation">
          <a className="hover:opacity-100 opacity-80" href="/">Home</a>
          <a className="hover:opacity-100 opacity-80" href="/privacy">Privacy</a>
          <a className="hover:opacity-100 opacity-80" href="/terms">Terms</a>
          <a className="hover:opacity-100 opacity-80" href="mailto:admin@dhkalign.com">Contact</a>
          <a className="hover:opacity-100 opacity-80" href="https://edge.dhkalign.com/version" target="_blank" rel="noreferrer">Status</a>
        </nav>
      </div>
    </footer>
  );
}