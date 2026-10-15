#!/usr/bin/env bash
# s20_mesh_monitor.sh
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Lauburu Mesh - L7 Samsung S20 7-Layer Mesh Network Monitor & Fleet Attach
#
# Polling:
#   Polls connectivity (ICMP/RTT) and interface states across all 7 mesh layers:
#   L1 (Mac Host), L2 (MacBook Pro), L3 (Linux Mini), L4 (Linux Tablet),
#   L5 (MacBook Air), L6 (Pixel 10), L7 (Samsung S20), and GW (GL.iNet).
#
# Fleet Attach:
#   Offers single-key shortcut ('a') to seamlessly attach to `mesh_agy_fleet`
#   tmux session directly (if on Mac Host) or over SSH back to Mac Mini Host.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAC_HOST_LAN="192.168.8.230"
MAC_HOST_TAILSCALE="100.119.199.76"
MAC_USER="aaron"
TMUX_SESSION="mesh_agy_fleet"

# Device definitions: Name | Local IP | Tailscale IP | Role
DEVICES=(
    "L1_Mac_Host|192.168.8.230|100.119.199.76|Master Orchestrator"
    "L2_MacBook_Pro|192.168.8.127|100.103.212.21|GPU Metal Vault"
    "L3_Linux_Mini|192.168.8.224|100.101.39.98|Compute & Docker Hub"
    "L4_Linux_Tablet|DHCP|100.81.92.125|Mobile DSP & Standby"
    "L5_MacBook_Air|192.168.8.222|100.93.158.96|Secondary Metal"
    "L6_Pixel_10_Pro_XL|DHCP|100.73.38.87|Edge TPU & Vision"
    "L7_Samsung_S20|192.168.8.131|100.78.206.96|Automated ADB Tester"
    "GW_GLiNet_Router|192.168.8.1|100.103.212.34|Sovereign Gateway"
)

# Ping helper returning latency or OFFLINE
check_ping() {
    local target="$1"
    if [ "$target" = "DHCP" ] || [ -z "$target" ]; then
        echo "N/A"
        return
    fi
    
    local ping_output=""
    if [[ "$OSTYPE" == "darwin"* ]]; then
        ping_output=$(ping -c 1 -W 300 "$target" 2>/dev/null || true)
    else
        ping_output=$(ping -c 1 -W 1 "$target" 2>/dev/null || true)
    fi

    if echo "$ping_output" | grep -q "1 packets received\|1 packets transmitted, 1 received\|1 received"; then
        local rtt=$(echo "$ping_output" | awk -F'/' 'END{print $5}' | cut -d'.' -f1)
        if [ -n "$rtt" ]; then
            echo "${rtt}ms"
        else
            echo "ONLINE"
        fi
    else
        echo "OFFLINE"
    fi
}

# Non-interactive / JSON mode handler
if [ "$1" = "--json" ] || [ "$1" = "-j" ]; then
    echo "{"
    echo '  "timestamp": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'",'
    echo '  "devices": ['
    count=${#DEVICES[@]}
    i=0
    for dev_entry in "${DEVICES[@]}"; do
        IFS="|" read -r name lan_ip ts_ip role <<< "$dev_entry"
        lan_stat=$(check_ping "$lan_ip")
        ts_stat=$(check_ping "$ts_ip")
        comma=","
        [ $i -eq $((count - 1)) ] && comma=""
        echo "    {\"name\": \"$name\", \"role\": \"$role\", \"lan_ip\": \"$lan_ip\", \"lan_status\": \"$lan_stat\", \"tailscale_ip\": \"$ts_ip\", \"tailscale_status\": \"$ts_stat\"}$comma"
        i=$((i + 1))
    done
    echo "  ]"
    echo "}"
    exit 0
fi

# Visual Dashboard
clear 2>/dev/null || true
echo "================================================================================"
echo "           🌐 LAUBURU 7-LAYER PHYSICAL MESH MONITOR (L7 S20 LENS)               "
echo "================================================================================"
printf "%-18s %-20s %-16s %-10s %-10s\n" "NODE" "ROLE" "TARGET IP" "LAN" "TAILSCALE"
echo "--------------------------------------------------------------------------------"

for dev_entry in "${DEVICES[@]}"; do
    IFS="|" read -r name lan_ip ts_ip role <<< "$dev_entry"
    lan_stat=$(check_ping "$lan_ip")
    ts_stat=$(check_ping "$ts_ip")
    printf "%-18s %-20s %-16s %-10s %-10s\n" "$name" "$role" "$lan_ip" "$lan_stat" "$ts_stat"
done

echo "================================================================================"
echo "[*] Router & Gateway Diagnostics:"
python3 "$SCRIPT_DIR/glinet_luci_tools.py" --action wg_client_status 2>/dev/null | grep -E "success|host|command" || echo "    (Router query completed)"

echo "--------------------------------------------------------------------------------"
echo "[*] Samsung S20 (L7) Local/Shizuku Diagnostics:"
python3 "$SCRIPT_DIR/s20_shizuku_network.py" --action ping --host 127.0.0.1 --count 1 2>/dev/null | grep -E "success|transport|exit_code" || echo "    (S20 probe completed)"

echo "================================================================================"

# If running in batch or non-interactive mode, exit cleanly
if [ ! -t 0 ] || [ "$1" = "--batch" ] || [ "${BATCH_MODE:-0}" = "1" ]; then
    echo "[*] Batch mode detected. Monitoring sweep complete."
    exit 0
fi

echo -n "Press [a] to attach to '${TMUX_SESSION}' tmux fleet, or any other key to exit: "
read -n 1 -r choice
echo ""

if [ "$choice" = "a" ] || [ "$choice" = "A" ]; then
    echo "[*] Attaching to tmux fleet session '${TMUX_SESSION}'..."
    if [ "$(hostname)" = "aaron-macmini" ] || [ -f "/Users/aaron/.gemini/config/rules/00_canonical_hardware_matrix.md" ]; then
        if tmux has-session -t "$TMUX_SESSION" 2>/dev/null; then
            exec tmux attach -t "$TMUX_SESSION"
        else
            echo "[*] Session '${TMUX_SESSION}' not found locally. Spawning..."
            tmux new-session -d -s "$TMUX_SESSION"
            exec tmux attach -t "$TMUX_SESSION"
        fi
    else
        echo "[*] Initiating SSH bridge to Mac Host ($MAC_HOST_LAN)..."
        ssh -o StrictHostKeyChecking=no -o ConnectTimeout=3 -t "${MAC_USER}@${MAC_HOST_LAN}" "tmux attach -t ${TMUX_SESSION} || tmux new -s ${TMUX_SESSION}" || \
        ssh -o StrictHostKeyChecking=no -o ConnectTimeout=3 -t "${MAC_USER}@${MAC_HOST_TAILSCALE}" "tmux attach -t ${TMUX_SESSION} || tmux new -s ${TMUX_SESSION}"
    fi
else
    echo "[*] Exiting monitor."
fi
