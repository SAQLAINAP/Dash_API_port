import re
from typing import List, Dict, Any
from app.agents.base import BaseAgent
from playwright.sync_api import sync_playwright

class PriceCrawlerAgent(BaseAgent):
    """
    Scrapes real-time pricing from https://pricepertoken.com/
    """
    
    def fetch(self) -> List[Dict[str, Any]]:
        url = "https://pricepertoken.com/"
        results = []
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                # Use a specific user agent to look more like a real browser
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
                )
                page = context.new_page()
                
                # Increase timeout to 60s and wait for commit instead of networkidle which happens too late sometimes
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    # wait a bit for dynamic content
                    page.wait_for_timeout(5000) 
                except Exception as e:
                    print(f"Navigation error: {e}")
                    browser.close()
                    return []
                
                # Wait for the table to load
                try:
                    page.wait_for_selector("tbody tr", timeout=30000)
                except Exception as e:
                    print(f"Selector timeout: {e}")
                
                rows = page.query_selector_all("tbody tr")
                print(f"Found {len(rows)} rows on {url}")
                
                for row in rows:
                    try:
                        # Extract cells
                        cells = row.query_selector_all("td")
                        if len(cells) < 5:
                            continue
                            
                        # 1. Provider
                        provider_elem = cells[0].query_selector("a span") or cells[0].query_selector("span") or cells[0].query_selector("a")
                        provider_name = provider_elem.inner_text().strip() if provider_elem else "Unknown"
                        
                        # 2. Model
                        model_elem = cells[1].query_selector("a") or cells[1]
                        model_name = model_elem.inner_text().strip()
                        
                        # 3. Context Window
                        context_elem = cells[2].query_selector("span") or cells[2]
                        context_text = context_elem.inner_text().strip()
                        context_window = self._parse_context(context_text)
                        
                        # 4. Input Price
                        input_elem = cells[3].query_selector("span") or cells[3]
                        input_price = self._parse_price(input_elem.inner_text())
                        
                        # 5. Output Price
                        output_elem = cells[4].query_selector("span") or cells[4]
                        output_price = self._parse_price(output_elem.inner_text())
                        
                        # Construct standardized dict
                        entry = {
                            "provider": provider_name.lower(),
                            "model_name": model_name,
                            "pricing": {
                                "input": input_price,
                                "output": output_price,
                                "unit": "1M tokens" # Standard on this site
                            },
                            "context_window": context_window,
                            "source": url
                        }
                        results.append(entry)
                        
                    except Exception as e:
                        print(f"Error parsing row: {e}")
                        continue
                        
                browser.close()
                
        except Exception as e:
            print(f"Failed to scrape {url}: {e}")
            # Fallback strategy could go here
            
        return results

    def _parse_price(self, price_str: str) -> float:
        """
        Parses '$0.010' -> 0.010
        """
        clean_str = price_str.replace('$', '').replace(',', '').strip()
        try:
            return float(clean_str)
        except ValueError:
            return 0.0

    def _parse_context(self, context_str: str) -> int:
        """
        Parses '128K' -> 128000, '1M' -> 1000000
        """
        clean_str = context_str.upper().replace(',', '').strip()
        multiplier = 1
        if 'K' in clean_str:
            multiplier = 1000
            clean_str = clean_str.replace('K', '')
        elif 'M' in clean_str:
            multiplier = 1000000
            clean_str = clean_str.replace('M', '')
        
        try:
            return int(float(clean_str) * multiplier)
        except ValueError:
            return 0
