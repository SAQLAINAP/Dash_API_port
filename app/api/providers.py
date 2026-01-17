from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.storage.postgres import get_db, Model
from app.api.models import ModelResponse

router = APIRouter()

@router.get("/models", response_model=List[ModelResponse])
def get_all_models(db: Session = Depends(get_db)):
    models = db.query(Model).all()
    results = []
    for m in models:
        # Reconstruct the response format from the DB model
        # Using the stored config if available, or building it manually
        data = m.config if m.config else {}
        
        # Ensure critical fields are present from columns
        data['model'] = m.name
        data['provider'] = m.provider
        
        if 'fields' not in data:
            data['fields'] = {}
        if 'pricing' not in data['fields']:
             data['fields']['pricing'] = {'value': {}}
        
        data['fields']['pricing']['value']['input'] = m.input_price
        data['fields']['pricing']['value']['output'] = m.output_price
        
        results.append(ModelResponse(**data))
    return results

@router.get("/providers/{provider}/models", response_model=List[ModelResponse])
def get_provider_models(provider: str, db: Session = Depends(get_db)):
    models = db.query(Model).filter(Model.provider == provider).all()
    if not models:
        return []
    
    results = []
    for m in models:
        data = m.config if m.config else {}
        data['model'] = m.name
        data['provider'] = m.provider
        results.append(ModelResponse(**data))
    return results

@router.get("/models/{model}/history")
def get_model_history(model: str, db: Session = Depends(get_db)):
    # Placeholder
    return {"message": "History endpoint pending implementation with SQL history table."}
