"""
db/models.py

WHY THIS FILE EXISTS:
Every database table in this project is defined here as a Python class.
This is Batch 1 of Phase 2: CoverageArea, Plan, Customer, Subscription.
(Batch 2 will add Payments, SupportTickets, Engineers, Appointments,
ActivityLogs, Notifications on top of this foundation.)

READING GUIDE for each column type you'll see below:
- Column(Integer, primary_key=True)  -> auto-incrementing unique ID
- Column(String, nullable=False)      -> required text field
- Column(String, unique=True)         -> no two rows can share this value
- Column(ForeignKey("table.id"))      -> links this row to a row in another table
- relationship(...)                   -> lets us write `customer.subscriptions`
                                          in Python instead of writing a JOIN
                                          query by hand every time
"""

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import relationship

from app.db.session import Base


def utcnow():
    """Centralized helper so every timestamp default is consistent (UTC)."""
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# CoverageArea
# ---------------------------------------------------------------------------
class CoverageArea(Base):
    """
    Represents a geographic area H-Engineers services (or plans to).
    Used by the WhatsApp bot to answer "do you cover my area?" and to
    validate a customer's address during registration.
    """

    __tablename__ = "coverage_areas"

    id = Column(Integer, primary_key=True)
    area_name = Column(String(150), nullable=False)
    state = Column(String(100), nullable=False)
    lga = Column(String(100), nullable=True)  # Local Government Area
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    # One CoverageArea -> many Customers
    customers = relationship("Customer", back_populates="coverage_area")

    def __repr__(self):
        return f"<CoverageArea {self.area_name}, {self.state}>"


# ---------------------------------------------------------------------------
# Plan
# ---------------------------------------------------------------------------
class BillingCycle(str, enum.Enum):
    """
    WHY AN ENUM: this restricts billing_cycle to only these three exact
    values at the database level — no risk of a typo like "montly" sneaking
    into production data.
    """

    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


class Plan(Base):
    """A subscription tier customers can choose, e.g. '10Mbps Home'."""

    __tablename__ = "plans"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    speed_mbps = Column(Integer, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)  # Numeric, not Float — exact for money
    billing_cycle = Column(Enum(BillingCycle), nullable=False, default=BillingCycle.MONTHLY)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    subscriptions = relationship("Subscription", back_populates="plan")

    def __repr__(self):
        return f"<Plan {self.name} ({self.speed_mbps}Mbps) - {self.price}>"


# ---------------------------------------------------------------------------
# Customer
# ---------------------------------------------------------------------------
class AccountStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DEACTIVATED = "deactivated"


class Customer(Base):
    """The core entity — every registered ISP customer."""

    __tablename__ = "customers"

    id = Column(Integer, primary_key=True)
    customer_code = Column(String(20), unique=True, nullable=False)  # e.g. "NF-00001"
    full_name = Column(String(150), nullable=False)
    phone_number = Column(String(20), unique=True, nullable=False)  # WhatsApp number, our lookup key
    email = Column(String(150), nullable=True)
    address = Column(String(255), nullable=True)
    gps_latitude = Column(Float, nullable=True)
    gps_longitude = Column(Float, nullable=True)

    coverage_area_id = Column(Integer, ForeignKey("coverage_areas.id"), nullable=True)
    coverage_area = relationship("CoverageArea", back_populates="customers")

    account_status = Column(Enum(AccountStatus), nullable=False, default=AccountStatus.PENDING)
    registration_date = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    subscriptions = relationship("Subscription", back_populates="customer")

    def __repr__(self):
        return f"<Customer {self.customer_code} - {self.full_name}>"


# ---------------------------------------------------------------------------
# Subscription
# ---------------------------------------------------------------------------
class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"


class Subscription(Base):
    """
    Links a Customer to a Plan and tracks their billing state.
    `balance` is what the customer currently owes (positive) or has as
    credit (negative) — this is what powers the "check balance" feature.
    """

    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True)

    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    customer = relationship("Customer", back_populates="subscriptions")

    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False)
    plan = relationship("Plan", back_populates="subscriptions")

    start_date = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    expiry_date = Column(DateTime(timezone=True), nullable=False)
    status = Column(Enum(SubscriptionStatus), nullable=False, default=SubscriptionStatus.ACTIVE)

    # Positive = customer owes this much. Negative = customer has credit.
    balance = Column(Numeric(10, 2), nullable=False, default=0)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    def __repr__(self):
        return f"<Subscription customer={self.customer_id} plan={self.plan_id} status={self.status}>"
