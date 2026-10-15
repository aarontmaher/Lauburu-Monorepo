#!/usr/bin/env bash
# ==============================================================================
# Lauburu Flutter & Swift Container Entrypoint
# Boots Rust backend on Port 4000 and serves Flutter Console UI on Port 4001.
# ==============================================================================
set -euo pipefail

MONOREPO_ROOT="${MONOREPO_ROOT:-/workspace}"
cd "${MONOREPO_ROOT}"

echo "=============================================================================="
echo "🚀 LAUBURU FLUTTER & SWIFT SPECIALIST CONTAINER — PORT 4000 CONSOLE"
echo "=============================================================================="

# Build and start Rust backend on Port 4000
echo "🦀 Building & starting Port 4000 Rust backend..."
cd "${MONOREPO_ROOT}/01_apps/port_4000_flutter_rust/rust_backend"
cargo build --release
./target/release/port4000_server &
RUST_PID=$!
echo "✔ Rust backend running with PID ${RUST_PID} on http://0.0.0.0:4000"

# Generate Flutter web build
echo "📱 Generating Flutter Console Web assets..."
cd "${MONOREPO_ROOT}/01_apps/port_4000_flutter_rust/flutter_ui"
dart lib/main.dart

# Serve Flutter web UI on Port 4001 using Python HTTP server
echo "🌐 Serving Flutter Web UI on http://0.0.0.0:4001 ..."
cd "${MONOREPO_ROOT}/01_apps/port_4000_flutter_rust/flutter_ui/build"
python3 -m http.server 4001 &
UI_PID=$!

trap "kill ${RUST_PID} ${UI_PID} 2>/dev/null || true" EXIT

echo "=============================================================================="
echo "✅ Port 4000 Ecosystem is ONLINE:"
echo "   • Backend API & Websocket: http://0.0.0.0:4000"
echo "   • Flutter Web Console UI:  http://0.0.0.0:4001"
echo "=============================================================================="

wait ${RUST_PID}
