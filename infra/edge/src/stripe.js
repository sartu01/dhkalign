// Stripe webhook handler for Cloudflare Workers (SDK-free, hardened)
export async function handleStripeWebhook(request, env) {
  const sig = request.headers.get("stripe-signature");
  if (!sig || !env.STRIPE_WEBHOOK_SECRET) {
    return j(false, null, "missing signature or secret", 400);
  }

  const raw = await request.text();

  // Verify Stripe signature with tolerance (5 min)
  const verify = await verifyStripeSignature(
    raw,
    sig,
    env.STRIPE_WEBHOOK_SECRET,
    300
  );
  if (!verify.ok) {
    return j(false, null, "signature verification failed", 400);
  }

  let event;
  try {
    event = JSON.parse(raw);
  } catch {
    return j(false, null, "invalid json", 400);
  }
  if (!event || !event.id) return j(false, null, "missing event id", 400);

  // Replay lock (KV)
  const replayKey = `stripe_evt:${event.id}`;
  const seen = await env.USAGE.get(replayKey);
  if (seen) return j(true, { replay: true });

  if (event.type !== "checkout.session.completed") {
    await env.USAGE.put(replayKey, "ignored", { expirationTtl: 90 * 24 * 3600 });
    return j(true, { ignored: event.type });
  }

  const session = event.data?.object || {};
  const rawPlan = (session.metadata?.plan || "pro").toLowerCase();
  const allowedPlans = new Set(["pro", "starter", "basic", "trial"]);
  const plan = allowedPlans.has(rawPlan) ? rawPlan : "pro";
  const email = (session.customer_details?.email || session.customer_email || "").slice(0, 320);
  const sessionId = session.id || "";

  // Optional guards: ignore unexpected modes or unpaid sessions
  const allowedModes = ["payment", "subscription", "setup"];
  if (session.mode && !allowedModes.includes(session.mode)) {
    await env.USAGE.put(replayKey, `ignored_mode:${session.mode}`, { expirationTtl: 90 * 24 * 3600 });
    return j(true, { ignored: `mode:${session.mode}` });
  }
  // treat paid or no_payment_required or completed as acceptable
  const paid = session.payment_status === 'paid' || session.payment_status === 'no_payment_required' || session.status === 'complete';
  if (!paid) {
    await env.USAGE.put(replayKey, "ignored_unpaid", { expirationTtl: 90 * 24 * 3600 });
    return j(true, { ignored: 'unpaid' });
  }

  // Mint API key
  const apiKey = crypto.randomUUID().replace(/-/g, "");

  try {
    // 1) Edge gate enable flag
    await env.USAGE.put(`apikey:${apiKey}`, "1");

    // 2) Metadata
    const meta = {
      status: "active",
      plan,
      issuedAt: new Date().toISOString(),
      issuedBy: "stripe",
      eventId: event.id,
      sessionId,
      email,
    };
    await env.USAGE.put(`apikey.meta:${apiKey}`, JSON.stringify(meta));

    // 3) Session -> key mapping (7 days)
    if (sessionId) {
      await env.USAGE.put(`session_to_key:${sessionId}`, apiKey, { expirationTtl: 7 * 24 * 3600 });
    }

    // 4) Replay lock (90 days)
    await env.USAGE.put(replayKey, "processed", { expirationTtl: 90 * 24 * 3600 });

    // Do not echo the key to Stripe; clients fetch via /billing/key
    return j(true, {});
  } catch (e) {
    // Minimal visibility in tail without leaking secrets
    console.warn("[stripe] KV write failed for", event.id, String(e));
    return j(false, null, "kv_write_failed", 500);
  }
}

// Standard JSON helper with CORS
function j(ok, data = null, error = null, status = 200, extraHeaders = {}) {
  const body = ok ? { ok: true, data } : { ok: false, error };
  const h = new Headers({ "content-type": "application/json", ...extraHeaders });
  // permissive CORS; Worker/router should still gate sensitive routes
  h.set('Access-Control-Allow-Origin', '*');
  h.set('Access-Control-Allow-Methods', 'GET,POST,OPTIONS');
  h.set('Access-Control-Allow-Headers', 'Content-Type, x-api-key, x-admin-key, stripe-signature');
  return new Response(JSON.stringify(body), { status, headers: h });
}

// --- signature verification with tolerance ---
async function verifyStripeSignature(rawBody, sigHeader, secret, toleranceSeconds) {
  try {
    const parsed = parseStripeSigHeader(sigHeader);
    if (!parsed.t || parsed.v1.length === 0) return { ok: false, error: "bad sig header" };

    const now = Math.floor(Date.now() / 1000);
    if (Math.abs(now - parsed.t) > toleranceSeconds) return { ok: false, error: "timestamp outside tolerance" };

    const payload = `${parsed.t}.${rawBody}`;
    const expected = await hmacSHA256Hex(secret, payload);
    const match = parsed.v1.some(v => safeEqual(v, expected));
    return match ? { ok: true } : { ok: false, error: "no matching signature" };
  } catch (e) {
    return { ok: false, error: e.message || String(e) };
  }
}

function parseStripeSigHeader(h) {
  const parts = String(h).split(",").map(x => x.trim());
  let t = null; const v1 = [];
  for (const p of parts) {
    const [k, v] = p.split("=", 2);
    if (k === "t") t = Number(v);
    if (k === "v1") v1.push(v);
  }
  return { t, v1 };
}

async function hmacSHA256Hex(secret, payload) {
  const enc = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    enc.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const sig = await crypto.subtle.sign("HMAC", key, enc.encode(payload));
  const bytes = new Uint8Array(sig);
  return Array.from(bytes).map(b => b.toString(16).padStart(2, "0")).join("");
}
function safeEqual(a, b) {
  if (a.length !== b.length) return false;
  let r = 0; for (let i = 0; i < a.length; i++) r |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return r === 0;
}
