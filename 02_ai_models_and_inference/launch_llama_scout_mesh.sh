#!/usr/bin/env bash
# ==============================================================================
# Llama 4 Scout (109B) - 7-Layer Mesh RPC Sharding Launch Script
# ==============================================================================
# WARNING: Thunderbolt bridge0 is currently experiencing 600ms latency and 
# 100% packet loss to L8 (10.0.0.8). Until spanning tree / network loops are 
# resolved, this script defaults to Tailscale IPs to prevent RPC timeouts.
# ==============================================================================

# 1. Start the RPC Workers on the Peripheral Macs (Run these in separate terminals)
echo "[1] Start RPC Worker on Mac Mini M4 (L1)"
echo "ssh aaron@100.119.199.76 'llama-rpc-server --host 0.0.0.0 --port 50052'"
echo ""

echo "[2] Start RPC Worker on Mac Air M4 (L1a) - Required for 109B memory footprint"
echo "ssh aaronmaher@100.121.202.34 'llama-rpc-server --host 0.0.0.0 --port 50052'"
echo ""

echo "[3] Start RPC Worker on Mac Intel (L2) - Optional/Overflow"
echo "ssh aaronmaher@100.103.212.21 'llama-rpc-server --host 0.0.0.0 --port 50052'"
echo ""

# 2. Launch the Main Orchestrator Node on L8 (Linux Mini)
echo "[4] Launch Main Llama 4 Scout Server on L8 (lauburu)"
echo "Run the following on L8 to distribute the 63GB payload across the mesh:"

cat << 'EOF'
llama-server \
  -m /path/to/model_vault_gguf/Llama-4-Scout-17B-16E-Instruct-Q4_K_M-00001-of-00002.gguf \
  --port 8090 \
  --host 0.0.0.0 \
  -c 65536 \
  --cache-type-k q4_0 \
  --cache-type-v q4_0 \
  --rpc 100.119.199.76:50052,100.121.202.34:50052,100.103.212.21:50052 \
  --tensor-split 4,3,2,1
EOF

echo ""
echo "Note: The context length has been capped at 64K (-c 65536) and KV cache is 4-bit quantized."
