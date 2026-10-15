#!/usr/bin/env bash
# ==============================================================================
# Start KwaaiNet P2P Transport Daemon
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MONOREPO_ROOT="/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo"
mkdir -p "${MONOREPO_ROOT}/session_logs"

pkill -f "kwaai-p2p" 2>/dev/null || true

cd "${SCRIPT_DIR}"
cargo build --release 2>/dev/null || cargo run -- --bind "0.0.0.0:50054" --daemon > "${MONOREPO_ROOT}/session_logs/kwaainet_daemon.log" 2>&1 &

echo "✔ KwaaiNet P2P Transport Daemon active on Port 50054."
