"""
9-Screen Stability Hierarchy for Canonical Port NOC.
====================================================
Subsystem: 01_apps/operator_and_dev/canonical_port/views/screens.py
"""

from typing import List
from ..core.models import StabilityScreenInfo

STABILITY_SCREENS: List[StabilityScreenInfo] = [
    StabilityScreenInfo(1, "overview", "Screen 1: Mesh Topology & System Overview", "1"),
    StabilityScreenInfo(2, "nodes", "Screen 2: 7 Physical Nodes & Dynamic Caps", "2"),
    StabilityScreenInfo(3, "memory", "Screen 3: 108GB RAM Pool & Headroom Governor", "3"),
    StabilityScreenInfo(4, "biometrics", "Screen 4: 512Hz Bicep ECG & PTT Hemodynamics", "4"),
    StabilityScreenInfo(5, "inference", "Screen 5: llama.cpp RPC & Multi-Model Sharding", "5"),
    StabilityScreenInfo(6, "debate", "Screen 6: AI Debate Council & Genetic MoE", "6"),
    StabilityScreenInfo(7, "tri_vault", "Screen 7: Tri-Vault Storage (Obsidian, PySpark, Git)", "7"),
    StabilityScreenInfo(8, "airgap", "Screen 8: Cloudflare Zero-Leak Biometrics Firewall", "8"),
    StabilityScreenInfo(9, "logs", "Screen 9: Audit Logs & 4-Tier E2E Test Suite", "9"),
]
