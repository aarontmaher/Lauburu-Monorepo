#!/bin/bash
# ==============================================================================
# Lauburu Mesh Ecosystem — Master Unified Global CLI
# ==============================================================================
# Single-word global commands:
#   lauburu           -> Launch full Canonical 9-Screen TUI Command Center
#   lauburu dev       -> Launch Live Side-by-Side Dual Graphical Arena (--dev)
#   lauburu arena     -> Launch Live Side-by-Side Dual Graphical Arena (--dev)
#   lauburu map       -> Run Unified 3D Spatial Fusion Engine
#   lauburu movesense -> Check / restart Movesense BLE GATT 128Hz daemon
#   tui               -> Fast alias for 'lauburu'
#   arena             -> Fast alias for 'lauburu dev'
# ==============================================================================

MONOREPO_DIR="/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo"
TUI_DIR="$MONOREPO_DIR/01_apps/canonical_port"

# Detect invoked command name
INVOKED_CMD=$(basename "$0")

if [ "$INVOKED_CMD" = "arena" ]; then
    CMD="arena"
elif [ "$INVOKED_CMD" = "tui" ]; then
    CMD="tui"
elif [ "$INVOKED_CMD" = "priority" ] || [ "$INVOKED_CMD" = "governor" ]; then
    CMD="priority"
else
    CMD="${1:-tui}"
    shift || true
fi

case "$CMD" in
    tui|"")
        echo "🚀 Launching Lauburu Canonical TUI Command Center (Live --dev Mode)..."
        cd "$TUI_DIR"
        exec ./run_live_tui.sh --dev "$@"
        ;;
    --dev|dev|arena)
        echo "🚀 Launching Lauburu Live Side-by-Side Dual Graphical Arena..."
        cd "$TUI_DIR"
        exec ./run_live_arena_dev.sh "$@"
        ;;
    web|browser)
        echo "🌐 Launching Lauburu Textual-Web Browser Server on http://0.0.0.0:8088..."
        cd "$TUI_DIR"
        exec ./run_live_tui.sh web "$@"
        ;;
    map)
        echo "🌐 Running Unified 3D Spatial Fusion Engine..."
        cd "$MONOREPO_DIR"
        python3 00_core_infrastructure/self_healing_hub/src/spatial_3d_unified_fusion.py
        ;;
    map-all|discover)
        echo "🗺️ Running Autonomous Whole-Project & Network Feature Discovery Engine..."
        cd "$MONOREPO_DIR"
        python3 00_core_infrastructure/self_healing_hub/src/autonomous_feature_discovery_engine.py
        ;;
    math|math-daemon)
        echo "🧮 Running Standalone Qwen Math Trend & Optimization Daemon..."
        cd "$MONOREPO_DIR"
        python3 02_ai_models_and_inference/quantum/autonomous_math_trend_optimizer.py
        ;;
    movesense)
        echo "💓 Checking Movesense 261030002013 BLE daemon status..."
        if ps aux | grep "run_real_movesense_daemon.py" | grep -v grep > /dev/null; then
            echo "✅ Movesense BLE daemon is ACTIVE and streaming live packets."
        else
            echo "⚠️ Movesense daemon not running. Starting background streamer..."
            nohup /Users/aaron/DFS_UNIFIED/lora_datasets/.venv/bin/python "$MONOREPO_DIR/03_biometrics_and_telemetry/run_real_movesense_daemon.py" > /tmp/movesense_ble.log 2>&1 &
            echo "✅ Started Movesense BLE daemon."
        fi
        ;;
    priority|governor)
        echo "🛡️ Running Hybrid Real-RAM Mesh Governor & Master Priority Swarm..."
        cd "$MONOREPO_DIR"
        python3 06_scripts_and_tooling/network/real_hardware_router_ram_governor.py "$@"
        python3 05_agents_and_swarms/master_priority_automation_loop.py --once
        ;;
    governor-optimize|optimize-network)
        echo "⚡ Executing Real-Hardware Network-Wide Settings Optimization..."
        cd "$MONOREPO_DIR"
        exec python3 06_scripts_and_tooling/network/real_hardware_router_ram_governor.py "$@"
        ;;
    governor-test|test-tiny-models)
        echo "🔬 Running Continuous Tiny Model Governance Benchmark..."
        cd "$MONOREPO_DIR"
        exec python3 02_ai_models_and_inference/benchmarks/router_ram_governor_model_bench.py "$@"
        ;;
    priority-daemon|governor-daemon)
        echo "🚀 Starting 24/7 Master Priority Continuous Automation Daemon..."
        cd "$MONOREPO_DIR"
        exec python3 05_agents_and_swarms/master_priority_automation_loop.py --daemon
        ;;
    router-bench|bench-router)
        echo "🔬 Running Sandboxed GL.iNet Router Micro AI Benchmark..."
        cd "$MONOREPO_DIR"
        exec python3 02_ai_models_and_inference/benchmarks/glinet_router_micro_ai_benchmark.py
        ;;
    help|--help|-h)
        echo "======================================================================"
        echo "🌟 LAUBURU MESH UNIFIED GLOBAL CLI"
        echo "======================================================================"
        echo "Usage: lauburu [command] [options]"
        echo ""
        echo "Commands:"
        echo "  lauburu (or tui)        Launch full Canonical 9-Screen TUI Command Center"
        echo "  lauburu dev (or arena)   Launch Live Side-by-Side Dual Graphical Arena"
        echo "  lauburu priority         Run Hybrid Real-RAM Mesh Governor & Priority Loop"
        echo "  lauburu priority-daemon  Start 24/7 Master Priority Automation Daemon"
        echo "  lauburu router-bench     Run Sandboxed GL.iNet Router Micro AI Benchmark"
        echo "  lauburu map              Run Unified 3D Spatial Fusion Engine"
        echo "  lauburu map-all          Run Autonomous Whole-Project Feature Discovery"
        echo "  lauburu math             Run Standalone Qwen Math Telemetry Trend Optimizer"
        echo "  lauburu movesense        Check / Start Physical Movesense 128Hz BLE daemon"
        echo "  lauburu help             Show this help message"
        echo "======================================================================"
        ;;
    *)
        echo "Unknown command: $CMD"
        echo "Run 'lauburu help' for available commands."
        exit 1
        ;;
esac
