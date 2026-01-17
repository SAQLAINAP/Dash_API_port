from app.agents.price_crawler import PriceCrawlerAgent
from app.ingestion.orchestrator import IngestionOrchestrator

def check_and_run_ingestion():
    """
    Orchestrates the crawling process by triggering agents.
    Data is pushed to Redis Stream for the worker to process.
    """
    print("Starting ingestion trigger...")
    
    orchestrator = IngestionOrchestrator()
    
    # 1. Price Crawler
    crawler = PriceCrawlerAgent()
    orchestrator.run_agent(crawler)
    
    print("Ingestion triggered. Check worker logs for processing status.")
