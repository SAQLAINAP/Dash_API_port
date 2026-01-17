from app.ingestion.orchestrator import IngestionOrchestrator
from app.agents.price_crawler import PriceCrawlerAgent
from app.storage.postgres import engine, Base
import sys

def main():
    print("Initializing Database...")
    Base.metadata.create_all(bind=engine)
    
    print("Starting Ingestion Pipeline...")
    orchestrator = IngestionOrchestrator()
    
    # Run PriceCrawlerAgent (PricePerToken.com)
    # This single agent covers many providers now
    print("--- PricePerToken Crawler ---")
    price_crawler = PriceCrawlerAgent("pricepertoken")
    orchestrator.run_agent(price_crawler)
    
    # Dump Registry
    print("--- Dumping Registry ---")
    orchestrator.dump_registry_json()
    
    print("Done!")

if __name__ == "__main__":
    main()
