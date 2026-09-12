
import shutil
def check_storage_health():
    return (os.path.isdir("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault") and
            os.path.isdir("/Users/aaron/DFS_UNIFIED/lora_datasets") and
            shutil.disk_usage("/Users/aaron").free / (1024**3) >= 5.0)

#!/usr/bin/env python3
"""
01_apps/screen_lens/ai_dev_noter/lauburu_dev_historian.py
=========================================================
Lauburu Project Development Historian & Structuring Synthesizer
--------------------------------------------------------------
Ingests multimodal observations from:
- Layer 1 (Mac Mini M4 Pro): Native Screen Lens (:3035 / SQLite ~/.lauburu/screen_lens.sqlite)
- Layer 5 (MacBook Air M2): Manual AI Task Screen Lens (:3035 / SQLite ~/.lauburu/screen_lens.sqlite)
- Layer 6 (Pixel 10 Pro XL): Android Screen Lens (:3035 / Termux SQLite)
- Git AST working tree diffs and commit states

Synthesizes structured developmental milestones, architectural decisions, and
continuous 24/7 LoRA training datasets into the Tri-Vault architecture:
1. Obsidian Knowledge Core:
   • obsidian_vault/00_CHRONOLOGY/LIVE_DEVELOPMENT_LOG_2026.md (Deduplicated Chronology)
   • obsidian_vault/07_ARCHITECTURE/PROJECT_TAXONOMY_MAP.md (Whole Project Structure)
   • obsidian_vault/07_ARCHITECTURE/ACTIVE_AUTOMATION_PLANS.md (Workflow Optimization Plans)
   • obsidian_vault/04_ANALYTICS/CROSS_DEVICE_LENS_TELEMETRY.md (Tri-Node Lens Dashboard)
2. PySpark Data Lake (04_data_and_memory/lora_datasets/project_development_history.jsonl)
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
OBSIDIAN_DIR = REPO_ROOT / "obsidian_vault"
CHRONOLOGY_FILE = OBSIDIAN_DIR / "00_CHRONOLOGY/LIVE_DEVELOPMENT_LOG_2026.md"
TAXONOMY_FILE = OBSIDIAN_DIR / "07_ARCHITECTURE/PROJECT_TAXONOMY_MAP.md"
AUTOMATION_PLANS_FILE = OBSIDIAN_DIR / "07_ARCHITECTURE/ACTIVE_AUTOMATION_PLANS.md"
TELEMETRY_FILE = OBSIDIAN_DIR / "04_ANALYTICS/CROSS_DEVICE_LENS_TELEMETRY.md"
LORA_DATASET_FILE = REPO_ROOT / "04_data_and_memory/lora_datasets/project_development_history.jsonl"
MAC_DB_PATH = Path(os.path.expanduser("~/.lauburu/screen_lens.sqlite"))
STATE_FILE = Path(os.path.expanduser("~/.lauburu/dev_historian_state.json"))

MONOREPO_SUBSYSTEMS = {
    "00_core_infrastructure": "Core Infrastructure (SeaweedFS, Docker, Tailscale, Self-Healing Hub)",
    "01_apps": "User Applications & Client Ecosystems (Automotive Android Auto, Screen Lens, Zone 2)",
    "02_ai_models_and_inference": "Distributed AI Inference Mesh (llama.cpp RPC, Petals DHT, Exo P2P, prima.cpp)",
    "03_biometrics_and_telemetry": "Biometrics & Sensor DSP (Movesense 512Hz ECG, Pan-Tompkins, PTT BP)",
    "04_data_and_memory": "Data Lake & Knowledge Memory (PySpark Crawlers, 24/7 LoRA Datasets, Qdrant)",
    "05_agents_and_swarms": "Agent Swarms & Tri-Orchestrator Governance (AI Debate Council, Genetic MoE)",
    "06_scripts_and_tooling": "Tooling & Hardware Automation (Universal SSH, ADB Keepalive, WoL Daemon)",
    "07_docs_and_architecture": "Canonical Architecture & RFC Whitepapers",
    "obsidian_vault": "Obsidian Knowledge Vault (Tri-Vault Human & Semantic Core)"
}


def load_state() -> Dict[str, Any]:
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"last_mac_id": 0, "last_macbook_air_id": 0, "last_pixel_id": 0, "total_syntheses": 0, "last_sig": ""}


def save_state(state: Dict[str, Any]):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def fetch_mac_lens_context(last_id: int = 0, limit: int = 20) -> List[Dict[str, Any]]:
    items = []
    if not MAC_DB_PATH.exists():
        return items

    try:
        conn = sqlite3.connect(MAC_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, timestamp, active_app_name, active_window_title, raw_text_summary, ocr_duration_ms
            FROM captures
            WHERE id > ?
            ORDER BY id ASC
            LIMIT ?
        """, (last_id, limit))
        rows = cursor.fetchall()
        conn.close()

        for r in rows:
            items.append({
                "source": "Mac_Mini_M4_Pro (L1)",
                "id": r[0],
                "timestamp": r[1],
                "app": r[2] or "Unknown",
                "window": r[3] or "Unknown",
                "text": (r[4] or "").strip(),
                "duration_ms": r[5]
            })
    except Exception as e:
        print(f"Error querying Mac Lens SQLite: {e}")
    return items


def fetch_macbook_air_lens_context(last_id: int = 0, limit: int = 20) -> List[Dict[str, Any]]:
    items = []
    try:
        cmd = [
            "ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=2", "macbook-air",
            f"python3 -c \"import sqlite3, json, os; "
            f"db=os.path.expanduser('~/.lauburu/screen_lens.sqlite'); "
            f"conn=sqlite3.connect(db) if os.path.exists(db) else None; "
            f"rows=conn.cursor().execute('SELECT id, timestamp, active_app_name, active_window_title, raw_text_summary, ocr_duration_ms FROM captures WHERE id > {last_id} ORDER BY id ASC LIMIT {limit}').fetchall() if conn else []; "
            f"print(json.dumps(rows))\""
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=4.0)
        if res.returncode == 0 and res.stdout.strip():
            raw_rows = json.loads(res.stdout.strip())
            for r in raw_rows:
                items.append({
                    "source": "MacBook_Air_M2 (L5)",
                    "id": r[0],
                    "timestamp": r[1],
                    "app": r[2] or "Unknown",
                    "window": r[3] or "Unknown",
                    "text": (r[4] or "").strip(),
                    "duration_ms": r[5]
                })
    except Exception:
        pass
    return items


def fetch_pixel_lens_context(last_id: int = 0, limit: int = 20) -> List[Dict[str, Any]]:
    items = []
    try:
        cmd = [
            "ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=2", "pixel",
            f"python3 -c \"import sqlite3, json, os; "
            f"db=os.path.expanduser('~/.lauburu/screen_lens.sqlite'); "
            f"conn=sqlite3.connect(db) if os.path.exists(db) else None; "
            f"rows=conn.cursor().execute('SELECT id, timestamp, app_name, app_package, ocr_text, ocr_latency_ms FROM frames WHERE id > {last_id} ORDER BY id ASC LIMIT {limit}').fetchall() if conn else []; "
            f"print(json.dumps(rows))\""
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=4.0)
        if res.returncode == 0 and res.stdout.strip():
            raw_rows = json.loads(res.stdout.strip())
            for r in raw_rows:
                items.append({
                    "source": "Pixel_10_Pro_XL (L6)",
                    "id": r[0],
                    "timestamp": r[1],
                    "app": r[2] or "Android",
                    "window": r[3] or "com.android",
                    "text": (r[4] or "").strip(),
                    "duration_ms": r[5]
                })
    except Exception:
        pass
    return items


def fetch_git_diff_context() -> Dict[str, Any]:
    try:
        status = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "status", "--short"],
            capture_output=True, text=True, timeout=3.0
        ).stdout.strip()

        log = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "log", "-n", "3", "--oneline"],
            capture_output=True, text=True, timeout=3.0
        ).stdout.strip()

        return {
            "changed_files": [l for l in status.splitlines() if l][:15],
            "recent_commits": [l for l in log.splitlines() if l]
        }
    except Exception:
        return {"changed_files": [], "recent_commits": []}


def update_project_taxonomy_map():
    """Generates and updates the canonical Monorepo Project Taxonomy Map in Obsidian."""
    TAXONOMY_FILE.parent.mkdir(parents=True, exist_ok=True)
    now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    lines = [
        "---",
        "title: \"Lauburu Monorepo - Hierarchical Project Taxonomy Map\"",
        "tags: [lauburu, taxonomy, architecture, subsystems, dev_historian]",
        f"updated: \"{now_str}\"",
        "canonical_source: true",
        "---",
        "",
        "# 🗺️ Lauburu Monorepo — Canonical Project Taxonomy Map",
        f"> Continuously updated by `lauburu-dev-historian` on {now_str}.",
        "",
        "- [[Index]]",
        "- [[CANONICAL_PROJECT_AND_STORAGE_RULE]]",
        "- [[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]",
        "",
        "---",
        "",
        "## 🏛️ Subsystem Hierarchy & Core Modules",
        ""
    ]

    for dir_name, desc in MONOREPO_SUBSYSTEMS.items():
        dir_path = REPO_ROOT / dir_name
        file_count = len(list(dir_path.rglob("*"))) if dir_path.exists() else 0
        lines.append(f"### 📦 `{dir_name}/`")
        lines.append(f"- **Description**: {desc}")
        lines.append(f"- **Total Indexed Files**: {file_count}")
        lines.append("")

    lines.append("---")
    lines.append("## 🌐 Active Compute Nodes & Sharding Roles")
    lines.append("- **L1 Mac Mini M4 Pro**: Host Controller, Memory Governor, Screen Lens Host (:3035)")
    lines.append("- **L2 MacBook Pro M1 Max**: Metal GPU RPC Shard (:8081), 285 GB Model Vault")
    lines.append("- **L3 Linux Head Node**: Gateway Ingress, Docker Engine, Ray Cluster (:8082)")
    lines.append("- **L5 MacBook Air M2**: Manual AI Task Worker, Active Screen Lens (:3035)")
    lines.append("- **L6 Pixel 10 Pro XL**: Android Auto In-Car Voice Coding Host, 24/7 Mobile Screen Lens (:3035)")
    lines.append("- **L7 Samsung Galaxy S20+**: Automated UI Testing & ADB Target (:5555)")
    lines.append("")

    with open(TAXONOMY_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def update_active_automation_plans(detected_actions: List[str], active_apps: Set[str]):
    """Synthesizes active optimization and automation proposals based on observed workflows."""
    AUTOMATION_PLANS_FILE.parent.mkdir(parents=True, exist_ok=True)
    now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    lines = [
        "---",
        "title: \"Lauburu AI - Active Workflow Optimization & Automation Plans\"",
        "tags: [lauburu, automation, workflow_optimization, dev_historian]",
        f"updated: \"{now_str}\"",
        "canonical_source: true",
        "---",
        "",
        "# ⚡ Active Workflow Optimization & Automation Plans",
        f"> Synthesized from multimodal Screen Lens & Git activity on {now_str}.",
        "",
        "- [[Index]]",
        "- [[PROJECT_TAXONOMY_MAP]]",
        "- [[LIVE_DEVELOPMENT_LOG_2026]]",
        "",
        "---",
        "",
        "## 🎯 Current Workflow Context",
        f"- **Active Applications Observed**: {', '.join(f'`{a}`' for a in sorted(active_apps)) if active_apps else 'IDLE'}",
        ""
    ]

    lines.append("## 💡 Automated Optimization Proposals")
    lines.append("1. **MacBook Air Manual AI Task Offload**:")
    lines.append("   • *Proposal*: Route manual interactive prompts and UI prototyping directly to MacBook Air M2 Metal shaders.")
    lines.append("   • *Target Module*: `01_apps/screen_lens` & `02_ai_models_and_inference/lauburu_tui`.")
    lines.append("")
    lines.append("2. **Android Auto Voice Coding Streaming Mode**:")
    lines.append("   • *Proposal*: Direct 16kHz PCM audio streaming over Tailscale WebSocket (Port 8765) when driving.")
    lines.append("   • *Target Module*: `01_apps/automotive/android_auto_voice_coder` & `voice_bridge_daemon.py`.")
    lines.append("")
    lines.append("3. **Ephemeral Frame Compression & Hardware Acceleration**:")
    lines.append("   • *Proposal*: Retain 0 disk image frames on Pixel 10 Pro XL, MacBook Air, and Mac Mini by executing OCR in RAM.")
    lines.append("   • *Target Module*: `01_apps/screen_lens/android/lauburu_lens_android.py` & native ScreenCaptureKit.")
    lines.append("")

    with open(AUTOMATION_PLANS_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def update_cross_device_telemetry():
    """Updates the Tri-Node Screen Lens Telemetry Dashboard in Obsidian."""
    TELEMETRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    mac_count = 0
    if MAC_DB_PATH.exists():
        try:
            conn = sqlite3.connect(MAC_DB_PATH)
            mac_count = conn.cursor().execute("SELECT COUNT(*) FROM captures").fetchone()[0]
            conn.close()
        except Exception:
            pass

    content = f"""---
title: "Cross-Device Screen Lens Telemetry"
tags: [telemetry, screen_lens, tri_device, mac_mini, macbook_air, pixel_10]
updated: "{datetime.datetime.now(datetime.timezone.utc).isoformat()}"
canonical_source: true
---
# 📊 Cross-Device Screen Lens Telemetry & Live Tracker

| Dimension | Mac Mini M4 Pro (L1) | MacBook Air M2 (L5) | Pixel 10 Pro XL (L6) |
| :--- | :--- | :--- | :--- |
| **Role** | Primary Host & Governor | Manual AI Task Worker | In-Car Voice & Mobile Edge |
| **Daemon Status** | 🟢 Active Background | 🟢 Active Background | 🟢 Active Termux Daemon |
| **Port** | `:3035` | `:3035` | `:3035` |
| **Capture Engine** | `ScreenCaptureKit` + Apple Vision | `ScreenCaptureKit` + Apple Vision | Android Screencap + Tesseract |
| **Storage Mode** | Ephemeral (0 Disk PNGs) | Ephemeral (0 Disk PNGs) | Ephemeral (0 Disk PNGs) |
| **Total Frames** | `{mac_count}` | Active Rolling SQLite | Active Rolling SQLite |
| **AI Historian** | Ingesting 24/7 | Ingesting 24/7 | Ingesting 24/7 |

*Last Synced*: `{datetime.datetime.now(datetime.timezone.utc).isoformat()}`
"""
    with open(TELEMETRY_FILE, "w", encoding="utf-8") as f:
        f.write(content)


def synthesize_development_insights(mac_items: List[Dict[str, Any]], mba_items: List[Dict[str, Any]], pixel_items: List[Dict[str, Any]], git_info: Dict[str, Any]) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    now = datetime.datetime.now(datetime.timezone.utc)
    timestamp_header = now.strftime("%Y-%m-%d %H:%M:%S UTC")

    detected_subsystems = set()
    code_actions = []
    test_verifications = []
    device_activities = []
    active_apps = set()
    all_texts = []

    for item in mac_items:
        app = item.get("app", "")
        window = item.get("window", "")
        text = item.get("text", "")
        if app:
            active_apps.add(f"MacMini:{app}")
        all_texts.append(f"[{item['source']}|{app}|{window}]: {text[:150]}")

        if "automotive" in window or "voice_coder" in text:
            detected_subsystems.add("`01_apps/automotive` (Android Auto Voice Coding & STT/TTS)")
        if "screen_lens" in text or "lauburu_lens" in window:
            detected_subsystems.add("`01_apps/screen_lens` (Activity-Driven Tri-Device Screen Lens)")
        if "lauburu_tui" in window or "lauburu_tui" in text:
            detected_subsystems.add("`02_ai_models_and_inference/lauburu_tui` (Rust Ratatui Multi-Pane TUI)")
        if "passed" in text.lower() or "100% ok" in text.lower() or "success" in text.lower():
            test_verifications.append(f"Verified execution on Mac Mini in {app} ({window[:40]})")

    for item in mba_items:
        app = item.get("app", "")
        window = item.get("window", "")
        text = item.get("text", "")
        if app:
            active_apps.add(f"MacBookAir:{app}")
        all_texts.append(f"[{item['source']}|{app}|{window}]: {text[:150]}")
        detected_subsystems.add("`01_apps/screen_lens` (MacBook Air Manual AI Task Observation)")
        device_activities.append(f"MacBook Air active in `{app}` ({window[:40]})")

    for item in pixel_items:
        app = item.get("app", "Android")
        active_apps.add(f"Pixel:{app}")
        detected_subsystems.add("`01_apps/screen_lens/android` (Pixel 10 Pro XL Mobile Daemon)")
        device_activities.append(f"Pixel active in `{app}` (`{item.get('window', '')}`)")

    for chg in git_info.get("changed_files", []):
        if "automotive" in chg or "voice_coder" in chg:
            detected_subsystems.add("`01_apps/automotive`")
        elif "screen_lens" in chg:
            detected_subsystems.add("`01_apps/screen_lens`")
        elif "lauburu_tui" in chg:
            detected_subsystems.add("`02_ai_models_and_inference/lauburu_tui`")
        code_actions.append(f"Working tree mutation: `{chg}`")

    if not detected_subsystems:
        detected_subsystems.add("`01_apps/screen_lens` (Continuous Multi-Device Observation & Ingestion)")

    # Build structured deduplicated log entry
    log_entry = [
        f"### ⏱️ Session Milestone: {timestamp_header}\n",
        "- **Active Hardware Targets**: Mac Mini M4 Pro (L1), MacBook Air M2 (L5), Pixel 10 Pro XL (L6)",
        "- **Subsystems Modified / Tracked**:"
    ]
    for sub in sorted(detected_subsystems):
        log_entry.append(f"  • {sub}")

    if code_actions:
        log_entry.append("- **Key Code & Repository Diffs**:")
        for act in code_actions[:8]:
            log_entry.append(f"  • {act}")

    if test_verifications:
        log_entry.append("- **Empirical Verifications**:")
        for ver in test_verifications[:4]:
            log_entry.append(f"  • ✅ {ver}")

    if device_activities:
        log_entry.append("- **Cross-Node Remote Telemetry**:")
        for da in device_activities[:4]:
            log_entry.append(f"  • 💻/📱 {da}")

    log_entry.append("\n---\n")
    structured_md = "\n".join(log_entry)

    # Generate LoRA training sample
    training_sample = {
        "timestamp": timestamp_header,
        "input_context": {
            "mac_observations": len(mac_items),
            "mba_observations": len(mba_items),
            "pixel_observations": len(pixel_items),
            "git_changed_files": len(git_info.get("changed_files", [])),
            "active_apps": list(active_apps),
            "raw_snippets": all_texts[:4]
        },
        "target_structured_notes": structured_md,
        "subsystems": list(detected_subsystems)
    }

    # Update dynamic project taxonomy, automation plans, and telemetry
    update_project_taxonomy_map()
    update_active_automation_plans(code_actions, active_apps)
    update_cross_device_telemetry()

    return structured_md, training_sample


def append_to_obsidian(structured_md: str):
    CHRONOLOGY_FILE.parent.mkdir(parents=True, exist_ok=True)

    if not CHRONOLOGY_FILE.exists():
        header = (
            "---\ntitle: \"Lauburu Monorepo - Live Continuous Development Log\"\n"
            "tags: [lauburu, chronology, development, tri_device_lens, live_notes]\n---\n"
            "# 📜 Lauburu AI Monorepo — Continuous Development Log (2026)\n"
            "> Automatically synthesized by `lauburu-dev-historian` from Mac Mini, MacBook Air & Pixel Screen Lens streams.\n\n"
            "- [[Index]]\n- [[CANONICAL_PROJECT_AND_STORAGE_RULE]]\n- [[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]\n"
            "- [[PROJECT_TAXONOMY_MAP]]\n- [[ACTIVE_AUTOMATION_PLANS]]\n\n---\n\n"
        )
        with open(CHRONOLOGY_FILE, "w", encoding="utf-8") as f:
            f.write(header)

    with open(CHRONOLOGY_FILE, "r", encoding="utf-8") as f:
        existing_content = f.read()

    if "\n---\n\n" in existing_content:
        parts = existing_content.split("\n---\n\n", 1)
        new_content = parts[0] + "\n---\n\n" + structured_md + parts[1]
    else:
        new_content = existing_content + "\n" + structured_md

    with open(CHRONOLOGY_FILE, "w", encoding="utf-8") as f:
        f.write(new_content)


def append_to_lora_dataset(training_sample: Dict[str, Any]):
    LORA_DATASET_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LORA_DATASET_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(training_sample) + "\n")


def execute_cycle(verbose: bool = False):
    state = load_state()
    mac_items = fetch_mac_lens_context(last_id=state.get("last_mac_id", 0), limit=20)
    mba_items = fetch_macbook_air_lens_context(last_id=state.get("last_macbook_air_id", 0), limit=20)
    pixel_items = fetch_pixel_lens_context(last_id=state.get("last_pixel_id", 0), limit=20)
    git_info = fetch_git_diff_context()

    if not mac_items and not mba_items and not pixel_items and not git_info.get("changed_files"):
        if verbose:
            print("ℹ️ No new developmental changes detected across all 3 nodes.")
        return

    content_sig = f"{len(mac_items)}:{len(mba_items)}:{len(pixel_items)}:{','.join(git_info.get('changed_files', []))}"
    if state.get("last_sig") == content_sig and not mac_items and not mba_items and not pixel_items:
        return

    structured_md, training_sample = synthesize_development_insights(mac_items, mba_items, pixel_items, git_info)
    if structured_md and training_sample:
        append_to_obsidian(structured_md)
        append_to_lora_dataset(training_sample)

    if mac_items:
        state["last_mac_id"] = max(item["id"] for item in mac_items)
    if mba_items:
        state["last_macbook_air_id"] = max(item["id"] for item in mba_items)
    if pixel_items:
        state["last_pixel_id"] = max(item["id"] for item in pixel_items)
    state["total_syntheses"] = state.get("total_syntheses", 0) + 1
    state["last_sig"] = content_sig
    save_state(state)

    if verbose:
        print("✅ Successfully synthesized tri-node developmental milestones and synced to Obsidian & LoRA datasets.")


def main():
    parser = argparse.ArgumentParser(description="Lauburu Tri-Node Project Development Historian")
    parser.add_argument("--once", action="store_true", help="Run single synthesis cycle and exit")
    parser.add_argument("--daemon", action="store_true", help="Run continuously in background loop")
    parser.add_argument("--interval", type=float, default=15.0, help="Cycle interval in seconds")
    args = parser.parse_args()

    if args.once or not args.daemon:
        execute_cycle(verbose=True)
    else:
        print(f"🚀 Starting Lauburu Tri-Node Project Development Historian (Interval: {args.interval}s)...")
        while True:
            try:
                execute_cycle(verbose=False)
            except Exception as e:
                print(f"Historian cycle error: {e}")
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
