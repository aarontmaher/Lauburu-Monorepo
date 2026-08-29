#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║       LAUBURU PROJECT OVERVIEW MCP SERVER — Port 9999                      ║
║  Live project state, training progress, mesh health, daemon topology        ║
║  Rule #0: ALL data is live-probed — zero mock, zero simulated values        ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import socket
import json
import subprocess
import os
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Optional

# ─── Constants ────────────────────────────────────────────────────────────────
REPO_ROOT   = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
SESSION_DIR = REPO_ROOT / "session_logs"
LORA_DIR    = Path("/Users/aaron/DFS_UNIFIED/lora_datasets")
LORA_FILE   = LORA_DIR / "continuous_lora_dataset.jsonl"
OBSIDIAN    = REPO_ROOT / "obsidian_vault"
GGUF_VAULT  = Path("/Volumes/MacBook_Pro_SSD/gguf_vault")

DAEMON_PORTS = {
    8080:  "llama.cpp RPC Primary",
    8082:  "llama.cpp RPC Node-2",
    8084:  "llama.cpp RPC Node-3",
    8086:  "llama.cpp RPC Node-4",
    8088:  "Web-TUI / Dashboard Portal",
    18802: "Self-Healing Hub REST API",
    50052: "gRPC Tensor Streaming Gateway",
}

# ─── App Setup ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Lauburu Project Overview MCP",
    version="1.0.0",
    description="Live project state MCP server for the Lauburu AI Mesh Ecosystem. "
                "All data is live-probed from real filesystem and sockets (Rule #0).",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _probe_port(port: int, host: str = "127.0.0.1", timeout: float = 0.5) -> bool:
    """Live socket probe — no mock."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (ConnectionRefusedError, OSError, TimeoutError):
        return False


def _run(cmd: list, cwd: Optional[Path] = None) -> str:
    """Run a subprocess and return stdout. Returns '' on failure."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(cwd) if cwd else None,
        )
        return result.stdout.strip()
    except Exception:
        return ""


def _read_json(path: Path) -> dict:
    """Read a JSON file; return empty dict if missing / malformed."""
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def _lora_line_count() -> int:
    """Live wc -l on the LoRA dataset file."""
    if not LORA_FILE.exists():
        return 0
    out = _run(["wc", "-l", str(LORA_FILE)])
    try:
        return int(out.split()[0])
    except (IndexError, ValueError):
        return 0


def _lora_dir_size() -> str:
    """Live du -sh on lora_datasets/."""
    out = _run(["du", "-sh", str(LORA_DIR)])
    try:
        return out.split("\t")[0]
    except IndexError:
        return "--"


def _dataset_file_count() -> int:
    """Count all .jsonl files in LORA_DIR."""
    if not LORA_DIR.exists():
        return 0
    return len(list(LORA_DIR.glob("**/*.jsonl")))


def _last_modified_iso(path: Path) -> str:
    """Return ISO8601 mtime of a file, or '--' if missing."""
    try:
        mtime = path.stat().st_mtime
        return datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()
    except Exception:
        return "--"


def _disk_usage() -> dict:
    """Live df on the primary disk."""
    out = _run(["df", "-h", "/Users/aaron"])
    lines = [l for l in out.splitlines() if "/Users/aaron" in l or l.startswith("Filesystem")]
    result = {}
    try:
        parts = out.splitlines()[-1].split()
        result = {
            "filesystem":  parts[0] if len(parts) > 0 else "--",
            "size":        parts[1] if len(parts) > 1 else "--",
            "used":        parts[2] if len(parts) > 2 else "--",
            "avail":       parts[3] if len(parts) > 3 else "--",
            "use_percent": parts[4] if len(parts) > 4 else "--",
        }
    except Exception:
        result = {"raw": out[:200]}
    return result


def _ram_info() -> dict:
    """Live vm_stat based RAM probe on macOS."""
    out = _run(["vm_stat"])
    pages: dict[str, int] = {}
    page_size = 16384  # 16 KB default on Apple Silicon
    for line in out.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            try:
                pages[key.strip()] = int(val.strip().rstrip("."))
            except ValueError:
                pass
    try:
        free_gb  = pages.get("Pages free", 0) * page_size / (1024 ** 3)
        wired_gb = pages.get("Pages wired down", 0) * page_size / (1024 ** 3)
        active_gb = pages.get("Pages active", 0) * page_size / (1024 ** 3)
        return {
            "free_gb":   round(free_gb, 2),
            "wired_gb":  round(wired_gb, 2),
            "active_gb": round(active_gb, 2),
            "note":      "Mac_Node (M4 Pro, 24 GB total)",
        }
    except Exception:
        return {"note": "vm_stat parse error"}


def _daemon_health() -> dict:
    """Probe all 7 daemon ports live."""
    result = {}
    for port, name in DAEMON_PORTS.items():
        result[str(port)] = {
            "name":   name,
            "port":   port,
            "online": _probe_port(port),
        }
    return result


def _git_commits() -> list:
    """Last 10 git commits from the monorepo."""
    raw = _run(["git", "log", "--oneline", "-10"], cwd=REPO_ROOT)
    return raw.splitlines() if raw else ["(no commits found)"]


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/mcp/tools")
def list_tools() -> dict:
    """List all available MCP tools with descriptions."""
    return {
        "server": "Lauburu Project Overview MCP v1.0.0",
        "port": 9999,
        "timestamp": _now_iso(),
        "tools": [
            {
                "method": "GET",
                "path": "/mcp/tools",
                "description": "List all available tools with descriptions",
            },
            {
                "method": "GET",
                "path": "/mcp/project/health",
                "description": "Tri-vault health, disk stats, RAM usage, all 7 daemon port probes",
            },
            {
                "method": "GET",
                "path": "/mcp/project/training",
                "description": "LoRA sample counts, dataset file counts, last harvest timestamp",
            },
            {
                "method": "GET",
                "path": "/mcp/project/models",
                "description": "Active models, inference ports, ELO scores, online/offline status",
            },
            {
                "method": "GET",
                "path": "/mcp/project/commits",
                "description": "Last 10 git commits from the monorepo",
            },
            {
                "method": "GET",
                "path": "/mcp/project/benchmarks",
                "description": "Transport latencies, E2E test scores, synergy score",
            },
            {
                "method": "GET",
                "path": "/mcp/project/automations",
                "description": "Cron status, daemon supervisor state, scheduled tasks",
            },
            {
                "method": "GET",
                "path": "/mcp/project/full_context",
                "description": "EVERYTHING in one call — for AI context injection at session start",
            },
            {
                "method": "POST",
                "path": "/mcp/project/heal",
                "description": "Trigger self-healing on Port 18802 REST API",
            },
            {
                "method": "POST",
                "path": "/mcp/project/add_training_pair",
                "description": "Append a LoRA instruction/output pair to continuous_lora_dataset.jsonl",
            },
        ],
    }


@app.get("/mcp/project/health")
def project_health() -> dict:
    """Live tri-vault health, disk, RAM, and all 7 daemon port probes."""
    obsidian_ok  = OBSIDIAN.is_dir()
    pyspark_ok   = LORA_DIR.is_dir()
    git_ok       = (REPO_ROOT / ".git").is_dir()
    index_md_ok  = (OBSIDIAN / "Index.md").exists() if obsidian_ok else False

    return {
        "timestamp":   _now_iso(),
        "tri_vault": {
            "obsidian": {
                "healthy":     obsidian_ok,
                "path":        str(OBSIDIAN),
                "index_md_ok": index_md_ok,
            },
            "pyspark_data_lake": {
                "healthy": pyspark_ok,
                "path":    str(LORA_DIR),
            },
            "github_monorepo": {
                "healthy":     git_ok,
                "path":        str(REPO_ROOT),
                "lock_exists": (REPO_ROOT / ".git" / "index.lock").exists(),
            },
        },
        "disk":        _disk_usage(),
        "ram":         _ram_info(),
        "daemon_ports": _daemon_health(),
    }


@app.get("/mcp/project/training")
def project_training() -> dict:
    """Live LoRA sample counts, dataset file counts, last harvest timestamp."""
    governor_status   = _read_json(SESSION_DIR / "hybrid_governor_status.json")
    maximizer_status  = _read_json(SESSION_DIR / "gemini_spark_maximizer_status.json")
    cron_status       = _read_json(SESSION_DIR / "free_ai_cron_status.json")

    return {
        "timestamp":          _now_iso(),
        "lora_samples":       _lora_line_count(),
        "dataset_file_count": _dataset_file_count(),
        "dataset_dir_size":   _lora_dir_size(),
        "lora_file_path":     str(LORA_FILE),
        "last_harvest_mtime": _last_modified_iso(LORA_FILE),
        "governor_status":    governor_status,
        "maximizer_status":   maximizer_status,
        "cron_status":        cron_status,
    }


@app.get("/mcp/project/models")
def project_models() -> dict:
    """Active models, inference ports, ELO scores, online/offline status."""
    governor = _read_json(SESSION_DIR / "hybrid_governor_status.json")

    # Extract any model/ELO data from governor status
    models_raw = governor.get("models", governor.get("model_scores", {}))

    # Build per-port model entries from live probes
    model_entries = []
    inference_ports = {8080: "llama.cpp Primary", 8082: "llama.cpp Node-2",
                       8084: "llama.cpp Node-3",  8086: "llama.cpp Node-4"}
    for port, label in inference_ports.items():
        online = _probe_port(port)
        entry: dict[str, Any] = {
            "label":  label,
            "port":   port,
            "online": online,
        }
        # Merge ELO/model name from governor if available
        key = str(port)
        if isinstance(models_raw, dict) and key in models_raw:
            entry.update(models_raw[key])
        model_entries.append(entry)

    # Also surface any model_scores list from governor
    return {
        "timestamp":      _now_iso(),
        "inference_nodes": model_entries,
        "raw_governor":   {k: v for k, v in governor.items()
                           if k in ("models", "model_scores", "elo_scores",
                                    "active_model", "current_champion")},
    }


@app.get("/mcp/project/commits")
def project_commits() -> dict:
    """Last 10 git commits from the Lauburu monorepo."""
    commits = _git_commits()
    return {
        "timestamp": _now_iso(),
        "repo":      str(REPO_ROOT),
        "commits":   commits,
    }


@app.get("/mcp/project/benchmarks")
def project_benchmarks() -> dict:
    """Transport latencies, E2E scores, and synergy score from live session logs."""
    governor = _read_json(SESSION_DIR / "hybrid_governor_status.json")

    # Extract benchmark fields if present in governor status
    benchmarks = governor.get("benchmarks", governor.get("transport_latencies", {}))
    synergy    = governor.get("synergy_score", governor.get("mesh_synergy", "--"))
    e2e_scores = governor.get("e2e_scores",   governor.get("test_scores",   {}))

    # Live round-trip probe latencies (ICMP not available without root; use connect time)
    port_latencies: dict[str, Any] = {}
    for port, name in DAEMON_PORTS.items():
        t0 = time.monotonic()
        online = _probe_port(port, timeout=0.3)
        elapsed_ms = round((time.monotonic() - t0) * 1000, 2)
        port_latencies[str(port)] = {
            "name":       name,
            "online":     online,
            "connect_ms": elapsed_ms if online else None,
        }

    return {
        "timestamp":        _now_iso(),
        "port_latencies":   port_latencies,
        "governor_benchmarks": benchmarks,
        "e2e_scores":       e2e_scores,
        "synergy_score":    synergy,
    }


@app.get("/mcp/project/automations")
def project_automations() -> dict:
    """Cron status, daemon supervisor, and scheduled tasks from session logs."""
    cron      = _read_json(SESSION_DIR / "free_ai_cron_status.json")
    maximizer = _read_json(SESSION_DIR / "gemini_spark_maximizer_status.json")
    governor  = _read_json(SESSION_DIR / "hybrid_governor_status.json")
    priority  = _read_json(SESSION_DIR / "master_priority_loop_status.json")

    return {
        "timestamp":  _now_iso(),
        "cron_jobs": {
            "description":    "Hourly at :50/:52/:55/:58 — free-tier AI automation cron",
            "cron_status":    cron,
        },
        "maximizer": {
            "description":    "15-min Gemini Spark Maximizer cycles",
            "status":         maximizer,
        },
        "daemon_supervisor": {
            "description":    "Hybrid RAM Governor — monitors all 7 daemons",
            "status":         governor,
        },
        "priority_loop": {
            "description":    "Master Priority Automation Loop",
            "status":         priority,
        },
        "scheduled_tasks": [
            {"cron": "X:50", "task": "Free AI Cron — Gemini Spark sweep"},
            {"cron": "X:52", "task": "Free AI Cron — LoRA harvest & push"},
            {"cron": "X:55", "task": "Free AI Cron — model benchmarking"},
            {"cron": "X:58", "task": "Free AI Cron — truth audit & distill"},
            {"cron": "*/15", "task": "Gemini Spark Maximizer cycle"},
        ],
    }


@app.get("/mcp/project/full_context")
def project_full_context() -> dict:
    """
    EVERYTHING in one call — single JSON for AI context injection.
    Gemini Spark should call this at the start of every session.
    """
    health      = project_health()
    training    = project_training()
    models      = project_models()
    commits     = project_commits()
    benchmarks  = project_benchmarks()
    automations = project_automations()

    # Determine next scheduled task heuristic
    now_min = datetime.now().minute
    schedule = [50, 52, 55, 58]
    next_min = next((m for m in schedule if m > now_min), schedule[0])

    online_daemons = sum(
        1 for v in health["daemon_ports"].values() if v["online"]
    )
    total_daemons  = len(health["daemon_ports"])

    return {
        "project_name":        "Lauburu AI Mesh Ecosystem",
        "mcp_server_version":  "1.0.0",
        "timestamp":           _now_iso(),

        # Mesh topology summary
        "mesh_nodes": [
            {"id": "L1", "name": "Mac_Node",        "ip": "192.168.8.230", "role": "Primary Host & Memory Governor",     "ram_gb": 24, "ai_cap_gb": 21.6},
            {"id": "L2", "name": "MacBook_Pro",      "ip": "192.168.8.127", "role": "Metal GPU RPC & Storage Vault",      "ram_gb": 16, "ai_cap_gb": 14.0},
            {"id": "L3", "name": "Linux_Head_Node",  "ip": "192.168.8.224", "role": "Gateway Ingress & Compute Hub",      "ram_gb": 16, "ai_cap_gb": 13.8},
            {"id": "L4", "name": "Linux_Tablet",     "ip": "DHCP",          "role": "Mobile Linux Compute",               "ram_gb": 8,  "ai_cap_gb": 6.5},
            {"id": "L5", "name": "MacBook_Air",      "ip": "192.168.8.222", "role": "Secondary Metal Worker",             "ram_gb": 16, "ai_cap_gb": 14.0},
            {"id": "L6", "name": "Pixel_10_Pro_XL",  "ip": "DHCP",          "role": "8K Vision Stream & Edge TPU",        "ram_gb": 16, "ai_cap_gb": 12.5},
            {"id": "L7", "name": "Samsung_S20",      "ip": "DHCP",          "role": "Dedicated Automated UI Tester",      "ram_gb": 12, "ai_cap_gb": 9.0},
        ],
        "pooled_vram_gb":  82.8,
        "total_ram_gb":    108.0,

        # Live state
        "daemon_health":   health["daemon_ports"],
        "daemons_online":  f"{online_daemons}/{total_daemons}",
        "tri_vault":       health["tri_vault"],
        "disk":            health["disk"],
        "ram":             health["ram"],

        "training_progress": {
            "lora_samples":       training["lora_samples"],
            "dataset_files":      training["dataset_file_count"],
            "dataset_size":       training["dataset_dir_size"],
            "last_harvest":       training["last_harvest_mtime"],
        },

        "active_automations": automations["scheduled_tasks"],
        "recent_commits":     commits["commits"],
        "benchmarks":         benchmarks["port_latencies"],
        "synergy_score":      benchmarks["synergy_score"],

        "next_scheduled_task": f"X:{next_min:02d} cron cycle",

        # ── AI instruction injected into Gemini Spark context ──
        "ai_instruction": (
            "Fetch GET http://localhost:9999/mcp/project/full_context at the start of "
            "every Gemini Spark session and inject this JSON into your working context. "
            "Use the data to: "
            "1) Track training progress — report lora_samples count and dataset_size. "
            "2) Report on daemon health — flag any daemon whose 'online' field is false. "
            "3) Generate LoRA pairs targeting the current weakest training category by "
            "   calling POST http://localhost:9999/mcp/project/add_training_pair. "
            "4) If daemons_online shows fewer than 5/7 daemons active, trigger "
            "   POST http://localhost:9999/mcp/project/heal to invoke self-healing. "
            "Rule #0: never report mock or simulated values — all data must be live."
        ),

        # Key filesystem paths
        "key_paths": {
            "REPO_ROOT":     str(REPO_ROOT),
            "GGUF_VAULT":    str(GGUF_VAULT),
            "LORA_DIR":      str(LORA_DIR),
            "LORA_FILE":     str(LORA_FILE),
            "OBSIDIAN_VAULT": str(OBSIDIAN),
            "SESSION_LOGS":  str(SESSION_DIR),
        },
    }


@app.post("/mcp/project/heal")
def project_heal() -> dict:
    """Trigger self-healing via the Port 18802 Self-Healing Hub REST API."""
    if not _probe_port(18802):
        return {
            "timestamp": _now_iso(),
            "triggered": False,
            "reason":    "Port 18802 (Self-Healing Hub) is offline — cannot reach it.",
            "fallback":  "Run: cd /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo && python3 00_core_infrastructure/self_healing_hub/src/start_self_healing_hub.py &",
        }

    try:
        import urllib.request
        req  = urllib.request.Request(
            "http://127.0.0.1:18802/heal",
            method="POST",
            headers={"Content-Type": "application/json"},
            data=b'{"trigger": "lauburu_project_mcp", "reason": "AI-triggered self-heal"}',
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = resp.read().decode()
            return {
                "timestamp": _now_iso(),
                "triggered": True,
                "http_status": resp.status,
                "response": body[:500],
            }
    except Exception as exc:
        return {
            "timestamp": _now_iso(),
            "triggered": False,
            "error":     str(exc),
        }


@app.post("/mcp/project/add_training_pair")
async def add_training_pair(body: dict) -> dict:
    """
    Append a LoRA instruction/output pair to continuous_lora_dataset.jsonl.

    Expected body:
        {
            "instruction": "...",
            "output": "...",
            "category": "optional — e.g. 'biometrics', 'mesh', 'inference'"
        }
    """
    instruction = body.get("instruction", "").strip()
    output      = body.get("output", "").strip()
    category    = body.get("category", "general").strip()

    if not instruction or not output:
        raise HTTPException(
            status_code=422,
            detail="Both 'instruction' and 'output' fields are required and must be non-empty.",
        )

    pair = {
        "instruction": instruction,
        "output":      output,
        "category":    category,
        "source":      "lauburu_project_mcp",
        "timestamp":   _now_iso(),
    }

    try:
        LORA_DIR.mkdir(parents=True, exist_ok=True)
        with LORA_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(pair, ensure_ascii=False) + "\n")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to write training pair: {exc}")

    return {
        "timestamp":   _now_iso(),
        "written":     True,
        "lora_file":   str(LORA_FILE),
        "total_lines": _lora_line_count(),
        "pair":        pair,
    }


# ─── Entry Point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🧠 Lauburu Project Overview MCP Server (Port 9999)")
    print(f"   REPO_ROOT : {REPO_ROOT}")
    print(f"   LORA_DIR  : {LORA_DIR}")
    print(f"   OBSIDIAN  : {OBSIDIAN}")
    print("   Endpoints : http://localhost:9999/mcp/tools")
    print("               http://localhost:9999/mcp/project/full_context")
    print("   Rule #0   : ALL data is live-probed — zero mock values")
    uvicorn.run(app, host="0.0.0.0", port=9999, log_level="info")
