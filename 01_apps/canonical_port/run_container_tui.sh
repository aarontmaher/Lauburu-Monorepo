#!/usr/bin/env bash
# ==============================================================================
# Universal Multi-Arch TUI Container Launcher
# Automatically detects Docker / Podman / Termux PRoot environment
# Subsystem: 01_apps/canonical_port/run_container_tui.sh
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARCH=$(uname -m)

echo "=============================================================================="
echo "⚡ LAUBURU TUI CONTAINER LAUNCHER"
echo "• Detected Architecture: ${ARCH}"
echo "• Directory: ${SCRIPT_DIR}"
echo "=============================================================================="

MODE="${1:-interactive}"

if command -v docker >/dev/null 2>&1; then
    echo "▶ Building / Verifying multi-arch image lauburu/canonical-tui:latest..."
    docker build -t lauburu/canonical-tui:latest -f "${SCRIPT_DIR}/Dockerfile.tui" "${SCRIPT_DIR}"
    
    if [ "${MODE}" = "web" ]; then
        echo "▶ Starting Web-TUI on http://0.0.0.0:8088..."
        docker run -d --name lauburu_tui_web -p 8088:8088 -e MODE=web --rm lauburu/canonical-tui:latest
        echo "✔ Web-TUI active at http://127.0.0.1:8088"
    elif [ "${MODE}" = "verify" ]; then
        echo "▶ Running Headless Verification in container..."
        docker run --rm --name lauburu_tui_verify lauburu/canonical-tui:latest verify
    else
        echo "▶ Launching Interactive TUI in container..."
        docker run -it --rm --name lauburu_tui_interactive \
            -e TERM=xterm-256color \
            -e COLORTERM=truecolor \
            -v "${SCRIPT_DIR}/../..:/app:ro" \
            lauburu/canonical-tui:latest interactive
    fi
elif [ -n "${TERMUX_VERSION:-}" ]; then
    echo "▶ Android Termux environment detected. Running natively in Termux..."
    bash "${SCRIPT_DIR}/run_live_tui.sh" "${MODE}"
else
    echo "▶ Docker not found. Falling back to native host runner..."
    bash "${SCRIPT_DIR}/run_live_tui.sh" "${MODE}"
fi
