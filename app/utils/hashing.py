import hashlib
import json
from typing import Any

def compute_hash(data: Any) -> str:
    """
    Computes a stable SHA-256 hash of a dictionary or list.
    """
    if isinstance(data, (dict, list)):
        serialized = json.dumps(data, sort_keys=True, default=str)
    else:
        serialized = str(data)
    
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
