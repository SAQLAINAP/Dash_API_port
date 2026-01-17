from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.storage.postgres import get_db
from app.models.registry import RegistryEntry
from app.api.models import ModelResponse

router = APIRouter()

@router.get("/models", response_model=List[ModelResponse])
def get_all_models(db: Session = Depends(get_db)):
    entries = db.query(RegistryEntry).all()
    results = []
    for e in entries:
        # Assuming e.data follows the structure
        results.append(e.data)
    return results

@router.get("/providers/{provider}/models", response_model=List[ModelResponse])
def get_provider_models(provider: str, db: Session = Depends(get_db)):
    entries = db.query(RegistryEntry).filter(RegistryEntry.provider == provider).all()
    if not entries:
        return []
    return [e.data for e in entries]

@router.get("/models/{model}/history")
def get_model_history(model: str, db: Session = Depends(get_db)):
    # Placeholder: Implement history fetching logic
    # entries = db.query(HistoryEntry).filter(HistoryEntry.model == model).all()
    return {"message": "History endpoint not fully connected to HistoryEntry table yet."}
