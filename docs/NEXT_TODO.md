# Next To‑Do (Iron‑Clad Phase)

## 1) Edge Shield (Cloudflare Worker + KV)
```bash
mkdir -p gateway
cat > gateway/worker.js <<'JS'
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (!url.hostname.endsWith("dhkalign.com")) return new Response("Forbidden", { status: 403 });
    const ua = request.headers.get("user-agent") || "";
    if (!ua || /bot|curl|python-requests|wget/i.test(ua)) return new Response("Denied", { status: 403 });
    const allowed = ["/health", "/translate", "/translate/pro"];
    if (!allowed.includes(url.pathname)) return new Response("Not Found", { status: 404 });
    const ip = request.headers.get("CF-Connecting-IP") || "unknown";
    const bucket = Math.floor(Date.now() / 60000);
    const key = `rate:${ip}:${bucket}`;
    const raw = await env.KV.get(key);
    const count = parseInt(raw || "0", 10);
    const LIMIT = url.pathname === "/translate/pro" ? 300 : 100;
    if (count >= LIMIT) return new Response("Too many requests", { status: 429 });
    await env.KV.put(key, String(count + 1), { expirationTtl: 90 });
    const backend = env.BACKEND_BASE;
    return fetch(backend + url.pathname, { method: request.method, headers: request.headers, body: request.method === "POST" ? request.body : null });
  }
}
JS
cat > gateway/wrangler.toml <<'TOML'
name = "dhkalign-core"
main = "gateway/worker.js"
compatibility_date = "2025-08-23"
kv_namespaces = [{ binding = "KV", id = "REPLACE_WITH_YOUR_KV_ID" }]
[vars]
BACKEND_BASE = "https://REPLACE_WITH_YOUR_PRIVATE_ORIGIN"
TOML

