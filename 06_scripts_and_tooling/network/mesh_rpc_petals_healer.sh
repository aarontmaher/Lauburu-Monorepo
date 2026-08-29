#!/usr/bin/env bash
# =============================================================================
# LAUBURU MESH — llama.cpp RPC + Petals Self-Healing Network Governor
# Runs across all 7 nodes via SSH. Called every 120s by launchd.
# =============================================================================
set -euo pipefail

LOG=/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/logs/mesh_rpc_petals.log
LORA_LOG=/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/data/lora_datasets/nomad_autonomous_actions.jsonl
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
exec >> "$LOG" 2>&1

log() { echo "[$TIMESTAMP] $*"; }

# ─── MESH NODE TABLE ────────────────────────────────────────────────────────
declare -A NODE_USER=(
  [macbook_pro]="aaronmaher"
  [linux_head]="linux"
  [pixel]="u0_a363"
)
declare -A NODE_HOST=(
  [macbook_pro]="192.168.8.127"
  [linux_head]="100.101.39.98"
  [pixel]="100.73.38.87"
)
declare -A NODE_PORT=(
  [macbook_pro]="22"
  [linux_head]="22"
  [pixel]="8022"
)
declare -A NODE_JUMP=(
  [macbook_pro]="root@192.168.8.1"
  [linux_head]=""
  [pixel]=""
)
declare -A LLAMA_RPC_BIN=(
  [macbook_pro]="/Users/aaronmaher/llama.cpp/build/bin/ggml-rpc-server"
  [linux_head]="/home/linux/llama.cpp/build/bin/ggml-rpc-server"
  [pixel]="/data/data/com.termux/files/home/llama.cpp/build/bin/ggml-rpc-server"
)
declare -A PETALS_MODEL=(
  [linux_head]="Qwen/Qwen2-7B-Instruct"
  [pixel]="Qwen/Qwen2-7B-Instruct"
)

# ─── SSH HELPER ─────────────────────────────────────────────────────────────
ssh_cmd() {
  local node="$1"; shift
  local user="${NODE_USER[$node]}"
  local host="${NODE_HOST[$node]}"
  local port="${NODE_PORT[$node]}"
  local jump="${NODE_JUMP[$node]:-}"
  local proxy_args=""
  [[ -n "$jump" ]] && proxy_args="-o ProxyJump=$jump"
  ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -o BatchMode=yes \
      -p "$port" $proxy_args "${user}@${host}" "$@" 2>/dev/null
}

# ─── RPC HEALTH CHECK + RESTART ─────────────────────────────────────────────
heal_rpc() {
  local node="$1"
  local rpc_bin="${LLAMA_RPC_BIN[$node]}"
  local host="${NODE_HOST[$node]}"

  # Check TCP port 50052
  if nc -z -w2 "$host" 50052 2>/dev/null; then
    log "✅ RPC $node ($host:50052) HEALTHY"
    return 0
  fi

  log "⚠️  RPC $node OFFLINE — attempting restart"
  ssh_cmd "$node" "nohup $rpc_bin -H 0.0.0.0 -p 50052 > /tmp/llama_rpc_${node}.log 2>&1 & echo started" && \
    log "✅ RPC $node restarted" || \
    log "❌ RPC $node restart FAILED"

  # Log to LoRA dataset
  echo "{\"timestamp_utc\":\"$TIMESTAMP\",\"instruction\":\"Nomad Governor: heal mesh RPC daemon\",\"input\":\"Heal mesh RPC node $node\",\"output\":\"Result: RESTARTED\",\"action\":\"HEAL_RPC_${node^^}\",\"result\":\"RESTARTED\",\"nomad_agent\":\"Multi-WAN Nomad Courier v3.0\"}" >> "$LORA_LOG"
}

# ─── PETALS HEALTH CHECK + RESTART ─────────────────────────────────────────
heal_petals() {
  local node="$1"
  local model="${PETALS_MODEL[$node]}"

  # Check if petals process is running
  local running
  running=$(ssh_cmd "$node" "pgrep -f petals 2>/dev/null | wc -l" 2>/dev/null || echo 0)

  if [[ "$running" -gt 0 ]]; then
    log "✅ Petals $node RUNNING ($running processes)"
    return 0
  fi

  log "⚠️  Petals $node OFFLINE — attempting restart"
  ssh_cmd "$node" "
    python3 -m petals.cli.run_server \
      '$model' \
      --device cpu \
      --num_blocks 4 \
      --throughput 1 \
      --port 31337 \
      > /tmp/petals_${node}.log 2>&1 &
    echo started PID \$!
  " && log "✅ Petals $node restarted" || log "❌ Petals $node restart FAILED"

  echo "{\"timestamp_utc\":\"$TIMESTAMP\",\"instruction\":\"Nomad Governor: heal Petals distributed cluster\",\"input\":\"Heal Petals cluster node $node\",\"output\":\"Result: RESTARTED\",\"action\":\"HEAL_PETALS_${node^^}\",\"result\":\"RESTARTED\",\"nomad_agent\":\"Multi-WAN Nomad Courier v3.0\"}" >> "$LORA_LOG"
}

# ─── LOCAL MAC MINI HEAL ────────────────────────────────────────────────────
heal_local_models() {
  local proxy_status
  proxy_status=$(curl -s --max-time 2 http://127.0.0.1:8080/health 2>/dev/null | python3 -c "import json,sys; print(json.load(sys.stdin).get('status','fail'))" 2>/dev/null || echo "fail")

  if [[ "$proxy_status" == "ok" ]]; then
    log "✅ Local proxy :8080 HEALTHY"
  else
    log "⚠️  Local proxy :8080 DOWN — reloading launchd"
    launchctl unload /Users/aaron/Library/LaunchAgents/ai.lauburu.unified.proxy.plist 2>/dev/null
    sleep 1
    launchctl load  /Users/aaron/Library/LaunchAgents/ai.lauburu.unified.proxy.plist 2>/dev/null
    echo "{\"timestamp_utc\":\"$TIMESTAMP\",\"instruction\":\"Nomad Governor: reload AI Proxy gateway\",\"input\":\"Reload LaunchAgent ai.lauburu.unified.proxy.plist\",\"output\":\"Result: RELOADED\",\"action\":\"RESTART_PROXY_8080\",\"result\":\"RELOADED\",\"nomad_agent\":\"Multi-WAN Nomad Courier v3.0\"}" >> "$LORA_LOG"
  fi

  # Check Qwen27B on :8085
  if ! curl -sf --max-time 2 http://127.0.0.1:8085/health &>/dev/null; then
    log "⚠️  Qwen27B :8085 DOWN — restarting"
    pkill -f "Huihui-Qwen3.8-27B" 2>/dev/null || true; sleep 1
    nohup /Users/aaron/.local/bin/llama-server \
      -m /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf/Huihui-Qwen3.8-27B-abliterated-UD-Q4_K_XL.gguf \
      --port 8085 -ngl 0 -c 2048 -b 256 -t 8 --host 0.0.0.0 \
      >> /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/logs/qwen38_abliterated_8085.log 2>&1 &
    log "✅ Qwen27B :8085 restarted (PID $!)"
  else
    log "✅ Qwen27B :8085 HEALTHY"
  fi

  # Check Qwen Coder 7B on :8083
  if ! curl -sf --max-time 2 http://127.0.0.1:8083/health &>/dev/null; then
    log "⚠️  Qwen-Coder-7B :8083 DOWN — restarting"
    nohup /Users/aaron/.local/bin/llama-server \
      -m /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf/qwen2.5-coder-7b-instruct-q4_k_m.gguf \
      --port 8083 -ngl 99 -c 8192 --host 0.0.0.0 \
      >> /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/logs/qwen_coder_8083.log 2>&1 &
    log "✅ Qwen-Coder-7B :8083 restarted (PID $!)"
  else
    log "✅ Qwen-Coder-7B :8083 HEALTHY"
  fi

  # Check Pixel llama-server :8087
  if ! nc -z -w2 100.73.38.87 8087 2>/dev/null; then
    log "⚠️  Pixel llama-server :8087 DOWN — restarting via SSH"
    ssh -p 8022 -o ConnectTimeout=5 -o BatchMode=yes u0_a363@100.73.38.87 \
      "nohup llama-server -m ~/qwen2.5-coder-14b-instruct-q3_k_m.gguf --port 8087 -ngl 99 -c 4096 --host 0.0.0.0 > ~/llama_14b_8087.log 2>&1 &" 2>/dev/null && \
      log "✅ Pixel :8087 restarted" || log "❌ Pixel :8087 restart FAILED"
  else
    log "✅ Pixel llama-server :8087 HEALTHY"
  fi
}

heal_ai_debate_cycle() {
  log "🗣️ Running Continuous AI Debate Cycle..."
  python3 /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/05_agents_and_swarms/ai_debate/continuous_free_ai_debate_cycle.py >> "$LOG" 2>&1 || log "⚠️ Debate cycle failed"
}

heal_agentworld_data() {
  log "🤖 Refreshing AgentWorld Stage datasets..."
  python3 /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/agentworld_train.py --stage 1 --dry-run >> "$LOG" 2>&1 || true
}

# ─── MAIN ───────────────────────────────────────────────────────────────────
log "════════ Mesh RPC+Petals Healer cycle ════════"
heal_local_models
heal_rpc macbook_pro
heal_rpc linux_head
heal_rpc pixel
heal_petals linux_head
heal_ai_debate_cycle
heal_agentworld_data
log "════════ Cycle complete ════════"
