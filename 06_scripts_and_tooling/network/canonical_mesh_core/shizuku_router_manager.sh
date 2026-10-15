#!/usr/bin/env bash
# ==============================================================================
# LAUBURU MESH - SHIZUKU ROUTER MANAGER
# Subsystem: 06_scripts_and_tooling/network
# Purpose:   Use Samsung S20's Shizuku rish shell as a privileged bridge
#            to manage GL.iNet router, LuCI, WireGuard, and network config.
# ==============================================================================
set -euo pipefail

# --- Configuration ---
ROUTER_IP="${ROUTER_IP:-192.168.8.1}"
ROUTER_USER="root"
ROUTER_SSH_PORT=22
S20_ADB_TARGET="${S20_ADB:-192.168.8.131:5555}"
S20_SSH_USER="u0_a420"
S20_SSH_PORT=8022
PIXEL_USB_SERIAL="5B080DLCQ001LQ"
WG_SERVER_PORT=51820
WG_SUBNET="10.1.0.0/24"
REPO="/Volumes/Lauburu-Monorepo"
LOG_DIR="${REPO}/obsidian_vault/05_Hardware_Mesh/Routing_Logs"
TIMESTAMP="$(date '+%Y-%m-%d_%H%M%S')"
LOG_FILE="${LOG_DIR}/${TIMESTAMP}_shizuku_router.md"

# --- Colors ---
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'

info()  { echo -e "${GREEN}[✓]${NC} $*"; }
warn()  { echo -e "${YELLOW}[⚠]${NC} $*"; }
fail()  { echo -e "${RED}[✗]${NC} $*"; }
header(){ echo -e "\n${CYAN}=== $* ===${NC}"; }

# --- Ensure log dir exists ---
mkdir -p "$LOG_DIR" 2>/dev/null || true

# --- Helper: Execute via S20 Shizuku rish ---
rish_exec() {
    local cmd="$1"
    adb -s "$S20_ADB_TARGET" shell "
        export RISH_DEX=/data/local/tmp/rish_shizuku.dex
        sh /data/local/tmp/rish -c '$cmd'
    " 2>&1
}

# --- Helper: Router SSH command ---
router_ssh() {
    ssh -o ConnectTimeout=3 -o StrictHostKeyChecking=no -o BatchMode=yes \
        -p "$ROUTER_SSH_PORT" "${ROUTER_USER}@${ROUTER_IP}" "$1" 2>&1
}

# --- Helper: Pixel via router USB ADB ---
pixel_usb_exec() {
    local cmd="$1"
    router_ssh "adb -s $PIXEL_USB_SERIAL shell '$cmd'" 2>&1
}

# ==============================================================================
# PHASE 1: SHIZUKU HEALTH CHECK
# ==============================================================================
shizuku_health() {
    header "Shizuku Health Check"
    
    # Check ADB connectivity
    if adb -s "$S20_ADB_TARGET" shell "echo 'ADB_OK'" 2>/dev/null | grep -q 'ADB_OK'; then
        info "S20 ADB connectivity: OK ($S20_ADB_TARGET)"
    else
        fail "S20 ADB not reachable at $S20_ADB_TARGET"
        return 1
    fi
    
    # Check Shizuku server
    local shizuku_status
    shizuku_status=$(adb -s "$S20_ADB_TARGET" shell "ps -A 2>/dev/null | grep -c shizuku_server" 2>/dev/null || echo "0")
    if [ "$shizuku_status" -gt 0 ] 2>/dev/null; then
        info "Shizuku server: RUNNING"
    else
        warn "Shizuku server: DOWN — restarting..."
        adb -s "$S20_ADB_TARGET" shell "sh /sdcard/Android/data/moe.shizuku.privileged.api/files/start.sh" 2>&1
        sleep 2
    fi
    
    # Verify rish UID 2000
    local uid
    uid=$(rish_exec "id -u" 2>/dev/null | tr -d '[:space:]')
    if [ "$uid" = "2000" ]; then
        info "rish shell: UID $uid (shell) verified"
    else
        fail "rish shell: unexpected UID '$uid'"
        return 1
    fi
}

# ==============================================================================
# PHASE 2: ROUTER HEALTH AUDIT
# ==============================================================================
router_health() {
    header "GL.iNet Router Health Audit"
    
    # Uptime and load
    local uptime_info
    uptime_info=$(router_ssh "uptime | sed 's/.*up /up /' | sed 's/,.*load/ load/'")
    info "Router $uptime_info"
    
    # RAM
    local mem_info
    mem_info=$(router_ssh "free -m | awk '/Mem:/{printf \"RAM: %dMB used / %dMB total (%.0f%%)\", \$3, \$2, \$3/\$2*100}'")
    info "$mem_info"
    
    # SWAP
    local swap_active
    swap_active=$(router_ssh "cat /proc/swaps | wc -l")
    if [ "$swap_active" -gt 1 ] 2>/dev/null; then
        info "SWAP: Active ($(router_ssh "free -m | awk '/Swap:/{print \$2}' ")MB)"
    else
        warn "SWAP: NOT active"
    fi
    
    # Kernel stability
    local timer_mig
    timer_mig=$(router_ssh "sysctl -n kernel.timer_migration 2>/dev/null")
    if [ "$timer_mig" = "0" ]; then
        info "Kernel timer_migration: DISABLED (safe)"
    else
        warn "Kernel timer_migration: ENABLED (crash risk!)"
        router_ssh "sysctl -w kernel.timer_migration=0"
    fi
    
    # Repeater storm check
    local scan_int
    scan_int=$(router_ssh "uci get repeater.@main[0].switch_interval 2>/dev/null || echo 'N/A'")
    if [ "$scan_int" = "3600" ]; then
        info "Repeater scan interval: 3600s (safe)"
    elif [ "$scan_int" != "N/A" ]; then
        warn "Repeater scan interval: ${scan_int}s (should be 3600)"
    fi
    
    # Kernel panics/oops
    local crash_count
    crash_count=$(router_ssh "dmesg | grep -ciE 'oops|panic|error' 2>/dev/null || echo 0")
    if [ "$crash_count" -lt 5 ] 2>/dev/null; then
        info "Kernel errors in dmesg: $crash_count"
    else
        warn "Kernel errors in dmesg: $crash_count (review recommended)"
    fi
}

# ==============================================================================
# PHASE 3: WIREGUARD MESH AUDIT
# ==============================================================================
wireguard_audit() {
    header "WireGuard Mesh Audit"
    
    # Server status
    local peer_count
    peer_count=$(router_ssh "wg show wgserver 2>/dev/null | grep -c 'peer:' || echo 0")
    info "WG Server peers in kernel: $peer_count"
    
    # Check each peer handshake freshness
    router_ssh "
wg show wgserver dump 2>/dev/null | tail -n +2 | while IFS=\$'\t' read pubkey psk endpoint allowedips handshake rx tx keepalive; do
    name=\$(uci show wireguard_server 2>/dev/null | grep \"public_key='\${pubkey}'\" | sed 's/.public_key.*//' | xargs -I{} uci get {}.name 2>/dev/null || echo 'unknown')
    if [ \"\$handshake\" != '0' ] && [ -n \"\$handshake\" ]; then
        age=\$(( \$(date +%s) - handshake ))
        if [ \$age -lt 180 ]; then
            echo \"  🟢 \$name (\$allowedips) — handshake \${age}s ago (RX: \$rx TX: \$tx)\"
        else
            echo \"  🟡 \$name (\$allowedips) — handshake \${age}s ago (STALE)\"
        fi
    else
        echo \"  ⚪ \$name (\$allowedips) — NO handshake (dormant)\"
    fi
done
"
    
    # WG client tunnels
    local client_count
    client_count=$(router_ssh "wg show all 2>/dev/null | grep -c 'interface: wgclient' || echo 0")
    info "WG Client tunnels: $client_count"
}

# ==============================================================================
# PHASE 4: NETWORK OVERVIEW (All Devices)
# ==============================================================================
network_overview() {
    header "Mesh Network Device Overview"
    
    # DHCP leases
    router_ssh "
echo '--- Active DHCP Leases ---'
cat /tmp/dhcp.leases | while read ts mac ip name extra; do
    echo \"  \$ip  \$name  (\$mac)\"
done
"
    
    # Tailscale peers from router perspective
    info "Tailscale peer summary:"
    router_ssh "tailscale status 2>/dev/null | grep -E 'active|offline' | head -12"
    
    # USB devices
    local usb_devs
    usb_devs=$(router_ssh "lsusb 2>/dev/null | grep -v 'root hub' | grep -v '1d6b:000'")
    if [ -n "$usb_devs" ]; then
        info "Router USB devices:"
        echo "  $usb_devs"
    fi
}

# ==============================================================================
# PHASE 5: S20 WIREGUARD TUNNEL MANAGEMENT
# ==============================================================================
s20_wireguard() {
    header "S20 WireGuard Tunnel Management"
    
    # Check current VPN state
    local tun_status
    tun_status=$(rish_exec "ip addr show | grep -E 'tun|wg' | head -5" 2>/dev/null)
    if echo "$tun_status" | grep -q "10.1.0"; then
        info "S20 WireGuard tunnel: ACTIVE"
        echo "  $tun_status"
    else
        warn "S20 WireGuard tunnel: NOT active"
        info "Config available at /sdcard/WireGuard/lauburu-mesh.conf"
        info "Import in WireGuard app or use 'wg-quick up' via Termux"
    fi
    
    # Connectivity test to WG subnet
    local wg_ping
    wg_ping=$(rish_exec "ping -c 1 -W 2 10.1.0.1 2>&1 | tail -1" 2>/dev/null)
    if echo "$wg_ping" | grep -q "0%"; then
        info "S20 → WG Server (10.1.0.1): REACHABLE"
    else
        warn "S20 → WG Server (10.1.0.1): UNREACHABLE via WG"
    fi
}

# ==============================================================================
# PHASE 6: PIXEL 10 VIA ROUTER USB
# ==============================================================================
pixel_status() {
    header "Pixel 10 Pro XL (Router USB ADB)"
    
    local pixel_bat
    pixel_bat=$(pixel_usb_exec "dumpsys battery | grep level" 2>/dev/null | tr -d '[:space:]')
    if [ -n "$pixel_bat" ]; then
        info "Pixel 10 battery: $pixel_bat"
    else
        warn "Pixel 10: Not responding via router USB ADB"
        return
    fi
    
    # WireGuard on Pixel
    local pixel_wg
    pixel_wg=$(pixel_usb_exec "ip addr show | grep '10.1.0'" 2>/dev/null)
    if [ -n "$pixel_wg" ]; then
        info "Pixel WG tunnel: ACTIVE ($pixel_wg)"
    else
        warn "Pixel WG tunnel: NOT active"
    fi
}

# ==============================================================================
# PHASE 7: LUCI API HEALTH
# ==============================================================================
luci_health() {
    header "LuCI Web Admin Health"
    
    # Test LuCI accessibility
    local luci_code
    luci_code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 3 "http://${ROUTER_IP}/cgi-bin/luci/" 2>/dev/null || echo "000")
    if [ "$luci_code" = "200" ] || [ "$luci_code" = "302" ] || [ "$luci_code" = "403" ]; then
        info "LuCI web UI: Accessible (HTTP $luci_code)"
    else
        fail "LuCI web UI: NOT accessible (HTTP $luci_code)"
    fi
    
    # Check luci packages
    local luci_pkgs
    luci_pkgs=$(router_ssh "opkg list-installed | grep -c luci" 2>/dev/null || echo "0")
    info "LuCI packages installed: $luci_pkgs"
}

# ==============================================================================
# MAIN
# ==============================================================================
main() {
    echo "================================================================"
    echo "  LAUBURU MESH — SHIZUKU ROUTER MANAGER v1.0"
    echo "  Timestamp: $(date '+%Y-%m-%d %H:%M:%S %Z')"
    echo "================================================================"
    
    case "${1:-all}" in
        shizuku)     shizuku_health ;;
        router)      router_health ;;
        wireguard)   wireguard_audit ;;
        network)     network_overview ;;
        s20wg)       s20_wireguard ;;
        pixel)       pixel_status ;;
        luci)        luci_health ;;
        all)
            shizuku_health
            router_health
            wireguard_audit
            network_overview
            s20_wireguard
            pixel_status
            luci_health
            ;;
        *)
            echo "Usage: $0 {all|shizuku|router|wireguard|network|s20wg|pixel|luci}"
            exit 1
            ;;
    esac
    
    echo ""
    echo "================================================================"
    echo "  SHIZUKU ROUTER MANAGER — COMPLETE"
    echo "================================================================"
}

main "$@"
