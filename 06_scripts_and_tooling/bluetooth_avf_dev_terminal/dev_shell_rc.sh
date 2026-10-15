#!/usr/bin/env bash
# ==============================================================================
# Lauburu Bluetooth Serial Terminal — Live Dev Shell RC (Pane 3)
# Pre-loads live hot-reload, packet injection, and AVF stability helper commands
# ==============================================================================
export BT_SERIAL_DEV=1
export TERM="${TERM:-xterm-256color}"
export PATH="/usr/local/bin:/usr/bin:/bin:$HOME/.local/bin:$PATH"

BT_DEV_DIR="$(python3 -c 'import os,sys; print(os.path.dirname(os.path.realpath(sys.argv[1])))' "${BASH_SOURCE[0]}")"
export BT_DEV_DIR

# ── Live Helper Functions ────────────────────────────────────────────────────

# 1. Live self-patch a new command into bt_serial_commands.py (<50ms hot-reload)
bt-patch() {
    if [ $# -lt 2 ]; then
        echo "Usage: bt-patch <cmd_name> <response_string>"
        echo "Example: bt-patch vbat 'VBAT=4.19V TEMP=31.0C RSSI=-48dBm'"
        return 1
    fi
    local cmd_name="$1"
    shift
    local response="$*"
    python3 "$BT_DEV_DIR/bt_serial_terminal.py" --exec "patch $cmd_name $response"
}

# 2. Inject an ASCII command or frame directly into Virtual RFCOMM PTY (/tmp/bt_serial_pty) or TCP :4005
bt-send() {
    if [ $# -lt 1 ]; then
        echo "Usage: bt-send <ascii_payload>"
        return 1
    fi
    local payload="$*"
    if [ -e /tmp/bt_serial_pty ]; then
        printf "%s\r\n" "$payload" > /tmp/bt_serial_pty
        echo "[TX -> /tmp/bt_serial_pty] $payload"
    else
        printf "%s\r\n" "$payload" | nc -w 1 127.0.0.1 4005 2>/dev/null || true
        echo "[TX -> tcp://127.0.0.1:4005] $payload"
    fi
}

# 3. Inject raw hex bytes into the Bluetooth Serial Terminal
bt-hex() {
    if [ $# -lt 1 ]; then
        echo "Usage: bt-hex <hex_bytes>"
        return 1
    fi
    python3 - "$*" << 'PYEOF'
import os, socket, sys
hex_str = sys.argv[1].replace(" ", "").replace("0x", "")
raw = bytes.fromhex(hex_str)
if os.path.exists("/tmp/bt_serial_pty"):
    fd = os.open("/tmp/bt_serial_pty", os.O_WRONLY | os.O_NOCTTY)
    os.write(fd, raw)
    os.close(fd)
    print(f"[TX HEX -> /tmp/bt_serial_pty] {len(raw)}B: {raw.hex(' ').upper()}")
else:
    with socket.create_connection(("127.0.0.1", 4005), timeout=1.0) as s:
        s.sendall(raw)
    print(f"[TX HEX -> tcp://127.0.0.1:4005] {len(raw)}B: {raw.hex(' ').upper()}")
PYEOF
}

# 4. Stream Movesense Teleplot biometric frames into the serial terminal
bt-teleplot() {
    local count="${1:-10}"
    python3 - "$count" << 'PYEOF'
import math, os, socket, sys, time
count = int(sys.argv[1])
for i in range(count):
    hr = 64.0 + 4.5 * math.sin(i * 0.45)
    rmssd = 55.0 + 6.0 * math.cos(i * 0.35)
    rssi = -48.0 + 3.0 * math.sin(i * 0.8)
    line = f">hr_bpm:{hr:.1f}\r\n>rmssd_ms:{rmssd:.1f}\r\n>bt_rssi_dbm:{rssi:.1f}\r\n"
    if os.path.exists("/tmp/bt_serial_pty"):
        fd = os.open("/tmp/bt_serial_pty", os.O_WRONLY | os.O_NOCTTY)
        os.write(fd, line.encode())
        os.close(fd)
    else:
        with socket.create_connection(("127.0.0.1", 4005), timeout=1.0) as s:
            s.sendall(line.encode())
    time.sleep(0.12)
print(f"[Teleplot] Streamed {count} frames into BT Serial Terminal.")
PYEOF
}

# 5. Open live modules in $EDITOR (nano/vim) for instant hot-reload on save
bt-edit() {
    local target="${1:-commands}"
    local editor="${EDITOR:-nano}"
    case "$target" in
        commands|cmd) "$editor" "$BT_DEV_DIR/bt_serial_commands.py" ;;
        ui|view)      "$editor" "$BT_DEV_DIR/bt_serial_ui.py" ;;
        state)        "$editor" "$BT_DEV_DIR/bt_serial_state.py" ;;
        main|term)    "$editor" "$BT_DEV_DIR/bt_serial_terminal.py" ;;
        *)            "$editor" "$BT_DEV_DIR/$target" ;;
    esac
}

# 6. Check AVF & Bluetooth Serial health snapshot
avf-shield() {
    python3 "$BT_DEV_DIR/bt_serial_terminal.py" --exec "avf"
}

bt-selftest() {
    python3 "$BT_DEV_DIR/bt_serial_terminal.py" --self-test
}

# ── Interactive Dev Shell Banner (Compact for Pixel AVF & Desktop) ──────────
clear
printf "\033[1;36m━━ ⚡ LIVE DEV SHELL & INJECTOR (<50ms) ━━\033[0m\n"
printf " \033[1;32mbt-patch <c> <txt>\033[0m  Add live command\n"
printf " \033[1;32mbt-edit commands\033[0m    Edit commands.py\n"
printf " \033[1;32mbt-edit ui\033[0m          Edit ui.py theme\n"
printf " \033[1;32mbt-send '<ascii>'\033[0m   TX ASCII -> PTY\n"
printf " \033[1;32mbt-hex 'AA 55 01'\033[0m   TX HEX -> PTY\n"
printf " \033[1;32mbt-teleplot 15\033[0m      Stream Teleplot\n"
printf " \033[1;32mavf-shield\033[0m          AVF RAM/OOM status\n"
PS1="\[\033[1;35m\][bt-dev]\[\033[0m\] \$ "
