#!/usr/bin/env bash
# Iterates through all models in the vault, rsyncs them to Linux agentworld, and tests PRP sharding

VAULT_DIR="/Users/aaronmaher/DFS_UNIFIED/AI_Models_Vault"
LINUX_IP="100.101.39.98"
AGENTWORLD_DIR="/home/linux/agentworld"
IDENTITY="~/.ssh/id_ed25519"

echo "=== Lauburu Mesh: Agentworld Sharding Tester ==="
echo "Targeting Linux node: $LINUX_IP"

# Find all GGUF models on the MBP vault
MODELS=$(find "$VAULT_DIR" -maxdepth 2 -name "*.gguf" 2>/dev/null)

for MODEL_PATH in $MODELS; do
    MODEL_NAME=$(basename "$MODEL_PATH")
    echo "------------------------------------------------"
    echo "[*] Testing Model: $MODEL_NAME"
    
    # Q3 Option B: Rsync to Linux Agentworld
    echo "    Syncing to Linux agentworld..."
    rsync -avz --progress -e "ssh -i $IDENTITY -o StrictHostKeyChecking=no -o IdentitiesOnly=yes" \
      "$MODEL_PATH" "linux@${LINUX_IP}:${AGENTWORLD_DIR}/${MODEL_NAME}"
      
    # Run the remote worker script
    echo "    Launching Linux Worker..."
    SSH_AUTH_SOCK="" ssh -i $IDENTITY -o StrictHostKeyChecking=no -o IdentitiesOnly=yes linux@${LINUX_IP} \
      "bash ~/Lauburu-Monorepo/02_ai_models_and_inference/llama_rpc_mesh/remote_prima_worker.sh \
       ${AGENTWORLD_DIR}/${MODEL_NAME} 2 1 100.119.199.76 100.119.199.76" &
       
    sleep 3
    
    # Launch Master on Mac Mini
    echo "    Launching Mac Mini Master..."
    pkill -f "prima-server" 2>/dev/null || true
    ~/.local/bin/prima-server -m "$MODEL_PATH" --world 2 --rank 0 \
      --master 127.0.0.1 --next "${LINUX_IP}:50053" --prefetch \
      --port 8082 --host 0.0.0.0 > /tmp/prima_master_test.log 2>&1 &
    MASTER_PID=$!
    
    echo "    Waiting for model load (30s)..."
    sleep 30
    
    echo "    Running Sharding Test..."
    curl -s http://127.0.0.1:8082/v1/chat/completions \
      -H "Content-Type: application/json" \
      -d '{"model":"local","messages":[{"role":"user","content":"System test. Reply with OK."}],"max_tokens":10}' > /tmp/test_out.json 2>/dev/null
      
    if grep -q "OK\|ok\|Ok" /tmp/test_out.json; then
        echo "    ✅ TEST PASSED: $MODEL_NAME distributed successfully."
    else
        echo "    ❌ TEST FAILED: $MODEL_NAME."
    fi
    
    echo "    Cleaning up..."
    kill $MASTER_PID 2>/dev/null
    SSH_AUTH_SOCK="" ssh -i $IDENTITY -o StrictHostKeyChecking=no -o IdentitiesOnly=yes linux@${LINUX_IP} "pkill -f prima-cli"
    sleep 2
done
echo "=== Testing Complete ==="
