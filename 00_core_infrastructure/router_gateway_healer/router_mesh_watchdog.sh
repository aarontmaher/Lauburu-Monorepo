#!/bin/sh
# ==============================================================================
# LAUBURU SOVEREIGN GATEWAY AUTONOMOUS MESH & DAEMON HEALER (OpenWrt POSIX)
# Subsystem: 00_core_infrastructure/router_gateway_healer
# Hardware Host: GL.iNet MT3600BE Gateway (100.122.185.123 / 192.168.8.1)
# Memory Footprint: < 4.0 MB RAM
# ==============================================================================

LOG_FILE="/var/log/mesh_watchdog.log"
STATUS_JSON="/www/mesh_status.json"
SSH_KEY="/root/.ssh/id_ed25519"
LOCK_FILE="/tmp/mesh_watchdog.lock"

# ------------------------------------------------------------------------------
# Hardware Mesh Topology & Credentials
# ------------------------------------------------------------------------------
MAC_MINI_IP="100.119.199.76"
MAC_MINI_USER="aaron"
MAC_MINI_MAC="1c:f6:4c:7d:d7:0a"

MBP_IP="100.103.212.21"
MBP_USER="aaronmaher"
MBP_MAC="98:fc:84:e6:e2:12"

MBA_IP="100.93.158.96"
MBA_USER="aaronmaher"
MBA_MAC="66:74:75:d8:16:fb"

LINUX_HEAD_IP="100.101.39.98"
LINUX_HEAD_USER="linux"
LINUX_HEAD_MAC="00:41:0e:14:28:43"

PIXEL_IP="100.73.38.87"
PIXEL_USER="u0_a363"
PIXEL_PORT="8022"

SAMSUNG_SERIAL="R3CN40CJJ1R"
SAMSUNG_IP="100.84.40.95"
SAMSUNG_USER="u0_a420"
SAMSUNG_PORT="8022"

log() {
    echo "$(date -u +'%Y-%m-%dT%H:%M:%SZ') [GATEWAY_HEALER] $*" | tee -a "$LOG_FILE"
}

# Single instance lock
if [ -f "$LOCK_FILE" ]; then
    PID=$(cat "$LOCK_FILE" 2>/dev/null)
    if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
        exit 0
    fi
fi
echo "$$" > "$LOCK_FILE"
trap 'rm -f "$LOCK_FILE"' EXIT INT TERM

# Helper: Remote SSH Execution (Dropbear compatible)
ssh_cmd() {
    local target_ip="$1"
    local target_user="$2"
    local target_port="${3:-22}"
    local cmd="$4"
    ssh -i "$SSH_KEY" -y -p "$target_port" "${target_user}@${target_ip}" "$cmd" 2>/dev/null
}

# Helper: TCP Port Probe
probe_port() {
    local ip="$1"
    local port="$2"
    nc -z -w2 "$ip" "$port" 2>/dev/null
    return $?
}

# ------------------------------------------------------------------------------
# 1. Mesh Hardware Reachability & WoL Resurrection
# ------------------------------------------------------------------------------
heal_hardware_nodes() {
    # Tailscale on router
    if ! tailscale status >/dev/null 2>&1; then
        log "[WARN] Router Tailscale down. Restarting..."
        /etc/init.d/tailscale restart >/dev/null 2>&1
        sleep 2
    fi

    # Mac Mini
    if ! ping -c 1 -W 2 "$MAC_MINI_IP" >/dev/null 2>&1; then
        log "[HEAL] Mac Mini ($MAC_MINI_IP) sleeping. Broadcasting WoL..."
        etherwake -i br-lan "$MAC_MINI_MAC" 2>/dev/null || true
    fi

    # MacBook Pro
    if ! ping -c 1 -W 2 "$MBP_IP" >/dev/null 2>&1; then
        etherwake -i br-lan "$MBP_MAC" 2>/dev/null || true
    fi

    # Linux Head Node
    if ! ping -c 1 -W 2 "$LINUX_HEAD_IP" >/dev/null 2>&1; then
        etherwake -i br-lan "$LINUX_HEAD_MAC" 2>/dev/null || true
    fi

    # Samsung S20 USB ADB
    adb start-server >/dev/null 2>&1
    if adb devices 2>/dev/null | grep -q "$SAMSUNG_SERIAL.*device"; then
        if ! adb -s "$SAMSUNG_SERIAL" shell ps -ef 2>/dev/null | grep -q "moe.shizuku.privileged.api"; then
            log "[HEAL] Bootstrapping Shizuku on Samsung S20 via USB..."
            adb -s "$SAMSUNG_SERIAL" shell 'sh /sdcard/Android/data/moe.shizuku.privileged.api/start.sh || sh /storage/emulated/0/Android/data/moe.shizuku.privileged.api/start.sh' >/dev/null 2>&1 || true
            adb -s "$SAMSUNG_SERIAL" tcpip 5555 >/dev/null 2>&1 || true
        fi
        adb -s "$SAMSUNG_SERIAL" shell dumpsys deviceidle whitelist +com.termux >/dev/null 2>&1 || true
        adb -s "$SAMSUNG_SERIAL" shell dumpsys deviceidle whitelist +com.tailscale.ipn >/dev/null 2>&1 || true
    fi
}

# ------------------------------------------------------------------------------
# 2. AI Inference Daemons (llama.cpp, Petals, Exo, Accelerate)
# ------------------------------------------------------------------------------
heal_ai_daemons() {
    # 2.1 llama.cpp Local OpenAI Server (Port 8081 / 8082 / 8083)
    if ping -c 1 -W 1 "$MAC_MINI_IP" >/dev/null 2>&1; then
        if ! probe_port "$MAC_MINI_IP" 8081; then
            log "[HEAL] llama.cpp (8081) on Mac Mini offline. Attempting automated relaunch..."
            ssh_cmd "$MAC_MINI_IP" "$MAC_MINI_USER" 22 "
                if [ -f ~/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/multi_wan/launch_llama_server.sh ]; then
                    nohup bash ~/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/multi_wan/launch_llama_server.sh >/dev/null 2>&1 &
                fi
            " &
        fi
    fi

    # 2.2 Exo Distributed P2P AI Mesh (Port 52415)
    if ping -c 1 -W 1 "$MAC_MINI_IP" >/dev/null 2>&1; then
        if ! probe_port "$MAC_MINI_IP" 52415; then
            log "[INFO] Exo P2P port 52415 offline on Mac Mini."
        fi
    fi

    # 2.3 Petals DHT Worker on Linux Head Node
    if ping -c 1 -W 1 "$LINUX_HEAD_IP" >/dev/null 2>&1; then
        if ! probe_port "$LINUX_HEAD_IP" 31337; then
            log "[INFO] Petals DHT swarm port offline on Linux Head Node."
        fi
    fi
}

# ------------------------------------------------------------------------------
# 3. Infrastructure, Storage & Cloudflare Edge Daemons
# ------------------------------------------------------------------------------
heal_infrastructure_daemons() {
    # 3.1 SeaweedFS Distributed Storage Filer (Port 8888 on Linux Head / Mac Mini)
    if ping -c 1 -W 1 "$LINUX_HEAD_IP" >/dev/null 2>&1; then
        if ! probe_port "$LINUX_HEAD_IP" 8888; then
            log "[HEAL] SeaweedFS Filer (8888) on Linux Head Node offline. Restarting docker container..."
            ssh_cmd "$LINUX_HEAD_IP" "$LINUX_HEAD_USER" 22 "docker restart lauburu_seaweed_filer || docker restart seaweed_filer" &
        fi
    fi

    # 3.2 Cloudflare Tunnel (`cloudflared`) on Mac Mini / Linux
    if ping -c 1 -W 1 "$MAC_MINI_IP" >/dev/null 2>&1; then
        ssh_cmd "$MAC_MINI_IP" "$MAC_MINI_USER" 22 "
            if ! pgrep -x cloudflared >/dev/null 2>&1; then
                brew services restart cloudflared >/dev/null 2>&1 || nohup cloudflared tunnel run >/dev/null 2>&1 &
            fi
        " &
    fi

    # 3.3 Self-Healing Hub (Reflex Arc API Port 18802)
    if ping -c 1 -W 1 "$MAC_MINI_IP" >/dev/null 2>&1; then
        if ! probe_port "$MAC_MINI_IP" 18802; then
            ssh_cmd "$MAC_MINI_IP" "$MAC_MINI_USER" 22 "
                if [ -f ~/DFS_UNIFIED/Lauburu-Monorepo/self_healing_hub/src/universal_mesh_healer.py ]; then
                    nohup python3 ~/DFS_UNIFIED/Lauburu-Monorepo/self_healing_hub/src/universal_mesh_healer.py >/dev/null 2>&1 &
                fi
            " &
        fi
    fi

    # 3.4 Qdrant Vector DB (Port 6333)
    if ping -c 1 -W 1 "$MAC_MINI_IP" >/dev/null 2>&1; then
        if ! probe_port "$MAC_MINI_IP" 6333; then
            ssh_cmd "$MAC_MINI_IP" "$MAC_MINI_USER" 22 "docker start qdrant || docker restart qdrant" &
        fi
    fi
}

# ------------------------------------------------------------------------------
# 4. Generate Comprehensive Structured JSON Telemetry
# ------------------------------------------------------------------------------
emit_telemetry() {
    local TS_STATE="online"
    local MAC_STATE="offline"
    local MBP_STATE="offline"
    local MBA_STATE="offline"
    local SAM_STATE="offline"
    local PIX_STATE="offline"
    local LNX_STATE="offline"

    local LLAMA_STATE="offline"
    local SEAWEED_STATE="offline"
    local QDRANT_STATE="offline"
    local HUB_STATE="offline"

    tailscale status >/dev/null 2>&1 || TS_STATE="degraded"
    ping -c 1 -W 1 "$MAC_MINI_IP" >/dev/null 2>&1 && MAC_STATE="online"
    ping -c 1 -W 1 "$MBP_IP" >/dev/null 2>&1 && MBP_STATE="online"
    ping -c 1 -W 1 "$MBA_IP" >/dev/null 2>&1 && MBA_STATE="online"
    ping -c 1 -W 1 "$LINUX_HEAD_IP" >/dev/null 2>&1 && LNX_STATE="online"
    ping -c 1 -W 1 "$PIXEL_IP" >/dev/null 2>&1 && PIX_STATE="online"
    (adb devices 2>/dev/null | grep -q "$SAMSUNG_SERIAL.*device" || ping -c 1 -W 1 "$SAMSUNG_IP" >/dev/null 2>&1) && SAM_STATE="online"

    probe_port "$MAC_MINI_IP" 8081 && LLAMA_STATE="online"
    probe_port "$LINUX_HEAD_IP" 8888 && SEAWEED_STATE="online"
    probe_port "$MAC_MINI_IP" 6333 && QDRANT_STATE="online"
    probe_port "$MAC_MINI_IP" 18802 && HUB_STATE="online"

    mkdir -p /www 2>/dev/null || true
    cat << EOF > "$STATUS_JSON"
{
  "timestamp": "$(date -u +'%Y-%m-%dT%H:%M:%SZ')",
  "gateway": "GL-MT3600BE",
  "gateway_tailscale_ip": "100.122.185.123",
  "gateway_lan_ip": "192.168.8.1",
  "hardware_layers": {
    "l1_mac_mini": "$MAC_STATE",
    "l2_macbook_pro": "$MBP_STATE",
    "l3_linux_head_node": "$LNX_STATE",
    "l5_macbook_air": "$MBA_STATE",
    "l6_pixel_10_pro": "$PIX_STATE",
    "l7_samsung_s20": "$SAM_STATE"
  },
  "daemons": {
    "tailscale_mesh": "$TS_STATE",
    "llamacpp_rpc": "$LLAMA_STATE",
    "seaweedfs_storage": "$SEAWEED_STATE",
    "qdrant_vector_db": "$QDRANT_STATE",
    "self_healing_hub_18802": "$HUB_STATE"
  }
}
EOF
}

# Main Execution Flow
heal_hardware_nodes
heal_ai_daemons
heal_infrastructure_daemons
emit_telemetry
