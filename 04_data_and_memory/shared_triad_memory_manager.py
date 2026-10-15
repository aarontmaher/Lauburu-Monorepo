#!/usr/bin/env python3
"""
Shared Memory Triad Bank (Continuous Vector Graph)
Allows the Cloud Triad (Gemini Flash), Sovereign Local AI, and Tiny LMs 
to persist and read historic optimization rules and evolutionary knowledge.
"""

import json
from pathlib import Path
from datetime import datetime

class SharedTriadMemory:
    def __init__(self, db_path="/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/shared_triad_memory.json"):
        self.db_path = Path(db_path)
        self.memory = self._load()

    def _load(self):
        if not self.db_path.exists():
            return {"optimizations": [], "architectural_rulings": []}
        return json.loads(self.db_path.read_text())

    def _save(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path.write_text(json.dumps(self.memory, indent=2))

    def append_optimization(self, author: str, finding: str):
        """Append a new structural optimization discovered by an AI model."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "author": author,
            "insight": finding
        }
        self.memory["optimizations"].append(entry)
        self._save()
        print(f"[Memory Bank] Successfully committed new optimization by {author}.")

    def retrieve_context(self) -> str:
        """Injects historic optimizations into a system prompt."""
        if not self.memory["optimizations"]:
            return "No previous optimizations recorded."
        
        # Get the 5 most recent insights to prevent context bloat
        recent = self.memory["optimizations"][-5:]
        context = "### Historic AI Optimizations (Do not repeat these mistakes):\n"
        for opt in recent:
            context += f"- [{opt['author']}] {opt['insight']}\n"
        return context

if __name__ == "__main__":
    memory = SharedTriadMemory()
    # Test read/write
    memory.append_optimization(
        author="gemini-3.8-flash", 
        finding="Tiny LMs must use bounded gradient clipping. Unbounded mutation vectors lead to NaN loss spikes within 40 iterations."
    )
    print("\n[Generated Context for Next Prompt]")
    print(memory.retrieve_context())
