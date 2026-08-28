#!/usr/bin/env python3
import socket
import json
import time
import subprocess
import os

UDP_IP = "0.0.0.0"
UDP_PORT = 18803
TIMEOUT_SECONDS = 90

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))
sock.settimeout(10.0)

last_heartbeat_time = time.time()
router_state = "UNKNOWN"

def trigger_resurrection(reason, state):
    print(f"[{time.strftime('%Y-%m-%dT%H:%M:%SZ')}] Triggering resurrection. Reason: {reason}")
    subprocess.run(["echo", "Resurrection triggered! (Placeholder for Wake-on-LAN / mesh-universal-ssh)"], check=False)
    
    log_file = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault/Network_Anomalies.md"
    try:
        with open(log_file, "a") as f:
            f.write(f"\n- **{time.strftime('%Y-%m-%dT%H:%M:%SZ')}**: Router Health Issue. Reason: {reason}, State: {state}. Resuscitation initiated.\n")
    except Exception:
        pass

print(f"[{time.strftime('%Y-%m-%dT%H:%M:%SZ')}] Lauburu Mac_Node Heartbeat Listener started on UDP port {UDP_PORT}")

while True:
    try:
        data, addr = sock.recvfrom(1024)
        last_heartbeat_time = time.time()
        payload = json.loads(data.decode('utf-8').strip())
        router_state = payload.get("state", "UNKNOWN")
        
        if router_state != "HEALTHY":
            trigger_resurrection("Degraded payload received", router_state)
            
    except socket.timeout:
        if time.time() - last_heartbeat_time > TIMEOUT_SECONDS:
            trigger_resurrection("Heartbeat timeout (>90s)", "OFFLINE")
            last_heartbeat_time = time.time() # Reset to prevent spamming
    except Exception as e:
        print(f"Error: {e}")
