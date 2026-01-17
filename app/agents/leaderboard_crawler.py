
import sys
import os

# Add project root to path for imports
sys.path.append(os.getcwd())

from playwright.sync_api import sync_playwright
import json
import time
from app.config import settings

OUTPUT_FILE = "registry/leaderboard.json"

class LeaderboardCrawler:
    def __init__(self):
        self.url = "https://lmarena.ai/leaderboard/text"
        self.data = []

    def run(self):
        print(f"Starting Leaderboard Crawl: {self.url}")
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1280, "height": 720}
                )
                page = context.new_page()
                
                try:
                    page.goto(self.url, timeout=60000)
                    # Wait for ANY table, which is the core content we need
                    page.wait_for_selector('table', timeout=30000)
                    
                    time.sleep(5) # Allow dynamic rows to hydrate
                    
                    rows = page.query_selector_all("table tbody tr")
                    print(f"Found {len(rows)} rows in the leaderboard.")
                    
                    extracted_count = 0
                    for row in rows:
                        cells = row.query_selector_all("td")
                        if len(cells) < 3:
                            continue
                            
                        try:
                            # Attempt to find the rank (usually first col)
                            rank = cells[0].inner_text().strip()
                            
                            # Model name (usually second col, looks for a div or link)
                            model_div = cells[1].query_selector("div") or cells[1].query_selector("a") or cells[1]
                            model = model_div.inner_text().strip()
                            
                            # Score (usually 3rd col)
                            score = cells[2].inner_text().strip()
                            
                            # CI (usually 4th col)
                            ci = cells[3].inner_text().strip() if len(cells) > 3 else "-"
                            
                            self.data.append({
                                "rank": rank,
                                "model": model,
                                "arena_score": score,
                                "ci_95": ci,
                                "category": "Overall"
                            })
                            extracted_count += 1
                        except:
                            continue
                            
                    print(f"Extracted {extracted_count} entries.")

                except Exception as e:
                    print(f"Scraping error: {e}")
                    print("Attempting to use fallback/mock data due to scrape failure.")
                    self.use_fallback_data()
                finally:
                    browser.close()

        except Exception as e:
             print(f"Playwright error: {e}")
             self.use_fallback_data()

        self.save_data()

    def use_fallback_data(self):
        # Fallback if scraping gets blocked by Cloudflare or connection issues
        print("Generating fallback leaderboard data...")
        self.data = [
            {"rank": "1", "model": "gpt-4o-2024-05-13", "arena_score": "1287", "ci_95": "+13 / -15", "category": "Overall"},
            {"rank": "2", "model": "gemini-1.5-pro-latest", "arena_score": "1261", "ci_95": "+12 / -14", "category": "Overall"},
            {"rank": "3", "model": "claude-3-opus-20240229", "arena_score": "1246", "ci_95": "+14 / -10", "category": "Overall"},
            {"rank": "4", "model": "gpt-4-0125-preview", "arena_score": "1245", "ci_95": "+11 / -12", "category": "Overall"},
            {"rank": "5", "model": "llama-3-70b-instruct", "arena_score": "1208", "ci_95": "+18 / -11", "category": "Overall"}
        ]


    def save_data(self):
        os.makedirs("registry", exist_ok=True)
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)
        print(f"Leaderboard data saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    crawler = LeaderboardCrawler()
    crawler.run()
