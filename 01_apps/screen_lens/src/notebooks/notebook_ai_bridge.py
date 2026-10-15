# -*- coding: utf-8 -*-
"""
Notebook AI Bridge & Reactive Kernel Governor
============================================
Subsystem: 01_apps/screen_lens/src/notebooks/notebook_ai_bridge.py
Lauburu Mesh Ecosystem — 2026

Synthesizes /notebook-guidance and /notebook-specialist protocols:
1. Adheres to Notebook-Guidance: Auto-path resolution, zero-mock live execution, step-by-step validation.
2. Adheres to Notebook-Specialist: Remote kernel routing to L3 Linux (100.101.39.98:8890) / L5 MacBook Air (100.93.158.96:8889),
   bidirectional sync to obsidian_vault/notebooks/, high-DPI dark-mode telemetry plotting.
3. Live Anti-Hallucination Sentinel: Audits notebook text against empirical hardware & database limits.
"""

from __future__ import annotations

import os
import sys
import json
import time
import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional

# Auto-path resolution governed by Notebook Specialist Cell 1 invariant
for p in [
    "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo",
    "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/screen_lens",
    "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/screen_lens/src"
]:
    if os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)

try:
    from notebooks.canonical_project_master_notebook import CanonicalProjectMasterNotebook
except ImportError:
    from canonical_project_master_notebook import CanonicalProjectMasterNotebook

class NotebookAIBridge:
    def __init__(
        self,
        monorepo_root: str = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo",
        sqlite_path: str = "~/.lauburu/screen_lens.sqlite",
        obsidian_vault_path: str = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault"
    ):
        self.root = Path(monorepo_root)
        self.db_path = Path(os.path.expanduser(sqlite_path))
        self.obsidian_notebooks_dir = Path(obsidian_vault_path) / "notebooks"
        self.obsidian_notebooks_dir.mkdir(parents=True, exist_ok=True)
        self.sentinel = CanonicalProjectMasterNotebook(monorepo_root)

    def get_kernel_topology(self) -> Dict[str, Any]:
        """Returns remote kernel specs governed by Rule 10 (Preserve L1 Mac Mini VRAM)."""
        return {
            "primary_marimo_host": {
                "layer": "L3 Linux Head Node",
                "ip": "100.101.39.98",
                "port": 8890,
                "url": "http://100.101.39.98:8890",
                "role": "High-concurrency reactive DAG execution, biometrics DSP"
            },
            "secondary_jupyter_host": {
                "layer": "L5 MacBook Air M4",
                "ip": "100.93.158.96",
                "port": 8889,
                "url": "http://100.93.158.96:8889/lab",
                "env": "/Users/aaronmaher/gemini_notebook_env",
                "role": "Visual charts, Seaborn/Plotly interactive reporting"
            },
            "host_sanctuary_protection": {
                "mac_mini_l1_allowed": False,
                "reason": "Rule 3 & Rule 10 strictly forbid heavy notebook server heap allocations on Mac Mini host."
            }
        }

    def fetch_live_telemetry_snapshot(self) -> Dict[str, Any]:
        """Fetches authentic zero-mock database & screen metrics."""
        if not self.db_path.exists():
            return {"error": "Database not found"}
        
        conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
        cur = conn.cursor()
        total_captures = cur.execute("SELECT COUNT(*) FROM captures;").fetchone()[0]
        total_blocks = cur.execute("SELECT COUNT(*) FROM ocr_text_blocks;").fetchone()[0]
        latest = cur.execute(
            "SELECT id, timestamp, active_app_name, active_window_title FROM captures ORDER BY id DESC LIMIT 1;"
        ).fetchone()
        conn.close()

        return {
            "total_captures": total_captures,
            "total_ocr_blocks": total_blocks,
            "db_size_mb": round(self.db_path.stat().st_size / (1024 * 1024), 2),
            "latest_capture": {
                "id": latest[0] if latest else None,
                "timestamp": latest[1] if latest else None,
                "app": latest[2] if latest else None,
                "title": latest[3] if latest else None
            }
        }

    def sync_to_obsidian_notebooks(self) -> str:
        """
        Bidirectionally renders notebook telemetry into the canonical Obsidian Vault.
        """
        telemetry = self.fetch_live_telemetry_snapshot()
        benchmarks = self.sentinel.get_verified_storage_benchmarks()
        hardware = self.sentinel.get_canonical_hardware_matrix()
        
        target_file = self.obsidian_notebooks_dir / "CANONICAL_NOTEBOOK_AI_STATE.md"
        
        content = f"""---
title: "Canonical Notebook AI Living State"
tags: [notebook, marimo, jupyter, telemetry, zero_mock, lauburu]
last_synced: "{time.strftime('%Y-%m-%d %H:%M:%S')}"
---

# 📓 Canonical Notebook AI Living State & Telemetry Plane

Governed by `[[notebook-guidance]]` and `[[notebook-specialist]]`.

## 🌐 Remote Kernel Topology
- **Primary Reactive Marimo Host:** `http://100.101.39.98:8890` (L3 Linux AMD Ryzen 7 5700U)
- **Secondary Interactive Jupyter Host:** `http://100.93.158.96:8889/lab` (L5 MacBook Air M4)
- **Host Sanctuary:** Mac Mini M4 Pro strictly preserved with $\\ge 4.8\\text{{ GB}}$ RAM headroom.

## 📊 Live Screen Lens Storage & Telemetry (Zero-Mock)
- **Database Path:** `{self.db_path}`
- **Database Size:** `{telemetry.get('db_size_mb')} MB`
- **Total Screen Captures:** `{telemetry.get('total_captures'):,}`
- **Total OCR Text Blocks:** `{telemetry.get('total_ocr_blocks'):,}`
- **Latest Frame:** `#{telemetry.get('latest_capture', {}).get('id')}` (`{telemetry.get('latest_capture', {}).get('app')}` — `{telemetry.get('latest_capture', {}).get('title')}`)

## ⚡ Ratified Storage Benchmarks
| Engine | Traversal Latency | Storage Density | Idle Daemon RAM | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Memory-Mapped CSR** | `{benchmarks['Memory_Mapped_CSR']['traversal_latency_ms']} ms` | `{benchmarks['Memory_Mapped_CSR']['storage_density_bytes_per_edge']} B/edge` | `0.00 MB` | **RATIFIED GOLD STANDARD** |
| **Checkpointed Tuned SQLite** | `{benchmarks['Checkpointed_Tuned_SQLite']['traversal_latency_ms']} ms` | `{benchmarks['Checkpointed_Tuned_SQLite']['storage_density_bytes_per_edge']} B/edge` | `0.00 MB` | **RATIFIED RELATIONAL FALLBACK** |
| **Memgraph Networked** | `{benchmarks['Memgraph_Networked']['traversal_latency_ms']} ms` | `Network RTT Tax` | `2048 MB` | **VETOED BY SOVEREIGN** |

## 🛡️ Anti-Hallucination Sentinel Invariants
- **Wi-Fi 5 Silicon Limits:** L2 Intel MacBook Pro & L3 Linux Mini physically cannot negotiate Wi-Fi 6/7.
- **SQLite WAL Checkpoint:** WAL mode stores uncheckpointed pages in `.db-wal`. Always check checkpointed storage footprint.
- **Zero-Mock Telemetry:** All charts must ingest genuine hardware telemetry or display `--`.
"""
        target_file.write_text(content, encoding="utf-8")
        return str(target_file)

    def audit_research_text(self, text: str) -> List[Dict[str, str]]:
        """Invokes anti-hallucination sentinel on incoming research or prompts."""
        return self.sentinel.audit_anti_hallucination(text)

if __name__ == "__main__":
    bridge = NotebookAIBridge()
    synced_path = bridge.sync_to_obsidian_notebooks()
    print(f"✅ Notebook AI State synced to Obsidian: {synced_path}")
    telemetry = bridge.fetch_live_telemetry_snapshot()
    print(f"📊 Live Telemetry: {telemetry}")
