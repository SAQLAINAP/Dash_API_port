from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.storage.postgres import Base

class HistoryEntry(Base):
    __tablename__ = "history_entries"

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String, nullable=False)
    model = Column(String, nullable=False)
    
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Snapshot of the semantic diff or the change applied
    diff = Column(JSONB, nullable=False) 
    
    # Snapshot of the full entry at this point (optional, but good for rollback)
    snapshot = Column(JSONB, nullable=True)

    # Could link to RegistryEntry if foreign keys are desired, 
    # but soft linking via provider/model is often flexible for history.
