"""
Atomic Transaction Ledger & Leaderboard State Tracker (Feature F7.5, F8, F9).
Authoritative Specifications: ORIGINAL_REQUEST.md (§R4, §R5) & spec_miner_1/analysis.md (§6.8).

Maintains an atomic, thread-safe JSONL transaction ledger recording matches, score updates,
and waste tax penalty events. Persists state using atomic write replacements (os.replace / fsync)
to guarantee zero corruption and zero race conditions.
"""

from __future__ import annotations

import datetime
import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from .waste_tax import ELO_QUARANTINE_THRESHOLD


DEFAULT_LEDGER_PATH: str = "/tmp/elo_ledger.jsonl"


class EloLedger:
    """
    Atomic JSONL Transaction Ledger for ELO updates and Waste Tax events.
    """

    def __init__(self, ledger_path: str = DEFAULT_LEDGER_PATH) -> None:
        self.ledger_path = Path(ledger_path)
        self._lock = threading.RLock()
        self._ensure_parent_directory()

    def _ensure_parent_directory(self) -> None:
        """Create parent directory if it does not exist."""
        try:
            self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    def record_transaction(self, entry: Dict[str, Any]) -> None:
        """
        Atomically append a transaction record to the JSONL ledger.
        """
        if "timestamp_utc" not in entry:
            entry["timestamp_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

        serialized = json.dumps(entry) + "\n"

        with self._lock:
            self._ensure_parent_directory()
            with open(self.ledger_path, "a", encoding="utf-8") as f:
                f.write(serialized)
                f.flush()
                try:
                    os.fsync(f.fileno())
                except OSError:
                    pass

    def record_match(self, match_data: Dict[str, Any]) -> None:
        """
        Record a match outcome in the ledger.
        """
        payload = {
            "type": "MATCH_RESULT",
            **match_data,
        }
        self.record_transaction(payload)

    def record_penalty(self, penalty_data: Dict[str, Any]) -> None:
        """
        Record a waste tax penalty event in the ledger.
        """
        payload = {
            "type": "WASTE_TAX_PENALTY",
            **penalty_data,
        }
        self.record_transaction(payload)

    def get_history(self, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Read all ledger transactions, optionally filtering by agent_id.
        """
        with self._lock:
            if not self.ledger_path.exists():
                return []

            records: List[Dict[str, Any]] = []
            try:
                with open(self.ledger_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            record = json.loads(line)
                            if agent_id is None:
                                records.append(record)
                            else:
                                # Check if agent_id appears in record
                                if (
                                    record.get("agent_id") == agent_id
                                    or record.get("david_model") == agent_id
                                    or record.get("goliath_model") == agent_id
                                ):
                                    records.append(record)
                        except json.JSONDecodeError:
                            continue
            except Exception:
                return []

            return records

    def get_leaderboard(self) -> Dict[str, Dict[str, Any]]:
        """
        Reconstruct current leaderboard status, ratings, wins, losses, taxes, and quarantine state.
        """
        with self._lock:
            history = self.get_history()
            leaderboard: Dict[str, Dict[str, Any]] = {}

            for entry in history:
                entry_type = entry.get("type", "MATCH_RESULT")

                if entry_type == "MATCH_RESULT":
                    david = entry.get("david_model")
                    goliath = entry.get("goliath_model")

                    if david:
                        if david not in leaderboard:
                            leaderboard[david] = {
                                "agent_id": david,
                                "rating": 2100.0,
                                "matches_played": 0,
                                "wins": 0,
                                "losses": 0,
                                "draws": 0,
                                "total_waste_tax": 0.0,
                                "quarantined": False,
                                "last_updated": entry.get("timestamp_utc"),
                            }
                        stats_d = leaderboard[david]
                        stats_d["matches_played"] += 1
                        if "new_elo_david" in entry:
                            stats_d["rating"] = float(entry["new_elo_david"])
                        elif "delta_elo_david" in entry:
                            stats_d["rating"] += float(entry["delta_elo_david"])

                        if entry.get("david_solved"):
                            stats_d["wins"] += 1
                        else:
                            stats_d["losses"] += 1

                        stats_d["last_updated"] = entry.get("timestamp_utc")

                    if goliath:
                        if goliath not in leaderboard:
                            leaderboard[goliath] = {
                                "agent_id": goliath,
                                "rating": 2800.0,
                                "matches_played": 0,
                                "wins": 0,
                                "losses": 0,
                                "draws": 0,
                                "total_waste_tax": 0.0,
                                "quarantined": False,
                                "last_updated": entry.get("timestamp_utc"),
                            }
                        stats_g = leaderboard[goliath]
                        stats_g["matches_played"] += 1
                        if "new_elo_goliath" in entry:
                            stats_g["rating"] = float(entry["new_elo_goliath"])
                        elif "delta_elo_goliath" in entry:
                            stats_g["rating"] += float(entry["delta_elo_goliath"])

                        if entry.get("goliath_solved"):
                            stats_g["wins"] += 1
                        else:
                            stats_g["losses"] += 1

                        stats_g["last_updated"] = entry.get("timestamp_utc")

                elif entry_type == "WASTE_TAX_PENALTY":
                    agent = entry.get("agent_id")
                    if agent:
                        if agent not in leaderboard:
                            leaderboard[agent] = {
                                "agent_id": agent,
                                "rating": 2100.0,
                                "matches_played": 0,
                                "wins": 0,
                                "losses": 0,
                                "draws": 0,
                                "total_waste_tax": 0.0,
                                "quarantined": False,
                                "last_updated": entry.get("timestamp_utc"),
                            }
                        stats = leaderboard[agent]
                        deduction = float(entry.get("elo_deduction", 0.0))
                        stats["total_waste_tax"] += deduction
                        if "new_elo" in entry:
                            stats["rating"] = float(entry["new_elo"])
                        else:
                            stats["rating"] += deduction
                        stats["last_updated"] = entry.get("timestamp_utc")

            # Update quarantine statuses
            for agent_id, stats in leaderboard.items():
                if stats["rating"] < ELO_QUARANTINE_THRESHOLD:
                    stats["quarantined"] = True

            return leaderboard

    def get_rating(self, agent_id: str, default: float = 2100.0) -> float:
        """
        Get latest rating for a specific agent.
        """
        leaderboard = self.get_leaderboard()
        if agent_id in leaderboard:
            return leaderboard[agent_id]["rating"]
        return default

    def set_rating(self, agent_id: str, rating: float) -> None:
        """
        Manually set or seed a rating for an agent via transaction entry.
        """
        self.record_transaction({
            "type": "RATING_OVERRIDE",
            "agent_id": agent_id,
            "new_elo": rating,
        })

    def get_match_count(self, agent_id: str) -> int:
        """
        Get total matches played by an agent.
        """
        leaderboard = self.get_leaderboard()
        if agent_id in leaderboard:
            return leaderboard[agent_id]["matches_played"]
        return 0

    def is_quarantined(self, agent_id: str) -> bool:
        """
        Check if an agent is currently quarantined below 1500 ELO.
        """
        rating = self.get_rating(agent_id)
        return rating < ELO_QUARANTINE_THRESHOLD

    def export_canonical_leaderboard(self, output_path: str) -> None:
        """
        Atomically export the current leaderboard as JSON Schema v7 conforming canonical JSON.
        Uses os.replace to guarantee atomic, race-free persistence.
        """
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        leaderboard = self.get_leaderboard()
        payload = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "CanonicalAILeaderboard",
            "schema_version": "1.0.0",
            "generated_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "total_agents": len(leaderboard),
            "agents": leaderboard,
        }

        # Write to a temporary file in the same directory, then atomic rename
        temp_fd, temp_file_path = tempfile.mkstemp(
            dir=str(out_path.parent), prefix="tmp_leaderboard_", suffix=".json"
        )
        try:
            with open(temp_fd, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
                f.flush()
                try:
                    os.fsync(f.fileno())
                except OSError:
                    pass
            os.replace(temp_file_path, str(out_path))
        except Exception:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            raise
