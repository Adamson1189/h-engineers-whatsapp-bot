"""
db/models.py

WHY THIS FILE EXISTS:
Every database table in this project is defined here as a Python class.
Batch 1: CoverageArea, Plan, Customer, Subscription.
Batch 2 (added below): Engineer, Payment, SupportTicket, Appointment,
ActivityLog, Notification.

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
    Text,
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


# ---------------------------------------------------------------------------
# Engineer
# ---------------------------------------------------------------------------
class Engineer(Base):
    """
    Field staff who handle installations and support tickets.
    Referenced by SupportTicket.assigned_engineer and Appointment.engineer.
    """

    __tablename__ = "engineers"

    id = Column(Integer, primary_key=True)
    full_name = Column(String(150), nullable=False)
    phone_number = Column(String(20), unique=True, nullable=False)
    email = Column(String(150), nullable=True)
    specialization = Column(String(100), nullable=True)  # e.g. "fiber", "wireless", "CCTV"
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    tickets = relationship("SupportTicket", back_populates="assigned_engineer")
    appointments = relationship("Appointment", back_populates="engineer")

    def __repr__(self):
        return f"<Engineer {self.full_name}>"


# ---------------------------------------------------------------------------
# Payment
# ---------------------------------------------------------------------------
class PaymentMethod(str, enum.Enum):
    PAYSTACK = "paystack"
    BANK_TRANSFER = "bank_transfer"
    CASH = "cash"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCESSFUL = "successful"
    FAILED = "failed"


class Payment(Base):
    """A single payment made against a Subscription."""

    __tablename__ = "payments"

    id = Column(Integer, primary_key=True)

    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=False)
    subscription = relationship("Subscription", backref="payments")

    amount = Column(Numeric(10, 2), nullable=False)
    payment_method = Column(Enum(PaymentMethod), nullable=False, default=PaymentMethod.PAYSTACK)
    reference = Column(String(150), unique=True, nullable=True)  # Paystack transaction reference
    status = Column(Enum(PaymentStatus), nullable=False, default=PaymentStatus.PENDING)

    paid_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    def __repr__(self):
        return f"<Payment {self.amount} sub={self.subscription_id} status={self.status}>"


# ---------------------------------------------------------------------------
# SupportTicket
# ---------------------------------------------------------------------------
class TicketCategory(str, enum.Enum):
    NO_INTERNET = "no_internet"
    SLOW_INTERNET = "slow_internet"
    WIFI_PROBLEM = "wifi_problem"
    LOS_RED = "los_red"
    BILLING_ISSUE = "billing_issue"
    OTHER = "other"


class TicketPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TicketStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class SupportTicket(Base):
    """A complaint/issue raised by a customer, e.g. via the WhatsApp menu."""

    __tablename__ = "support_tickets"

    id = Column(Integer, primary_key=True)
    ticket_code = Column(String(20), unique=True, nullable=False)  # e.g. "TCK-00001"

    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    customer = relationship("Customer", backref="support_tickets")

    category = Column(Enum(TicketCategory), nullable=False, default=TicketCategory.OTHER)
    description = Column(Text, nullable=True)
    priority = Column(Enum(TicketPriority), nullable=False, default=TicketPriority.MEDIUM)
    status = Column(Enum(TicketStatus), nullable=False, default=TicketStatus.OPEN)

    assigned_engineer_id = Column(Integer, ForeignKey("engineers.id"), nullable=True)
    assigned_engineer = relationship("Engineer", back_populates="tickets")

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<SupportTicket {self.ticket_code} - {self.category} - {self.status}>"


# ---------------------------------------------------------------------------
# Appointment
# ---------------------------------------------------------------------------
class AppointmentType(str, enum.Enum):
    INSTALLATION = "installation"
    MAINTENANCE = "maintenance"
    INSPECTION = "inspection"


class AppointmentStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    RESCHEDULED = "rescheduled"


class Appointment(Base):
    """A scheduled installation, maintenance visit, or inspection."""

    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True)

    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    customer = relationship("Customer", backref="appointments")

    engineer_id = Column(Integer, ForeignKey("engineers.id"), nullable=True)
    engineer = relationship("Engineer", back_populates="appointments")

    appointment_type = Column(Enum(AppointmentType), nullable=False, default=AppointmentType.INSTALLATION)
    scheduled_date = Column(DateTime(timezone=True), nullable=False)
    status = Column(Enum(AppointmentStatus), nullable=False, default=AppointmentStatus.SCHEDULED)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    def __repr__(self):
        return f"<Appointment customer={self.customer_id} type={self.appointment_type} date={self.scheduled_date}>"


# ---------------------------------------------------------------------------
# ActivityLog
# ---------------------------------------------------------------------------
class ActivityLog(Base):
    """
    Audit trail — one row per significant action taken in the system
    (registration, payment received, ticket raised, balance checked, etc.).
    customer_id is nullable because not every logged action is tied to a
    specific customer (e.g. an admin action).
    """

    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True)

    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    customer = relationship("Customer", backref="activity_logs")

    action = Column(String(100), nullable=False)  # e.g. "registered", "payment_received"
    details = Column(Text, nullable=True)  # free-text or JSON-encoded extra context

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    def __repr__(self):
        return f"<ActivityLog {self.action} customer={self.customer_id}>"


# ---------------------------------------------------------------------------
# Notification
# ---------------------------------------------------------------------------
class NotificationType(str, enum.Enum):
    INSTALLATION_REMINDER = "installation_reminder"
    PAYMENT_REMINDER = "payment_reminder"
    TICKET_UPDATE = "ticket_update"
    MAINTENANCE_ALERT = "maintenance_alert"
    OUTAGE_NOTICE = "outage_notice"
    INVOICE = "invoice"
    RECEIPT = "receipt"


class NotificationStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class Notification(Base):
    """An outbound message queued (and later sent) to a customer via WhatsApp."""

    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)

    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    customer = relationship("Customer", backref="notifications")

    notification_type = Column(Enum(NotificationType), nullable=False)
    message = Column(Text, nullable=False)
    status = Column(Enum(NotificationStatus), nullable=False, default=NotificationStatus.PENDING)

    sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    def __repr__(self):
        return f"<Notification {self.notification_type} customer={self.customer_id} status={self.status}>"
