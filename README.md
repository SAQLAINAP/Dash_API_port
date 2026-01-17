# LLM Atlas 🌍

**The "Pro Terminal" for LLM Pricing & Intelligence.**

LLM Atlas is a high-performance dashboard and API for tracking Large Language Model (LLM) pricing, capabilities, and leaderboard rankings in real-time. It uses a streaming data pipeline to provide immediate updates on the AI model landscape.

## 🚀 Key Features
- **Real-Time Streaming**: Ingestion pipeline powered by **Redis Streams** for sub-second data updates.
- **Pro Terminal UI**: Dark-themed, responsive dashboard with interactive **ECharts** visualizations.
- **Live Metrics**:
    - **Header Status**: "ONLINE" pipeline indicator with real-time metadata.
    - **Visual Analytics**: Price Correlation Scatter, Provider Market Share Pie, and Capabilities Radar.
- **Leaderboard Integration**: Ingests rankings from LMArena.
- **Robust Backend**: PostgreSQL database with Redis caching and message brokering.

## 🏗️ Architecture
The system follows a **Producer-Consumer** architecture:
1.  **Agents (Producers)**: Scrape data and push immediately to `stream:ingestion` in Redis.
2.  **Stream Worker (Consumer)**: A dedicated process (`stream_worker.py`) listens to the stream, normalizes data, computes semantic diffs, and updates PostgreSQL.
3.  **Dashboard**: Generates a static HTML report from the latest DB state.

## 🛠️ Quick Start Guide

### Prerequisites
- Docker & Docker Compose
- Python 3.9+

### 1. Start Infrastructure
Launch PostgreSQL and Redis containers.
```bash
docker-compose up -d
```

### 2. Start Ingestion Worker
Start the background worker to listen for stream data.
```bash
python run_worker.py
```

### 3. Trigger Data Ingestion
Run the orchestrator to trigger agents. They will push data to the stream which the worker processes.
```bash
python run_ingestion.py
```

### 4. Update Leaderboard
Scrape the latest model rankings from LMArena.
```bash
python app/agents/leaderboard_crawler.py
```

### 5. Generate Dashboard
Create the interactive HTML dashboard (`registry_report.html`).
```bash
python generate_visual_report.py
```
*Open `registry_report.html` in your browser to view the Pro Terminal.*

---

## 📡 API Server (Optional)
To access the data programmatically via a REST API:
```bash
uvicorn app.main:app --reload
```
- **Docs**: http://127.0.0.1:8000/docs
- **Models**: http://127.0.0.1:8000/models

## 📂 Key Files
- `app/ingestion/stream_worker.py`: **[NEW]** Consumer logic for Redis Streams.
- `app/agents/`: Web crawlers (Playwright).
- `run_ingestion.py`: Trigger script for data collection.
- `generate_visual_report.py`: Dashboard generator (Python -> HTML/JS).
- `docker-compose.yml`: Infrastructure definition (Postgres + Redis).
