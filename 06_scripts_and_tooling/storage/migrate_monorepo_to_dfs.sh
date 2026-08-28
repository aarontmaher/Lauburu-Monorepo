#!/usr/bin/env bash
set -euo pipefail

# 06_scripts_and_tooling/storage/migrate_monorepo_to_dfs.sh
# Fast shell launcher for DFS migration engine

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="/usr/bin/python3"

echo "[DFS-Launcher] Starting Lauburu Monorepo DFS Migration..."
exec "$PYTHON_BIN" "$SCRIPT_DIR/migrate_monorepo_to_dfs.py" "$@"
