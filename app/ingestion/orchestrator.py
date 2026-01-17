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
        """
        Triggers the agent to fetch data and push it to the stream.
        """
        print(f"Triggering agent for {agent.provider}...")
        raw_items = agent.fetch()
        
        count = 0
        for item in raw_items:
            # Push normalized-ready data to stream
            agent.push_to_stream(item)
            count += 1
            
        print(f"Pushed {count} items to stream for {agent.provider}")
            
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
