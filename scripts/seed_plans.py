"""
scripts/seed_plans.py

WHY THIS FILE EXISTS:
Before customers can subscribe to a plan, the Plans table needs to actually
contain your real plans. This is a one-time (or run-whenever-prices-change)
script that inserts/updates Netfiber's real pricing into the database.

HOW TO RUN THIS:
    python -m scripts.seed_plans

WHY THIS APPROACH (upsert by name, not blind insert):
Running this script twice shouldn't create duplicate plans. We check if a
plan with the same name already exists -- if so, we update its price/speed
(in case prices changed), rather than inserting a second "Starter" row.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.models import BillingCycle, Plan
from app.db.session import SessionLocal

# Real Netfiber pricing, as of the current website.
PLANS = [
    {"name": "Starter", "speed_mbps": 6, "price": 16909},
    {"name": "Basic", "speed_mbps": 10, "price": 21856},
    {"name": "Premium", "speed_mbps": 20, "price": 26922},
    {"name": "Elite", "speed_mbps": 30, "price": 34937},
    {"name": "Gold", "speed_mbps": 40, "price": 43898},
    {"name": "Silver", "speed_mbps": 75, "price": 60313},
    {"name": "Platinum", "speed_mbps": 100, "price": 90377},
]


def seed_plans():
    db = SessionLocal()
    try:
        for plan_data in PLANS:
            existing = db.query(Plan).filter(Plan.name == plan_data["name"]).first()
            if existing:
                existing.speed_mbps = plan_data["speed_mbps"]
                existing.price = plan_data["price"]
                existing.is_active = True
                print(f"Updated: {plan_data['name']}")
            else:
                db.add(
                    Plan(
                        name=plan_data["name"],
                        speed_mbps=plan_data["speed_mbps"],
                        price=plan_data["price"],
                        billing_cycle=BillingCycle.MONTHLY,
                        is_active=True,
                    )
                )
                print(f"Created: {plan_data['name']}")
        db.commit()
        print("\nAll plans seeded successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_plans()
