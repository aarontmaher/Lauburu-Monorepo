#!/usr/bin/env bash
# ==============================================================================
# Pixel AVF microVM — Chromium IDE & Remote Debugging Launcher
# Optimizations: Low memory, touch events, DevTools remote port 9222
# ==============================================================================
set -euo pipefail

TARGET_URL="${1:-http://127.0.0.1:8443}"
REMOTE_PORT="${2:-9222}"

exec chromium \
    --no-sandbox \
    --disable-dev-shm-usage \
    --disable-gpu \
    --remote-debugging-address=0.0.0.0 \
    --remote-debugging-port="$REMOTE_PORT" \
    --enable-features=TouchEvents,OverlayScrollbar \
    --touch-events=enabled \
    --force-dark-mode \
    --disable-background-timer-throttling \
    --disable-renderer-backgrounding \
    --window-size=1080,2400 \
    --user-data-dir="$HOME/.config/chromium-ide" \
    "$TARGET_URL"
