# SIH-157_SOC-SA: SOC Situational Awareness Dashboard

## 📌 Problem Statement
Modern Security Operations Centers (SOCs) are overwhelmed with a high volume of security alerts, making it difficult to prioritize threats, identify blind spots, and respond to critical incidents in real-time. Analysts suffer from alert fatigue and lack a unified, intuitive view of the organization's security posture.

## 💡 Solution
The **SOC Situational Awareness (SA) Dashboard** provides a centralized, real-time visualization platform that aggregates security alerts, analyzes risks, and highlights anomalies. By leveraging data analytics and intuitive visualizations, it empowers security analysts to quickly identify critical threats, understand their context, and take decisive action, thereby reducing response times and improving overall security posture.

## 🏗️ Architecture
The project follows a modern client-server architecture:

- **Frontend:** Built with Next.js and React. Provides an interactive, dynamic user interface with specialized visualization components (e.g., Risk Score Badges, Anomaly Tables, Blind Spot Charts, and Scatter Plots).
- **Backend:** Built with Python (FastAPI). Acts as the analytics engine, processing raw SOC alerts, computing risk scores, and serving data to the frontend via RESTful APIs.
- **Data Source:** Ingests SOC alert data and asset inventory to drive analytics.

## 🔄 Flow of Data
1. **Data Ingestion:** The backend ingests security alerts and asset inventory data.
2. **Processing & Analytics:** The analytics engine processes the raw data, identifies anomalies, calculates risk scores based on asset criticality and threat severity, and detects potential blind spots.
3. **API Delivery:** The processed insights are exposed through backend API endpoints.
4. **Visualization:** The Next.js frontend fetches the data from the backend APIs and renders it in real-time using interactive charts, tables, and metrics bars.

## 🚀 Getting Started

### Prerequisites
- Node.js (v18+)
- Python (3.8+)

### Backend Setup
1. Navigate to the backend directory: `cd backend`
2. Install dependencies: `pip install -r requirements.txt`
3. Run the backend server: `uvicorn main:app --reload --port 8000`

### Frontend Setup
1. Navigate to the frontend directory: `cd frontend`
2. Install dependencies: `npm install`
3. Run the development server: `npm run dev`

## 🛡️ Key Features
- **Real-time Metrics:** Overview of critical alerts and system health.
- **Risk Scoring:** Automated risk calculation for prioritized response.
- **Anomaly Detection:** Identification of unusual patterns in network traffic or user behavior.
- **Blind Spot Analysis:** Visualizing unmonitored or vulnerable assets.
