import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from app.agents.base import BaseAgent

class ProviderCrawlerAgent(BaseAgent):
    """
    Scrapes official provider documentation to extract pricing and capabilities.
    """
    
    def fetch(self) -> List[Dict[str, Any]]:
        # This agent is deprecated in favor of PriceCrawlerAgent for real-time data.
        # Leaving this stub for architecture compliance if specific provider logic is needed later.
        return []

    def _fetch_openai(self) -> List[Dict[str, Any]]:
        return []

    def _fetch_anthropic(self) -> List[Dict[str, Any]]:
        return []
