from fastapi import FastAPI
from app.config import settings
from app.api.providers import router as providers_router
from app.storage.postgres import engine, Base
# Import all models to ensure they are registered for creation
from app.models import registry, history

# Create tables for MVP (In production, use Alembic)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="A living, conflict-aware registry of LLM pricing, limits, and capabilities."
)

app.include_router(providers_router)

@app.get("/")
def root():
    return {"message": "Welcome to LLM-Atlas API. Check /docs for endpoints."}

@app.on_event("startup")
def startup_event():
    print("Starting up LLM-Atlas...")
    # Optional: Trigger ingestion on startup for demo purposes
    # from app.ingestion.orchestrator import IngestionOrchestrator
    # from app.agents.provider_crawler import ProviderCrawlerAgent
    # orchestrator = IngestionOrchestrator()
    # orchestrator.run_agent(ProviderCrawlerAgent("openai"))
    # orchestrator.dump_registry_json()
