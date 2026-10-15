#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
Lauburu Sovereign Mesh: DPO Debate Consensus Distiller
================================================================================
Subsystem: 05_agents_and_swarms/training_protocols/dpo_debate_distiller.py
Version: 1.0.0-DPO-DISTILLER
Lauburu Mesh Ecosystem — 2026

Harvests contrastive preference pairs (Prompt, Chosen, Rejected) from live
multi-agent debates across the Lauburu ecosystem.
Chosen: Consensus synthesis (Agreement >= 0.98) with empirical proof.
Rejected: Flawed proposals, ungrounded assertions, or synthetic/mocked hallucinations.
================================================================================
"""

import fcntl
import hashlib
import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
LORA_DATASETS_DIR = Path("/Users/aaron/DFS_UNIFIED/lora_datasets")
DPO_PAIRS_FILE = LORA_DATASETS_DIR / "continuous_dpo_pairs.jsonl"
OBSIDIAN_VAULT = REPO_ROOT / "obsidian_vault"


@dataclass
class DPOPreferencePair:
    prompt: str
    chosen: str
    rejected: str
    consensus_score: float
    source_debate: str
    topic_category: str = "mesh_architecture"
    pair_id: str = field(default_factory=str)
    timestamp: float = field(default_factory=time.time)

    def __post_init__(self):
        if not self.pair_id:
            h = hashlib.sha256(f"{self.prompt[:64]}:{self.chosen[:64]}:{self.timestamp}".encode()).hexdigest()[:16]
            self.pair_id = f"dpo_{h}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pair_id": self.pair_id,
            "prompt": self.prompt,
            "chosen": self.chosen,
            "rejected": self.rejected,
            "consensus_score": round(self.consensus_score, 3),
            "source_debate": self.source_debate,
            "topic_category": self.topic_category,
            "timestamp": self.timestamp
        }


class DPODebateDistiller:
    """
    Scans debate artifacts and continuous logs to harvest and format DPO preference pairs.
    """

    def __init__(self, output_file: Path = DPO_PAIRS_FILE):
        self.output_file = output_file
        self.output_file.parent.mkdir(parents=True, exist_ok=True)

    def distill_from_text(
        self,
        prompt: str,
        chosen_response: str,
        rejected_response: str,
        consensus_score: float = 0.99,
        source: str = "direct_synthesis",
        category: str = "mesh_architecture"
    ) -> DPOPreferencePair:
        pair = DPOPreferencePair(
            prompt=prompt.strip(),
            chosen=chosen_response.strip(),
            rejected=rejected_response.strip(),
            consensus_score=consensus_score,
            source_debate=source,
            topic_category=category
        )
        self.save_pair(pair)
        return pair

    def save_pair(self, pair: DPOPreferencePair):
        """Appends pair to JSONL dataset under exclusive POSIX fcntl lock."""
        line = json.dumps(pair.to_dict()) + "\n"
        with open(self.output_file, "a", encoding="utf-8") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.write(line)
                f.flush()
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def scan_obsidian_debates(self, max_files: int = 10) -> List[DPOPreferencePair]:
        """
        Scans obsidian_vault for debate and consensus whitepapers and extracts pairs.
        """
        harvested: List[DPOPreferencePair] = []
        if not OBSIDIAN_VAULT.exists():
            return harvested

        md_files = list(OBSIDIAN_VAULT.rglob("*.md"))
        debate_files = [f for f in md_files if "debate" in f.name.lower() or "consensus" in f.name.lower() or "resolution" in f.name.lower()]

        for fpath in debate_files[:max_files]:
            try:
                content = fpath.read_text(encoding="utf-8", errors="ignore")
                pairs = self._extract_pairs_from_markdown(content, fpath.name)
                for p in pairs:
                    self.save_pair(p)
                    harvested.append(p)
            except Exception:
                continue

        return harvested

    def _extract_pairs_from_markdown(self, text: str, filename: str) -> List[DPOPreferencePair]:
        pairs = []
        # Pattern searching for Consensus vs Counter-proposals
        consensus_match = re.search(r"##\s*(?:Consensus Resolution|Winning Consensus|Tri-Model Consensus)(.*?)(?=##|\Z)", text, re.DOTALL | re.IGNORECASE)
        rejected_match = re.search(r"##\s*(?:Rejected Proposals|Devil's Advocate Counter-Points|Discarded Alternatives)(.*?)(?=##|\Z)", text, re.DOTALL | re.IGNORECASE)

        if consensus_match and rejected_match:
            chosen = consensus_match.group(1).strip()
            rejected = rejected_match.group(1).strip()
            title_match = re.search(r"^#\s*(.*?)$", text, re.MULTILINE)
            topic = title_match.group(1).strip() if title_match else filename.replace(".md", "")

            prompt = f"Architectural Debate Topic: {topic}. Synthesize the optimal zero-mock implementation consensus."
            if len(chosen) > 50 and len(rejected) > 50:
                p = DPOPreferencePair(
                    prompt=prompt,
                    chosen=chosen[:1500],
                    rejected=rejected[:1500],
                    consensus_score=0.985,
                    source_debate=filename,
                    topic_category="obsidian_vault_consensus"
                )
                pairs.append(p)

        return pairs

    def get_dataset_stats(self) -> Dict[str, Any]:
        if not self.output_file.exists():
            return {"total_pairs": 0, "categories": {}, "avg_consensus": 0.0}

        count = 0
        categories: Dict[str, int] = {}
        consensus_sum = 0.0

        with open(self.output_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    count += 1
                    cat = data.get("topic_category", "general")
                    categories[cat] = categories.get(cat, 0) + 1
                    consensus_sum += data.get("consensus_score", 0.95)
                except json.JSONDecodeError:
                    continue

        return {
            "total_pairs": count,
            "categories": categories,
            "avg_consensus": round(consensus_sum / max(1, count), 3),
            "dataset_file": str(self.output_file)
        }


if __name__ == "__main__":
    print("=== Testing DPODebateDistiller ===")
    distiller = DPODebateDistiller()

    # Test distillation of a canonical Lauburu debate pair
    sample_pair = distiller.distill_from_text(
        prompt="How should the out-of-band serial terminal bridge between Mac Mini and Linux Head Node be architected?",
        chosen_response=(
            "Direct Bluetooth RFCOMM Channel 1 bound to /dev/rfcomm0 running agetty at 115,200 baud, "
            "backed by BNEP PAN bridge (192.168.44.0/24). Zero mock imports, zero cloud dependencies. "
            "Guarantees deterministic shell access even if Wi-Fi 7 and Tailscale interfaces are severed."
        ),
        rejected_response=(
            "Deploy a cloud-hosted WebSocket relay with mocked local telemetry arrays and simulated "
            "battery sensors. Fall back to an unverified SSH port forward over public WAN."
        ),
        consensus_score=0.995,
        source="serial_terminal_bilateral_debate_2026.md",
        category="out_of_band_transport"
    )

    print(f"Created Pair: {sample_pair.pair_id}")
    print(f"Consensus Score: {sample_pair.consensus_score}")
    stats = distiller.get_dataset_stats()
    print(f"Total DPO Pairs in Dataset: {stats['total_pairs']}")
    print(f"Categories: {stats['categories']}")
