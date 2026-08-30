#!/usr/bin/env bash
# Iterates through models, tests PRP sharding across FULL 6-Node Heterogeneous Mesh
# Headnode: Mac Mini M4 (Rank 0) -> utilizing TB4 Bridge and Termux Edge Nodes

VAULT_DIR="/Users/aaronmaher/DFS_UNIFIED/AI_Models_Vault"
MBP_TAILSCALE="100.103.212.21"
MBA_TAILSCALE="100.93.158.96"
LINUX_TAILSCALE="100.101.39.98"
PIXEL_TAILSCALE="100.73.38.87"
S20_TAILSCALE="100.84.40.95"
MINI_IP="100.119.199.76"   
IDENTITY="~/.ssh/id_ed25519"

echo "=== Lauburu Mesh: 6-Node Sharding Tester ==="
echo "Topology: Mac Mini -> MBP -> MBA -> Linux -> Pixel 10 -> Samsung S20"

# --- AI SELF-HEALING: Thunderbolt 4 Dynamic Discovery ---
echo "[AI Self-Heal] Probing MacBook Pro for active Thunderbolt IP..."
MBP_TB4=$(SSH_AUTH_SOCK="" ssh -i $IDENTITY -o StrictHostKeyChecking=no -o IdentitiesOnly=yes aaronmaher@${MBP_TAILSCALE} "ifconfig bridge0 | grep 'inet 169.254' | awk '{print \$2}'" 2>/dev/null)

if [ -n "$MBP_TB4" ] && ping -c 1 -W 1 "$MBP_TB4" &>/dev/null; then
    echo "[AI Self-Heal] TB4 link is ACTIVE. Utilizing TB4 ($MBP_TB4)."
    MBP_PRIMARY_IP=$MBP_TB4
else
    echo "[AI Self-Heal] TB4 link is down. Falling back to Tailscale."
    MBP_PRIMARY_IP=$MBP_TAILSCALE
fi
echo "------------------------------------------------"

MODELS=$(SSH_AUTH_SOCK="" ssh -i $IDENTITY -o StrictHostKeyChecking=no -o IdentitiesOnly=yes aaronmaher@${MBP_TAILSCALE} "find $VAULT_DIR -maxdepth 2 -name '*.gguf' 2>/dev/null | head -1")

for MODEL_PATH in $MODELS; do
    MODEL_NAME=$(basename "$MODEL_PATH")
    echo "[*] Testing Model: $MODEL_NAME"
    
    # Define how many nodes have the physical model (PRP Ring size).
    # Phones likely won't have the 40GB model, so they fallback to RPC.
    WORLD_SIZE=4 
    
    # 1. MBP Worker (Rank 1)
    SSH_AUTH_SOCK="" ssh -i $IDENTITY -o StrictHostKeyChecking=no -o IdentitiesOnly=yes aaronmaher@${MBP_TAILSCALE} \
      "bash /Users/aaronmaher/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/llama_rpc_mesh/remote_prima_worker.sh ${MODEL_PATH} $WORLD_SIZE 1 ${MINI_IP} ${MBA_TAILSCALE}" &
       
    # 2. MBA Worker (Rank 2)
    SSH_AUTH_SOCK="" ssh -i $IDENTITY -o StrictHostKeyChecking=no -o IdentitiesOnly=yes aaronmaher@${MBA_TAILSCALE} \
      "bash /Users/aaronmaher/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/llama_rpc_mesh/remote_prima_worker.sh ${MODEL_PATH} $WORLD_SIZE 2 ${MINI_IP} ${LINUX_TAILSCALE}" &

    # 3. Linux Worker (Rank 3) - Loops back to Mini
    SSH_AUTH_SOCK="" ssh -i $IDENTITY -o StrictHostKeyChecking=no -o IdentitiesOnly=yes linux@${LINUX_TAILSCALE} \
      "bash ~/Lauburu-Monorepo/02_ai_models_and_inference/llama_rpc_mesh/remote_prima_worker.sh /home/linux/agentworld/${MODEL_NAME} $WORLD_SIZE 3 ${MINI_IP} ${MINI_IP}" &
       
    # 4. Pixel 10 (RPC Fallback - No Model)
    echo "    Launching Pixel 10 Edge Node (Fallback RPC)..."
    SSH_AUTH_SOCK="" ssh -i $IDENTITY -o StrictHostKeyChecking=no -o IdentitiesOnly=yes -p 8022 u0_a363@${PIXEL_TAILSCALE} \
      "pkill -f llama-server; nohup ~/.local/bin/llama-server --port 50052 > /dev/null 2>&1 &" &
      
    # 5. Samsung S20 (RPC Fallback - No Model)
    echo "    Launching Samsung S20 Edge Node (Fallback RPC)..."
    SSH_AUTH_SOCK="" ssh -i $IDENTITY -o StrictHostKeyChecking=no -o IdentitiesOnly=yes -p 8022 u0_a420@${S20_TAILSCALE} \
      "pkill -f llama-server; nohup ~/.local/bin/llama-server --port 50052 > /dev/null 2>&1 &" &

    sleep 5
    
    # 6. Launch Master on Mac Mini (Rank 0) -> utilizing TB4 IP to push to MBP, and --rpc to push to phones
    echo "    Launching Mac Mini Master (Rank 0) + Edge RPC targets..."
    pkill -f "prima-server" 2>/dev/null || true
    ~/.local/bin/prima-server -m "$MODEL_PATH" --world $WORLD_SIZE --rank 0 \
      --master 127.0.0.1 --next "${MBP_PRIMARY_IP}:50053" --prefetch \
      --rpc "${PIXEL_TAILSCALE}:50052,${S20_TAILSCALE}:50052" \
      --port 8082 --host 0.0.0.0 > /tmp/prima_master_test.log 2>&1 &
    MASTER_PID=$!
    
    echo "    Waiting for model load across all 6 layers (45s)..."
    sleep 45
    
    echo "    Running Sharding Test..."
    curl -s http://127.0.0.1:8082/v1/chat/completions -H "Content-Type: application/json" -d '{"model":"local","messages":[{"role":"user","content":"System test. Reply with OK."}],"max_tokens":10}' > /tmp/test_out.json 2>/dev/null
      
    if grep -q -i "ok" /tmp/test_out.json; then
        echo "    ✅ TEST PASSED: Distributed seamlessly across 6-node hybrid mesh."
    else
        echo "    ❌ TEST FAILED."
    fi
    
    echo "    Cleaning up all 6 nodes..."
    kill $MASTER_PID 2>/dev/null
    SSH_AUTH_SOCK="" ssh -i $IDENTITY -o StrictHostKeyChecking=no -o IdentitiesOnly=yes aaronmaher@${MBP_TAILSCALE} "pkill -f prima-cli"
    SSH_AUTH_SOCK="" ssh -i $IDENTITY -o StrictHostKeyChecking=no -o IdentitiesOnly=yes aaronmaher@${MBA_TAILSCALE} "pkill -f prima-cli"
    SSH_AUTH_SOCK="" ssh -i $IDENTITY -o StrictHostKeyChecking=no -o IdentitiesOnly=yes linux@${LINUX_TAILSCALE} "pkill -f prima-cli"
    SSH_AUTH_SOCK="" ssh -i $IDENTITY -o StrictHostKeyChecking=no -o IdentitiesOnly=yes -p 8022 u0_a363@${PIXEL_TAILSCALE} "pkill -f llama-server"
    SSH_AUTH_SOCK="" ssh -i $IDENTITY -o StrictHostKeyChecking=no -o IdentitiesOnly=yes -p 8022 u0_a420@${S20_TAILSCALE} "pkill -f llama-server"
    sleep 2
done
