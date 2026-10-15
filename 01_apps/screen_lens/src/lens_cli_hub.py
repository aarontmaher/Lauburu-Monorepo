#!/usr/bin/env python3
"""
lens_cli_hub.py — Lauburu Lens Unified CLI Hub
================================================
Wraps: LuCI CLI, GL.iNet CLI, ADB CLI, Android CLI, F-Droid CLI,
       Shizuku, Scrcpy GUI control, Magisk/Sui evaluation

Usage:
  python3 lens_cli_hub.py <command> [args...]

Commands:
  router <uci|status|wg|restart>  — GL.iNet router CLI
  adb <serial> <shell|forward|install|...>  — ADB with mesh fallback
  android <device> <wake|screen|prop|settings>  — Android higher-level ops
  fdroid <device> <search|install|update>  — F-Droid headless APK install
  shizuku <device> <status|start|rish>  — Shizuku management
  scrcpy <device> [scrcpy_args...]  — Launch scrcpy with device
  magisk <device>  — Evaluate Magisk/Sui/root status
  status  — Full mesh status report
  daemon  — Start 24/7 heal daemon (wraps lens_android_dependency_daemon.py)
"""

import os, sys, subprocess, json, time, socket, logging, shlex
from typing import Optional, Dict, List, Tuple

# ── Canonical paths ──────────────────────────────────────────────────────────
ADB_PATH = (
    os.environ.get("ADB_PATH") or
    "/Users/aaron/.local/bin/adb"
)
for _c in ["/Users/aaron/android-sdk/platform-tools/adb", "/opt/homebrew/bin/adb"]:
    if not os.path.exists(ADB_PATH) and os.path.exists(_c):
        ADB_PATH = _c

GLINET_PATH = next((
    p for p in [
        "/Users/aaron/.local/bin/glinet",
        "/usr/local/bin/glinet",
        "/opt/homebrew/bin/glinet",
    ] if os.path.exists(p)
), "glinet")

SCRCPY_PATH = next((
    p for p in [
        "/Users/aaron/.local/bin/scrcpy",
        "/opt/homebrew/bin/scrcpy",
        "/usr/local/bin/scrcpy",
    ] if os.path.exists(p)
), "scrcpy")

FDROIDCL_PATH = next((
    p for p in [
        "/opt/homebrew/bin/fdroidcl",
        "/usr/local/bin/fdroidcl",
        os.path.expanduser("~/go/bin/fdroidcl"),
        "/Users/aaron/.local/bin/fdroidcl",
    ] if os.path.exists(p)
), "fdroidcl")

MONOREPO = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo"
ROUTER_IP = "192.168.8.1"
ROUTER_SSH = f"root@{ROUTER_IP}"

# ── Mesh device registry ─────────────────────────────────────────────────────
MESH_DEVICES: Dict[str, Dict] = {
    "s20": {
        "name": "Samsung Galaxy S20+ (L7)",
        "ips": ["192.168.8.157", "192.168.8.134", "192.168.8.131", "100.84.40.95"],
        "port": 5555,
        "tls_transport": 3619,
        "rish_base": "/data/local/tmp/rish_dir",
        "rish_app_id": "com.android.shell",
        "shizuku_starter": "/data/local/tmp/shizuku_starter",
        "scrcpy_extra": ["--max-size=1080", "--bit-rate=4M"],
    },
    "pixel": {
        "name": "Pixel 10 Pro XL (L6)",
        "ips": ["192.168.8.114", "192.168.8.163", "192.168.8.213", "100.73.38.87"],
        "port": 5555,
        "tls_transport": None,
        "rish_base": "/data/local/tmp/pix_rish_dir",
        "rish_app_id": "com.android.shell",
        "shizuku_starter": "/data/local/tmp/shizuku_starter",
        "scrcpy_extra": ["--max-size=1440", "--bit-rate=8M"],
    },
}

log = logging.getLogger("LensHub")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [LensHub] %(levelname)s: %(message)s",
)

# ═══════════════════════════════════════════════════════════════════════════════
# ADB HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def adb(*args, serial: str = None, transport: int = None,
        timeout: int = 15) -> subprocess.CompletedProcess:
    """Run ADB with optional serial or transport ID."""
    cmd = [ADB_PATH]
    if transport is not None:
        cmd += ["-t", str(transport)]
    elif serial:
        cmd += ["-s", serial]
    cmd += list(args)
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

def resolve_adb_serial(device_key: str) -> Optional[str]:
    """Resolve device key to working ADB serial using mesh IP matrix and active ADB devices."""
    dev = MESH_DEVICES.get(device_key)
    if not dev:
        return None
    # 0. Check already-connected ADB devices first!
    try:
        proc = subprocess.run([ADB_PATH, "devices", "-l"], capture_output=True, text=True, timeout=3)
        if proc.returncode == 0:
            for line in proc.stdout.splitlines():
                if "device" in line and not line.startswith("List of"):
                    parts = line.split()
                    if parts:
                        ser = parts[0]
                        line_lower = line.lower()
                        # Match S20
                        if device_key == "s20" and any(k in line_lower for k in ["sm-g986", "sm_g986", "y2s", "s20"]):
                            return ser
                        # Match Pixel
                        if device_key == "pixel" and any(k in line_lower for k in ["pixel", "cheetah", "husky", "tokay", "komodo"]):
                            return ser
    except Exception:
        pass

    # Try each IP
    for ip in dev["ips"]:
        serial = f"{ip}:{dev['port']}"
        r = adb("shell", "echo", "ALIVE", serial=serial, timeout=3)
        if r.returncode == 0 and "ALIVE" in r.stdout:
            return serial
    # Try TLS transport
    tid = dev.get("tls_transport")
    if tid:
        r = adb("shell", "echo", "ALIVE_TLS", transport=tid, timeout=3)
        if r.returncode == 0 and "ALIVE_TLS" in r.stdout:
            return f"tls:{tid}"
    return None

def rish_cmd(device_key: str, cmd: str, timeout: int = 20) -> str:
    """Run a command via Shizuku rish (UID=2000 shell)."""
    dev = MESH_DEVICES.get(device_key, {})
    serial = resolve_adb_serial(device_key)
    if not serial:
        # Fallback to direct SSH bridge per Rule 9 Multi-IP Fallback
        if device_key == "pixel":
            try:
                r = subprocess.run(
                    ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=5", "pixel", f"~/bin/rish -c {shlex.quote(cmd)}"],
                    capture_output=True, text=True, timeout=timeout
                )
                if r.returncode == 0:
                    return r.stdout.strip()
                elif r.stderr.strip():
                    return f"ERROR: {r.stderr.strip()}"
            except Exception as e:
                log.warning(f"SSH rish fallback failed: {e}")
        return f"ERROR: {device_key} unreachable"
    rish = dev["rish_base"] + "/rish"
    app_id = dev["rish_app_id"]
    full = (
        f"dumpsys deviceidle whitelist +com.android.shell 2>/dev/null; "
        f"RISH_APPLICATION_ID={app_id} BASEDIR={dev['rish_base']} "
        f"{rish} -c '{cmd}' 2>&1"
    )
    if serial.startswith("tls:"):
        r = adb("shell", full, transport=int(serial.split(":")[1]), timeout=timeout)
    else:
        r = adb("shell", full, serial=serial, timeout=timeout)
    return r.stdout.strip()

# ═══════════════════════════════════════════════════════════════════════════════
# ROUTER CLI (GL.iNet LuCI/UCI via SSH)
# ═══════════════════════════════════════════════════════════════════════════════

def router_ssh(cmd: str, timeout: int = 15) -> str:
    """Run a command on the GL.iNet router via SSH."""
    r = subprocess.run(
        ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=5",
         ROUTER_SSH, cmd],
        capture_output=True, text=True, timeout=timeout
    )
    return r.stdout.strip() or r.stderr.strip()

def cmd_router(subcmd: str, args: List[str]) -> None:
    """GL.iNet / LuCI CLI commands — uses `glinet` binary + SSH fallback."""
    def glinet(*cmd_args) -> str:
        r = subprocess.run(
            [GLINET_PATH] + list(cmd_args),
            capture_output=True, text=True, timeout=15
        )
        return r.stdout.strip() or r.stderr.strip()

    if subcmd == "status":
        print("[Router] GL.iNet Status:")
        print(glinet("status"))

    elif subcmd == "wg":
        action = args[0] if args else "status"
        if action in ("status", "show"):
            print(glinet("wg-status"))
        elif action == "peers":
            print(glinet("peers"))
        elif action == "restart":
            print(glinet("restart-wg"))
        elif action == "routing":
            print(glinet("check-routing"))
        elif action == "fix":
            print(glinet("fix-routing"))
        elif action == "client":
            client_id = args[1] if len(args) > 1 else None
            if client_id:
                print(glinet("client", client_id))
            else:
                print(glinet("peers"))
        else:
            print(glinet("wg-status"))

    elif subcmd == "peers":
        print(glinet("peers"))

    elif subcmd == "webui":
        print(glinet("webui"))

    elif subcmd == "check-routing":
        print(glinet("check-routing"))

    elif subcmd == "fix-routing":
        print(glinet("fix-routing"))

    elif subcmd == "uci":
        uci_cmd = " ".join(args) if args else "show"
        print(router_ssh(f"uci {uci_cmd}"))

    elif subcmd == "restart":
        service = args[0] if args else "network"
        if service == "wg":
            print(glinet("restart-wg"))
        else:
            print(router_ssh(f"/etc/init.d/{service} restart"))

    elif subcmd == "wifi":
        action = args[0] if args else "status"
        print(router_ssh(f"wifi {action} 2>/dev/null || iwinfo 2>/dev/null | head -20"))

    elif subcmd == "dns":
        print(router_ssh("cat /tmp/resolv.conf.auto 2>/dev/null"))
        print(router_ssh("uci show dhcp.@dnsmasq[0] 2>/dev/null"))

    elif subcmd == "logs":
        print(router_ssh("logread 2>/dev/null | tail -50"))

    elif subcmd == "tailscale":
        print(router_ssh("tailscale status 2>/dev/null || echo 'Tailscale not running'"))

    elif subcmd == "ping":
        target = args[0] if args else "8.8.8.8"
        print(router_ssh(f"ping -c 3 {target}"))

    elif subcmd == "ssh":
        cmd_to_run = " ".join(args) if args else "echo SSH_OK"
        print(router_ssh(cmd_to_run))

    else:
        print(f"Usage: router <subcmd> [args...]")
        print(f"Subcmds: status, wg [status|peers|restart|routing|fix|client], peers,")
        print(f"         webui, check-routing, fix-routing, uci <cmd>, restart <svc>,")
        print(f"         wifi, dns, logs, tailscale, ping <host>, ssh <cmd>")

# ═══════════════════════════════════════════════════════════════════════════════
# ADB CLI WRAPPER
# ═══════════════════════════════════════════════════════════════════════════════

def cmd_adb(device_key: str, args: List[str]) -> None:
    """ADB CLI with automatic mesh serial resolution."""
    serial = resolve_adb_serial(device_key)
    if not serial:
        log.error(f"Device '{device_key}' unreachable")
        return
    log.info(f"[{device_key}] serial={serial}")
    if serial.startswith("tls:"):
        r = adb(*args, transport=int(serial.split(":")[1]), timeout=60)
    else:
        r = adb(*args, serial=serial, timeout=60)
    print(r.stdout)
    if r.stderr and "Warning" not in r.stderr:
        print(r.stderr, file=sys.stderr)

# ═══════════════════════════════════════════════════════════════════════════════
# ANDROID HIGHER-LEVEL CLI
# ═══════════════════════════════════════════════════════════════════════════════

def cmd_android(device_key: str, subcmd: str, args: List[str]) -> None:
    """High-level Android device commands."""
    serial = resolve_adb_serial(device_key)
    if not serial:
        log.error(f"Device '{device_key}' unreachable")
        return

    def shell(cmd: str) -> str:
        if serial.startswith("tls:"):
            r = adb("shell", cmd, transport=int(serial.split(":")[1]), timeout=15)
        else:
            r = adb("shell", cmd, serial=serial, timeout=15)
        return r.stdout.strip()

    if subcmd == "wake":
        shell("input keyevent KEYCODE_WAKEUP")
        shell("input keyevent KEYCODE_MENU")
        print(f"[{device_key}] Screen woken")

    elif subcmd == "sleep":
        shell("input keyevent KEYCODE_SLEEP")
        print(f"[{device_key}] Screen slept")

    elif subcmd == "screenshot":
        path = args[0] if args else f"/tmp/{device_key}_screenshot.png"
        shell("screencap -p /sdcard/screen.png")
        if serial.startswith("tls:"):
            adb("pull", "/sdcard/screen.png", path, transport=int(serial.split(":")[1]))
        else:
            adb("pull", "/sdcard/screen.png", path, serial=serial)
        print(f"[{device_key}] Screenshot saved to {path}")

    elif subcmd == "prop":
        key = args[0] if args else "ro.product.model"
        print(shell(f"getprop {key}"))

    elif subcmd == "props":
        print(shell("getprop | grep -E 'ro.product|ro.build|ro.version' | head -20"))

    elif subcmd == "settings":
        ns = args[0] if args else "global"
        key = args[1] if len(args) > 1 else None
        val = args[2] if len(args) > 2 else None
        if val:
            shell(f"settings put {ns} {key} {val}")
            print(f"[{device_key}] Set {ns}.{key}={val}")
        elif key:
            print(shell(f"settings get {ns} {key}"))
        else:
            print(shell(f"settings list {ns} | head -30"))

    elif subcmd == "install":
        apk = args[0] if args else None
        if not apk:
            print("Usage: android <device> install <path.apk>")
            return
        if serial.startswith("tls:"):
            r = adb("install", "-r", apk, transport=int(serial.split(":")[1]), timeout=120)
        else:
            r = adb("install", "-r", apk, serial=serial, timeout=120)
        print(r.stdout or r.stderr)

    elif subcmd == "packages":
        filter_str = args[0] if args else ""
        pkgs = shell(f"pm list packages | grep {filter_str}" if filter_str else "pm list packages")
        print(pkgs)

    elif subcmd == "keepalive":
        cmds = [
            "settings put global settings_enable_monitor_phantom_procs false",
            "settings put system screen_off_timeout 3600000",
            "dumpsys deviceidle whitelist +com.android.shell",
            "dumpsys deviceidle whitelist +com.termux",
            "dumpsys deviceidle whitelist +moe.shizuku.privileged.api",
            "cmd appops set com.termux RUN_IN_BACKGROUND allow",
        ]
        for cmd in cmds:
            shell(cmd)
        print(f"[{device_key}] Keepalive enforced")

    elif subcmd == "wifi":
        action = args[0] if args else "status"
        if action == "on":
            shell("svc wifi enable")
        elif action == "off":
            shell("svc wifi disable")
        else:
            print(shell("dumpsys wifi | grep 'Wi-Fi is' | head -3"))
            print(shell("ip addr show wlan0 2>/dev/null | grep 'inet ' | awk '{print $2}'"))

    elif subcmd == "info":
        print(shell("getprop ro.product.model && getprop ro.build.version.release && getprop ro.build.version.sdk"))
        print(shell("free -m | head -3"))
        print(shell("df /data | tail -1"))
    else:
        print(f"Unknown android command: {subcmd}")
        print("Available: wake, sleep, screenshot, prop, props, settings, install, packages, keepalive, wifi, info")

# ═══════════════════════════════════════════════════════════════════════════════
# F-DROID CLI (fdroidcl wrapper)
# ═══════════════════════════════════════════════════════════════════════════════

def cmd_fdroid(device_key: str, subcmd: str, args: List[str]) -> None:
    """F-Droid headless APK install via fdroidcl."""
    serial = resolve_adb_serial(device_key)
    if not serial:
        log.error(f"Device '{device_key}' unreachable")
        return

    env = {**os.environ, "ADB_VENDOR_KEYS": os.path.expanduser("~/.android/")}

    # Prefer fdroidcl if available
    if os.path.exists(FDROIDCL_PATH):
        if subcmd == "update":
            print(f"[F-Droid] Updating index...")
            r = subprocess.run([FDROIDCL_PATH, "update"], capture_output=True, text=True, env=env)
            print(r.stdout or r.stderr)

        elif subcmd == "search":
            query = " ".join(args) if args else ""
            r = subprocess.run([FDROIDCL_PATH, "search", query], capture_output=True, text=True, env=env)
            print(r.stdout or r.stderr)

        elif subcmd == "install":
            app_id = args[0] if args else None
            if not app_id:
                print("Usage: fdroid <device> install <app.id>")
                return
            print(f"[F-Droid] Installing {app_id} to {device_key} ({serial})...")
            # fdroidcl installs via ADB
            r = subprocess.run(
                [FDROIDCL_PATH, "install", app_id],
                capture_output=True, text=True, env={**env, "ANDROID_SERIAL": serial}
            )
            print(r.stdout or r.stderr)

        elif subcmd == "download":
            app_id = args[0] if args else None
            if not app_id:
                print("Usage: fdroid <device> download <app.id>")
                return
            r = subprocess.run([FDROIDCL_PATH, "download", app_id], capture_output=True, text=True, env=env)
            print(r.stdout or r.stderr)

    else:
        # Fallback: direct APK install via ADB from known F-Droid APKs
        print(f"[F-Droid] fdroidcl not found at {FDROIDCL_PATH}")
        print("Install via: brew install fdroidcl  OR  go install mvdan.cc/fdroidcl@latest")
        if subcmd == "install" and args:
            app_id = args[0]
            # Known essential APKs we can sideload directly
            ESSENTIAL_APKS = {
                "org.fdroid.fdroid": "https://f-droid.org/F-Droid.apk",
                "com.wireguard.android": "https://download.wireguard.com/android-client/latest.apk",
            }
            if app_id in ESSENTIAL_APKS:
                url = ESSENTIAL_APKS[app_id]
                apk_path = f"/tmp/{app_id}.apk"
                print(f"[F-Droid] Downloading {app_id} from {url}...")
                subprocess.run(["curl", "-L", "-o", apk_path, url], check=True)
                if serial.startswith("tls:"):
                    r = adb("install", "-r", apk_path, transport=int(serial.split(":")[1]), timeout=120)
                else:
                    r = adb("install", "-r", apk_path, serial=serial, timeout=120)
                print(r.stdout or r.stderr)
            else:
                print(f"No direct download available for {app_id}. Install fdroidcl for full support.")

# ═══════════════════════════════════════════════════════════════════════════════
# SHIZUKU CLI
# ═══════════════════════════════════════════════════════════════════════════════

def cmd_shizuku(device_key: str, subcmd: str, args: List[str]) -> None:
    """Shizuku management CLI."""
    dev = MESH_DEVICES.get(device_key, {})
    serial = resolve_adb_serial(device_key)
    if not serial and device_key != "pixel":
        log.error(f"Device '{device_key}' unreachable")
        return

    def shell(cmd: str, timeout: int = 15) -> str:
        if serial:
            if serial.startswith("tls:"):
                r = adb("shell", cmd, transport=int(serial.split(":")[1]), timeout=timeout)
            else:
                r = adb("shell", cmd, serial=serial, timeout=timeout)
            return r.stdout.strip()
        elif device_key == "pixel":
            r = subprocess.run(
                ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=5", "pixel", f"~/bin/shizuku-exec {shlex.quote(cmd)}"],
                capture_output=True, text=True, timeout=timeout
            )
            return r.stdout.strip()
        return ""

    if subcmd == "status":
        print(f"[{device_key}] Shizuku status:")
        procs = shell("ps -ef | grep -E 'shizuku|moe.shizuku' | grep -v grep")
        print(procs or "No Shizuku processes found")
        rish_out = rish_cmd(device_key, "echo RISH_STATUS; id")
        print(f"rish: {'✅ ALIVE' if ('RISH_STATUS' in rish_out or 'uid=2000' in rish_out) else '❌ NOT RUNNING'}")
        if "uid=2000" in rish_out:
            print("UID: 2000 (ADB shell) ✅")

    elif subcmd == "start":
        print(f"[{device_key}] Starting Shizuku...")
        shell("input keyevent KEYCODE_WAKEUP", timeout=5)
        time.sleep(1)
        shell("monkey -p moe.shizuku.privileged.api -c android.intent.category.LAUNCHER 1", timeout=10)
        time.sleep(5)
        starter = dev.get("shizuku_starter", "/data/local/tmp/shizuku_starter")
        shell(f"nohup {starter} > /tmp/shizuku.log 2>&1 &", timeout=5)
        time.sleep(12)
        result = rish_cmd(device_key, "echo SHIZUKU_STARTED; id")
        print(f"Result: {'✅ Started' if 'SHIZUKU_STARTED' in result else '❌ Failed'}")
        print(result)

    elif subcmd == "rish":
        cmd_to_run = " ".join(args) if args else "id"
        print(f"[{device_key}] rish> {cmd_to_run}")
        print(rish_cmd(device_key, cmd_to_run))

    elif subcmd == "whitelist":
        pkg = args[0] if args else "com.android.shell"
        print(shell(f"dumpsys deviceidle whitelist +{pkg}"))

    elif subcmd == "packages":
        # List packages that can use Shizuku
        shizuku_clients = rish_cmd(device_key, "pm list packages | grep -E 'shizuku|sui|rish'")
        print(f"[{device_key}] Shizuku-aware packages:")
        print(shizuku_clients)

# ═══════════════════════════════════════════════════════════════════════════════
# MAGISK / SUI CLI
# ═══════════════════════════════════════════════════════════════════════════════

def cmd_magisk(device_key: str) -> None:
    """Evaluate Magisk/Sui root status on device."""
    print(f"[{device_key}] Magisk/Sui/Root Evaluation:")

    dev = MESH_DEVICES.get(device_key, {})
    serial = resolve_adb_serial(device_key)
    if not serial:
        log.error(f"Device '{device_key}' unreachable")
        return

    def shell(cmd: str) -> str:
        if serial.startswith("tls:"):
            r = adb("shell", cmd, transport=int(serial.split(":")[1]), timeout=15)
        else:
            r = adb("shell", cmd, serial=serial, timeout=15)
        return r.stdout.strip()

    # Package checks
    pkgs = shell("pm list packages 2>/dev/null")
    magisk_found = [p for p in pkgs.split('\n') if any(k in p.lower() for k in ['magisk', 'topjohnwu', 'superuser', 'kingroot', 'supersu'])]
    sui_found = [p for p in pkgs.split('\n') if 'sui' in p.lower() or 'rikka' in p.lower()]

    print(f"  Magisk packages: {magisk_found or 'NONE'}")
    print(f"  Sui packages: {sui_found or 'NONE'}")

    # Root detection
    su_paths = ["/system/xbin/su", "/sbin/su", "/su/bin/su", "/data/adb/magisk/busybox"]
    for path in su_paths:
        exists = shell(f"ls {path} 2>/dev/null && echo EXISTS || echo MISSING")
        if "EXISTS" in exists:
            print(f"  ✅ Found: {path}")

    # Build type
    build_type = shell("getprop ro.build.type")
    debuggable = shell("getprop ro.debuggable")
    print(f"  Build type: {build_type} | Debuggable: {debuggable}")

    # Magisk via Shizuku rish
    magisk_rish = rish_cmd(device_key, "ls /data/adb/ 2>/dev/null && echo MAGISK_DATA_EXISTS || echo NO_MAGISK_DATA")
    print(f"  /data/adb/: {'✅ EXISTS (Magisk data dir)' if 'EXISTS' in magisk_rish else '❌ Not found'}")

    # Sui evaluation
    print("\n  Sui Assessment:")
    print("  - Sui is a Shizuku-based privileged shell provider")
    print("  - Does NOT require bootloader unlock or flash")
    print("  - Requires: Shizuku ✅ (already installed)")
    if "EXISTS" in magisk_rish:
        print("  - Magisk detected: Sui adds MagiskHide + module support")
    else:
        print("  - No Magisk: Sui provides rish-level root shell via Shizuku IPC")
    print("  - Install Sui: adb install sui.apk (from rikka.app/sui/)")
    print("  - After install: grant via Shizuku → rish executes as root")

    print("\n  Recommendation:")
    if not magisk_found:
        print("  → S20: Stock firmware, no root. Shizuku (UID=2000 ADB shell) is max privilege.")
        print("  → For root: Flash TWRP + Magisk via Odin (requires bootloader unlock — blocks Knox)")
        print("  → Alternative: Sui works WITHOUT root on ADB-authorized devices via Shizuku")

# ═══════════════════════════════════════════════════════════════════════════════
# SCRCPY GUI INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════

def cmd_scrcpy(device_key: str, extra_args: List[str]) -> None:
    """Launch scrcpy with optimal settings for the device."""
    dev = MESH_DEVICES.get(device_key, {})
    serial = resolve_adb_serial(device_key)
    if not serial:
        log.error(f"Device '{device_key}' unreachable")
        return

    if not os.path.exists(SCRCPY_PATH):
        print(f"scrcpy not found at {SCRCPY_PATH}")
        print("Install: brew install scrcpy")
        return

    # Base scrcpy command
    cmd_args = [SCRCPY_PATH]

    # Serial resolution
    if serial.startswith("tls:"):
        # For TLS transport, use the actual IP serial
        for ip in dev["ips"]:
            test = f"{ip}:{dev['port']}"
            r = adb("shell", "echo OK", serial=test, timeout=3)
            if r.returncode == 0:
                cmd_args += ["-s", test]
                break
    else:
        cmd_args += ["-s", serial]

    # Device-specific optimal settings
    cmd_args += dev.get("scrcpy_extra", [])

    # Common quality settings
    cmd_args += [
        "--video-codec=h265",          # H265 for better quality
        "--audio-codec=aac",            # AAC audio
        "--stay-awake",                 # Keep device awake
        "--no-power-on",               # Don't force power on
        "--shortcut-mod=lalt,lsuper",   # Alt+Super shortcuts
        "--window-title", f"Lens — {dev['name']}",
    ]

    # OTG mode if device supports it
    if "--otg" in extra_args:
        cmd_args = [SCRCPY_PATH, "--otg", "-s", serial.replace("tls:", "")]
        extra_args = [a for a in extra_args if a != "--otg"]

    cmd_args += extra_args

    print(f"[scrcpy] Launching: {' '.join(cmd_args)}")
    subprocess.Popen(cmd_args, env={**os.environ, "ADB": ADB_PATH})
    print(f"[scrcpy] Window opened for {dev['name']}")

def cmd_scrcpy_record(device_key: str, output_path: str = None) -> None:
    """Record device screen via scrcpy."""
    dev = MESH_DEVICES.get(device_key, {})
    serial = resolve_adb_serial(device_key)
    if not serial:
        log.error(f"Device '{device_key}' unreachable")
        return
    if not output_path:
        output_path = f"/tmp/lens_{device_key}_{int(time.time())}.mp4"
    cmd_args = [SCRCPY_PATH, "-s", serial, "--record", output_path, "--no-display"]
    print(f"[scrcpy] Recording to {output_path} (Ctrl+C to stop)")
    subprocess.run(cmd_args, env={**os.environ, "ADB": ADB_PATH})

# ═══════════════════════════════════════════════════════════════════════════════
# STATUS REPORT
# ═══════════════════════════════════════════════════════════════════════════════

def cmd_status() -> None:
    """Full mesh status report."""
    print("=" * 60)
    print("LAUBURU LENS CLI HUB — MESH STATUS")
    print("=" * 60)
    print(f"\nADB: {ADB_PATH}")
    print(f"scrcpy: {SCRCPY_PATH}")
    print(f"fdroidcl: {FDROIDCL_PATH}")

    # Router
    print("\n🌐 Router (GL.iNet):")
    try:
        router_ok = router_ssh("echo ROUTER_OK", timeout=5)
        if "ROUTER_OK" in router_ok:
            uptime = router_ssh("uptime | awk '{print $3,$4}'")
            wg_peers = router_ssh("wg show wgserver | grep 'peer:' | wc -l")
            print(f"  ✅ {ROUTER_IP} | Uptime: {uptime} | WG peers: {wg_peers.strip()}")
        else:
            print(f"  ❌ Router unreachable")
    except Exception as e:
        print(f"  ❌ Router: {e}")

    # Devices
    print("\n📱 Android Devices:")
    for key, dev in MESH_DEVICES.items():
        serial = resolve_adb_serial(key)
        rish_out = rish_cmd(key, "echo RISH_OK", timeout=10)
        rish_ok = "RISH_OK" in rish_out
        if serial or rish_ok:
            conn_method = f"serial={serial}" if serial else "transport=ssh-bridge (u0_a363@pixel:8022)"
            cdp_port = 9223 if key == "s20" else 9224
            try:
                import urllib.request
                cdp = json.loads(urllib.request.urlopen(
                    f"http://localhost:{cdp_port}/json/version", timeout=2
                ).read())
                cdp_status = f"✅ {cdp.get('Browser','?')}"
            except:
                cdp_status = "❌ offline"
            print(f"  ✅ {dev['name']}: {conn_method}")
            print(f"     Shizuku/rish: {'✅' if rish_ok else '❌'} | Chrome CDP {cdp_port}: {cdp_status}")
        else:
            print(f"  ❌ {dev['name']}: UNREACHABLE")

    # Mac CDP
    print("\n🖥️ Mac Chrome CDP:")
    try:
        import urllib.request
        cdp = json.loads(urllib.request.urlopen("http://localhost:9222/json/version", timeout=2).read())
        print(f"  ✅ Port 9222: {cdp.get('Browser','?')}")
    except:
        print("  ❌ Port 9222: offline")

    print("\n🔧 Tools:")
    print(f"  scrcpy: {'✅ ' + SCRCPY_PATH if os.path.exists(SCRCPY_PATH) else '❌ not installed (brew install scrcpy)'}")
    print(f"  fdroidcl: {'✅ ' + FDROIDCL_PATH if os.path.exists(FDROIDCL_PATH) else '❌ not installed (brew install fdroidcl)'}")

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return

    cmd = args[0].lower()
    rest = args[1:]

    if cmd == "status":
        cmd_status()

    elif cmd == "router":
        subcmd = rest[0] if rest else "status"
        cmd_router(subcmd, rest[1:])

    elif cmd == "adb":
        device_key = rest[0] if rest else "s20"
        cmd_adb(device_key, rest[1:])

    elif cmd == "android":
        device_key = rest[0] if rest else "s20"
        subcmd = rest[1] if len(rest) > 1 else "info"
        cmd_android(device_key, subcmd, rest[2:])

    elif cmd == "fdroid":
        device_key = rest[0] if rest else "s20"
        subcmd = rest[1] if len(rest) > 1 else "update"
        cmd_fdroid(device_key, subcmd, rest[2:])

    elif cmd == "shizuku":
        device_key = rest[0] if rest else "s20"
        subcmd = rest[1] if len(rest) > 1 else "status"
        cmd_shizuku(device_key, subcmd, rest[2:])

    elif cmd == "scrcpy":
        device_key = rest[0] if rest else "s20"
        cmd_scrcpy(device_key, rest[1:])

    elif cmd == "scrcpy-record":
        device_key = rest[0] if rest else "s20"
        output = rest[1] if len(rest) > 1 else None
        cmd_scrcpy_record(device_key, output)

    elif cmd == "magisk":
        device_key = rest[0] if rest else "s20"
        cmd_magisk(device_key)

    elif cmd == "daemon":
        daemon_script = os.path.join(os.path.dirname(__file__), "lens_android_dependency_daemon.py")
        interval = rest[0] if rest else "60"
        os.execv(sys.executable, [sys.executable, daemon_script, "daemon", "--interval", interval])

    elif cmd in ("pycharm", "charm"):
        run_cmd = ["open", "-na", "PyCharm.app", "--args"] + rest
        print(f"🚀 Launching JetBrains PyCharm via Lens CLI Hub: {' '.join(run_cmd)}")
        sys.exit(subprocess.call(run_cmd))

    elif cmd == "rish":
        device_key = rest[0] if rest else "s20"
        rish_command = " ".join(rest[1:]) if len(rest) > 1 else "id"
        print(rish_cmd(device_key, rish_command))

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)

if __name__ == "__main__":
    main()
