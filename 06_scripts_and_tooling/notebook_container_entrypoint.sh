#!/usr/bin/env bash
# ==============================================================================
# Lauburu Master Notebook Specialist Container Entrypoint
# Boots JupyterLab on Port 8888 and Marimo on Port 2718.
# ==============================================================================
set -euo pipefail

MONOREPO_ROOT="${MONOREPO_ROOT:-/workspace}"
cd "${MONOREPO_ROOT}"

echo "=============================================================================="
echo "📓 LAUBURU NOTEBOOK & INTERACTIVE DATA SPECIALIST CONTAINER"
echo "=============================================================================="
echo "📁 Monorepo Root:    ${MONOREPO_ROOT}"
echo "📚 Obsidian Vault:   /obsidian_vault"
echo "🧠 LoRA Datasets:    /lora_datasets"
echo "🌐 JupyterLab Port:  8888 (tokenless local access)"
echo "🌐 Marimo Port:      2718 (reactive interactive notebook)"
echo "=============================================================================="

# Ensure kernel auto-path configuration exists
mkdir -p /root/.ipython/profile_default/startup
cat << 'EOF' > /root/.ipython/profile_default/startup/00-lauburu-autopath.py
import sys, os
paths = ["/workspace", "/workspace/01_apps", "/workspace/03_biometrics_and_telemetry", "/workspace/04_data_and_memory"]
for p in paths:
    if os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)
print("🧠 Lauburu Auto-Path Initialized:", sys.path[:3])
EOF

# Start Marimo in background on port 2718
echo "🚀 Starting Marimo Server on http://0.0.0.0:2718 ..."
marimo tutorial --port 2718 --host 0.0.0.0 --no-token &
MARIMO_PID=$!

# Start JupyterLab on port 8888
echo "🚀 Starting JupyterLab Server on http://0.0.0.0:8888 ..."
exec jupyter lab \
    --ip=0.0.0.0 \
    --port=8888 \
    --no-browser \
    --allow-root \
    --NotebookApp.token='' \
    --NotebookApp.password='' \
    --notebook-dir=/workspace
