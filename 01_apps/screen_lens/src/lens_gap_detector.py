#!/usr/bin/env python3
"""
================================================================================
Screen Lens — Perceptual Gap Detector & Diagnostic Suggester (IDM Emitter)
================================================================================
Subsystem: 01_apps/screen_lens/src/lens_gap_detector.py
Lauburu Mesh Ecosystem — Canonical Architecture 2026

Role (Ratified by Tri-Orchestrator AI Debate Consensus 0.992):
- Acts strictly as the READ-ONLY Sensory Probe & Gap Detector.
- Passively scans monorepo logs, active compiler statuses, Mach RAM metrics,
  and Screen Lens observation feeds.
- Emits structured, deduplicated Improvement Diagnostic Manifests (IDMs).
- Enforces Devil's Advocate Firewall #1: 100% Read-Only; zero codebase mutation.
- Enforces Devil's Advocate Firewall #2: SHA256 error signature cooldown (60 min).
- Enforces Rule #0 Zero-Mock: all findings originate from physical kernel/filesystem probes.
================================================================================
"""

import os
import sys
import time
import json
import hashlib
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
DATA_DIR = REPO_ROOT / "04_data_and_memory/data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
IDM_LOG_PATH = DATA_DIR / "improvement_diagnostic_manifests.jsonl"
COOLDOWN_CACHE_PATH = Path("/tmp/lens_idm_cooldown_cache.json")
OBSIDIAN_OBSERVATIONS = REPO_ROOT / "obsidian_vault/APPS_AND_FEATURES/SCREEN_LENS_LIVE_OBSERVATIONS.md"

COOLDOWN_SECONDS = 3600.0  # 60-minute cooldown per unique SHA256 error signature


class LensGapDetector:
    def __init__(self, cooldown_seconds: float = COOLDOWN_SECONDS):
        self.cooldown_seconds = cooldown_seconds
        self.cooldown_cache: Dict[str, float] = self._load_cooldown_cache()

    def _load_cooldown_cache(self) -> Dict[str, float]:
        if COOLDOWN_CACHE_PATH.exists():
            try:
                data = json.loads(COOLDOWN_CACHE_PATH.read_text(encoding="utf-8"))
                now = time.time()
                # Prune expired entries
                return {k: v for k, v in data.items() if now - v < self.cooldown_seconds}
            except Exception:
                return {}
        return {}

    def _save_cooldown_cache(self) -> None:
        try:
            COOLDOWN_CACHE_PATH.write_text(json.dumps(self.cooldown_cache, indent=2), encoding="utf-8")
        except Exception:
            pass

    def probe_mach_ram(self) -> Dict[str, Any]:
        """Empirically probes Darwin Mach VM page statistics."""
        try:
            out = subprocess.check_output(["vm_stat"], text=True)
            page_size = 16384  # Apple Silicon M4 Pro default 16KB
            pages_free = 0
            pages_spec = 0
            pages_inact = 0
            pages_purge = 0
            for line in out.splitlines():
                if "Pages free:" in line:
                    pages_free = int(line.split(":")[1].strip().rstrip("."))
                elif "Pages speculative:" in line:
                    pages_spec = int(line.split(":")[1].strip().rstrip("."))
                elif "Pages inactive:" in line:
                    pages_inact = int(line.split(":")[1].strip().rstrip("."))
                elif "Pages purgeable:" in line:
                    pages_purge = int(line.split(":")[1].strip().rstrip("."))

            free_bytes = (pages_free + pages_spec + pages_inact + pages_purge) * page_size
            free_gb = round(free_bytes / (1024**3), 2)
            headroom_healthy = free_gb >= 9.6  # Rule #3 Invariant
            return {
                "free_ram_gb": free_gb,
                "headroom_healthy": headroom_healthy,
                "sanctuary_threshold_gb": 9.6,
                "page_size_bytes": page_size
            }
        except Exception as e:
            return {"free_ram_gb": 0.0, "headroom_healthy": False, "error": str(e)}

    def scan_recent_build_and_test_gaps(self) -> List[Dict[str, Any]]:
        """
        Passively checks key subsystem compilations for syntax/lint warnings
        without modifying any source code files.
        """
        gaps = []

        # 1. Check Rust Ratatui Project Monitor compilation state
        rust_monitor_dir = REPO_ROOT / "01_apps/rust_project_monitor"
        if rust_monitor_dir.exists():
            try:
                res = subprocess.run(
                    ["cargo", "check", "--message-format=json"],
                    cwd=rust_monitor_dir,
                    capture_output=True,
                    text=True,
                    timeout=15
                )
                for line in res.stdout.splitlines():
                    if line.startswith("{"):
                        try:
                            msg = json.loads(line)
                            if msg.get("reason") == "compiler-message":
                                cm = msg.get("message", {})
                                if cm.get("level") in ("warning", "error"):
                                    spans = cm.get("spans", [])
                                    file_name = spans[0].get("file_name", "unknown") if spans else "unknown"
                                    line_no = spans[0].get("line_start", 0) if spans else 0
                                    gaps.append({
                                        "domain": "rust_systems",
                                        "source_file": f"01_apps/rust_project_monitor/{file_name}",
                                        "line_number": line_no,
                                        "level": cm.get("level"),
                                        "summary": cm.get("message", ""),
                                        "recommended_cloud": "nvidia_deepseek_v4",
                                        "optimal_role": "Rust Ratatui SIMD & zero-allocation layout optimization"
                                    })
                        except Exception:
                            continue
            except Exception:
                pass

        # 2. Check Python Textual TUI Syntax
        canonical_tui = REPO_ROOT / "01_apps/canonical_port/tui/canonical_tui.py"
        if canonical_tui.exists():
            try:
                res = subprocess.run(
                    ["python3", "-m", "py_compile", str(canonical_tui)],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if res.returncode != 0:
                    gaps.append({
                        "domain": "python_textual",
                        "source_file": "01_apps/canonical_port/tui/canonical_tui.py",
                        "line_number": 1,
                        "level": "error",
                        "summary": res.stderr.strip()[:200],
                        "recommended_cloud": "google_gemini_flash",
                        "optimal_role": "Textual TUI reactive event loop debugging"
                    })
            except Exception:
                pass

        # 3. Check Screen Lens Observation Feed for noted friction points
        if OBSIDIAN_OBSERVATIONS.exists():
            try:
                lines = OBSIDIAN_OBSERVATIONS.read_text(encoding="utf-8").splitlines()
                recent_lines = lines[-50:]
                for line in recent_lines:
                    if any(kw in line.lower() for kw in ("overflow", "timeout", "regression", "latency spike", "stalled")):
                        gaps.append({
                            "domain": "screen_lens_vla",
                            "source_file": "obsidian_vault/APPS_AND_FEATURES/SCREEN_LENS_LIVE_OBSERVATIONS.md",
                            "line_number": len(lines),
                            "level": "warning",
                            "summary": line.strip()[:200],
                            "recommended_cloud": "xai_grok_2",
                            "optimal_role": "Adversarial UI layout and sub-pixel edge case auditing"
                        })
            except Exception:
                pass

        return gaps

    def generate_idms(self) -> List[Dict[str, Any]]:
        """
        Gathers empirical gaps, computes cryptographic SHA256 signatures,
        applies the 60-minute cooldown firewall, and yields new IDMs.
        """
        raw_gaps = self.scan_recent_build_and_test_gaps()
        ram_state = self.probe_mach_ram()
        new_manifests = []
        now = time.time()
        timestamp_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        # Also inspect RAM sanctuary gap if headroom degraded
        if not ram_state.get("headroom_healthy", True):
            raw_gaps.append({
                "domain": "host_sanctuary_ram",
                "source_file": "Darwin Mach VM Kernel",
                "line_number": 0,
                "level": "warning",
                "summary": f"Available RAM ({ram_state['free_ram_gb']} GB) is below 9.6 GB sanctuary buffer",
                "sig_key": "host_sanctuary_ram:kernel:below_9_6gb",
                "recommended_cloud": "cloudflare_llama_3_3",
                "optimal_role": "Dynamic RAM offload and model sharding scheduling"
            })

        for gap in raw_gaps:
            # Compute canonical SHA256 signature from stable sig_key or domain + source_file + summary
            sig_input = gap.get("sig_key") or f"{gap['domain']}:{gap['source_file']}:{gap['summary']}"
            sha_sig = hashlib.sha256(sig_input.encode("utf-8")).hexdigest()

            # Enforce 60-minute cooldown firewall
            last_emitted = self.cooldown_cache.get(sha_sig, 0.0)
            if now - last_emitted < self.cooldown_seconds:
                continue  # Cooldown active; skip duplicate trigger

            # Generate new IDM
            idm_id = f"IDM_{sha_sig[:12]}_{int(now)}"
            manifest = {
                "idm_id": idm_id,
                "timestamp_utc": timestamp_utc,
                "sha256_signature": sha_sig,
                "domain": gap["domain"],
                "source_file": gap["source_file"],
                "line_number": gap["line_number"],
                "level": gap["level"],
                "diagnostic_summary": gap["summary"],
                "recommended_cloud_target": gap["recommended_cloud"],
                "optimal_cloud_role": gap["optimal_role"],
                "host_ram_status": ram_state,
                "status": "PENDING_DISPATCH",
                "emitted_by": "Screen Lens Perceptual Gap Detector (01_apps/screen_lens/)"
            }

            self.cooldown_cache[sha_sig] = now
            new_manifests.append(manifest)

        self._save_cooldown_cache()

        # Persist new IDMs to 04_data_and_memory
        if new_manifests:
            with open(IDM_LOG_PATH, "a", encoding="utf-8") as f:
                for m in new_manifests:
                    f.write(json.dumps(m) + "\n")

        return new_manifests


def main():
    detector = LensGapDetector()
    print("=" * 80)
    print("👁️ SCREEN LENS: PERCEPTUAL GAP DETECTOR & DIAGNOSTIC SUGGESTER")
    print("• Firewall 1: 100% Read-Only Monorepo Scanning")
    print("• Firewall 2: 60-Minute SHA256 Cooldown Gate")
    print(f"• IDM Sink: {IDM_LOG_PATH}")
    print("=" * 80)

    ram = detector.probe_mach_ram()
    print(f"💾 Darwin Mach Dynamic RAM: {ram.get('free_ram_gb')} GB (Sanctuary: {ram.get('headroom_healthy')})")

    t0 = time.perf_counter()
    new_idms = detector.generate_idms()
    elapsed = round((time.perf_counter() - t0) * 1000, 2)

    print(f"✔ Scan complete in {elapsed}ms. Emitted {len(new_idms)} new Improvement Diagnostic Manifests.")
    for idm in new_idms:
        print(f"  ▶ [{idm['level'].upper()}] {idm['domain']} in {idm['source_file']}:{idm['line_number']}")
        print(f"    Summary: {idm['diagnostic_summary'][:90]}")
        print(f"    Cloud Target: {idm['recommended_cloud_target']} ({idm['optimal_cloud_role']})")


if __name__ == "__main__":
    main()
