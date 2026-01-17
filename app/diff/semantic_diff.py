from typing import Dict, Any, List, Optional
from app.models.registry import RegistryEntryData, ModelFields
from app.diff.classifiers import classify_change, Severity

class SemanticDiff:
    """
    Compares two RegistryEntryData objects to detect semantic changes.
    """
    
    def compute_diff(self, old_entry: Optional[RegistryEntryData], new_entry: RegistryEntryData) -> Dict[str, Any]:
        """
        Returns a diff dictionary.
        If old_entry is None, it's a new model.
        """
        if old_entry is None:
            return {
                "type": "new_model",
                "severity": Severity.LOW,
                "changes": []
            }
        
        changes = []
        
        # Compare fields
        new_fields = new_entry.fields.model_dump(exclude_unset=True)
        old_fields = old_entry.fields.model_dump(exclude_unset=True)
        
        for field_name, new_meta in new_fields.items():
            old_meta = old_fields.get(field_name)
            
            if not old_meta:
                 changes.append({
                    "field": field_name,
                    "action": "added",
                    "value": new_meta["value"],
                    "severity": Severity.LOW
                })
                 continue

            if new_meta["value"] != old_meta["value"]:
                classification = classify_change(field_name, old_meta["value"], new_meta["value"])
                changes.append({
                    "field": field_name,
                    "action": "modified",
                    "old_value": old_meta["value"],
                    "new_value": new_meta["value"],
                    **classification
                })
        
        return {
            "type": "update",
            "changes": changes,
            "provider": new_entry.provider,
            "model": new_entry.model
        }
