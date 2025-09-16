import { handleStripeWebhook } from './stripe.js';

export default {
  async fetch(request, env, ctx) {
    // CORS preflight
    if (request.method === 'OPTIONS') return cors();

    const url = new URL(request.url);

    // Stripe webhook route
    if (url.pathname === '/webhook/stripe' && request.method === 'POST') {
      return await handleStripeWebhook(request, env);
    }

    // Billing key fetch route
    if (url.pathname === '/billing/key' && request.method === 'GET') {
      const session_id = url.searchParams.get('session_id');
      if (!session_id) {
        return json({ error: 'missing session_id' }, 400);
      }
      const api_key = await env.USAGE.get('session_to_key:' + session_id);
      if (!api_key) {
        return json({ error: 'not found' }, 404);
      }
      return json({ api_key });
    }

    // --- Admin API key management (edge-handled, no forward) ---
    if (url.pathname.startsWith('/admin/keys/')) {
      if (request.headers.get('x-admin-key') !== env.ADMIN_KEY) {
        return json({ error: 'unauthorized' }, 401);
      }
      const k = url.searchParams.get('key') || '';
      if (!k) return json({ error: 'missing key' }, 400);
      const action = url.pathname.slice('/admin/keys/'.length);
      if (action === 'add')   { await env.USAGE.put('apikey:' + k, "1"); return json({ ok: true, key: k }); }
      if (action === 'del')   { await env.USAGE.delete('apikey:' + k);   return json({ ok: true, key: k }); }
      if (action === 'check') { const enabled = (await env.USAGE.get('apikey:' + k)) === "1"; return json({ key: k, enabled }); }
      return json({ error: 'unknown action' }, 400);
    }

    // Edge-only health
    if (url.pathname === '/edge/health') {
      return json({ status: 'ok', source: 'edge', time: new Date().toISOString() });
    }

    // Admin aggregate health (edge -> origin /health)
    if (url.pathname === '/admin/health') {
      const key = request.headers.get('x-admin-key');
      if (!key || key !== env.ADMIN_KEY) return json({ error: 'unauthorized' }, 401);
      let origin = { status: 'unknown' };
      try {
        const r = await fetch(new URL('/health', env.ORIGIN_BASE_URL), {
          headers: { 'x-edge-shield': env.EDGE_SHIELD_TOKEN }
        });
        origin = await safeJson(r);
        origin.status ||= r.ok ? 'ok' : 'error';
        origin.code = r.status;
      } catch (e) {
        origin = { status: 'down', error: String(e) };
      }
      return json({ status: 'ok', source: 'edge', origin, time: new Date().toISOString() });
    }

    // API key gating (edge): ONLY for /translate/pro
    const apiKeyHeader = request.headers.get('x-api-key');
    if (url.pathname.startsWith('/translate/pro')) {
      if (!apiKeyHeader) return json({ error: 'x-api-key required' }, 401);
      const ok = (await env.USAGE.get('apikey:' + apiKeyHeader)) === "1";
      if (!ok) return json({ error: 'invalid api key' }, 401);
    }

    // Caching decision
    const method = request.method.toUpperCase();
    const cacheable = url.pathname.startsWith('/translate') && (method === 'GET' || method === 'POST');
    const bypass = url.searchParams.get('cache') === 'no';

    // KV cache lookup
    let cacheKey = null;
    if (cacheable && !bypass) {
      cacheKey = await cacheKeyFrom(request);
      const hit = await env.CACHE.get(cacheKey);
      if (hit) {
        const obj = JSON.parse(hit);
        const bytes = Uint8Array.from(atob(obj.body_b64), c => c.charCodeAt(0));
        const res = new Response(bytes, { status: obj.status, headers: obj.headers });
        res.headers.set('CF-Cache-Edge', 'HIT');
        addCors(res.headers);
        return res;
      }
    }

    // Forward to origin with shield header
    const forwardUrl = new URL(url.pathname + url.search, env.ORIGIN_BASE_URL);
    const headers = new Headers(request.headers);
    headers.set('x-edge-shield', env.EDGE_SHIELD_TOKEN);
    headers.set('host', new URL(env.ORIGIN_BASE_URL).host);

    const init = {
      method: request.method,
      headers,
      body: ['GET', 'HEAD'].includes(method) ? undefined : await request.arrayBuffer(),
    };

    const originResp = await fetch(forwardUrl, init);
    const status = originResp.status;
    const respHeaders = new Headers(originResp.headers);
    addCors(respHeaders);
    const bodyArr = await originResp.arrayBuffer();
    const resp = new Response(bodyArr, { status, headers: respHeaders });

    // Async usage log (per API key per day; uses DEFAULT when none)
    const apiKeyForMeter = apiKeyHeader || env.DEFAULT_API_KEY || 'dev';
    ctx.waitUntil(logDailyUsage(env, apiKeyForMeter, url.pathname));

    // KV store on success
    if (cacheKey && status >= 200 && status < 300) {
      const ttl = parseInt(env.CACHE_TTL_SECONDS || '300', 10);
      const storeObj = {
        status,
        headers: Object.fromEntries(respHeaders.entries()),
        body_b64: btoa(String.fromCharCode(...new Uint8Array(bodyArr))),
      };
      ctx.waitUntil(env.CACHE.put(cacheKey, JSON.stringify(storeObj), { expirationTtl: ttl }));
      resp.headers.set('CF-Cache-Edge', 'MISS');
      resp.headers.set('Cache-Control', `public, max-age=${ttl}`);
    }

    return resp;
  }
};

// ---------- helpers ----------
function cors() { const h = new Headers(); addCors(h); return new Response(null, { headers: h }); }
function addCors(h) {
  h.set('Access-Control-Allow-Origin', '*');
  h.set('Access-Control-Allow-Methods', 'GET,POST,OPTIONS');
  h.set('Access-Control-Allow-Headers', 'Content-Type, x-api-key, x-admin-key');
}
function json(obj, status = 200) { const h = new Headers({ 'content-type': 'application/json' }); addCors(h); return new Response(JSON.stringify(obj), { status, headers: h }); }
async function safeJson(r) { try { return await r.json(); } catch { return { raw: await r.text() }; } }
async function cacheKeyFrom(request) {
  const url = new URL(request.url);
  const method = request.method.toUpperCase();
  let bodyHash = '';
  if (method === 'POST') {
    const buf = await request.clone().arrayBuffer();
    bodyHash = await sha256Hex(new Uint8Array(buf));
  }
  const base = `${method}:${url.pathname}?${url.searchParams}${bodyHash ? ':body=' + bodyHash : ''}`;
  return 'resp:' + await sha256Hex(new TextEncoder().encode(base));
}
async function sha256Hex(bytes) {
  const d = await crypto.subtle.digest('SHA-256', bytes);
  return [...new Uint8Array(d)].map(x => x.toString(16).padStart(2, '0')).join('');
}
async function logDailyUsage(env, apiKey, path) {
  try {
    const now = new Date();
    const day = now.toISOString().slice(0, 10);
    const key = `usage:${apiKey}:${day}`;
    const raw = await env.USAGE.get(key);
    let data = raw ? JSON.parse(raw) : { count: 0, last: null, paths: {} };
    data.count += 1;
    data.last = now.toISOString();
    data.paths[path] = (data.paths[path] || 0) + 1;
    await env.USAGE.put(key, JSON.stringify(data), { expirationTtl: 40 * 60 * 60 }); // ~40h
  } catch {}
}
