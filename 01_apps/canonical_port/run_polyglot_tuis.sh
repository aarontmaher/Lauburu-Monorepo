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
echo "⚡ LAUBURU MASTER CLI RUNNER & BENCHMARK SUITE"
echo "=============================================================================="
echo ""
echo "📋 LIST 1: ALL-IN-ONE MULTI-WINDOW TMUX COCKPITS"
echo "  • [tmux]           - Full Polyglot TUI Session (Switch with Ctrl+b 0..3)"
echo "  • [tmux-lab]       - Dedicated Mesh Transfer Lab Session (95% CI Tests)"
echo ""
echo "📋 LIST 2: DIRECT SINGLE-LANGUAGE TUI FRONTENDS"
echo "  • [python]         - Python Textual Unified Mesh Cockpit (Port 4000 Integration)"
echo "  • [rust]           - Rust Ratatui Native Immediate-Mode TUI (Sub-ms 120 FPS)"
echo "  • [go]             - Go Bubble Tea Elm-Architecture TUI (Zero-Alloc Goroutines)"
echo "  • [lab]            - Mesh Transfer Lab (Statistical 95% CI & Chaos Tests)"
echo "  • [web]            - Web Browser TUI on Port 8088 (textual-web)"
echo ""
echo "📋 LIST 3: DEDICATED LOCAL AI TRAINING & LORA DISTILLATION TASKS"
echo "  • [train-prepare]  - Assemble & validate 63,385 multi-domain agent action samples"
echo "  • [train-mlx]      - Launch Apple MLX Metal QLoRA fast-training on Apple M4 Pro"
echo "  • [train-sft-st1]  - Launch SFT Stage 1 (MCP Tool-Calling & Terminal Automation)"
echo "  • [train-sft-st2]  - Launch SFT Stage 2 (SWE Code Patches & Android ADB Actions)"
echo "  • [train-rl-st3]   - Launch Stage 3 (RL Governor Reward & System Admin Tuning)"
echo "  • [train-game]     - Run Autonomous AI Game Arena Training & ELO Evolution"
echo "=============================================================================="

case "${TARGET}" in
    # ── LIST 1: INTEGRATED POLYGLOT SINGLE TUI & TMUX ───────────────────────────
    single|polyglot|integrated|unified)
        echo "🚀 Launching Integrated Polyglot Single TUI (Rust + Go + Python + Metal)..."
        export PYTHONPATH="${SCRIPT_DIR}/tui:${SCRIPT_DIR}:${PYTHONPATH:-}"
        exec "${PYTHON_VENV}" "${SCRIPT_DIR}/tui/polyglot_unified_cockpit.py"
        ;;
    tmux|all)
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
    tmux-lab|lab-session)
        echo "🚀 Spawning Mesh Transfer Lab in Tmux..."
        "${SCRIPT_DIR}/run_mesh_transfer_lab.sh"
        ;;

    # ── LIST 2: SINGLE-LANGUAGE TUI FRONTENDS ───────────────────────────────────
    python|textual)
        echo "🚀 Launching Python Textual Unified Cockpit..."
        export PYTHONPATH="${SCRIPT_DIR}/tui:${SCRIPT_DIR}:${PYTHONPATH:-}"
        exec "${PYTHON_VENV}" "${SCRIPT_DIR}/tui/unified_mesh_cockpit_tui.py"
        ;;
    rust|ratatui)
        echo "🚀 Launching Rust Ratatui Cockpit..."
        RUST_BIN="${MONOREPO_ROOT}/01_apps/canonical_tui_prototypes/rust_ratatui/bin/canonical_tui_rust"
        if [ -x "${RUST_BIN}" ]; then
            exec "${RUST_BIN}"
        else
            cd "${MONOREPO_ROOT}/01_apps/canonical_tui_prototypes/rust_ratatui"
            exec cargo run --release
        fi
        ;;
    go|bubbletea)
        echo "🚀 Launching Go Bubble Tea Cockpit..."
        GO_BIN="${MONOREPO_ROOT}/01_apps/canonical_tui_prototypes/go_bubbletea/bin/tui_go"
        if [ -x "${GO_BIN}" ]; then
            exec "${GO_BIN}"
        else
            cd "${MONOREPO_ROOT}/01_apps/canonical_tui_prototypes/go_bubbletea"
            exec go run main.go
        fi
        ;;
    lab|transfer)
        echo "🚀 Launching Mesh Transfer Lab..."
        export PYTHONPATH="${SCRIPT_DIR}/tui:${SCRIPT_DIR}:${PYTHONPATH:-}"
        exec "${PYTHON_VENV}" "${SCRIPT_DIR}/tui/tui_mesh_transfer_lab.py"
        ;;
    web)
        echo "🚀 Serving Web TUI on http://0.0.0.0:8088 ..."
        export PYTHONPATH="${SCRIPT_DIR}/tui:${SCRIPT_DIR}:${PYTHONPATH:-}"
        exec "${PYTHON_VENV}" "${SCRIPT_DIR}/tui/serve_web_tui.py"
        ;;

    # ── LIST 3: DEDICATED AI TRAINING & LORA DISTILLATION TASKS ────────────────
    train-prepare|prepare)
        echo "📦 Preparing & validating 63,385 multi-domain agent action samples..."
        exec "${PYTHON_VENV}" "${MONOREPO_ROOT}/04_data_and_memory/fast_train_agentworld_mac.py" --prepare-only
        ;;
    train-mlx|mlx)
        echo "⚡ Launching Apple MLX Metal QLoRA fast-training on Apple M4 Pro..."
        exec "${PYTHON_VENV}" "${MONOREPO_ROOT}/04_data_and_memory/fast_train_agentworld_mac.py" --backend mlx --stage 1 --iters 500
        ;;
    train-sft-st1|sft1)
        echo "🚀 Launching SFT Stage 1 (MCP & Terminal Tool-Calling)..."
        exec "${PYTHON_VENV}" "${MONOREPO_ROOT}/04_data_and_memory/agentworld_train.py" --model agentworld_35b --stage 1
        ;;
    train-sft-st2|sft2)
        echo "🚀 Launching SFT Stage 2 (SWE Code Patches & Android ADB)..."
        exec "${PYTHON_VENV}" "${MONOREPO_ROOT}/04_data_and_memory/agentworld_train.py" --model agentworld_35b --stage 2
        ;;
    train-rl-st3|rl3)
        echo "🚀 Launching Stage 3 (RL Governor Reward & System Admin)..."
        exec "${PYTHON_VENV}" "${MONOREPO_ROOT}/04_data_and_memory/agentworld_train.py" --model agentworld_35b --stage 3
        ;;
    train-game|game)
        echo "🎮 Running Autonomous AI Game Arena Training & ELO Evolution..."
        exec "${PYTHON_VENV}" "${MONOREPO_ROOT}/00_core_infrastructure/self_healing_hub/src/game_arena_manager.py" --simulate-round
        ;;

    menu|*)
        echo "Run with any flag above, e.g.:"
        echo "  $0 tmux          (All-in-One Tmux Session)"
        echo "  $0 rust          (Rust Ratatui)"
        echo "  $0 train-mlx     (Apple MLX Metal QLoRA Training)"
        ;;
esac
