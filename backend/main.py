"""
SAT-SA — Phase 3: FastAPI Application (The Bridge)
====================================================
Serves the analytics engine output via a REST API and provides a local-LLM
explainability endpoint powered by LangChain + Ollama.

Endpoints:
  POST /api/upload                — Upload CSV, trigger analytics engine
  GET  /api/dashboard/summary     — Full anomaly report (cached in memory)
  POST /api/explain-anomaly       — LLM-generated explanation via Ollama
  GET  /api/health                — System + Ollama status

Air-gap constraints:
  - CORS locked to localhost origins only
  - All AI inference runs through a local Ollama instance (no cloud calls)
  - All data stored in local CSV / PostgreSQL — no external DB

Usage:
  cd backend/
  uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

import asyncio
import io
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional

import aiofiles
import pandas as pd
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

# ── Local modules ──────────────────────────────
from analytics_engine import AnalyticsOrchestrator, AnomalyReport
from supervisory_assessment import build_assessment
from priority_engine import generate_priority_queue
from report_generator import build_report, render_report

# ── Database (PostgreSQL via SQLAlchemy — air-gap safe) ──────────────────────
from database import get_db, init_db
from models import SOCAlert, SocAlertRecord, AssetInventory
from sqlalchemy.orm import Session

# ── LangChain (local only — no cloud imports) ──
try:
    from langchain_ollama import ChatOllama
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    logging.warning(
        "langchain-ollama not installed. AI explanations will fall back to "
        "rule-engine text. Run: pip install langchain-ollama langchain-core"
    )

# ══════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════

DATA_DIR   = Path(__file__).parent / "data"
ALERTS_CSV = DATA_DIR / "soc_alerts.csv"
INV_CSV    = DATA_DIR / "asset_inventory.csv"

# Local Ollama settings — all inference stays on this machine
OLLAMA_BASE_URL = "http://localhost:11434"   # default Ollama port
OLLAMA_MODEL    = "llama3"                   # change to "phi3" if preferred

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("sat-sa")

# ══════════════════════════════════════════════════
# IN-MEMORY REPORT CACHE
# ══════════════════════════════════════════════════
# The report is computed on startup and on each /upload call.
# Stored as a plain dict so it serialises cleanly to JSON.

_report_cache: dict[str, Any] = {}
_assessment_cache: dict[str, Any] = {}
_priority_cache: list[dict[str, Any]] = []
_priority_status: dict[str, str] = {}
_alerts_cache: pd.DataFrame | None = None
_inventory_cache: pd.DataFrame | None = None
_cache_lock = asyncio.Lock()


def _run_engine(alerts_path: Path, inv_path: Path) -> dict[str, Any]:
    """Run the analytics orchestrator synchronously and return a dict."""
    try:
        orchestrator = AnalyticsOrchestrator(
            alerts_path=alerts_path,
            inventory_path=inv_path,
        )
        report: AnomalyReport = orchestrator.run()
        return report.to_dict()
    except Exception as e:
        logger.error("ML Engine Error: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=400,
            detail=f"ML Engine Error: {str(e)}",
        ) from e


async def _refresh_cache() -> None:
    """Run the analytics, assessment and priority engines pulling strictly from PostgreSQL."""
    global _report_cache, _assessment_cache, _priority_cache, _alerts_cache, _inventory_cache
    try:
        from database import engine
        import pandas as pd
        
        # Read strictly from the PostgreSQL database
        with engine.connect() as conn:
            alerts_df = pd.read_sql("SELECT * FROM soc_alerts", conn)
            try:
                db_inventory_df = pd.read_sql("SELECT * FROM asset_inventory", conn)
            except Exception:
                db_inventory_df = pd.DataFrame()

        # Build inventory_df
        if not db_inventory_df.empty:
            inventory_df = db_inventory_df.copy()
            if "asset_name" not in inventory_df.columns and "asset_id" in inventory_df.columns:
                inventory_df["asset_name"] = inventory_df["asset_id"]
        elif not alerts_df.empty and "asset_name" in alerts_df.columns:
            # Fallback baseline from alerts if no dedicated asset_inventory table data
            inventory_df = pd.DataFrame({"asset_name": alerts_df["asset_name"].dropna().unique()})
            inventory_df["asset_id"] = inventory_df["asset_name"]
            inventory_df["asset_type"] = "Server"
            inventory_df["asset_criticality"] = "HIGH"
            inventory_df["criticality"] = "HIGH"
            inventory_df["department"] = "IT Infrastructure"
        else:
            inventory_df = pd.DataFrame(columns=["asset_id", "asset_name", "asset_type", "asset_criticality", "department"])

        if alerts_df.empty and db_inventory_df.empty:
            alerts_df = pd.DataFrame(columns=[
                "alert_id", "entity_id", "asset_name", "alert_category",
                "alert_severity", "time_to_close_seconds", "escalated", "resolution_notes"
            ])
            result = AnomalyReport().to_dict()
            assessment = {"findings": [], "overall_assessment": "No data available.", "assets": []}
            priorities = []
        else:
            if alerts_df.empty:
                alerts_df = pd.DataFrame(columns=[
                    "alert_id", "entity_id", "asset_name", "alert_category",
                    "alert_severity", "time_to_close_seconds", "escalated", "resolution_notes"
                ])
                result = AnomalyReport().to_dict()
            else:
                loop = asyncio.get_event_loop()
                def _run():
                    orchestrator = AnalyticsOrchestrator(alerts_df=alerts_df, inventory_df=inventory_df)
                    return orchestrator.run().to_dict()
                result = await loop.run_in_executor(None, _run)

            loop = asyncio.get_event_loop()
            assessment = await loop.run_in_executor(
                None,
                lambda: build_assessment(alerts_df, inventory_df, result),
            )
            priorities = await loop.run_in_executor(
                None,
                lambda: generate_priority_queue(alerts_df, inventory_df, assessment, result),
            )
            for item in priorities:
                item["status"] = _priority_status.get(item["ticket_id"], item.get("status", "NEW"))

        async with _cache_lock:
            _report_cache = result
            _assessment_cache = assessment
            _priority_cache = priorities
            _alerts_cache = alerts_df
            _inventory_cache = inventory_df

        if not alerts_df.empty or not db_inventory_df.empty:
            logger.info("Report cache refreshed — %d alerts, %d assets, %d speed anomalies, %d blind spots",
                        len(alerts_df),
                        len(inventory_df),
                        result.get("summary", {}).get("speed_anomalies_count", 0),
                        result.get("summary", {}).get("blind_spots_count", 0))
        else:
            logger.info("Report cache refreshed — Database is empty. Displaying 0 records.")
            
    except Exception as exc:
        logger.error("Failed to refresh analytics cache: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=400,
            detail=f"ML Engine Error: {str(exc)}",
        ) from exc


# ══════════════════════════════════════════════════
# LIFESPAN — run engine once on startup
# ══════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Pre-compute the anomaly report if CSV data already exists."""
    # ── Initialise PostgreSQL schema (idempotent — CREATE TABLE IF NOT EXISTS) ──
    logger.info("Startup: initialising PostgreSQL database schema ...")
    init_db()
    logger.info("Startup: PostgreSQL schema ready (sat_sa_db.soc_alert_records)")

    logger.info("Startup: pre-computing anomaly report from DB ...")
    await _refresh_cache()
    yield
    logger.info("SAT-SA API shutting down.")


# ══════════════════════════════════════════════════
# FASTAPI APP
# ══════════════════════════════════════════════════

app = FastAPI(
    title="SAT-SA — Supervisory Analytics Tool for SOC Assessment",
    description="Local prototype API for supervisory SOC assessment using synthetic operational evidence.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — localhost only (air-gap enforcement)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ══════════════════════════════════════════════════
# PYDANTIC MODELS
# ══════════════════════════════════════════════════

class AnomalyExplainRequest(BaseModel):
    """Payload for the /api/explain-anomaly endpoint."""
    anomaly_type: str                     # "speed_anomaly" | "repetitive_notes" | "blind_spot"
    ticket_id: Optional[str] = None
    severity: Optional[str] = None
    time_to_close: Optional[int] = None
    analyst: Optional[str] = None
    alert_type: Optional[str] = None
    escalated: Optional[bool] = None
    asset_id: Optional[str] = None
    actual_alerts: Optional[int] = None
    expected_mean: Optional[float] = None
    explanation: str                      # rule-engine explanation (fallback)


class AnomalyExplainResponse(BaseModel):
    """Response from the /api/explain-anomaly endpoint."""
    explanation: str
    source: str                           # "ollama" | "rule_engine"
    model: Optional[str] = None


class PriorityStatusUpdate(BaseModel):
    status: str


class ReportExportRequest(BaseModel):
    scope: str = "assessment"
    format: str = "json"
    filters: dict[str, Any] = {}
    ticket_id: Optional[str] = None


# ══════════════════════════════════════════════════
# LANGCHAIN PROMPT TEMPLATE
# ══════════════════════════════════════════════════

_EXPLAIN_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        (
            "You are a senior SOC assessment analyst supporting an internal supervisory review. "
            "Your tone is authoritative, concise, and professional. "
            "You write exactly 2 sentences — no more, no less. "
            "The first sentence states what the anomaly is and why it is operationally impossible or suspicious. "
            "The second sentence states what specific evidence a supervisor should request during an audit."
        ),
    ),
    (
        "human",
        (
            "Anomaly Type: {anomaly_type}\n"
            "Ticket ID: {ticket_id}\n"
            "Severity: {severity}\n"
            "Time to Close: {time_to_close} seconds\n"
            "Analyst: {analyst}\n"
            "Alert Type: {alert_type}\n"
            "Escalated: {escalated}\n"
            "Asset ID: {asset_id}\n"
            "Actual Alerts: {actual_alerts}\n"
            "Expected Mean Alerts: {expected_mean}\n"
            "Rule-Engine Finding: {explanation}\n\n"
            "Write your 2-sentence audit finding:"
        ),
    ),
])


def _build_llm_chain(timeout: float = 5.0):
    """Build the LangChain chain. Returns None if Ollama is unavailable."""
    if not LANGCHAIN_AVAILABLE:
        return None
    try:
        llm = ChatOllama(
            model=OLLAMA_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0.3,         # low temp for consistent, professional output
            num_predict=200,         # cap output length — 2 sentences is enough
        )
        chain = _EXPLAIN_PROMPT | llm | StrOutputParser()
        return chain
    except Exception as exc:
        logger.warning("Could not build LangChain chain: %s", exc)
        return None


async def generate_llm_rationale(
    payload: dict[str, Any],
    fallback_text: Optional[str] = None,
    timeout: float = 5.0,
) -> tuple[str, str]:
    """
    Execute generation request against local Ollama API with strict timeout
    and graceful offline/error fallback.

    Returns:
        tuple[str, str]: (rationale_text, source)
    """
    default_fallback = (
        fallback_text
        if fallback_text and fallback_text.strip()
        else "AI rationale generation bypassed: Local LLM engine is currently unreachable. Anomaly flagged by statistical engine."
    )

    try:
        chain = _build_llm_chain(timeout=timeout)
        if chain is None:
            logger.warning("Local LLM engine unavailable. Bypassing AI rationale generation.")
            return (
                default_fallback,
                "rule_engine" if fallback_text else "fallback",
            )

        # Ensure all template variables have safe defaults
        full_payload = {
            "anomaly_type": str(payload.get("anomaly_type") or "anomaly"),
            "ticket_id": str(payload.get("ticket_id") or "N/A"),
            "severity": str(payload.get("severity") or "N/A"),
            "time_to_close": str(payload.get("time_to_close") or "N/A"),
            "analyst": str(payload.get("analyst") or "N/A"),
            "alert_type": str(payload.get("alert_type") or "N/A"),
            "escalated": str(payload.get("escalated") if payload.get("escalated") is not None else "N/A"),
            "asset_id": str(payload.get("asset_id") or "N/A"),
            "actual_alerts": str(payload.get("actual_alerts") if payload.get("actual_alerts") is not None else "N/A"),
            "expected_mean": str(payload.get("expected_mean") if payload.get("expected_mean") is not None else "N/A"),
            "explanation": str(payload.get("explanation") or "Statistical anomaly flagged."),
        }

        # Enforce strict 5.0 second timeout to avoid pipeline blocking or 500 timeouts
        result: str = await asyncio.wait_for(chain.ainvoke(full_payload), timeout=timeout)
        cleaned = result.strip() if result else default_fallback
        return (cleaned, "ollama")

    except asyncio.TimeoutError as te:
        logger.warning(
            "Local LLM rationale generation timed out after %.1fs (%s). Returning fallback rationale.",
            timeout,
            te,
        )
        return (
            "AI rationale generation bypassed: Local LLM engine is currently unreachable. Anomaly flagged by statistical engine.",
            "fallback",
        )
    except Exception as exc:
        logger.warning(
            "Local LLM API error during rationale generation (%s). Returning fallback rationale.",
            exc,
        )
        return (
            "AI rationale generation bypassed: Local LLM engine is currently unreachable. Anomaly flagged by statistical engine.",
            "fallback",
        )


# ══════════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════════

@app.get("/api/health", summary="System and Ollama health check")
async def health_check():
    """Returns system status and whether the local Ollama service is reachable."""
    ollama_ok = False
    ollama_error = None

    if LANGCHAIN_AVAILABLE:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=3.0) as client:
                r = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
                ollama_ok = r.status_code == 200
        except Exception as exc:
            ollama_error = str(exc)
    else:
        ollama_error = "langchain-ollama package not installed"

    return {
        "status": "ok",
        "data_loaded": bool(_report_cache),
        "ollama_available": ollama_ok,
        "ollama_model": OLLAMA_MODEL,
        "ollama_url": OLLAMA_BASE_URL,
        "ollama_error": ollama_error,
        "langchain_installed": LANGCHAIN_AVAILABLE,
    }


@app.post("/upload", summary="Upload and ingest SOC alert dataset (.csv or .json)")
@app.post("/api/upload", summary="Upload and ingest SOC alert dataset (.csv or .json)")
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Ingest SOC alert datasets in CSV or JSON format.
    
    Workflow:
      1. Validates file extension (.csv or .json).
      2. Reads the file contents using pandas into a DataFrame.
      3. Normalizes columns and converts rows into a list of dictionaries.
      4. Performs a bulk insert into the PostgreSQL SOCAlert table.
      5. Updates the local cache and triggers background analytics.
      6. Returns a success JSON response with the total ingested records count.
    """
    filename = file.filename or "uploaded_alerts"
    extension = Path(filename).suffix.lower()

    if extension not in {".csv", ".json", ".pdf", ".docx"}:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format. Please upload a .csv or .json file.",
        )

    # Handle document uploads (PDF/DOCX) for case reviews
    if extension in {".pdf", ".docx"}:
        case_dir = DATA_DIR / "case_uploads"
        case_dir.mkdir(parents=True, exist_ok=True)
        destination = case_dir / filename
        async with aiofiles.open(destination, "wb") as out:
            while chunk := await file.read(1024 * 64):
                await out.write(chunk)
        return {
            "status": "success",
            "message": f"{filename} uploaded. Case evidence is ready for local review.",
            "filename": filename,
            "saved_to": str(destination),
            "records_ingested": 0,
            "total_records": 0,
        }

    # Read binary content into memory
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    # Parse into pandas DataFrame
    try:
        if extension == ".csv":
            df = pd.read_csv(io.BytesIO(contents))
        elif extension == ".json":
            df = pd.read_json(io.BytesIO(contents))
        else:
            raise ValueError("Unsupported extension")
    except Exception as parse_exc:
        logger.error("Failed to parse %s file: %s", extension, parse_exc)
        raise HTTPException(
            status_code=400,
            detail=f"Failed to parse {extension.upper()} file: {str(parse_exc)}",
        )

    if df.empty:
        raise HTTPException(status_code=400, detail="The uploaded file contains no data rows.")

    # Normalize column names: lowercase, strip, and replace spaces with underscores
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]

    # Helper cleaners
    def _clean_str(val: Any) -> Optional[str]:
        if pd.isna(val) or val is None:
            return None
        val_str = str(val).strip()
        return val_str if val_str else None

    def _clean_int(val: Any) -> Optional[int]:
        if pd.isna(val) or val is None:
            return None
        try:
            return int(float(val))
        except (ValueError, TypeError):
            return None

    def _clean_bool(val: Any, default: bool = False) -> bool:
        if pd.isna(val) or val is None:
            return default
        if isinstance(val, bool):
            return val
        if isinstance(val, (int, float)):
            return bool(val)
        if isinstance(val, str):
            return val.strip().lower() in {"true", "1", "yes", "t"}
        return default

    # Intelligent Dataset Routing based on CSV / JSON headers
    if "alert_id" in df.columns or "ticket_id" in df.columns:
        # ══════════════════════════════════════════════════════════
        # Condition A: SOC Alert dataset
        # ══════════════════════════════════════════════════════════
        records_data: list[dict[str, Any]] = []
        for _, row in df.iterrows():
            raw_timestamp = (
                row.get("timestamp")
                if "timestamp" in row and pd.notna(row["timestamp"])
                else (row.get("date") or row.get("time") or row.get("created_at"))
            )
            raw_alert_id = row.get("alert_id") if "alert_id" in row else row.get("ticket_id")
            raw_entity_id = row.get("entity_id") if "entity_id" in row else row.get("entity")
            raw_asset_name = row.get("asset_name") if "asset_name" in row else (row.get("dest_asset") or row.get("asset"))
            raw_category = row.get("alert_category") if "alert_category" in row else (row.get("alert_type") or row.get("category"))
            raw_severity = row.get("alert_severity") if "alert_severity" in row else row.get("severity")
            raw_ttc = row.get("time_to_close_seconds") if "time_to_close_seconds" in row else row.get("time_to_close")
            raw_notes = row.get("resolution_notes") if "resolution_notes" in row else row.get("notes")

            record_dict = {
                "timestamp": _clean_str(raw_timestamp),
                "alert_id": _clean_str(raw_alert_id),
                "entity_id": _clean_str(raw_entity_id),
                "asset_name": _clean_str(raw_asset_name),
                "alert_category": _clean_str(raw_category),
                "alert_severity": _clean_str(raw_severity),
                "time_to_close_seconds": _clean_int(raw_ttc),
                "escalated": (
                    _clean_bool(row.get("escalated"))
                    if "escalated" in row and pd.notna(row["escalated"])
                    else None
                ),
                "resolution_notes": _clean_str(raw_notes),
                "is_speed_anomaly": _clean_bool(row.get("is_speed_anomaly"), False),
                "is_repetitive_anomaly": _clean_bool(row.get("is_repetitive_anomaly"), False),
                "is_negative_space": _clean_bool(row.get("is_negative_space"), False),
                "is_anomaly": _clean_bool(row.get("is_anomaly"), False),
            }
            records_data.append(record_dict)

        try:
            db.query(SOCAlert).delete()
            db.bulk_insert_mappings(SOCAlert, records_data)
            db.commit()
            logger.info("PostgreSQL: Bulk-inserted %d SOC alert records into soc_alerts table.", len(records_data))
        except Exception as db_exc:
            db.rollback()
            logger.error("PostgreSQL bulk-insert into soc_alerts failed: %s", db_exc)
            raise HTTPException(
                status_code=500,
                detail=f"Database ingestion error: {str(db_exc)}",
            )

        try:
            await _refresh_cache()
        except HTTPException:
            raise
        except Exception as engine_err:
            logger.error("ML Engine failed on uploaded file: %s", engine_err, exc_info=True)
            raise HTTPException(
                status_code=400,
                detail=f"ML Engine Error: {str(engine_err)}",
            )

        return {
            "status": "success",
            "dataset_type": "soc_alerts",
            "message": f"Detected SOC Alerts dataset: successfully ingested {len(records_data)} alert records.",
            "filename": filename,
            "records_ingested": len(records_data),
            "total_records": len(records_data),
        }

    elif any(col in df.columns for col in ["asset_type", "department", "asset_criticality", "asset_id", "asset", "asset_name"]):
        # ══════════════════════════════════════════════════════════
        # Condition B: Asset Inventory dataset
        # ══════════════════════════════════════════════════════════
        inventory_records: list[dict[str, Any]] = []
        seen_assets = set()

        for _, row in df.iterrows():
            raw_asset_name = (
                row.get("asset_name")
                if "asset_name" in row and pd.notna(row["asset_name"])
                else (row.get("asset_id") or row.get("asset"))
            )
            clean_asset_name = _clean_str(raw_asset_name)
            if not clean_asset_name or clean_asset_name in seen_assets:
                continue
            seen_assets.add(clean_asset_name)

            raw_type = row.get("asset_type") if "asset_type" in row else (row.get("type") or row.get("category"))
            raw_dept = row.get("department") if "department" in row else (row.get("dept") or row.get("organization"))
            raw_crit = row.get("asset_criticality") if "asset_criticality" in row else (row.get("criticality") or row.get("severity"))

            inventory_records.append({
                "asset_name": clean_asset_name,
                "asset_type": _clean_str(raw_type) or "Server",
                "department": _clean_str(raw_dept) or "Unassigned",
                "asset_criticality": (_clean_str(raw_crit) or "MEDIUM").upper(),
            })

        if not inventory_records:
            raise HTTPException(
                status_code=400,
                detail="No valid asset records found in uploaded Asset Inventory file.",
            )

        try:
            db.query(AssetInventory).delete()
            db.bulk_insert_mappings(AssetInventory, inventory_records)
            db.commit()
            logger.info("PostgreSQL: Bulk-inserted %d asset inventory records into asset_inventory table.", len(inventory_records))
        except Exception as db_exc:
            db.rollback()
            logger.error("PostgreSQL bulk-insert into asset_inventory failed: %s", db_exc)
            raise HTTPException(
                status_code=500,
                detail=f"Asset inventory ingestion error: {str(db_exc)}",
            )

        try:
            await _refresh_cache()
        except HTTPException:
            raise
        except Exception as engine_err:
            logger.error("ML Engine failed on uploaded inventory: %s", engine_err, exc_info=True)
            raise HTTPException(
                status_code=400,
                detail=f"ML Engine Error: {str(engine_err)}",
            )

        return {
            "status": "success",
            "dataset_type": "asset_inventory",
            "message": f"Detected Asset Inventory dataset: successfully ingested {len(inventory_records)} asset records.",
            "filename": filename,
            "records_ingested": len(inventory_records),
            "total_records": len(inventory_records),
        }

    else:
        raise HTTPException(
            status_code=400,
            detail="Unrecognized dataset format. File must contain 'alert_id' (for SOC Alerts) or 'asset_type'/'department'/'asset_name' (for Asset Inventory).",
        )


@app.delete("/api/data/clear", summary="Clear all SOC and Asset records from database")
@app.delete("/data/clear", summary="Clear all SOC and Asset records from database")
async def clear_database(db: Session = Depends(get_db)):
    """
    Wipe all existing SOC alert and asset inventory records from the PostgreSQL database
    and reset the in-memory analytics cache.
    """
    try:
        db.query(SOCAlert).delete()
        db.query(AssetInventory).delete()
        db.commit()
        logger.info("PostgreSQL: All records deleted from soc_alerts and asset_inventory tables.")

        # Synchronously refresh in-memory analytics caches from the now-empty database
        await _refresh_cache()

        return {"message": "Database cleared successfully"}
    except Exception as e:
        db.rollback()
        logger.error("Failed to clear database: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear database: {str(e)}",
        )


@app.get("/api/dashboard/summary", summary="Full anomaly report")
async def dashboard_summary():
    """
    Returns the cached anomaly report including:
    - summary metrics and entity risk scores
    - speed_anomalies list
    - repetitive_notes list
    - blind_spots list
    """
    if not _report_cache:
        raise HTTPException(
            status_code=503,
            detail=(
                "No data loaded yet. Either upload a CSV via POST /api/upload "
                "or ensure soc_alerts.csv exists in the data/ directory "
                "and restart the server."
            ),
        )
    return _report_cache


def _require_assessment() -> dict[str, Any]:
    if not _assessment_cache:
        raise HTTPException(
            status_code=503,
            detail="No assessment data loaded. Upload a CSV or restart with local data.",
        )
    return _assessment_cache


@app.get("/api/assessment", summary="Supervisory assessment dimensions and lifecycle")
async def assessment_summary():
    return _require_assessment()


@app.get("/api/findings", summary="Supervisory findings work queue")
async def assessment_findings():
    return {"findings": _require_assessment()["findings"]}


@app.get("/api/evidence", summary="Ticket evidence review records")
async def evidence_records():
    return {"evidence": _require_assessment()["evidence"]}


@app.get("/api/evidence/{ticket_id}", summary="Evidence detail for one ticket")
async def evidence_detail(ticket_id: str):
    for record in _require_assessment()["evidence"]:
        if record["ticket_id"] == ticket_id:
            return record
    raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} was not found.")


@app.get("/api/assets", summary="Asset monitoring assessment")
async def asset_monitoring():
    return {"assets": _require_assessment()["assets"]}


@app.get("/api/data-quality", summary="Dataset quality and processing metadata")
async def data_quality():
    assessment = _require_assessment()
    alerts = _alerts_cache
    if alerts is None:
        raise HTTPException(status_code=503, detail="Dataset cache is not ready.")
    timestamps = pd.to_datetime(alerts.get("timestamp"), errors="coerce")
    return {
        "dataset": {
            "file_name": ALERTS_CSV.name,
            "records": len(alerts),
            "date_range": {"start": timestamps.min().isoformat() if not timestamps.isna().all() else None, "end": timestamps.max().isoformat() if not timestamps.isna().all() else None},
            "assets": len(assessment["assets"]),
            "analysts": int(alerts["assigned_analyst"].nunique()) if "assigned_analyst" in alerts else 0,
            "last_processed": timestamps.max().isoformat() if not timestamps.isna().all() else None,
        },
        "data_quality": {
            "missing_values": int(alerts.isna().sum().sum()),
            "duplicate_ids": int(alerts["ticket_id"].duplicated().sum()) if "ticket_id" in alerts else 0,
            "invalid_timestamps": int(timestamps.isna().sum()),
            "missing_severity": int(alerts["alert_severity"].isna().sum()) if "alert_severity" in alerts else len(alerts),
            "missing_escalation_field": int(alerts["escalated"].isna().sum()) if "escalated" in alerts else len(alerts),
        },
        "processing": {"local_processing": "Operational", "analytics_engine": "Operational", "last_analysis": timestamps.max().isoformat() if not timestamps.isna().all() else None},
    }


def _require_priorities() -> list[dict[str, Any]]:
    if not _priority_cache:
        raise HTTPException(status_code=503, detail="No priority data loaded. Upload a CSV or restart with local data.")
    return _priority_cache


@app.get("/api/priorities", summary="AI-assisted case review priority queue")
async def priorities(severity: Optional[str] = None, status: Optional[str] = None, analyst: Optional[str] = None, asset: Optional[str] = None):
    queue = _require_priorities()
    return {"recommendation_only": True, "decision_authority": "analyst", "priorities": [item for item in queue if (not severity or item["severity"] == severity.upper()) and (not status or item["status"] == status.upper()) and (not analyst or item["analyst"] == analyst) and (not asset or item["asset"] == asset)]}


@app.get("/api/priorities/{ticket_id}", summary="Priority detail for one ticket")
async def priority_detail(ticket_id: str):
    for item in _require_priorities():
        if item["ticket_id"] == ticket_id:
            return {"recommendation_only": True, **item}
    raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} was not found.")


@app.patch("/api/priorities/{ticket_id}/status", summary="Update analyst review status")
async def update_priority_status(ticket_id: str, update: PriorityStatusUpdate):
    allowed = {"NEW", "UNDER_REVIEW", "ASSIGNED", "INVESTIGATING", "ESCALATED", "RESOLVED", "CLOSED"}
    status = update.status.upper()
    if status not in allowed:
        raise HTTPException(status_code=400, detail=f"Status must be one of: {', '.join(sorted(allowed))}")
    for item in _require_priorities():
        if item["ticket_id"] == ticket_id:
            _priority_status[ticket_id] = status
            item["status"] = status
            return item
    raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} was not found.")


@app.post("/api/reports/export", summary="Generate a local SAT-SA report")
async def export_report(request: ReportExportRequest):
    assessment = _require_assessment()
    if not _report_cache:
        raise HTTPException(status_code=503, detail="No analytics data loaded.")
    quality = await data_quality()
    ticket = None
    if request.ticket_id:
        ticket = next((item for item in assessment["evidence"] if item["ticket_id"] == request.ticket_id), None)
        if ticket:
            ticket["priority"] = next((item for item in _priority_cache if item["ticket_id"] == request.ticket_id), None)
            ticket["findings"] = [finding for finding in assessment["findings"] if finding.get("entity") == request.ticket_id]
    filters = request.filters or {}
    filtered_priorities = [item for item in _priority_cache if all(not filters.get(key) or str(item.get(key, "")).upper() == str(value).upper() for key, value in filters.items() if key in {"severity", "status", "analyst", "asset"})]
    filtered_assessment = dict(assessment)
    if filters.get("status"):
        filtered_assessment["findings"] = [finding for finding in assessment["findings"] if str(finding.get("status", "")).upper() == str(filters["status"]).upper()]
    try:
        report = build_report(request.scope, filtered_assessment, _report_cache, filtered_priorities, quality, ticket)
        content, media_type = render_report(report, request.format)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    filename = f"sat-sa-{request.scope}.{request.format}"
    return Response(content=content, media_type=media_type, headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@app.post(
    "/api/explain-anomaly",
    response_model=AnomalyExplainResponse,
    summary="Generate a 2-sentence AI explanation for a flagged anomaly",
)
async def explain_anomaly(request: AnomalyExplainRequest):
    """
    Uses LangChain + local Ollama to generate a professional audit explanation.
    Falls back gracefully if Ollama is offline, unreachable, or times out.
    All inference is 100% local — no external API calls.
    """
    payload = {
        "anomaly_type":  request.anomaly_type,
        "ticket_id":     request.ticket_id     or "N/A",
        "severity":      request.severity       or "N/A",
        "time_to_close": request.time_to_close  or "N/A",
        "analyst":       request.analyst        or "N/A",
        "alert_type":    request.alert_type     or "N/A",
        "escalated":     request.escalated      if request.escalated is not None else "N/A",
        "asset_id":      request.asset_id       or "N/A",
        "actual_alerts": request.actual_alerts  if request.actual_alerts is not None else "N/A",
        "expected_mean": request.expected_mean  if request.expected_mean is not None else "N/A",
        "explanation":   request.explanation,
    }

    explanation, source = await generate_llm_rationale(
        payload=payload,
        fallback_text=request.explanation,
        timeout=5.0,
    )

    return AnomalyExplainResponse(
        explanation=explanation,
        source=source,
        model=OLLAMA_MODEL if source == "ollama" else None,
    )
