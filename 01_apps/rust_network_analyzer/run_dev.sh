#!/usr/bin/env bash
# 01_apps/rust_network_analyzer/run_dev.sh
# Automated Hot-Reloading Dev Mode Runner for Lauburu Network Lens

set -e

PROJECT_DIR="/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/rust_network_analyzer"
cd "$PROJECT_DIR"

echo "🔥 Starting Lauburu Network Lens in Hot-Reload DEV Mode..."
echo "📂 Watching $PROJECT_DIR/src for code changes..."

FSWATCH_BIN=""
if [ -x "/Users/aaron/.local/bin/fswatch" ]; then
    FSWATCH_BIN="/Users/aaron/.local/bin/fswatch"
elif command -v fswatch >/dev/null 2>&1; then
    FSWATCH_BIN=$(command -v fswatch)
fi

cargo build --release

if [ -n "$FSWATCH_BIN" ]; then
    while true; do
        "$PROJECT_DIR/target/release/lauburu_network_lens" --dev || true
        echo "👀 Watching for file modifications in src/ to hot-reload (or press Ctrl+C to stop)..."
        "$FSWATCH_BIN" -1 -r "$PROJECT_DIR/src" "$PROJECT_DIR/Cargo.toml"
        echo "⚡ Detected file modification! Recompiling..."
        cargo build --release
    done
else
    "$PROJECT_DIR/target/release/lauburu_network_lens" --dev
fi
