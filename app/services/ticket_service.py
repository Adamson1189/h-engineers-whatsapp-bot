"""
services/ticket_service.py

WHY THIS FILE EXISTS:
Business logic for Support Tickets -- generating human-friendly ticket
codes, creating tickets with an appropriate priority, and looking them up
for status tracking. Kept separate from customer_service.py since tickets
are their own concern, even though they reference a Customer.
"""

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import SupportTicket, TicketCategory, TicketPriority, TicketStatus

# WHY THIS MAPPING EXISTS: different complaint types have different real-world
# urgency. A total outage (no_internet) or a damaged fiber line (los_red)
# affects someone's ability to work/communicate right now, so those jump the
# queue ahead of a billing question. This mapping is what makes "assign a
# priority" automatic instead of requiring a human to triage every ticket.
CATEGORY_PRIORITY = {
    TicketCategory.NO_INTERNET: TicketPriority.URGENT,
    TicketCategory.LOS_RED: TicketPriority.URGENT,
    TicketCategory.SLOW_INTERNET: TicketPriority.MEDIUM,
    TicketCategory.WIFI_PROBLEM: TicketPriority.MEDIUM,
    TicketCategory.BILLING_ISSUE: TicketPriority.LOW,
    TicketCategory.OTHER: TicketPriority.MEDIUM,
}

# The numbered menu we show the customer, and what category/label each maps to.
CATEGORY_MENU = {
    "1": (TicketCategory.NO_INTERNET, "No Internet"),
    "2": (TicketCategory.SLOW_INTERNET, "Slow Internet"),
    "3": (TicketCategory.WIFI_PROBLEM, "Wi-Fi Problem"),
    "4": (TicketCategory.LOS_RED, "LOS Red"),
    "5": (TicketCategory.BILLING_ISSUE, "Billing Issue"),
    "6": (TicketCategory.OTHER, "New Complaint"),
}


def generate_ticket_code(db: Session) -> str:
    """Generates the next ticket code in the form TCK-00001, TCK-00002, etc."""
    count = db.query(func.count(SupportTicket.id)).scalar() or 0
    next_number = count + 1
    return f"TCK-{next_number:05d}"


def create_ticket(
    db: Session,
    customer_id: int,
    category: TicketCategory,
    description: str,
) -> SupportTicket:
    """Creates and saves a new SupportTicket, with priority auto-assigned
    based on category (see CATEGORY_PRIORITY above)."""
    ticket = SupportTicket(
        ticket_code=generate_ticket_code(db),
        customer_id=customer_id,
        category=category,
        description=description,
        priority=CATEGORY_PRIORITY.get(category, TicketPriority.MEDIUM),
        status=TicketStatus.OPEN,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


def get_ticket_by_code(db: Session, ticket_code: str) -> SupportTicket | None:
    """Looks up a ticket by its code, tolerant of case and missing dash,
    matching the same forgiving pattern as get_customer_by_code()."""
    normalized = ticket_code.strip().upper().replace(" ", "")
    if not normalized.startswith("TCK-") and normalized.startswith("TCK"):
        normalized = "TCK-" + normalized[3:]
    return db.query(SupportTicket).filter(func.upper(SupportTicket.ticket_code) == normalized).first()
