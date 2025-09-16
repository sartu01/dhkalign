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
