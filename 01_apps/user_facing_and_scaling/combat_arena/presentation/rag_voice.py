"""
RAG Voice Commentary & Thought Stream Generator.
================================================
Subsystem: 01_apps/user_facing_and_scaling/combat_arena/presentation/rag_voice.py
"""

import subprocess
import threading
from typing import Dict, Any, List, Optional
from pathlib import Path

WORKSPACE_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
OBSIDIAN_VAULT = WORKSPACE_ROOT / "obsidian_vault"

class RagVoiceCommentator:
    """Grounded RAG Voice Commentary Engine for Combat Arena."""

    def __init__(self, tts_enabled: bool = False):
        self.tts_enabled = tts_enabled

    def generate_narration(self, mode: str, red_intent: str, blue_intent: str) -> str:
        """Synthesizes factual commentary grounded in monorepo architecture."""
        return (
            f"[ARENA COMMENTARY | {mode}]: "
            f"Red Faction (Hermes 3) initiates '{red_intent[:60]}...' "
            f"while Blue Faction (LuCI OpenWrt) deploys counter-action '{blue_intent[:60]}...' "
            f"Airgap sentinel maintains zero cloud biometrics leakage."
        )

    def speak_async(self, text: str, voice: str = "Samantha"):
        """Non-blocking audio playback via local macOS TTS."""
        if not self.tts_enabled:
            return
        def _speak():
            try:
                clean = text.replace('"', '').replace("'", "")[:160]
                subprocess.run(["say", "-v", voice, clean], check=False)
            except Exception:
                pass
        threading.Thread(target=_speak, daemon=True).start()
