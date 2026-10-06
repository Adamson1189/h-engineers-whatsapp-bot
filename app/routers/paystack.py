"""
routers/paystack.py

WHY THIS FILE EXISTS:
The other half of the payment flow -- this is where PAYSTACK talks to US,
the moment a customer finishes paying. Mirrors the shape of
routers/whatsapp.py: Meta calls our WhatsApp webhook when a message
arrives, Paystack calls THIS webhook when a payment completes.

SECURITY NOTE: unlike our WhatsApp webhook (which uses a shared verify
token checked once during setup), every single Paystack webhook call must
be signature-verified (see payment_service.verify_webhook_signature) --
otherwise anyone who finds this URL could fake a "payment succeeded"
request and get free service.
"""

import logging

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.db.models import Subscription
from app.db.session import get_db
from app.services import payment_service
from app.services.whatsapp_client import send_text_message

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/paystack")
async def receive_paystack_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Receives Paystack's payment events. We only act on `charge.success` --
    other event types (e.g. a failed charge) are logged but don't need
    action from us, since the customer simply never got a working payment
    link to begin with in that case.
    """
    raw_body = await request.body()
    signature = request.headers.get("x-paystack-signature")

    if not payment_service.verify_webhook_signature(raw_body, signature):
        logger.warning("Paystack webhook signature verification failed -- ignoring request.")
        # Returning 200 here (not 401) is deliberate: Paystack doesn't need
        # to know WHY we ignored it, and responding 200 to everything
        # prevents an attacker probing this endpoint from learning that
        # signature checking exists at all.
        return Response(status_code=200)

    payload = await request.json()
    event = payload.get("event")
    logger.info(f"Paystack webhook event: {event}")

    if event == "charge.success":
        data = payload.get("data", {})
        reference = data.get("reference")
        amount_kobo = data.get("amount", 0)
        amount_naira = amount_kobo / 100
        metadata = data.get("metadata", {})
        subscription_id = metadata.get("subscription_id")
        customer_phone = metadata.get("customer_phone")

        if subscription_id:
            subscription = db.get(Subscription, subscription_id)
            if subscription:
                payment_service.record_successful_payment(
                    db, subscription, amount=amount_naira, reference=reference
                )
                logger.info(f"Payment recorded: {reference} -- ₦{amount_naira} for subscription {subscription_id}")

                if customer_phone:
                    await send_text_message(
                        to=customer_phone,
                        body=(
                            "NETFIBER AI\npowered by H-Engineers Enterprise\n\n"
                            f"✅ Payment of ₦{amount_naira:,.0f} received!\n"
                            f"Remaining Balance: ₦{subscription.balance:,.0f}\n\n"
                            "Thank you for your payment. Reply 'menu' to see other options."
                        ),
                    )
            else:
                logger.error(f"Paystack webhook: subscription {subscription_id} not found.")
        else:
            logger.error(f"Paystack webhook: no subscription_id in metadata for reference {reference}")

    return Response(status_code=200)
