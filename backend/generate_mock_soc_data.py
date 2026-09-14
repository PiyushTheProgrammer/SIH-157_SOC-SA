"""
SAT-SA — Phase 1: Mock SOC Data Generator (The Synthesizer)
============================================================
Generates 10,000 synthetic SOC alert tickets and a 50-asset inventory.
Intentionally injects three classes of anomalies:
  1. Speed Anomalies   — CRITICAL tickets closed in < 15s, no escalation.
  2. Repetitive Notes   — Analysts paste identical resolution text across
                          disparate alert types.
  3. Telemetry Blind Spots — Critical assets with ZERO alerts over 30 days.

Usage:
    python generate_mock_soc_data.py          # writes to data/
    python generate_mock_soc_data.py --outdir /custom/path

All processing is 100 % offline — no network calls.
"""

import argparse
import csv
import os
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path

# ──────────────────────────────────────────────
# CONSTANTS
# ──────────────────────────────────────────────

TOTAL_TICKETS = 10_000
NUM_ASSETS = 50
NUM_ANALYSTS = 15
TIME_WINDOW_DAYS = 30
SEED = 42  # reproducible runs

# Severity distribution for *normal* tickets
SEVERITY_WEIGHTS = {
    "LOW": 0.35,
    "MEDIUM": 0.30,
    "HIGH": 0.25,
    "CRITICAL": 0.10,
}

ALERT_TYPES = [
    "Malware Detection",
    "Brute Force Attempt",
    "Data Exfiltration",
    "Phishing Email",
    "Unauthorized Access",
    "Privilege Escalation",
    "DDoS Attack",
    "Insider Threat",
    "Ransomware",
    "Port Scan",
    "SQL Injection",
    "XSS Attack",
    "DNS Tunneling",
    "Lateral Movement",
    "C2 Communication",
]

ANALYST_NAMES = [
    "Ananya Sharma",
    "Rajesh Kumar",
    "Priya Patel",
    "Vikram Singh",
    "Meera Iyer",
    "Arjun Nair",
    "Kavita Deshmukh",
    "Sanjay Gupta",
    "Neha Joshi",
    "Rohit Malhotra",
    "Deepa Reddy",
    "Amit Verma",
    "Sunita Rao",
    "Karan Mehta",
    "Pooja Chauhan",
]

SHIFTS = ["DAY", "SWING", "NIGHT"]

# ──────────────────────────────────────────────
# Generic resolution notes used for anomaly injection
# These are intentionally shallow / copy-paste phrases.
# ──────────────────────────────────────────────
GENERIC_NOTES = [
    "Resolved per SOP.",
    "False positive, no action needed.",
    "Ticket auto-closed after initial review.",
    "No threat detected upon investigation.",
    "Issue resolved. Closing ticket.",
]

# Realistic resolution note templates for normal tickets
REALISTIC_NOTE_TEMPLATES = [
    "Investigated {alert_type} on {asset}. Contained threat by isolating the host and running full AV scan. Root cause: {cause}.",
    "Confirmed true positive for {alert_type}. Blocked source IP at perimeter firewall. Notified asset owner in {dept}.",
    "Triaged {alert_type} alert from {asset}. Correlated with SIEM logs — determined to be benign activity from scheduled {cause}.",
    "Escalated {alert_type} to Tier-2. Forensic analysis revealed {cause}. Remediation applied, monitoring for recurrence.",
    "Reviewed {alert_type} targeting {asset}. Source identified as internal penetration test. Verified with {dept} team lead.",
    "Detected {alert_type} pattern on {asset}. Updated IDS signatures and added source to watchlist. {cause} confirmed.",
    "Performed deep-dive on {alert_type}. Memory dump analysis showed no IOCs. Likely caused by {cause}. Closing as benign.",
    "Responded to {alert_type} on {asset}. Quarantined suspicious binary, submitted hash to local sandbox. Result: {cause}.",
]

ROOT_CAUSES = [
    "misconfigured service account",
    "outdated vulnerability scanner signatures",
    "scheduled maintenance script execution",
    "legitimate admin remote session",
    "legacy application compatibility issue",
    "expired SSL certificate renewal process",
    "network topology change during patching",
    "test traffic from red-team exercise",
]

DEPARTMENTS = [
    "Finance",
    "Engineering",
    "HR",
    "Operations",
    "Legal",
    "IT Infrastructure",
    "Executive Office",
    "Research",
]

# ──────────────────────────────────────────────
# ASSET INVENTORY BUILDER
# ──────────────────────────────────────────────

# 5 critical assets that will intentionally receive ZERO alerts
SILENT_CRITICAL_ASSETS = [
    ("prod-db-01", "CRITICAL", "Database Server", "IT Infrastructure"),
    ("prod-auth-srv", "CRITICAL", "Authentication Server", "Engineering"),
    ("prod-pay-gw", "CRITICAL", "Payment Gateway", "Finance"),
    ("prod-vault-01", "CRITICAL", "Secrets Vault", "IT Infrastructure"),
    ("prod-ci-master", "CRITICAL", "CI/CD Controller", "Engineering"),
]

ASSET_TEMPLATES = [
    # (prefix, criticality, asset_type, department)
    ("prod-web-{i}", "HIGH", "Web Server", "Engineering"),
    ("prod-app-{i}", "HIGH", "Application Server", "Engineering"),
    ("prod-db-{i}", "CRITICAL", "Database Server", "IT Infrastructure"),
    ("stg-web-{i}", "MEDIUM", "Web Server", "Engineering"),
    ("stg-app-{i}", "MEDIUM", "Application Server", "Engineering"),
    ("dev-ws-{i}", "LOW", "Workstation", "Engineering"),
    ("corp-ws-{i}", "LOW", "Workstation", "Operations"),
    ("fin-ws-{i}", "MEDIUM", "Workstation", "Finance"),
    ("hr-ws-{i}", "LOW", "Workstation", "HR"),
    ("exec-ws-{i}", "MEDIUM", "Workstation", "Executive Office"),
    ("net-fw-{i}", "HIGH", "Firewall", "IT Infrastructure"),
    ("net-sw-{i}", "MEDIUM", "Network Switch", "IT Infrastructure"),
    ("mail-srv-{i}", "HIGH", "Mail Server", "IT Infrastructure"),
    ("file-srv-{i}", "MEDIUM", "File Server", "Operations"),
    ("vpn-gw-{i}", "HIGH", "VPN Gateway", "IT Infrastructure"),
]


def build_asset_inventory() -> list[dict]:
    """Build a 50-asset inventory including 5 'silent' critical assets."""
    assets: list[dict] = []

    # Add the 5 silent critical assets first
    for hostname, crit, atype, dept in SILENT_CRITICAL_ASSETS:
        assets.append(
            {
                "asset_id": hostname,
                "asset_criticality": crit,
                "asset_type": atype,
                "department": dept,
            }
        )

    # Fill remaining slots from templates
    idx = 1
    while len(assets) < NUM_ASSETS:
        tpl = ASSET_TEMPLATES[idx % len(ASSET_TEMPLATES)]
        hostname = tpl[0].format(i=idx)
        # Skip if it would collide with a silent asset
        if hostname not in {a["asset_id"] for a in assets}:
            assets.append(
                {
                    "asset_id": hostname,
                    "asset_criticality": tpl[1],
                    "asset_type": tpl[2],
                    "department": tpl[3],
                }
            )
        idx += 1

    return assets


# ──────────────────────────────────────────────
# TICKET GENERATORS
# ──────────────────────────────────────────────


def _random_ip() -> str:
    """Generate a random RFC-1918 internal IP address."""
    return f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"


def _random_timestamp(rng_start: datetime, rng_end: datetime) -> datetime:
    """Return a random datetime between rng_start and rng_end."""
    delta = rng_end - rng_start
    offset = random.random() * delta.total_seconds()
    return rng_start + timedelta(seconds=offset)


def _normal_time_to_close(severity: str) -> int:
    """Return a realistic time-to-close (seconds) based on severity."""
    ranges = {
        "CRITICAL": (1800, 14400),   # 30 min – 4 hrs
        "HIGH": (900, 7200),         # 15 min – 2 hrs
        "MEDIUM": (600, 3600),       # 10 min – 1 hr
        "LOW": (300, 1800),          # 5 min – 30 min
    }
    lo, hi = ranges[severity]
    return random.randint(lo, hi)


def _normal_time_to_ack(severity: str) -> int:
    """Return a realistic time-to-acknowledge (seconds) based on severity."""
    ranges = {
        "CRITICAL": (10, 120),
        "HIGH": (30, 300),
        "MEDIUM": (60, 600),
        "LOW": (120, 900),
    }
    lo, hi = ranges[severity]
    return random.randint(lo, hi)


def _realistic_note(alert_type: str, asset: str, dept: str) -> str:
    """Generate a plausible, unique resolution note."""
    template = random.choice(REALISTIC_NOTE_TEMPLATES)
    cause = random.choice(ROOT_CAUSES)
    return template.format(alert_type=alert_type, asset=asset, dept=dept, cause=cause)


def generate_normal_ticket(
    ticket_num: int,
    eligible_assets: list[dict],
    ts_start: datetime,
    ts_end: datetime,
) -> dict:
    """Generate a single normal (non-anomalous) SOC ticket."""
    severity = random.choices(
        list(SEVERITY_WEIGHTS.keys()),
        weights=list(SEVERITY_WEIGHTS.values()),
        k=1,
    )[0]
    asset = random.choice(eligible_assets)
    alert_type = random.choice(ALERT_TYPES)
    analyst = random.choice(ANALYST_NAMES)
    timestamp = _random_timestamp(ts_start, ts_end)

    ttc = _normal_time_to_close(severity)
    tta = _normal_time_to_ack(severity)

    # CRITICAL alerts have a ~60 % escalation rate; others much lower
    escalation_rates = {"CRITICAL": 0.60, "HIGH": 0.30, "MEDIUM": 0.10, "LOW": 0.02}
    escalated = random.random() < escalation_rates[severity]

    shift = _shift_from_hour(timestamp.hour)

    return {
        "ticket_id": f"TKT-{ticket_num:06d}",
        "timestamp": timestamp.isoformat(),
        "alert_severity": severity,
        "alert_type": alert_type,
        "source_ip": _random_ip(),
        "dest_asset": asset["asset_id"],
        "assigned_analyst": analyst,
        "time_to_acknowledge": tta,
        "time_to_close": ttc,
        "resolution_notes": _realistic_note(alert_type, asset["asset_id"], asset["department"]),
        "escalated": escalated,
        "shift": shift,
    }


def generate_speed_anomaly_ticket(
    ticket_num: int,
    eligible_assets: list[dict],
    ts_start: datetime,
    ts_end: datetime,
) -> dict:
    """
    Generate a speed-anomaly ticket:
    CRITICAL severity, closed in < 15 seconds, NOT escalated.
    """
    asset = random.choice(eligible_assets)
    alert_type = random.choice(ALERT_TYPES)
    analyst = random.choice(ANALYST_NAMES)
    timestamp = _random_timestamp(ts_start, ts_end)
    shift = _shift_from_hour(timestamp.hour)

    return {
        "ticket_id": f"TKT-{ticket_num:06d}",
        "timestamp": timestamp.isoformat(),
        "alert_severity": "CRITICAL",
        "alert_type": alert_type,
        "source_ip": _random_ip(),
        "dest_asset": asset["asset_id"],
        "assigned_analyst": analyst,
        "time_to_acknowledge": random.randint(1, 5),
        "time_to_close": random.randint(3, 14),  # < 15 seconds
        "resolution_notes": random.choice(GENERIC_NOTES),
        "escalated": False,
        "shift": shift,
    }


def generate_repetitive_note_tickets(
    start_ticket_num: int,
    batch_size: int,
    analyst: str,
    note: str,
    eligible_assets: list[dict],
    ts_start: datetime,
    ts_end: datetime,
) -> list[dict]:
    """
    Generate a batch of tickets for a single analyst, all using an identical
    generic resolution note across different alert types.
    """
    tickets = []
    # Ensure we spread across at least 3+ different alert types
    alert_types_pool = random.sample(ALERT_TYPES, k=min(batch_size, len(ALERT_TYPES)))

    for i in range(batch_size):
        asset = random.choice(eligible_assets)
        alert_type = alert_types_pool[i % len(alert_types_pool)]
        severity = random.choices(
            list(SEVERITY_WEIGHTS.keys()),
            weights=list(SEVERITY_WEIGHTS.values()),
            k=1,
        )[0]
        timestamp = _random_timestamp(ts_start, ts_end)
        shift = _shift_from_hour(timestamp.hour)

        tickets.append(
            {
                "ticket_id": f"TKT-{start_ticket_num + i:06d}",
                "timestamp": timestamp.isoformat(),
                "alert_severity": severity,
                "alert_type": alert_type,
                "source_ip": _random_ip(),
                "dest_asset": asset["asset_id"],
                "assigned_analyst": analyst,
                "time_to_acknowledge": _normal_time_to_ack(severity),
                "time_to_close": _normal_time_to_close(severity),
                "resolution_notes": note,  # <-- the identical note
                "escalated": random.random() < 0.15,
                "shift": shift,
            }
        )
    return tickets


def _shift_from_hour(hour: int) -> str:
    """Map hour of day to shift label."""
    if 6 <= hour < 14:
        return "DAY"
    elif 14 <= hour < 22:
        return "SWING"
    else:
        return "NIGHT"


def _add_lifecycle_evidence(ticket: dict) -> dict:
    """Add deterministic lifecycle evidence fields to legacy-compatible tickets."""
    severe = ticket["alert_severity"] in {"CRITICAL", "HIGH"}
    speed_gap = ticket["alert_severity"] == "CRITICAL" and ticket["time_to_close"] < 15
    repetitive_gap = ticket["resolution_notes"] in GENERIC_NOTES
    investigation_ok = not speed_gap
    evidence_ok = investigation_ok and not repetitive_gap
    escalation_required = severe
    escalation_recorded = bool(ticket["escalated"]) if escalation_required else False
    response_recorded = not speed_gap
    recovery_recorded = not speed_gap
    evidence_ref = f"EV-{ticket['ticket_id']}" if evidence_ok else ""
    return {
        **ticket,
        "case_id": f"CASE-{ticket['ticket_id'][4:]}",
        "investigation_started": ticket["timestamp"] if investigation_ok else "",
        "investigator": ticket["assigned_analyst"] if investigation_ok else "",
        "investigation_duration_seconds": max(ticket["time_to_close"] - ticket["time_to_acknowledge"], 0) if investigation_ok else 0,
        "evidence_attached": evidence_ok,
        "ioc_checked": investigation_ok,
        "logs_correlated": evidence_ok,
        "root_cause_documented": evidence_ok,
        "investigation_conclusion": ticket["resolution_notes"] if investigation_ok and not repetitive_gap else "",
        "escalation_required": escalation_required,
        "escalation_recorded": escalation_recorded,
        "escalation_timestamp": ticket["timestamp"] if escalation_recorded else "",
        "response_recorded": response_recorded,
        "response_action": "Containment and remediation recorded" if response_recorded else "",
        "recovery_recorded": recovery_recorded,
        "closure_recorded": True,
        "closure_reason": "Resolved per supplied record",
        "closure_evidence": evidence_ref,
        "evidence_reference": evidence_ref,
    }


# ──────────────────────────────────────────────
# MAIN ORCHESTRATOR
# ──────────────────────────────────────────────


def generate_dataset(outdir: str) -> None:
    """Generate the full synthetic dataset and write CSVs."""
    random.seed(SEED)
    os.makedirs(outdir, exist_ok=True)

    # ── Build asset inventory ──
    assets = build_asset_inventory()
    silent_ids = {a["asset_id"] for a in assets[:5]}  # first 5 are silent
    eligible_assets = [a for a in assets if a["asset_id"] not in silent_ids]

    # ── Time window ──
    ts_end = datetime.now()
    ts_start = ts_end - timedelta(days=TIME_WINDOW_DAYS)

    all_tickets: list[dict] = []
    ticket_counter = 1

    # ── Inject speed anomalies (~200 tickets) ──
    num_speed_anomalies = 200
    print(f"[Phase 1] Injecting {num_speed_anomalies} speed-anomaly tickets ...")
    for _ in range(num_speed_anomalies):
        all_tickets.append(
            generate_speed_anomaly_ticket(ticket_counter, eligible_assets, ts_start, ts_end)
        )
        ticket_counter += 1

    # ── Inject repetitive-note anomalies (~300 tickets) ──
    # Select 6 analysts, each gets a batch of ~50 tickets with an identical note
    rep_analysts = random.sample(ANALYST_NAMES, k=6)
    rep_notes_cycle = GENERIC_NOTES + [GENERIC_NOTES[0]]  # 6 notes for 6 analysts
    total_rep = 0
    print("[Phase 1] Injecting repetitive-note batches ...")
    for analyst, note in zip(rep_analysts, rep_notes_cycle):
        batch_size = random.randint(40, 60)
        batch = generate_repetitive_note_tickets(
            ticket_counter, batch_size, analyst, note, eligible_assets, ts_start, ts_end
        )
        all_tickets.extend(batch)
        ticket_counter += batch_size
        total_rep += batch_size
    print(f"           -> {total_rep} repetitive-note tickets across {len(rep_analysts)} analysts")

    # ── Fill remaining with normal tickets ──
    remaining = TOTAL_TICKETS - len(all_tickets)
    print(f"[Phase 1] Generating {remaining} normal tickets ...")
    for _ in range(remaining):
        all_tickets.append(
            generate_normal_ticket(ticket_counter, eligible_assets, ts_start, ts_end)
        )
        ticket_counter += 1

    # Shuffle to mix anomalies into the normal flow
    all_tickets = [_add_lifecycle_evidence(ticket) for ticket in all_tickets]
    random.shuffle(all_tickets)

    # ── Write soc_alerts.csv ──
    alerts_path = os.path.join(outdir, "soc_alerts.csv")
    fieldnames = [
        "ticket_id",
        "timestamp",
        "alert_severity",
        "alert_type",
        "source_ip",
        "dest_asset",
        "assigned_analyst",
        "time_to_acknowledge",
        "time_to_close",
        "resolution_notes",
        "escalated",
        "shift",
        "case_id",
        "investigation_started",
        "investigator",
        "investigation_duration_seconds",
        "evidence_attached",
        "ioc_checked",
        "logs_correlated",
        "root_cause_documented",
        "investigation_conclusion",
        "escalation_required",
        "escalation_recorded",
        "escalation_timestamp",
        "response_recorded",
        "response_action",
        "recovery_recorded",
        "closure_recorded",
        "closure_reason",
        "closure_evidence",
        "evidence_reference",
    ]
    with open(alerts_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_tickets)
    print(f"[Phase 1] [OK] Wrote {len(all_tickets)} tickets -> {alerts_path}")

    # ── Write asset_inventory.csv ──
    inv_path = os.path.join(outdir, "asset_inventory.csv")
    inv_fields = ["asset_id", "asset_criticality", "asset_type", "department"]
    with open(inv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=inv_fields)
        writer.writeheader()
        writer.writerows(assets)
    print(f"[Phase 1] [OK] Wrote {len(assets)} assets   -> {inv_path}")

    # ── Summary ──
    speed_count = sum(
        1
        for t in all_tickets
        if t["alert_severity"] == "CRITICAL" and t["time_to_close"] < 15
    )
    silent_in_tickets = silent_ids - {t["dest_asset"] for t in all_tickets}
    print("\n-- Injection Summary --")
    print(f"  Speed anomalies  (CRITICAL, <15s):   {speed_count}")
    print(f"  Repetitive-note tickets:             {total_rep}")
    print(f"  Silent critical assets (0 alerts):   {len(silent_in_tickets)} of {len(silent_ids)}")
    print("  [OK] Data generation complete.\n")


# ──────────────────────────────────────────────
# CLI ENTRY POINT
# ──────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="SAT-SA Mock SOC Data Generator (Phase 1)"
    )
    parser.add_argument(
        "--outdir",
        type=str,
        default=os.path.join(os.path.dirname(__file__), "data"),
        help="Output directory for CSV files (default: ./data)",
    )
    args = parser.parse_args()
    generate_dataset(args.outdir)
