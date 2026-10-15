import os
from pathlib import Path
from typing import Dict, Optional

class TriVaultRAG:
    """
    Parses Obsidian vault files and current tasks to construct 
    a highly compressed system prompt for local models.
    """
    def __init__(self, workspace_root: str = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo"):
        self.workspace_root = Path(workspace_root)
        self.obsidian_path = self.workspace_root / "obsidian_vault"
        
    def _read_file_safe(self, path: Path) -> str:
        if path.exists() and path.is_file():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return f.read().strip()
            except Exception:
                return ""
        return ""

    def get_core_architecture_rules(self) -> str:
        """Extracts the fundamental mesh invariants from the master index."""
        index_file = self.obsidian_path / "Index.md"
        content = self.self_heal_index_if_missing(index_file)
        
        # In a full RAG, we would parse Wikilinks and traverse. 
        # For this prototype, we return the master index summary.
        return f"TRI-VAULT ARCHITECTURE RULES:\n{content}"

    def self_heal_index_if_missing(self, index_file: Path) -> str:
        if not index_file.exists():
            # Trigger Self-Healing Protocol
            os.makedirs(index_file.parent, exist_ok=True)
            default_content = (
                "# 🧠 Lauburu AI Monorepo - Master Knowledge Vault\n"
                "- [[CANONICAL_PROJECT_AND_STORAGE_RULE]]\n"
                "- [[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]\n"
            )
            with open(index_file, "w") as f:
                f.write(default_content)
            return default_content
        return self._read_file_safe(index_file)

    def get_active_task_context(self, task_file_path: Optional[str] = None) -> str:
        """Reads the active checklist to inject into the model's immediate context."""
        if not task_file_path:
            return "No active task.md provided."
            
        task_path = Path(task_file_path)
        content = self._read_file_safe(task_path)
        if not content:
            return "Task file empty or unreadable."
            
        return f"ACTIVE TASK CONTEXT:\n{content}"

    def build_system_prompt(self, task_file_path: Optional[str] = None) -> str:
        """Assembles the final compressed context for the local Sovereign Orchestrator."""
        rules = self.get_core_architecture_rules()
        tasks = self.get_active_task_context(task_file_path)
        
        return (
            "You are Qwen 3.8 Max, the Sovereign Local Orchestrator of the Lauburu Mesh.\n"
            "You must obey the following architecture rules:\n"
            f"{rules}\n\n"
            "Here is the current task priority checklist:\n"
            f"{tasks}\n\n"
            "Act cleanly, directly, and delegate complex tool calls to the cloud Agy via <CALL_AGY: action>."
        )
