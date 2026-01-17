from datetime import datetime, timezone

def get_current_timestamp() -> str:
    """
    Returns current UTC timestamp in ISO 8601 format.
    """
    return datetime.now(timezone.utc).isoformat()
