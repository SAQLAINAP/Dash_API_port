from app.storage.redis import get_redis
import json
import time

def test_push():
    r = get_redis()
    stream_key = "stream:ingestion"
    
    data = {
        "provider": "test-provider",
        "model_name": "test-model-stream",
        "pricing": {"input": 0.001, "output": 0.002, "unit": "1M"},
        "context_window": 128000,
        "source": "manual_test"
    }
    
    print(f"Pushing mock item to {stream_key}...")
    r.xadd(stream_key, {"payload": json.dumps(data)})
    print("Pushed.")

if __name__ == "__main__":
    test_push()
