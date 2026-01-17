from abc import ABC, abstractmethod
from typing import Dict, Any, List

class BaseAgent(ABC):
    """
    Abstract base class for all data ingestion agents.
    Agents are stateless and responsible for fetching raw data and returning it in a structured format.
    """

    def __init__(self, provider: str):
        self.provider = provider

    @abstractmethod
    def fetch(self) -> List[Dict[str, Any]]:
        """
        Fetch data from the source.
        Returns a list of dictionaries, where each dictionary represents a model entry
        in a raw or semi-structured format.
        """
        pass
