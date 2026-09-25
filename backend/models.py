"""
SAT-SA — models.py
====================
SQLAlchemy ORM model representing a single SOC alert record.

Air-gap compliant: SQLite is bundled with Python — zero external calls.
"""

from sqlalchemy import Boolean, Column, Integer, String, Text

from database import Base


class SocAlertRecord(Base):
    """
    Represents one row of uploaded SOC alert data stored in the local SQLite DB.

    All fields match the expected CSV schema documented in the Data Ingestion
    format reference table.
    """

    __tablename__ = "soc_alert_records"

    # ── Primary key (auto-assigned by the DB) ────────────────────────────────
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # ── Alert identification ──────────────────────────────────────────────────
    alert_id   = Column(String(64),  index=True,  nullable=True, comment="Unique alert identifier, e.g. AL-1001")
    entity_id  = Column(String(64),  index=True,  nullable=True, comment="Entity / organisation ID, e.g. ENT-A")
    asset_name = Column(String(128), nullable=True, comment="Affected asset name, e.g. web-server-01")

    # ── Alert classification ──────────────────────────────────────────────────
    alert_category = Column(String(64),  nullable=True, comment="Alert category: Malware, DDoS, Unauthorised Access …")
    alert_severity = Column(String(32),  nullable=True, comment="Severity: Critical / High / Medium / Low")

    # ── Resolution metrics ────────────────────────────────────────────────────
    time_to_close_seconds = Column(Integer, nullable=True, comment="Resolution time in seconds")
    escalated             = Column(Boolean, nullable=True, comment="True if the alert was escalated")
    resolution_notes      = Column(Text,    nullable=True, comment="Free-text analyst resolution notes")

    # ── Analytics flag (set by the anomaly detection engine post-insert) ──────
    is_anomaly = Column(Boolean, nullable=False, default=False, comment="True if flagged as anomalous by the ML engine")

    def __repr__(self) -> str:
        return (
            f"<SocAlertRecord id={self.id!r} alert_id={self.alert_id!r} "
            f"severity={self.alert_severity!r} is_anomaly={self.is_anomaly!r}>"
        )
