import json
import time
from typing import Optional
from app.storage.redis import get_redis
from app.storage.postgres import SessionLocal
from app.models.registry import RegistryEntry, RegistryEntryData
from app.models.history import HistoryEntry
from app.ingestion.normalizer import Normalizer
from app.diff.semantic_diff import SemanticDiff
from app.utils.hashing import compute_hash

STREAM_KEY = "stream:ingestion"
CONSUMER_GROUP = "ingestion_group"
CONSUMER_NAME = "worker_1"

class StreamWorker:
    def __init__(self):
        self.redis = get_redis()
        self.normalizer = Normalizer()
        self.diff_engine = SemanticDiff()
        self.setup_stream()

    def setup_stream(self):
        try:
            self.redis.xgroup_create(STREAM_KEY, CONSUMER_GROUP, id="0", mkstream=True)
            print(f"Created consumer group {CONSUMER_GROUP}")
        except Exception as e:
            if "BUSYGROUP" in str(e):
                pass
            else:
                print(f"Error creating consumer group: {e}")

    def process_message(self, message_id, message_data):
        """
        Process a single message from the stream.
        Expected format: {"payload": json_string}
        """
        raw_payload = message_data.get("payload")
        if not raw_payload:
            return

        try:
            item = json.loads(raw_payload)
            provider_name = item.get("provider", "unknown")
            
            # Normalize
            new_entry_data = self.normalizer.normalize(item, provider_name)
            
            self._save_to_db(new_entry_data)
            
            # ACK message
            self.redis.xack(STREAM_KEY, CONSUMER_GROUP, message_id)
            # Optional: Delete to keep stream size manageable
            # self.redis.xdel(STREAM_KEY, message_id)
            
        except Exception as e:
            print(f"Error processing message {message_id}: {e}")

    def _save_to_db(self, new_entry_data: RegistryEntryData):
        db = SessionLocal()
        try:
            # Check for existing
            existing_entry_db = db.query(RegistryEntry).filter_by(
                provider=new_entry_data.provider, 
                model=new_entry_data.model
            ).first()
            
            old_entry_data = None
            if existing_entry_db:
                data_dict = existing_entry_db.data if isinstance(existing_entry_db.data, dict) else json.loads(existing_entry_db.data)
                old_entry_data = RegistryEntryData(**data_dict)

            # Diff
            diff = self.diff_engine.compute_diff(old_entry_data, new_entry_data)
            
            if diff["type"] == "new_model" or diff["changes"]:
                print(f"Update: {new_entry_data.provider}/{new_entry_data.model}")
                entry_dict = new_entry_data.model_dump(mode='json')
                
                if existing_entry_db:
                    existing_entry_db.data = entry_dict
                else:
                    new_db_entry = RegistryEntry(
                        provider=new_entry_data.provider,
                        model=new_entry_data.model,
                        data=entry_dict
                    )
                    db.add(new_db_entry)
                
                # History
                history_entry = HistoryEntry(
                    provider=new_entry_data.provider,
                    model=new_entry_data.model,
                    diff=diff,
                    snapshot=entry_dict
                )
                db.add(history_entry)
                db.commit()
            else:
                # No change, just log debug or skip
                pass
                
        except Exception as e:
            print(f"DB Error: {e}")
            db.rollback()
        finally:
            db.close()

    def run(self):
        print(f"Worker listening on {STREAM_KEY}...")
        while True:
            try:
                # Block for 5 seconds waiting for new messages
                messages = self.redis.xreadgroup(CONSUMER_GROUP, CONSUMER_NAME, {STREAM_KEY: ">"}, count=10, block=5000)
                
                if not messages:
                    continue
                    
                for stream, rows in messages:
                    for message_id, message_data in rows:
                        self.process_message(message_id, message_data)
                        
            except Exception as e:
                print(f"Worker loop error: {e}")
                time.sleep(1)
