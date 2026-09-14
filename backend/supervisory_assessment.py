"""Deterministic supervisory assessment built on top of the anomaly engine.

This module deliberately treats missing records as missing evidence, not proof that
an operational action did not occur. It supports both the extended synthetic schema
and the original alert CSV through deterministic compatibility defaults.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd


DIMENSION_WEIGHTS = {
    "Detection": 0.15,
    "Investigation": 0.20,
    "Escalation": 0.15,
    "Response": 0.15,
    "Closure": 0.10,
    "Evidence Completeness": 0.15,
    "Monitoring": 0.10,
}


def _bool(value: Any, default: bool = False) -> bool:
    if pd.isna(value):
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "observed"}


def _text(value: Any, default: str = "") -> str:
    if value is None or pd.isna(value):
        return default
    return str(value)


def _has_column(df: pd.DataFrame, name: str) -> bool:
    return name in df.columns


def _observed(row: pd.Series, field: str, fallback: bool = False) -> bool:
    return _bool(row[field], fallback) if field in row else fallback


def _derive_ticket(row: pd.Series) -> dict[str, Any]:
    severity = _text(row.get("alert_severity"), "UNKNOWN").upper()
    notes = _text(row.get("resolution_notes"))
    legacy_escalated = _bool(row.get("escalated"))
    has_notes = bool(notes.strip())
    speed_anomaly = severity in {"CRITICAL", "HIGH"} and int(row.get("time_to_close", 0) or 0) < ({"CRITICAL": 120, "HIGH": 60}.get(severity, 0))
    repetitive_note = notes in {"Resolved per SOP.", "False positive, no action needed.", "Ticket auto-closed after initial review.", "No threat detected upon investigation.", "Issue resolved. Closing ticket."}
    investigation = _observed(row, "investigation_started", has_notes)
    investigator = _text(row.get("investigator"), _text(row.get("assigned_analyst")))
    evidence_attached = _observed(row, "evidence_attached", has_notes and not (speed_anomaly or repetitive_note))
    ioc_checked = _observed(row, "ioc_checked", has_notes and not speed_anomaly)
    logs_correlated = _observed(row, "logs_correlated", has_notes and not repetitive_note)
    conclusion = _text(row.get("investigation_conclusion"), notes if not repetitive_note else "")
    escalation_required = _observed(row, "escalation_required", severity in {"CRITICAL", "HIGH"})
    escalation_recorded = _observed(row, "escalation_recorded", legacy_escalated)
    response_recorded = _observed(row, "response_recorded", has_notes and not speed_anomaly)
    recovery_recorded = _observed(row, "recovery_recorded", has_notes and not speed_anomaly)
    closure_recorded = _observed(row, "closure_recorded", has_notes)
    closure_reason = _text(row.get("closure_reason"), "Resolved per supplied record" if closure_recorded else "")
    closure_evidence = _text(row.get("closure_evidence"), _text(row.get("evidence_reference")) if closure_recorded else "")
    expected = {
        "Alert": True,
        "Case": bool(_text(row.get("case_id"), _text(row.get("ticket_id")))),
        "Investigation": investigation,
        "Escalation": (not escalation_required) or escalation_recorded,
        "Response": response_recorded,
        "Recovery": recovery_recorded,
        "Closure": closure_recorded,
    }
    return {
        "ticket_id": _text(row.get("ticket_id")),
        "severity": severity,
        "alert_type": _text(row.get("alert_type")),
        "analyst": _text(row.get("assigned_analyst")),
        "asset": _text(row.get("dest_asset")),
        "case_id": _text(row.get("case_id"), _text(row.get("ticket_id"))),
        "timestamp": _text(row.get("timestamp")),
        "stages": {
            "Alert": {"status": "Observed", "timestamp": _text(row.get("timestamp")), "actor": "System", "evidence_reference": _text(row.get("ticket_id")), "notes": "Alert record supplied."},
            "Case": {"status": "Observed" if expected["Case"] else "Missing", "timestamp": _text(row.get("timestamp")), "actor": "System", "evidence_reference": _text(row.get("case_id")), "notes": "Case reference observed." if expected["Case"] else "Evidence not observed in the supplied records."},
            "Investigation": {"status": "Observed" if investigation else "Missing", "timestamp": _text(row.get("investigation_started"), _text(row.get("timestamp"))), "actor": investigator, "evidence_reference": _text(row.get("evidence_reference")), "notes": "Investigation evidence observed." if investigation else "Available records do not demonstrate completion of the investigation step."},
            "Escalation": {"status": "Not Required" if not escalation_required else ("Observed" if escalation_recorded else "Missing"), "timestamp": _text(row.get("escalation_timestamp")), "actor": investigator, "evidence_reference": _text(row.get("evidence_reference")), "notes": "Escalation evidence observed." if escalation_recorded else "Evidence not observed in the supplied records."},
            "Response": {"status": "Observed" if response_recorded else "Missing", "timestamp": _text(row.get("timestamp")), "actor": investigator, "evidence_reference": _text(row.get("evidence_reference")), "notes": _text(row.get("response_action"), "Response evidence observed." if response_recorded else "Evidence not observed in the supplied records.")},
            "Recovery": {"status": "Observed" if recovery_recorded else "Missing", "timestamp": _text(row.get("timestamp")), "actor": investigator, "evidence_reference": _text(row.get("evidence_reference")), "notes": "Recovery evidence observed." if recovery_recorded else "Evidence not observed in the supplied records."},
            "Closure": {"status": "Observed" if closure_recorded else "Missing", "timestamp": _text(row.get("timestamp")), "actor": investigator, "evidence_reference": closure_evidence, "notes": closure_reason or "Evidence not observed in the supplied records."},
        },
        "expected": expected,
        "evidence_attached": evidence_attached,
        "ioc_checked": ioc_checked,
        "logs_correlated": logs_correlated,
        "conclusion": bool(conclusion.strip()),
        "escalation_required": escalation_required,
        "speed_anomaly": speed_anomaly,
        "repetitive_note": repetitive_note,
    }


def _score_ticket(ticket: dict[str, Any]) -> dict[str, float]:
    investigation_items = [ticket["expected"]["Investigation"], bool(ticket["analyst"]), ticket["evidence_attached"], ticket["ioc_checked"], ticket["logs_correlated"], ticket["conclusion"]]
    investigation = sum(value * weight for value, weight in zip(investigation_items, [20, 15, 20, 15, 15, 15]))
    escalation = 100 if not ticket["escalation_required"] or ticket["expected"]["Escalation"] else 0
    response = sum([ticket["expected"]["Response"], bool(ticket["stages"]["Response"]["notes"]), bool(ticket["stages"]["Response"]["evidence_reference"])]) / 3 * 100
    closure = sum([ticket["expected"]["Closure"], bool(ticket["stages"]["Closure"]["notes"]), bool(ticket["stages"]["Closure"]["evidence_reference"]), ticket["conclusion"]]) / 4 * 100
    evidence_items = [ticket["evidence_attached"], ticket["ioc_checked"], ticket["logs_correlated"], ticket["stages"]["Escalation"]["status"] in {"Observed", "Not Required"}, ticket["stages"]["Response"]["status"] == "Observed", ticket["stages"]["Closure"]["status"] == "Observed"]
    return {"Investigation": round(investigation, 1), "Escalation": round(escalation, 1), "Response": round(response, 1), "Closure": round(closure, 1), "Evidence Completeness": round(sum(evidence_items) / len(evidence_items) * 100, 1)}


def build_assessment(alerts_df: pd.DataFrame, inventory_df: pd.DataFrame, report: dict[str, Any] | None = None) -> dict[str, Any]:
    tickets = [_derive_ticket(row) for _, row in alerts_df.iterrows()]
    ticket_scores = [_score_ticket(ticket) for ticket in tickets]
    attention_findings: list[dict[str, Any]] = []
    for ticket in tickets:
        if ticket["escalation_required"] and not ticket["expected"]["Escalation"]:
            attention_findings.append({"finding_id": f"ESC-{ticket['ticket_id']}", "dimension": "Escalation", "entity": ticket["ticket_id"], "observation": "Required escalation evidence was not observed.", "severity": ticket["severity"], "evidence_state": "Missing", "recommended_review": "Verify escalation record and supporting evidence.", "status": "Open", "finding_type": "Escalation gap", "analyst": ticket["analyst"], "asset": ticket["asset"]})
        if not ticket["expected"]["Investigation"]:
            attention_findings.append({"finding_id": f"INV-{ticket['ticket_id']}", "dimension": "Investigation", "entity": ticket["ticket_id"], "observation": "Available records do not demonstrate completion of the investigation step.", "severity": ticket["severity"], "evidence_state": "Missing", "recommended_review": "Verify investigation record and supporting evidence.", "status": "Open", "finding_type": "Missing evidence", "analyst": ticket["analyst"], "asset": ticket["asset"]})
        if not ticket["expected"]["Response"] and ticket["severity"] in {"CRITICAL", "HIGH"}:
            attention_findings.append({"finding_id": f"RESP-{ticket['ticket_id']}", "dimension": "Response", "entity": ticket["ticket_id"], "observation": "Response evidence was not observed in the supplied records.", "severity": ticket["severity"], "evidence_state": "Missing", "recommended_review": "Verify response action and evidence reference.", "status": "Open", "finding_type": "Response evidence gap", "analyst": ticket["analyst"], "asset": ticket["asset"]})
        if ticket["repetitive_note"]:
            attention_findings.append({"finding_id": f"DOC-{ticket['ticket_id']}", "dimension": "Evidence Completeness", "entity": ticket["ticket_id"], "observation": "Documentation similarity signal indicates limited ticket-specific detail.", "severity": ticket["severity"], "evidence_state": "Review", "recommended_review": "Review supporting investigation evidence.", "status": "Open", "finding_type": "Repetitive documentation", "analyst": ticket["analyst"], "asset": ticket["asset"]})
    blind_spots = (report or {}).get("blind_spots", [])
    for blind in blind_spots:
        attention_findings.append({"finding_id": f"MON-{blind['asset_id']}", "dimension": "Monitoring", "entity": blind["asset_id"], "observation": "Telemetry volume is materially below the peer baseline.", "severity": blind["criticality"], "evidence_state": "Missing", "recommended_review": "Verify telemetry collection and monitoring coverage.", "status": "Open", "finding_type": "Telemetry blind spot", "analyst": "", "asset": blind["asset_id"]})
    dimensions: list[dict[str, Any]] = []
    for name, weight in DIMENSION_WEIGHTS.items():
        if name == "Detection": score, logic = 100.0, "Alert record present for each assessed ticket."
        elif name == "Monitoring":
            score = max(0.0, 100.0 - (len(blind_spots) / max(len(inventory_df), 1) * 100))
            logic = "100 minus the percentage of inventory assets with telemetry coverage gaps."
        else:
            score = sum(item[name] for item in ticket_scores) / max(len(ticket_scores), 1)
            logic = {"Investigation": "20 start + 15 investigator + 20 evidence + 15 IOC + 15 logs + 15 conclusion.", "Escalation": "100 when required evidence is observed or escalation is not required; otherwise 0.", "Response": "Observed response record, action notes, and evidence reference averaged equally.", "Closure": "Closure record, reason, supporting evidence, and conclusion averaged equally.", "Evidence Completeness": "Observed expected evidence items divided by expected evidence items."}[name]
        missing = sum(1 for ticket in tickets if (name in ticket_scores[0] if ticket_scores else False) and ticket_scores[tickets.index(ticket)][name] < 100) if name not in {"Detection", "Monitoring"} else len(blind_spots) if name == "Monitoring" else 0
        dimensions.append({"dimension": name, "score": round(score, 1), "weight": weight, "records_assessed": len(tickets) if name != "Monitoring" else len(inventory_df), "records_missing_evidence": missing, "finding_count": sum(1 for finding in attention_findings if finding["dimension"] == name), "status": "Adequate" if score >= 75 else ("Review" if score >= 60 else "Attention"), "assessment_logic": logic})
    overall = round(sum(item["score"] * item["weight"] for item in dimensions), 1)
    evidence = []
    for ticket in tickets:
        item = {key: ticket[key] for key in ["ticket_id", "severity", "alert_type", "analyst", "asset", "case_id", "timestamp", "stages"]}
        item["evidence_completeness"] = next(score["Evidence Completeness"] for score, source in zip(ticket_scores, tickets) if source["ticket_id"] == ticket["ticket_id"])
        item["assessment"] = "Attention" if any(f["entity"] == ticket["ticket_id"] for f in attention_findings) else "Adequate"
        evidence.append(item)
    asset_counts = alerts_df["dest_asset"].value_counts().to_dict() if "dest_asset" in alerts_df else {}
    assets = []
    for _, asset in inventory_df.iterrows():
        peer = inventory_df[inventory_df["asset_criticality"] == asset["asset_criticality"]]["asset_id"].map(asset_counts).fillna(0)
        volume = int(asset_counts.get(asset["asset_id"], 0))
        expected = round(float(peer.mean()), 1) if len(peer) else 0.0
        assets.append({"asset": asset["asset_id"], "criticality": asset["asset_criticality"], "type": asset["asset_type"], "department": asset["department"], "alert_volume": volume, "expected_peer_volume": expected, "deviation": round(volume - expected, 1), "monitoring_status": "Telemetry silence requiring review" if volume == 0 and asset["asset_criticality"] in {"CRITICAL", "HIGH"} else "Observed"})
    return {"overall_score": overall, "dimensions": dimensions, "findings": attention_findings, "evidence": evidence, "assets": assets, "lifecycle": {"stages": ["Alert", "Case", "Investigation", "Escalation", "Response", "Recovery", "Closure"], "records_assessed": len(tickets), "finding": "Required evidence was not observed in the supplied records where applicable."}, "basis": "Missing evidence is an assessment signal, not proof that an action did not happen.", "analytics_signal_count": (report or {}).get("summary", {}).get("total_flagged_anomalies", 0)}
