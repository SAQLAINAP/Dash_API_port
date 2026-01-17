from typing import Dict, Any, List
from app.models.registry import RegistryEntryData, ModelFields, FieldMetadata, Conflict
from app.utils.timestamps import get_current_timestamp

class Normalizer:
    """
    Normalizes raw data from agents into the standard RegistryEntryData format.
    Ensures every field has metadata.
    """
    
    def normalize(self, raw_data: Dict[str, Any], provider: str) -> RegistryEntryData:
        # Basic normalization strategy
        model_name = raw_data.get("model_name") or raw_data.get("id")
        if not model_name:
            # Fallback or error
            model_name = "unknown-model"

        # Construct fields
        # This mapping depends heavily on the source structure. 
        # For MVP, we stick to the example structure used in ProviderCrawlerAgent
        
        fields = ModelFields()
        timestamp = get_current_timestamp()
        source = raw_data.get("source", "unknown")
        
        if "pricing" in raw_data:
            fields.pricing = FieldMetadata(
                value=raw_data["pricing"],
                sources=[source],
                last_verified=timestamp,
                confidence=0.9,
                conflicts=[]
            )
            
        if "context_window" in raw_data:
             fields.context_window = FieldMetadata(
                value=raw_data["context_window"],
                sources=[source],
                last_verified=timestamp,
                confidence=0.9,
                conflicts=[]
             )
             
        # Normalize other fields...

        return RegistryEntryData(
            provider=provider,
            model=model_name,
            fields=fields
        )
