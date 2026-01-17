from typing import List, Optional
import json
import os
from sqlalchemy.orm import Session
from app.agents.base import BaseAgent
from app.ingestion.normalizer import Normalizer
from app.ingestion.state_manager import StateManager
from app.utils.hashing import compute_hash
from app.diff.semantic_diff import SemanticDiff
from app.storage.postgres import SessionLocal
from app.models.registry import RegistryEntry, RegistryEntryData
from app.models.history import HistoryEntry  # Added import

class IngestionOrchestrator:
    def __init__(self):
        self.normalizer = Normalizer()
        self.state_manager = StateManager()
        self.diff_engine = SemanticDiff()

    def run_agent(self, agent: BaseAgent):
        print(f"Running agent for {agent.provider}...")
        raw_items = agent.fetch()
        
        db = SessionLocal()
        try:
            for item in raw_items:
                # Normalize
                # Use a generic provider name if the agent didn't set one, 
                # but PriceCrawler usually returns it in the item.
                provider_name = item.get("provider", agent.provider)
                new_entry_data = self.normalizer.normalize(item, provider_name)
                
                # Check DB for existing entry to compare against
                existing_entry_db = db.query(RegistryEntry).filter_by(
                    provider=new_entry_data.provider, 
                    model=new_entry_data.model
                ).first()
                
                old_entry_data = None
                if existing_entry_db:
                    # Convert dict back to Pydantic model for diffing
                    # Verify if data is dict or string
                    data_dict = existing_entry_db.data if isinstance(existing_entry_db.data, dict) else json.loads(existing_entry_db.data)
                    old_entry_data = RegistryEntryData(**data_dict)

                # Compute Diff
                diff = self.diff_engine.compute_diff(old_entry_data, new_entry_data)
                
                # If changes or no existing entry, update
                if diff["type"] == "new_model" or diff["changes"]:
                    print(f"Changes detected for {new_entry_data.provider}/{new_entry_data.model}. Saving...")
                    
                    # Persist to DB (RegistryEntry)
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
                    
                    # Create HistoryEntry
                    history_entry = HistoryEntry(
                        provider=new_entry_data.provider,
                        model=new_entry_data.model,
                        diff=diff,
                        snapshot=entry_dict
                    )
                    db.add(history_entry)
                    
                    db.commit()
                    
                    # Update State Manager (Redis)
                    entry_hash = compute_hash(entry_dict)
                    # State key needs to match the orchestrator logic
                    state_key = f"{agent.provider}:{new_entry_data.model}"
                    self.state_manager.update_state(state_key, entry_hash)

                else:
                    print(f"No semantic changes for {new_entry_data.provider}/{new_entry_data.model}.")
                    
        finally:
            db.close()
            
    def dump_registry_json(self):
        """
        Dumps the current DB state to registry/latest.json
        """
        db = SessionLocal()
        try:
            entries = db.query(RegistryEntry).all()
            output = []
            for e in entries:
                output.append(e.data)
            
            os.makedirs("registry", exist_ok=True)
            with open("registry/latest.json", "w") as f:
                json.dump(output, f, indent=2)
            print("Registry dumped to registry/latest.json")
        finally:
            db.close()
