#!/usr/bin/env bash
# ==============================================================================
# Lauburu Mesh - Router Foundation Deployment & Verification Script
# Subsystem: 00_core_infrastructure/router_foundation
# Target: GL.iNet GL-BE14000 (192.168.8.1)
#
# Idempotently deploys:
#   - R1: /etc/init.d/router_bluetooth_hub
#   - R3: /etc/hotplug.d/dhcp/10-mesh_dhcp_oracle.sh
#   - R3: /usr/bin/mesh_arp_oracle.sh
#   - R4: /usr/bin/lauburu_oob_wan_healer.sh
#   - R4: /etc/init.d/wan_healer
#   - R5: /usr/bin/edge_security_streamer.sh
#
# Validates syntax via `sh -n`, checks/installs `socat` via opkg, and registers
# procd services.
# ==============================================================================

set -euo pipefail

ROUTER_HOST="${ROUTER_HOST:-192.168.8.1}"
ROUTER_USER="${ROUTER_USER:-root}"
SSH_OPTS="-o ConnectTimeout=3 -o BatchMode=yes -o StrictHostKeyChecking=no"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ROUTER_SRC="$BASE_DIR/router"

log_info() {
    echo -e "\033[1;34m[INFO]\033[0m $1"
}

log_success() {
    echo -e "\033[1;32m[SUCCESS]\033[0m $1"
}

log_warn() {
    echo -e "\033[1;33m[WARN]\033[0m $1"
}

log_error() {
    echo -e "\033[1;31m[ERROR]\033[0m $1"
}

# 1. Local pre-flight syntax validation
log_info "Step 1: Performing local syntax validation with sh -n..."
for script in \
    "$ROUTER_SRC/etc/init.d/router_bluetooth_hub" \
    "$ROUTER_SRC/etc/init.d/wan_healer" \
    "$ROUTER_SRC/etc/init.d/mesh_arp_oracle" \
    "$ROUTER_SRC/etc/init.d/edge_security_streamer" \
    "$ROUTER_SRC/usr/bin/lauburu_oob_wan_healer.sh" \
    "$ROUTER_SRC/usr/bin/mesh_arp_oracle.sh" \
    "$ROUTER_SRC/usr/bin/edge_security_streamer.sh" \
    "$ROUTER_SRC/etc/hotplug.d/dhcp/10-mesh_dhcp_oracle.sh"; do
    if [ -f "$script" ]; then
        sh -n "$script"
        log_success "Local syntax valid: $(basename "$script")"
    else
        log_error "Missing source file: $script"
        exit 1
    fi
done

# 2. Router connectivity check
log_info "Step 2: Probing router connectivity at $ROUTER_USER@$ROUTER_HOST..."
if ! ssh $SSH_OPTS "$ROUTER_USER@$ROUTER_HOST" "uptime" >/dev/null 2>&1; then
    log_error "Cannot reach router at $ROUTER_USER@$ROUTER_HOST via SSH."
    exit 1
fi
ROUTER_UPTIME="$(ssh $SSH_OPTS "$ROUTER_USER@$ROUTER_HOST" "uptime | awk '{print \$3, \$4}' | tr -d ','")"
log_success "Router reachable (Uptime: $ROUTER_UPTIME)"

# 3. Check and install socat if missing
log_info "Step 3: Checking prerequisites on router (socat, btmon, tcpdump)..."
ssh $SSH_OPTS "$ROUTER_USER@$ROUTER_HOST" "
    if ! command -v socat >/dev/null 2>&1; then
        echo 'Installing socat via opkg...'
        opkg update && opkg install socat
    else
        echo 'socat is already installed.'
    fi

    command -v btmon >/dev/null 2>&1 || echo 'WARNING: btmon not found'
    command -v tcpdump >/dev/null 2>&1 || echo 'WARNING: tcpdump not found'
    command -v ip >/dev/null 2>&1 || echo 'WARNING: ip command not found'
"

# 4. Prepare remote directories
log_info "Step 4: Ensuring target directory layout exists on router..."
ssh $SSH_OPTS "$ROUTER_USER@$ROUTER_HOST" "mkdir -p /etc/init.d /usr/bin /etc/hotplug.d/dhcp /www /tmp"

# 5. Copy files to router using scp -O with fallback to ssh pipe
copy_file() {
    local src="$1"
    local dest="$2"
    log_info "Deploying $(basename "$src") -> $dest"
    if ! scp -O $SSH_OPTS "$src" "$ROUTER_USER@$ROUTER_HOST:$dest" 2>/dev/null; then
        # Fallback to SSH cat pipe if scp fails
        ssh $SSH_OPTS "$ROUTER_USER@$ROUTER_HOST" "cat > '$dest'" < "$src"
    fi
}

log_info "Step 5: Copying components to router..."
copy_file "$ROUTER_SRC/etc/init.d/router_bluetooth_hub" "/etc/init.d/router_bluetooth_hub"
copy_file "$ROUTER_SRC/etc/init.d/wan_healer" "/etc/init.d/wan_healer"
copy_file "$ROUTER_SRC/etc/init.d/mesh_arp_oracle" "/etc/init.d/mesh_arp_oracle"
copy_file "$ROUTER_SRC/etc/init.d/edge_security_streamer" "/etc/init.d/edge_security_streamer"
copy_file "$ROUTER_SRC/usr/bin/lauburu_oob_wan_healer.sh" "/usr/bin/lauburu_oob_wan_healer.sh"
copy_file "$ROUTER_SRC/usr/bin/mesh_arp_oracle.sh" "/usr/bin/mesh_arp_oracle.sh"
copy_file "$ROUTER_SRC/usr/bin/edge_security_streamer.sh" "/usr/bin/edge_security_streamer.sh"
copy_file "$ROUTER_SRC/etc/hotplug.d/dhcp/10-mesh_dhcp_oracle.sh" "/etc/hotplug.d/dhcp/10-mesh_dhcp_oracle.sh"

# 6. Set executable permissions on router
log_info "Step 6: Setting executable permissions..."
ssh $SSH_OPTS "$ROUTER_USER@$ROUTER_HOST" "chmod +x \
    /etc/init.d/router_bluetooth_hub \
    /etc/init.d/wan_healer \
    /etc/init.d/mesh_arp_oracle \
    /etc/init.d/edge_security_streamer \
    /usr/bin/lauburu_oob_wan_healer.sh \
    /usr/bin/mesh_arp_oracle.sh \
    /usr/bin/edge_security_streamer.sh \
    /etc/hotplug.d/dhcp/10-mesh_dhcp_oracle.sh"

# 7. Remote syntax verification on the router shell
log_info "Step 7: Validating script syntax directly on router (/bin/sh -n)..."
ssh $SSH_OPTS "$ROUTER_USER@$ROUTER_HOST" "
    set -e
    for s in \
        /etc/init.d/router_bluetooth_hub \
        /etc/init.d/wan_healer \
        /etc/init.d/mesh_arp_oracle \
        /etc/init.d/edge_security_streamer \
        /usr/bin/lauburu_oob_wan_healer.sh \
        /usr/bin/mesh_arp_oracle.sh \
        /usr/bin/edge_security_streamer.sh \
        /etc/hotplug.d/dhcp/10-mesh_dhcp_oracle.sh; do
        /bin/sh -n \"\$s\"
        echo \"[OK] \$s syntax verified on router\"
    done
"

# 8. Enable and restart procd services
log_info "Step 8: Registering, enabling, and restarting procd services..."
ssh $SSH_OPTS "$ROUTER_USER@$ROUTER_HOST" "
    /etc/init.d/router_bluetooth_hub enable
    /etc/init.d/router_bluetooth_hub restart
    /etc/init.d/wan_healer enable
    /etc/init.d/wan_healer restart
    /etc/init.d/mesh_arp_oracle enable
    /etc/init.d/mesh_arp_oracle restart
    /etc/init.d/edge_security_streamer enable
    /etc/init.d/edge_security_streamer restart
"

# 9. Verify single probe run of WAN healer
log_info "Step 9: Testing single FSM probe run of lauburu_oob_wan_healer.sh..."
ssh $SSH_OPTS "$ROUTER_USER@$ROUTER_HOST" "/usr/bin/lauburu_oob_wan_healer.sh --check-once"

# 10. Verify live status of router foundation services
log_info "Step 10: Verifying live status of services and ports..."
ssh $SSH_OPTS "$ROUTER_USER@$ROUTER_HOST" "
    echo '=== Controller Discovery State ==='
    bluetoothctl show 2>/dev/null | grep -E 'Powered|Discovering' || true
    echo '=== Active Listening Ports (9002, 9005) ==='
    netstat -tlpn 2>/dev/null | grep -E ':(9002|9005)' || true
    echo '=== Running Procd Service Instances ==='
    ps | grep -E 'btmon|socat|mesh_arp|edge_security|wan_healer' | grep -v grep || true
"

log_success "================================================================="
log_success "All Router Foundation components deployed and verified on router!"
log_success "================================================================="
