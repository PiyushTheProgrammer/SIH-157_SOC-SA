"""
SAT-SA — database.py
=====================
Configures the local PostgreSQL database via SQLAlchemy.

Air-gap compliant: PostgreSQL runs on-premises — zero external calls.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 HOW TO SET YOUR PASSWORD
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Replace the placeholder below with your real credentials:
   DATABASE_PASSWORD = "your_actual_password_here"
   DATABASE_USER     = "postgres"          # or your PG user
   DATABASE_HOST     = "localhost"
   DATABASE_PORT     = 5432
   DATABASE_NAME     = "sat_sa_db"         # must already exist in PG

 Then run once in psql to create the database if needed:
   CREATE DATABASE sat_sa_db;
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# ── Connection parameters — edit here or provide via environment variables ──
DATABASE_USER     = os.getenv("DATABASE_USER", "postgres")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD", "YOUR_PASSWORD_HERE")  # <── REPLACE THIS
DATABASE_HOST     = os.getenv("DATABASE_HOST", "localhost")
DATABASE_PORT     = int(os.getenv("DATABASE_PORT", "5432"))
DATABASE_NAME     = os.getenv("DATABASE_NAME", "sat_sa_db")

SQLALCHEMY_DATABASE_URL = (
    f"postgresql://{DATABASE_USER}:{DATABASE_PASSWORD}"
    f"@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}"
)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,        # verifies connections before use
    pool_size=5,
    max_overflow=10,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ── Base class for all ORM models ─────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ── Dependency — yields a DB session and guarantees cleanup ───────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Create all tables (idempotent — safe to call multiple times) ───────────────
def init_db() -> None:
    """
    Import all model modules so SQLAlchemy registers their metadata,
    then issue CREATE TABLE … IF NOT EXISTS for every registered table.
    Call once at application startup via the FastAPI lifespan hook.
    """
    import models  # noqa: F401 — side-effect import registers ORM mappings
    Base.metadata.create_all(bind=engine)
