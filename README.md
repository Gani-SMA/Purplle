# Purplle Store Intelligence System

The **Purplle Store Intelligence System** is a real-time computer vision and analytics platform that tracks visitor foot traffic, monitors billing queue depths, identifies store staff uniforms, and triggers operational alerts for retail outlets.

---

## 🏗️ Architecture & Port Mapping

| Service | Port | Description |
| :--- | :--- | :--- |
| **FastAPI Backend** | `8000` | The Intelligence REST API and WebSocket event broadcast |
| **PostgreSQL DB** | `5432` | Relational database containing events, sessions, transactions |
| **Redis Cache** | `6379` | Rate-limiting, deduplication, and realtime state management |
| **Dashboard UI** | `5173` | React/Vite-based live telemetry and analytics dashboard |

---

## 🚀 Quick Setup (5 Commands)

To comply with the project constraints, here is the zero-friction setup guide. Run these exactly 5 commands to initialize the infrastructure, install dependencies, and run the detection pipeline:

```bash
# 1. Clone the repository and enter the root directory
git clone <your_github_repo_url> && cd cam

# 2. Spin up the entire infrastructure (DB, Redis, API, Dashboard)
docker compose up -d

# 3. Create and activate a Python virtual environment (Use `source venv/bin/activate` on Linux/Mac)
python -m venv venv && .\venv\Scripts\Activate.ps1

# 4. Install all required dependencies
pip install -r app/requirements.txt

# 5. Run the detection pipeline to process clips and stream events into the system
cd pipeline && ./run.sh
```

---

## 📹 Running the Detection Pipeline Separately

If you only want to process surveillance footage and upload the telemetry data without executing the other setup steps, simply do:

```bash
cd pipeline

# You can adjust --replay-speed to simulate real-time ingestion (e.g. 1.0 or 10x)
./run.sh --replay-speed 1.0
```

---

## 🧪 Running the Acceptance Tests

To verify that the system handles edge cases (like zero traffic or DB unavailability) and passes all strict requirements:

```bash
# Make sure you are in the root directory and your venv is activated
python tests/assertions.py

# To run the full pytest suite (>70% coverage requirement)
pytest --cov
```

---

## 📡 API Endpoints Reference

The FastAPI server exposes the following documented endpoints. All responses omit raw stack traces on errors.

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/events/ingest` | Batch ingest store events (max 500). Idempotent by `event_id`. |
| `GET`  | `/stores/{id}/metrics` | Retrieve unique visitor count (excl. staff), conversion rate, avg dwell & queue depths. |
| `GET`  | `/stores/{id}/funnel` | Retrieve 4-stage visitor conversion funnel (Entry → Zone → Billing → Purchase) with drop-off %. |
| `GET`  | `/stores/{id}/heatmap` | Fetch visitor dwell counts & zone scores (normalized 0-100). |
| `GET`  | `/stores/{id}/anomalies` | Retrieve critical alerts (queue spikes, conversion drops, dead-zones) with suggested actions. |
| `GET`  | `/health` | Check backend, database status, last events, and `STALE_FEED` alerts (>10min lag). |
| `WS`   | `/ws/stores/{id}` | Connect to live telemetry broadcast stream for real-time dashboard updates. |
