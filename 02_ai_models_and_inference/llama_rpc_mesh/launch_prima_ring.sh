#!/usr/bin/env bash
# =============================================================================
# launch_prima_ring.sh — Lauburu Mesh prima.cpp PRP Ring Launcher
# =============================================================================
set -euo pipefail

PRIMA_BIN="${HOME}/.local/bin/llama-server"
VAULT_DIR="/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf"
PRIMA_PORT=8085
WORKER_PORT=50053
SSH_OPTS="-i $HOME/.ssh/id_rsa -o StrictHostKeyChecking=no -o ConnectTimeout=5 -o IdentitiesOnly=yes"

# MBP L2
MBP_HOST="100.103.212.21"
MBP_USER="aaronmaher"
MBP_PRIMA="/usr/local/bin/llama-server"

# MBA L5 (Fixed IP & User after reset)
MBA_HOST="100.121.202.34"
MBA_USER="aaronmaher"
MBA_PRIMA="/usr/local/bin/llama-server"

MASTER_MODEL="$VAULT_DIR/qwen_38_max.gguf"
CTX=32768
NGL_PER_NODE=30 # Leaves VRAM for other tasks (Rule 3 + User request)

log() { echo "[$(date '+%H:%M:%S')] $*"; }
do_ssh() {
  local host="$1" user="$2"; shift 2
  ssh $SSH_OPTS "${user}@${host}" "$@" 2>&1
}

log "Starting MacBook Pro worker ($MBP_HOST)..."
do_ssh "$MBP_HOST" "$MBP_USER" \
  "pkill -f 'llama-server.*${WORKER_PORT}' 2>/dev/null || true; \
   nohup ${MBP_PRIMA} --rpc-server --host 0.0.0.0 --port ${WORKER_PORT} > /tmp/prima_worker_mbp.log 2>&1 & sleep 2" || log "[WARN] MBP worker failed"

log "Starting MacBook Air worker ($MBA_HOST)..."
do_ssh "$MBA_HOST" "$MBA_USER" \
  "pkill -f 'llama-server.*${WORKER_PORT}' 2>/dev/null || true; \
   nohup ${MBA_PRIMA} --rpc-server --host 0.0.0.0 --port ${WORKER_PORT} > /tmp/prima_worker_mba.log 2>&1 & sleep 2" || log "[WARN] MBA worker failed"

log "Waiting 5s for all workers to initialise..."
sleep 5

NEXT_NODES="${MBP_HOST}:${WORKER_PORT},${MBA_HOST}:${WORKER_PORT}"
log "Launching prima.cpp PRP master on port $PRIMA_PORT..."

CMD="${PRIMA_BIN} \
  -m \"${MASTER_MODEL}\" \
  --rpc \"${NEXT_NODES}\" \
  --port ${PRIMA_PORT} \
  --host 0.0.0.0 \
  -c ${CTX} \
  -ngl 30" # 30 layers on host, rest distributed to RPCs. 

log "Master running on :${PRIMA_PORT} in background."
eval "nohup $CMD > /tmp/prima_master.log 2>&1 &"
log "DONE."
