"""Local SAT-SA report rendering for JSON, CSV, TXT, and PDF exports."""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from typing import Any


SUPPORTED_SCOPES = {"assessment", "findings", "analytics", "assets", "single_case", "custom"}
SUPPORTED_FORMATS = {"pdf", "json", "csv", "txt"}


def _metadata(scope: str) -> dict[str, str]:
    return {
        "title": f"SAT-SA {scope.replace('_', ' ').title()} Report",
        "scope": scope,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "disclaimer": "Prototype report based on synthetic/local operational evidence. Recommendations are decision support; final review remains with the analyst.",
    }


def build_report(scope: str, assessment: dict[str, Any], dashboard: dict[str, Any], priorities: list[dict[str, Any]], data_quality: dict[str, Any], ticket: dict[str, Any] | None = None) -> dict[str, Any]:
    if scope not in SUPPORTED_SCOPES:
        raise ValueError(f"Unsupported report scope: {scope}")
    report: dict[str, Any] = {"metadata": _metadata(scope)}
    if scope in {"assessment", "custom"}:
        report["assessment"] = {"score": assessment.get("overall_score"), "dimensions": assessment.get("dimensions", []), "records_assessed": assessment.get("lifecycle", {}).get("records_assessed", 0), "assets_monitored": len(assessment.get("assets", []))}
        report["findings_summary"] = assessment.get("findings", [])
        report["data_quality"] = data_quality
    if scope in {"findings", "custom"}:
        report["findings"] = assessment.get("findings", [])
    if scope in {"analytics", "custom"}:
        report["analytics_signals"] = {"summary": dashboard.get("summary", {}), "speed_anomalies": dashboard.get("speed_anomalies", []), "repetitive_notes": dashboard.get("repetitive_notes", []), "blind_spots": dashboard.get("blind_spots", [])}
    if scope in {"assets", "assessment", "custom"}:
        report["asset_monitoring"] = assessment.get("assets", [])
    if scope in {"assessment", "custom"}:
        report["priority_queue"] = priorities[:50]
    if scope == "single_case":
        if not ticket:
            raise ValueError("ticket_id is required for a single case report")
        report["case"] = ticket
    return report


def _lines(value: Any, indent: int = 0) -> list[str]:
    prefix = " " * indent
    if isinstance(value, dict):
        result: list[str] = []
        for key, item in value.items():
            result.append(f"{prefix}{key.replace('_', ' ').title()}:")
            result.extend(_lines(item, indent + 2))
        return result
    if isinstance(value, list):
        result = []
        for item in value:
            result.extend(_lines(item, indent))
        return result or [f"{prefix}(none)"]
    return [f"{prefix}{value}"]


def render_text(report: dict[str, Any]) -> bytes:
    return ("\n".join(["SAT-SA | Supervisory Analytics for SOC Assessment", "", *_lines(report)]) + "\n").encode("utf-8")


def render_json(report: dict[str, Any]) -> bytes:
    return json.dumps(report, indent=2, default=str).encode("utf-8")


def render_csv(report: dict[str, Any]) -> bytes:
    rows: list[dict[str, Any]] = []
    for key in ("findings", "priority_queue", "asset_monitoring"):
        values = report.get(key, [])
        if isinstance(values, list):
            rows.extend({"section": key, **{field: str(value) for field, value in row.items()}} for row in values if isinstance(row, dict))
    if not rows:
        rows = [{"section": "report", "content": json.dumps(report, default=str)}]
    fields = sorted({field for row in rows for field in row})
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def _fallback_pdf(text: bytes) -> bytes:
    safe = text.decode("utf-8", "replace").replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    content = f"BT /F1 9 Tf 40 760 Td ({safe[:4000]}) Tj ET".encode("latin-1", "replace")
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>", b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>", b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>", b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream"]
    pdf = b"%PDF-1.4\n"
    offsets = []
    for number, obj in enumerate(objects, 1):
        offsets.append(len(pdf))
        pdf += f"{number} 0 obj\n".encode() + obj + b"\nendobj\n"
    start = len(pdf)
    pdf += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    pdf += b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets)
    pdf += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF".encode()
    return pdf


def render_pdf(report: dict[str, Any]) -> bytes:
    text = render_text(report)
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        stream = io.BytesIO()
        document = canvas.Canvas(stream, pagesize=letter)
        y = 760
        document.setFont("Helvetica-Bold", 14)
        document.drawString(40, y, "SAT-SA | Supervisory Analytics for SOC Assessment")
        document.setFont("Helvetica", 9)
        for line in text.decode("utf-8").splitlines()[2:]:
            y -= 13
            if y < 40:
                document.showPage()
                y = 760
            document.drawString(40, y, line[:110])
        document.save()
        return stream.getvalue()
    except ImportError:
        return _fallback_pdf(text)


def render_report(report: dict[str, Any], format_name: str) -> tuple[bytes, str]:
    if format_name not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported report format: {format_name}")
    renderers = {"json": render_json, "csv": render_csv, "txt": render_text, "pdf": render_pdf}
    media_types = {"json": "application/json", "csv": "text/csv", "txt": "text/plain", "pdf": "application/pdf"}
    return renderers[format_name](report), media_types[format_name]
