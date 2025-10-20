# DHK Align — Privacy Policy & Notice (Oct 2025)

_Single, authoritative privacy document for DHK Align. This reflects current production behavior across the Cloudflare **Edge** (Worker), private **Origins** on Fly.io (FastAPI + Go sidecar), and the Cloudflare Pages frontend._

---

## 0) Our Privacy Commitment

- **Privacy‑first**: We design for minimum server‑side data.  
- **Edge‑only ingress**: Clients call the **Cloudflare Worker**; only the Worker calls private origins with an internal header `x‑edge‑shield`. Clients **never** send this header.  
- **No server‑side content retention** (default): We do **not** persist translation text on the server. The browser may cache results locally for speed.

> **Optional exception — Pro fallback**: On a DB miss, the origin may call a model (e.g., `gpt‑4o‑mini`). To avoid repeat cost/latency, we store **only the minimal pair** (input text + model output + langs; `pack=auto`) into the **pro dataset**. No user identifiers. You may request deletion (see §7).

---

## 1) What we collect (and don’t)

### We **do not** collect by default
- ❌ Translation text stored server‑side (see fallback exception above)  
- ❌ Fingerprints or unique device IDs  
- ❌ Third‑party advertising trackers/pixels  
- ❌ Social widgets/beacons  
- ❌ Behavior analytics (off by default)

### Minimal data we **do** process

- **Security events (all tiers)** — tamper‑evident, local security/audit logs (append‑only JSONL).  
  **What**: event kind (bad request, rate‑limited, auth fail), IP, timestamp, route.  
  **What not**: no translation text; no user IDs.  
  **Where**: local file `private/audit/security.jsonl` (HMAC‑signed). Not in Edge KV.  
  **Retention**: **≤ 90 days**, then rotate/offline.

- **Edge counters (KV)** — per‑key/day usage for quotas; no content; keys auto‑expire (**~30–35 days**).

- **Billing (Pro/Lifetime)** — via Stripe/BTCPay: event IDs, timestamps, plan status; optional email from Stripe for receipts/support. **We never see card numbers.**

- **Account metadata (if you create one)** — email, subscription status, API‑key metadata (plan, issuedAt), last login timestamp.

- **Local device storage (your browser)** — preferences, recent translations cache, optional stored API key; fully under your control.

---

## 2) Where processing happens

- **Edge**: Cloudflare Worker — request handling, quotas, cache.  
- **Origins (private)**: Fly.io — **FastAPI** (prod origin), **Go sidecar** (parity `/go/*`, parked by default).  
- **Frontend**: Cloudflare Pages SPA.

Origins are never called directly by clients; the Worker authenticates with `x‑edge‑shield`.

---

## 3) How we use data

- **Operate the service**: authenticate, enforce quotas/rate‑limits, translate, serve cached results.  
- **Security**: detect abuse (quota exceed, replay, invalid signatures), protect origin (shield + WAF).  
- **Billing**: process Stripe/BTCPay events; mint/activate API keys after checkout.  
- **Support**: respond to user inquiries.

### Legal bases (GDPR)
- **Contract necessity** — providing the service, issuing/validating API keys after payment.  
- **Legitimate interests** — abuse prevention and reliability (minimal logs, short retention).  
- **Consent** — only if you explicitly enable optional analytics in the future (off by default).

---

## 4) Data retention (harmonized)

| Data category | Retention | Notes |
|---|---:|---|
| Edge usage counters (KV) | ~30–35 days | per‑day keys auto‑expire |
| `session_to_key:<sessionId>` (billing handoff) | 7 days (or on first read) | deleted at first successful `/billing/key` |
| Stripe replay locks | 90 days | replay protection |
| API‑key enable flags/metadata | active + 30 days | then archived/removed |
| **Security/audit logs** (local) | **≤ 90 days** | HMAC‑signed, no text |
| Origin request logs (debug, if enabled) | ≤ 30 days | off by default |
| Optional analytics (if ever enabled) | 90 days | anonymous aggregates |
| Feedback (user‑initiated) | up to 5 years | manual review → improvement |
| Backups | BC/DR only | encrypted snapshots; periodic purge |

We bias to shorter retention where feasible.

---

## 5) Sharing & processors

- **Cloudflare** — edge execution, KV, transport security.  
- **Stripe / BTCPay** — payments and webhooks (no card data to us).  
- **Email provider** — support/receipts (if you contact us).

We do **not** sell or share data with advertisers or data brokers.

---

## 6) International transfers

We limit what we store and use standard contractual protections when required. Edge processing can occur globally; origins run in Fly.io regions we select.

---

## 7) Your rights & controls

- **Access/Deletion/Portability** — email **privacy@dhkalign.com** from your billing email or include your API key.  
- **Pro fallback deletions** — send the text + approximate timestamp; we’ll remove matching pairs from the pro dataset.  
- **Opt‑out** — any optional analytics are opt‑in; disable at any time.  
- **Free tier** — no account required; local cache is under your control (browser settings).

Reasonable verification (receipt or API‑key ownership) may be required.

---

## 8) Cookies & local storage

- No marketing cookies.  
- The client may store your API key, preferences, and recent translations **locally**. Clear via browser settings or in‑app “Clear cache”.

---

## 9) Children

Not directed to children under 13 (or under 16 in the EU). Do not use the service if below the applicable age of digital consent.

---

## 10) Security measures (summary)

- **Private origin** behind Worker; internal shield (`x‑edge‑shield`).  
- **API key** for `/translate/pro`; **admin key** for `/admin/*`.  
- **Quotas** per key at Edge; optional IP rate‑limits at origin.  
- **CORS** allowlist; strict security headers (CSP, HSTS, etc.).  
- **Stripe replay protection** (timestamp tolerance + KV dedupe).  
- **Least data**: minimize logs; avoid text storage by default.

> See `docs/PROPERTY_DEFENSE.md` and `docs/OPS.md` for incident runbooks and ops details.

---

## 11) Changes & contact

If we materially change this policy, we will update this page (and provide reasonable advance notice for substantive changes).

**Contacts**  
- Privacy/DPO: **privacy@dhkalign.com**  
- Security/Ops: **admin@dhkalign.com**  
- General: **info@dhkalign.com**