#!/usr/bin/env bash
# ==============================================================================
# 06_scripts_and_tooling/launch_npu_bluetooth_tui_ecosystem.sh
# ==============================================================================
# Master Launcher for Lauburu NPU AI Local Router & Bluetooth Terminal Ecosystem.
# Integrates with Kai Morich Serial Bluetooth Terminal (Android v1.52).
# Governed by Rule 0 (Zero-Mock), Rule 1 (Tri-Proof), Rule 3 (RAM Sanctuary),
# and Rule 8 (Local AI Hierarchy & TB4 Sharding Gate).
# ==============================================================================

set -euo pipefail

REPO_ROOT="/Volumes/Lauburu-Monorepo"
BT_STREAM_PIPE="/tmp/bluetooth_terminal_stream.ansi"
BT_PTY="/tmp/bluetooth_terminal_pty"

echo "=================================================================="
echo "⚡ LAUBURU MESH: NPU AI LOCAL ROUTER & BLUETOOTH TUI ECOSYSTEM"
echo "=================================================================="

# 1. Pre-Flight Storage Health Check (Rule 2)
if [ ! -d "$REPO_ROOT/obsidian_vault" ] || [ ! -d "/Volumes/Lauburu-Monorepo/04_data_and_memory/data" ]; then
    echo "❌ ERROR: Tri-Vault storage degraded! Healing directories..."
    mkdir -p "$REPO_ROOT/obsidian_vault" "/Volumes/Lauburu-Monorepo/04_data_and_memory/data"
fi

# 2. Host RAM Sanctuary Check (Rule 3)
FREE_RAM_GB=$(python3 -c 'import psutil; print(f"{psutil.virtual_memory().available / (1024**3):.2f}")')
echo "• Host Available RAM: ${FREE_RAM_GB} GB (Rule 3 Sanctuary Threshold >= 3.0 GB)"

# 3. Model Inference Ports Check (Rule 8)
echo "• Probing Local Model Engines..."
PRIMA_8082=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8082/v1/models || echo "000")
LLAMA_8081=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8081/v1/models || echo "000")
PRIMA_8083=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8083/v1/models || echo "000")

echo "  - Port 8082 (prima.cpp Master - Qwen 3.8 Max): HTTP $PRIMA_8082"
echo "  - Port 8081 (llama.cpp Normal Plane):          HTTP $LLAMA_8081"
echo "  - Port 8083 (Devils Advocate Abliterated 27B): HTTP $PRIMA_8083"

# 4. Initialize Out-of-Band Bluetooth Stream Buffer
touch "$BT_STREAM_PIPE"
echo "• Bluetooth Terminal Stream Pipe initialized: $BT_STREAM_PIPE"

# 5. Check Kai Morich Terminal App on S20 & Pixel
echo "• Checking Kai Morich Serial Bluetooth Terminal App on Mesh Nodes..."
if command -v adb >/dev/null 2>&1; then
    S20_PKG=$(adb -s 100.78.206.96:5555 shell pm list packages | grep kai_morich || true)
    if [ -n "$S20_PKG" ]; then
        echo "  - Samsung S20 (100.78.206.96): INSTALLED ($S20_PKG)"
    else
        echo "  - Samsung S20 (100.78.206.96): NOT DETECTED"
    fi
fi

echo "=================================================================="
echo "Select TUI Component to Launch:"
echo " 1) Bluetooth Serial Self-Healing TUI (06_scripts_and_tooling)"
echo " 2) Dual-Sandbox Arena TUI (Pure-NPU vs GPU MLX)"
echo " 3) High-ROI AI Training TUI (01_apps/ai_training_tui)"
echo " 4) Omniterminal Interactive Shell (/Users/aaron/.local/bin/omniterminal)"
echo " 5) Lauburu-TUI Native Rust Ratatui Client (02_ai_models_and_inference)"
echo " 6) Kai Morich Bluetooth Terminal Server Daemon"
echo " 7) Run Automated NPU Bluetooth Router Test Suite"
echo " 8) Snapshot Evaluation & Exit"
echo "=================================================================="

TARGET="${1:-8}"

case "$TARGET" in
    1)
        exec python3 "$REPO_ROOT/06_scripts_and_tooling/bluetooth_serial_self_healing_tui.py" --watch
        ;;
    2)
        exec python3 "$REPO_ROOT/01_apps/screen_lens/sandbox_evolution/bluetooth_terminal_arena/bluetooth_arena_tui.py"
        ;;
    3)
        exec python3 "$REPO_ROOT/01_apps/ai_training_tui/training_tui.py"
        ;;
    4)
        exec /Users/aaron/.local/bin/omniterminal console
        ;;
    5)
        cd "$REPO_ROOT/02_ai_models_and_inference/lauburu_tui" && cargo run --release
        ;;
    6)
        exec python3 "$REPO_ROOT/06_scripts_and_tooling/bluetooth_kai_morich_terminal_server.py" --daemon
        ;;
    7)
        exec python3 "$REPO_ROOT/tests/test_npu_tui_bluetooth_router.py"
        ;;
    8)
        echo "Running snapshot test of NPU AI Local Router and Kai Morich Server..."
        python3 "$REPO_ROOT/06_scripts_and_tooling/bluetooth_kai_morich_terminal_server.py" --test
        python3 "$REPO_ROOT/06_scripts_and_tooling/bluetooth_serial_self_healing_tui.py" --snapshot
        echo "✓ ECOSYSTEM PRE-FLIGHT VERIFIED (Exit Code 0)"
        ;;
    *)
        echo "Invalid selection. Exiting."
        exit 1
        ;;
esac
