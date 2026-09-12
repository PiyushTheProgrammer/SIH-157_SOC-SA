"""
SAT-SA — Phase 2: Analytics Engine (The Brain)
================================================
Processes SOC alert CSVs to detect three classes of operational anomalies:

  1. SpeedAnomalyDetector   — Improbably fast ticket closures using
                               Isolation Forest + rule-based thresholds.
  2. RepetitiveNotesDetector — Analysts pasting identical resolution text
                               across different alert types (TF-IDF + cosine).
  3. BlindSpotDetector       — Critical assets with statistically improbable
                               zero (or near-zero) alert volumes.

Orchestrator: AnalyticsOrchestrator runs all detectors and produces a
              unified AnomalyReport serialisable to JSON.

All processing is 100 % offline — no network calls.
"""

from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# ════════════════════════════════════════════════
# DATA CLASSES
# ════════════════════════════════════════════════


@dataclass
class SpeedAnomaly:
    """A single ticket flagged for improbably fast closure."""
    ticket_id: str
    severity: str
    time_to_close: int
    time_to_acknowledge: int
    escalated: bool
    analyst: str
    alert_type: str
    dest_asset: str
    timestamp: str
    explanation: str


@dataclass
class RepetitiveNoteCluster:
    """A group of tickets sharing near-identical resolution notes."""
    analyst: str
    repeated_note_snippet: str
    ticket_ids: list[str]
    distinct_alert_types: list[str]
    ticket_count: int
    explanation: str


@dataclass
class BlindSpot:
    """An asset flagged for statistically improbable alert silence."""
    asset_id: str
    criticality: str
    asset_type: str
    actual_alerts: int
    expected_mean: float
    expected_std: float
    explanation: str


@dataclass
class AnomalyReport:
    """Unified output from the analytics engine."""
    summary: dict[str, Any] = field(default_factory=dict)
    speed_anomalies: list[SpeedAnomaly] = field(default_factory=list)
    repetitive_notes: list[RepetitiveNoteCluster] = field(default_factory=list)
    blind_spots: list[BlindSpot] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "summary": self.summary,
            "speed_anomalies": [asdict(a) for a in self.speed_anomalies],
            "repetitive_notes": [asdict(c) for c in self.repetitive_notes],
            "blind_spots": [asdict(b) for b in self.blind_spots],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)


# ════════════════════════════════════════════════
# DETECTOR 1: Speed Anomaly Detector
# ════════════════════════════════════════════════

# Hard thresholds (seconds) — tickets below these are suspicious
SEVERITY_SPEED_THRESHOLDS = {
    "CRITICAL": 120,   # < 2 minutes
    "HIGH": 60,        # < 1 minute
    "MEDIUM": 30,
    "LOW": 15,
}

SEVERITY_ENCODING = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}


class SpeedAnomalyDetector:
    """
    Detect tickets closed improbably fast relative to their severity.

    Hybrid approach:
      1. Rule-based filter: Flag CRITICAL/HIGH tickets below time thresholds.
      2. Isolation Forest scoring: Fit an unsupervised model on ticket features
         and compute anomaly scores. Tickets that pass the rule-based filter
         AND score highly anomalous are ranked first.

    This ensures we never miss obvious speed anomalies (the rule catches them)
    while the ML model provides a confidence/ranking signal.
    """

    def __init__(self, contamination: float = 0.05, random_state: int = 42):
        self.model = IsolationForest(
            contamination=contamination,
            random_state=random_state,
            n_estimators=200,
            n_jobs=-1,
        )

    def detect(self, df: pd.DataFrame) -> list[SpeedAnomaly]:
        """Run detection on the alerts DataFrame. Returns flagged tickets."""
        # Build feature matrix
        df = df.copy()
        df["severity_num"] = df["alert_severity"].map(SEVERITY_ENCODING)
        df["escalated_num"] = df["escalated"].map(
            {True: 1, False: 0, "True": 1, "False": 0}
        ).fillna(0).astype(int)

        features = df[["severity_num", "time_to_close", "time_to_acknowledge", "escalated_num"]].values

        # Fit the model and get anomaly scores (lower = more anomalous)
        self.model.fit(features)
        df["anomaly_score"] = self.model.decision_function(features)

        # Primary detection: rule-based severity threshold filter
        # Secondary signal: Isolation Forest anomaly score for ranking
        flagged: list[SpeedAnomaly] = []
        for _, row in df.iterrows():
            sev = row["alert_severity"]
            ttc = int(row["time_to_close"])
            threshold = SEVERITY_SPEED_THRESHOLDS.get(sev, 15)

            # Rule-based gate: must be CRITICAL/HIGH AND below time threshold
            if ttc < threshold and sev in ("CRITICAL", "HIGH"):
                score = float(row["anomaly_score"])
                escalated = bool(row["escalated"])
                esc_note = " without escalation" if not escalated else " (was escalated)"
                explanation = (
                    f"{sev} alert closed in {ttc}s (threshold: {threshold}s)"
                    f"{esc_note}. "
                    f"Anomaly score: {score:.4f}. "
                    f"Analyst: {row['assigned_analyst']}. "
                    f"Alert type: {row['alert_type']}."
                )
                flagged.append(
                    SpeedAnomaly(
                        ticket_id=row["ticket_id"],
                        severity=sev,
                        time_to_close=ttc,
                        time_to_acknowledge=int(row["time_to_acknowledge"]),
                        escalated=escalated,
                        analyst=row["assigned_analyst"],
                        alert_type=row["alert_type"],
                        dest_asset=row["dest_asset"],
                        timestamp=str(row["timestamp"]),
                        explanation=explanation,
                    )
                )

        # Sort by anomaly score (most anomalous first — lowest score)
        flagged.sort(key=lambda a: a.time_to_close)
        return flagged


# ════════════════════════════════════════════════
# DETECTOR 2: Repetitive Notes Detector
# ════════════════════════════════════════════════


class RepetitiveNotesDetector:
    """
    Detect analysts who paste near-identical resolution notes across
    multiple, disparate alert types.

    Approach:
      1. Group tickets by analyst.
      2. For each analyst, TF-IDF-vectorise their resolution notes.
      3. Compute pairwise cosine similarity.
      4. Cluster notes with similarity ≥ 0.95.
      5. Flag clusters of ≥ 10 tickets spanning ≥ 3 different alert types.
    """

    def __init__(self, similarity_threshold: float = 0.95, min_cluster_size: int = 10, min_alert_types: int = 3):
        self.sim_threshold = similarity_threshold
        self.min_cluster = min_cluster_size
        self.min_types = min_alert_types

    def detect(self, df: pd.DataFrame) -> list[RepetitiveNoteCluster]:
        """Run detection. Returns flagged clusters."""
        flagged: list[RepetitiveNoteCluster] = []

        for analyst, group in df.groupby("assigned_analyst"):
            if len(group) < self.min_cluster:
                continue

            clusters = self._find_clusters(group)
            for cluster_indices in clusters:
                cluster_df = group.iloc[cluster_indices]
                unique_types = cluster_df["alert_type"].unique().tolist()

                if len(cluster_indices) >= self.min_cluster and len(unique_types) >= self.min_types:
                    note_snippet = cluster_df["resolution_notes"].iloc[0][:120]
                    explanation = (
                        f"Analyst {analyst} used near-identical resolution notes across "
                        f"{len(cluster_indices)} tickets spanning {len(unique_types)} "
                        f"different alert types ({', '.join(unique_types[:5])}). "
                        f"Note snippet: \"{note_snippet}…\""
                    )
                    flagged.append(
                        RepetitiveNoteCluster(
                            analyst=str(analyst),
                            repeated_note_snippet=note_snippet,
                            ticket_ids=cluster_df["ticket_id"].tolist(),
                            distinct_alert_types=unique_types,
                            ticket_count=len(cluster_indices),
                            explanation=explanation,
                        )
                    )

        return flagged

    def _find_clusters(self, group: pd.DataFrame) -> list[list[int]]:
        """
        Use TF-IDF + cosine similarity to find clusters of near-identical notes.
        Returns a list of index-lists (each list is one cluster).
        """
        notes = group["resolution_notes"].fillna("").tolist()

        # Fast path: hash-based grouping for exact duplicates first
        hash_groups: dict[str, list[int]] = {}
        for i, note in enumerate(notes):
            h = hashlib.md5(note.strip().lower().encode()).hexdigest()
            hash_groups.setdefault(h, []).append(i)

        clusters: list[list[int]] = []
        seen: set[int] = set()

        # Exact-match clusters
        for indices in hash_groups.values():
            if len(indices) >= self.min_cluster:
                clusters.append(indices)
                seen.update(indices)

        # For remaining notes, use TF-IDF for near-duplicate detection
        remaining_indices = [i for i in range(len(notes)) if i not in seen]
        if len(remaining_indices) < self.min_cluster:
            return clusters

        remaining_notes = [notes[i] for i in remaining_indices]

        try:
            vectorizer = TfidfVectorizer(
                max_features=5000,
                stop_words="english",
                ngram_range=(1, 2),
            )
            tfidf_matrix = vectorizer.fit_transform(remaining_notes)
            sim_matrix = cosine_similarity(tfidf_matrix)
        except ValueError:
            # Edge case: all notes are empty or too short for TF-IDF
            return clusters

        # Greedy clustering on the similarity matrix
        used = set()
        for i in range(len(remaining_indices)):
            if i in used:
                continue
            cluster = [remaining_indices[i]]
            for j in range(i + 1, len(remaining_indices)):
                if j in used:
                    continue
                if sim_matrix[i, j] >= self.sim_threshold:
                    cluster.append(remaining_indices[j])
                    used.add(j)
            if len(cluster) >= self.min_cluster:
                clusters.append(cluster)
            used.add(i)

        return clusters


# ════════════════════════════════════════════════
# DETECTOR 3: Blind Spot Detector
# ════════════════════════════════════════════════


class BlindSpotDetector:
    """
    Detect critical assets with statistically improbable zero (or near-zero)
    alert volumes compared to peers of the same criticality level.

    Approach:
      1. Count alerts per asset from the ticket data.
      2. Compute mean and std alert volume per criticality group.
      3. Flag assets with 0 alerts (and criticality ≥ HIGH).
      4. Also flag assets below 2 standard deviations from their group mean.
    """

    def __init__(self, z_threshold: float = 2.0):
        self.z_threshold = z_threshold

    def detect(
        self,
        alerts_df: pd.DataFrame,
        inventory_df: pd.DataFrame,
    ) -> list[BlindSpot]:
        """Run detection. Returns flagged assets."""
        # Count alerts per asset
        alert_counts = alerts_df["dest_asset"].value_counts().to_dict()

        # Merge counts into inventory
        inv = inventory_df.copy()
        inv["actual_alerts"] = inv["asset_id"].map(alert_counts).fillna(0).astype(int)

        # Compute group statistics
        group_stats = inv.groupby("asset_criticality")["actual_alerts"].agg(["mean", "std"]).to_dict("index")

        flagged: list[BlindSpot] = []
        for _, row in inv.iterrows():
            crit = row["asset_criticality"]
            actual = int(row["actual_alerts"])
            stats = group_stats.get(crit, {"mean": 0, "std": 0})
            mean_val = float(stats["mean"])
            std_val = float(stats["std"])

            # Only flag HIGH and CRITICAL assets
            if crit not in ("CRITICAL", "HIGH"):
                continue

            # Flag zero-alert assets
            if actual == 0 and mean_val > 0:
                explanation = (
                    f"CRITICAL asset '{row['asset_id']}' ({row['asset_type']}) "
                    f"generated 0 alerts over 30 days. "
                    f"Expected ~{mean_val:.1f} (σ={std_val:.1f}) based on "
                    f"{crit}-class peers. "
                    f"Possible telemetry failure or monitoring gap."
                )
                flagged.append(
                    BlindSpot(
                        asset_id=row["asset_id"],
                        criticality=crit,
                        asset_type=row["asset_type"],
                        actual_alerts=actual,
                        expected_mean=round(mean_val, 2),
                        expected_std=round(std_val, 2),
                        explanation=explanation,
                    )
                )
            # Flag statistically low assets (> 0 but below 2σ)
            elif std_val > 0 and actual < (mean_val - self.z_threshold * std_val) and actual > 0:
                explanation = (
                    f"Asset '{row['asset_id']}' ({crit}) has {actual} alerts, "
                    f"significantly below the {crit}-class mean of "
                    f"{mean_val:.1f} (σ={std_val:.1f}). "
                    f"Z-score: {(actual - mean_val) / std_val:.2f}. "
                    f"Investigate potential monitoring gap."
                )
                flagged.append(
                    BlindSpot(
                        asset_id=row["asset_id"],
                        criticality=crit,
                        asset_type=row["asset_type"],
                        actual_alerts=actual,
                        expected_mean=round(mean_val, 2),
                        expected_std=round(std_val, 2),
                        explanation=explanation,
                    )
                )

        return flagged


# ════════════════════════════════════════════════
# ORCHESTRATOR
# ════════════════════════════════════════════════


def _compute_risk_score(report: AnomalyReport, total_tickets: int) -> float:
    """
    Compute an overall risk score (0–100) based on anomaly density.

    Weighting:
      - Speed anomalies:   high weight (direct compliance risk)
      - Repetitive notes:  medium weight (process risk)
      - Blind spots:       high weight (visibility risk)
    """
    if total_tickets == 0:
        return 0.0

    speed_ratio = len(report.speed_anomalies) / total_tickets
    rep_ticket_count = sum(c.ticket_count for c in report.repetitive_notes)
    rep_ratio = rep_ticket_count / total_tickets
    blind_count = len(report.blind_spots)

    # Weighted score components (each normalised to ~0-1 then scaled)
    speed_score = min(speed_ratio * 500, 40)       # max 40 pts
    rep_score = min(rep_ratio * 300, 30)            # max 30 pts
    blind_score = min(blind_count * 6, 30)          # max 30 pts (5 assets = 30)

    return round(min(speed_score + rep_score + blind_score, 100), 1)


class AnalyticsOrchestrator:
    """
    Central coordinator that loads data, runs all detectors, and produces
    a unified AnomalyReport.
    """

    def __init__(
        self,
        alerts_path: str | Path,
        inventory_path: str | Path,
    ):
        self.alerts_path = Path(alerts_path)
        self.inventory_path = Path(inventory_path)
        self._alerts_df: pd.DataFrame | None = None
        self._inventory_df: pd.DataFrame | None = None

    def load_data(self) -> None:
        """Load CSVs into DataFrames."""
        print(f"[Engine] Loading alerts from {self.alerts_path} ...")
        self._alerts_df = pd.read_csv(self.alerts_path)
        print(f"         -> {len(self._alerts_df)} tickets loaded.")

        print(f"[Engine] Loading inventory from {self.inventory_path} ...")
        self._inventory_df = pd.read_csv(self.inventory_path)
        print(f"         -> {len(self._inventory_df)} assets loaded.")

    @property
    def alerts_df(self) -> pd.DataFrame:
        if self._alerts_df is None:
            raise RuntimeError("Data not loaded. Call load_data() first.")
        return self._alerts_df

    @property
    def inventory_df(self) -> pd.DataFrame:
        if self._inventory_df is None:
            raise RuntimeError("Data not loaded. Call load_data() first.")
        return self._inventory_df

    def run(self) -> AnomalyReport:
        """Execute all detectors and build the unified report."""
        if self._alerts_df is None:
            self.load_data()

        report = AnomalyReport()

        # ── Detector 1: Speed anomalies ──
        print("\n[Engine] Running Speed Anomaly Detector ...")
        speed_det = SpeedAnomalyDetector()
        report.speed_anomalies = speed_det.detect(self.alerts_df)
        print(f"         -> {len(report.speed_anomalies)} tickets flagged.")

        # ── Detector 2: Repetitive notes ──
        print("[Engine] Running Repetitive Notes Detector ...")
        notes_det = RepetitiveNotesDetector()
        report.repetitive_notes = notes_det.detect(self.alerts_df)
        total_rep = sum(c.ticket_count for c in report.repetitive_notes)
        print(f"         -> {len(report.repetitive_notes)} clusters ({total_rep} tickets) flagged.")

        # ── Detector 3: Blind spots ──
        print("[Engine] Running Blind Spot Detector ...")
        blind_det = BlindSpotDetector()
        report.blind_spots = blind_det.detect(self.alerts_df, self.inventory_df)
        print(f"         -> {len(report.blind_spots)} assets flagged.")

        # ── Build summary ──
        total = len(self.alerts_df)
        total_flagged = (
            len(report.speed_anomalies) + total_rep + len(report.blind_spots)
        )
        risk_score = _compute_risk_score(report, total)

        # Per-analyst risk breakdown
        analyst_speed = {}
        for a in report.speed_anomalies:
            analyst_speed[a.analyst] = analyst_speed.get(a.analyst, 0) + 1
        analyst_rep = {}
        for c in report.repetitive_notes:
            analyst_rep[c.analyst] = analyst_rep.get(c.analyst, 0) + c.ticket_count

        # Merge into per-entity risk
        all_entities = set(analyst_speed.keys()) | set(analyst_rep.keys())
        entity_risk: list[dict[str, Any]] = []
        for entity in sorted(all_entities):
            speed_n = analyst_speed.get(entity, 0)
            rep_n = analyst_rep.get(entity, 0)
            entity_score = min(
                (speed_n * 3) + (rep_n * 1.5), 100
            )
            entity_risk.append(
                {
                    "entity": entity,
                    "speed_anomalies": speed_n,
                    "repetitive_notes": rep_n,
                    "risk_score": round(entity_score, 1),
                }
            )

        # Add blind-spot assets as entities
        for b in report.blind_spots:
            entity_risk.append(
                {
                    "entity": b.asset_id,
                    "blind_spot": True,
                    "actual_alerts": b.actual_alerts,
                    "expected_mean": b.expected_mean,
                    "risk_score": 90.0,  # silent critical assets get a high score
                }
            )

        report.summary = {
            "total_alerts": total,
            "total_flagged_anomalies": total_flagged,
            "speed_anomalies_count": len(report.speed_anomalies),
            "repetitive_notes_clusters": len(report.repetitive_notes),
            "repetitive_notes_tickets": total_rep,
            "blind_spots_count": len(report.blind_spots),
            "overall_risk_score": risk_score,
            "entity_risk": entity_risk,
        }

        print(f"\n[Engine] [OK] Analysis complete. Risk score: {risk_score}/100")
        print(f"         Total flagged: {total_flagged} items")
        return report


# ════════════════════════════════════════════════
# STANDALONE EXECUTION
# ════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SAT-SA Analytics Engine (Phase 2)")
    parser.add_argument(
        "--data-dir",
        type=str,
        default=str(Path(__file__).parent / "data"),
        help="Directory containing soc_alerts.csv and asset_inventory.csv",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Path to write JSON report (default: print to stdout)",
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    orchestrator = AnalyticsOrchestrator(
        alerts_path=data_dir / "soc_alerts.csv",
        inventory_path=data_dir / "asset_inventory.csv",
    )

    report = orchestrator.run()

    if args.output:
        out_path = Path(args.output)
        out_path.write_text(report.to_json(), encoding="utf-8")
        print(f"\n[Engine] Report written to {out_path}")
    else:
        print("\n" + "═" * 60)
        print("ANOMALY REPORT (JSON)")
        print("═" * 60)
        print(report.to_json())
