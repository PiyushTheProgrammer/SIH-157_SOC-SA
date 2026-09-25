"""
SAT-SA — models.py
==================
SQLAlchemy ORM models representing the SOC Alert dataset.
Strictly air-gap compliant: PostgreSQL runs on-premises — zero external calls.

Requirements:
  - sqlalchemy >= 2.0.0
  - psycopg2-binary >= 2.9.9
"""

from sqlalchemy import Boolean, Column, Integer, String, Text
from database import Base


class SOCAlert(Base):
    """
    SQLAlchemy ORM model representing a single SOC alert record matching
    the NCIIPC synthetic dataset structure.

    Columns:
      - id: Primary Key (auto-incrementing integer)
      - alert_id: Unique alert identifier (e.g., AL-1001)
      - entity_id: Critical sector / entity identifier (e.g., ENT-A)
      - asset_name: Host / asset name (e.g., web-server-01)
      - alert_category: Threat category (e.g., Malware, DDoS, Unauthorized Access)
      - alert_severity: Severity level (Critical, High, Medium, Low)
      - time_to_close_seconds: Resolution time in seconds
      - escalated: Boolean flag indicating if the alert was escalated
      - resolution_notes: Text notes entered by the analyst upon closure

    Analytics Engine Anomaly Flags (default False):
      - is_speed_anomaly: Flagged if time_to_close is suspiciously rapid
      - is_repetitive_anomaly: Flagged if closure notes match copy-paste patterns
      - is_negative_space: Flagged if asset exhibits silent/dormant periods
      - is_anomaly: Aggregate anomaly indicator for backwards compatibility
    """

    __tablename__ = "soc_alerts"

    # ── Primary Key ───────────────────────────────────────────────────────────
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # ── NCIIPC Synthetic Dataset Core Columns ─────────────────────────────────
    alert_id = Column(String(64), index=True, nullable=True, comment="Alert identifier, e.g. AL-1001")
    entity_id = Column(String(64), index=True, nullable=True, comment="Entity identifier, e.g. ENT-A")
    asset_name = Column(String(128), index=True, nullable=True, comment="Asset name, e.g. web-server-01")
    alert_category = Column(String(64), nullable=True, comment="Category: Malware, DDoS, etc.")
    alert_severity = Column(String(32), nullable=True, comment="Severity: Critical, High, Medium, Low")
    time_to_close_seconds = Column(Integer, nullable=True, comment="Resolution time in seconds")
    escalated = Column(Boolean, nullable=True, comment="True if alert was escalated")
    resolution_notes = Column(Text, nullable=True, comment="Analyst resolution commentary")

    # ── Analytics Engine Flags (updated post-ingestion by supervisory engine) ──
    is_speed_anomaly = Column(Boolean, nullable=False, default=False, comment="Suspiciously fast closure")
    is_repetitive_anomaly = Column(Boolean, nullable=False, default=False, comment="Repetitive copy-paste resolution")
    is_negative_space = Column(Boolean, nullable=False, default=False, comment="Negative space / blind spot anomaly")

    # Aggregate anomaly flag for backward compatibility
    is_anomaly = Column(Boolean, nullable=False, default=False, comment="General anomaly flag")

    def to_dict(self) -> dict:
        """Convert ORM model instance into a dictionary."""
        return {
            "id": self.id,
            "alert_id": self.alert_id,
            "entity_id": self.entity_id,
            "asset_name": self.asset_name,
            "alert_category": self.alert_category,
            "alert_severity": self.alert_severity,
            "time_to_close_seconds": self.time_to_close_seconds,
            "escalated": self.escalated,
            "resolution_notes": self.resolution_notes,
            "is_speed_anomaly": self.is_speed_anomaly,
            "is_repetitive_anomaly": self.is_repetitive_anomaly,
            "is_negative_space": self.is_negative_space,
            "is_anomaly": self.is_anomaly,
        }

    def __repr__(self) -> str:
        return (
            f"<SOCAlert id={self.id} alert_id={self.alert_id!r} "
            f"entity_id={self.entity_id!r} severity={self.alert_severity!r}>"
        )


# Backward compatibility alias
SocAlertRecord = SOCAlert
