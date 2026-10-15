#!/usr/bin/env bash
# Nexus LoRA Sync Script
set -euo pipefail

echo "🧠 Triggering Single-Chat Nexus 24/7 LoRA Distillation Sync..."
curl -s -X POST http://127.0.0.1:4050/api/chat/nexus/lora/sync | jq . || {
    echo "Querying active threads from Single-Chat Nexus:"
    curl -s http://127.0.0.1:4050/api/chat/nexus/threads | jq '.[0:5]'
}
