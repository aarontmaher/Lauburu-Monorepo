#!/bin/sh
# /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/router_heartbeat.sh
# Intended for GL.iNet OpenWrt Cron (run every 1 minute)
# * * * * * /root/router_heartbeat.sh

L1_IP="192.168.8.230"
HEARTBEAT_PORT=18803

STATE="HEALTHY"

# 1. Check Tailscale
if ! ip link show tailscale0 > /dev/null 2>&1; then
    STATE="DEGRADED_TAILSCALE"
fi

# 2. Check USB ADB Daemon
if ! netstat -nlp | grep -q ":5037"; then
    if [ "$STATE" = "HEALTHY" ]; then
        STATE="DEGRADED_ADB"
    else
        STATE="${STATE}_ADB"
    fi
fi

# 3. Fire UDP Heartbeat payload to Mac Host
PAYLOAD="{\"node\": \"GL-MT3600BE\", \"state\": \"$STATE\", \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}"
echo "$PAYLOAD" | nc -u -w 1 $L1_IP $HEARTBEAT_PORT
