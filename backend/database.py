"""
SAT-SA — database.py
====================
Configures the local PostgreSQL database connection via SQLAlchemy.

Air-gap compliant: PostgreSQL runs on-premises — zero external API or cloud dependencies.

Connection string format:
    postgresql://postgres:<password>@localhost:5432/sat_sa_db

Requirements:
    - sqlalchemy >= 2.0.0
    - psycopg2-binary >= 2.9.9
    - python-dotenv >= 1.0.0
"""

import os
from typing import Generator
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# Load environment configuration from .env file
load_dotenv()

# ── Connection Parameters ───────────────────────────────────────────────────
DATABASE_USER = os.getenv("DATABASE_USER", "postgres")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")

if DATABASE_PASSWORD is None:
    raise ValueError("DATABASE_PASSWORD environment variable is missing.")

DATABASE_HOST = os.getenv("DATABASE_HOST", "localhost")
DATABASE_PORT = int(os.getenv("DATABASE_PORT", "5432"))
DATABASE_NAME = os.getenv("DATABASE_NAME", "sat_sa_db")

# URL-encode password to handle special characters (e.g., '@', ':', '/') safely
encoded_password = quote_plus(DATABASE_PASSWORD)

# Connection string format: postgresql://postgres:<password>@localhost:5432/sat_sa_db
SQLALCHEMY_DATABASE_URL = (
    f"postgresql://{DATABASE_USER}:{encoded_password}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}"
)

# ── SQLAlchemy Engine ───────────────────────────────────────────────────────
# pool_pre_ping tests connection liveness before issuing queries;
# pool_size and max_overflow handle concurrent API requests efficiently.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# ── Session Factory ─────────────────────────────────────────────────────────
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# ── Declarative Base Setup ──────────────────────────────────────────────────
Base = declarative_base()


# ── Database Dependency for FastAPI Endpoints ───────────────────────────────
def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency yielding an independent SQLAlchemy session per request
    and ensuring proper session closure in the finally block.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Idempotent Table Initialization ─────────────────────────────────────────
def init_db() -> None:
    """
    Imports all models to register their metadata and executes
    CREATE TABLE IF NOT EXISTS for each registered table against PostgreSQL.
    Invoked during FastAPI application startup.
    """
    import models  # noqa: F401 — side-effect registers ORM mappings
    Base.metadata.create_all(bind=engine)
