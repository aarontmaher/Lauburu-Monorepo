#!/usr/bin/env bash
# ==============================================================================
# Master Polyglot TUI Runner & Benchmark Switcher
# Lauburu Mesh Ecosystem — 2026
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MONOREPO_ROOT="/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo"
PYTHON_VENV="${SCRIPT_DIR}/.venv/bin/python3"
if [ ! -x "${PYTHON_VENV}" ]; then PYTHON_VENV="python3"; fi

TARGET="${1:-menu}"

echo "=============================================================================="
echo "⚡ LAUBURU POLYGLOT TUI BENCHMARK & COCKPIT RUNNER"
echo "=============================================================================="
echo "Available TUI Environments:"
echo "  1) [python]  - Python Textual Unified Mesh Cockpit (Port 4000 Integration)"
echo "  2) [rust]    - Rust Ratatui Native Immediate-Mode TUI (Sub-ms 120 FPS)"
echo "  3) [go]      - Go Bubble Tea Elm-Architecture TUI (Zero-Alloc Goroutines)"
echo "  4) [lab]     - Python Mesh Transfer Lab (Statistical 95% CI & Chaos Tests)"
echo "  5) [web]     - Web Browser TUI on Port 8088 (textual-web)"
echo "  6) [tmux]    - All-in-One Multi-Window Tmux Cockpit (Switch with Ctrl+b 0..4)"
echo "=============================================================================="

case "${TARGET}" in
    1|python|textual)
        echo "🚀 Launching Python Textual Unified Cockpit..."
        export PYTHONPATH="${SCRIPT_DIR}/tui:${SCRIPT_DIR}:${PYTHONPATH:-}"
        exec "${PYTHON_VENV}" "${SCRIPT_DIR}/tui/unified_mesh_cockpit_tui.py"
        ;;
    2|rust|ratatui)
        echo "🚀 Launching Rust Ratatui Cockpit..."
        RUST_BIN="${MONOREPO_ROOT}/01_apps/canonical_tui_prototypes/rust_ratatui/bin/canonical_tui_rust"
        if [ -x "${RUST_BIN}" ]; then
            exec "${RUST_BIN}"
        else
            cd "${MONOREPO_ROOT}/01_apps/canonical_tui_prototypes/rust_ratatui"
            exec cargo run --release
        fi
        ;;
    3|go|bubbletea)
        echo "🚀 Launching Go Bubble Tea Cockpit..."
        GO_BIN="${MONOREPO_ROOT}/01_apps/canonical_tui_prototypes/go_bubbletea/bin/tui_go"
        if [ -x "${GO_BIN}" ]; then
            exec "${GO_BIN}"
        else
            cd "${MONOREPO_ROOT}/01_apps/canonical_tui_prototypes/go_bubbletea"
            exec go run main.go
        fi
        ;;
    4|lab|transfer)
        echo "🚀 Launching Mesh Transfer Lab..."
        export PYTHONPATH="${SCRIPT_DIR}/tui:${SCRIPT_DIR}:${PYTHONPATH:-}"
        exec "${PYTHON_VENV}" "${SCRIPT_DIR}/tui/tui_mesh_transfer_lab.py"
        ;;
    5|web)
        echo "🚀 Serving Web TUI on http://0.0.0.0:8088 ..."
        export PYTHONPATH="${SCRIPT_DIR}/tui:${SCRIPT_DIR}:${PYTHONPATH:-}"
        exec "${PYTHON_VENV}" "${SCRIPT_DIR}/tui/serve_web_tui.py"
        ;;
    6|tmux|all)
        echo "🚀 Spawning Polyglot Tmux Cockpit..."
        tmux kill-session -t lauburu_polyglot_tui 2>/dev/null || true
        tmux new-session -d -s lauburu_polyglot_tui -n "Python_Cockpit" -c "${SCRIPT_DIR}/tui" "${PYTHON_VENV} unified_mesh_cockpit_tui.py"
        tmux new-window -t lauburu_polyglot_tui:1 -n "Mesh_Transfer_Lab" -c "${SCRIPT_DIR}/tui" "${PYTHON_VENV} tui_mesh_transfer_lab.py"
        tmux new-window -t lauburu_polyglot_tui:2 -n "Rust_Ratatui" -c "${MONOREPO_ROOT}/01_apps/canonical_tui_prototypes/rust_ratatui" "cargo run --release || ./bin/canonical_tui_rust"
        tmux new-window -t lauburu_polyglot_tui:3 -n "Go_BubbleTea" -c "${MONOREPO_ROOT}/01_apps/canonical_tui_prototypes/go_bubbletea" "go run main.go || ./bin/tui_go"
        
        if [ "$(uname)" = "Darwin" ]; then
            osascript -e 'tell application "Terminal"
                do script "tmux attach -t lauburu_polyglot_tui"
                activate
            end tell'
        fi
        echo "✔ All 4 Polyglot TUIs live in tmux session: lauburu_polyglot_tui"
        ;;
    *)
        echo "Run with one of: python | rust | go | lab | web | tmux"
        ;;
esac
