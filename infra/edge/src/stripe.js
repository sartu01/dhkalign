<<<<<<< HEAD
// Stripe webhook handler for Cloudflare Workers (SDK-free, hardened with replay lock + tolerance)
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

  // Replay protection
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

  return j({ ok: true, data: { api_key: apiKey, plan } });
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
    if (!parsed.t || !parsed.v1.length) return { ok: false, error: "bad sig header" };

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
=======
// Stripe webhook handler for Cloudflare Workers without Stripe SDK

export async function handleStripeWebhook(request, env) {
  const sig = request.headers.get('stripe-signature');
  const body = await request.text();

  if (!sig) {
    return new Response('Missing stripe-signature header', { status: 400 });
  }

  const event = await verifyStripeSignature(body, sig, env.STRIPE_WEBHOOK_SECRET);
  if (!event) {
    return new Response('Invalid signature', { status: 400 });
  }

  // Replay protection: check if event id already processed
  const eventId = event.id;
  if (!eventId) {
    return new Response('Missing event id', { status: 400 });
  }

  const existing = await env.USAGE.get(eventId);
  if (existing) {
    // Event already processed
    return new Response('Event already processed', { status: 200 });
  }

  // Mark event as processed
  await env.USAGE.put(eventId, 'processed');

  if (event.type === 'checkout.session.completed') {
    const session = event.data.object;

    // Mint API key and store metadata
    const apiKey = crypto.randomUUID();

    // Store metadata in KV: for example, store by apiKey with customer info
    const metadata = {
      customerId: session.customer,
      sessionId: session.id,
      created: Date.now(),
      status: session.status,
      plan: session.display_items?.[0]?.plan?.id || null,
      issuedAt: Date.now(),
      issuedBy: 'stripe-webhook',
      eventId: event.id,
      email: session.customer_details?.email || null,
    };

    await env.USAGE.put(`apikey:${apiKey}`, JSON.stringify(metadata));

    // Store session to apiKey mapping with TTL 7 days
    await env.USAGE.put(`session_to_key:${session.id}`, apiKey, { expirationTtl: 7 * 24 * 60 * 60 });

    // Respond with minted API key
    return new Response(JSON.stringify({ apiKey }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  // For other event types, just acknowledge
  return new Response('Success', { status: 200 });
}

async function verifyStripeSignature(payload, header, secret) {
  const parsed = parseStripeSigHeader(header);
  if (!parsed) return null;

  const { t, signatures } = parsed;

  const signedPayload = `${t}.${payload}`;
  const expectedSignature = await hmacSHA256Hex(secret, signedPayload);

  for (const sig of signatures) {
    if (safeEqual(sig, expectedSignature)) {
      // Parse JSON payload to event object
      try {
        return JSON.parse(payload);
      } catch {
        return null;
      }
    }
  }

  return null;
}

function parseStripeSigHeader(header) {
  // Example header: t=timestamp,v1=signature,v1=signature2
  const parts = header.split(',');
  let t = null;
  const signatures = [];

  for (const part of parts) {
    const [key, value] = part.split('=');
    if (key === 't') {
      t = value;
    } else if (key === 'v1') {
      signatures.push(value);
    }
  }

  if (!t || signatures.length === 0) {
    return null;
  }

  return { t, signatures };
}

async function hmacSHA256Hex(key, msg) {
  const enc = new TextEncoder();
  const keyData = enc.encode(key);
  const msgData = enc.encode(msg);

  const cryptoKey = await crypto.subtle.importKey(
    'raw',
    keyData,
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  );

  const signature = await crypto.subtle.sign('HMAC', cryptoKey, msgData);
  return Array.from(new Uint8Array(signature))
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');
}

function safeEqual(a, b) {
  if (a.length !== b.length) {
    return false;
  }
  let result = 0;
  for (let i = 0; i < a.length; i++) {
    result |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return result === 0;
}
>>>>>>> origin/main
