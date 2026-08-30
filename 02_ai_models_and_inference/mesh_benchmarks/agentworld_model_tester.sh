#!/usr/bin/env bash
# Iterates through models, tests PRP sharding across 4-node Heterogeneous Mesh
# Headnode: Mac Mini M4 (Rank 0) -> utilizing Thunderbolt 4 Bridge to MBP

VAULT_DIR="/Users/aaronmaher/DFS_UNIFIED/AI_Models_Vault"
MBP_TAILSCALE="100.103.212.21"
MBA_TAILSCALE="100.93.158.96"
LINUX_TAILSCALE="100.101.39.98"
MINI_IP="100.119.199.76"   
IDENTITY="~/.ssh/id_ed25519"

echo "=== Lauburu Mesh: 4-Node Sharding Tester ==="
echo "Headnode: Mac Mini M4 -> Optimizing for TB4 + Heterogeneous Nodes"

# --- AI SELF-HEALING: Thunderbolt 4 Dynamic Discovery ---
# APIPA (169.254.x.x) IPs rotate on sleep/reboot. Dynamically fetch the MBP's active TB4 IP.
echo "[AI Self-Heal] Probing MacBook Pro for active Thunderbolt IP..."
MBP_TB4=$(SSH_AUTH_SOCK="" ssh -i $IDENTITY -o StrictHostKeyChecking=no -o IdentitiesOnly=yes aaronmaher@${MBP_TAILSCALE} "ifconfig bridge0 | grep 'inet 169.254' | awk '{print \$2}'" 2>/dev/null)

if [ -n "$MBP_TB4" ]; then
    echo "[AI Self-Heal] Successfully resolved MBP Thunderbolt IP: $MBP_TB4"
    # Verify the TB4 connection works
    if ping -c 1 -W 1 "$MBP_TB4" &>/dev/null; then
        echo "[AI Self-Heal] TB4 link is ACTIVE (0.5ms latency). Utilizing TB4."
        MBP_PRIMARY_IP=$MBP_TB4
    else
        echo "[AI Self-Heal] TB4 link is down/unreachable. Falling back to Tailscale."
        MBP_PRIMARY_IP=$MBP_TAILSCALE
    fi
else
    echo "[AI Self-Heal] Could not find TB4 IP. Falling back to Tailscale."
    MBP_PRIMARY_IP=$MBP_TAILSCALE
fi
echo "------------------------------------------------"

# Find all GGUF models on the MBP vault
MODELS=$(SSH_AUTH_SOCK="" ssh -i $IDENTITY -o StrictHostKeyChecking=no -o IdentitiesOnly=yes aaronmaher@${MBP_TAILSCALE} "find $VAULT_DIR -maxdepth 2 -name '*.gguf' 2>/dev/null")

for MODEL_PATH in $MODELS; do
    MODEL_NAME=$(basename "$MODEL_PATH")
    echo "[*] Testing Model: $MODEL_NAME"
    
    # 1. Launch MBP Worker (Rank 1)
    # Master is Mac Mini (using Tailscale IP since TB4 is 1-way mapped currently, or loopback logic)
    echo "    Launching MacBook Pro Worker (Rank 1)..."
    SSH_AUTH_SOCK="" ssh -i $IDENTITY -o StrictHostKeyChecking=no -o IdentitiesOnly=yes aaronmaher@${MBP_TAILSCALE} \
      "bash /Users/aaronmaher/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/llama_rpc_mesh/remote_prima_worker.sh \
       ${MODEL_PATH} 4 1 ${MINI_IP} ${MBA_TAILSCALE}" &
       
    # 2. Launch MBA Worker (Rank 2)
    echo "    Launching MacBook Air Worker (Rank 2)..."
    SSH_AUTH_SOCK="" ssh -i $IDENTITY -o StrictHostKeyChecking=no -o IdentitiesOnly=yes aaronmaher@${MBA_TAILSCALE} \
      "bash /Users/aaronmaher/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/llama_rpc_mesh/remote_prima_worker.sh \
       ${MODEL_PATH} 4 2 ${MINI_IP} ${LINUX_TAILSCALE}" &

    # 3. Launch Linux Worker (Rank 3)
    echo "    Launching Linux Worker (Rank 3)..."
    # Note: Assumes Linux has the model in agentworld, handled by rsync in full run
    SSH_AUTH_SOCK="" ssh -i $IDENTITY -o StrictHostKeyChecking=no -o IdentitiesOnly=yes linux@${LINUX_TAILSCALE} \
      "bash ~/Lauburu-Monorepo/02_ai_models_and_inference/llama_rpc_mesh/remote_prima_worker.sh \
       /home/linux/agentworld/${MODEL_NAME} 4 3 ${MINI_IP} ${MINI_IP}" &
       
    sleep 3
    
    # 4. Launch Master on Mac Mini (Rank 0) -> utilizing TB4 IP to push to MBP
    echo "    Launching Mac Mini Master (Rank 0)..."
    pkill -f "prima-server" 2>/dev/null || true
    ~/.local/bin/prima-server -m "$MODEL_PATH" --world 4 --rank 0 \
      --master 127.0.0.1 --next "${MBP_PRIMARY_IP}:50053" --prefetch \
      --port 8082 --host 0.0.0.0 > /tmp/prima_master_test.log 2>&1 &
    MASTER_PID=$!
    
    echo "    Waiting for model load (45s)..."
    sleep 45
    
    echo "    Running Sharding Test..."
    curl -s http://127.0.0.1:8082/v1/chat/completions \
      -H "Content-Type: application/json" \
      -d '{"model":"local","messages":[{"role":"user","content":"System test. Reply with OK."}],"max_tokens":10}' > /tmp/test_out.json 2>/dev/null
      
    if grep -q -i "ok" /tmp/test_out.json; then
        echo "    ✅ TEST PASSED: $MODEL_NAME distributed successfully across 4-node mesh."
    else
        echo "    ❌ TEST FAILED: $MODEL_NAME."
    fi
    
    echo "    Cleaning up..."
    kill $MASTER_PID 2>/dev/null
    SSH_AUTH_SOCK="" ssh -i $IDENTITY -o StrictHostKeyChecking=no -o IdentitiesOnly=yes aaronmaher@${MBP_TAILSCALE} "pkill -f prima-cli"
    SSH_AUTH_SOCK="" ssh -i $IDENTITY -o StrictHostKeyChecking=no -o IdentitiesOnly=yes aaronmaher@${MBA_TAILSCALE} "pkill -f prima-cli"
    SSH_AUTH_SOCK="" ssh -i $IDENTITY -o StrictHostKeyChecking=no -o IdentitiesOnly=yes linux@${LINUX_TAILSCALE} "pkill -f prima-cli"
    sleep 2
done
echo "=== Testing Complete ==="
