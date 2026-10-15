#!/usr/bin/env bash
# ==============================================================================
# Sovereign Nexus Canonical Shell Wrapper — installnexus
# ==============================================================================

set -euo pipefail

REPO_ROOT="/Volumes/Lauburu-Monorepo"
PYTHON_BIN="/Users/aaron/.venv/bin/python3"
INSTALL_SCRIPT="${REPO_ROOT}/06_scripts_and_tooling/install_nexus.py"

if [ ! -x "${PYTHON_BIN}" ]; then
    PYTHON_BIN="$(which python3)"
fi

exec "${PYTHON_BIN}" "${INSTALL_SCRIPT}" "$@"
