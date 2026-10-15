#!/usr/bin/env bash
# ==============================================================================
# 🚀 L3 Linux Laptop prima.cpp Auto-Deployment Watcher Daemon
# Continuously monitors candidate IPs (Tailscale 10.1.0.12 / LAN 192.168.8.224/225)
# Autonomously deploys and enables ggml-rpc-server on Port 50052 upon network ingress.
# ==============================================================================

echo "[L3_WATCHER] Started listening for L3 Linux Laptop network ingress..."

while true; do
  for ip in 10.1.0.12 192.168.8.224 192.168.8.225; do
    if nc -z -w 1 "$ip" 22 2>/dev/null; then
      echo "[L3_WATCHER] 🟢 Detected active SSH listener on $ip! Deploying prima.cpp..."
      
      # Attempt SSH deployment as 'linux' user, fallback to 'aaron'
      for user in linux aaron; do
        ssh -o BatchMode=yes -o StrictHostKeyChecking=no -o ConnectTimeout=3 "${user}@${ip}" "
          # 1. Kill stale rpc-server if present
          killall ggml-rpc-server 2>/dev/null || true
          
          # 2. Locate or launch binary
          RPC_BIN=\$(which ggml-rpc-server 2>/dev/null || find /home/${user} -name ggml-rpc-server 2>/dev/null | head -n 1)
          if [ -n \"\$RPC_BIN\" ] && [ -x \"\$RPC_BIN\" ]; then
            nohup \"\$RPC_BIN\" -H 0.0.0.0 -p 50052 -t 8 -c > /tmp/ggml_rpc.log 2>&1 &
            echo \"[L3] Launched \$RPC_BIN on :50052\"
            
            # 3. Persist systemd unit
            echo goldfighting1 | sudo -S bash -c \"cat << EOF > /etc/systemd/system/ggml-rpc-server.service
[Unit]
Description=llama.cpp GGML RPC Server
After=network.target

[Service]
Type=simple
User=${user}
ExecStart=\$RPC_BIN -H 0.0.0.0 -p 50052 -t 8 -c
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable ggml-rpc-server.service
\" 2>/dev/null || true
          fi
        " 2>/dev/null
        
        # Verify port 50052
        if nc -z -w 1 "$ip" 50052 2>/dev/null; then
          echo "[L3_WATCHER] 🎯 Port 50052 verified active on $ip! Restarting Port 4007 analyzer..."
          pkill -f "uvicorn.*4007" 2>/dev/null || true
          sleep 1
          /Users/aaron/.venv/bin/python3 -m uvicorn 01_apps.network_cable_analyzer.backend.server:app --port 4007 --host 0.0.0.0 > /dev/null 2>&1 &
          exit 0
        fi
      done
    fi
  done
  sleep 4
done
