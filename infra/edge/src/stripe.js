// Stripe webhook handler for Cloudflare Workers (SDK-free, hardened)
export async function handleStripeWebhook(request, env) {
  const sig = request.headers.get("stripe-signature");
  if (!sig || !env.STRIPE_WEBHOOK_SECRET) {
    return j({ ok: false, error: "missing signature or secret" }, 400);
  }

  const raw = await request.text();

  // Verify signature with 5‑minute tolerance
  const verify = await verifyStripeSignature(raw, sig, env.STRIPE_WEBHOOK_SECRET, 300);
  if (!verify.ok) return j({ ok: false, error: "signature verification failed" }, 400);

  let event;
  try { event = JSON.parse(raw); } catch { return j({ ok: false, error: "invalid json" }, 400); }
  if (!event?.id) return j({ ok: false, error: "missing event id" }, 400);

  // Replay protection (KV)
  const replayKey = `stripe_evt:${event.id}`;
  if (await env.USAGE.get(replayKey)) return j({ ok: true, replay: true });

  if (event.type !== "checkout.session.completed") {
    await env.USAGE.put(replayKey, "ignored", { expirationTtl: 90 * 24 * 60 * 60 });
    return j({ ok: true, ignored: event.type });
  }

  const session = event.data?.object || {};
  const plan = session.metadata?.plan || "pro";
  const email = session.customer_details?.email || session.customer_email || "";
  const sessionId = session.id || "";

  // Optional guards: ignore unexpected modes or unpaid sessions
  const allowedModes = ["payment", "subscription", "setup"]; // adjust as needed
  if (session.mode && !allowedModes.includes(session.mode)) {
    await env.USAGE.put(replayKey, `ignored_mode:${session.mode}`, { expirationTtl: 90 * 24 * 3600 });
    return j({ ok: true, ignored: `mode:${session.mode}` });
  }
  // treat paid or no_payment_required or completed as acceptable
  const paid = session.payment_status === 'paid' || session.payment_status === 'no_payment_required' || session.status === 'complete';
  if (!paid) {
    await env.USAGE.put(replayKey, "ignored_unpaid", { expirationTtl: 90 * 24 * 3600 });
    return j({ ok: true, ignored: 'unpaid' });
  }

  // Mint API key
  const apiKey = crypto.randomUUID().replace(/-/g, "");

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
    email
  };
  await env.USAGE.put(`apikey.meta:${apiKey}`, JSON.stringify(meta));

  // 3) Session -> key mapping (7 days)
  if (sessionId) {
    await env.USAGE.put(`session_to_key:${sessionId}`, apiKey, { expirationTtl: 7 * 24 * 3600 });
  }

  // 4) Replay lock (90 days)
  await env.USAGE.put(replayKey, "processed", { expirationTtl: 90 * 24 * 3600 });

  // Do not echo the key to Stripe; clients fetch via /billing/key
  return j({ ok: true });
}

function j(obj, status = 200, headers = {}) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "content-type": "application/json", ...headers }
  });
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
  const key = await crypto.subtle.importKey("raw", enc.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const sig = await crypto.subtle.sign("HMAC", key, enc.encode(payload));
  const bytes = new Uint8Array(sig);
  return Array.from(bytes).map(b => b.toString(16).padStart(2, "0")).join("");
}
function safeEqual(a, b) { if (a.length !== b.length) return false; let r=0; for (let i=0;i<a.length;i++) r |= a.charCodeAt(i) ^ b.charCodeAt(i); return r===0; }
