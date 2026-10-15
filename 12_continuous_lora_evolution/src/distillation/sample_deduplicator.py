"""
Sample Deduplication Engine for Continuous DPO & SFT Distillation.

Provides a multi-tier deduplication pipeline:
- Tier 1: Canonical field normalization & exact SHA-256 hash deduplication.
- Tier 2: 64-bit SimHash locality-sensitive hashing for near-duplicate rejection
          (e.g., catching identical prompts with only timestamps or minor variations).
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import unicodedata
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger(__name__)


def normalize_text(text: str) -> str:
    """
    Normalizes text for consistent hashing:
    - Unicode NFKC normalization
    - Stripping leading/trailing whitespace
    - Collapsing multiple whitespace/newlines into standard spaces
    """
    if not isinstance(text, str):
        text = str(text)
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_canonical_text(record: Union[str, Dict[str, Any]]) -> str:
    """
    Extracts a canonical string representation from a record dictionary or string.
    Handles DPO (prompt/chosen/rejected), SFT (instruction/input/output),
    CoT (thought/solution), and messages formats.
    """
    if isinstance(record, str):
        return normalize_text(record)

    if not isinstance(record, dict):
        return normalize_text(str(record))

    parts: List[str] = []

    # Priority 1: DPO schema
    if "prompt" in record and ("chosen" in record or "rejected" in record):
        parts.append(f"PROMPT:{normalize_text(record.get('prompt', ''))}")
        if "chosen" in record:
            parts.append(f"CHOSEN:{normalize_text(record.get('chosen', ''))}")
        if "rejected" in record:
            parts.append(f"REJECTED:{normalize_text(record.get('rejected', ''))}")
        return "||".join(parts)

    # Priority 2: SFT / CoT schema
    if "instruction" in record:
        parts.append(f"INSTRUCTION:{normalize_text(record.get('instruction', ''))}")
        if record.get("input"):
            parts.append(f"INPUT:{normalize_text(record.get('input', ''))}")
        if "thought" in record or "think" in record:
            thought = record.get("thought") or record.get("think") or ""
            parts.append(f"THOUGHT:{normalize_text(thought)}")
        if "output" in record or "solution" in record:
            out = record.get("output") or record.get("solution") or ""
            parts.append(f"OUTPUT:{normalize_text(out)}")
        if "response" in record:
            parts.append(f"RESPONSE:{normalize_text(record.get('response', ''))}")
        return "||".join(parts)

    # Priority 3: Messages schema
    if "messages" in record and isinstance(record["messages"], list):
        for msg in record["messages"]:
            if isinstance(msg, dict):
                role = msg.get("role", "")
                content = normalize_text(msg.get("content", ""))
                parts.append(f"{role.upper()}:{content}")
        return "||".join(parts)

    # Fallback: Sort all keys deterministically
    sorted_keys = sorted(record.keys())
    for k in sorted_keys:
        if k in ("timestamp", "timestamp_utc", "trial_id", "snapshot_id", "metadata"):
            continue
        v = record[k]
        if isinstance(v, (dict, list)):
            v_str = json.dumps(v, sort_keys=True)
        else:
            v_str = str(v)
        parts.append(f"{k.upper()}:{normalize_text(v_str)}")

    return "||".join(parts) if parts else normalize_text(json.dumps(record, sort_keys=True))


class SimHash:
    """
    64-bit SimHash implementation for locality-sensitive hashing over character shingles.
    """

    def __init__(self, shingle_size: int = 3, num_bits: int = 64):
        self.shingle_size = shingle_size
        self.num_bits = num_bits

    def _hash_shingle(self, shingle: str) -> int:
        """Computes a 64-bit integer hash for a shingle."""
        digest = hashlib.md5(shingle.encode("utf-8", errors="ignore")).digest()
        return int.from_bytes(digest[:8], byteorder="big", signed=False)

    def compute(self, text: str) -> int:
        """
        Computes the 64-bit SimHash integer for a given text.
        """
        text = normalize_text(text)
        if not text:
            return 0

        # Generate character shingles
        if len(text) < self.shingle_size:
            shingles = [text]
        else:
            shingles = [
                text[i : i + self.shingle_size]
                for i in range(len(text) - self.shingle_size + 1)
            ]

        if not shingles:
            return 0

        shingle_counts: Dict[str, int] = defaultdict(int)
        for s in shingles:
            shingle_counts[s] += 1

        v = [0] * self.num_bits
        for shingle, weight in shingle_counts.items():
            h = self._hash_shingle(shingle)
            for i in range(self.num_bits):
                bit = (h >> i) & 1
                if bit == 1:
                    v[i] += weight
                else:
                    v[i] -= weight

        fingerprint = 0
        for i in range(self.num_bits):
            if v[i] > 0:
                fingerprint |= 1 << i

        return fingerprint

    @staticmethod
    def hamming_distance(h1: int, h2: int) -> int:
        """Computes bitwise Hamming distance between two integer hashes."""
        x = h1 ^ h2
        return bin(x).count("1")

    @staticmethod
    def similarity(h1: int, h2: int, num_bits: int = 64) -> float:
        """Computes approximate similarity from Hamming distance."""
        dist = SimHash.hamming_distance(h1, h2)
        return 1.0 - (dist / float(num_bits))


class SampleDeduplicator:
    """
    Multi-Tier Sample Deduplicator for continuous training pipelines.
    
    Tier 1: Exact SHA-256 hash set (O(1) duplicate rejection).
    Tier 2: 64-bit SimHash LSH index for near-duplicate detection.
    """

    def __init__(
        self,
        enable_exact: bool = True,
        enable_simhash: bool = True,
        simhash_bits: int = 64,
        simhash_threshold: int = 6,
        similarity_threshold: Optional[float] = None,
        shingle_size: int = 3,
    ):
        self.enable_exact = enable_exact
        self.enable_simhash = enable_simhash
        self.simhash_bits = simhash_bits
        if similarity_threshold is not None:
            self.simhash_threshold = int((1.0 - similarity_threshold) * simhash_bits)
        else:
            self.simhash_threshold = simhash_threshold

        self.simhash_engine = SimHash(shingle_size=shingle_size, num_bits=simhash_bits)

        self.seen_exact_hashes: Set[str] = set()
        self.seen_simhashes: List[int] = []

        self.num_blocks = 4
        self.block_bits = simhash_bits // self.num_blocks
        self.simhash_buckets: Dict[Tuple[int, int], List[int]] = defaultdict(list)

    def _get_block_key(self, fingerprint: int, block_idx: int) -> int:
        mask = (1 << self.block_bits) - 1
        return (fingerprint >> (block_idx * self.block_bits)) & mask

    def compute_exact_hash(self, record: Union[str, Dict[str, Any]]) -> str:
        """Computes hex SHA-256 hash of canonicalized record."""
        canonical = extract_canonical_text(record)
        return hashlib.sha256(canonical.encode("utf-8", errors="ignore")).hexdigest()

    def compute_simhash(self, record: Union[str, Dict[str, Any]]) -> int:
        """Computes integer SimHash of canonicalized record."""
        canonical = extract_canonical_text(record)
        return self.simhash_engine.compute(canonical)

    def is_exact_duplicate(self, exact_hash: str) -> bool:
        """Returns True if exact SHA-256 hash has been seen."""
        return exact_hash in self.seen_exact_hashes

    def is_near_duplicate(self, simhash_val: int) -> Tuple[bool, int]:
        """
        Checks if simhash_val is within simhash_threshold Hamming distance of any seen hash.
        Returns (is_near_dup, min_distance).
        """
        if not self.seen_simhashes:
            return False, self.simhash_bits

        min_dist = self.simhash_bits
        # Fast candidate query via buckets
        candidates: Set[int] = set()
        for block_idx in range(self.num_blocks):
            key = (block_idx, self._get_block_key(simhash_val, block_idx))
            if key in self.simhash_buckets:
                for idx in self.simhash_buckets[key]:
                    candidates.add(self.seen_simhashes[idx])

        if candidates:
            for candidate in candidates:
                dist = self.simhash_engine.hamming_distance(simhash_val, candidate)
                if dist < min_dist:
                    min_dist = dist
                if dist <= self.simhash_threshold:
                    return True, dist

        # Check all seen hashes to guarantee zero false negatives
        for seen in self.seen_simhashes:
            dist = self.simhash_engine.hamming_distance(simhash_val, seen)
            if dist < min_dist:
                min_dist = dist
            if dist <= self.simhash_threshold:
                return True, dist

        return False, min_dist

    def check_duplicate(self, record: Union[str, Dict[str, Any]]) -> Tuple[bool, str]:
        """
        Evaluates whether a record is a duplicate.
        Returns:
            (is_duplicate: bool, reason: str)
        """
        if self.enable_exact:
            exact_h = self.compute_exact_hash(record)
            if self.is_exact_duplicate(exact_h):
                return True, "EXACT_DUPLICATE"

        if self.enable_simhash:
            sim_h = self.compute_simhash(record)
            if sim_h != 0:
                is_near, dist = self.is_near_duplicate(sim_h)
                if is_near:
                    return True, f"SIMHASH_NEAR_DUPLICATE (distance={dist})"

        return False, "UNIQUE"

    def add_record(self, record: Union[str, Dict[str, Any]]) -> bool:
        """
        Checks and records a new sample.
        Returns True if sample was unique and added, False if duplicate.
        """
        is_dup, reason = self.check_duplicate(record)
        if is_dup:
            return False

        if self.enable_exact:
            exact_h = self.compute_exact_hash(record)
            self.seen_exact_hashes.add(exact_h)

        if self.enable_simhash:
            sim_h = self.compute_simhash(record)
            if sim_h != 0:
                new_idx = len(self.seen_simhashes)
                self.seen_simhashes.append(sim_h)
                for block_idx in range(self.num_blocks):
                    key = (block_idx, self._get_block_key(sim_h, block_idx))
                    self.simhash_buckets[key].append(new_idx)

        return True

    def deduplicate_dataset(
        self, records: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Deduplicates a batch or list of dataset records.
        """
        unique_records: List[Dict[str, Any]] = []
        exact_dups = 0
        near_dups = 0

        for r in records:
            if self.enable_exact:
                eh = self.compute_exact_hash(r)
                if self.is_exact_duplicate(eh):
                    exact_dups += 1
                    continue

            if self.enable_simhash:
                sh = self.compute_simhash(r)
                if sh != 0:
                    is_near, _ = self.is_near_duplicate(sh)
                    if is_near:
                        near_dups += 1
                        continue

            self.add_record(r)
            unique_records.append(r)

        total_in = len(records)
        unique_out = len(unique_records)
        duplicate_count = exact_dups + near_dups
        dup_rate = (duplicate_count / total_in * 100.0) if total_in > 0 else 0.0

        stats = {
            "total_in": total_in,
            "exact_duplicates": exact_dups,
            "near_duplicates": near_dups,
            "total_duplicates": duplicate_count,
            "unique_out": unique_out,
            "duplicate_rate_pct": round(dup_rate, 2),
        }
        return unique_records, stats

    def save_state(self, filepath: str) -> None:
        state = {
            "seen_exact_hashes": list(self.seen_exact_hashes),
            "seen_simhashes": self.seen_simhashes,
            "simhash_threshold": self.simhash_threshold,
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(state, f)

    def load_state(self, filepath: str) -> None:
        with open(filepath, "r", encoding="utf-8") as f:
            state = json.load(f)
        self.clear()
        self.seen_exact_hashes = set(state.get("seen_exact_hashes", []))
        self.simhash_threshold = state.get("simhash_threshold", self.simhash_threshold)
        for sh in state.get("seen_simhashes", []):
            new_idx = len(self.seen_simhashes)
            self.seen_simhashes.append(sh)
            for block_idx in range(self.num_blocks):
                key = (block_idx, self._get_block_key(sh, block_idx))
                self.simhash_buckets[key].append(new_idx)

    def clear(self) -> None:
        self.seen_exact_hashes.clear()
        self.seen_simhashes.clear()
        self.simhash_buckets.clear()
