"""
services/faq_content.py

WHY THIS FILE EXISTS:
Keeping the actual FAQ questions/answers in their own file (separate from
the conversation-flow logic in message_handler.py) means updating an
answer -- or adding a new FAQ -- never requires touching the conversation
code itself. Just edit the dictionary below.

This is intentionally STATIC content, not AI-generated. Phase 9 will add a
real AI assistant for open-ended questions this list doesn't cover; this
FAQ menu exists for fast, reliable, always-correct answers to the most
common questions, without depending on an AI call.
"""

FAQ_MENU = {
    "1": (
        "Coverage Areas",
        "We currently serve select estates and neighborhoods across Abuja. "
        "Reply with your address during registration and our team will "
        "confirm if you're within our coverage area.",
    ),
    "2": (
        "Installation Process",
        "Once you register and select a plan, our installation team will "
        "contact you within 24-48 hours to schedule a visit. Installation "
        "is free with all plans and typically takes 1-2 hours on-site work.",
    ),
    "3": (
        "Pricing & Plans",
        "We offer 7 plans from Starter (6Mbps) to Platinum (100Mbps), all "
        "with unlimited data and no hidden fees. Reply '3' from the main "
        "menu to see current pricing and subscribe.",
    ),
    "4": (
        "Business Hours",
        "Our support team is available Monday-Saturday, 8am-6pm WAT. "
        "This WhatsApp bot is available 24/7 for registration, complaints, "
        "and account info.",
    ),
    "5": (
        "Payment & Billing",
        "Subscriptions are billed monthly. You can renew or change your "
        "plan anytime by replying '3' from the main menu. Payment options "
        "will be available directly through this chat soon.",
    ),
    "6": (
        "Refund Policy",
        "Installation fees are non-refundable once a technician has been "
        "dispatched. Subscription payments are non-refundable but unused "
        "days carry over if you renew before your plan expires.",
    ),
    "7": (
        "Compensation Policy",
        "once a downtime exceede 24 hours all affected client will be compensated for 2 Days.",
    )
}


def format_faq_menu() -> str:
    lines = [f"{key}. {title}" for key, (title, _) in FAQ_MENU.items()]
    return "\n".join(lines)