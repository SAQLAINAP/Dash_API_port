from typing import Optional
from app.storage.redis import get_redis
from app.utils.hashing import compute_hash

class StateManager:
    """
    Tracks the state of ingested data to avoid redundant processing.
    Uses Redis to store hashes of the last processed state.
    """
    
    def __init__(self):
        self.redis = get_redis()
        
    def should_process(self, provider: str, data_hash: str) -> bool:
        """
        Returns True if the data has changed since last time.
        """
        key = f"state:{provider}:last_hash"
        last_hash = self.redis.get(key)
        
        if last_hash == data_hash:
            return False
            
        return True

    def update_state(self, provider: str, data_hash: str):
        key = f"state:{provider}:last_hash"
        self.redis.set(key, data_hash)
