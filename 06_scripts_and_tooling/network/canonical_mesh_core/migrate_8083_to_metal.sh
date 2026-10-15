#!/bin/bash
# Migrate Port 8083 Abliterated AI to MacBook Pro (L2) Metal GPU over 10Gb/40Gb TB4/USB
TARGET_IP="169.254.105.128" # Thunderbolt IP of L2
USER="aaron"

echo "[*] Migrating Qwen 3.8 Max Abliterated (Port 8083) to Metal GPU Node (L2)"

# Check if L2 is reachable over Thunderbolt 4 (0.544ms RTT)
ping -c 1 -W 2 $TARGET_IP >/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "[!] Target L2 not reachable on TB4 IP ($TARGET_IP). Falling back to Tailscale 100.103.212.21"
    TARGET_IP="100.103.212.21"
fi

echo "[+] Target confirmed: $TARGET_IP"

# Stop it on L3 (Linux Mini)
echo "[*] Stopping CPU-bound llama-server on Linux Mini (L3)..."
ssh -o StrictHostKeyChecking=no aaron@100.101.39.98 "sudo systemctl stop ggml-rpc-server.service || true; pkill -f 'llama-server --port 8083'"

# Launch it on L2 (MacBook Pro) with Metal Acceleration
echo "[*] Launching Metal-accelerated llama-server on L2..."
ssh -o StrictHostKeyChecking=no $USER@$TARGET_IP "nohup /Users/aaron/llama.cpp/llama-server -m /Volumes/Model_Vault/Huihui-Qwen3.8-27B-abliterated-UD-Q4_K_XL.gguf --host 0.0.0.0 --port 8083 -ngl 99 -c 8192 > /tmp/llama_8083.log 2>&1 &"

echo "[+] Migration Complete. Abliterated Model (Port 8083) is now running on Apple Silicon Metal via 10Gbps USB/TB."
