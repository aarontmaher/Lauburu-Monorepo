#!/usr/bin/env bash
# ==============================================================================
# LAUBURU SEAWEEDFS 3-NODE RAFT HA CLUSTER DEPLOYMENT & BOOTSTRAPPER
# Subsystem: 00_core_infrastructure/scripts
# Target: 7-Node Tailscale Mesh (Linux Head, Mac Host, MacBook Pro Vault)
# Master Peers: 100.101.39.98:9333, 100.119.199.76:9333, 100.103.212.21:9333
# ==============================================================================
set -euo pipefail

# --- Color Output Helpers ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# --- Cluster Configuration ---
MASTER_PEERS="${DFS_MASTER_PEERS:-100.101.39.98:9333,100.119.199.76:9333,100.103.212.21:9333}"
FILER_PEERS="${DFS_FILER_PEERS:-100.101.39.98:8888,100.119.199.76:8888,100.103.212.21:8888}"

NODE1_IP="100.101.39.98"   # Linux Head Node (Peer 1)
NODE2_IP="100.119.199.76"  # Mac Host (M4 Mini Host) (Peer 2)
NODE3_IP="100.103.212.21"  # MacBook Pro Vault (Peer 3)

log_info() { echo -e "${CYAN}$(date -u +'%Y-%m-%dT%H:%M:%SZ') [INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}$(date -u +'%Y-%m-%dT%H:%M:%SZ') [SUCCESS]${NC} $*"; }
log_warn() { echo -e "${YELLOW}$(date -u +'%Y-%m-%dT%H:%M:%SZ') [WARN]${NC} $*"; }
log_error() { echo -e "${RED}$(date -u +'%Y-%m-%dT%H:%M:%SZ') [ERROR]${NC} $*" >&2; }

# --- Step 1: Pre-Flight Tailscale Interface & Socket Checks ---
check_tailscale_connectivity() {
    log_info "Verifying Tailscale reachability across Raft peer nodes..."
    local peers=("$NODE1_IP" "$NODE2_IP" "$NODE3_IP")
    for peer in "${peers[@]}"; do
        if ping -c 1 -W 2 "$peer" >/dev/null 2>&1; then
            log_success "Node $peer is reachable via ICMP."
        else
            log_warn "Node $peer did not respond to ICMP ping (may be firewalled, sleeping, or off-mesh)."
        fi
    done
}

# --- Step 2: Ensure Storage Directories Exist ---
prepare_local_directories() {
    log_info "Preparing local storage brick directories..."
    local os_type
    os_type="$(uname -s)"
    
    if [ "$os_type" = "Linux" ]; then
        mkdir -p /mnt/ssd_1tb/dfs_master /mnt/ssd_1tb/dfs_filer /mnt/ssd_1tb/dfs_bricks 2>/dev/null || true
        chmod -R 755 /mnt/ssd_1tb/dfs_master /mnt/ssd_1tb/dfs_filer /mnt/ssd_1tb/dfs_bricks 2>/dev/null || true
    elif [ "$os_type" = "Darwin" ]; then
        mkdir -p "$HOME/.local/var/seaweedfs/master" \
                 "$HOME/.local/var/seaweedfs/filer" \
                 "$HOME/.local/var/seaweedfs/volume" \
                 "$REPO_ROOT/data/dfs_bricks" \
                 "$REPO_ROOT/data/dfs_master" \
                 "$REPO_ROOT/data/dfs_filer" 2>/dev/null || true
    fi
}

# --- Step 3: Deploy Local Node via Docker Compose (Linux) or Native (macOS) ---
start_local_stack() {
    local os_type
    os_type="$(uname -s)"
    log_info "Starting SeaweedFS HA service stack on local host ($os_type)..."

    if [ "$os_type" = "Linux" ]; then
        local compose_file="$REPO_ROOT/00_core_infrastructure/docker/docker-compose.dfs-ha.yml"
        if [ ! -f "$compose_file" ]; then
            compose_file="$REPO_ROOT/00_core_infrastructure/seaweedfs/docker-compose.yml"
        fi
        log_info "Executing Docker Compose: $compose_file"
        if command -v docker >/dev/null 2>&1; then
            docker compose -f "$compose_file" up -d --remove-orphans
            log_success "Docker Compose stack deployed successfully."
        else
            log_error "Docker is not installed or not in PATH."
            return 1
        fi
    elif [ "$os_type" = "Darwin" ]; then
        # Check if local weed binary exists
        local weed_bin=""
        if [ -x "/Users/aaron/.local/bin/weed" ]; then
            weed_bin="/Users/aaron/.local/bin/weed"
        elif [ -x "/usr/local/bin/weed" ]; then
            weed_bin="/usr/local/bin/weed"
        elif command -v weed >/dev/null 2>&1; then
            weed_bin="$(command -v weed)"
        fi

        if [ -z "$weed_bin" ]; then
            log_warn "SeaweedFS native binary 'weed' not found in PATH or standard paths."
            log_info "Checking Docker Compose fallback on macOS..."
            local compose_file="$REPO_ROOT/00_core_infrastructure/seaweedfs/docker-compose.yml"
            if command -v docker >/dev/null 2>&1 && [ -f "$compose_file" ]; then
                NODE_IP="$NODE2_IP" docker compose -f "$compose_file" up -d --remove-orphans || true
            fi
            return 0
        fi

        log_info "Launching native SeaweedFS server on macOS node ($NODE2_IP) using $weed_bin..."
        pkill -f "weed (server|master|filer|volume)" 2>/dev/null || true
        sleep 1

        local log_file="/tmp/seaweed_mac_host.log"
        nohup "$weed_bin" server \
            -dir="$HOME/.local/var/seaweedfs" \
            -ip="$NODE2_IP" \
            -ip.bind=0.0.0.0 \
            -master.port=9333 \
            -master.port.grpc=19333 \
            -master.peers="$MASTER_PEERS" \
            -master.electionTimeout=2s \
            -master.heartbeatInterval=200ms \
            -filer=true \
            -filer.port=8888 \
            -filer.port.grpc=18888 \
            -volume=true \
            -volume.port=8080 \
            -volume.port.grpc=18080 \
            -volume.max=25 \
            -dataCenter=Thunderbolt \
            -volume.publicUrl="$NODE2_IP:8080" \
            -telemetry=false > "$log_file" 2>&1 &

        log_success "Native SeaweedFS server process started (PID: $!). Logs: $log_file"
    fi
}

# --- Step 4: Validate Cluster Raft Convergence ---
validate_cluster() {
    log_info "Waiting 5 seconds for Raft consensus convergence..."
    sleep 5

    local validator_script="$SCRIPT_DIR/validate_seaweed_ha.sh"
    if [ -f "$validator_script" ]; then
        bash "$validator_script" "$MASTER_PEERS" || true
    else
        log_warn "Validator script not found at $validator_script. Running inline curl probe..."
        curl -s "http://$NODE1_IP:9333/cluster/status" | jq . || true
        curl -s "http://$NODE2_IP:9333/cluster/status" | jq . || true
        curl -s "http://$NODE3_IP:9333/cluster/status" | jq . || true
    fi
}

# --- Main Entry Point ---
main() {
    echo -e "${BOLD}${BLUE}================================================================${NC}"
    echo -e "${BOLD}${BLUE}     LAUBURU SEAWEEDFS 3-NODE RAFT HA CLUSTER DEPLOYER          ${NC}"
    echo -e "${BOLD}${BLUE}================================================================${NC}"
    log_info "Master Peers: $MASTER_PEERS"
    
    check_tailscale_connectivity
    prepare_local_directories
    start_local_stack
    validate_cluster

    log_success "SeaweedFS 3-Node Raft Cluster deployment workflow complete."
}

main "$@"
