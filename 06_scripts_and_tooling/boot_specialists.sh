#!/usr/bin/env bash
# ==============================================================================
# Master Boot & Orchestrator Script for Lauburu Specialist Containers
# ==============================================================================
set -euo pipefail

MONOREPO_ROOT="/Volumes/Lauburu-Monorepo"
COMPOSE_FILE="${MONOREPO_ROOT}/00_core_infrastructure/docker-compose.specialists.yml"

ACTION="${1:-status}"

echo "=============================================================================="
echo "⚡ LAUBURU SPECIALIST CONTAINERS CONTROLLER"
echo "=============================================================================="

case "${ACTION}" in
    build)
        echo "🔨 Building all specialist container images..."
        cd "${MONOREPO_ROOT}/00_core_infrastructure"
        docker compose -f "${COMPOSE_FILE}" build
        ;;
    up|start)
        echo "🚀 Starting all specialist containers in background..."
        cd "${MONOREPO_ROOT}/00_core_infrastructure"
        docker compose -f "${COMPOSE_FILE}" up -d
        echo ""
        echo "✅ Active Specialist Endpoints:"
        echo "   • TUI Studio (ttyd / tmux):     http://localhost:8088"
        echo "   • Flutter/Rust Console (Port 4000): http://localhost:4000 & http://localhost:4001"
        echo "   • WebGPU 3D Kinematics Visualizer:  http://localhost:8090"
        echo "   • JupyterLab Notebook Studio:       http://localhost:8888"
        echo "   • Marimo Reactive Notebook:         http://localhost:2718"
        echo "   • Medical Biometrics DSP Stream:    http://localhost:4005"
        ;;
    down|stop)
        echo "🛑 Stopping all specialist containers..."
        cd "${MONOREPO_ROOT}/00_core_infrastructure"
        docker compose -f "${COMPOSE_FILE}" down
        ;;
    logs)
        cd "${MONOREPO_ROOT}/00_core_infrastructure"
        docker compose -f "${COMPOSE_FILE}" logs -f "${2:-}"
        ;;
    verify)
        echo "🔍 Verifying all polyglot local builds & schemas..."
        echo "1. C/ncurses TUI:"
        (cd "${MONOREPO_ROOT}/01_apps/canonical_tui_prototypes/c_ncurses" && make && ./bin/canonical_tui_c --verify)
        echo ""
        echo "2. Python Textual TUI:"
        python3 "${MONOREPO_ROOT}/01_apps/canonical_tui_prototypes/python_textual/app.py" --verify
        echo ""
        echo "3. Go Bubble Tea TUI:"
        (cd "${MONOREPO_ROOT}/01_apps/canonical_tui_prototypes/go_bubbletea" && go build -o bin/canonical_tui_go main.go && ./bin/canonical_tui_go --verify)
        echo ""
        echo "4. Rust Ratatui TUI:"
        (cd "${MONOREPO_ROOT}/01_apps/canonical_tui_prototypes/rust_ratatui" && ./target/release/canonical_tui_rust --verify)
        echo ""
        echo "5. WebGPU Rust Crate:"
        (cd "${MONOREPO_ROOT}/01_apps/spatial_and_3d/webgpu_specialist" && cargo test --quiet)
        echo ""
        echo "6. Flutter / Swift Port 4000 Engine:"
        (cd "${MONOREPO_ROOT}/01_apps/port_4000_flutter_rust/flutter_ui" && dart lib/main.dart)
        echo ""
        echo "7. Docker Compose Config Validation:"
        docker compose -f "${COMPOSE_FILE}" config >/dev/null && echo "✓ docker-compose.specialists.yml syntax valid."
        ;;
    status|*)
        cd "${MONOREPO_ROOT}/00_core_infrastructure"
        docker compose -f "${COMPOSE_FILE}" ps
        ;;
esac
