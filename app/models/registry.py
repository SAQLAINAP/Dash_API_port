from sqlalchemy import Column, String, DateTime, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.storage.postgres import Base
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

# --- Pydantic Models for JSONB Structure ---

class Conflict(BaseModel):
    source: str
    value: Any
    timestamp: str
    reason: Optional[str] = None

class FieldMetadata(BaseModel):
    value: Any
    sources: List[str]
    last_verified: str
    confidence: float
    conflicts: List[Conflict] = []

class ModelFields(BaseModel):
    pricing: Optional[FieldMetadata] = None
    context_window: Optional[FieldMetadata] = None
    rate_limits: Optional[FieldMetadata] = None
    capabilities: Optional[FieldMetadata] = None
    # Allow extra fields
    model_config = {"extra": "allow"}

class RegistryEntryData(BaseModel):
    provider: str
    model: str
    fields: ModelFields

# --- SQLAlchemy Model ---

class RegistryEntry(Base):
    __tablename__ = "registry_entries"

    provider = Column(String, primary_key=True)
    model = Column(String, primary_key=True)
    
    # Stores the full JSON structure including fields with metadata
    data = Column(JSONB, nullable=False)
    
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_registry_provider", "provider"),
        Index("ix_registry_model", "model"),
    )
