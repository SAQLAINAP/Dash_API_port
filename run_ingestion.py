from app.agents.price_crawler import PriceCrawlerAgent
from app.storage.postgres import SessionLocal, upsert_model

def check_and_run_ingestion():
    """
    Orchestrates the crawling and database update process.
    """
    print("Starting ingestion process...")
    
    # 1. Price Crawler
    crawler = PriceCrawlerAgent()
    print("Fetching data from PricePerToken...")
    price_data = crawler.fetch()
    
    if not price_data:
        print("No data fetched from PricePerToken.")
        return

    print(f"Fetched {len(price_data)} records. Updating Database...")
    
    db = SessionLocal()
    try:
        for item in price_data:
            model_data = {
                'name': item['model_name'],
                'provider': item['provider'],
                'input_price': item['pricing']['input'],
                'output_price': item['pricing']['output'],
                'context_window': item['context_window'],
                'config': {
                   'model': item['model_name'],
                   'provider': item['provider'],
                   'fields': {
                       'pricing': {'value': item['pricing']},
                       'context_window': {'value': item['context_window']}
                   }
                }
            }
            upsert_model(db, model_data)
        print("Database update complete.")
    except Exception as e:
        print(f"Error updating DB: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_and_run_ingestion()
