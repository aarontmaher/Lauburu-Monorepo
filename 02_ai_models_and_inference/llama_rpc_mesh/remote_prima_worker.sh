#!/usr/bin/env bash
# Deploys to a remote node and launches the correct worker backend based on model presence

MODEL_PATH=$1
WORLD=$2
RANK=$3
MASTER_IP=$4
NEXT_IP=$5
GPU_MEM=$6

if [ -z "$MODEL_PATH" ]; then
    echo "Usage: remote_prima_worker.sh <model_path> <world> <rank> <master_ip> <next_ip> [gpu_mem]"
    exit 1
fi

pkill -f "prima.*50053\|llama-server.*50052" 2>/dev/null || true

if [ -f "$MODEL_PATH" ]; then
    echo "Model found locally. Launching prima.cpp PRP node (Rank $RANK)..."
    GPU_FLAG=""
    [ -n "$GPU_MEM" ] && GPU_FLAG="--gpu-mem $GPU_MEM"
    nohup ~/.local/bin/prima-cli -m "$MODEL_PATH" \
      --world "$WORLD" --rank "$RANK" --master "$MASTER_IP" \
      --next "$NEXT_IP" --prefetch $GPU_FLAG \
      > /tmp/prima_worker.log 2>&1 &
    echo "PRP_STARTED"
else
    echo "Model NOT found locally. Falling back to legacy llama.cpp RPC listener..."
    nohup ~/.local/bin/llama-server --port 50052 > /tmp/llama_rpc_fallback.log 2>&1 &
    echo "RPC_FALLBACK_STARTED"
fi
