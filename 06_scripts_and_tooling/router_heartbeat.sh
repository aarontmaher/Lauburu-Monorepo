#!/bin/sh
# /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/router_heartbeat.sh
# Intended for GL.iNet OpenWrt Cron (run every 1 minute)
# * * * * * /root/router_heartbeat.sh

L1_IP="192.168.8.230"
L1_TS_IP="100.119.199.76"
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

# 3. Fire UDP Heartbeat payload to Mac Host across both LAN and Tailscale paths via Python socket
python3 -c "
import socket, json, time, sys
payload = json.dumps({'node': 'GL-MT3600BE', 'state': '$STATE', 'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ')}).encode('utf-8')
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(1.0)
for ip in ['$L1_IP', '$L1_TS_IP']:
    try:
        sock.sendto(payload, (ip, $HEARTBEAT_PORT))
    except Exception:
        pass
sock.close()
" 2>/dev/null || true
