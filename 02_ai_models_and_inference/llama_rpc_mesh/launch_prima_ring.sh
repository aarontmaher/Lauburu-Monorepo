#!/usr/bin/env bash
# =============================================================================
# launch_prima_ring.sh — Lauburu Mesh prima.cpp PRP Ring Launcher
# =============================================================================
# Starts the 4-node Pipelined-Ring Parallelism ring.
# Port 8082 — prima.cpp PRP master (Halda ILP, Metal, ZMQ)
# Port 8081 — legacy llama.cpp RPC (preserved, zero disruption)
#
# Usage:
#   bash launch_prima_ring.sh [kimi|qwen32b] [--dry-run]
# =============================================================================
set -euo pipefail

# ── Binary paths (Makefile build outputs to repo root, not build/bin/) ────────
PRIMA_BIN="${HOME}/.local/bin/prima-server"
MODEL_DIR="/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/models"
VAULT_DIR="/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf"
PRIMA_PORT=8082
WORKER_PORT=50053
SSH_OPTS="-i $HOME/.ssh/id_ed25519 -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o IdentitiesOnly=yes"

# ── Node definitions ──────────────────────────────────────────────────────────
LINUX_HOST="100.101.39.98"
LINUX_USER="linux"
LINUX_PRIMA="/home/linux/prima_cpp/llama-server"
LINUX_MODEL="/mnt/ssd_1tb/llama.cpp/models/kimi-dev-72b-instruct-q4_k_m.gguf"

MBP_HOST="100.103.212.21"     # Tailscale (TB4 169.254.187.138 as fallback)
MBP_USER="aaron"
MBP_PRIMA="/Users/aaron/prima_cpp/llama-server"
MBP_MODEL="/Volumes/NAS/AI_Models/kimi-dev-72b-instruct-q4_k_m.gguf"

MBA_HOST="100.93.158.96"      # MacBook Air M4
MBA_USER="aaron"
MBA_PRIMA="/Users/aaron/prima_cpp/llama-server"
MBA_MODEL="/Volumes/NAS/AI_Models/kimi-dev-72b-instruct-q4_k_m.gguf"

MODEL_ARG="${1:-kimi}"
DRY_RUN="${2:-}"
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN="1" && MODEL_ARG="kimi"

case "$MODEL_ARG" in
  kimi|kimi72b)
    MASTER_MODEL="$MODEL_DIR/kimi-dev-72b-instruct-q4_k_m.gguf"
    CTX=16384 ;;
  qwen32b)
    MASTER_MODEL="$VAULT_DIR/qwen2.5-coder-32b-instruct-q4_k_m.gguf"
    CTX=32768 ;;
  qwen7b)
    MASTER_MODEL="$VAULT_DIR/qwen2.5-coder-7b-instruct-q4_k_m.gguf"
    CTX=32768 ;;
  *)
    echo "[ERROR] Unknown model: $MODEL_ARG. Use: kimi | qwen32b | qwen7b"; exit 1 ;;
esac

log() { echo "[$(date '+%H:%M:%S')] $*"; }

do_ssh() {
  local host="$1" user="$2"; shift 2
  ssh $SSH_OPTS "${user}@${host}" "$@" 2>&1
}

# ─── Step 1: Verify local prima binary ────────────────────────────────────────
log "Checking local prima-server at $PRIMA_BIN..."
if [ ! -x "$PRIMA_BIN" ]; then
  # Fallback to repo copy
  PRIMA_BIN="/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/prima_cpp/llama-server"
fi
if [ ! -x "$PRIMA_BIN" ]; then
  echo "[ERROR] prima-server binary not found. Run: cd prima_cpp && make USE_HIGHS=1 -j14"
  exit 1
fi
log "  prima-server: $(${PRIMA_BIN} --version 2>&1 | head -1)"

# ─── Step 2: Launch Linux worker ──────────────────────────────────────────────
log "Starting Linux worker ($LINUX_HOST:$WORKER_PORT)..."
if [ -z "$DRY_RUN" ]; then
  do_ssh "$LINUX_HOST" "$LINUX_USER" \
    "pkill -f 'llama-server.*${WORKER_PORT}' 2>/dev/null || true; \
     nohup ${LINUX_PRIMA} --worker --port ${WORKER_PORT} \
       > /tmp/prima_worker_linux.log 2>&1 & sleep 2 && echo LINUX_WORKER_OK" || \
    log "[WARN] Linux worker launch failed — will run 2-node ring"
else
  log "[DRY-RUN] SSH $LINUX_USER@$LINUX_HOST: prima-server --worker --port $WORKER_PORT"
fi

# ─── Step 3: Launch MacBook Pro worker ───────────────────────────────────────
log "Starting MacBook Pro worker ($MBP_HOST:$WORKER_PORT)..."
if [ -z "$DRY_RUN" ]; then
  do_ssh "$MBP_HOST" "$MBP_USER" \
    "pkill -f 'prima.*${WORKER_PORT}' 2>/dev/null || true; \
     nohup ${MBP_PRIMA} --worker --port ${WORKER_PORT} -ngl 999 \
       > /tmp/prima_worker_mbp.log 2>&1 & sleep 2 && echo MBP_WORKER_OK" || \
    log "[WARN] MacBook Pro worker failed — will run without it"
else
  log "[DRY-RUN] SSH $MBP_USER@$MBP_HOST: prima-server --worker --port $WORKER_PORT"
fi

# ─── Step 4: Launch MacBook Air worker ───────────────────────────────────────
log "Starting MacBook Air worker ($MBA_HOST:$WORKER_PORT)..."
if [ -z "$DRY_RUN" ]; then
  do_ssh "$MBA_HOST" "$MBA_USER" \
    "pkill -f 'prima.*${WORKER_PORT}' 2>/dev/null || true; \
     nohup ${MBA_PRIMA} --worker --port ${WORKER_PORT} -ngl 999 \
       > /tmp/prima_worker_mba.log 2>&1 & sleep 2 && echo MBA_WORKER_OK" || \
    log "[WARN] MacBook Air worker failed — continuing"
else
  log "[DRY-RUN] SSH $MBA_USER@$MBA_HOST: prima-server --worker --port $WORKER_PORT"
fi

# ─── Step 5: Wait for workers ─────────────────────────────────────────────────
log "Waiting 8s for all workers to initialise..."
[ -z "$DRY_RUN" ] && sleep 8

# ─── Step 6: Launch master ────────────────────────────────────────────────────
NEXT_NODES="${LINUX_HOST}:${WORKER_PORT},${MBP_HOST}:${WORKER_PORT},${MBA_HOST}:${WORKER_PORT}"
log "Launching prima.cpp PRP master on port $PRIMA_PORT..."
log "  Model:   $MASTER_MODEL"
log "  Workers: $NEXT_NODES"
log "  Halda:   ILP layer-window auto-scheduling active"

CMD="${PRIMA_BIN} \
  --model \"${MASTER_MODEL}\" \
  --next \"${NEXT_NODES}\" \
  --port ${PRIMA_PORT} \
  --host 0.0.0.0 \
  --ctx-size ${CTX} \
  --parallel 2 \
  -ngl 999"

if [ -z "$DRY_RUN" ]; then
  log "Master running on :${PRIMA_PORT}. Ctrl+C to stop."
  eval $CMD
else
  log "[DRY-RUN] Would run: $CMD"
  log "[DRY-RUN] Ring ready. Port 8081 (legacy RPC) preserved."
fi
