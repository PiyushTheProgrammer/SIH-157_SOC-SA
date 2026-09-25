"""
SAT-SA — database.py
=====================
Configures a local SQLite database via SQLAlchemy.
The DB file (sat_sa_records.db) lives in the backend/ directory.

Air-gap compliant: SQLite is bundled with Python — zero external calls.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# ── Database URL ──────────────────────────────────────────────────────────────
# Relative path keeps the DB file next to main.py regardless of CWD.
SQLALCHEMY_DATABASE_URL = "sqlite:///./sat_sa_records.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},  # Required for SQLite + FastAPI
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


# ── Create all tables defined in models that import this Base ─────────────────
def init_db() -> None:
    """
    Import all model modules so that SQLAlchemy registers their metadata,
    then issue CREATE TABLE … IF NOT EXISTS for every registered table.
    Call this once at application startup (via the FastAPI lifespan hook).
    """
    import models  # noqa: F401 — side-effect import registers the ORM mappings
    Base.metadata.create_all(bind=engine)
