#!/usr/bin/env python3
"""
================================================================================
Screen Lens Sovereign — Android Dependency Daemon
================================================================================
Subsystem: 01_apps/screen_lens/src/lens_android_dependency_daemon.py
Version: 1.0.0-ANDROID-DEP-DAEMON

24/7 daemon that ensures Shizuku + all tool-use dependencies are alive on
BOTH Android devices: Samsung Galaxy S20 (L7) and Pixel 10 Pro XL (L6).

Per Screen Lens Skill §8 (24/7 Autonomous Dependency Lifecycle):
  Tier 0: Bluetooth/IP heartbeat
  Tier 1: Shizuku self-bootstrap
  Tier 2: Android OS keepalive / anti-Doze
  Tier 3: Zero-prompt silent package install via rish

Governed by:
  Rule #0: Zero-mock — all health probes are real syscalls
  Rule #9: No schedule tool polling — pure native daemon loop
  Rule #10: Linux Mini first-offload invariant
================================================================================
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ── Paths ──────────────────────────────────────────────────────────────────
REPO = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
LORA = REPO / "lora_datasets" / "continuous_lora_dataset.jsonl"
VAULT = REPO / "obsidian_vault" / "APPS_AND_FEATURES" / "ANDROID_DEPENDENCY_DAEMON.md"
LOG_FILE = Path("/tmp/lens_android_dep_daemon.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [AndroidDep] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(str(LOG_FILE), mode="a"),
    ],
)
log = logging.getLogger("AndroidDepDaemon")

# ── Device Configuration ────────────────────────────────────────────────────
DEVICES: Dict[str, Dict] = {
    "s20": {
        "name": "Samsung Galaxy S20 (L7)",
        "ips": ["192.168.8.101", "192.168.8.131", "192.168.8.157", "100.84.40.95"],
        "port": 5555,
        "tls_transport": 3405,
        "rish_base": "/data/local/tmp/rish_dir",
        "rish_app_id": "com.android.shell",
        "shizuku_starter": "/data/local/tmp/shizuku_starter",
        "shizuku_start_sh": "/sdcard/Android/data/moe.shizuku.privileged.api/files/start.sh",
        "termux_boot": "/data/data/com.termux/files/home/.termux/boot/lauburu_boot.sh",
        # S20 Samsung Android 13: must re-whitelist com.android.shell before each rish call
        "pre_rish_cmds": ["dumpsys deviceidle whitelist +com.android.shell"],
    },
    "pixel": {
        "name": "Pixel 10 Pro XL (L6)",
        "ips": ["192.168.8.116", "192.168.8.213", "100.114.215.68", "192.168.8.114", "192.168.8.163"],
        "port": 5555,
        "tls_transport": None,
        "rish_base": "/data/local/tmp/pix_rish_dir",
        "rish_app_id": "com.android.shell",
        "shizuku_starter": "/data/local/tmp/shizuku_starter",
        "shizuku_start_sh": "/sdcard/Android/data/moe.shizuku.privileged.api/files/start.sh",
        "termux_boot": "/data/data/com.termux/files/home/.termux/boot/lauburu_boot.sh",
        "pre_rish_cmds": ["dumpsys deviceidle whitelist +com.android.shell"],
    },
}

CRITICAL_PACKAGES = [
    "com.android.shell",
    "com.termux",
    "moe.shizuku.privileged.api",
    "com.wireguard.android",
]

BOOT_SCRIPT_TEMPLATE = """\
#!/data/data/com.termux/files/usr/bin/bash
# Lauburu {device} Termux Boot — Auto-managed by lens_android_dependency_daemon.py
termux-wake-lock 2>/dev/null||true
sshd 2>/dev/null||true
settings put system screen_off_timeout 3600000 2>/dev/null||true
settings put global settings_enable_monitor_phantom_procs false 2>/dev/null||true
echo "$(date): Lauburu boot complete [{device}]" >> /sdcard/lauburu_boot.log
"""

# ── ADB Helper ──────────────────────────────────────────────────────────────
# Full path required — LaunchAgent environment has limited PATH
ADB_PATH = (
    os.environ.get("ADB_PATH") or
    "/Users/aaron/.local/bin/adb"
)
# Verify at startup
if not os.path.exists(ADB_PATH):
    for candidate in [
        "/Users/aaron/android-sdk/platform-tools/adb",
        "/opt/homebrew/bin/adb",
        "/usr/local/bin/adb",
    ]:
        if os.path.exists(candidate):
            ADB_PATH = candidate
            break

log.info(f"ADB binary: {ADB_PATH}")

def adb(device_serial: str, *args, timeout: int = 15) -> subprocess.CompletedProcess:
    cmd = [ADB_PATH, "-s", device_serial] + list(args)
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

def adb_t(transport_id: int, *args, timeout: int = 15) -> subprocess.CompletedProcess:
    cmd = [ADB_PATH, "-t", str(transport_id)] + list(args)
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

def resolve_device(dev: Dict) -> Optional[str]:
    """
    Resolve the live ADB serial for a device using dynamic discovery and the mesh IP matrix.
    Returns serial string or None.
    """
    # 0. Check already connected adb devices first (dynamic wireless ADB discovery)
    try:
        r = subprocess.run([ADB_PATH, "devices", "-l"], capture_output=True, text=True, timeout=3)
        if r.returncode == 0:
            for line in r.stdout.splitlines():
                if "device" in line and not line.startswith("List of"):
                    serial = line.split()[0]
                    name_lower = dev["name"].lower()
                    if ("s20" in name_lower and ("SM_G986" in line or "y2s" in line or any(ip in serial for ip in dev["ips"]))) or \
                       ("pixel" in name_lower and ("Pixel" in line or "komodo" in line or any(ip in serial for ip in dev["ips"]))):
                        # Quick validation
                        test_r = subprocess.run(
                            [ADB_PATH, "-s", serial, "shell", "echo", "ALIVE"],
                            capture_output=True, text=True, timeout=3
                        )
                        if test_r.returncode == 0 and "ALIVE" in test_r.stdout:
                            return serial
    except Exception:
        pass

    # Try each IP in order
    for ip in dev["ips"]:
        serial = f"{ip}:{dev['port']}"
        r = subprocess.run(
            [ADB_PATH, "-s", serial, "shell", "echo", "ALIVE"],
            capture_output=True, text=True, timeout=3
        )
        if r.returncode == 0 and "ALIVE" in r.stdout:
            return serial

    # Try TLS transport (S20 mDNS)
    if dev.get("tls_transport"):
        r = adb_t(dev["tls_transport"], "shell", "echo", "ALIVE_TLS")
        if r.returncode == 0 and "ALIVE_TLS" in r.stdout:
            return f"tls:{dev['tls_transport']}"

    return None

def adb_run(serial: str, *args, timeout: int = 15) -> subprocess.CompletedProcess:
    """Run adb with resolved serial (handles tls: prefix)."""
    if serial.startswith("tls:"):
        tid = int(serial.split(":")[1])
        return adb_t(tid, *args, timeout=timeout)
    return adb(serial, *args, timeout=timeout)

# ── Shizuku Health ───────────────────────────────────────────────────────────
def test_rish(serial: str, dev: Dict) -> bool:
    """Test if rish is responsive (UID 2000 shell) — all in one adb shell call."""
    rish = dev["rish_base"] + "/rish"
    app_id = dev["rish_app_id"]

    # Chain: pre_rish_cmds + rish invocation in a SINGLE shell session
    pre = "; ".join(dev.get("pre_rish_cmds", []))
    env_cmd = f"RISH_APPLICATION_ID={app_id} BASEDIR={dev['rish_base']} {rish} -c 'echo RISH_ALIVE; id'"
    full_cmd = f"{pre}; {env_cmd}" if pre else env_cmd
    r = adb_run(serial, "shell", full_cmd, timeout=20)
    return "RISH_ALIVE" in r.stdout and "uid=2000" in r.stdout


def start_shizuku(serial: str, dev: Dict) -> bool:
    """Launch Shizuku permanently disabled per user request."""
    log.info(f"[{dev.get('name', serial)}] Shizuku auto-launch disabled per user request. Skipping.")
    return False

# ── OS Keepalive ─────────────────────────────────────────────────────────────
def enforce_keepalive(serial: str) -> None:
    """Enforce anti-Doze, screen timeout, phantom process killer off."""
    cmds = [
        "settings put global settings_enable_monitor_phantom_procs false",
        "settings put system screen_off_timeout 3600000",
        "cmd appops set com.termux RUN_IN_BACKGROUND allow",
        "cmd appops set com.android.shell RUN_IN_BACKGROUND allow",
        "input keyevent KEYCODE_WAKEUP",
    ]
    for cmd in cmds:
        adb_run(serial, "shell", cmd, timeout=8)

    # Whitelist all critical packages
    for pkg in CRITICAL_PACKAGES:
        adb_run(serial, "shell", f"dumpsys deviceidle whitelist +{pkg}", timeout=8)

def ensure_boot_script(serial: str, dev: Dict) -> bool:
    """Write Termux boot script if missing. Uses rish for privileged file access."""
    boot_path = dev["termux_boot"]
    boot_dir = "/".join(boot_path.split("/")[:-1])
    rish = dev["rish_base"] + "/rish"
    app_id = dev["rish_app_id"]
    pre = "; ".join(dev.get("pre_rish_cmds", []))

    # Check via rish (privileged — Termux dir is restricted from adb shell)
    check_cmd = f"RISH_APPLICATION_ID={app_id} BASEDIR={dev['rish_base']} {rish} -c '[ -f {boot_path} ] && echo EXISTS || echo MISSING'"
    full_check = f"{pre}; {check_cmd}" if pre else check_cmd
    r = adb_run(serial, "shell", full_check, timeout=20)
    if "EXISTS" in r.stdout:
        return True

    # Write boot script via rish
    content_lines = [
        "#!/data/data/com.termux/files/usr/bin/bash",
        "termux-wake-lock 2>/dev/null||true",
        "sshd 2>/dev/null||true",
        "settings put system screen_off_timeout 3600000 2>/dev/null||true",
        "settings put global settings_enable_monitor_phantom_procs false 2>/dev/null||true",
    ]
    printf_cmds = "\n".join(
        f'printf "%s\\n" "{line}" >> {boot_path}' for line in content_lines
    )
    write_cmd = (
        f"RISH_APPLICATION_ID={app_id} BASEDIR={dev['rish_base']} {rish} -c '"
        f"mkdir -p {boot_dir}; {printf_cmds}; chmod 755 {boot_path}; echo WRITTEN'"
    )
    full_write = f"{pre}; {write_cmd}" if pre else write_cmd
    r2 = adb_run(serial, "shell", full_write, timeout=25)
    return "WRITTEN" in r2.stdout

# ── Chrome Remote Debugging ──────────────────────────────────────────────────
def setup_chrome_cdp_forward(serial: str, local_port: int) -> bool:
    """Forward Android Chrome DevTools to local port."""
    r = subprocess.run(
        [ADB_PATH, "-s", serial.replace("tls:", ""), "forward",
         f"tcp:{local_port}", "localabstract:chrome_devtools_remote"],
        capture_output=True, text=True, timeout=10
    )
    if r.returncode == 0:
        # Verify
        import urllib.request
        try:
            with urllib.request.urlopen(f"http://localhost:{local_port}/json/version", timeout=2) as resp:
                ver = json.loads(resp.read())
                log.info(f"Android Chrome CDP port {local_port}: {ver.get('Browser', '?')}")
                return True
        except Exception:
            log.debug(f"Chrome CDP port {local_port} forwarded but Chrome not open on device")
            return True  # Forward succeeded, Chrome just not open
    return False

# ── LoRA Logging ─────────────────────────────────────────────────────────────
def log_to_lora(device_name: str, action: str, result: str, success: bool) -> None:
    LORA.parent.mkdir(parents=True, exist_ok=True)
    pair = {
        "instruction": f"Maintain Shizuku and tool dependencies on {device_name}",
        "input": json.dumps({"action": action, "device": device_name, "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}),
        "output": json.dumps({"result": result, "success": success}),
    }
    with open(LORA, "a") as f:
        f.write(json.dumps(pair) + "\n")

def log_to_vault(msg: str) -> None:
    VAULT.parent.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(VAULT, "a") as f:
        f.write(f"\n### {ts}\n{msg}\n")

# ── Per-Device Health Check Cycle ─────────────────────────────────────────────
def health_cycle(dev_key: str, dev: Dict) -> Dict:
    """Run one full health check + heal cycle for a device. Returns status dict."""
    status = {
        "device": dev_key,
        "name": dev["name"],
        "reachable": False,
        "serial": None,
        "rish_ok": False,
        "keepalive_enforced": False,
        "boot_script_ok": False,
        "chrome_cdp_forwarded": False,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    # 1. Resolve device connection
    serial = resolve_device(dev)
    if not serial:
        log.warning(f"[{dev_key}] OFFLINE — no reachable IP/transport")
        log_to_lora(dev["name"], "resolve", "OFFLINE", False)
        return status

    status["reachable"] = True
    status["serial"] = serial
    log.info(f"[{dev_key}] Reachable via {serial}")

    # 2. Enforce OS keepalive (anti-Doze, screen on, phantom killer off)
    enforce_keepalive(serial)
    status["keepalive_enforced"] = True

    # 3. Ensure Termux boot script
    boot_ok = ensure_boot_script(serial, dev)
    status["boot_script_ok"] = boot_ok
    if boot_ok:
        log.info(f"[{dev_key}] Boot script OK")
    else:
        log.warning(f"[{dev_key}] Boot script missing/failed")

    # 4. Check Shizuku / rish
    rish_ok = test_rish(serial, dev)
    if rish_ok:
        log.info(f"[{dev_key}] rish ✅ ACTIVE uid=2000")
        status["rish_ok"] = True
        log_to_lora(dev["name"], "rish_check", "uid=2000_ACTIVE", True)
    else:
        log.info(f"[{dev_key}] rish NOT running — Shizuku auto-restart disabled per user request")
        status["rish_ok"] = False

    # 5. Set up Chrome remote debugging forwarding
    port_map = {"s20": 9223, "pixel": 9224}
    local_port = port_map.get(dev_key, 9225)
    # Only forward if serial is not TLS (ADB forward needs serial, not transport)
    if not serial.startswith("tls:"):
        cdp_ok = setup_chrome_cdp_forward(serial, local_port)
        status["chrome_cdp_forwarded"] = cdp_ok

    return status

# ── Main Daemon Loop ─────────────────────────────────────────────────────────
def run_daemon(interval_seconds: int = 60) -> None:
    """Main 24/7 daemon loop. Checks both devices every `interval_seconds`."""
    log.info("=" * 60)
    log.info("Lens Android Dependency Daemon starting...")
    log.info(f"Monitoring: {list(DEVICES.keys())}")
    log.info(f"Check interval: {interval_seconds}s")
    log.info("=" * 60)

    log_to_vault("## Lens Android Dependency Daemon Started\n"
                 f"- Devices: {list(DEVICES.keys())}\n"
                 f"- Interval: {interval_seconds}s\n"
                 f"- PID: {os.getpid()}\n")

    cycle = 0
    while True:
        cycle += 1
        log.info(f"\n{'='*50}\nCycle #{cycle} — {time.strftime('%Y-%m-%d %H:%M:%S')}\n{'='*50}")

        all_status = {}
        for dev_key, dev in DEVICES.items():
            try:
                status = health_cycle(dev_key, dev)
                all_status[dev_key] = status
            except Exception as e:
                log.error(f"[{dev_key}] Health cycle error: {e}")
                all_status[dev_key] = {"device": dev_key, "error": str(e)}

        # Summary log
        summary_lines = [f"\n### Cycle #{cycle} — {time.strftime('%Y-%m-%d %H:%M:%S')}"]
        for dev_key, st in all_status.items():
            icon = "✅" if st.get("rish_ok") else "❌"
            summary_lines.append(
                f"- {icon} **{dev_key}**: "
                f"reachable={st.get('reachable')}, "
                f"rish={st.get('rish_ok')}, "
                f"boot={st.get('boot_script_ok')}, "
                f"cdp={st.get('chrome_cdp_forwarded')}"
            )
        log_to_vault("\n".join(summary_lines))
        log.info("Cycle complete. Sleeping %ds...", interval_seconds)

        # Write state to JSON for other processes to read
        state_path = Path("/tmp/lens_android_dep_state.json")
        state_path.write_text(json.dumps(all_status, indent=2))

        time.sleep(interval_seconds)


# ── One-shot status check ────────────────────────────────────────────────────
def run_status() -> None:
    """Single status check of both devices."""
    print(json.dumps({
        k: health_cycle(k, v)
        for k, v in DEVICES.items()
    }, indent=2))


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Lens Android Dependency Daemon")
    p.add_argument("command", nargs="?", default="daemon",
                   choices=["daemon", "status", "heal-s20", "heal-pixel"])
    p.add_argument("--interval", type=int, default=60)
    args = p.parse_args()

    if args.command == "daemon":
        run_daemon(args.interval)
    elif args.command == "status":
        run_status()
    elif args.command == "heal-s20":
        serial = resolve_device(DEVICES["s20"])
        if serial:
            enforce_keepalive(serial)
            ok = start_shizuku(serial, DEVICES["s20"])
            print(f"S20 Shizuku heal: {'OK' if ok else 'FAILED'}")
        else:
            print("S20 OFFLINE")
    elif args.command == "heal-pixel":
        serial = resolve_device(DEVICES["pixel"])
        if serial:
            enforce_keepalive(serial)
            ok = start_shizuku(serial, DEVICES["pixel"])
            print(f"Pixel Shizuku heal: {'OK' if ok else 'FAILED'}")
        else:
            print("Pixel OFFLINE")
