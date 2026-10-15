#!/usr/bin/env bash
# ==============================================================================
# lauburu_ipless_serial_launcher.sh (aliased as `bt-serial`)
# 🌿 Sovereign IP-less Serial Terminal Launcher & RFCOMM PTY Bridge
#
# Uses `tio` (115200 8N1, auto-reconnect, zero Ctrl-A conflict with tmux)
# to connect any low-RAM terminal emulator (Ghostty, Alacritty, WezTerm, Kitty,
# or Terminal.app) to IP-less POSIX PTYs and Bluetooth RFCOMM serial consoles.
# ==============================================================================
set -euo pipefail

TIO_BIN="/opt/homebrew/bin/tio"
if [ ! -x "$TIO_BIN" ]; then
    TIO_BIN="$(command -v tio || true)"
fi
BLUEUTIL_BIN="/Users/aaron/.local/bin/blueutil"
REPO_ROOT="/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo"

# Canonical Bluetooth MACs & Link-Local Thunderbolt Hardware Addresses
L1_BT_MAC="1C:F6:4C:81:0B:28"
L2_BT_MAC="A4:83:E7:DA:D0:B0"
L3_BT_MAC="00:41:0E:14:28:44"
L8_BT_MAC="3C:22:FB:4E:9F:BB"
L8_TB_LL="fe80::1082:a3ff:fe9e:ae71%bridge0"

usage() {
    cat << 'EOF'
╔══════════════════════════════════════════════════════════════════════════╗
║ 🌿 LAUBURU SOVEREIGN IP-LESS SERIAL TERMINAL LAUNCHER (`bt-serial`)      ║
╚══════════════════════════════════════════════════════════════════════════╝
Usage:
  bt-serial [l1|local]     Attach `tio` to L1 Sovereign BT Serial PTY (/tmp/bt_daemon_4005_pty)
  bt-serial dev            Attach `tio` to Hot-Reload Dev Serial PTY (/tmp/bt_serial_pty)
  bt-serial l3             Attach `tio` to L3 (linux-amd-gpu) Bluetooth RFCOMM Ch 1 agetty
  bt-serial l8             Attach `tio` to L8 (lauburu) Bluetooth RFCOMM Ch 1 agetty
  bt-serial l2             Attach `tio` to L2 (MacBook Pro) /dev/cu.aaronsMacBookPro
  bt-serial hw             Attach `tio` to /dev/cu.Lauburu-Linux-HeadNode (115200 8N1)
  bt-serial raw <dev>      Attach `tio` to any raw /dev/cu.* or /tmp/* serial device
  bt-serial --status       Live-probe all local PTYs, /dev/cu.*, TB4 Link-Local, & RFCOMM agetty
  bt-serial --verify       Run non-interactive E2E verification of IP-less serial endpoints

Tips inside `tio`:
  • Press Ctrl-T then Q to quit `tio` cleanly (does not conflict with tmux Ctrl-B or screen Ctrl-A)
  • Press Ctrl-T then ? to view all `tio` serial keybindings (hex mode, line states, log to file)
EOF
}

ensure_l1_daemon_pty() {
    if [ ! -e "/tmp/bt_daemon_4005_pty" ]; then
        nohup /usr/bin/python3 "$REPO_ROOT/06_scripts_and_tooling/bluetooth_serial_terminal_daemon.py" \
            >> /private/tmp/bt_terminal_4005.log 2>> /private/tmp/bt_terminal_4005_err.log &
        sleep 1.2
    fi
}

spawn_rfcomm_pty_bridge() {
    local target_node="$1"
    local bt_mac="$2"
    local channel="$3"
    local pty_link="$4"
    local relay_host="$5"

    python3 - "$target_node" "$bt_mac" "$channel" "$pty_link" "$relay_host" << 'PYEOF'
import fcntl
import os
import pty
import select
import signal
import subprocess
import sys
import termios
import time
from pathlib import Path

target_node, bt_mac, channel, pty_link_str, relay_host = sys.argv[1:6]
pty_link = Path(pty_link_str)

master_fd, slave_fd = pty.openpty()
slave_name = os.ttyname(slave_fd)

attrs = termios.tcgetattr(slave_fd)
attrs[0] = 0
attrs[1] = 0
attrs[2] = (attrs[2] & ~(termios.CSIZE | termios.PARENB | termios.CSTOPB)) | termios.CS8 | termios.CREAD | termios.CLOCAL
attrs[3] = 0
attrs[4] = termios.B115200
attrs[5] = termios.B115200
termios.tcsetattr(slave_fd, termios.TCSANOW, attrs)

if pty_link.is_symlink() or pty_link.exists():
    pty_link.unlink()
pty_link.symlink_to(slave_name)

remote_py = (
    "import socket, sys, select, os; "
    f"s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM); "
    "s.settimeout(8.0); "
    f"s.connect(('{bt_mac}', {int(channel)})); "
    "s.setblocking(False); "
    "os.write(1, b'\\r\\n[RFCOMM DLC CONNECTED: " + bt_mac + " CH " + channel + "]\\r\\n'); "
    "s.sendall(b'\\r\\n'); "
    "while True:\n"
    "    r, _, _ = select.select([0, s], [], [], 1.0)\n"
    "    if 0 in r:\n"
    "        d = os.read(0, 4096)\n"
    "        if not d: break\n"
    "        s.sendall(d)\n"
    "    if s in r:\n"
    "        d = s.recv(4096)\n"
    "        if not d: break\n"
    "        os.write(1, d)\n"
)

proc = subprocess.Popen(
    ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=3", relay_host, f"python3 -u -c \"{remote_py}\""],
    stdin=master_fd,
    stdout=master_fd,
    stderr=master_fd,
    close_fds=True,
)
os.close(master_fd)

def cleanup(*_):
    try:
        proc.terminate()
    except Exception:
        pass
    try:
        if pty_link.is_symlink():
            pty_link.unlink()
    except Exception:
        pass
    sys.exit(0)

signal.signal(signal.SIGTERM, cleanup)
signal.signal(signal.SIGINT, cleanup)

while proc.poll() is None:
    time.sleep(0.5)
cleanup()
PYEOF
}

run_status() {
    echo "╔══════════════════════════════════════════════════════════════════════════╗"
    echo "║ 🌿 LAUBURU IP-LESS SERIAL & LAYER-0 RFCOMM STATUS                        ║"
    echo "╚══════════════════════════════════════════════════════════════════════════╝"
    echo "• Serial Client: $( "$TIO_BIN" --version | head -n 1 ) ($TIO_BIN)"
    echo ""
    echo "[1] Local Darwin Bluetooth & Virtual Serial Devices:"
    for dev in /tmp/bt_daemon_4005_pty /tmp/bt_serial_pty /dev/cu.Bluetooth-Incoming-Port /dev/cu.Lauburu-Linux-HeadNode /dev/cu.aaronsMacBookPro /dev/cu.Macbook; do
        if [ -e "$dev" ]; then
            target="$(readlink "$dev" 2>/dev/null || echo "character-device")"
            printf "  ✔ %-34s -> %s\n" "$dev" "$target"
        else
            printf "  - %-34s -> (inactive)\n" "$dev"
        fi
    done

    echo ""
    echo "[2] Thunderbolt 4 Hardware Link-Local (Zero-DHCP / Zero-IPv4) Neighbors:"
    ndp -an 2>/dev/null | grep bridge0 | grep -v incomplete | sed 's/^/  • /' || true

    echo ""
    echo "[3] Live Bluetooth RFCOMM Channel 1 Serial Consoles (agetty 115200 8N1):"
    # Probe L3 RFCOMM agetty from L8 over pure Bluetooth RFCOMM
    l3_banner="$(ssh -o BatchMode=yes -o ConnectTimeout=2 "linuxmini@10.0.0.8" 'python3 -c "
import socket, select, time
s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
s.settimeout(5.0)
s.connect((\"00:41:0E:14:28:44\", 1))
time.sleep(1.2)
r, _, _ = select.select([s], [], [], 2.5)
data = \" \".join(s.recv(1024).decode(\"utf-8\", errors=\"replace\").split()) if r else \"CONNECTED\"
s.close()
print(data)
"' 2>/dev/null || echo "STANDBY")"
    printf "  • L3 (linux-amd-gpu) [%s ch 1]: %s\n" "$L3_BT_MAC" "${l3_banner:-STANDBY}"

    # Probe L8 RFCOMM agetty from L3 over pure Bluetooth RFCOMM
    l8_banner="$(ssh -o BatchMode=yes -o ConnectTimeout=2 "linux@192.168.8.225" 'python3 -c "
import socket, select, time
s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
s.settimeout(5.0)
s.connect((\"3C:22:FB:4E:9F:BB\", 1))
time.sleep(1.2)
r, _, _ = select.select([s], [], [], 2.5)
data = \" \".join(s.recv(1024).decode(\"utf-8\", errors=\"replace\").split()) if r else \"CONNECTED\"
s.close()
print(data)
"' 2>/dev/null || echo "STANDBY")"
    printf "  • L8 (lauburu)       [%s ch 1]: %s\n" "$L8_BT_MAC" "${l8_banner:-STANDBY}"
}

run_verify() {
    ensure_l1_daemon_pty
    run_status
    echo ""
    echo "[4] Verifying Local IP-less POSIX PTY (/tmp/bt_daemon_4005_pty) Round-Trip:"
    python3 -c '
import os, select, time
fd = os.open("/tmp/bt_daemon_4005_pty", os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
while select.select([fd], [], [], 0.05)[0]:
    os.read(fd, 8192)
os.write(fd, b"echo IPLESS_SERIAL_VERIFIED_OK\r\n")
time.sleep(0.6)
chunks = []
while select.select([fd], [], [], 0.2)[0]:
    chunks.append(os.read(fd, 8192).decode("utf-8", errors="replace"))
os.close(fd)
out = "".join(chunks)
if "IPLESS_SERIAL_VERIFIED_OK" in out or "lauburu>" in out:
    print("  ✔ /tmp/bt_daemon_4005_pty verified responsive (115200 8N1, Exit Code 0)")
else:
    print("  ! Unexpected PTY output:", repr(out[:120]))
    raise SystemExit(1)
'
}

MODE="${1:-l1}"
case "$MODE" in
    l1|local)
        ensure_l1_daemon_pty
        echo "🌿 Attaching tio (115200 8N1) to L1 IP-less Serial PTY (/tmp/bt_daemon_4005_pty)..."
        exec "$TIO_BIN" -b 115200 --mute /tmp/bt_daemon_4005_pty
        ;;
    dev|avf)
        if [ ! -e "/tmp/bt_serial_pty" ]; then
            "$REPO_ROOT/06_scripts_and_tooling/bluetooth_avf_dev_terminal/bt_serial_dev_launcher.sh" --detached >/dev/null
            sleep 0.8
        fi
        echo "🌿 Attaching tio (115200 8N1) to Hot-Reload Dev Serial PTY (/tmp/bt_serial_pty)..."
        exec "$TIO_BIN" -b 115200 --mute /tmp/bt_serial_pty
        ;;
    l3)
        PTY_LINK="/tmp/bt_rfcomm_l3_pty"
        rm -f "$PTY_LINK"
        spawn_rfcomm_pty_bridge "l3" "$L3_BT_MAC" 1 "$PTY_LINK" "linuxmini@${L8_TB_LL}" &
        BRIDGE_PID=$!
        trap 'kill $BRIDGE_PID 2>/dev/null || true; rm -f "$PTY_LINK"' EXIT
        for _ in {1..20}; do
            [ -e "$PTY_LINK" ] && break
            sleep 0.1
        done
        echo "🌿 Attaching tio (115200 8N1) to L3 ($L3_BT_MAC Ch 1) via $PTY_LINK..."
        "$TIO_BIN" -b 115200 "$PTY_LINK"
        ;;
    l8)
        PTY_LINK="/tmp/bt_rfcomm_l8_pty"
        rm -f "$PTY_LINK"
        spawn_rfcomm_pty_bridge "l8" "$L8_BT_MAC" 1 "$PTY_LINK" "linux@192.168.8.225" &
        BRIDGE_PID=$!
        trap 'kill $BRIDGE_PID 2>/dev/null || true; rm -f "$PTY_LINK"' EXIT
        for _ in {1..20}; do
            [ -e "$PTY_LINK" ] && break
            sleep 0.1
        done
        echo "🌿 Attaching tio (115200 8N1) to L8 ($L8_BT_MAC Ch 1) via $PTY_LINK..."
        "$TIO_BIN" -b 115200 "$PTY_LINK"
        ;;
    l2)
        exec "$TIO_BIN" -b 115200 /dev/cu.aaronsMacBookPro
        ;;
    hw)
        exec "$TIO_BIN" -b 115200 /dev/cu.Lauburu-Linux-HeadNode
        ;;
    raw)
        shift
        exec "$TIO_BIN" -b 115200 "$@"
        ;;
    --status|status)
        run_status
        ;;
    --verify|verify)
        run_verify
        ;;
    --help|-h|help)
        usage
        ;;
    *)
        usage
        exit 1
        ;;
esac
