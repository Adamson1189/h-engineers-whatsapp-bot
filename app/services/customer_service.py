"""
services/customer_service.py

WHY THIS FILE EXISTS:
This is the business-logic layer for anything to do with Customers --
looking them up by phone number, generating their human-friendly customer
code, and creating new registrations. Routers (like whatsapp.py) call
these functions instead of writing raw database queries directly, which
keeps the webhook code focused on "what should we say back" rather than
"how do we query the database."
"""

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import AccountStatus, Customer


def get_customer_by_phone(db: Session, phone_number: str) -> Customer | None:
    """Looks up an existing customer by their WhatsApp phone number.
    Returns None if this is a new/unregistered number."""
    return db.query(Customer).filter(Customer.phone_number == phone_number).first()


def get_customer_by_email(db: Session, email: str) -> Customer | None:
    """Looks up an existing customer by email address (case-insensitive)."""
    return db.query(Customer).filter(func.lower(Customer.email) == email.lower().strip()).first()


def get_customer_by_code(db: Session, customer_code: str) -> Customer | None:
    """Looks up an existing customer by their Customer ID, e.g. 'NF-00001'
    (case-insensitive, and tolerant of the person forgetting the dash)."""
    normalized = customer_code.strip().upper().replace(" ", "")
    if not normalized.startswith("NF-") and normalized.startswith("NF"):
        normalized = "NF-" + normalized[2:]
    return db.query(Customer).filter(func.upper(Customer.customer_code) == normalized).first()


def generate_customer_code(db: Session) -> str:
    """
    Generates the next customer code in the form NF-00001, NF-00002, etc.

    WHY THIS APPROACH: we count existing customers and add 1, rather than
    using the database's own auto-increment `id` column directly, because
    we want a clean, branded, zero-padded code (NF-00001) instead of
    exposing the raw internal database ID to customers.
    """
    count = db.query(func.count(Customer.id)).scalar() or 0
    next_number = count + 1
    return f"NF-{next_number:05d}"


def create_customer(
    db: Session,
    phone_number: str,
    full_name: str,
    email: str | None,
    address: str | None,
) -> Customer:
    """
    Creates and saves a new Customer row.

    Note: coverage_area_id and subscription/plan linkage are intentionally
    left out here -- coverage-area matching and plan selection are separate
    pieces of logic we'll wire in as the registration flow grows. For now,
    a successfully registered customer starts with account_status=PENDING,
    reflecting that installation hasn't happened yet.
    """
    customer = Customer(
        customer_code=generate_customer_code(db),
        full_name=full_name,
        phone_number=phone_number,
        email=email,
        address=address,
        account_status=AccountStatus.PENDING,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer
