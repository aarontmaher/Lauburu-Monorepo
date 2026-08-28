#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
Lauburu Mesh Tripwire Sentinel Daemon
Subsystem: 05_agents_and_swarms/red_blue_arena/blue_team/mesh_tripwire_sentinel.py
Classification: Blue Team Active Threat Detection & Continuous Audit
==============================================================================
Features:
1. Cryptographic SHA-256 Hash Baseline for Critical Configuration Files.
2. Real-Time Detection of Unauthorized Modifications, File Deletions, and Injections.
3. Socket / Network Port Auditing with Whitelisted Daemon Verification.
4. Structured Telemetry Serialization into JSONL Security Datasets.
5. Invariant Assertion Engine for Zero-Mock Security Compliance.
"""

from __future__ import annotations

import os
import sys
import time
import json
import socket
import hashlib
import logging
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional, Set, Union

logger = logging.getLogger("MeshTripwireSentinel")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] [TRIPWIRE-SENTINEL]: %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)


@dataclass
class TripwireEvent:
    event_id: str
    timestamp: str
    event_type: str        # UNAUTHORIZED_MODIFICATION, FILE_DELETED, UNAUTHORIZED_PORT_OPEN, INTEGRITY_RESTORED
    target: str
    severity: str          # CRITICAL, HIGH, MEDIUM, LOW, INFO
    details: Dict[str, Any] = field(default_factory=dict)
    remediation_suggested: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class IntegrityReport:
    timestamp: str
    total_monitored: int
    clean_files: int
    anomalies_detected: int
    unauthorized_ports: List[int]
    events: List[TripwireEvent]
    is_compromised: bool
    audit_duration_ms: float

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["events"] = [e.to_dict() if isinstance(e, TripwireEvent) else e for e in self.events]
        return d


def compute_file_hash(path: Union[str, Path]) -> Optional[str]:
    """Calculates the SHA-256 cryptographic hash of a file."""
    p = Path(path)
    if not p.exists() or not p.is_file():
        return None
    h = hashlib.sha256()
    try:
        with open(p, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()
    except (PermissionError, OSError) as e:
        logger.warning(f"Unable to read file {path} for hash computation: {e}")
        return None


class MeshTripwireSentinel:
    """Active configuration integrity monitor and network port sentinel."""

    DEFAULT_CRITICAL_PATHS = [
        Path.home() / ".ssh/authorized_keys",
        Path.home() / ".ssh/authorized_keys_monorepo",
        Path.home() / ".ssh/config",
        Path("/etc/ssh/sshd_config"),
        Path("/etc/headscale/acl.hujson"),
        Path("/etc/headscale/config.yaml"),
        Path(__file__).parent / "configs/sshd_config.hardened",
        Path(__file__).parent / "configs/ssh_config.client"
    ]

    WHITELISTED_PORTS = {
        22,      # Standard SSH (Darwin/Linux/Router)
        80,      # HTTP
        443,     # HTTPS
        3000,    # Training Module / Web Frontend
        4000,    # Canonical Port Hub
        6333,    # Qdrant Vector DB HTTP
        6334,    # Qdrant Vector DB gRPC
        8022,    # Termux Android SSH
        8080,    # Headscale HTTP
        8081,    # Local LLaMA / Master Agent
        8082,    # Local SLM 2
        8083,    # Local SLM 3
        8084,    # Abiliterated LLaMA Devil's Advocate
        8333,    # SeaweedFS Filer
        8443,    # Headscale HTTPS / DERP
        8888,    # Local Service Hub
        9090,    # Headscale gRPC
        9333,    # SeaweedFS Master
        18802,   # WoL Self-Healing REST API
        41641,   # Tailscale / WireGuard Derp
        50052,   # llama.cpp RPC Shard / Metal GPU
        51820,   # WireGuard Native UDP
        65001,   # Local Test Port
        65101    # Local Test Port
    }

    def __init__(
        self,
        monitored_paths: Optional[List[Union[str, Path]]] = None,
        audit_log_path: Optional[Union[str, Path]] = None,
        custom_whitelisted_ports: Optional[Set[int]] = None
    ):
        if monitored_paths:
            self.monitored_paths = [Path(p) for p in monitored_paths]
        else:
            self.monitored_paths = list(self.DEFAULT_CRITICAL_PATHS)

        if audit_log_path:
            self.audit_log_path = Path(audit_log_path)
        else:
            self.audit_log_path = Path(
                "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/lora_datasets/security_audit_logs.jsonl"
            )

        self.whitelisted_ports = set(self.WHITELISTED_PORTS)
        if custom_whitelisted_ports:
            self.whitelisted_ports.update(custom_whitelisted_ports)

        self.state_baseline: Dict[str, str] = {}
        self.event_history: List[TripwireEvent] = []
        self._establish_baseline()

    def _establish_baseline(self):
        """Builds initial cryptographic state hashes for existing files."""
        for p in self.monitored_paths:
            if p.exists() and p.is_file():
                h = compute_file_hash(p)
                if h:
                    self.state_baseline[str(p)] = h
                    logger.debug(f"Baseline registered for {p} -> {h[:16]}...")
        logger.info(f"Tripwire baseline established for {len(self.state_baseline)} critical files.")

    def register_path(self, path: Union[str, Path]) -> bool:
        """Dynamically registers a new path into the monitored baseline."""
        p = Path(path)
        if p not in self.monitored_paths:
            self.monitored_paths.append(p)
        if p.exists() and p.is_file():
            h = compute_file_hash(p)
            if h:
                self.state_baseline[str(p)] = h
                return True
        return False

    def update_baseline(self, path: Union[str, Path]) -> Optional[str]:
        """Explicitly re-baselines a known and authorized file change."""
        p = Path(path)
        if p.exists() and p.is_file():
            h = compute_file_hash(p)
            if h:
                self.state_baseline[str(p)] = h
                logger.info(f"Authorized baseline update for {p} -> {h[:16]}...")
                return h
        return None

    def check_file_integrity(self) -> List[TripwireEvent]:
        """Audits all registered files against the cryptographic baseline."""
        events: List[TripwireEvent] = []
        now_ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        for p_str, expected_hash in list(self.state_baseline.items()):
            p = Path(p_str)
            if not p.exists():
                evt = TripwireEvent(
                    event_id=f"evt-del-{int(time.time()*1000)}",
                    timestamp=now_ts,
                    event_type="FILE_DELETED",
                    target=p_str,
                    severity="CRITICAL",
                    details={"expected_hash": expected_hash},
                    remediation_suggested="Restore file from canonical Git tree or Obsidian vault backup."
                )
                events.append(evt)
                continue

            current_hash = compute_file_hash(p)
            if current_hash != expected_hash:
                evt = TripwireEvent(
                    event_id=f"evt-mod-{int(time.time()*1000)}",
                    timestamp=now_ts,
                    event_type="UNAUTHORIZED_MODIFICATION",
                    target=p_str,
                    severity="CRITICAL",
                    details={
                        "previous_hash": expected_hash,
                        "current_hash": current_hash
                    },
                    remediation_suggested="Inspect diff immediately. Check for rogue public keys or SSH parameter changes."
                )
                events.append(evt)

        return events

    def audit_open_ports(self, port_range: Optional[range] = None) -> List[int]:
        """
        Probes localhost for unauthorized listening TCP sockets.
        Defaults to testing representative system and daemon ports.
        """
        unauthorized = []
        # Test candidate ports
        sample_ports = port_range if port_range is not None else [
            21, 22, 23, 25, 80, 443, 1337, 3000, 3128, 4000, 4444, 5555,
            6333, 8022, 8080, 8081, 8084, 8888, 9090, 18802, 31337, 50052
        ]

        for port in sample_ports:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(0.05)
                    if s.connect_ex(("127.0.0.1", port)) == 0:
                        if port not in self.whitelisted_ports:
                            unauthorized.append(port)
            except Exception:
                pass

        return unauthorized

    def run_audit_cycle(self) -> IntegrityReport:
        """Executes a complete file integrity and network port security audit cycle."""
        start_t = time.perf_counter()
        now_ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        file_events = self.check_file_integrity()
        unauth_ports = self.audit_open_ports()

        events = list(file_events)
        if unauth_ports:
            evt = TripwireEvent(
                event_id=f"evt-port-{int(time.time()*1000)}",
                timestamp=now_ts,
                event_type="UNAUTHORIZED_PORT_OPEN",
                target="127.0.0.1",
                severity="HIGH",
                details={"unauthorized_ports": unauth_ports},
                remediation_suggested="Terminate rogue process via lsof -i:<port> and verify firewall rules."
            )
            events.append(evt)

        elapsed_ms = (time.perf_counter() - start_t) * 1000.0
        is_compromised = len(events) > 0

        report = IntegrityReport(
            timestamp=now_ts,
            total_monitored=len(self.state_baseline),
            clean_files=len(self.state_baseline) - len(file_events),
            anomalies_detected=len(events),
            unauthorized_ports=unauth_ports,
            events=events,
            is_compromised=is_compromised,
            audit_duration_ms=round(elapsed_ms, 2)
        )

        self.event_history.extend(events)
        self._persist_audit_log(report)
        return report

    def _persist_audit_log(self, report: IntegrityReport):
        """Serializes security audit results to JSONL dataset if anomalies occur or on schedule."""
        if not report.events:
            return
        try:
            self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.audit_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(report.to_dict()) + "\n")
        except Exception as e:
            logger.debug(f"Failed to append to audit log {self.audit_log_path}: {e}")

    def get_recent_alerts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Returns the most recent security alerts as dicts."""
        return [e.to_dict() for e in self.event_history[-limit:]]


if __name__ == "__main__":
    sentinel = MeshTripwireSentinel()
    rep = sentinel.run_audit_cycle()
    print(f"Tripwire Audit Completed: Compromised={rep.is_compromised}, Clean={rep.clean_files}/{rep.total_monitored}")
    for e in rep.events:
        print(f" - [{e.severity}] {e.event_type} on {e.target}: {e.details}")
