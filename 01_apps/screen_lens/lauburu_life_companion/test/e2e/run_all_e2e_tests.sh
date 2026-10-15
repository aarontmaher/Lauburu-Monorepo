#!/usr/bin/env bash
# ==============================================================================
# Master Shell Wrapper for Lauburu Life Companion Opaque-Box E2E Tests
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

echo "Starting Opaque-Box E2E Test Runner..."
echo "Project Root: ${PROJECT_ROOT}"

python3 "${SCRIPT_DIR}/run_all_e2e_tests.py" "$@"
