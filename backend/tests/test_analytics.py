"""
SAT-SA — Phase 2: Analytics Engine Unit Tests
===============================================
Validates that the three detectors correctly identify the anomalies
injected by the Phase 1 data generator.

Run:
    cd backend/
    python generate_mock_soc_data.py   # must generate data first
    python -m pytest tests/ -v
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

# Ensure backend/ is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analytics_engine import (
    AnalyticsOrchestrator,
    BlindSpotDetector,
    RepetitiveNotesDetector,
    SpeedAnomalyDetector,
)

# ── Paths ──
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
ALERTS_CSV = DATA_DIR / "soc_alerts.csv"
INVENTORY_CSV = DATA_DIR / "asset_inventory.csv"

# Known injected values from generate_mock_soc_data.py
SILENT_CRITICAL_ASSETS = {
    "prod-db-01",
    "prod-auth-srv",
    "prod-pay-gw",
    "prod-vault-01",
    "prod-ci-master",
}

GENERIC_NOTES = [
    "Resolved per SOP.",
    "False positive, no action needed.",
    "Ticket auto-closed after initial review.",
    "No threat detected upon investigation.",
    "Issue resolved. Closing ticket.",
]


# ──────────────────────────────────────────────
# FIXTURES
# ──────────────────────────────────────────────


@pytest.fixture(scope="module")
def alerts_df() -> pd.DataFrame:
    """Load the generated alerts CSV."""
    if not ALERTS_CSV.exists():
        pytest.skip(f"Data file not found: {ALERTS_CSV}. Run generate_mock_soc_data.py first.")
    return pd.read_csv(ALERTS_CSV)


@pytest.fixture(scope="module")
def inventory_df() -> pd.DataFrame:
    """Load the generated asset inventory CSV."""
    if not INVENTORY_CSV.exists():
        pytest.skip(f"Data file not found: {INVENTORY_CSV}. Run generate_mock_soc_data.py first.")
    return pd.read_csv(INVENTORY_CSV)


@pytest.fixture(scope="module")
def full_report(alerts_df, inventory_df) -> dict:
    """Run the full orchestrator and cache the result."""
    orchestrator = AnalyticsOrchestrator(ALERTS_CSV, INVENTORY_CSV)
    orchestrator.load_data()
    report = orchestrator.run()
    return report.to_dict()


# ──────────────────────────────────────────────
# TEST: Data Integrity
# ──────────────────────────────────────────────


class TestDataIntegrity:
    """Validate the generated CSV files have the correct shape."""

    def test_alerts_row_count(self, alerts_df: pd.DataFrame):
        assert len(alerts_df) == 10_000, f"Expected 10,000 alerts, got {len(alerts_df)}"

    def test_alerts_columns(self, alerts_df: pd.DataFrame):
        required = {
            "ticket_id", "timestamp", "alert_severity", "alert_type",
            "source_ip", "dest_asset", "assigned_analyst",
            "time_to_acknowledge", "time_to_close", "resolution_notes",
            "escalated", "shift",
        }
        assert required.issubset(set(alerts_df.columns)), (
            f"Missing columns: {required - set(alerts_df.columns)}"
        )

    def test_inventory_row_count(self, inventory_df: pd.DataFrame):
        assert len(inventory_df) == 50, f"Expected 50 assets, got {len(inventory_df)}"

    def test_no_alerts_for_silent_assets(self, alerts_df: pd.DataFrame):
        """The 5 silent critical assets should have exactly 0 tickets."""
        alerted_assets = set(alerts_df["dest_asset"].unique())
        silent_with_alerts = SILENT_CRITICAL_ASSETS & alerted_assets
        assert len(silent_with_alerts) == 0, (
            f"Silent assets unexpectedly have alerts: {silent_with_alerts}"
        )


# ──────────────────────────────────────────────
# TEST: Speed Anomaly Detector
# ──────────────────────────────────────────────


class TestSpeedAnomalyDetector:
    """Validate the Isolation Forest + threshold detector."""

    def test_detects_speed_anomalies(self, alerts_df: pd.DataFrame):
        detector = SpeedAnomalyDetector()
        flagged = detector.detect(alerts_df)

        # We injected 200 speed anomalies (CRITICAL, <15s)
        # The detector should catch at least 80% of them
        assert len(flagged) >= 160, (
            f"Expected ≥160 flagged speed anomalies, got {len(flagged)}"
        )

    def test_all_flagged_are_critical_or_high(self, alerts_df: pd.DataFrame):
        detector = SpeedAnomalyDetector()
        flagged = detector.detect(alerts_df)

        for anomaly in flagged:
            assert anomaly.severity in ("CRITICAL", "HIGH"), (
                f"Unexpected severity {anomaly.severity} in flagged ticket {anomaly.ticket_id}"
            )

    def test_flagged_have_low_close_times(self, alerts_df: pd.DataFrame):
        detector = SpeedAnomalyDetector()
        flagged = detector.detect(alerts_df)

        for anomaly in flagged:
            threshold = 120 if anomaly.severity == "CRITICAL" else 60
            assert anomaly.time_to_close < threshold, (
                f"Ticket {anomaly.ticket_id} has time_to_close={anomaly.time_to_close}s "
                f"but threshold is {threshold}s"
            )

    def test_explanations_are_populated(self, alerts_df: pd.DataFrame):
        detector = SpeedAnomalyDetector()
        flagged = detector.detect(alerts_df)

        for anomaly in flagged[:5]:  # spot-check first 5
            assert len(anomaly.explanation) > 20, "Explanation is too short"
            assert anomaly.analyst in anomaly.explanation


# ──────────────────────────────────────────────
# TEST: Repetitive Notes Detector
# ──────────────────────────────────────────────


class TestRepetitiveNotesDetector:
    """Validate the TF-IDF / hash-based repetitive note detection."""

    def test_detects_repetitive_clusters(self, alerts_df: pd.DataFrame):
        detector = RepetitiveNotesDetector()
        flagged = detector.detect(alerts_df)

        # We injected ~300 tickets across 6 analysts with identical notes
        assert len(flagged) >= 4, (
            f"Expected ≥4 repetitive-note clusters, got {len(flagged)}"
        )

    def test_clusters_span_multiple_alert_types(self, alerts_df: pd.DataFrame):
        detector = RepetitiveNotesDetector()
        flagged = detector.detect(alerts_df)

        for cluster in flagged:
            assert len(cluster.distinct_alert_types) >= 3, (
                f"Cluster for {cluster.analyst} spans only "
                f"{len(cluster.distinct_alert_types)} alert types (need ≥3)"
            )

    def test_known_generic_notes_detected(self, alerts_df: pd.DataFrame):
        detector = RepetitiveNotesDetector()
        flagged = detector.detect(alerts_df)

        detected_snippets = {c.repeated_note_snippet.strip().rstrip("…") for c in flagged}
        known_set = {n[:120] for n in GENERIC_NOTES}

        # At least 3 of the 5 known generic notes should appear
        overlap = detected_snippets & known_set
        assert len(overlap) >= 3, (
            f"Expected ≥3 known generic notes detected, got {len(overlap)}: {overlap}"
        )


# ──────────────────────────────────────────────
# TEST: Blind Spot Detector
# ──────────────────────────────────────────────


class TestBlindSpotDetector:
    """Validate the statistical blind-spot detection."""

    def test_detects_all_silent_critical_assets(self, alerts_df, inventory_df):
        detector = BlindSpotDetector()
        flagged = detector.detect(alerts_df, inventory_df)

        flagged_ids = {b.asset_id for b in flagged}
        missing = SILENT_CRITICAL_ASSETS - flagged_ids
        assert len(missing) == 0, (
            f"Failed to detect silent critical assets: {missing}"
        )

    def test_flagged_have_zero_alerts(self, alerts_df, inventory_df):
        detector = BlindSpotDetector()
        flagged = detector.detect(alerts_df, inventory_df)

        for blind_spot in flagged:
            if blind_spot.asset_id in SILENT_CRITICAL_ASSETS:
                assert blind_spot.actual_alerts == 0, (
                    f"Asset {blind_spot.asset_id} should have 0 alerts but has {blind_spot.actual_alerts}"
                )

    def test_explanations_mention_telemetry(self, alerts_df, inventory_df):
        detector = BlindSpotDetector()
        flagged = detector.detect(alerts_df, inventory_df)

        for b in flagged:
            if b.actual_alerts == 0:
                assert "telemetry" in b.explanation.lower() or "monitoring" in b.explanation.lower(), (
                    f"Explanation for {b.asset_id} should mention telemetry or monitoring gap"
                )


# ──────────────────────────────────────────────
# TEST: Orchestrator & Report
# ──────────────────────────────────────────────


class TestOrchestrator:
    """Validate the orchestrator produces a valid unified report."""

    def test_report_has_summary(self, full_report: dict):
        assert "summary" in full_report
        summary = full_report["summary"]
        assert summary["total_alerts"] == 10_000
        assert summary["overall_risk_score"] > 0

    def test_report_has_all_sections(self, full_report: dict):
        assert "speed_anomalies" in full_report
        assert "repetitive_notes" in full_report
        assert "blind_spots" in full_report

    def test_report_entity_risk_populated(self, full_report: dict):
        entity_risk = full_report["summary"]["entity_risk"]
        assert len(entity_risk) > 0, "Entity risk list should not be empty"

        for entity in entity_risk:
            assert "entity" in entity
            assert "risk_score" in entity

    def test_report_json_serialisable(self, full_report: dict):
        """The report must be JSON-serialisable for the API layer."""
        import json
        try:
            json_str = json.dumps(full_report, default=str)
            assert len(json_str) > 100
        except (TypeError, ValueError) as e:
            pytest.fail(f"Report is not JSON-serialisable: {e}")

    def test_total_flagged_count(self, full_report: dict):
        summary = full_report["summary"]
        expected_total = (
            summary["speed_anomalies_count"]
            + summary["repetitive_notes_tickets"]
            + summary["blind_spots_count"]
        )
        assert summary["total_flagged_anomalies"] == expected_total
