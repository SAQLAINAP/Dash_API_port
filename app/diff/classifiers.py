from enum import Enum
from typing import Dict, Any

class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class ChangeType(str, Enum):
    PRICING_CHANGE = "pricing_change"
    CAPABILITY_ADDED = "capability_added"
    CAPABILITY_REMOVED = "capability_removed"
    LIMIT_CHANGE = "limit_change"
    NEW_MODEL = "new_model"
    UNKNOWN = "unknown"

def classify_change(field: str, old_val: Any, new_val: Any) -> Dict[str, Any]:
    """
    Determines severity and change type based on field and values.
    """
    if field == "pricing":
        # Any pricing change is at least medium, could be high
        return {"severity": Severity.MEDIUM, "type": ChangeType.PRICING_CHANGE}
    
    if field == "context_window":
        if isinstance(new_val, (int, float)) and isinstance(old_val, (int, float)):
            if new_val < old_val:
                return {"severity": Severity.HIGH, "type": ChangeType.LIMIT_CHANGE, "breaking": True}
        return {"severity": Severity.LOW, "type": ChangeType.LIMIT_CHANGE}

    return {"severity": Severity.LOW, "type": ChangeType.UNKNOWN}
