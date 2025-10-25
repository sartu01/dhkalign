

import os
import json
from typing import Optional, Dict
from fastapi import APIRouter, HTTPException, Request, Header
from pydantic import BaseModel, Field
import httpx

# Stripe is optional import; only required when price ids are configured
try:
    import stripe  # type: ignore
except Exception:  # pragma: no cover
    stripe = None

router = APIRouter()

# ----- Config / Env -----
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_PRICE_EVERYDAY = os.environ.get("STRIPE_PRICE_EVERYDAY", "")  # not used (free)
STRIPE_PRICE_SLANG = os.environ.get("STRIPE_PRICE_SLANG", "")
STRIPE_PRICE_DIALECTS = os.environ.get("STRIPE_PRICE_DIALECTS", "")
STRIPE_PRICE_PRO_BUNDLE = os.environ.get("STRIPE_PRICE_PRO_BUNDLE", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
TURNSTILE_SECRET = os.environ.get("TURNSTILE_SECRET", "")  # optional

PACK_PRICES: Dict[str, str] = {
    # "everyday": STRIPE_PRICE_EVERYDAY,  # everyday is free → no checkout
    "slang": STRIPE_PRICE_SLANG,
    "dialects": STRIPE_PRICE_DIALECTS,
    "pro_bundle": STRIPE_PRICE_PRO_BUNDLE,
}

if STRIPE_SECRET_KEY and stripe:
    stripe.api_key = STRIPE_SECRET_KEY


# ----- Models -----
class CheckoutBody(BaseModel):
    pack: str = Field(..., description="Which pack to buy: slang | dialects | pro_bundle (everyday is free)")
    success_url: str
    cancel_url: str


# ----- Helpers -----
async def verify_turnstile(token: Optional[str]) -> bool:
    """
    Validate Cloudflare Turnstile token if TURNSTILE_SECRET is configured.
    If not configured or token missing, we do NOT block (return True) to keep flow simple.
    Enable this after you wire the widget on the client.
    """
    if not TURNSTILE_SECRET:
        return True
    if not token:
        return False
    data = {"secret": TURNSTILE_SECRET, "response": token}
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            r = await client.post("https://challenges.cloudflare.com/turnstile/v0/siteverify", data=data)
        j = r.json()
        return bool(j.get("success") is True)
    except Exception:
        return False


# ----- Routes -----
@router.post("/api/billing/create-checkout-session")
async def create_checkout_session(
    body: CheckoutBody,
    x_turnstile: Optional[str] = Header(default=None, convert_underscores=False),
):
    """
    Create a one-time Stripe Checkout session for paid packs.
    - everyday: free → no checkout (400)
    - slang/dialects/pro_bundle: paid → redirect URL returned
    """
    # Optional bot gate
    ok = await verify_turnstile(x_turnstile)
    if not ok:
        raise HTTPException(status_code=401, detail="turnstile_failed")

    pack = body.pack.strip().lower()
    if pack == "everyday":
        raise HTTPException(status_code=400, detail="everyday_is_free")

    price_id = PACK_PRICES.get(pack, "")
    if not STRIPE_SECRET_KEY or not stripe or not price_id:
        raise HTTPException(status_code=500, detail="billing_not_configured")

    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            payment_method_types=["card"],  # Apple Pay shows automatically when eligible
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=body.success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=body.cancel_url,
            allow_promotion_codes=True,
        )
        return {"url": session.url}
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/billing/create-btcpay-invoice")
async def create_btcpay_invoice():
    """
    Placeholder for BTCPay. Implement once BTCPay server/store is ready.
    Return 501 for now.
    """
    raise HTTPException(status_code=501, detail="btcpay_not_configured")


class WebhookEvent(BaseModel):
    # keep flexible; we only check the type we care about
    id: Optional[str] = None
    type: Optional[str] = None
    data: Optional[dict] = None


@router.post("/api/billing/webhook")
async def stripe_webhook(request: Request):
    """
    Stripe webhook (optional now, more useful for subscriptions or delivery receipts).
    For one-time payments you may still store a receipt. This stub validates the
    signature when STRIPE_WEBHOOK_SECRET is set and returns ok.
    """
    payload = await request.body()
    if not STRIPE_WEBHOOK_SECRET:
        # Accept but do nothing; you can restrict by IP if you want later.
        return {"ok": True}

    sig = request.headers.get("stripe-signature")
    if not stripe or not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="stripe_not_available")
    try:
        event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=400, detail=f"Webhook error: {e}")

    # Handle event types you care about
    if event["type"] == "checkout.session.completed":
        sess = event["data"]["object"]
        # Example: extract basic info (email might be None if not collected)
        # email = sess.get("customer_details", {}).get("email")
        # pack metadata could be added later
        pass

    return {"ok": True}