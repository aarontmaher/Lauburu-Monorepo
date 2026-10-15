#!/usr/bin/env python3
"""
================================================================================
Unified Tooling & API Registry Engine for Qwen MoE
================================================================================
Subsystem: 06_scripts_and_tooling/unified_tooling_and_api_registry.py
Version: 2.0.0-UNIFIED-TOOL-REGISTRY
Lauburu Mesh Ecosystem — 2026

Unifies the entire 4-Tier Tooling Catalog for Qwen MoE:
1. Google Cloud APIs & SDKs (Cloud Run, Cloud Storage, Vertex AI, Jules)
2. Google Workspace APIs (Drive v3, Gmail v1, Chat Card v2, Sheets v4, Docs v1)
3. Monorepo Systems CLIs (gh, git, adb, tailscale, wrangler, uv, jq, docker, shopify)
4. Local Physical Mesh APIs (Screen Lens :3035, Prima.cpp :8082, TB4 DMA bridge0)
================================================================================
"""

import os
import sys
import time
import json
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional

REPO_ROOT = Path(os.environ.get("LAUBURU_ROOT", "/Volumes/Lauburu-Monorepo"))
if not REPO_ROOT.exists():
    REPO_ROOT = Path(__file__).resolve().parents[1]
AUTH_DIR = REPO_ROOT / "00_core_infrastructure/auth"
NOTIF_DIR = REPO_ROOT / "06_scripts_and_tooling/notifications"

if str(AUTH_DIR) not in sys.path:
    sys.path.insert(0, str(AUTH_DIR))
if str(NOTIF_DIR) not in sys.path:
    sys.path.insert(0, str(NOTIF_DIR))

# Unified 4-Tier Tool & API Catalog
UNIFIED_TOOL_CATALOG = {
    # ── Tier 1: Google Cloud APIs & SDKs ────────────────────────────────────
    "google_cloud_run": {
        "tier": "google_cloud",
        "name": "Google Cloud Run API & MCP",
        "category": "cloud_compute",
        "capabilities": ["Container Deployment", "Serverless Services", "Service Logs", "Direct Revision Rollouts"],
        "auth_type": "ADC / Service Account Key",
        "sdk_package": "google-cloud-run"
    },
    "google_cloud_storage": {
        "tier": "google_cloud",
        "name": "Google Cloud Storage API (GCS)",
        "category": "cloud_storage",
        "capabilities": ["Bucket Sync", "Large LoRA Checkpoint Backup", "Resumable Uploads", "Blob Streaming"],
        "auth_type": "ADC / IAM Token",
        "sdk_package": "google-cloud-storage"
    },
    "google_vertex_ai": {
        "tier": "google_cloud",
        "name": "Google Vertex AI & Gemini Interactions API",
        "category": "cloud_ai",
        "capabilities": ["Gemini 2.0 Pro Exp", "Flash Thinking Exp", "Function Calling", "Multimodal Video/Audio"],
        "auth_type": "GEMINI_API_KEY / Express Mode",
        "sdk_package": "google-genai"
    },
    "google_jules": {
        "tier": "google_cloud",
        "name": "Google Jules Async GitHub Agent",
        "category": "autonomous_coding",
        "capabilities": ["Multi-file Repo Refactoring", "Async Session Polling", "Automated Diff Patching"],
        "auth_type": "Google Ultra Account Token",
        "binary_path": "/Users/aaron/.local/bin/jules"
    },
    "nvidia_nim_deepseek_v4": {
        "tier": "google_cloud",
        "name": "NVIDIA NIM DeepSeek V4 (1.6T Pro / 284B Flash)",
        "category": "frontier_cloud_ai",
        "capabilities": ["1.6T MoE Reasoning (49B Active)", "284B MoE High-Speed Coding", "1,000,000 Context Window", "OpenAI Compatible REST"],
        "auth_type": "NVIDIA_API_KEY (Bearer Token)",
        "endpoint": "https://integrate.api.nvidia.com/v1/chat/completions"
    },

    # ── Tier 2: Google Workspace APIs ───────────────────────────────────────
    "google_drive_api": {
        "tier": "google_workspace",
        "name": "Google Drive API v3",
        "category": "workspace_storage",
        "capabilities": ["2TB Cold Storage Sync", "Folder Search", "Chunked File Upload", "LoRA Dataset Ingestion"],
        "auth_type": "Domain-Wide Delegation (DWD)",
        "subject": "lauburu@lauburugrappling.com",
        "scope": "https://www.googleapis.com/auth/drive"
    },
    "google_gmail_api": {
        "tier": "google_workspace",
        "name": "Gmail API v1",
        "category": "communication_and_alerts",
        "capabilities": ["Out-of-band Mesh Alerting", "Audit Digest Emails", "Automated Incident Escalation"],
        "auth_type": "Domain-Wide Delegation (DWD)",
        "subject": "lauburu@lauburugrappling.com",
        "scope": "https://www.googleapis.com/auth/gmail.send"
    },
    "google_chat_api": {
        "tier": "google_workspace",
        "name": "Google Chat API & Card v2 Bridge",
        "category": "realtime_messaging",
        "capabilities": ["Interactive Card v2 UI", "Real-time Mesh Telemetry Alerts", "AI Debate Verdict Cards"],
        "auth_type": "Webhook & DWD Chat Bot",
        "scope": "https://www.googleapis.com/auth/chat.bot"
    },
    "google_sheets_api": {
        "tier": "google_workspace",
        "name": "Google Sheets API v4",
        "category": "analytics_and_dashboards",
        "capabilities": ["Live Telemetry Streaming", "Looker Studio Connectors", "Tournament ELO Data Feeds"],
        "auth_type": "Domain-Wide Delegation (DWD)",
        "scope": "https://www.googleapis.com/auth/spreadsheets"
    },
    "google_docs_api": {
        "tier": "google_workspace",
        "name": "Google Docs API v1",
        "category": "whitepaper_publishing",
        "capabilities": ["Automated Architecture Paper Export", "Consensus Whitepaper Formatting"],
        "auth_type": "Domain-Wide Delegation (DWD)",
        "scope": "https://www.googleapis.com/auth/documents"
    },

    # ── Tier 3: Monorepo Systems CLIs ───────────────────────────────────────
    "gh": {
        "tier": "systems_cli",
        "name": "GitHub CLI",
        "category": "version_control",
        "binary_path": "/Users/aaron/.local/bin/gh",
        "capabilities": ["PR Management", "Issue Backlogs", "Fork Syncing", "GHA Secret Injection"]
    },
    "git": {
        "tier": "systems_cli",
        "name": "Git Core",
        "category": "version_control",
        "binary_path": "/usr/bin/git",
        "capabilities": ["Worktrees", "Branch Lineage", "Sparse Checkouts", "Commit Stamping"]
    },
    "adb": {
        "tier": "systems_cli",
        "name": "Android Debug Bridge",
        "category": "mobile_transport",
        "binary_path": "/Users/aaron/.local/bin/adb",
        "capabilities": ["Port 5555 TCP", "Termux Keepalive Injection", "Android 15 Doze Whitelisting"]
    },
    "tailscale": {
        "tier": "systems_cli",
        "name": "Tailscale WireGuard Mesh",
        "category": "mesh_overlay",
        "binary_path": "/Users/aaron/.local/bin/tailscale",
        "capabilities": ["7-Layer Peer Topology", "Sub-ms Mesh Ping", "Encrypted DERP Relay"]
    },
    "wrangler": {
        "tier": "systems_cli",
        "name": "Cloudflare Wrangler & Agents SDK",
        "category": "cloud_edge",
        "binary_path": "npx -y wrangler",
        "capabilities": ["Stateful Durable Objects", "D1 SQLite Queries", "Vectorize Search", "Workers AI"]
    },
    "uv": {
        "tier": "systems_cli",
        "name": "Astral uv Package Manager",
        "category": "python_build",
        "binary_path": "/Users/aaron/.local/bin/uv",
        "capabilities": ["Fast Virtualenv Resolution", "Test Runner Acceleration", "PyPI Mirror Caching"]
    },

    # ── Tier 4: Local Physical Mesh APIs ────────────────────────────────────
    "screen_lens_rest": {
        "tier": "local_mesh_api",
        "name": "Screen Lens Real-Time Perception Daemon",
        "category": "multimodal_vision",
        "endpoint": "http://127.0.0.1:3035",
        "capabilities": ["OCR Screen Capture", "Active Window State", "Visual ROI Bounding Box"]
    },
    "prima_distributed_ring": {
        "tier": "local_mesh_api",
        "name": "Prima.cpp Pipelined-Ring Sharder",
        "category": "distributed_inference",
        "endpoint": "http://127.0.0.1:8082",
        "capabilities": ["Ring Parallel Tensor Slicing", "10Gbps TB4 DMA Transport", "0ms Host Offload"]
    },
    "llama_server_devils_advocate": {
        "tier": "local_mesh_api",
        "name": "llama-server Devil's Advocate",
        "category": "local_reasoning",
        "endpoint": "http://127.0.0.1:8083",
        "capabilities": ["Qwen 2.5 Coder 7B", "Qwen 3.8 Max 27B Abliterated", "Adversarial Code Audits"]
    },
    "tb4_pcie_dma_bridge": {
        "tier": "local_mesh_api",
        "name": "Thunderbolt 4 PCIe DMA Interconnect",
        "category": "hardware_transport",
        "interface": "bridge0",
        "capabilities": ["0.277ms Latency", "40 Gbps Bandwidth", "MTU 9000 Jumbo Frames", "Metal AllReduce"]
    }
}


class UnifiedToolingRegistry:
    """Master Tooling & API Orchestrator for Qwen MoE."""

    def __init__(self):
        self.catalog = UNIFIED_TOOL_CATALOG

    def list_all_tools(self) -> List[Dict[str, Any]]:
        result = []
        for tid, data in self.catalog.items():
            entry = {"id": tid}
            entry.update(data)
            result.append(entry)
        return result

    def get_tools_by_tier(self, tier_name: str) -> List[Dict[str, Any]]:
        return [t for t in self.list_all_tools() if t.get("tier") == tier_name]

    def query_tool_capability(self, keyword: str) -> List[Dict[str, Any]]:
        matches = []
        kw_lower = keyword.lower()
        for t in self.list_all_tools():
            caps = " ".join(t.get("capabilities", [])).lower()
            name = t.get("name", "").lower()
            if kw_lower in name or kw_lower in caps or kw_lower in t.get("category", ""):
                matches.append(t)
        return matches


if __name__ == "__main__":
    reg = UnifiedToolingRegistry()
    print("=== Qwen MoE Unified Tooling & API Registry ===")
    for tier in ["google_cloud", "google_workspace", "systems_cli", "local_mesh_api"]:
        tools = reg.get_tools_by_tier(tier)
        print(f"\n📂 Tier [{tier.upper()}]: ({len(tools)} registered tools)")
        for t in tools:
            print(f"  • {t['name']:<40} | Category: {t['category']}")
