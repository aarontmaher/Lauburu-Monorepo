#!/usr/bin/env bash
# ==============================================================================
# Lauburu TUI Specialist Container Entrypoint
# Boots polyglot TUI engines, builds binaries if needed, and starts ttyd on port 8088.
# ==============================================================================
set -euo pipefail

MONOREPO_ROOT="${MONOREPO_ROOT:-/workspace}"
cd "${MONOREPO_ROOT}"

echo "=============================================================================="
echo "⚡ LAUBURU POLYGLOT TUI SPECIALIST CONTAINER"
echo "=============================================================================="
echo "📁 Monorepo Root:    ${MONOREPO_ROOT}"
echo "📚 Obsidian Vault:   /obsidian_vault"
echo "🧠 LoRA Datasets:    /lora_datasets"
echo "🌐 Web-TUI Port:     8088 (ttyd terminal streamer)"
echo "=============================================================================="

# Pre-build C/ncurses binary if missing
if [ -d "${MONOREPO_ROOT}/01_apps/canonical_tui_prototypes/c_ncurses" ]; then
    echo "🔨 Checking C/ncurses binary..."
    cd "${MONOREPO_ROOT}/01_apps/canonical_tui_prototypes/c_ncurses"
    make >/dev/null 2>&1 || true
fi

# Pre-build Go binary if missing
if [ -d "${MONOREPO_ROOT}/01_apps/canonical_tui_prototypes/go_bubbletea" ]; then
    echo "🔨 Checking Go Bubble Tea binary..."
    cd "${MONOREPO_ROOT}/01_apps/canonical_tui_prototypes/go_bubbletea"
    go build -o bin/canonical_tui_go main.go >/dev/null 2>&1 || true
fi

# Pre-build Rust Ratatui binary if missing
if [ -d "${MONOREPO_ROOT}/01_apps/canonical_tui_prototypes/rust_ratatui" ]; then
    echo "🔨 Checking Rust Ratatui binary..."
    cd "${MONOREPO_ROOT}/01_apps/canonical_tui_prototypes/rust_ratatui"
    cargo build --release >/dev/null 2>&1 || true
fi

cd "${MONOREPO_ROOT}"

# Create tmux multi-window session with all 4 polyglot TUIs
tmux kill-session -t lauburu_tui 2>/dev/null || true
tmux new-session -d -s lauburu_tui -n "Python_Textual" "python3 01_apps/canonical_tui_prototypes/python_textual/app.py"
tmux new-window -t lauburu_tui:1 -n "Rust_Ratatui" "01_apps/canonical_tui_prototypes/rust_ratatui/target/release/canonical_tui_rust || 01_apps/canonical_tui_prototypes/rust_ratatui/bin/canonical_tui_rust"
tmux new-window -t lauburu_tui:2 -n "Go_BubbleTea" "01_apps/canonical_tui_prototypes/go_bubbletea/bin/canonical_tui_go"
tmux new-window -t lauburu_tui:3 -n "C_Ncurses" "01_apps/canonical_tui_prototypes/c_ncurses/bin/canonical_tui_c"
tmux new-window -t lauburu_tui:4 -n "Practice_Shell" "bash"

echo "✔ Polyglot tmux session 'lauburu_tui' initialized with 5 windows (Python, Rust, Go, C, Shell)."

# If interactive mode requested, attach tmux directly
if [ "${1:-}" = "tmux" ] || [ "${1:-}" = "shell" ]; then
    exec tmux attach -t lauburu_tui
fi

# Otherwise launch ttyd web terminal on port 8088
echo "🚀 Starting ttyd on 0.0.0.0:8088 ..."
exec ttyd -p 8088 -W -t fontSize=14 -t fontFamily="monospace" tmux attach -t lauburu_tui
