#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(dirname "$SCRIPT_DIR")"

echo "========================================================"
echo "  CANONICAL PORT 4-TIER E2E TEST SUITE RUNNER"
echo "  Target: $APP_DIR"
echo "========================================================"

cd "$APP_DIR"

# 1. Build Verification (Vite React Web UI)
echo "[1/3] Verifying React / Vite Web Dashboard Build..."
npm run build

# 2. Python Textual & Pytest 4-Tier Test Execution
echo "[2/3] Executing 4-Tier Pytest Suite (Unit, Tiers 1-4)..."
uv run --with rich,textual,pyyaml,pytest,pytest-asyncio,httpx python tests/run_all_tiers.py

# 3. Overall Verdict
echo "[3/3] All verification gates certified."
echo "========================================================"
echo "  E2E TEST SUITE EXECUTION COMPLETE: 100% PASSING"
echo "========================================================"
