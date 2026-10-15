"""
80/20 Stratified Replay Buffer Engine for Anti-Catastrophic Forgetting.

Maintains partitioned domain reservoirs for foundational competencies:
1. biometrics_dsp: 512Hz ECG DSP, Pan-Tompkins, PTT Blood Pressure
2. mesh_healing: OpenWrt networking, WoL resurrection, Tailscale routing
3. code_correctness: Python AST, SWE-bench refactoring, zero-mock invariants
4. system_architecture: Tri-vault storage, monorepo cohesion, security
5. general_reasoning: AI debate consensus, tool invocation planning

Provides 80% active innovation + 20% historical anchor domain stratification.
"""

from __future__ import annotations

import json
import logging
import math
import os
import random
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

CANONICAL_ANCHOR_DOMAINS = [
    "biometrics_dsp",
    "mesh_healing",
    "code_correctness",
    "system_architecture",
    "general_reasoning",
]


class DomainReservoir:
    """
    Fixed-capacity reservoir for a single domain with priority / reservoir replacement.
    """

    def __init__(self, domain: str, max_capacity: int = 2000):
        self.domain = domain
        self.max_capacity = max_capacity
        self.items: List[Dict[str, Any]] = []
        self.priorities: List[float] = []

    def __len__(self) -> int:
        return len(self.items)

    def add(self, item: Dict[str, Any], priority: float = 1.0) -> bool:
        """
        Adds an item to the reservoir. Uses priority/reservoir sampling if full.
        """
        if len(self.items) < self.max_capacity:
            self.items.append(item)
            self.priorities.append(priority)
            return True

        # Reservoir is full: replace item with probability or lowest priority
        min_p_idx = self.priorities.index(min(self.priorities))
        if priority > self.priorities[min_p_idx]:
            self.items[min_p_idx] = item
            self.priorities[min_p_idx] = priority
            return True
        else:
            # Standard reservoir sampling replacement with probability max_capacity / total_seen
            replace_idx = random.randint(0, self.max_capacity - 1)
            self.items[replace_idx] = item
            self.priorities[replace_idx] = priority
            return True

    def sample(self, count: int) -> List[Dict[str, Any]]:
        """Samples up to `count` items without replacement if count <= len, else with replacement."""
        if not self.items:
            return []
        if count <= len(self.items):
            return random.sample(self.items, count)
        return random.choices(self.items, k=count)

    def clear(self) -> None:
        self.items.clear()
        self.priorities.clear()


class StratifiedReplayBuffer:
    """
    Stratified Replay Buffer managing active and historical domain streams.
    """

    def __init__(
        self,
        reservoir_capacity: int = 2000,
        active_ratio: float = 0.80,
        seed: Optional[int] = 42,
    ):
        self.reservoir_capacity = reservoir_capacity
        self.active_ratio = active_ratio
        if seed is not None:
            random.seed(seed)

        self.reservoirs: Dict[str, DomainReservoir] = {
            dom: DomainReservoir(dom, max_capacity=reservoir_capacity)
            for dom in CANONICAL_ANCHOR_DOMAINS
        }

    def infer_domain(self, record: Dict[str, Any]) -> str:
        """
        Infers canonical anchor domain from record content or metadata.
        """
        if "domain" in record and record["domain"] in self.reservoirs:
            return record["domain"]

        meta = record.get("metadata", {}) or record.get("meta", {})
        if isinstance(meta, dict) and "domain" in meta and meta["domain"] in self.reservoirs:
            return meta["domain"]

        text = json.dumps(record).lower()

        if any(k in text for k in ("ecg", "biometric", "pan-tompkins", "qrs", "ptt", "heart_rate")):
            return "biometrics_dsp"
        if any(k in text for k in ("openwrt", "mesh", "tailscale", "wol", "router", "wake_on_lan")):
            return "mesh_healing"
        if any(k in text for k in ("def ", "python", "ast", "swe_bench", "syntaxerror", "pytest")):
            return "code_correctness"
        if any(k in text for k in ("obsidian", "tri-vault", "architecture", "monorepo", "storage_rule")):
            return "system_architecture"

        return "general_reasoning"

    def add_anchor_sample(
        self,
        sample: Dict[str, Any],
        domain: Optional[str] = None,
        priority: float = 1.0,
    ) -> bool:
        """
        Adds a verified anchor sample into the appropriate domain reservoir.
        """
        target_domain = domain if domain and domain in self.reservoirs else self.infer_domain(sample)
        if target_domain not in self.reservoirs:
            self.reservoirs[target_domain] = DomainReservoir(target_domain, max_capacity=self.reservoir_capacity)

        return self.reservoirs[target_domain].add(sample, priority=priority)

    def load_anchor_dataset(
        self, dataset_records: List[Dict[str, Any]], domain: Optional[str] = None
    ) -> int:
        """
        Populates reservoirs with a list of anchor records.
        Returns total count of samples loaded.
        """
        count = 0
        for r in dataset_records:
            if self.add_anchor_sample(r, domain=domain):
                count += 1
        return count

    def get_total_anchor_count(self) -> int:
        """Returns the total number of anchor samples stored across all reservoirs."""
        return sum(len(res) for res in self.reservoirs.values())

    def get_domain_counts(self) -> Dict[str, int]:
        """Returns the count of samples in each domain reservoir."""
        return {dom: len(res) for dom, res in self.reservoirs.items()}

    def sample_replay_items(self, count: int) -> List[Dict[str, Any]]:
        """
        Samples `count` replay items uniformly across non-empty domain reservoirs.
        """
        active_domains = [dom for dom, res in self.reservoirs.items() if len(res) > 0]
        if not active_domains or count <= 0:
            return []

        sampled_items: List[Dict[str, Any]] = []
        per_domain = max(1, count // len(active_domains))

        for dom in active_domains:
            if len(sampled_items) >= count:
                break
            needed = min(per_domain, count - len(sampled_items))
            sampled_items.extend(self.reservoirs[dom].sample(needed))

        # If still short, sample randomly from any available domain
        while len(sampled_items) < count:
            dom = random.choice(active_domains)
            sampled_items.extend(self.reservoirs[dom].sample(1))

        return sampled_items[:count]

    def sample_stratified_batch(
        self,
        active_items: List[Dict[str, Any]],
        batch_size: int,
        active_ratio: Optional[float] = None,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Constructs a stratified batch combining active items and anchor replay items.
        
        Default ratio is 80% active / 20% replay.
        If batch_size is 1, randomly selects active with probability active_ratio.
        """
        ratio = active_ratio if active_ratio is not None else self.active_ratio

        if batch_size <= 0:
            return [], {"active": 0, "replay": 0, "total": 0}

        total_anchors = self.get_total_anchor_count()

        if total_anchors == 0:
            # No replay available: return up to batch_size active items
            chosen = active_items[:batch_size] if len(active_items) >= batch_size else active_items
            return chosen, {"active": len(chosen), "replay": 0, "total": len(chosen)}

        if batch_size == 1:
            if random.random() < ratio and active_items:
                chosen = [random.choice(active_items)]
                return chosen, {"active": 1, "replay": 0, "total": 1}
            else:
                chosen = self.sample_replay_items(1)
                return chosen, {"active": 0, "replay": 1, "total": 1}

        target_active = math.floor(batch_size * ratio)
        target_replay = batch_size - target_active

        # Guarantee at least 1 replay if batch_size >= 4 and anchors exist
        if target_replay == 0 and batch_size >= 4 and total_anchors > 0:
            target_replay = 1
            target_active = batch_size - 1

        # Sample active
        if len(active_items) >= target_active:
            sampled_active = random.sample(active_items, target_active)
        else:
            sampled_active = list(active_items)

        # Sample replay
        sampled_replay = self.sample_replay_items(target_replay)

        # If active underfilled, backfill with replay
        shortfall = batch_size - (len(sampled_active) + len(sampled_replay))
        if shortfall > 0 and total_anchors > 0:
            sampled_replay.extend(self.sample_replay_items(shortfall))

        batch = sampled_active + sampled_replay
        random.shuffle(batch)

        meta = {
            "active": len(sampled_active),
            "replay": len(sampled_replay),
            "total": len(batch),
            "domains": self.get_domain_counts(),
        }
        return batch, meta

    def create_stratified_dataset(
        self,
        active_dataset: List[Dict[str, Any]],
        replay_ratio: float = 0.20,
    ) -> List[Dict[str, Any]]:
        """
        Augments an active dataset by injecting historical anchor items according to replay_ratio.
        """
        if not active_dataset or self.get_total_anchor_count() == 0 or replay_ratio <= 0:
            return list(active_dataset)

        num_active = len(active_dataset)
        num_replay = int(math.ceil(num_active * (replay_ratio / (1.0 - replay_ratio))))
        replay_items = self.sample_replay_items(num_replay)

        combined = list(active_dataset) + replay_items
        random.shuffle(combined)
        return combined

    def save_state(self, filepath: str) -> None:
        """Serializes all reservoirs to a JSON file."""
        state: Dict[str, Any] = {
            "reservoir_capacity": self.reservoir_capacity,
            "active_ratio": self.active_ratio,
            "reservoirs": {},
        }
        for dom, res in self.reservoirs.items():
            state["reservoirs"][dom] = {
                "items": res.items,
                "priorities": res.priorities,
            }

        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(state, f)

    def load_state(self, filepath: str) -> None:
        """Restores reservoirs from a serialized JSON file."""
        with open(filepath, "r", encoding="utf-8") as f:
            state = json.load(f)

        self.reservoir_capacity = state.get("reservoir_capacity", self.reservoir_capacity)
        self.active_ratio = state.get("active_ratio", self.active_ratio)

        for dom, res_data in state.get("reservoirs", {}).items():
            if dom not in self.reservoirs:
                self.reservoirs[dom] = DomainReservoir(dom, max_capacity=self.reservoir_capacity)
            self.reservoirs[dom].items = res_data.get("items", [])
            self.reservoirs[dom].priorities = res_data.get("priorities", [])
