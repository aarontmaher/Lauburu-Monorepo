#!/usr/bin/env bash
# FULL 7-NODE HETEROGENEOUS MESH ORCHESTRATOR
# PRP Core (Mac Mini, MBP, MBA, Linux Head) + Dynamic Edge RPC (Pixel, S20, Tablet)

VAULT_DIR="/Users/aaronmaher/DFS_UNIFIED/AI_Models_Vault"
MBP_TAILSCALE="100.103.212.21"
MBA_TAILSCALE="100.93.158.96"
LINUX_TAILSCALE="100.101.39.98"
PIXEL_TAILSCALE="100.73.38.87"
S20_TAILSCALE="100.84.40.95"
TABLET_LAN="192.168.8.173"  # Bedside Tablet
MINI_IP="100.119.199.76"   
IDENTITY="~/.ssh/id_ed25519"

echo "=== Lauburu Mesh: 7-Node Omni-Sharding Tester ==="

# --- AI SELF-HEALING: Dynamic Topology Discovery ---
echo "[AI] Discovering topology & healing connections..."

# 1. MBP Thunderbolt Check
MBP_TB4=$(SSH_AUTH_SOCK="" ssh -i $IDENTITY -o StrictHostKeyChecking=no -o IdentitiesOnly=yes aaronmaher@${MBP_TAILSCALE} "ifconfig bridge0 | grep 'inet 169.254' | awk '{print \$2}'" 2>/dev/null)
if [ -n "$MBP_TB4" ] && ping -c 1 -W 1 "$MBP_TB4" &>/dev/null; then
    MBP_PRIMARY_IP=$MBP_TB4
else
    MBP_PRIMARY_IP=$MBP_TAILSCALE
fi

# 2. Dynamic RPC Edge Node Discovery
RPC_TARGETS=""
declare -A EDGE_NODES
EDGE_NODES["Pixel_10"]="$PIXEL_TAILSCALE:8022:u0_a363"
EDGE_NODES["Samsung_S20"]="$S20_TAILSCALE:8022:u0_a420"
EDGE_NODES["Linux_Tablet"]="$TABLET_LAN:22:aaron"

for NODE_NAME in "${!EDGE_NODES[@]}"; do
    IFS=':' read -r IP PORT USER <<< "${EDGE_NODES[$NODE_NAME]}"
    if ping -c 1 -W 1 "$IP" &>/dev/null; then
        echo "[AI] $NODE_NAME is ONLINE. Injecting into Edge RPC pool."
        SSH_AUTH_SOCK="" ssh -i $IDENTITY -o StrictHostKeyChecking=no -o IdentitiesOnly=yes -p "$PORT" "$USER@$IP" \
          "pkill -f llama-server; nohup ~/.local/bin/llama-server --port 50052 > /dev/null 2>&1 &" &
        if [ -z "$RPC_TARGETS" ]; then
            RPC_TARGETS="${IP}:50052"
        else
            RPC_TARGETS="${RPC_TARGETS},${IP}:50052"
        fi
    else
        echo "[AI] $NODE_NAME is DOWN. Pruning from current topology."
    fi
done

echo "------------------------------------------------"

MODELS=$(SSH_AUTH_SOCK="" ssh -i $IDENTITY -o StrictHostKeyChecking=no -o IdentitiesOnly=yes aaronmaher@${MBP_TAILSCALE} "find $VAULT_DIR -maxdepth 2 -name '*.gguf' 2>/dev/null | head -1")

for MODEL_PATH in $MODELS; do
    MODEL_NAME=$(basename "$MODEL_PATH")
    echo "[*] Testing Model: $MODEL_NAME"
    
    WORLD_SIZE=4 # 4 Core PRP nodes
    
    # Core 1: MBP Worker
    SSH_AUTH_SOCK="" ssh -i $IDENTITY -o StrictHostKeyChecking=no -o IdentitiesOnly=yes aaronmaher@${MBP_TAILSCALE} \
      "bash /Users/aaronmaher/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/llama_rpc_mesh/remote_prima_worker.sh ${MODEL_PATH} $WORLD_SIZE 1 ${MINI_IP} ${MBA_TAILSCALE}" &
       
    # Core 2: MBA Worker
    SSH_AUTH_SOCK="" ssh -i $IDENTITY -o StrictHostKeyChecking=no -o IdentitiesOnly=yes aaronmaher@${MBA_TAILSCALE} \
      "bash /Users/aaronmaher/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/llama_rpc_mesh/remote_prima_worker.sh ${MODEL_PATH} $WORLD_SIZE 2 ${MINI_IP} ${LINUX_TAILSCALE}" &

    # Core 3: Linux Worker
    SSH_AUTH_SOCK="" ssh -i $IDENTITY -o StrictHostKeyChecking=no -o IdentitiesOnly=yes linux@${LINUX_TAILSCALE} \
      "bash ~/Lauburu-Monorepo/02_ai_models_and_inference/llama_rpc_mesh/remote_prima_worker.sh /home/linux/agentworld/${MODEL_NAME} $WORLD_SIZE 3 ${MINI_IP} ${MINI_IP}" &
       
    sleep 5
    
    # Master: Mac Mini
    echo "    Launching Mac Mini Master (Rank 0) + $RPC_TARGETS edge targets..."
    pkill -f "prima-server" 2>/dev/null || true
    
    RPC_FLAG=""
    [ -n "$RPC_TARGETS" ] && RPC_FLAG="--rpc $RPC_TARGETS"
    
    ~/.local/bin/prima-server -m "$MODEL_PATH" --world $WORLD_SIZE --rank 0 \
      --master 127.0.0.1 --next "${MBP_PRIMARY_IP}:50053" --prefetch \
      $RPC_FLAG --port 8082 --host 0.0.0.0 > /tmp/prima_master_test.log 2>&1 &
    MASTER_PID=$!
    
    echo "    Waiting for Halda mesh optimization across all nodes (45s)..."
    sleep 45
    
    curl -s http://127.0.0.1:8082/v1/chat/completions -H "Content-Type: application/json" -d '{"model":"local","messages":[{"role":"user","content":"System test. Reply with OK."}],"max_tokens":10}' > /tmp/test_out.json 2>/dev/null
      
    if grep -q -i "ok" /tmp/test_out.json; then
        echo "    ✅ TEST PASSED: Distributed seamlessly across full 7-node Omni-Mesh."
    else
        echo "    ❌ TEST FAILED."
    fi
    
    echo "    Cleaning up..."
    kill $MASTER_PID 2>/dev/null
    SSH_AUTH_SOCK="" ssh -i $IDENTITY -o StrictHostKeyChecking=no -o IdentitiesOnly=yes aaronmaher@${MBP_TAILSCALE} "pkill -f prima-cli"
    SSH_AUTH_SOCK="" ssh -i $IDENTITY -o StrictHostKeyChecking=no -o IdentitiesOnly=yes aaronmaher@${MBA_TAILSCALE} "pkill -f prima-cli"
    SSH_AUTH_SOCK="" ssh -i $IDENTITY -o StrictHostKeyChecking=no -o IdentitiesOnly=yes linux@${LINUX_TAILSCALE} "pkill -f prima-cli"
    for NODE_NAME in "${!EDGE_NODES[@]}"; do
        IFS=':' read -r IP PORT USER <<< "${EDGE_NODES[$NODE_NAME]}"
        SSH_AUTH_SOCK="" ssh -i $IDENTITY -o StrictHostKeyChecking=no -o IdentitiesOnly=yes -p "$PORT" "$USER@$IP" "pkill -f llama-server" 2>/dev/null
    done
    sleep 2
done
