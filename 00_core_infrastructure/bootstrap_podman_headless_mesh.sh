#!/usr/bin/env bash
# ==============================================================================
# LAUBURU SOVEREIGN MESH — PODMAN FULL-ACCESS NETWORK & LOCAL AI TRAINING BOOTSTRAP
# ==============================================================================
# 1. Configures rootless/system Podman sockets on Linux Compute Nodes (L8 100.121.247.8 & L3 100.101.39.98)
# 2. Configures `podman system connection` on macOS Sanctuary Nodes (L5 & L1) for 0 MB VM RAM overhead
# 3. Synchronizes full monorepo datasets, EmbeddingGemma 2 orchestrator, and training scripts to L8 & L3
# 4. Deploys `podman-local-ai-trainer` (:8096) with full access to Monorepo, LoRA datasets,
#    EmbeddingGemma 2 (:8087), Neo4j 5.26.32 (:7474/:7687), and Qdrant MRL (:6333).
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MONOREPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

L8_HOST="linuxmini@100.121.247.8"
L8_REPO="/home/linuxmini/DFS_UNIFIED/Lauburu-Monorepo"

L3_HOST="linux@100.101.39.98"
L3_REPO="/home/linux/DFS_UNIFIED/Lauburu-Monorepo"

EMBEDDINGGEMMA2_URL="${EMBEDDINGGEMMA2_URL:-http://100.119.199.76:8087/v1/embeddings}"
NEO4J_HTTP_URL="${NEO4J_HTTP_URL:-http://100.101.39.98:7474/db/neo4j/tx/commit}"
NEO4J_BOLT_URI="${NEO4J_BOLT_URI:-bolt://100.101.39.98:7687}"
QDRANT_URL="${QDRANT_URL:-http://100.101.39.98:6333}"
LENS_CHAT_URL="${LENS_CHAT_URL:-http://100.119.199.76:8090/v1/chat/completions}"

echo "================================================================================"
echo " [1/4] Configuring Remote Podman Connections (Zero Mac VM RAM Overhead)"
echo "================================================================================"
if command -v podman >/dev/null 2>&1; then
    SSH_KEY="${HOME}/.ssh/id_ed25519"
    if [ ! -f "${SSH_KEY}" ] && [ -f "${HOME}/.ssh/id_rsa" ]; then
        SSH_KEY="${HOME}/.ssh/id_rsa"
    fi
    podman system connection remove lauburu-l8 >/dev/null 2>&1 || true
    podman system connection remove lauburu-l3 >/dev/null 2>&1 || true
    if [ -f "${SSH_KEY}" ]; then
        podman system connection add --identity "${SSH_KEY}" --default lauburu-l8 "ssh://linuxmini@100.121.247.8:22/run/user/1000/podman/podman.sock" || true
        podman system connection add --identity "${SSH_KEY}" lauburu-l3 "ssh://linux@100.101.39.98:22/run/user/1000/podman/podman.sock" || true
    fi
    podman system connection list || true
fi

echo "================================================================================"
echo " [2/4] Syncing Full Monorepo Datasets, Scripts & Configs to L8 and L3"
echo "================================================================================"
for TARGET_SPEC in "${L8_HOST}:${L8_REPO}" "${L3_HOST}:${L3_REPO}"; do
    HOST="${TARGET_SPEC%%:*}"
    REMOTE_DIR="${TARGET_SPEC#*:}"
    echo " -> Preparing directories on ${HOST}:${REMOTE_DIR} ..."
    ssh -o ConnectTimeout=6 "${HOST}" "mkdir -p ${REMOTE_DIR}/00_core_infrastructure ${REMOTE_DIR}/02_ai_models_and_inference/models/lora_adapters ${REMOTE_DIR}/04_data_and_memory/data ${REMOTE_DIR}/06_scripts_and_tooling/network ${REMOTE_DIR}/obsidian_vault/04_ANALYTICS ${REMOTE_DIR}/01_apps/screen_lens"
    rsync -az --timeout=20 \
        "${MONOREPO_ROOT}/00_core_infrastructure/podman-compose-headless-mesh.yml" \
        "${MONOREPO_ROOT}/00_core_infrastructure/bootstrap_podman_headless_mesh.sh" \
        "${HOST}:${REMOTE_DIR}/00_core_infrastructure/"
    rsync -az --timeout=20 \
        "${MONOREPO_ROOT}/06_scripts_and_tooling/lens_neo4j_gemma2_orchestrator.py" \
        "${MONOREPO_ROOT}/06_scripts_and_tooling/podman_local_ai_trainer.py" \
        "${HOST}:${REMOTE_DIR}/06_scripts_and_tooling/"
    rsync -az --timeout=20 \
        "${MONOREPO_ROOT}/06_scripts_and_tooling/network/chrome_devtools_sentinel_bridge.py" \
        "${HOST}:${REMOTE_DIR}/06_scripts_and_tooling/network/"
    rsync -az --timeout=20 \
        "${MONOREPO_ROOT}/04_data_and_memory/data/"*.jsonl \
        "${HOST}:${REMOTE_DIR}/04_data_and_memory/data/"
    rsync -az --timeout=20 \
        "${MONOREPO_ROOT}/01_apps/screen_lens/chrome_extension" \
        "${HOST}:${REMOTE_DIR}/01_apps/screen_lens/"
done

echo "================================================================================"
echo " [3/4] Launching Podman Local AI Trainer (:8096) on L8 & L3 with Full Access"
echo "================================================================================"
for TARGET_SPEC in "L8:${L8_HOST}:${L8_REPO}" "L3:${L3_HOST}:${L3_REPO}"; do
    NODE_ID="${TARGET_SPEC%%:*}"
    REST="${TARGET_SPEC#*:}"
    HOST="${REST%%:*}"
    REMOTE_DIR="${REST#*:}"
    echo " -> Deploying podman-local-ai-trainer on ${NODE_ID} (${HOST}) ..."
    ssh -o ConnectTimeout=8 "${HOST}" "
        mv ~/.docker/config.json ~/.docker/config.json.bak 2>/dev/null || true
        systemctl --user enable --now podman.socket 2>/dev/null || sudo -n systemctl enable --now podman.socket 2>/dev/null || true
        podman rm -f podman-local-ai-trainer >/dev/null 2>&1 || true
        podman run -d \
            --name podman-local-ai-trainer \
            --restart always \
            --network host \
            -e LAUBURU_NODE_ID=${NODE_ID} \
            -e LAUBURU_MONOREPO_ROOT=/workspace \
            -e EMBEDDINGGEMMA2_URL=${EMBEDDINGGEMMA2_URL} \
            -e NEO4J_HTTP_URL=${NEO4J_HTTP_URL} \
            -e NEO4J_BOLT_URI=${NEO4J_BOLT_URI} \
            -e QDRANT_URL=${QDRANT_URL} \
            -e LENS_CHAT_URL=${LENS_CHAT_URL} \
            -v ${REMOTE_DIR}:/workspace:Z \
            -v \${HOME}/.ssh:/root/.ssh:ro \
            docker.io/library/python:3.11-slim \
            python3 /workspace/06_scripts_and_tooling/podman_local_ai_trainer.py --daemon --port 8096
        podman ps --filter name=podman-local-ai-trainer
    "
done

echo "================================================================================"
echo " [4/4] Verifying Podman Local AI Trainer Endpoints"
echo "================================================================================"
sleep 2
curl -s http://100.121.247.8:8096/status | head -n 25 || true
curl -s http://100.101.39.98:8096/status | head -n 25 || true
echo "✅ Podman Full-Access Local AI Mesh Deployment Complete."
