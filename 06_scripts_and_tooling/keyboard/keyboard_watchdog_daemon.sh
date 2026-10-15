#!/usr/bin/env bash
# ==============================================================================
# ⌨️ Lauburu Sovereign Keyboard Watchdog & Auto-Reconnection Daemon
# ==============================================================================
# Continuously monitors Aaron's Magic Keyboard (38-09-fb-38-ca-62) & USB HID link,
# performs non-blocking wake reconnection attempts, and maintains zero stuck modifiers.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="/usr/bin/python3"
RECONNECT_PY="${SCRIPT_DIR}/reconnect_magic_keyboard.py"
LOG_FILE="/tmp/lauburu_keyboard_watchdog.log"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting Lauburu Keyboard Watchdog Daemon..." >> "${LOG_FILE}"

exec "${PYTHON}" "${RECONNECT_PY}" --daemon --interval 8.0 >> "${LOG_FILE}" 2>&1
