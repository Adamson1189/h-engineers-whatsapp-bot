"""
db/session.py

WHY THIS FILE EXISTS:
This is the ONE place that knows how to connect to PostgreSQL. Every other
file that needs database access imports from here — nobody else builds
their own connection.

Key concepts:
- `engine`: the object that actually knows how to talk to Postgres (host,
  port, credentials — all pulled from DATABASE_URL in your .env).
- `SessionLocal`: a factory that creates individual "sessions" — think of a
  session as one conversation with the database (you open it, do some
  queries/inserts, then close it). We create a NEW session per request,
  never share one across requests.
- `Base`: every model class (Customer, Plan, etc.) will inherit from this.
  It's how SQLAlchemy knows "these Python classes correspond to database
  tables."
- `get_db()`: a FastAPI "dependency" — a function we plug into route
  functions so FastAPI automatically gives us a fresh session per request
  and guarantees it gets closed afterward, even if an error happens.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import get_settings

settings = get_settings()

engine = create_engine(settings.database_url, echo=settings.debug)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    FastAPI dependency. Usage in a route:

        @app.get("/customers")
        def list_customers(db: Session = Depends(get_db)):
            return db.query(Customer).all()

    The `yield` pattern guarantees the session is closed after the request
    finishes — success or failure — so we never leak database connections.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
