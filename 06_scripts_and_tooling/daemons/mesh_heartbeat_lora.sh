#!/usr/bin/env bash
# Lauburu 30-min Mesh Health + LoRA Append + prima heartbeat (POSIX-safe)
TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
LOG=/tmp/lauburu_mesh_heartbeat.log
DATASET=/Volumes/Lauburu-Monorepo/04_data_and_memory/data/continuous_lora_dataset.jsonl
exec >> "$LOG" 2>&1
echo "══════════════════════ [$TS] ══════════════════════"

probe() {
  local name="$1" url="$2" t0 t1 ms
  t0=$(date +%s)
  if curl -sf --max-time 3 "$url" > /dev/null 2>&1; then
    t1=$(date +%s); ms=$(( (t1-t0)*1000 ))
    echo "${name}|ONLINE|~${ms}ms"
  else
    echo "${name}|OFFLINE|--"
  fi
}

R_PRIMA=$(probe "prima_ring"   "http://127.0.0.1:8082/health")
R_QWEN=$(probe  "qwen_proxy"   "http://127.0.0.1:8083/v1/models")
R_MBA=$(probe   "mba_qwen"     "http://100.93.158.96:8081/v1/models")
R_LINUX=$(probe "linux_node"   "http://100.101.39.98:8083/v1/models")
R_PIXEL=$(probe "pixel_10"     "http://100.73.38.87:8081/v1/models")

HB=$(curl -sf --max-time 3 -X POST http://127.0.0.1:8082/v1/heartbeat \
  -H "Content-Type: application/json" \
  -d "{\"node\":\"mac_mini_m4\",\"ts\":\"$TS\"}" 2>/dev/null | \
  python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status','ok'))" 2>/dev/null || echo "no_response")

VRAM=$(curl -sf --max-time 3 "http://127.0.0.1:8082/health" 2>/dev/null | \
  python3 -c "import sys,json; d=json.load(sys.stdin); print(round(d.get('pooled_vram_gb',0),1))" 2>/dev/null || echo "?")

echo "$R_PRIMA" | grep -q "OFFLINE" && {
  echo "⚠️ prima OFFLINE — heal attempt"
  curl -sf -X POST http://127.0.0.1:8082/v1/heal 2>/dev/null || true
}

ENTRY_COUNT=$(wc -l < "$DATASET" 2>/dev/null | tr -d ' ' || echo 0)
ONLINE=$(printf '%s\n' "$R_PRIMA" "$R_QWEN" "$R_MBA" "$R_LINUX" "$R_PIXEL" | grep -c "ONLINE" || true)

echo "Nodes: $ONLINE/5 | VRAM: ${VRAM}GB | Dataset: ${ENTRY_COUNT} | hb: $HB"
printf '%s\n' "$R_PRIMA" "$R_QWEN" "$R_MBA" "$R_LINUX" "$R_PIXEL"

# Append LoRA pair
MYTS="$TS" MYVRAM="$VRAM" MYONLINE="$ONLINE" MYCOUNT="$ENTRY_COUNT" \
  MYHB="$HB" MYPRIMA="$R_PRIMA" MYQWEN="$R_QWEN" MYMBA="$R_MBA" \
  MYLINUX="$R_LINUX" MYPIXEL="$R_PIXEL" \
python3 - << 'PYEOF'
import json, os
ts     = os.environ["MYTS"]
vram   = os.environ["MYVRAM"]
online = os.environ["MYONLINE"]
count  = os.environ["MYCOUNT"]
hb     = os.environ["MYHB"]
entry = {
    "timestamp": ts,
    "category": "mesh_health_audit",
    "quality_score": 0.91,
    "conversation": [
        {"role": "user", "content": "30-min Lauburu mesh health audit + prima.cpp heartbeat"},
        {"role": "assistant", "content": (
            f"Audit {ts} | nodes={online}/5 ONLINE | VRAM={vram}GB | prima_hb={hb} | "
            + os.environ.get("MYPRIMA","?") + " | " + os.environ.get("MYQWEN","?") + " | "
            + os.environ.get("MYMBA","?") + " | " + os.environ.get("MYLINUX","?") + " | "
            + os.environ.get("MYPIXEL","?")
        )}
    ]
}
dataset = "/Volumes/Lauburu-Monorepo/04_data_and_memory/data/continuous_lora_dataset.jsonl"
with open(dataset, "a") as f:
    f.write(json.dumps(entry) + "\n")
print(f"LoRA appended. Total: {int(count)+1}")
PYEOF

echo "══════════════════════════════════════════════════"
# NOTE: Probes use HTTP API endpoints. Nodes are Tailscale-reachable even if API offline.
# For Tailscale-level health, see: /usr/local/bin/tailscale status --json
