#!/usr/bin/env python3
"""
NotebookLM & Gemini Spark Knowledge Compiler
=============================================
Subsystem: 04_data_and_memory/
Compiles high-fidelity, structured multi-source Markdown bundles from the monorepo,
Obsidian Vault, and live telemetry, staging them for zero-click Google NotebookLM
and Gemini Spark knowledge ingestion.
"""

import argparse
import datetime
import json
import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
OUTPUT_DIR = REPO_ROOT / "04_data_and_memory" / "notebooklm_sources"
GDRIVE_SYNC_DIR = Path("/Volumes/Google Drive/My Drive/Lauburu_AI_Memory/notebooklm_sync")
SCREEN_LENS_DB = Path(os.path.expanduser("~/.lauburu/screen_lens.sqlite"))


class NotebookLMKnowledgeCompiler:
    """Compiles canonical monorepo knowledge into specialized NotebookLM source documents."""

    def __init__(self, output_dir: Path = OUTPUT_DIR, gdrive_dir: Path = GDRIVE_SYNC_DIR):
        self.output_dir = output_dir
        self.gdrive_dir = gdrive_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _read_file_safe(self, rel_path: str, max_chars: int = 15000) -> str:
        fpath = REPO_ROOT / rel_path
        if fpath.exists():
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read().strip()
                    if len(content) > max_chars:
                        return content[:max_chars] + f"\n\n... [Truncated for NotebookLM source limits from {len(content)} chars]"
                    return content
            except Exception as e:
                return f"[Error reading {rel_path}: {e}]"
        return f"[File {rel_path} not found]"

    def _get_live_screen_lens_summary(self) -> str:
        if not SCREEN_LENS_DB.exists():
            return "No local Screen Lens captures recorded."
        try:
            conn = sqlite3.connect(f"file:{SCREEN_LENS_DB}?mode=ro", uri=True)
            c = conn.cursor()
            c.execute("SELECT id, timestamp FROM captures ORDER BY id DESC LIMIT 1")
            row_max = c.fetchone()
            count, last_ts = (row_max[0], row_max[1]) if row_max else (0, "N/A")
            c.execute("""
                SELECT active_app_name, active_window_title, substr(raw_text_summary, 1, 150), timestamp
                FROM captures ORDER BY id DESC LIMIT 5
            """)
            recent_rows = c.fetchall()
            conn.close()

            lines = [f"Total Indexed Captures: {count} | Latest Timestamp: {last_ts}"]
            for r in recent_rows:
                lines.append(f"- [{r[3]}] App: `{r[0]}` | Window: \"{r[1]}\" | Summary: {r[2]}...")
            return "\n".join(lines)
        except Exception as e:
            return f"[Screen Lens DB Read Error: {e}]"

    def compile_bundle_01_master_architecture(self) -> Path:
        """Bundle 1: Master System Architecture & Tri-Vault Storage Protocol."""
        target = self.output_dir / "01_lauburu_master_architecture.md"
        rule_content = self._read_file_safe("obsidian_vault/CANONICAL_PROJECT_AND_STORAGE_RULE.md")
        root_readme = self._read_file_safe("README.md")

        content = f"""# 🏛️ Source 1: Lauburu Master Architecture & Tri-Vault Storage Protocol
*Generated for Google NotebookLM & Gemini Spark | Monorepo Canonical Source*
*Compilation Timestamp: {datetime.datetime.now(datetime.timezone.utc).isoformat()}*

---

## 1. Executive Summary & Core Rules
- **Rule #0 (Zero-Mock Data):** Strictly no fake arrays, simulated metrics, or dummy placeholders. All telemetry originates from live BLE hardware, authentic log replays, or shows clean waiting states (`--`).
- **Rule 6.3 (Storage Invariant):** Agents verify Tri-Vault storage layers are HEALTHY and ensure host NVMe maintains >= 5.0 GB free disk headroom.
- **$0 Cloud Spend Goal:** Prioritize local quantized models on Apple Silicon Metal and AMD ROCm over cloud APIs.

---

## 2. Canonical Tri-Vault Storage Specification
{rule_content}

---

## 3. Monorepo Root Overview
{root_readme}
"""
        with open(target, "w", encoding="utf-8") as f:
            f.write(content)
        return target

    def compile_bundle_02_mesh_hardware_and_networking(self) -> Path:
        """Bundle 2: 7-Layer Mesh Network Topology & Dynamic RAM Governance."""
        target = self.output_dir / "02_mesh_hardware_and_networking.md"
        infra_readme = self._read_file_safe("00_core_infrastructure/README.md")

        content = f"""# 🌐 Source 2: 8-Node Hardware Mesh Network Topology & Dynamic RAM Governance
*Generated for Google NotebookLM & Gemini Spark | Monorepo Canonical Source*
*Compilation Timestamp: {datetime.datetime.now(datetime.timezone.utc).isoformat()}*

---

## 1. Hardware Matrix (139.0 GB RAM / 108.4 GB Usable AI VRAM Pool)

| Layer | Node Name | Network Role | Local IP | Tailscale IP | Dynamic RAM Ceiling | Hardware & Capabilities |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **L1** | `Mac_Node` | Primary Host & Memory Governor | `192.168.8.230` | `100.119.199.76` | **80%** (19.2 GB AI) | Apple M4 Pro Mac Mini. Primary controller, memory governor (>=4.8 GB free buffer). |
| **L2** | `MacBook_Pro` | Model Vault & Automation Target | `192.168.8.127` | `100.103.212.21` | **90%** (14.0 GB AI) | Intel Core i7-9750H, 16 GB, LAN Wi-Fi 5 (~6.5ms RTT, unlinked TB), 285 GB SSD vault. |
| **L8** | `Linux_Mini_lauburu` | 40Gbps TB4 DMA Bridge & Sharded GGUF | TB `10.0.0.8` | `100.121.247.8` | **80%** (25.6 GB AI) | Intel Core i7-8700B, 32 GB RAM, 40Gbps TB4 DMA bridge (0.38ms RTT), Ubuntu 24.04. |
| **L3** | `Linux_Head_Node` | Gateway Ingress & Compute Hub | `192.168.8.225` | `100.101.39.98` | **80%** (12.0 GB AI) | AMD Ryzen 7 5700U, 15 GB RAM, Docker Engine, Ray Head, BT paired (-28 dBm). |
| **L4** | `Linux_Tablet` | Mobile Compute & Touch DSP | `192.168.8.116` | `100.80.64.5` | **75%** (6.0 GB AI) | Debian Linux Tablet, Port 2 Router wired link, lightweight biometrics telemetry. |
| **L5** | `MacBook_Air` | Metal LoRA Distillation & Worker | `192.168.8.248` | `100.121.202.34` | **90%** (14.0 GB AI) | Apple M4 MacBook Air, Metal Performance Shaders, LoRA fine-tuning & distillation. |
| **L6** | `Pixel_10_Pro_XL` | 8K Vision Stream & Edge TPU | `192.168.8.213` | `100.114.215.68` | **85%** (13.6 GB AI) | Google Tensor G5, Edge TPU, 8K Digital PTZ, Termux SSH :8022. |
| **L7** | `Samsung_S20` | Dedicated Automated UI Tester | `192.168.8.157` | `100.84.40.95` | **75%** (9.0 GB AI) | Samsung Exynos 990, 12 GB RAM, Termux UI Tester & ADB target. |
| **GW** | `GL-BE14000` | Core Gateway & 2.5G NBN WAN | `192.168.8.1` | `100.70.123.123` | Embedded (2.0 GB) | GL-BE14000 Core Gateway, 2.5G NBN WAN on eth2, USB ADB bridge. |

---

## 2. Core Infrastructure Subsystem
{infra_readme}
"""
        with open(target, "w", encoding="utf-8") as f:
            f.write(content)
        return target

    def compile_bundle_03_local_inference_and_models(self) -> Path:
        """Bundle 3: Canonical Local Inference Hierarchy, Pinned Models & /ai-debate."""
        target = self.output_dir / "03_local_inference_and_models.md"
        ai_readme = self._read_file_safe("02_ai_models_and_inference/README.md")
        debate_skill = self._read_file_safe("../.gemini/config/skills/ai-debate/SKILL.md")

        content = f"""# 🧠 Source 3: Local Inference Hierarchy, Pinned Models & AI Debate Protocol
*Generated for Google NotebookLM & Gemini Spark | Monorepo Canonical Source*
*Compilation Timestamp: {datetime.datetime.now(datetime.timezone.utc).isoformat()}*

---

## 1. Local Inference Engine Hierarchy
1. **PRIMARY MASTER: `prima.cpp` (Port :8082):** Canonical primary master across all devices containing model weights over 10Gbps TB4 DMA Bridge.
2. **RESILIENT FALLBACK: `llama.cpp` (Port :8083):** Strictly used as automatic fallback ONLY if an edge device lacks local weights.
3. **MASTER LOCAL ORCHESTRATOR:** `Qwen 3.8 Max 27B` (Port :8081).
4. **PINNED DEVIL'S ADVOCATE:** `Qwen 3.8 Max 27B Abliterated` (`Huihui-Qwen3.8-27B-abliterated-UD-Q4_K_XL.gguf`, 16.0 GB on Port :8083).
5. **ROUTER EDGE SLM:** `SmolLM2-135M` / `SmolLM2-360M` on GL.iNet OpenWrt (<= 300 MB container budget).

---

## 2. AI Inference Mesh Specifications
{ai_readme}

---

## 3. Tri-Orchestrator AI Debate Consensus Engine
{debate_skill}
"""
        with open(target, "w", encoding="utf-8") as f:
            f.write(content)
        return target

    def compile_bundle_04_multimodal_screen_lens(self) -> Path:
        """Bundle 4: Sovereign Screen Lens Multimodal Perception & Development Historian."""
        target = self.output_dir / "04_multimodal_screen_lens_and_actions.md"
        lens_readme = self._read_file_safe("01_apps/screen_lens/README.md")
        lens_telemetry = self._get_live_screen_lens_summary()

        content = f"""# 👁️ Source 4: Sovereign Screen Lens Perception & Autonomous AI Historian
*Generated for Google NotebookLM & Gemini Spark | Monorepo Canonical Source*
*Compilation Timestamp: {datetime.datetime.now(datetime.timezone.utc).isoformat()}*

---

## 1. Subsystem Architecture
- **macOS Host Lens (Port :3035):** Swift 6 standalone binary leveraging Apple `ScreenCaptureKit` and Apple Vision Neural Engine (ANE) OCR (~187ms).
- **Mobile Edge Lens (Port :3035 / :3036):** Pixel 10 Pro XL Tesseract 5.5.2 LSTM OCR inside Termux.
- **Autonomous AI Historian (`lauburu-dev-historian`):** 24/7 background development synthesis logging to `LIVE_DEVELOPMENT_LOG_2026.md` and streaming DPO pairs.
- **Hermes 3 Code-as-Action & OpenClaw:** Ingests OCR bounding boxes and dispatches privileged Shizuku Binder gestures on Android.

---

## 2. Live Screen Lens Database Telemetry
```text
{lens_telemetry}
```

---

## 3. Canonical Subsystem Documentation
{lens_readme}
"""
        with open(target, "w", encoding="utf-8") as f:
            f.write(content)
        return target

    def compile_bundle_05_codeclash_and_lora(self) -> Path:
        """Bundle 5: CodeClash SWE Arena, ELO Leaderboard & 24/7 LoRA Distillation."""
        target = self.output_dir / "05_codeclash_swarm_and_lora_training.md"
        codeclash_readme = self._read_file_safe("05_agents_and_swarms/codeclash_swarm/README.md")
        chronology = self._read_file_safe("obsidian_vault/00_CHRONOLOGY/LIVE_DEVELOPMENT_LOG_2026.md", max_chars=8000)

        content = f"""# ⚔️ Source 5: CodeClash SWE Arena & 24/7 LoRA Distillation Engine
*Generated for Google NotebookLM & Gemini Spark | Monorepo Canonical Source*
*Compilation Timestamp: {datetime.datetime.now(datetime.timezone.utc).isoformat()}*

---

## 1. CodeClash SWE Competition & AST Decompiler
{codeclash_readme}

---

## 2. Continuous Development Milestones & DPO Training Logs
{chronology}
"""
        with open(target, "w", encoding="utf-8") as f:
            f.write(content)
        return target

    def compile_all(self) -> List[Path]:
        """Compiles all 5 source bundles and returns their paths."""
        bundles = [
            self.compile_bundle_01_master_architecture(),
            self.compile_bundle_02_mesh_hardware_and_networking(),
            self.compile_bundle_03_local_inference_and_models(),
            self.compile_bundle_04_multimodal_screen_lens(),
            self.compile_bundle_05_codeclash_and_lora(),
        ]
        return bundles

    def sync_to_google_drive(self) -> bool:
        """Synchronizes compiled bundles to Google Drive for zero-click NotebookLM auto-sync."""
        bundles = self.compile_all()
        try:
            if self.gdrive_dir.parent.exists():
                self.gdrive_dir.mkdir(parents=True, exist_ok=True)
                for b in bundles:
                    shutil.copy2(b, self.gdrive_dir / b.name)
                print(f"✅ Successfully synced {len(bundles)} bundles to Google Drive: {self.gdrive_dir}")
                return True
            else:
                print(f"⚠️ Google Drive mount not found at {self.gdrive_dir.parent}. Bundles staged locally at {self.output_dir}.")
                return False
        except Exception as e:
            print(f"⚠️ Google Drive sync skipped: {e}")
            return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NotebookLM & Gemini Spark Knowledge Compiler")
    parser.add_argument("--sync-gdrive", action="store_true", help="Sync compiled bundles to Google Drive")
    args = parser.parse_args()

    compiler = NotebookLMKnowledgeCompiler()
    if args.sync_gdrive:
        compiler.sync_to_google_drive()
    else:
        compiled = compiler.compile_all()
        print(f"✅ Successfully compiled {len(compiled)} NotebookLM source bundles in {compiler.output_dir}:")
        for c in compiled:
            print(f"  • {c.name} ({c.stat().st_size / 1024:.1f} KB)")
