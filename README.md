# LLM-Atlas

A living, conflict-aware registry of Large Language Model pricing, limits, and capabilities.

## Why

LLM providers silently change pricing, limits, and availability.
LLM-Atlas continuously tracks and normalizes these changes.

## Features

* Agent-based ingestion
* Semantic change detection
* Field-level metadata
* Conflict surfacing
* Historical pricing
* Machine-readable registry

## Quick Start

```bash
docker-compose up -d
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## API

* GET /models
* GET /providers/{provider}/models
* GET /models/{model}/history

## Status

Hackathon MVP (70% automated via AI agent)
