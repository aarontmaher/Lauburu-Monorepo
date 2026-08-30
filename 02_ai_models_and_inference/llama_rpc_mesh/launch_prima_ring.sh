#!/usr/bin/env bash
# =============================================================================
# launch_prima_ring.sh — Lauburu Mesh prima.cpp PRP Ring Launcher
# =============================================================================
# Starts the 3-node Pipelined-Ring Parallelism ring for Kimi-Dev-72B inference.
# Port 8082 — prima.cpp PRP (NEW, Halda ILP dynamic scheduling)
# Port 8081 — legacy llama.cpp RPC (preserved, unchanged)
#
# Usage:
#   bash launch_prima_ring.sh [--model kimi|llama4] [--dry-run]
# =============================================================================
set -euo pipefail

PRIMA_BIN="/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/prima_cpp/build/bin/llama-server"
MODEL_DIR="/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/models"
PRIMA_PORT=8082
WORKER_PORT=50053
SSH_KEY="$HOME/.ssh/id_ed25519"

LINUX_HOST="100.101.39.98"
LINUX_USER="linux"
LINUX_PRIMA="/home/linux/prima_cpp/build/bin/llama-server"
LINUX_MODEL="/mnt/ssd_1tb/llama.cpp/models/kimi-dev-72b-instruct-q4_k_m.gguf"

MBP_HOST="169.254.187.138"   # TB4 DMA for minimum latency
MBP_USER="aaron"
MBP_PRIMA="/Users/aaron/prima_cpp/build/bin/llama-server"
MBP_MODEL="/Volumes/NAS/AI_Models/kimi-dev-72b-instruct-q4_k_m.gguf"

MODEL_ARG="${1:-kimi}"
DRY_RUN="${2:-}"

case "$MODEL_ARG" in
  kimi|kimi72b)
    MASTER_MODEL="$MODEL_DIR/kimi-dev-72b-instruct-q4_k_m.gguf"
    CTX=16384
    ;;
  llama4|scout)
    MASTER_MODEL="$MODEL_DIR/../model_vault_gguf/Llama-4-Scout-17B-16E-Instruct-Q4_K_M-00001-of-00002.gguf"
    CTX=32768
    ;;
  *)
    echo "[ERROR] Unknown model: $MODEL_ARG. Use: kimi | llama4"; exit 1
    ;;
esac

log() { echo "[$(date -u +%H:%M:%S)] $*"; }

# ─── Step 1: Health-check prima binary ────────────────────────────────────────
if [ ! -x "$PRIMA_BIN" ]; then
  echo "[ERROR] prima-server binary not found at: $PRIMA_BIN"
  echo "        Run: cmake --build prima_cpp/build --config Release"
  exit 1
fi

# ─── Step 2: Launch Linux worker node ─────────────────────────────────────────
log "Starting Linux worker (Tailscale $LINUX_HOST, port $WORKER_PORT)..."
if [ -z "$DRY_RUN" ]; then
  ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=8 \
    "${LINUX_USER}@${LINUX_HOST}" \
    "pkill -f 'prima.*${WORKER_PORT}' 2>/dev/null; \
     nohup ${LINUX_PRIMA} --worker --port ${WORKER_PORT} \
       --model ${LINUX_MODEL} \
       > /tmp/prima_worker_linux.log 2>&1 &
     sleep 2 && echo LINUX_WORKER_OK"
else
  log "[DRY-RUN] Would SSH: ${LINUX_USER}@${LINUX_HOST} prima-server --worker --port ${WORKER_PORT}"
fi

# ─── Step 3: Launch MacBook Pro TB4 worker ───────────────────────────────────
log "Starting MacBook Pro TB4 worker ($MBP_HOST, port $WORKER_PORT)..."
if [ -z "$DRY_RUN" ]; then
  ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=8 \
    "${MBP_USER}@${MBP_HOST}" \
    "pkill -f 'prima.*${WORKER_PORT}' 2>/dev/null; \
     nohup ${MBP_PRIMA} --worker --port ${WORKER_PORT} \
       --model ${MBP_MODEL} \
       -ngl 999 \
       > /tmp/prima_worker_mbp.log 2>&1 &
     sleep 2 && echo MBP_WORKER_OK"
else
  log "[DRY-RUN] Would SSH: ${MBP_USER}@${MBP_HOST} prima-server --worker --port ${WORKER_PORT}"
fi

# ─── Step 4: Wait for workers to be ready ─────────────────────────────────────
log "Waiting 5s for workers to initialise..."
[ -z "$DRY_RUN" ] && sleep 5

# ─── Step 5: Launch master with Halda ILP + PRP ───────────────────────────────
log "Starting prima.cpp PRP master on port $PRIMA_PORT..."
log "  Model:   $MASTER_MODEL"
log "  Workers: ${LINUX_HOST}:${WORKER_PORT}, ${MBP_HOST}:${WORKER_PORT}"
log "  Halda:   auto layer-window + GPU-offload depth (ILP solver)"
log "  Legacy llama-server (port 8081) preserved — no disruption."

CMD="${PRIMA_BIN} \
  --model \"${MASTER_MODEL}\" \
  --next \"${LINUX_HOST}:${WORKER_PORT},${MBP_HOST}:${WORKER_PORT}\" \
  --port ${PRIMA_PORT} \
  --host 0.0.0.0 \
  --ctx-size ${CTX} \
  --parallel 2 \
  -ngl 999"

if [ -z "$DRY_RUN" ]; then
  log "Launching master... (Ctrl+C to stop)"
  eval $CMD
else
  log "[DRY-RUN] Would run: $CMD"
  log "[DRY-RUN] Launch complete."
fi
