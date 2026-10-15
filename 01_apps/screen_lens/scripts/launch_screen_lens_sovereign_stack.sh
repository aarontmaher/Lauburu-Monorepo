#!/usr/bin/env bash
# ==============================================================================
# launch_screen_lens_sovereign_stack.sh
# ==============================================================================
# Master Unified Launcher for the Screen Lens Sovereign Global Orchestrator Stack.
#
# Ports Governed:
# - Port 3035: Native Swift OCR & ScreenCaptureKit Engine (lauburu-lens)
# - Port 3036: Screen Life Companion Focus & Memory Engine (screen_life_companion.py)
# - Port 3037: Sovereign Master Global Orchestrator Control Plane (lens_global_orchestrator.py)
# - Port 4003: Live Multipart MJPEG Screen Stream Broadcast Server (lens_screen_live_stream_server.py)
# - Port 4006: Mesh Universal Remote HID CoreGraphics Server (mesh_universal_remote_hid_server.py)
#
# Rule #0 Compliant & Idempotent: Checks port liveness before launching.
# ==============================================================================

set -euo pipefail

REPO_ROOT="/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo"
LENS_DIR="${REPO_ROOT}/01_apps/screen_lens"
LOG_DIR="${REPO_ROOT}/logs/screen_lens"
mkdir -p "${LOG_DIR}"

# Sanitize SSL_CERT_FILE if pointing to ephemeral proxy cert or non-existent path
if [ -n "${SSL_CERT_FILE:-}" ]; then
    if [[ "${SSL_CERT_FILE}" == *"proxy_cert_"* ]] || [ ! -f "${SSL_CERT_FILE}" ]; then
        unset SSL_CERT_FILE
    fi
fi

echo "========================================================================"
echo "👁️  LAUNCHING SCREEN LENS SOVEREIGN GLOBAL ORCHESTRATOR STACK"
echo "========================================================================"

is_port_listening() {
    local port="$1"
    if ! lsof -i :"$port" -sTCP:LISTEN >/dev/null 2>&1; then
        return 1
    fi
    if curl -s -m 2 -o /dev/null "http://127.0.0.1:${port}/" 2>/dev/null; then
        return 0
    else
        echo "⚠️ Port ${port} is listening but unresponsive (hung/deadlocked). Terminating PID..."
        local pids
        pids=$(lsof -ti :"$port")
        if [ -n "$pids" ]; then
            kill -9 $pids 2>/dev/null || true
            sleep 0.5
        fi
        return 1
    fi
}

# 1. Port 3035: Swift OCR Engine
if is_port_listening 3035; then
    echo "🟢 Port 3035 (lauburu-lens OCR): Active."
else
    echo "🟡 Launching Port 3035 (lauburu-lens Swift OCR)..."
    nohup "${LENS_DIR}/bin/lauburu-lens" start --port 3035 --interval 2.0 --mode fast --foreground > "${LOG_DIR}/port_3035.log" 2>&1 &
    sleep 0.5
fi

# 2. Port 3036: Screen Life Companion Focus & Memory Engine
if is_port_listening 3036; then
    echo "🟢 Port 3036 (Screen Life Companion): Active."
else
    echo "🟡 Launching Port 3036 (Screen Life Companion)..."
    nohup python3 "${LENS_DIR}/screen_life_companion/screen_life_companion.py" --daemon > "${LOG_DIR}/port_3036.log" 2>&1 &
    sleep 0.5
fi

# 3. Port 4003: Sovereign VLA Remote Desktop & Live Stream Server
if is_port_listening 4003; then
    echo "🟢 Port 4003 (Sovereign Remote Desktop): Active."
else
    echo "🟡 Launching Port 4003 (Sovereign Remote Desktop Hub)..."
    nohup python3 "${LENS_DIR}/src/sovereign_remote_desktop_server.py" > "${LOG_DIR}/port_4003.log" 2>&1 &
    sleep 0.5
fi

# 4. Port 4006: Mesh Universal Remote HID CoreGraphics Server
if is_port_listening 4006; then
    echo "🟢 Port 4006 (HID Remote Server): Active."
else
    echo "🟡 Launching Port 4006 (HID CoreGraphics Server)..."
    nohup python3 "${LENS_DIR}/src/mesh_universal_remote_hid_server.py" > "${LOG_DIR}/port_4006.log" 2>&1 &
    sleep 0.5
fi

# 5. Port 3037: Sovereign Master Global Orchestrator Control Plane
if is_port_listening 3037; then
    echo "🟢 Port 3037 (Global Orchestrator): Active."
else
    echo "🟡 Launching Port 3037 (Screen Lens Sovereign Global Orchestrator)..."
    nohup python3 "${LENS_DIR}/src/lens_global_orchestrator.py" --port 3037 --daemon > "${LOG_DIR}/port_3037.log" 2>&1 &
    sleep 0.5
fi

# 6. Mac Voice Coder Assistant
if pgrep -f "lens_mac_voice_coder.py" >/dev/null 2>&1; then
    echo "🟢 Mac Voice Coder: Active."
else
    echo "🟡 Launching Mac Voice Coder..."
    nohup env PYTHONUNBUFFERED=1 /Users/aaron/DFS_UNIFIED/.venv/bin/python3 "${LENS_DIR}/src/lens_mac_voice_coder.py" > "${LOG_DIR}/mac_voice_coder.log" 2>&1 &
    sleep 0.5
fi

# 7. Netmon LoRA Distillation Daemon
if pgrep -f "netmon_lora_distillation_daemon.sh" >/dev/null 2>&1; then
    echo "🟢 Netmon LoRA Distillation: Active."
else
    echo "🟡 Launching Netmon LoRA Distillation Daemon..."
    nohup bash "${REPO_ROOT}/06_scripts_and_tooling/network/netmon_lora_distillation_daemon.sh" > "${LOG_DIR}/netmon_lora.log" 2>&1 &
    sleep 0.5
fi

echo "========================================================================"
echo ""
echo "========================================================================"
