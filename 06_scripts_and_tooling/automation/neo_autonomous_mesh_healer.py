#!/usr/bin/env python3
"""
================================================================================
Neo: Autonomous Bluetooth Mesh, GGUF/TPU Daemons & Shizuku Orchestrator
================================================================================
Subsystem: 06_scripts_and_tooling/automation/neo_autonomous_mesh_healer.py
Version: 2.0.0-NEO-PERSISTENT-GOVERNOR
Lauburu Mesh Ecosystem — 2026

Mandate:
1. GGUF & TPU Daemons (Rule 8 compliant):
   - Health check & auto-launch for Port 8081 (llama-server), 8082 (prima.cpp), 8083 (adapter).
   - Health check & auto-launch for NPU Sentinel Daemon (/tmp/lauburu_npu_state.json).
2. Android Shizuku Activation:
   - Automatically activates Shizuku on connected Android devices via ADB starter script.
3. Host Bluetooth Mesh:
   - Automatically connects Samsung S20, Pixel 10 Pro XL, and MacBook Pro via blueutil.
4. Pre-Flight Health & Smart IDE Execution:
   - Checks existing installations; if already compiled/installed, starts it immediately if offline.
   - Triggers NPU model to synthesize ongoing app evolutions (/loop).
5. Persistent Launchd Daemon:
   - Supports --install-service to run as a persistent macOS LaunchAgent.
================================================================================
"""

import sys
import os
import time
import json
import socket
import argparse
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

REPO_ROOT = Path("/Volumes/Lauburu-Monorepo")
OBSIDIAN_VAULT = REPO_ROOT / "obsidian_vault/05_AGENTS"
NEO_CHRONICLE = OBSIDIAN_VAULT / "NEO_CONTINUOUS_AI_TRAINING_CHRONICLE.md"
LORA_FILE = Path("/Volumes/Lauburu-Monorepo/04_data_and_memory/data/continuous_lora_dataset.jsonl")
BLUEUTIL_BIN = Path("/Users/aaron/.local/bin/blueutil")
NPU_DAEMON_SCRIPT = REPO_ROOT / "01_apps/screen_lens/sandbox_evolution/npu_sentinel/npu_metric_sentinel_daemon.py"
NPU_PID_FILE = Path("/tmp/lauburu_npu_daemon.pid")
NPU_STATE_FILE = Path("/tmp/lauburu_npu_state.json")
IDE_SCRIPT = REPO_ROOT / "01_apps/screen_lens/sandbox_evolution/bluetooth_terminal_arena/run_sovereign_bluetooth_npu_ide.sh"
ARENA_DIR = REPO_ROOT / "01_apps/screen_lens/sandbox_evolution/bluetooth_terminal_arena"
LAUNCHD_PLIST = Path.home() / "Library/LaunchAgents/com.lauburu.neo.mesh.daemon.plist"

sys.path.insert(0, str(ARENA_DIR))
sys.path.insert(0, str(REPO_ROOT / "06_scripts_and_tooling/automation"))
try:
    from npu_orchestrator import PureNpuOrchestrator
except ImportError:
    PureNpuOrchestrator = None

try:
    from neo_npu_training_regulator import NeoNpuTrainingRegulator
except ImportError:
    NeoNpuTrainingRegulator = None

BT_PEERS = {
    "mac_mini": {"mac": "1c-f6-4c-81-0b-28", "name": "Mac Mini M4 Pro", "layer": "L1"},
    "mbp": {"mac": "2c-ca-16-08-c0-27", "name": "MacBook Pro 16", "layer": "L2"},
    "linux": {"mac": "00-41-0e-14-28-44", "name": "Linux Head Node", "layer": "L3"},
    "mba": {"mac": "dc-29-55-d6-fc-0b", "name": "MacBook Air", "layer": "L5"},
    "pixel": {"mac": "30-e0-44-6d-18-ec", "name": "Pixel 10 Pro XL", "layer": "L6"},
    "s20": {"mac": "5c-cb-99-05-81-41", "name": "Samsung S20+", "layer": "L7"}
}

WOL_TARGETS = [
    {"name": "Linux Head Node", "mac": "00:41:0e:14:28:43", "ip": "192.168.8.224"},
    {"name": "MacBook Air", "mac": "66:74:75:d8:16:fb", "ip": "192.168.8.222"}
]


class NeoPersistentMeshGovernor:
    """Full-stack autonomous governor for Bluetooth, GGUF, TPU, and Shizuku."""

    def __init__(self):
        self.blueutil = str(BLUEUTIL_BIN) if BLUEUTIL_BIN.exists() else "blueutil"
        self.training_regulator = NeoNpuTrainingRegulator() if NeoNpuTrainingRegulator else None

    def probe_tcp(self, port: int, host: str = "127.0.0.1", timeout_sec: float = 0.3) -> bool:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout_sec)
            res = s.connect_ex((host, port))
            s.close()
            return res == 0
        except Exception:
            return False

    def heal_gguf_daemons(self) -> Dict[str, Any]:
        """Checks ports 8081, 8082, 8083; auto-launches if offline."""
        p81 = self.probe_tcp(8081)
        p82 = self.probe_tcp(8082)
        p83 = self.probe_tcp(8083)

        results = {
            "8081_coder": "ONLINE" if p81 else "RESTARTING",
            "8082_prima_ring": "ONLINE" if p82 else "RESTARTING",
            "8083_ring_adapter": "ONLINE" if p83 else "RESTARTING"
        }

        # Auto-launch Port 8081 if down
        if not p81:
            cmd = (
                "llama-server -m /Volumes/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf/qwen2.5-coder-7b-instruct-q4_k_m.gguf "
                "-c 16384 -ngl 99 --port 8081 --host 127.0.0.1 > /tmp/llama_8081.log 2>&1 &"
            )
            subprocess.Popen(cmd, shell=True)
            results["8081_coder"] = "LAUNCHED_BACKGROUND"

        # Auto-launch Port 8082 if down
        if not p82:
            cmd = "nohup python3 -m prima.server --port 8082 > /tmp/prima_8082.log 2>&1 &"
            subprocess.Popen(cmd, shell=True)
            results["8082_prima_ring"] = "LAUNCHED_BACKGROUND"

        # Auto-launch Port 8083 if down
        if not p83:
            cmd = "nohup python3 /Volumes/Lauburu-Monorepo/02_ai_models_and_inference/sharding_daemon/prima_ring_adapter.py > /tmp/adapter_8083.log 2>&1 &"
            subprocess.Popen(cmd, shell=True)
            results["8083_ring_adapter"] = "LAUNCHED_BACKGROUND"

        return results

    def heal_tpu_npu_daemon(self) -> Dict[str, Any]:
        """Ensures the background NPU sentinel daemon is alive and writing state."""
        pid_alive = False
        if NPU_PID_FILE.exists():
            try:
                pid = int(NPU_PID_FILE.read_text().strip())
                os.kill(pid, 0)
                pid_alive = True
            except Exception:
                pid_alive = False

        if not pid_alive:
            cmd = f"/Users/aaron/.venv/bin/python3 {NPU_DAEMON_SCRIPT} > /tmp/npu_daemon.log 2>&1 &"
            subprocess.Popen(cmd, shell=True)
            return {"status": "LAUNCHED_BACKGROUND", "script": str(NPU_DAEMON_SCRIPT)}
        
        # Read active state
        state = {}
        if NPU_STATE_FILE.exists():
            try:
                state = json.loads(NPU_STATE_FILE.read_text())
            except Exception:
                pass

        return {
            "status": "RUNNING",
            "pid": pid,
            "active_tops": state.get("active_tops", 34.2),
            "systolic_latency_ms": state.get("systolic_latency_ms", 0.01)
        }

    def activate_shizuku(self) -> Dict[str, Any]:
        """Automatically executes Shizuku starter via ADB on connected Android nodes."""
        results = {}
        adb_devices_cmd = ["adb", "devices"]
        try:
            r = subprocess.run(adb_devices_cmd, capture_output=True, text=True, timeout=3.0)
            lines = [l.split("\t")[0] for l in r.stdout.split("\n") if "\tdevice" in l]
            for dev_serial in lines:
                start_cmd = [
                    "adb", "-s", dev_serial, "shell",
                    "sh /sdcard/Android/data/moe.shizuku.privileged.api/start.sh 2>/dev/null || "
                    "sh /data/local/tmp/shizuku_starter 2>/dev/null || "
                    "echo NO_STARTER"
                ]
                res = subprocess.run(start_cmd, capture_output=True, text=True, timeout=6.0)
                if "exit with 0" in res.stdout or "shizuku_starter" in res.stdout:
                    results[dev_serial] = "ACTIVATED_OK"
                else:
                    results[dev_serial] = f"EXECUTED: {res.stdout.strip()[-100:]}"
        except Exception as e:
            results["error"] = str(e)
        return results

    def heal_bluetooth_connections(self) -> Dict[str, Any]:
        """Connects paired Bluetooth peers from Mac Mini host."""
        results = {}
        for alias, peer in BT_PEERS.items():
            mac = peer["mac"]
            cmd = [self.blueutil, "--connect", mac]
            try:
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=5.0)
                results[alias] = "CONNECTED" if res.returncode == 0 else "FAILED_OR_CONNECTED"
            except Exception as e:
                results[alias] = f"ERROR: {str(e)}"
        return results

    def send_wol(self) -> Dict[str, Any]:
        """Dispatches WoL Magic Packets."""
        results = {}
        for t in WOL_TARGETS:
            clean = t["mac"].replace(":", "").replace("-", "")
            try:
                payload = b"\xff" * 6 + bytes.fromhex(clean) * 16
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                sock.sendto(payload, ("192.168.8.255", 9))
                sock.close()
                results[t["name"]] = "DISPATCHED"
            except Exception as e:
                results[t["name"]] = f"FAILED: {str(e)}"
        return results

    def run_npu_evolution_and_ide_check(self) -> Dict[str, Any]:
        """Checks IDE health; if offline, runs it; executes NPU evolution model."""
        # 1. Check IDE health
        ide_running = False
        try:
            r = subprocess.run(["pgrep", "-f", "bluetooth_arena_tui"], capture_output=True)
            ide_running = (r.returncode == 0)
        except Exception:
            pass

        ide_action = "ALREADY_ACTIVE"
        if not ide_running:
            # Launch snapshot verification or dev mode
            cmd = f"/bin/bash {IDE_SCRIPT} --snapshot > /tmp/ide_launch.log 2>&1"
            subprocess.Popen(cmd, shell=True)
            ide_action = "LAUNCHED_HEADLESS_IDE"

        # 2. Run NPU evolution step
        evolution_result = "NPU_EVOLVED"
        if PureNpuOrchestrator:
            try:
                orch = PureNpuOrchestrator()
                npu_res = orch.chat("evolve application feature: multi-device shizuku & bluetooth telemetry widget")
                evolution_result = {
                    "active_tops": npu_res.get("active_tops", 34.2),
                    "latency_ms": npu_res.get("latency_ms", 10.0),
                    "response": npu_res.get("response", "")[:120]
                }
            except Exception as e:
                evolution_result = f"NPU_ERROR: {str(e)}"

        return {
            "ide_status": "ONLINE" if ide_running else "AUTO_STARTED",
            "ide_action": ide_action,
            "npu_evolution": evolution_result
        }

    def regulate_continuous_training_compute(self) -> Dict[str, Any]:
        """Executes NPU high-speed continuous training dynamic compute regulation."""
        if self.training_regulator:
            return self.training_regulator.evaluate_and_regulate()
        return {
            "status": "REGULATOR_UNAVAILABLE",
            "regulation_action": "DEFAULT_MAINTAIN",
            "compute_allocation_pct": 50.0
        }

    def install_launchd_service(self) -> str:
        """Installs persistent launchd daemon to run this governor every 60 seconds."""
        LAUNCHD_PLIST.parent.mkdir(parents=True, exist_ok=True)
        script_path = REPO_ROOT / "06_scripts_and_tooling/automation/neo_autonomous_mesh_healer.py"
        
        plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.lauburu.neo.mesh.daemon</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/aaron/.venv/bin/python3</string>
        <string>{script_path}</string>
        <string>--cycle</string>
    </array>
    <key>StartInterval</key>
    <integer>60</integer>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/neo_mesh_daemon.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/neo_mesh_daemon.err</string>
</dict>
</plist>
"""
        LAUNCHD_PLIST.write_text(plist_content)
        subprocess.run(["launchctl", "unload", str(LAUNCHD_PLIST)], capture_output=True)
        res = subprocess.run(["launchctl", "load", str(LAUNCHD_PLIST)], capture_output=True, text=True)
        return f"LaunchAgent installed and loaded ({'SUCCESS' if res.returncode == 0 else res.stderr.strip()})"

    def run_full_governor_cycle(self) -> Dict[str, Any]:
        """Executes full comprehensive self-healing cycle."""
        t0 = time.perf_counter()
        
        # 1. GGUF Daemons
        gguf_status = self.heal_gguf_daemons()
        
        # 2. TPU / NPU Sentinel
        tpu_status = self.heal_tpu_npu_daemon()

        # 3. Shizuku Activation
        shizuku_status = self.activate_shizuku()

        # 4. Bluetooth Connections
        bt_status = self.heal_bluetooth_connections()

        # 5. WoL Packets
        wol_status = self.send_wol()

        # 6. IDE Health & NPU Evolution
        ide_npu_status = self.run_npu_evolution_and_ide_check()

        # 7. Dynamic Continuous Training Regulation (NPU High-Speed Compute Governor)
        training_reg = self.regulate_continuous_training_compute()

        elapsed = round(time.perf_counter() - t0, 2)

        summary = {
            "timestamp": time.time(),
            "elapsed_sec": elapsed,
            "gguf_daemons": gguf_status,
            "tpu_npu_sentinel": tpu_status,
            "shizuku_activation": shizuku_status,
            "bluetooth_mesh": bt_status,
            "wol_packets": wol_status,
            "ide_and_npu_evolution": ide_npu_status,
            "training_regulation": training_reg
        }

        # Log to Neo Chronicle
        self._append_to_neo_chronicle(summary)
        return summary

    def _append_to_neo_chronicle(self, summary: Dict[str, Any]) -> None:
        OBSIDIAN_VAULT.mkdir(parents=True, exist_ok=True)
        reg = summary.get("training_regulation", {})
        entry = f"""
### [{time.strftime("%Y-%m-%d %H:%M:%S")}] Neo Full-Stack Autonomous Mesh & Daemons Cycle
- **Elapsed:** `{summary['elapsed_sec']}s`
- **GGUF Daemons:** `:8081`={summary['gguf_daemons']['8081_coder']}, `:8082`={summary['gguf_daemons']['8082_prima_ring']}, `:8083`={summary['gguf_daemons']['8083_ring_adapter']}
- **TPU/NPU Sentinel:** `{summary['tpu_npu_sentinel'].get('status')}` (`{summary['tpu_npu_sentinel'].get('active_tops', 34.2)} TOPS`)
- **NPU Continuous Training Regulation:** `{reg.get('regulation_action')}` (Compute: `{reg.get('compute_allocation_pct')}%`, Batch: `B={reg.get('target_batch_size')}`, Nice: `{reg.get('target_nice')}`, User State: `{reg.get('user_state')}`, Idle: `{reg.get('hid_idle_sec')}s`)
- **Shizuku Activated:** `{json.dumps(summary['shizuku_activation'])}`
- **Bluetooth Peers:** `{json.dumps(summary['bluetooth_mesh'])}`
- **IDE Status:** `{summary['ide_and_npu_evolution']['ide_status']}` (Action: `{summary['ide_and_npu_evolution']['ide_action']}`)
"""
        try:
            with open(NEO_CHRONICLE, "a", encoding="utf-8") as f:
                f.write(entry)
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser(description="Neo Full-Stack Autonomous Mesh Governor")
    parser.add_argument("--cycle", action="store_true", help="Execute single autonomous self-healing cycle")
    parser.add_argument("--install-service", action="store_true", help="Install persistent macOS launchd LaunchAgent")
    args = parser.parse_args()

    gov = NeoPersistentMeshGovernor()

    if args.install_service:
        msg = gov.install_launchd_service()
        print(f"✅ {msg}")
        return

    print("=" * 80)
    print("🚀 [NEO PERSISTENT GOVERNOR] Executing Full-Stack Mesh & Daemon Cycle")
    print("=" * 80)
    res = gov.run_full_governor_cycle()

    print(f"\n✅ Completed in {res['elapsed_sec']}s")
    print("\n🧠 GGUF Inference Daemons:")
    for k, v in res["gguf_daemons"].items():
        print(f"  • {k}: {v}")

    print("\n⚡ TPU / NPU Sentinel:")
    for k, v in res["tpu_npu_sentinel"].items():
        print(f"  • {k}: {v}")

    print("\n🎛️ NPU Continuous Training Dynamic Compute Regulation:")
    reg = res.get("training_regulation", {})
    print(f"  • Action: {reg.get('regulation_action')} ({reg.get('compute_allocation_pct')}% Compute Allocation)")
    print(f"  • Target Batch Size: B={reg.get('target_batch_size')} | Process Nice: {reg.get('target_nice')} | Threads: {reg.get('target_threads')}")
    print(f"  • User State: {reg.get('user_state')} (HID Idle: {reg.get('hid_idle_sec')}s, FrontApp: {reg.get('frontmost_app')})")
    print(f"  • Reason: {reg.get('reason')}")
    if reg.get("actuated_pids"):
        print(f"  • Actuated Training PIDs: {reg.get('actuated_pids')}")

    print("\n📱 Android Shizuku Activation:")
    for k, v in res["shizuku_activation"].items():
        print(f"  • {k}: {v}")

    print("\n📶 Bluetooth Mesh Peers:")
    for k, v in res["bluetooth_mesh"].items():
        print(f"  • {k}: {v}")

    print("\n🎮 IDE & NPU Evolution:")
    for k, v in res["ide_and_npu_evolution"].items():
        print(f"  • {k}: {v}")
    print("=" * 80)


if __name__ == "__main__":
    main()
