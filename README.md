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

## 🚀 Setup & Installation Instructions

### Prerequisites
- Node.js (v18+)
- Python (3.10+)
- Local Ollama installed (for AI Explainability)

### 1. Backend Setup
Navigate to the backend directory and set up the Python environment:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
pip install -r requirements.txt