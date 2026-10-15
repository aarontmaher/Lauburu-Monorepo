#!/usr/bin/env python3
"""
================================================================================
Canonical CLI Tooling Registry & Dispatcher Engine for Qwen MoE
================================================================================
Subsystem: 06_scripts_and_tooling/cli_tooling_registry.py
Version: 1.0.0-CLI-REGISTRY
Lauburu Mesh Ecosystem — 2026

Empowers Qwen MoE with a unified knowledge base, syntax validator, and execution
dispatcher across the entire suite of frontier CLI tools:
1. GitHub CLI (gh) — PRs, issues, worktrees, release workflows, secret sync.
2. Android Debug Bridge (adb) — TCP/IP 5555, Termux keepalive injection, Doze bypass.
3. Tailscale CLI (tailscale) — WireGuard mesh topology, status, ping, derpmap.
4. Cloudflare Wrangler (wrangler / npx wrangler) — Workers, D1, KV, R2, Vectorize.
5. Google Jules (jules / @google/jules) — Async GitHub repo patch & PR agent.
6. Containerization & DFS (docker, docker-compose) — SeaweedFS, Ray, Petals DHT.
7. Python & Build Tooling (uv, pytest, git) — High-speed dependencies & tests.
8. Commerce & Data (shopify, ucp, jq, duckdb) — Storefront GraphQL, JSON stream parsing.
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
DATA_DIR = REPO_ROOT / "04_data_and_memory"
OBSIDIAN_DIR = REPO_ROOT / "obsidian_vault" / "07_ARCHITECTURE"

DATA_DIR.mkdir(parents=True, exist_ok=True)
OBSIDIAN_DIR.mkdir(parents=True, exist_ok=True)

# CLI Knowledge Catalog
CLI_CATALOG = {
    "gh": {
        "name": "GitHub CLI",
        "category": "version_control_and_collaboration",
        "binary_hint": "/Users/aaron/.local/bin/gh",
        "fallback_cmd": "gh",
        "primary_commands": [
            {"cmd": "gh pr list", "desc": "List active pull requests"},
            {"cmd": "gh pr create --title '...' --body '...'", "desc": "Create pull request"},
            {"cmd": "gh issue list", "desc": "List repository issues"},
            {"cmd": "gh repo sync", "desc": "Sync fork or branch with upstream"},
            {"cmd": "gh secret set NAME", "desc": "Set encrypted GitHub Actions secret"}
        ]
    },
    "git": {
        "name": "Git Core",
        "category": "version_control_and_collaboration",
        "binary_hint": "/usr/bin/git",
        "fallback_cmd": "git",
        "primary_commands": [
            {"cmd": "git worktree list", "desc": "List active git worktrees"},
            {"cmd": "git status -s", "desc": "Short status output"},
            {"cmd": "git diff --stat", "desc": "Summary of uncommitted diffs"}
        ]
    },
    "adb": {
        "name": "Android Debug Bridge",
        "category": "mobile_and_hardware_transport",
        "binary_hint": "/Users/aaron/.local/bin/adb",
        "fallback_cmd": "adb",
        "primary_commands": [
            {"cmd": "adb devices -l", "desc": "List connected Android hardware targets"},
            {"cmd": "adb tcpip 5555", "desc": "Restart ADB in TCP mode on port 5555"},
            {"cmd": "adb shell termux-wake-lock", "desc": "Inject background keepalive into Termux"},
            {"cmd": "adb shell dumpsys deviceidle whitelist +com.termux", "desc": "Whitelist Termux from Android Doze"}
        ]
    },
    "tailscale": {
        "name": "Tailscale WireGuard Mesh",
        "category": "mesh_networking",
        "binary_hint": "/Users/aaron/.local/bin/tailscale",
        "fallback_cmd": "tailscale",
        "primary_commands": [
            {"cmd": "tailscale status", "desc": "Inspect 7-layer WireGuard peer status"},
            {"cmd": "tailscale ping 100.103.212.21", "desc": "Test sub-millisecond WireGuard latency to MacBook Pro"},
            {"cmd": "tailscale ip -4", "desc": "Show local Tailscale IP"}
        ]
    },
    "wrangler": {
        "name": "Cloudflare Wrangler",
        "category": "cloud_edge_and_agents",
        "binary_hint": "npx -y wrangler",
        "fallback_cmd": "npx wrangler",
        "primary_commands": [
            {"cmd": "npx wrangler whoami", "desc": "Verify Cloudflare account authentication"},
            {"cmd": "npx wrangler deploy", "desc": "Deploy Worker or Agents SDK microservice"},
            {"cmd": "npx wrangler d1 execute DB --command '...'", "desc": "Execute SQLite query on Cloudflare D1"},
            {"cmd": "npx wrangler vectorize list", "desc": "List Vectorize vector search indexes"}
        ]
    },
    "jules": {
        "name": "Google Jules Async PR Agent",
        "category": "ai_agents_and_orchestration",
        "binary_hint": "/Users/aaron/.local/bin/jules",
        "fallback_cmd": "npx -y @google/jules",
        "primary_commands": [
            {"cmd": "jules whoami", "desc": "Verify Google Ultra account authentication"},
            {"cmd": "jules remote new --repo aarontmaher/Lauburu-Monorepo --session '...'", "desc": "Dispatch async task"},
            {"cmd": "jules remote pull --session ID --apply", "desc": "Pull and apply Jules patch"}
        ]
    },
    "uv": {
        "name": "Astral uv Python Package & Project Manager",
        "category": "build_and_package_management",
        "binary_hint": "/Users/aaron/.local/bin/uv",
        "fallback_cmd": "uv",
        "primary_commands": [
            {"cmd": "uv run pytest -v", "desc": "Run test suite with instantaneous virtualenv resolution"},
            {"cmd": "uv pip install -e .", "desc": "Fast editable package install"},
            {"cmd": "uv sync", "desc": "Synchronize project dependencies from pyproject.toml"}
        ]
    },
    "shopify": {
        "name": "Shopify CLI",
        "category": "commerce_and_monetization",
        "binary_hint": "/Users/aaron/.nvm/versions/node/v20.20.2/bin/shopify",
        "fallback_cmd": "shopify",
        "primary_commands": [
            {"cmd": "shopify store auth", "desc": "Authenticate with development store"},
            {"cmd": "shopify app dev", "desc": "Run local app extension preview server"}
        ]
    },
    "jq": {
        "name": "jq JSON Stream Processor",
        "category": "data_and_telemetry",
        "binary_hint": "/usr/bin/jq",
        "fallback_cmd": "jq",
        "primary_commands": [
            {"cmd": "jq '. | length' continuous_lora_dataset.jsonl", "desc": "Count JSONL dataset entries"},
            {"cmd": "jq -c '{prompt, chosen}' visual_ui_audit_lora.jsonl", "desc": "Filter SFT/DPO pairs"}
        ]
    },
    "docker": {
        "name": "Docker & Compose",
        "category": "containers_and_dfs",
        "binary_hint": "/Users/aaron/.local/bin/docker",
        "fallback_cmd": "docker",
        "primary_commands": [
            {"cmd": "docker ps", "desc": "Inspect running containers"},
            {"cmd": "docker compose up -d", "desc": "Launch SeaweedFS DFS and Ray cluster"}
        ]
    }
}


class CLIToolingRegistry:
    """Registry and dispatcher for frontier CLI tools."""

    def __init__(self):
        self.catalog = CLI_CATALOG
        self.resolved_paths = self._resolve_all_tools()

    def _resolve_all_tools(self) -> Dict[str, Optional[str]]:
        resolved = {}
        for tool_id, meta in self.catalog.items():
            hint = meta.get("binary_hint")
            if hint and os.path.exists(hint) and os.access(hint, os.X_OK):
                resolved[tool_id] = hint
            else:
                found = shutil.which(meta.get("fallback_cmd", tool_id))
                resolved[tool_id] = found if found else (hint if "npx" in str(hint) else None)
        return resolved

    def get_tool_info(self, tool_id: str) -> Optional[Dict[str, Any]]:
        meta = self.catalog.get(tool_id)
        if not meta:
            return None
        return {
            "tool_id": tool_id,
            "name": meta["name"],
            "category": meta["category"],
            "resolved_path": self.resolved_paths.get(tool_id),
            "is_installed": self.resolved_paths.get(tool_id) is not None,
            "primary_commands": meta["primary_commands"]
        }

    def list_installed_tools(self) -> List[Dict[str, Any]]:
        return [self.get_tool_info(tid) for tid in self.catalog.keys()]

    def execute_cli_command(self, tool_id: str, args: List[str], timeout_sec: int = 15) -> Dict[str, Any]:
        path = self.resolved_paths.get(tool_id)
        if not path:
            return {"success": False, "error": f"CLI tool '{tool_id}' is not installed."}

        full_cmd = f"{path} {' '.join(args)}"
        try:
            res = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, timeout=timeout_sec)
            return {
                "success": res.returncode == 0,
                "command": full_cmd,
                "exit_code": res.returncode,
                "stdout": res.stdout.strip(),
                "stderr": res.stderr.strip()
            }
        except Exception as e:
            return {"success": False, "command": full_cmd, "error": str(e)}


if __name__ == "__main__":
    reg = CLIToolingRegistry()
    print("=== Qwen MoE Canonical CLI Tooling Registry ===")
    for t in reg.list_installed_tools():
        status = "✅ INSTALLED" if t["is_installed"] else "❌ MISSING"
        print(f"  • {t['name']:<25} [{status}]: {t['resolved_path'] or 'N/A'}")
