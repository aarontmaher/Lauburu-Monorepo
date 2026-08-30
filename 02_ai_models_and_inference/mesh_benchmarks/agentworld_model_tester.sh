#!/usr/bin/env bash
# Iterates through models, optimizing for the All-Apple Silicon Thunderbolt/Wi-Fi 7 Mesh
# Topology: Mac Mini M4 (Headnode) -> MacBook Pro (Worker) -> MacBook Air M4 (Worker)

VAULT_DIR="/Users/aaronmaher/DFS_UNIFIED/AI_Models_Vault"
MBP_IP="100.103.212.21"    # Replace with 169.254.187.138 when TB4 is physically up
MBA_IP="100.93.158.96"
MINI_IP="100.119.199.76"   # Headnode
IDENTITY="~/.ssh/id_ed25519"

echo "=== Lauburu Mesh: All-Apple Sharding Tester ==="
echo "Headnode: Mac Mini M4 ($MINI_IP) -> Optimizing for Apple Silicon / TB4"

# Find all GGUF models on the MBP vault
MODELS=$(SSH_AUTH_SOCK="" ssh -i $IDENTITY -o StrictHostKeyChecking=no -o IdentitiesOnly=yes aaronmaher@${MBP_IP} "find $VAULT_DIR -maxdepth 2 -name '*.gguf' 2>/dev/null")

for MODEL_PATH in $MODELS; do
    MODEL_NAME=$(basename "$MODEL_PATH")
    echo "------------------------------------------------"
    echo "[*] Testing Model: $MODEL_NAME"
    
    # Run the remote worker script on MBP (Rank 1)
    echo "    Launching MacBook Pro Worker (Rank 1)..."
    SSH_AUTH_SOCK="" ssh -i $IDENTITY -o StrictHostKeyChecking=no -o IdentitiesOnly=yes aaronmaher@${MBP_IP} \
      "bash /Users/aaronmaher/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/llama_rpc_mesh/remote_prima_worker.sh \
       ${MODEL_PATH} 3 1 ${MINI_IP} ${MBA_IP}" &
       
    sleep 2
    
    # Run the remote worker script on MBA (Rank 2)
    echo "    Launching MacBook Air Worker (Rank 2)..."
    SSH_AUTH_SOCK="" ssh -i $IDENTITY -o StrictHostKeyChecking=no -o IdentitiesOnly=yes aaronmaher@${MBA_IP} \
      "bash /Users/aaronmaher/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/llama_rpc_mesh/remote_prima_worker.sh \
       ${MODEL_PATH} 3 2 ${MINI_IP} ${MINI_IP}" &
       
    sleep 2
    
    # Launch Master on Mac Mini (Rank 0 - Headnode)
    echo "    Launching Mac Mini Master (Headnode)..."
    pkill -f "prima-server" 2>/dev/null || true
    ~/.local/bin/prima-server -m "$MODEL_PATH" --world 3 --rank 0 \
      --master 127.0.0.1 --next "${MBP_IP}:50053" --prefetch \
      --port 8082 --host 0.0.0.0 > /tmp/prima_master_test.log 2>&1 &
    MASTER_PID=$!
    
    echo "    Waiting for model load (30s)..."
    sleep 30
    
    echo "    Running Sharding Test..."
    curl -s http://127.0.0.1:8082/v1/chat/completions \
      -H "Content-Type: application/json" \
      -d '{"model":"local","messages":[{"role":"user","content":"System test. Reply with OK."}],"max_tokens":10}' > /tmp/test_out.json 2>/dev/null
      
    if grep -q -i "ok" /tmp/test_out.json; then
        echo "    ✅ TEST PASSED: $MODEL_NAME distributed successfully across Apple Mesh."
    else
        echo "    ❌ TEST FAILED: $MODEL_NAME."
    fi
    
    echo "    Cleaning up..."
    kill $MASTER_PID 2>/dev/null
    SSH_AUTH_SOCK="" ssh -i $IDENTITY -o StrictHostKeyChecking=no -o IdentitiesOnly=yes aaronmaher@${MBP_IP} "pkill -f prima-cli"
    SSH_AUTH_SOCK="" ssh -i $IDENTITY -o StrictHostKeyChecking=no -o IdentitiesOnly=yes aaronmaher@${MBA_IP} "pkill -f prima-cli"
    sleep 2
done
echo "=== Testing Complete ==="
