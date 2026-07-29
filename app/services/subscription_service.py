"""
services/subscription_service.py

WHY THIS FILE EXISTS:
Business logic for Plans and Subscriptions -- listing available plans,
subscribing a customer for the first time, renewing, and changing plans.
Kept separate from customer_service.py since subscription/billing logic
is its own concern.

NOTE ON BALANCE (until Phase 8 - Payments is built):
`balance` on a Subscription represents what the customer currently owes.
Since we don't have real payment processing wired in yet, every
subscribe/renew simply ADDS the plan price to their balance -- there's no
way to pay it down yet. That's expected and will be resolved once Phase 8
adds Paystack integration (a payment will reduce this balance).
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db.models import Plan, Subscription, SubscriptionStatus

SUBSCRIPTION_LENGTH_DAYS = 30


def list_active_plans(db: Session) -> list[Plan]:
    """Returns all currently sellable plans, cheapest first."""
    return db.query(Plan).filter(Plan.is_active == True).order_by(Plan.price).all()  # noqa: E712


def get_plan_by_number(db: Session, plans: list[Plan], number_text: str) -> Plan | None:
    """
    Given the numbered list we just showed the customer (1, 2, 3...) and
    what they typed, returns the matching Plan. Keeps the "which number
    means which plan" logic in one place rather than scattered across the
    message handler.
    """
    try:
        index = int(number_text.strip()) - 1
    except ValueError:
        return None
    if 0 <= index < len(plans):
        return plans[index]
    return None


def get_active_subscription(db: Session, customer_id: int) -> Subscription | None:
    """Returns the customer's current active subscription, if any."""
    return (
        db.query(Subscription)
        .filter(Subscription.customer_id == customer_id, Subscription.status == SubscriptionStatus.ACTIVE)
        .order_by(Subscription.id.desc())
        .first()
    )


def subscribe_customer_to_plan(db: Session, customer_id: int, plan: Plan) -> Subscription:
    """Creates a brand-new subscription for a customer with no existing one."""
    now = datetime.now(timezone.utc)
    subscription = Subscription(
        customer_id=customer_id,
        plan_id=plan.id,
        start_date=now,
        expiry_date=now + timedelta(days=SUBSCRIPTION_LENGTH_DAYS),
        status=SubscriptionStatus.ACTIVE,
        balance=plan.price,
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


def renew_subscription(db: Session, subscription: Subscription) -> Subscription:
    """
    Extends an existing subscription by another billing cycle.

    WHY `max(expiry_date, now)`: if they renew a day before it expires, the
    new cycle should extend from the ORIGINAL expiry date (so they don't
    lose the days they already paid for). If they renew after it already
    lapsed, the new cycle starts from today instead.
    """
    now = datetime.now(timezone.utc)
    current_expiry = subscription.expiry_date
    # WHY THIS EXISTS: SQLite (used in local testing) doesn't preserve
    # timezone info on stored datetimes the way PostgreSQL does -- it can
    # hand back a "naive" datetime with no tzinfo, which crashes when
    # compared directly against a timezone-aware `now`. If that happens,
    # we assume the stored value was UTC (since that's what we always save)
    # and attach the tzinfo before comparing. This is a no-op on Postgres,
    # where expiry_date already comes back timezone-aware.
    if current_expiry.tzinfo is None:
        current_expiry = current_expiry.replace(tzinfo=timezone.utc)
    base = max(current_expiry, now)
    subscription.expiry_date = base + timedelta(days=SUBSCRIPTION_LENGTH_DAYS)
    subscription.balance += subscription.plan.price
    subscription.status = SubscriptionStatus.ACTIVE
    db.commit()
    db.refresh(subscription)
    return subscription


def change_plan(db: Session, subscription: Subscription, new_plan: Plan) -> Subscription:
    """
    Switches a customer to a different plan, effective immediately.

    NOTE: kept simple on purpose -- no pro-rating of the price difference
    for the remaining days on the current cycle. Real ISPs often do prorate
    upgrades/downgrades, but that adds real complexity (partial-day math,
    refund/credit handling) that's better added as a deliberate improvement
    once the simple version is working and tested.
    """
    subscription.plan_id = new_plan.id
    db.commit()
    db.refresh(subscription)
    return subscription
