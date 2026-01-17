# LLM Atlas 🌍

**The "Pro Terminal" for LLM Pricing & Intelligence.**

LLM Atlas is a comprehensive dashboard and API for tracking Large Language Model (LLM) pricing, capabilities, and leaderboard rankings. It aggregates data from multiple sources to provide a unified view of the AI model landscape.

## 🚀 Key Features
- **Real-Time Registry**: Track input/output pricing and context windows for hundreds of models.
- **Visual Analytics**: Interactive charts for Price Correlation, Provider Market Share, and Capabilities Radar.
- **Leaderboard Integration**: Ingests rankings from LMArena.
- **PostgreSQL Backend**: Robust data persistence with Dockerized SQL database.

## 🛠️ Quick Start Guide

### Prerequisites
- Docker & Docker Compose
- Python 3.9+

### 1. Start the Database
Launch the PostgreSQL container using Docker Compose.
```bash
docker-compose up -d
```

### 2. Ingest Market Data
Run the crawler to fetch the latest pricing from PricePerToken.com and populate the database.
```bash
python run_ingestion.py
```

### 3. Update Leaderboard
Scrape the latest model rankings from LMArena (Chatbot Arena).
```bash
python app/agents/leaderboard_crawler.py
```

### 4. Generate Dashboard
Create the interactive HTML dashboard (`registry_report.html`) from the database.
```bash
python generate_visual_report.py
```

### 5. View the Dashboard
Open the generated report in your browser.
- **Windows**: `start registry_report.html`
- **Mac**: `open registry_report.html`
- **Linux**: `xdg-open registry_report.html`

---

## 📡 API Server (Optional)
To access the data programmatically via a REST API:
```bash
uvicorn app.main:app --reload
```
- Docs: http://127.0.0.1:8000/docs
- Models Endpoint: http://127.0.0.1:8000/models

## 📂 Project Structure
- `app/storage/postgres.py`: Database connection and schema models.
- `app/agents/`: Web crawlers (Playwright) for data sourcing.
- `generate_visual_report.py`: Script to generate the single-file HTML dashboard.
- `registry_report.html`: The output dashboard file.
