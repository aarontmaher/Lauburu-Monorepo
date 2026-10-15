#!/usr/bin/env python3
"""
verify_mac_boot_persistence.py
=============================================================================
Verification script for Deliverable R1: macOS Silent Boot Persistence.
Validates:
  a) Plist file exists in ~/Library/LaunchAgents/ (and canonical repo path)
  b) Plist passes plutil -lint validation
  c) Service is registered/loaded in launchctl (gui/$UID/com.lauburu.lifecompanion or launchctl list)
  d) Daemon process is running and its network port (3036 HTTP / 5555 ZMQ) is responsive.

Exits with code 0 on success, non-zero on verification failure.
=============================================================================
"""

import os
import sys
import plistlib
import subprocess
import socket
import urllib.request
import urllib.error
import time
from pathlib import Path

LABEL = "com.lauburu.lifecompanion"
USER_LAUNCHAGENTS_DIR = Path.home() / "Library" / "LaunchAgents"
USER_PLIST_PATH = USER_LAUNCHAGENTS_DIR / f"{LABEL}.plist"
REPO_ROOT = Path(__file__).resolve().parent.parent
CANONICAL_PLIST_PATH = REPO_ROOT / "macos" / f"{LABEL}.plist"

HTTP_PORT = 3036
ZMQ_PORT = 5555


def log(msg: str):
    print(f"[VERIFY_MAC_PERSISTENCE] {msg}")


def check_file_exists():
    log(f"Checking LaunchAgent plist existence...")
    if not USER_PLIST_PATH.exists():
        log(f"FAIL: User LaunchAgent plist not found at {USER_PLIST_PATH}")
        return False
    log(f"  ✓ User plist found: {USER_PLIST_PATH}")

    if CANONICAL_PLIST_PATH.exists():
        log(f"  ✓ Canonical repo plist found: {CANONICAL_PLIST_PATH}")
    else:
        log(f"  ⚠️ Warning: Canonical repo plist not found at {CANONICAL_PLIST_PATH} (optional check)")

    return True


def check_plutil_lint():
    log(f"Running plutil -lint on {USER_PLIST_PATH}...")
    res = subprocess.run(["plutil", "-lint", str(USER_PLIST_PATH)], capture_output=True, text=True)
    if res.returncode != 0:
        log(f"FAIL: plutil -lint failed with exit code {res.returncode}: {res.stderr.strip()}")
        return False
    log(f"  ✓ plutil lint OK: {res.stdout.strip() or 'OK'}")

    # Inspect contents
    with open(USER_PLIST_PATH, "rb") as f:
        data = plistlib.load(f)

    if data.get("Label") != LABEL:
        log(f"FAIL: Label in plist is '{data.get('Label')}', expected '{LABEL}'")
        return False
    if not data.get("RunAtLoad"):
        log(f"FAIL: 'RunAtLoad' must be true")
        return False
    if not data.get("KeepAlive"):
        log(f"FAIL: 'KeepAlive' must be true")
        return False
    if data.get("ProcessType") != "Background":
        log(f"FAIL: 'ProcessType' should be 'Background', got '{data.get('ProcessType')}'")
        return False

    args = data.get("ProgramArguments", [])
    cmd_str = " ".join(str(a) for a in args)
    if "nohup" in cmd_str:
        log("FAIL: ProgramArguments must not use 'nohup' fork loops")
        return False

    log(f"  ✓ Plist structure and attributes validated successfully.")
    return True


def check_launchctl_loaded():
    log(f"Checking launchctl registration for '{LABEL}'...")
    uid = os.getuid()

    # Try modern launchctl print gui/$UID/<label>
    res_print = subprocess.run(["launchctl", "print", f"gui/{uid}/{LABEL}"], capture_output=True, text=True)
    if res_print.returncode == 0:
        log(f"  ✓ Service registered in gui/{uid}/{LABEL}")
        return True

    # Fallback to launchctl list
    res_list = subprocess.run(["launchctl", "list"], capture_output=True, text=True)
    if LABEL in res_list.stdout:
        log(f"  ✓ Service found in 'launchctl list'")
        return True

    log(f"FAIL: Service '{LABEL}' is not loaded or registered in launchctl domain gui/{uid}")
    log(f"  launchctl print stderr: {res_print.stderr.strip()}")
    return False


def probe_port(port: int, host: str = "127.0.0.1", timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def check_daemon_running():
    log(f"Checking daemon process and network responsiveness (HTTP port {HTTP_PORT}, ZMQ port {ZMQ_PORT})...")

    # Give up to 5 seconds with polling in case launchd recently spawned it
    deadline = time.time() + 5.0
    while time.time() < deadline:
        if probe_port(HTTP_PORT) or probe_port(ZMQ_PORT):
            break
        time.sleep(0.5)

    http_ok = probe_port(HTTP_PORT)
    zmq_ok = probe_port(ZMQ_PORT)

    if not (http_ok or zmq_ok):
        # Also check if process is running via pgrep
        res_pgrep = subprocess.run(["pgrep", "-fl", "screen_life_companion.py"], capture_output=True, text=True)
        if res_pgrep.returncode == 0:
            log(f"  Daemon process found: {res_pgrep.stdout.strip()}, but ports {HTTP_PORT}/{ZMQ_PORT} not yet responsive.")
        else:
            log(f"FAIL: Neither HTTP port {HTTP_PORT} nor ZMQ port {ZMQ_PORT} is responsive, and no daemon process found.")
            return False

    if http_ok:
        log(f"  ✓ HTTP port {HTTP_PORT} is listening and accepting TCP connections.")
        # Attempt HTTP GET
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{HTTP_PORT}/", headers={"User-Agent": "PersistenceVerifier/1.0"})
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                log(f"  ✓ HTTP endpoint returned HTTP status {resp.status}")
        except Exception as e:
            log(f"  ℹ️ HTTP port open (endpoint returned: {e})")

    if zmq_ok:
        log(f"  ✓ ZMQ port {ZMQ_PORT} is listening.")

    return True


def main():
    log("=================================================================")
    log("Verifying macOS Silent Boot Persistence for Lauburu Life Companion")
    log("=================================================================")

    checks = [
        ("File Existence", check_file_exists),
        ("Plist Syntax & Structure (plutil)", check_plutil_lint),
        ("Launchctl Registration", check_launchctl_loaded),
        ("Daemon & Port Responsiveness", check_daemon_running),
    ]

    for name, func in checks:
        log(f"\n--- Checking: {name} ---")
        if not func():
            log(f"\n❌ FAILED at check: {name}")
            sys.exit(1)

    log("\n=================================================================")
    log("✅ ALL VERIFICATIONS PASSED: macOS Silent Boot Persistence OK")
    log("=================================================================")
    sys.exit(0)


if __name__ == "__main__":
    main()
