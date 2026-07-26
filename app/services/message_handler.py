"""
services/message_handler.py

WHY THIS FILE EXISTS:
This is where we decide WHAT TO SAY BACK based on: (1) what step of the
conversation this phone number is on, and (2) what they just typed. The
webhook router (routers/whatsapp.py) just extracts "who sent what" from
Meta's payload and hands it to `handle_incoming_message()` here -- all the
actual conversation logic lives in this one place, making it easy to find
and extend as we add more menu options in later phases.
"""

import logging

from sqlalchemy.orm import Session

from app.services import customer_service
from app.services.conversation_state import get_session, reset_session

logger = logging.getLogger(__name__)

BRAND_HEADER = "NETFIBER AI\npowered by H-Engineers Enterprise\n\n"

MAIN_MENU_TEXT = (
    "👋 Welcome! How can we help you today?\n\n"
    "1. Register\n"
    "2. Login\n"
    "3. Renew Subscription\n"
    "4. Report Complaint\n"
    "5. Track Complaint\n"
    "6. New Installation\n"
    "7. Talk to Customer Care\n"
    "8. FAQs\n\n"
    "Reply with a number to continue."
)


def handle_incoming_message(db: Session, phone_number: str, text: str) -> str:
    """
    The main entrypoint: given a phone number and the message they sent,
    return the text we should reply with. This function is deliberately
    synchronous and side-effect-light (aside from DB writes during
    registration) so it's easy to test without needing a real WhatsApp
    connection -- see the test suite for examples.
    """
    text = text.strip()
    session = get_session(phone_number)

    # Universal escape hatch: typing "menu" from anywhere jumps back to
    # the main menu and abandons whatever flow was in progress.
    if text.lower() == "menu":
        reset_session(phone_number)
        return BRAND_HEADER + MAIN_MENU_TEXT

    if session.step == "main_menu":
        return _handle_main_menu_choice(db, phone_number, text, session)

    if session.step.startswith("register_"):
        return _handle_registration_step(db, phone_number, text, session)

    # Fallback safety net: if we ever end up in an unrecognized step
    # (shouldn't happen, but defensive), reset rather than get the user
    # stuck in a broken state.
    reset_session(phone_number)
    return BRAND_HEADER + MAIN_MENU_TEXT


def _handle_main_menu_choice(db: Session, phone_number: str, text: str, session) -> str:
    """Handles the very first message, or a reply typed while at the main menu."""

    # A brand-new conversation, or anything that isn't a recognized menu
    # number, shows the menu (or shows it again).
    if text == "1":
        existing = customer_service.get_customer_by_phone(db, phone_number)
        if existing:
            return (
                BRAND_HEADER
                + f"You're already registered as {existing.full_name} "
                f"(Customer ID: {existing.customer_code}).\n\n"
                "Reply 'menu' to see other options."
            )
        session.step = "register_name"
        return BRAND_HEADER + "Great! Let's get you registered.\n\nWhat's your full name?"

    if text in {"2", "3", "4", "5", "6", "7", "8"}:
        # Phases 5-9 will implement each of these. For now, acknowledge
        # clearly rather than silently ignoring the choice.
        return (
            BRAND_HEADER
            + "This option is coming soon in a future update. "
            "Reply 'menu' to see other options."
        )

    # First-ever message, or unrecognized input -- show the menu.
    return BRAND_HEADER + MAIN_MENU_TEXT


def _handle_registration_step(db: Session, phone_number: str, text: str, session) -> str:
    """Walks through collecting: full name -> email -> address, then saves."""

    if session.step == "register_name":
        if len(text) < 2:
            return "That doesn't look like a full name. Please enter your full name:"
        session.data["full_name"] = text
        session.step = "register_email"
        return "Got it. What's your email address? (or reply 'skip' if you don't have one)"

    if session.step == "register_email":
        email = None if text.lower() == "skip" else text
        if email and "@" not in email:
            return "That doesn't look like a valid email. Please try again, or reply 'skip':"
        session.data["email"] = email
        session.step = "register_address"
        return "Thanks! What's your home/office address for installation?"

    if session.step == "register_address":
        session.data["address"] = text
        customer = customer_service.create_customer(
            db,
            phone_number=phone_number,
            full_name=session.data["full_name"],
            email=session.data.get("email"),
            address=session.data["address"],
        )
        reset_session(phone_number)
        logger.info(f"New customer registered: {customer.customer_code} ({phone_number})")
        return (
            BRAND_HEADER
            + f"🎉 Registration complete!\n\n"
            f"Your Customer ID is: {customer.customer_code}\n"
            f"Name: {customer.full_name}\n\n"
            "Our team will be in touch to schedule your installation. "
            "Reply 'menu' anytime to see other options."
        )

    # Shouldn't be reachable, but fall back safely.
    reset_session(phone_number)
    return BRAND_HEADER + MAIN_MENU_TEXT
