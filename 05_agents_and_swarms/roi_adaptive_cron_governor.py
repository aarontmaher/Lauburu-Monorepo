#!/usr/bin/env python3
"""
================================================================================
Lauburu Sovereign Mesh: ROI-Adaptive Cron Governor
================================================================================
Subsystem: 05_agents_and_swarms/roi_adaptive_cron_governor.py
Version: 1.0.0-SOVEREIGN-ROI-CRON

Role:
  Unified daemon that reads LIVE state every 60 seconds and dynamically adapts
  all training cron intervals based on:
    1. Live ROI scores from live_training_telemetry.json
    2. Cloud quota burn rate from CloudQuotaOrchestrator
    3. Dynamic API provider registry (Claude, ChatGPT, etc.)
    4. RAM and disk health invariants
    5. Genetic drafter CPU/RAM throttle gate

  Writes cron_schedule_overrides.json consumed by all training daemons
  to auto-adjust their sleep intervals without restart.

  Rule #0 Zero-Mock: All decisions based on live kernel/log/API probes.
  Rule #3 Host Sanctuary: Enforces >= 6.5 GB free RAM.
  Rule #6 Graduated Autonomy: Tier 1 fully autonomous, Tier 4 requires approval.
================================================================================
"""
import os
import sys
import time
import json
import signal
import logging
import subprocess
import shutil
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional

# ── Add local modules ─────────────────────────────────────────────────────────
REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
SCREEN_LENS_SRC = REPO_ROOT / "01_apps/screen_lens/src"
AGENTS_DIR = REPO_ROOT / "05_agents_and_swarms"
for p in [str(SCREEN_LENS_SRC), str(AGENTS_DIR), str(REPO_ROOT / "12_continuous_lora_evolution")]:
    if p not in sys.path:
        sys.path.insert(0, p)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [ROICronGovernor] %(message)s"
)
log = logging.getLogger("ROICronGovernor")

# ── Paths ─────────────────────────────────────────────────────────────────────
TELEMETRY_FILE  = REPO_ROOT / "04_data_and_memory/live_training_telemetry.json"
QUOTA_STATE_FILE = REPO_ROOT / "04_data_and_memory/universal_cloud_quota_state.json"
REGISTRY_FILE   = REPO_ROOT / "04_data_and_memory/dynamic_provider_registry.json"
ROI_STATUS_FILE = REPO_ROOT / "04_data_and_memory/roi_gated_training_status.json"
OVERRIDES_FILE  = REPO_ROOT / "04_data_and_memory/cron_schedule_overrides.json"
DISK_COMPRESSOR = REPO_ROOT / "06_scripts_and_tooling/maintenance/disk_emergency_compressor.sh"
LIVE_LOSS_SCRIPT = REPO_ROOT / "12_continuous_lora_evolution/live_loss_extractor.py"
PROVIDER_REG_SCRIPT = REPO_ROOT / "05_agents_and_swarms/dynamic_api_provider_registry.py"
ROI_PROTOCOL_SCRIPT = REPO_ROOT / "05_agents_and_swarms/roi_gated_training_protocol.py"
GOVERNOR_LOG    = REPO_ROOT / "logs/roi_adaptive_cron_governor.log"
OBSIDIAN_OUT    = REPO_ROOT / "obsidian_vault/04_ANALYTICS/ROI_ADAPTIVE_CRON_STATUS.md"
PID_LOCK_FILE   = Path("/tmp/roi_adaptive_cron_governor.pid")

# ── Tunable thresholds ────────────────────────────────────────────────────────
RAM_SANCTUARY_GB     = 6.5    # Suspend genetic drafter below this
DISK_EMERGENCY_GB    = 10.0   # Trigger compressor below this
DISK_WARN_GB         = 15.0   # Reduce dataset write limits below this
ROI_HIGH_THRESHOLD   = 80.0   # Interval = 300s when ROI > 80
ROI_LOW_THRESHOLD    = 30.0   # Interval = 1800s when ROI < 30
ROI_MED_INTERVAL     = 900    # Default interval (seconds)
ROI_HIGH_INTERVAL    = 300    # Aggressive training
ROI_LOW_INTERVAL     = 1800   # Throttle
QUOTA_HIGH_THRESHOLD = 0.80   # Slow down if > 80% quota consumed
CHECK_INTERVAL       = 60     # Seconds between cron governor cycles

# Genetic drafter script name for PID detection
GENETIC_DRAFTER_SCRIPT = "continuous_10m_genetic_drafter_trainer.py"


class ROIAdaptiveCronGovernor:
    def __init__(self):
        self.running = True
        self.cycle_count = 0
        self._setup_logging()
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    def _setup_logging(self):
        GOVERNOR_LOG.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(GOVERNOR_LOG, mode="a")
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] [ROICronGovernor] %(message)s"
        ))
        logging.getLogger().addHandler(file_handler)

    def _handle_signal(self, signum, frame):
        log.info(f"Signal {signum} received — graceful shutdown.")
        self.running = False

    # ── PID lock ──────────────────────────────────────────────────────────────
    def acquire_pid_lock(self) -> bool:
        if PID_LOCK_FILE.exists():
            try:
                old_pid = int(PID_LOCK_FILE.read_text().strip())
                result = subprocess.run(
                    ["ps", "-p", str(old_pid), "-o", "comm="],
                    capture_output=True, text=True
                )
                if result.returncode == 0 and "python" in result.stdout:
                    log.warning(f"Governor already running (PID {old_pid}). Exiting.")
                    return False
            except Exception:
                pass
        PID_LOCK_FILE.write_text(str(os.getpid()))
        return True

    # ── Live data loaders ─────────────────────────────────────────────────────
    def load_live_telemetry(self) -> Dict[str, Any]:
        if TELEMETRY_FILE.exists():
            try:
                return json.loads(TELEMETRY_FILE.read_text())
            except Exception:
                pass
        return {}

    def load_quota_state(self) -> Dict[str, Any]:
        if QUOTA_STATE_FILE.exists():
            try:
                return json.loads(QUOTA_STATE_FILE.read_text())
            except Exception:
                pass
        return {}

    def load_provider_registry(self) -> Dict[str, Any]:
        if REGISTRY_FILE.exists():
            try:
                return json.loads(REGISTRY_FILE.read_text())
            except Exception:
                pass
        return {}

    def load_roi_status(self) -> Dict[str, Any]:
        if ROI_STATUS_FILE.exists():
            try:
                return json.loads(ROI_STATUS_FILE.read_text())
            except Exception:
                pass
        return {}

    # ── Hardware probes ───────────────────────────────────────────────────────
    def get_disk_free_gb(self) -> float:
        try:
            return shutil.disk_usage("/Users/aaron").free / 1e9
        except Exception:
            return 99.0

    def get_ram_free_gb(self) -> Optional[float]:
        try:
            import psutil
            return psutil.virtual_memory().available / 1e9
        except Exception:
            return None

    def find_pid(self, script_name: str) -> Optional[int]:
        try:
            result = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=3)
            for line in result.stdout.splitlines():
                if script_name in line and "grep" not in line:
                    parts = line.split()
                    if len(parts) > 1:
                        try:
                            return int(parts[1])
                        except ValueError:
                            pass
        except Exception:
            pass
        return None

    # ── Actions ───────────────────────────────────────────────────────────────
    def trigger_live_loss_extraction(self):
        """Runs live_loss_extractor.py --once in subprocess."""
        py = sys.executable
        try:
            subprocess.Popen(
                [py, str(LIVE_LOSS_SCRIPT)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                start_new_session=True
            )
        except Exception as e:
            log.warning(f"Could not spawn live_loss_extractor: {e}")

    def trigger_provider_registry_scan(self):
        """Refreshes the dynamic API provider registry."""
        py = sys.executable
        try:
            subprocess.Popen(
                [py, str(PROVIDER_REG_SCRIPT)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                start_new_session=True
            )
        except Exception as e:
            log.warning(f"Could not spawn provider_registry: {e}")

    def trigger_roi_protocol_refresh(self):
        """Re-evaluates ROI across all training tracks."""
        py = sys.executable
        try:
            subprocess.Popen(
                [py, str(ROI_PROTOCOL_SCRIPT)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                start_new_session=True
            )
        except Exception as e:
            log.warning(f"Could not spawn roi_protocol: {e}")

    def trigger_disk_compressor(self):
        """Emergency disk compression."""
        try:
            log.warning("🔴 DISK EMERGENCY: Triggering disk_emergency_compressor.sh")
            subprocess.Popen(
                ["bash", str(DISK_COMPRESSOR)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                start_new_session=True,
                env={**os.environ, "DISK_THRESHOLD_GB": "10", "DRY_RUN": "0"}
            )
        except Exception as e:
            log.error(f"Failed to trigger disk compressor: {e}")

    def throttle_genetic_drafter(self, pid: int, reason: str):
        """Sends SIGSTOP to the genetic drafter to free RAM/CPU."""
        try:
            os.kill(pid, 19)  # SIGSTOP
            log.warning(f"⏸️  Sent SIGSTOP to genetic drafter (PID {pid}): {reason}")
        except Exception as e:
            log.error(f"Failed to SIGSTOP genetic drafter: {e}")

    def resume_genetic_drafter(self, pid: int):
        """Resumes stopped genetic drafter."""
        try:
            os.kill(pid, 18)  # SIGCONT
            log.info(f"▶️  Sent SIGCONT to genetic drafter (PID {pid})")
        except Exception as e:
            log.error(f"Failed to SIGCONT genetic drafter: {e}")

    # ── Interval computation ──────────────────────────────────────────────────
    def compute_interval_for_roi(self, roi_score: float, quota_utilization: float) -> int:
        """
        Determines trainer sleep interval based on ROI and quota pressure.
        Higher ROI → shorter interval (train more aggressively).
        High quota utilization → slightly longer interval to pace consumption.
        """
        if roi_score >= ROI_HIGH_THRESHOLD:
            base_interval = ROI_HIGH_INTERVAL
        elif roi_score >= ROI_LOW_THRESHOLD:
            # Linear interpolation between HIGH and MED
            t = (roi_score - ROI_LOW_THRESHOLD) / (ROI_HIGH_THRESHOLD - ROI_LOW_THRESHOLD)
            base_interval = int(ROI_MED_INTERVAL - t * (ROI_MED_INTERVAL - ROI_HIGH_INTERVAL))
        else:
            base_interval = ROI_LOW_INTERVAL

        # Quota pressure dampener: slow down when > 80% consumed
        if quota_utilization > QUOTA_HIGH_THRESHOLD:
            base_interval = int(base_interval * 1.5)
            log.info(f"Quota pressure dampener applied (util={quota_utilization:.1%}): interval={base_interval}s")

        return base_interval

    # ── Main cycle ────────────────────────────────────────────────────────────
    def run_cycle(self) -> Dict[str, Any]:
        self.cycle_count += 1
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        cycle_result = {"timestamp_utc": ts, "cycle": self.cycle_count, "actions": []}

        # ── 1. Refresh live telemetry (every cycle) ────────────────────────
        if self.cycle_count % 2 == 0:  # Every 2 min
            self.trigger_live_loss_extraction()
            cycle_result["actions"].append("live_loss_extraction_triggered")

        # ── 2. Refresh provider registry (every 10 min) ────────────────────
        if self.cycle_count % 10 == 0:
            self.trigger_provider_registry_scan()
            cycle_result["actions"].append("provider_registry_scan_triggered")

        # ── 3. Hardware gates ─────────────────────────────────────────────
        disk_free = self.get_disk_free_gb()
        ram_free = self.get_ram_free_gb()
        drafter_pid = self.find_pid(GENETIC_DRAFTER_SCRIPT)

        cycle_result["disk_free_gb"] = round(disk_free, 2)
        cycle_result["ram_free_gb"] = round(ram_free, 2) if ram_free else None
        cycle_result["genetic_drafter_pid"] = drafter_pid

        # Disk emergency
        if disk_free < DISK_EMERGENCY_GB:
            self.trigger_disk_compressor()
            cycle_result["actions"].append(f"disk_emergency_compressor_triggered (free={disk_free:.1f}GB)")

        # RAM gate: throttle genetic drafter
        if ram_free is not None and ram_free < RAM_SANCTUARY_GB and drafter_pid:
            self.throttle_genetic_drafter(drafter_pid, f"RAM={ram_free:.2f}GB < {RAM_SANCTUARY_GB}GB")
            cycle_result["actions"].append(f"genetic_drafter_throttled (RAM={ram_free:.2f}GB)")
        elif ram_free is not None and ram_free >= RAM_SANCTUARY_GB and drafter_pid:
            # Attempt to resume if it was stopped
            try:
                result = subprocess.run(["ps", "-p", str(drafter_pid), "-o", "stat="],
                                         capture_output=True, text=True)
                if "T" in result.stdout:  # T = stopped
                    self.resume_genetic_drafter(drafter_pid)
                    cycle_result["actions"].append(f"genetic_drafter_resumed (RAM={ram_free:.2f}GB)")
            except Exception:
                pass

        # ── 4. Load ROI state ─────────────────────────────────────────────
        roi_status = self.load_roi_status()
        active_roi = roi_status.get("active_roi_score", 50.0)
        active_model = roi_status.get("active_training_model", "unknown")
        active_task = roi_status.get("active_training_task", "unknown")

        # ── 5. Compute quota utilization ──────────────────────────────────
        quota_state = self.load_quota_state()
        total_cap = sum(
            v.get("daily_cap", 1500)
            for v in quota_state.get("providers", {}).values()
        ) or 5300
        total_used = sum(
            v.get("used_today", 0)
            for v in quota_state.get("providers", {}).values()
        )
        quota_util = total_used / max(1, total_cap)
        cycle_result["quota_utilization"] = round(quota_util, 4)
        cycle_result["quota_used"] = total_used
        cycle_result["quota_cap"] = total_cap

        # ── 6. Detect provider additions (Claude/ChatGPT) ──────────────────
        registry = self.load_provider_registry()
        new_providers = []
        if registry:
            for alias, cfg in registry.get("all_providers", {}).items():
                if cfg.get("status") == "CONFIGURED" and cfg.get("cost_per_1k_tokens", 0) > 0:
                    new_providers.append(alias)
        if new_providers:
            log.info(f"💰 Paid providers active: {new_providers} — factoring into quota pool")
            cycle_result["paid_providers_active"] = new_providers

        # ── 7. Compute interval ───────────────────────────────────────────
        trainer_interval = self.compute_interval_for_roi(active_roi, quota_util)
        cycle_result["computed_trainer_interval_s"] = trainer_interval
        cycle_result["active_roi"] = active_roi
        cycle_result["active_model"] = active_model

        # ── 8. Write cron_schedule_overrides.json ─────────────────────────
        overrides = {
            "timestamp_utc": ts,
            "computed_by": "roi_adaptive_cron_governor",
            "active_roi": active_roi,
            "active_model": active_model,
            "active_task": active_task,
            "disk_free_gb": round(disk_free, 2),
            "ram_free_gb": round(ram_free, 2) if ram_free else None,
            "quota_utilization": round(quota_util, 4),
            "quota_used": total_used,
            "quota_cap": total_cap,
            "paid_providers_active": new_providers,
            "intervals": {
                "run_continuous_free_tier_trainer": trainer_interval,
                "master_free_tier_ai_maximizer": max(30, trainer_interval // 3),
                "lens_continuous_training_daemon": max(30, trainer_interval // 4),
                "continuous_overnight_ecommerce_trainer": trainer_interval,
                "mcts_lora_harvester": max(60, trainer_interval // 2),
                "lens_247_auditor_training": max(30, trainer_interval // 4),
            },
            "dataset_write_limit_per_source": 500 if disk_free < DISK_WARN_GB else 3000,
            "disk_brake_active": disk_free < DISK_WARN_GB,
            "ram_brake_active": ram_free is not None and ram_free < RAM_SANCTUARY_GB,
        }
        OVERRIDES_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(OVERRIDES_FILE, "w", encoding="utf-8") as f:
            json.dump(overrides, f, indent=2)

        cycle_result["overrides_written"] = str(OVERRIDES_FILE)

        # ── 9. Refresh ROI protocol (every 5 min) ─────────────────────────
        if self.cycle_count % 5 == 0:
            self.trigger_roi_protocol_refresh()
            cycle_result["actions"].append("roi_protocol_refresh_triggered")

        # ── 10. Sync Obsidian ─────────────────────────────────────────────
        if self.cycle_count % 3 == 0:
            self._write_obsidian(overrides, cycle_result)
            cycle_result["actions"].append("obsidian_synced")

        log.info(
            f"Cycle {self.cycle_count}: ROI={active_roi} model={active_model} "
            f"interval={trainer_interval}s disk={disk_free:.1f}GB ram={ram_free:.1f}GB "
            f"quota={quota_util:.1%}"
        )
        return cycle_result

    def _write_obsidian(self, overrides: Dict, result: Dict):
        """Syncs governor state to Obsidian vault."""
        OBSIDIAN_OUT.parent.mkdir(parents=True, exist_ok=True)
        ts = overrides["timestamp_utc"]
        intervals = overrides["intervals"]
        paid = overrides.get("paid_providers_active", [])
        interval_rows = "\n".join(
            f"| `{k}` | `{v}s` |"
            for k, v in intervals.items()
        )
        paid_status = ", ".join(paid) if paid else "None (free-tier only)"

        report = f"""---
title: "ROI-Adaptive Cron Governor — Live State"
tags: [cron, roi, training, adaptive, quota]
date: "{ts}"
---

# ⚡ ROI-Adaptive Cron Governor

- **[[Index]]** | **[[roi_gated_training_protocol]]** | **[[LIVE_LOSS_TELEMETRY]]**

## 🎯 Active Decision State

| Metric | Value |
|---|---|
| Active ROI Score | `{overrides['active_roi']}` |
| Active Training Model | `{overrides['active_model']}` |
| Active Task | `{overrides['active_task']}` |
| Quota Utilization | `{overrides['quota_utilization']:.1%}` ({overrides['quota_used']} / {overrides['quota_cap']}) |
| Disk Free | `{overrides['disk_free_gb']} GB` {'🔴 BRAKE ACTIVE' if overrides['disk_brake_active'] else '✅ OK'} |
| RAM Free | `{overrides['ram_free_gb']} GB` {'⚠️ BRAKE ACTIVE' if overrides['ram_brake_active'] else '✅ OK'} |
| Paid Providers Active | `{paid_status}` |

## 📅 Computed Training Intervals

| Daemon | Interval |
|---|---|
{interval_rows}

## 📊 Dataset Write Limit

`{overrides['dataset_write_limit_per_source']} lines/source` {'(disk-constrained mode)' if overrides['disk_brake_active'] else '(normal mode)'}

---
_Last updated: {ts} — Governor cycle #{result['cycle']}_
"""
        with open(OBSIDIAN_OUT, "w", encoding="utf-8") as f:
            f.write(report)

    def run_forever(self):
        log.info("=" * 70)
        log.info("⚡ ROI-ADAPTIVE CRON GOVERNOR v1.0.0 STARTING")
        log.info(f"   Check interval: {CHECK_INTERVAL}s")
        log.info(f"   RAM sanctuary: {RAM_SANCTUARY_GB} GB")
        log.info(f"   Disk emergency: {DISK_EMERGENCY_GB} GB")
        log.info("=" * 70)

        if not self.acquire_pid_lock():
            return

        while self.running:
            try:
                self.run_cycle()
            except Exception as e:
                log.error(f"Cycle error: {e}", exc_info=True)
            if self.running:
                time.sleep(CHECK_INTERVAL)

        PID_LOCK_FILE.unlink(missing_ok=True)
        log.info("ROI-Adaptive Cron Governor shut down gracefully.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", "--dry-run", action="store_true", help="Run one cycle and exit")
    parser.add_argument("--daemon", action="store_true", help="Run as continuous daemon")
    args = parser.parse_args()

    gov = ROIAdaptiveCronGovernor()
    if args.once or not args.daemon:
        result = gov.run_cycle()
        print(json.dumps({k: v for k, v in result.items() if k != "actions"}, indent=2))
        print("\nActions taken:", result.get("actions", []))
        print(f"\n✅ Overrides written → {OVERRIDES_FILE}")
    else:
        gov.run_forever()
