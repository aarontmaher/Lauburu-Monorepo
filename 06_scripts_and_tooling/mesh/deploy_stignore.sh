#!/usr/bin/env bash
# ==============================================================================
# 06_scripts_and_tooling/mesh/deploy_stignore.sh
# Deploys comprehensive (?d) .stignore patterns to federated Syncthing folders
# prevents binary bloat (.venv, node_modules, target, filerldb2, caches)
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Target folders for .stignore deployment
TARGET_FOLDERS=(
  "${REPO_ROOT}/00_core_infrastructure"
  "${REPO_ROOT}/06_scripts_and_tooling"
  "${REPO_ROOT}/obsidian_vault"
)

# Optional additional folders passed via command line
if [ "$#" -gt 0 ]; then
  TARGET_FOLDERS=("$@")
fi

STIGNORE_CONTENT=$(cat << 'EOF'
// === Lauburu Zero-Bloat Syncthing Ignore Specification ===
(?d).git
(?d).git/**
(?d).github
(?d).agents
(?d).agents/**
(?d)__pycache__
(?d)**/__pycache__
(?d)*.pyc
(?d)**/*.pyc
(?d)*.pyo
(?d).pytest_cache
(?d)**/.pytest_cache
(?d).mypy_cache
(?d).ruff_cache
(?d).venv
(?d)**/.venv
(?d)venv*
(?d)**/venv*
(?d)node_modules
(?d)**/node_modules
(?d).npm
(?d).yarn
(?d)target
(?d)**/target
(?d)filerldb2
(?d)**/filerldb2
(?d)*.db-shm
(?d)*.db-wal
(?d)*.lock
(?d)*.sock
(?d)*.pid
(?d)*.tmp
(?d)*.tmp.*
(?d).DS_Store
(?d)**/.DS_Store
(?d)._*
(?d)**/.thumb*
(?d)Thumbs.db
(?d)*.sync-conflict-*
(?d).stversions
EOF
)

echo "🛡️ Deploying comprehensive (?d) .stignore specification..."
DEPLOYED_COUNT=0

for folder in "${TARGET_FOLDERS[@]}"; do
  if [ -d "$folder" ]; then
    echo "$STIGNORE_CONTENT" > "${folder}/.stignore"
    echo "  ✅ Deployed to: ${folder}/.stignore"
    DEPLOYED_COUNT=$((DEPLOYED_COUNT + 1))
  else
    echo "  ⚠️ Directory not found, creating and deploying: ${folder}"
    mkdir -p "$folder"
    echo "$STIGNORE_CONTENT" > "${folder}/.stignore"
    DEPLOYED_COUNT=$((DEPLOYED_COUNT + 1))
  fi
done

echo "🎉 Successfully deployed .stignore to ${DEPLOYED_COUNT} locations."
exit 0
