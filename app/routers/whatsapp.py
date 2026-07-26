"""
routers/whatsapp.py

WHY THIS FILE EXISTS:
This is the single door through which Meta's WhatsApp Cloud API talks to
our app. It has exactly two jobs, matching the two HTTP methods below:

1. GET  /webhook/whatsapp  -> Meta calls this ONCE, when you first configure
   the webhook URL in the App Dashboard. It's a handshake: Meta sends a
   "challenge" number and expects us to echo it back, PROVING we control
   this URL and know the shared verify token. If this doesn't match, Meta
   refuses to save the webhook.

2. POST /webhook/whatsapp  -> Meta calls this EVERY TIME a WhatsApp event
   happens (a customer sends a message, a message is delivered/read, etc.).
   This is where real conversation handling will live — for now we just log
   what arrives and send back a simple greeting, to prove the full loop
   (customer sends message -> Meta -> our server -> reply -> Meta -> customer)
   works end to end.
"""

import logging

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.session import get_db
from app.services.message_handler import handle_incoming_message
from app.services.whatsapp_client import send_text_message

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter()


@router.get("/whatsapp")
async def verify_webhook(
    hub_mode: str = Query(alias="hub.mode"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    hub_challenge: str = Query(alias="hub.challenge"),
):
    """
    Meta's one-time handshake. `Query(alias=...)` is needed because Meta
    sends parameters with dots in the name (hub.mode, hub.verify_token,
    hub.challenge), which aren't valid Python variable names, so we alias
    them to normal Python names underneath.
    """
    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token:
        logger.info("WhatsApp webhook verified successfully.")
        # Meta expects the raw challenge string back, NOT wrapped in JSON.
        return Response(content=hub_challenge, media_type="text/plain")

    logger.warning("WhatsApp webhook verification failed - token mismatch.")
    return Response(content="Verification failed", status_code=403)


@router.post("/whatsapp")
async def receive_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Receives every WhatsApp event: incoming messages, status updates
    (sent/delivered/read), etc. Meta's payload is deeply nested, so we
    carefully check each level exists before reading it -- a malformed or
    unexpected payload should never crash the webhook.
    """
    payload = await request.json()
    logger.info(f"Incoming WhatsApp webhook payload: {payload}")

    try:
        entry = payload["entry"][0]
        change = entry["changes"][0]
        value = change["value"]

        # `messages` is only present when a customer actually sent something
        # (it's absent for status-update pings like "delivered"/"read").
        if "messages" in value:
            message = value["messages"][0]
            from_number = message["from"]  # customer's WhatsApp number
            text_body = message.get("text", {}).get("body", "")

            logger.info(f"Message from {from_number}: {text_body}")

            reply = handle_incoming_message(db, from_number, text_body)
            await send_text_message(to=from_number, body=reply)

    except (KeyError, IndexError) as e:
        # Status updates and other event types won't match the shape above --
        # that's expected and NOT an error, just log it at debug level.
        logger.debug(f"Webhook payload did not contain a customer message: {e}")

    # Meta requires a 200 OK response quickly, or it will retry (and
    # eventually disable) the webhook. We always return 200 here even if we
    # didn't do anything with the payload above.
    return Response(status_code=200)
