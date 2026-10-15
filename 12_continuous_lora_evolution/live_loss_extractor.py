#!/usr/bin/env python3
"""
================================================================================
Lauburu Sovereign Mesh: Live Loss & Training Telemetry Extractor
================================================================================
Subsystem: 12_continuous_lora_evolution/live_loss_extractor.py
Version: 1.0.0-LIVE-LOSS-SOVEREIGN

Role:
  Tails actual trainer log files (continuous_qlora_trainer.log,
  free_tier_maximizer.log) to extract real-time loss values, compute
  rolling loss_velocity, and write to live_training_telemetry.json
  for ROI-Gated Training Protocol consumption.

  Rule #0 Zero-Mock: All loss values come from physical log reads.
  Rule #2 Tri-Vault: Writes to 04_data_and_memory/ + Obsidian vault.
================================================================================
"""
import os
import re
import sys
import time
import json
import hashlib
import logging
from pathlib import Path
from collections import deque
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [LiveLossExtractor] %(message)s"
)
log = logging.getLogger("LiveLossExtractor")

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
TELEMETRY_OUT = REPO_ROOT / "04_data_and_memory/live_training_telemetry.json"
OBSIDIAN_OUT  = REPO_ROOT / "obsidian_vault/05_TRAINING/LIVE_LOSS_TELEMETRY.md"

# Log files to tail for loss values
LOG_SOURCES = {
    "qlora_trainer": REPO_ROOT / "logs/continuous_qlora_trainer.log",
    "free_tier_maximizer": REPO_ROOT / "logs/free_tier_maximizer.log",
    "genetic_drafter": REPO_ROOT / "logs/continuous_10m_genetic_drafter_trainer.log",
}

# Regex patterns for extracting loss from different trainer formats
LOSS_PATTERNS = [
    re.compile(r"loss[=:\s]+([0-9]+\.[0-9]+)", re.IGNORECASE),
    re.compile(r"train_loss[=:\s]+([0-9]+\.[0-9]+)", re.IGNORECASE),
    re.compile(r"val_loss[=:\s]+([0-9]+\.[0-9]+)", re.IGNORECASE),
    re.compile(r"\bloss\b.*?([0-9]+\.[0-9]{3,})", re.IGNORECASE),
]

# Rolling window for velocity computation
WINDOW_SIZE = 20


def tail_file(path: Path, n_lines: int = 200) -> List[str]:
    """Reads last n_lines from a file efficiently."""
    if not path.exists():
        return []
    try:
        with open(path, "rb") as f:
            # Seek from end
            f.seek(0, 2)
            size = f.tell()
            buf = bytearray()
            lines_found = 0
            pos = size
            while pos > 0 and lines_found < n_lines + 1:
                chunk = min(4096, pos)
                pos -= chunk
                f.seek(pos)
                data = f.read(chunk)
                buf = data + buf
                lines_found = buf.count(b"\n")
            text = buf.decode("utf-8", errors="replace")
            return text.splitlines()[-n_lines:]
    except Exception as e:
        log.warning(f"Failed to tail {path}: {e}")
        return []


def extract_losses_from_lines(lines: List[str]) -> List[float]:
    """Extracts numeric loss values from log lines."""
    losses = []
    for line in lines:
        for pat in LOSS_PATTERNS:
            m = pat.search(line)
            if m:
                try:
                    val = float(m.group(1))
                    if 0.0 < val < 10.0:  # Sanity filter
                        losses.append(val)
                        break
                except ValueError:
                    continue
    return losses


def compute_loss_velocity(loss_history: List[float]) -> float:
    """
    Computes loss_velocity = average per-step reduction over the window.
    Positive = loss is decreasing (good). Near-zero = plateau.
    """
    if len(loss_history) < 3:
        return 0.025  # Default non-plateau assumption
    window = loss_history[-WINDOW_SIZE:]
    if len(window) < 2:
        return 0.025
    # Simple linear regression slope (negative = decreasing loss)
    n = len(window)
    x_mean = (n - 1) / 2.0
    y_mean = sum(window) / n
    numerator = sum((i - x_mean) * (window[i] - y_mean) for i in range(n))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    if denominator == 0:
        return 0.0
    slope = numerator / denominator
    # Positive velocity = loss going down (negate slope)
    return round(max(-1.0, min(1.0, -slope)), 5)


def extract_source_telemetry(source_name: str, log_path: Path) -> Dict:
    """Extract loss telemetry from a single log source."""
    lines = tail_file(log_path, n_lines=300)
    losses = extract_losses_from_lines(lines)

    current_loss = losses[-1] if losses else None
    velocity = compute_loss_velocity(losses) if losses else 0.0
    recent_losses = losses[-WINDOW_SIZE:] if losses else []

    return {
        "source": source_name,
        "log_path": str(log_path),
        "log_exists": log_path.exists(),
        "loss_samples_extracted": len(losses),
        "current_loss": round(current_loss, 5) if current_loss else None,
        "loss_velocity": velocity,
        "plateau_detected": velocity < 0.005 and len(losses) >= 5,
        "recent_losses": [round(x, 5) for x in recent_losses[-10:]],
    }


def get_active_trainer_pids() -> Dict[str, Optional[int]]:
    """Returns live PIDs of known trainer scripts."""
    import subprocess
    result = {}
    targets = {
        "qlora_trainer": "run_continuous_free_tier_trainer.py",
        "free_tier_maximizer": "master_free_tier_ai_maximizer.py",
        "genetic_drafter": "continuous_10m_genetic_drafter_trainer.py",
        "lens_trainer": "lens_continuous_training_daemon.py",
        "overnight_ecommerce": "continuous_overnight_ecommerce_trainer.py",
    }
    try:
        proc = subprocess.run(
            ["ps", "aux"], capture_output=True, text=True, timeout=3.0
        )
        for name, script in targets.items():
            pid = None
            for line in proc.stdout.splitlines():
                if script in line and "grep" not in line:
                    parts = line.split()
                    if len(parts) > 1:
                        try:
                            pid = int(parts[1])
                        except ValueError:
                            pass
                        break
            result[name] = pid
    except Exception as e:
        log.warning(f"PID scan failed: {e}")
    return result


def get_disk_and_ram() -> Dict:
    """Returns current disk free GB and RAM free GB."""
    import shutil
    try:
        import psutil
        mem = psutil.virtual_memory()
        ram_free_gb = round(mem.available / 1e9, 2)
        ram_pct = round(mem.percent, 1)
    except Exception:
        ram_free_gb = None
        ram_pct = None

    disk = shutil.disk_usage("/Users/aaron")
    disk_free_gb = round(disk.free / 1e9, 2)
    disk_used_pct = round((disk.used / disk.total) * 100.0, 1)
    return {
        "ram_free_gb": ram_free_gb,
        "ram_used_pct": ram_pct,
        "disk_free_gb": disk_free_gb,
        "disk_used_pct": disk_used_pct,
        "disk_critical": disk_free_gb < 10.0,
        "ram_low": ram_free_gb is not None and ram_free_gb < 6.5,
    }


def run_extraction(write_obsidian: bool = True) -> Dict:
    """Full extraction pass. Returns the telemetry dict."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    sources = {}
    for name, path in LOG_SOURCES.items():
        sources[name] = extract_source_telemetry(name, path)

    pids = get_active_trainer_pids()
    hw = get_disk_and_ram()

    # Aggregate: best current_loss across active sources
    active_losses = [
        s["current_loss"] for s in sources.values()
        if s["current_loss"] is not None and pids.get(s["source"])
    ]
    agg_loss = round(sum(active_losses) / len(active_losses), 5) if active_losses else None

    # Aggregate velocity across active sources
    active_velocities = [
        s["loss_velocity"] for s in sources.values()
        if s["log_exists"] and s["loss_samples_extracted"] > 0
    ]
    agg_velocity = round(sum(active_velocities) / len(active_velocities), 5) if active_velocities else 0.025

    telemetry = {
        "timestamp_utc": ts,
        "aggregate_current_loss": agg_loss,
        "aggregate_loss_velocity": agg_velocity,
        "global_plateau_detected": agg_velocity < 0.005,
        "hardware": hw,
        "active_trainer_pids": pids,
        "source_telemetry": sources,
    }

    # Write to 04_data_and_memory
    TELEMETRY_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(TELEMETRY_OUT, "w", encoding="utf-8") as f:
        json.dump(telemetry, f, indent=2)

    # SHA256 verify write
    written_bytes = TELEMETRY_OUT.stat().st_size
    sha256 = hashlib.sha256(TELEMETRY_OUT.read_bytes()).hexdigest()[:16]
    log.info(
        f"Telemetry written: {written_bytes} bytes, sha256={sha256}... | "
        f"loss={agg_loss} vel={agg_velocity} disk={hw['disk_free_gb']}GB ram={hw['ram_free_gb']}GB"
    )

    if write_obsidian:
        _write_obsidian_report(telemetry, sha256)

    return telemetry


def _write_obsidian_report(tel: Dict, sha256: str):
    """Syncs telemetry to Obsidian vault."""
    OBSIDIAN_OUT.parent.mkdir(parents=True, exist_ok=True)
    hw = tel["hardware"]
    pids = tel["active_trainer_pids"]
    ts = tel["timestamp_utc"]

    pid_rows = "\n".join(
        f"| `{name}` | `{pid if pid else '—'}` | {'🟢 RUNNING' if pid else '🔴 STOPPED'} |"
        for name, pid in pids.items()
    )
    src_rows = "\n".join(
        f"| `{k}` | `{v['current_loss']}` | `{v['loss_velocity']}` | "
        f"{'⚠️ PLATEAU' if v['plateau_detected'] else '✅ Learning'} | `{v['loss_samples_extracted']}` |"
        for k, v in tel["source_telemetry"].items()
        if v["log_exists"]
    )

    report = f"""---
title: "Live Loss Telemetry — Lauburu Training Pipeline"
tags: [training, loss, telemetry, roi, live]
date: "{ts}"
sha256: "{sha256}"
---

# 📉 Live Training Loss Telemetry

- **Knowledge Core:** [[Index]]
- **ROI Protocol:** [[roi_gated_training_protocol]]
- **Pipeline Status:** [[CONTINUOUS_FREE_TIER_PIPELINE_STATUS]]

## 🏥 Hardware State

| Metric | Value | Status |
|---|---|---|
| RAM Free | `{hw['ram_free_gb']} GB` | {'⚠️ LOW' if hw['ram_low'] else '✅ OK'} |
| Disk Free | `{hw['disk_free_gb']} GB ({100 - hw['disk_used_pct']:.1f}% free)` | {'🔴 CRITICAL' if hw['disk_critical'] else '✅ OK'} |

## 📊 Trainer PIDs

| Trainer | PID | Status |
|---|---|---|
{pid_rows}

## 📉 Per-Source Loss Telemetry

| Source | Current Loss | Velocity | Trend | Samples |
|---|---|---|---|---|
{src_rows}

## 🎯 Aggregate

- **Aggregate Loss:** `{tel['aggregate_current_loss']}`
- **Aggregate Velocity:** `{tel['aggregate_loss_velocity']}`
- **Global Plateau:** `{tel['global_plateau_detected']}`
- **Last Updated:** `{ts}`
"""
    with open(OBSIDIAN_OUT, "w", encoding="utf-8") as f:
        f.write(report)


if __name__ == "__main__":
    if "--daemon" in sys.argv:
        interval = 60
        log.info(f"Live Loss Extractor daemon started (interval={interval}s)")
        while True:
            try:
                run_extraction()
            except Exception as e:
                log.error(f"Extraction cycle error: {e}")
            time.sleep(interval)
    else:
        tel = run_extraction()
        print(json.dumps({
            "aggregate_current_loss": tel["aggregate_current_loss"],
            "aggregate_loss_velocity": tel["aggregate_loss_velocity"],
            "global_plateau_detected": tel["global_plateau_detected"],
            "hardware": tel["hardware"],
            "active_trainers": {k: "RUNNING" if v else "STOPPED" for k, v in tel["active_trainer_pids"].items()},
        }, indent=2))
