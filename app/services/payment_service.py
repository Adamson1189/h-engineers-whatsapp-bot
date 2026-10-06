"""
services/payment_service.py

WHY THIS FILE EXISTS:
Business logic for Paystack payments -- generating a unique payment
reference, asking Paystack to create a payment link, verifying a payment
actually succeeded, and recording it against a Subscription.

HOW PAYSTACK'S FLOW WORKS (so the code below makes sense):
1. We call Paystack's "initialize transaction" API with an amount and a
   unique reference WE generate. Paystack returns a checkout URL.
2. We send that URL to the customer on WhatsApp. They open it, pay with a
   card (or bank transfer, etc.) on Paystack's own secure page -- we never
   see or handle card details ourselves, which is exactly what we want.
3. Paystack confirms success two ways, and we use BOTH for reliability:
   a) A webhook call to OUR server (routers/paystack.py) the moment payment
      completes -- fast, but webhooks can occasionally be missed/delayed.
   b) We can also actively "verify" a specific reference by calling
      Paystack's API directly, as a reliable fallback/double-check.

WHY AMOUNTS ARE MULTIPLIED BY 100:
Paystack's API works in the smallest currency unit (kobo for NGN, the same
idea as cents for USD) to avoid floating-point rounding bugs with money.
Our database stores whole Naira (e.g. 16909.00), so we convert at the
boundary -- multiply by 100 going OUT to Paystack, divide by 100 coming
back IN, keeping our own database values in human-readable Naira.
"""

import hashlib
import hmac
import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import httpx

from app.config import get_settings
from app.db.models import Payment, PaymentMethod, PaymentStatus, Subscription

logger = logging.getLogger(__name__)

settings = get_settings()

PAYSTACK_BASE_URL = "https://api.paystack.co"


def generate_payment_reference() -> str:
    """
    A unique reference WE control, sent to Paystack and later used to look
    up this specific transaction. Using our own prefix (NF-PAY-) makes it
    instantly recognizable as ours in Paystack's dashboard among many
    businesses' transactions.
    """
    return f"NF-PAY-{uuid.uuid4().hex[:12].upper()}"


async def initialize_transaction(subscription: Subscription, customer_email: str | None, customer_phone: str) -> dict:
    """
    Asks Paystack to create a payment session for this subscription's
    current balance. Returns Paystack's response, which includes
    `authorization_url` (the link to send the customer) if successful.

    WHY A FALLBACK EMAIL: Paystack's API requires an email address, but our
    customers register via WhatsApp and may not have provided one (it's
    optional in our registration flow). Rather than block payment entirely,
    we build a placeholder from their phone number -- Paystack only uses
    this for its own receipt email, it doesn't need to be a real inbox we
    control.
    """
    email = customer_email or f"{customer_phone}@netfiber-customer.placeholder"
    reference = generate_payment_reference()
    amount_kobo = int(subscription.balance * 100)

    headers = {
        "Authorization": f"Bearer {settings.paystack_secret_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "email": email,
        "amount": amount_kobo,
        "reference": reference,
        "metadata": {"subscription_id": subscription.id, "customer_phone": customer_phone},
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{PAYSTACK_BASE_URL}/transaction/initialize", headers=headers, json=payload, timeout=10
        )

    data = response.json()
    if response.status_code != 200 or not data.get("status"):
        logger.error(f"Paystack initialize failed ({response.status_code}): {data}")
    return data


async def verify_transaction(reference: str) -> dict:
    """Asks Paystack directly whether a given reference actually succeeded.
    Used as a reliable fallback alongside the webhook."""
    headers = {"Authorization": f"Bearer {settings.paystack_secret_key}"}

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{PAYSTACK_BASE_URL}/transaction/verify/{reference}", headers=headers, timeout=10
        )

    return response.json()


def verify_webhook_signature(raw_body: bytes, signature_header: str | None) -> bool:
    """
    Confirms a webhook request genuinely came from Paystack, not an
    attacker who discovered our webhook URL and sent a fake "payment
    succeeded" request. Paystack signs every webhook with HMAC-SHA512
    using our secret key; we recompute that same signature ourselves and
    check it matches EXACTLY. hmac.compare_digest (rather than `==`) is
    used deliberately -- it compares in constant time, which prevents a
    timing-attack from gradually guessing the correct signature.
    """
    if not signature_header:
        return False
    computed = hmac.new(
        settings.paystack_secret_key.encode("utf-8"), raw_body, hashlib.sha512
    ).hexdigest()
    return hmac.compare_digest(computed, signature_header)


def record_successful_payment(db, subscription: Subscription, amount: float, reference: str) -> Payment:
    """
    Saves the Payment row and reduces the subscription's balance.
    `max(0, ...)` ensures balance never goes negative even if a payment
    somehow exceeds what was owed (e.g. a duplicate webhook delivery, or a
    slightly stale balance read) -- better to show ₦0 owed than a confusing
    negative number.
    """
    amount = Decimal(str(amount))
    payment = Payment(
        subscription_id=subscription.id,
        amount=amount,
        payment_method=PaymentMethod.PAYSTACK,
        reference=reference,
        status=PaymentStatus.SUCCESSFUL,
        paid_at=datetime.now(timezone.utc),
    )
    db.add(payment)
    subscription.balance = max(Decimal("0"), subscription.balance - amount)
    db.commit()
    db.refresh(payment)
    return payment
