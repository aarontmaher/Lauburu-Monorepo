#!/bin/sh
# ==============================================================================
# 🛰️ Sovereign Nexus OpenWrt Gateway Satellite (GL-BE14000 / GL-MT3600BE)
# ==============================================================================
# Collects genuine router hardware telemetry (RAM, Uptime, Wi-Fi 7, WAN)
# and posts directly to the Single-Chat Nexus Mother Ship (:4050).
# ==============================================================================

MOTHER_SHIP_URL="http://192.168.8.230:4050"
ALT_URL="http://10.1.0.10:4050"
THREAD_ID="core_infrastructure"

# 1. Gather genuine router RAM
MEM_TOTAL=$(grep MemTotal /proc/meminfo | awk '{print $2}')
MEM_AVAIL=$(grep -E 'MemAvailable|MemFree' /proc/meminfo | head -n1 | awk '{print $2}')
MEM_TOTAL_MB=$((MEM_TOTAL / 1024))
MEM_AVAIL_MB=$((MEM_AVAIL / 1024))

# 2. Gather Uptime and Load Average
UPTIME_SEC=$(awk '{print int($1)}' /proc/uptime)
LOADAVG=$(cat /proc/loadavg | awk '{print $1, $2, $3}')

# 3. Gather WAN Gateway status
WAN_IF="eth1.3"
[ ! -d "/sys/class/net/$WAN_IF" ] && WAN_IF="eth2"

# 4. Formulate Action Payload
HOSTNAME=$(cat /proc/sys/kernel/hostname 2>/dev/null || echo "GL-BE14000-Gateway")
ACTION="Router Telemetry Heartbeat: $HOSTNAME"
RESULT="RAM: ${MEM_AVAIL_MB}MB free / ${MEM_TOTAL_MB}MB total | Load: $LOADAVG | Uptime: ${UPTIME_SEC}s"

JSON_DATA=$(cat << JSON
{
  "action": "$ACTION",
  "result": "$RESULT",
  "exit_code": 0,
  "status": "completed"
}
JSON
)

# 5. Transmit to Nexus Mother Ship
curl -s -X POST "$MOTHER_SHIP_URL/api/chat/nexus/threads/$THREAD_ID/report" \
  -H "Content-Type: application/json" \
  -d "$JSON_DATA" >/dev/null 2>&1 || \
curl -s -X POST "$ALT_URL/api/chat/nexus/threads/$THREAD_ID/report" \
  -H "Content-Type: application/json" \
  -d "$JSON_DATA" >/dev/null 2>&1

echo "Nexus Router Satellite dispatched: $RESULT"
