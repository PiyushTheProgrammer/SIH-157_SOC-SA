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
  - All data stored in local CSV / SQLite — no external DB

Usage:
  cd backend/
  uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional

import aiofiles
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ── Local modules ──────────────────────────────
from analytics_engine import AnalyticsOrchestrator, AnomalyReport

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
_cache_lock = asyncio.Lock()


def _run_engine(alerts_path: Path, inv_path: Path) -> dict[str, Any]:
    """Run the analytics orchestrator synchronously and return a dict."""
    orchestrator = AnalyticsOrchestrator(
        alerts_path=alerts_path,
        inventory_path=inv_path,
    )
    report: AnomalyReport = orchestrator.run()
    return report.to_dict()


async def _refresh_cache(alerts_path: Path, inv_path: Path) -> None:
    """Run the engine in a thread pool (non-blocking) and update the cache."""
    global _report_cache
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _run_engine, alerts_path, inv_path)
    async with _cache_lock:
        _report_cache = result
    logger.info("Report cache refreshed — %d speed anomalies, %d blind spots",
                result["summary"]["speed_anomalies_count"],
                result["summary"]["blind_spots_count"])


# ══════════════════════════════════════════════════
# LIFESPAN — run engine once on startup
# ══════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Pre-compute the anomaly report if CSV data already exists."""
    if ALERTS_CSV.exists() and INV_CSV.exists():
        logger.info("Startup: pre-computing anomaly report ...")
        await _refresh_cache(ALERTS_CSV, INV_CSV)
    else:
        logger.warning(
            "Startup: CSV data not found at %s. "
            "Upload a file via POST /api/upload to populate the dashboard.",
            DATA_DIR,
        )
    yield
    logger.info("SAT-SA API shutting down.")


# ══════════════════════════════════════════════════
# FASTAPI APP
# ══════════════════════════════════════════════════

app = FastAPI(
    title="SAT-SA — Supervisory Analytics Tool for SOC Assessment",
    description="Air-gapped anomaly detection API for government SOC auditors.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — localhost only (air-gap enforcement)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
    ],
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


# ══════════════════════════════════════════════════
# LANGCHAIN PROMPT TEMPLATE
# ══════════════════════════════════════════════════

_EXPLAIN_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        (
            "You are a senior cybersecurity auditor reporting to NCIIPC supervisors. "
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


def _build_llm_chain():
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


@app.post("/api/upload", summary="Upload SOC alert CSV and trigger analysis")
async def upload_csv(file: UploadFile = File(...)):
    """
    Accept a CSV file upload, save it locally, and re-run the analytics engine.
    The dashboard summary is refreshed automatically.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted.")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    dest = DATA_DIR / "soc_alerts.csv"

    # Stream file to disk asynchronously
    async with aiofiles.open(dest, "wb") as out:
        while chunk := await file.read(1024 * 64):  # 64 KB chunks
            await out.write(chunk)

    logger.info("Uploaded CSV saved to %s (%d bytes)", dest, dest.stat().st_size)

    if not INV_CSV.exists():
        raise HTTPException(
            status_code=422,
            detail=(
                f"Asset inventory not found at {INV_CSV}. "
                "Run generate_mock_soc_data.py to create it, or place "
                "asset_inventory.csv in the data/ directory."
            ),
        )

    # Re-run engine in background — client gets immediate response
    asyncio.create_task(_refresh_cache(dest, INV_CSV))

    return {
        "status": "accepted",
        "message": "File saved. Analytics engine is running in the background. "
                   "The dashboard will refresh automatically.",
        "filename": file.filename,
        "saved_to": str(dest),
    }


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


@app.post(
    "/api/explain-anomaly",
    response_model=AnomalyExplainResponse,
    summary="Generate a 2-sentence AI explanation for a flagged anomaly",
)
async def explain_anomaly(request: AnomalyExplainRequest):
    """
    Uses LangChain + local Ollama to generate a professional audit explanation.
    Falls back to the rule-engine explanation if Ollama is not running.
    All inference is 100% local — no external API calls.
    """
    chain = _build_llm_chain()

    if chain is None:
        # Graceful fallback — return rule-engine text
        return AnomalyExplainResponse(
            explanation=request.explanation,
            source="rule_engine",
            model=None,
        )

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

    try:
        # ainvoke is async — FastAPI won't block while Ollama generates
        result: str = await chain.ainvoke(payload)
        return AnomalyExplainResponse(
            explanation=result.strip(),
            source="ollama",
            model=OLLAMA_MODEL,
        )
    except Exception as exc:
        logger.warning("Ollama inference failed (%s). Falling back to rule engine.", exc)
        return AnomalyExplainResponse(
            explanation=request.explanation,
            source="rule_engine",
            model=None,
        )
