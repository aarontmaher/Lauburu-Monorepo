#!/bin/bash
# Path: /Volumes/Lauburu-Monorepo/06_scripts_and_tooling/network/intelligent_lens_router_training_loop.sh
# Execution: Must be run as a silent background daemon (Rule 9)

LORA_LAKE="/Volumes/Lauburu-Monorepo/04_data_and_memory/data/continuous_lora_dataset.jsonl"
TELEMETRY="/Volumes/Lauburu-Monorepo/04_data_and_memory/omniscient_mesh_telemetry.json"
SYSTEM_PROMPT="You are the Frontier Triad Reviewer. Analyze the provided tiny model actions and Screen Lens routing. Correct any hallucinations, RAM mandate violations, or topology errors. Output strictly a single JSON object."

while true; do
    TIMESTAMP=$(date +%s)
    PAYLOAD_FILE="/tmp/lens_payload_${TIMESTAMP}.json"

    # 1. Pre-Flight RAM Governance (Rule 1 & Rule 10)
    # Calculate free RAM using Darwin vm_stat. If < 4.8GB, offload to L3 Linux.
    PAGE_SIZE=$(pagesize 2>/dev/null || echo 4096)
    FREE_PAGES=$(vm_stat | grep "Pages free" | awk '{print $3}' | tr -d '.')
    FREE_GB=$(echo "scale=2; ($FREE_PAGES * $PAGE_SIZE) / 1073741824" | bc)
    
    QWEN_MASTER_IP="127.0.0.1"
    if (( $(echo "$FREE_GB < 4.8" | bc -l) )); then
        QWEN_MASTER_IP="100.101.39.98" # Fallback to L3 Linux Head Node
    fi
    
    # Check if TCP Handshake is alive (Rule 8)
    nc -zv -w 1 $QWEN_MASTER_IP 8082 >/dev/null 2>&1 || QWEN_MASTER_IP="127.0.0.1"

    # 2. Gather Transcripts & Telemetry Safely (Valid JSON)
    TELEMETRY_DATA=$(cat "$TELEMETRY" 2>/dev/null)
    [ -z "$TELEMETRY_DATA" ] && TELEMETRY_DATA="{}"
    
    # -exec jq -c '.' {} \; validates and compresses each file.
    # jq -s '.' safely combines them into a valid JSON array, outputting '[]' if empty.
    TRANSCRIPTS=$(find ~/.gemini/antigravity/brain -type f -path "*/.system_generated/messages/*.json" -mmin -5 -exec jq -c '.' {} \; 2>/dev/null | jq -s '.')
    [ -z "$TRANSCRIPTS" ] && TRANSCRIPTS="[]"

    jq -n --argjson tel "$TELEMETRY_DATA" --argjson trans "$TRANSCRIPTS" '{telemetry: $tel, transcripts: $trans}' > "$PAYLOAD_FILE"

    # 3. Query the Canonical Triad
    
    # Model 1: Gemini 3.8 Flash (Cloud)
    # Using sed to strictly delete markdown fences before validating and appending
    agy run --headless --model gemini-3.8-flash --prompt "$SYSTEM_PROMPT" < "$PAYLOAD_FILE" | \
      sed '/^```/d' | \
      jq -c '.' >> "$LORA_LAKE" &
    
    # Model 2: Qwen 3.8 Max Abliterated (Master Orchestrator, Port 8082)
    curl -s -X POST "http://${QWEN_MASTER_IP}:8082/v1/chat/completions" \
      -H "Content-Type: application/json" \
      -d "{\"model\": \"qwen_38_max_abliterated\", \"messages\": [{\"role\": \"system\", \"content\": \"$SYSTEM_PROMPT\"}, {\"role\": \"user\", \"content\": $(jq -R -s '.' < \"$PAYLOAD_FILE\")}]}" | \
      jq -r '.choices[0].message.content // empty' | \
      sed '/^```/d' | \
      jq -c '.' >> "$LORA_LAKE" &

    # Model 3: Qwen 3.8 Max (Adversarial Red Team, Port 8083)
    curl -s -X POST "http://${QWEN_MASTER_IP}:8083/v1/chat/completions" \
      -H "Content-Type: application/json" \
      -d "{\"model\": \"qwen_38_max\", \"messages\": [{\"role\": \"system\", \"content\": \"$SYSTEM_PROMPT\"}, {\"role\": \"user\", \"content\": $(jq -R -s '.' < \"$PAYLOAD_FILE\")}]}" | \
      jq -r '.choices[0].message.content // empty' | \
      sed '/^```/d' | \
      jq -c '.' >> "$LORA_LAKE" &
    
    wait
    rm -f "$PAYLOAD_FILE"
    sleep 300
done
