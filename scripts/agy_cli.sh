#!/bin/bash
# Antigravity Dev Factory CLI Helper (Backup Command Console)

COMMAND=$1

case $COMMAND in
  "start")
    echo "[AGI] Starting full-stack Dev Factory server..."
    npm run dev
    ;;
  "diagnose")
    echo "[AGI] Querying local hardware diagnostic telemetry..."
    curl -s http://localhost:3000/api/hardware/diagnose | json_pp || curl -s http://localhost:3000/api/hardware/diagnose
    ;;
  "nodes")
    echo "[AGI] Querying active Ray cluster nodes..."
    curl -s http://localhost:3000/api/ray/nodes | json_pp || curl -s http://localhost:3000/api/ray/nodes
    ;;
  "train")
    echo "[AGI] Triggering local model fine-tuning..."
    curl -X POST -H "Content-Type: application/json" -d '{"directory":"."}' http://localhost:3000/api/training/start
    ;;
  "status")
    echo "[AGI] Fetching active training loss metrics..."
    curl -s http://localhost:3000/api/training/status | json_pp
    ;;
  "chat")
    PROMPT=$2
    if [ -z "$PROMPT" ]; then
      echo "Usage: ./agy_cli.sh chat \"your prompt text\""
      exit 1
    fi
    echo "[AGI] Querying distributed chat with prompt: $PROMPT"
    curl -X POST -H "Content-Type: application/json" -d "{\"text\":\"$PROMPT\", \"model\":\"gemma2:9b\"}" http://localhost:3000/api/chat/public/send
    ;;
  *)
    echo "Antigravity Dev Factory CLI Console"
    echo "Usage: ./agy_cli.sh [start|diagnose|nodes|train|status|chat]"
    echo "  start    : Boots the full-stack server"
    echo "  diagnose : Runs hardware bottleneck profiler"
    echo "  nodes    : Lists active Tailscale Ray nodes"
    echo "  train    : Starts distributed QLoRA fine-tuning"
    echo "  status   : Streams training logs & loss"
    echo "  chat     : Sends prompt to the distributed model pool"
    ;;
esac
