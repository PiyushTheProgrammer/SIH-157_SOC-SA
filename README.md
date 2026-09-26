# SAT-SA: Supervisory Analytics Tool for SOC Assessment (SIH-26157)

## 📌 Problem Statement
The National Critical Information Infrastructure Protection Centre (NCIIPC) manually reviews security alerts and case-management records from Critical Sector Entities (CSEs) to assess their cyber resilience. Manual review is highly resource-intensive and struggles to scale. NCIIPC requires a fully offline, air-gapped analytics tool to automatically ingest SOC data, identify execution gaps (poor operational quality), and detect negative space (missing monitoring telemetry).

## 💡 Solution
**SAT-SA** is a secure, localized dashboard that ingests periodic SOC exports (CSV/JSON). It uses offline machine learning (Isolation Forests) to flag suspicious operational patterns and local LLMs to generate human-readable rationales. It prioritizes the highest-value records for supervisory review without relying on external cloud APIs, ensuring 100% data sovereignty.

## 🏗️ Architecture
- **Frontend:** Next.js (React) with Tailwind CSS. Provides a clean, dark/light-mode dashboard optimized for long supervisory sessions.
- **Backend:** Python (FastAPI). High-performance asynchronous API handling data parsing and analytics.
- **Database:** Local SQLite / PostgreSQL (via SQLAlchemy) for offline, immutable storage of alerts, entities, and audit reports.
- **Analytics Engine:** Scikit-Learn (Isolation Forest) for anomaly detection and Ollama (Local Llama) for zero-network explainability.

## 🚀 One-Click Setup & Launch

After cloning the repository, you only need to run **one command**:

### On Windows (Recommended):
Double-click `run.bat` or run in terminal:
```powershell
.\run.bat
```
> **Note:** If this is your first time running, `run.bat` will automatically set up the Python virtual environment, install requirements, configure Node.js packages, create the PostgreSQL `sat_sa_db` database, and launch both services. On subsequent runs, it launches immediately.

### On Linux / macOS / Manual Setup:
```bash
python setup.py     # Run automated setup
python setup.py     # Or launch backend & frontend manually
```

- **Frontend Dashboard:** http://localhost:3000
- **Backend Swagger API Docs:** http://127.0.0.1:8000/docs
