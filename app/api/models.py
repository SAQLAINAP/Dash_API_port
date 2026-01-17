from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class ModelResponse(BaseModel):
    provider: str
    model: str
    fields: Dict[str, Any]

class HistoryResponse(BaseModel):
    timestamp: str
    diff: Dict[str, Any]
