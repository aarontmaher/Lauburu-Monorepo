#!/usr/bin/env bash
# ==============================================================================
# 🛡️ audit_mocks.sh — Static Mock Analysis & Verification Gate
# Subsystem: 06_scripts_and_tooling/truth
# Rules: Rule 0, Rule 1 (Zero-Mock Verification Gate)
#
# Supports:
#   --target-apps   Scan 01_apps, 02_ai_models_and_inference, 03_biometrics_and_telemetry (Default)
#   --all           Scan entire monorepo
#   --staged        Scan git staged files
#
# Exit codes:
#   0: 0 BLOCK violations found in scanned target.
#   1: One or more BLOCK violations detected.
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Locate python binary
PYTHON_BIN="python3"
if [ -x "${REPO_ROOT}/.venv/bin/python" ]; then
    PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"
elif [ -x "${REPO_ROOT}/01_apps/network_cable_analyzer/.venv/bin/python" ]; then
    PYTHON_BIN="${REPO_ROOT}/01_apps/network_cable_analyzer/.venv/bin/python"
fi

SCANNER="${SCRIPT_DIR}/fake_data_scanner.py"

# Default to --target-apps if no arguments provided
if [ $# -eq 0 ]; then
    set -- "--target-apps"
fi

exec "${PYTHON_BIN}" "${SCANNER}" --exit-on-block "$@"
