from abc import ABC, abstractmethod
from typing import Dict, Any, List, Generator
import json
from app.storage.redis import get_redis

class BaseAgent(ABC):
    """
    Abstract base class for all data ingestion agents.
    Agents are responsible for fetching raw data.
    Supports both batch fetch (returning list) and streaming (pushing to Redis).
    """

    def __init__(self, provider: str):
        self.provider = provider
        self.redis = get_redis()
        self.stream_key = "stream:ingestion"

    @abstractmethod
    def fetch(self) -> List[Dict[str, Any]]:
        """
        Fetch data from the source.
        Returns a list of dictionaries.
        """
        pass
        
    def push_to_stream(self, data: Dict[str, Any]):
        """
        Push a single data item to the Redis Stream.
        """
        if "provider" not in data:
            data["provider"] = self.provider
            
        self.redis.xadd(self.stream_key, {"payload": json.dumps(data)})

