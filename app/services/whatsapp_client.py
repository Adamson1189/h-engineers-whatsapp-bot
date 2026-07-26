"""
services/whatsapp_client.py

WHY THIS FILE EXISTS:
Every place in our app that needs to SEND a WhatsApp message (greeting,
menu, confirmation, notification, AI reply) needs the same boilerplate:
build the right URL, attach the access token, format the JSON body Meta
expects. Instead of repeating that in every router, we centralize it here.
If Meta changes their API version or we switch to a permanent token later,
we only update this ONE file.
"""

import logging

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

GRAPH_API_VERSION = "v21.0"


async def send_text_message(to: str, body: str) -> dict:
    """
    Sends a plain text WhatsApp message.

    Args:
        to: recipient's phone number in international format, no "+" or
            spaces, e.g. "2348012345678"
        body: the text to send

    Returns:
        The parsed JSON response from Meta (contains a message ID on success).
    """
    if not settings.whatsapp_token or not settings.whatsapp_phone_number_id:
        logger.error(
            "Cannot send WhatsApp message: WHATSAPP_TOKEN or "
            "WHATSAPP_PHONE_NUMBER_ID is not configured in .env"
        )
        return {"error": "WhatsApp credentials not configured"}

    url = (
        f"https://graph.facebook.com/{GRAPH_API_VERSION}/"
        f"{settings.whatsapp_phone_number_id}/messages"
    )

    headers = {
        "Authorization": f"Bearer {settings.whatsapp_token}",
        "Content-Type": "application/json",
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body},
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload, timeout=10)

    if response.status_code != 200:
        # We log the failure but don't crash the webhook over it — a failed
        # outbound message shouldn't take down message receiving.
        logger.error(f"WhatsApp send failed ({response.status_code}): {response.text}")
    else:
        logger.info(f"WhatsApp message sent to {to}")

    return response.json()
