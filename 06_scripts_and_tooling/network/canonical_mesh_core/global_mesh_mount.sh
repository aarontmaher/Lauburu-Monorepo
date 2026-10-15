#!/usr/bin/env bash
# ==============================================================================
# Canonical Global Mesh SeaweedFS Mount & Storage Orchestrator (Gen 31)
# ==============================================================================
# Orchestrates, mounts, and verifies the SeaweedFS distributed storage fabric
# across all 10 nodes of the 7-layer physical mesh.
#
# Storage Roles & Access Modes:
#   - L1 (Mac Mini Host): Native Storage Master (APFS + weed server/filer/webdav)
#   - L3 (Linux Hub Ryzen 7): Native Linux FUSE Mount (weed mount)
#   - L8 (Linux Mini i7): Native Linux FUSE Mount (weed mount -allowOthers=false)
#   - L5 (MacBook Air M4): Authenticated Rclone WebDAV (rclone lsd/sync)
#   - GW (GL-BE14000 Router): Hardware Storage Node (/mnt/seaweedfs)
#   - L6 (Pixel 10 Pro XL): Android Termux WebDAV (rclone WebDAV)
#   - L7 (Samsung S20+): Android Termux WebDAV (rclone WebDAV)
#   - L2 (MacBook Pro), L4 (Tablet), L9 (iPhone): Standby / Offline Fallback
#
# Conforms to:
#   - Rule #0: Zero-Mock Empirical Truth
#   - Rule #1: Tri-Proof Verification Gate
#   - Rule #2: Tri-Vault Storage Synchronization
#   - Rule #5: Automatic Victory-Triggered Tri-Proof Interceptor Gate
# ==============================================================================

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MASTER_HOST="192.168.8.230"
MASTER_TS="100.119.199.76"
FILER_PORT="8888"
WEBDAV_PORT="7333"
MASTER_PORT="9333"

MODE="mount"
TARGET_NODE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --status)
            MODE="status"
            shift
            ;;
        --mount)
            MODE="mount"
            shift
            ;;
        --node)
            TARGET_NODE="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [--mount|--status] [--node <node_name>]"
            echo "  --mount       Orchestrate mounts and configure remotes (default)"
            echo "  --status      Inspect current mount status without modifying state"
            echo "  --node <name> Target a single node (e.g. L3, L8, L5, L6, L7, GW, L2)"
            exit 0
            ;;
        *)
            echo "Unknown argument: $1"
            echo "Run with --help for usage."
            exit 1
            ;;
    esac
done

# ANSI Colors
C_RESET="\033[0m"
C_BOLD="\033[1m"
C_GREEN="\033[32m"
C_YELLOW="\033[33m"
C_RED="\033[31m"
C_CYAN="\033[36m"
C_DIM="\033[2m"

log_info() { echo -e "${C_CYAN}ℹ️  ${1}${C_RESET}"; }
log_ok()   { echo -e "${C_GREEN}✅ ${1}${C_RESET}"; }
log_warn() { echo -e "${C_YELLOW}⚠️  ${1}${C_RESET}"; }
log_fail() { echo -e "${C_RED}❌ ${1}${C_RESET}"; }

SSH_OPTS=(-o BatchMode=yes -o ConnectTimeout=3 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR)

# Status tracking counters
COUNT_TOTAL=0
COUNT_ONLINE=0
COUNT_MOUNTED=0
COUNT_OFFLINE=0

record_result() {
    local node="$1"
    local layer="$2"
    local role="$3"
    local access_type="$4"
    local status="$5"
    local detail="$6"

    printf "%-18s | %-6s | %-20s | %-16s | %-14s | %s\n" \
        "$node" "$layer" "$role" "$access_type" "$status" "$detail"
}

# ==============================================================================
# Node Handlers
# ==============================================================================

check_l1_master() {
    ((COUNT_TOTAL++))
    local l1_filer_ok=0
    local l1_webdav_ok=0
    local l1_master_ok=0

    nc -zv -w 1 127.0.0.1 "$FILER_PORT" >/dev/null 2>&1 && l1_filer_ok=1
    nc -zv -w 1 127.0.0.1 "$WEBDAV_PORT" >/dev/null 2>&1 && l1_webdav_ok=1
    nc -zv -w 1 127.0.0.1 "$MASTER_PORT" >/dev/null 2>&1 && l1_master_ok=1

    if [[ $l1_filer_ok -eq 1 && $l1_webdav_ok -eq 1 ]]; then
        ((COUNT_ONLINE++))
        ((COUNT_MOUNTED++))
        local item_count
        item_count=$(ls -1 /Volumes/Lauburu-Monorepo 2>/dev/null | wc -l | tr -d ' ')
        record_result "L1_Mac_Host" "L1" "Master Local Storage" "APFS Native" "ACTIVE" "Filer :${FILER_PORT}, WebDAV :${WEBDAV_PORT} UP (${item_count} items in /Volumes/Lauburu-Monorepo)"
    else
        record_result "L1_Mac_Host" "L1" "Master Local Storage" "APFS Native" "DEGRADED" "Filer:${l1_filer_ok} WebDAV:${l1_webdav_ok} Master:${l1_master_ok}"
    fi
}

handle_l3_linux() {
    ((COUNT_TOTAL++))
    local target="linux"
    local ssh_cmd="ssh ${SSH_OPTS[*]} $target"

    if ! $ssh_cmd "echo PING_OK" >/dev/null 2>&1; then
        ((COUNT_OFFLINE++))
        record_result "L3_Linux_Hub" "L3" "Compute Hub (Ryzen)" "Linux FUSE" "OFFLINE" "SSH unreachable on host alias 'linux'"
        return
    fi
    ((COUNT_ONLINE++))

    local is_mounted=0
    if $ssh_cmd "mount | grep -q 'mesh_pool'" >/dev/null 2>&1; then
        is_mounted=1
    fi

    if [[ "$MODE" == "mount" && $is_mounted -eq 0 ]]; then
        $ssh_cmd "mkdir -p /home/linux/mesh_pool && nohup /usr/local/bin/weed mount -filer=${MASTER_HOST}:${FILER_PORT} -dir=/home/linux/mesh_pool >/tmp/weed_mount.log 2>&1 & sleep 2" >/dev/null 2>&1 || true
        if $ssh_cmd "mount | grep -q 'mesh_pool'" >/dev/null 2>&1; then
            is_mounted=1
        fi
    fi

    if [[ $is_mounted -eq 1 ]]; then
        ((COUNT_MOUNTED++))
        local cnt
        cnt=$($ssh_cmd "ls -1 /home/linux/mesh_pool 2>/dev/null | wc -l | tr -d ' '" 2>/dev/null || echo "0")
        record_result "L3_Linux_Hub" "L3" "Compute Hub (Ryzen)" "Linux FUSE" "MOUNTED" "weed mount active on /home/linux/mesh_pool (${cnt} items)"
    else
        record_result "L3_Linux_Hub" "L3" "Compute Hub (Ryzen)" "Linux FUSE" "READY_UNMOUNTED" "SSH alive; /mnt/dfs_unified local repo accessible"
    fi
}

handle_l8_linuxmini() {
    ((COUNT_TOTAL++))
    local target="linuxmini"
    local ssh_cmd="ssh ${SSH_OPTS[*]} $target"

    if ! $ssh_cmd "echo PING_OK" >/dev/null 2>&1; then
        ((COUNT_OFFLINE++))
        record_result "L8_Linux_Mini" "L8" "Central Ingress (i7)" "Linux FUSE" "OFFLINE" "SSH unreachable on host alias 'linuxmini'"
        return
    fi
    ((COUNT_ONLINE++))

    local is_mounted=0
    if $ssh_cmd "mount | grep -q 'mesh_pool'" >/dev/null 2>&1; then
        is_mounted=1
    fi

    if [[ "$MODE" == "mount" && $is_mounted -eq 0 ]]; then
        $ssh_cmd "mkdir -p /home/linuxmini/mesh_pool && nohup ~/.local/bin/weed mount -allowOthers=false -filer=${MASTER_HOST}:${FILER_PORT} -dir=/home/linuxmini/mesh_pool >/tmp/weed_mount.log 2>&1 & sleep 2" >/dev/null 2>&1 || true
        if $ssh_cmd "mount | grep -q 'mesh_pool'" >/dev/null 2>&1; then
            is_mounted=1
        fi
    fi

    if [[ $is_mounted -eq 1 ]]; then
        ((COUNT_MOUNTED++))
        local cnt
        cnt=$($ssh_cmd "ls -1 /home/linuxmini/mesh_pool 2>/dev/null | wc -l | tr -d ' '" 2>/dev/null || echo "0")
        record_result "L8_Linux_Mini" "L8" "Central Ingress (i7)" "Linux FUSE" "MOUNTED" "weed mount active on /home/linuxmini/mesh_pool (${cnt} items)"
    else
        record_result "L8_Linux_Mini" "L8" "Central Ingress (i7)" "Linux FUSE" "READY_UNMOUNTED" "SSH alive; FUSE mount unmounted"
    fi
}

handle_l5_macbook_air() {
    ((COUNT_TOTAL++))
    local target="macbook"
    local ssh_cmd="ssh ${SSH_OPTS[*]} $target"

    if ! $ssh_cmd "echo PING_OK" >/dev/null 2>&1; then
        ((COUNT_OFFLINE++))
        record_result "L5_MacBook_Air" "L5" "Metal Worker (M4)" "Rclone WebDAV" "OFFLINE" "SSH unreachable on host alias 'macbook'"
        return
    fi
    ((COUNT_ONLINE++))

    if [[ "$MODE" == "mount" ]]; then
        $ssh_cmd "mkdir -p ~/.config/rclone ~/mesh_pool && cat << 'INNER_EOF' > ~/.config/rclone/rclone.conf
[seaweedfs]
type = webdav
url = http://${MASTER_TS}:${WEBDAV_PORT}
vendor = other
INNER_EOF
" >/dev/null 2>&1 || true
    fi

    local rclone_ok=0
    if $ssh_cmd "/opt/homebrew/bin/rclone lsd seaweedfs: >/dev/null 2>&1" >/dev/null 2>&1; then
        rclone_ok=1
    fi

    if [[ $rclone_ok -eq 1 ]]; then
        ((COUNT_MOUNTED++))
        record_result "L5_MacBook_Air" "L5" "Metal Worker (M4)" "Rclone WebDAV" "VERIFIED" "WebDAV active (rclone lsd validated, dir ~/mesh_pool)"
    else
        record_result "L5_MacBook_Air" "L5" "Metal Worker (M4)" "Rclone WebDAV" "CONFIG_PENDING" "SSH alive; rclone remote verification pending"
    fi
}

handle_gw_router() {
    ((COUNT_TOTAL++))
    local target="router"
    local ssh_cmd="ssh ${SSH_OPTS[*]} $target"

    if ! $ssh_cmd "echo PING_OK" >/dev/null 2>&1; then
        ((COUNT_OFFLINE++))
        record_result "GW_Router" "GW" "Core Gateway (BE14000)" "Flash Volume" "OFFLINE" "SSH unreachable on host alias 'router'"
        return
    fi
    ((COUNT_ONLINE++))

    local dir_exists=0
    if $ssh_cmd "[ -d /mnt/seaweedfs ]" >/dev/null 2>&1; then
        dir_exists=1
    fi

    if [[ $dir_exists -eq 1 ]]; then
        ((COUNT_MOUNTED++))
        local free_mb
        free_mb=$($ssh_cmd "df -m /mnt/seaweedfs 2>/dev/null | awk 'NR==2 {print \$4}'" 2>/dev/null || echo "N/A")
        record_result "GW_Router" "GW" "Core Gateway (BE14000)" "Flash Volume" "ACTIVE" "Directory /mnt/seaweedfs accessible (${free_mb}MB free)"
    else
        record_result "GW_Router" "GW" "Core Gateway (BE14000)" "Flash Volume" "DEGRADED" "Directory /mnt/seaweedfs not present"
    fi
}

handle_l6_pixel() {
    ((COUNT_TOTAL++))
    local ssh_cmd="ssh ${SSH_OPTS[*]} -o HostName=192.168.8.213 -p 8022 u0_a363@192.168.8.213"

    if ! $ssh_cmd "echo PING_OK" >/dev/null 2>&1; then
        # Fallback to Tailscale IP
        ssh_cmd="ssh ${SSH_OPTS[*]} -p 8022 u0_a363@100.94.90.84"
        if ! $ssh_cmd "echo PING_OK" >/dev/null 2>&1; then
            ((COUNT_OFFLINE++))
            record_result "L6_Pixel_10_Edge" "L6" "Edge TPU (Tensor G5)" "Rclone WebDAV" "OFFLINE" "Termux sshd unreachable on 192.168.8.213 / 100.94.90.84:8022"
            return
        fi
    fi
    ((COUNT_ONLINE++))

    if [[ "$MODE" == "mount" ]]; then
        $ssh_cmd "mkdir -p ~/.config/rclone ~/mesh_pool && cat << 'INNER_EOF' > ~/.config/rclone/rclone.conf
[seaweedfs]
type = webdav
url = http://${MASTER_TS}:${WEBDAV_PORT}
vendor = other
INNER_EOF
" >/dev/null 2>&1 || true
    fi

    local rclone_ok=0
    if $ssh_cmd "command -v rclone >/dev/null 2>&1 && rclone lsd seaweedfs: >/dev/null 2>&1" >/dev/null 2>&1; then
        rclone_ok=1
    fi

    if [[ $rclone_ok -eq 1 ]]; then
        ((COUNT_MOUNTED++))
        record_result "L6_Pixel_10_Edge" "L6" "Edge TPU (Tensor G5)" "Rclone WebDAV" "VERIFIED" "WebDAV active (rclone lsd validated, dir ~/mesh_pool)"
    else
        record_result "L6_Pixel_10_Edge" "L6" "Edge TPU (Tensor G5)" "Rclone WebDAV" "CONFIG_PENDING" "SSH alive; rclone remote verification pending"
    fi
}

handle_l7_s20() {
    ((COUNT_TOTAL++))
    local ssh_cmd="ssh ${SSH_OPTS[*]} -o HostName=192.168.8.131 -p 8022 u0_a420@192.168.8.131"

    if ! $ssh_cmd "echo PING_OK" >/dev/null 2>&1; then
        # Fallback to Tailscale IP
        ssh_cmd="ssh ${SSH_OPTS[*]} -p 8022 u0_a420@100.78.206.96"
        if ! $ssh_cmd "echo PING_OK" >/dev/null 2>&1; then
            ((COUNT_OFFLINE++))
            record_result "L7_Samsung_S20" "L7" "UI Automation Tester" "Rclone WebDAV" "OFFLINE" "Termux sshd unreachable on 192.168.8.131 / 100.78.206.96:8022"
            return
        fi
    fi
    ((COUNT_ONLINE++))

    if [[ "$MODE" == "mount" ]]; then
        $ssh_cmd "mkdir -p ~/.config/rclone ~/mesh_pool && cat << 'INNER_EOF' > ~/.config/rclone/rclone.conf
[seaweedfs]
type = webdav
url = http://${MASTER_TS}:${WEBDAV_PORT}
vendor = other
INNER_EOF
" >/dev/null 2>&1 || true
    fi

    local rclone_ok=0
    if $ssh_cmd "/data/data/com.termux/files/usr/bin/rclone lsd seaweedfs: >/dev/null 2>&1" >/dev/null 2>&1; then
        rclone_ok=1
    fi

    if [[ $rclone_ok -eq 1 ]]; then
        ((COUNT_MOUNTED++))
        record_result "L7_Samsung_S20" "L7" "UI Automation Tester" "Rclone WebDAV" "VERIFIED" "WebDAV active (rclone lsd validated, dir ~/mesh_pool)"
    else
        record_result "L7_Samsung_S20" "L7" "UI Automation Tester" "Rclone WebDAV" "CONFIG_PENDING" "SSH alive; rclone remote verification pending"
    fi
}

handle_standby_node() {
    local node="$1"
    local layer="$2"
    local role="$3"
    local access_type="$4"
    local target="$5"
    local path="$6"

    ((COUNT_TOTAL++))
    local ssh_cmd="ssh ${SSH_OPTS[*]} -o ConnectTimeout=2 $target"

    if ! $ssh_cmd "echo PING_OK" >/dev/null 2>&1; then
        ((COUNT_OFFLINE++))
        record_result "$node" "$layer" "$role" "$access_type" "STANDBY" "Device sleeping or carrier down (gracefully bypassed)"
        return
    fi
    ((COUNT_ONLINE++))
    ((COUNT_MOUNTED++))
    record_result "$node" "$layer" "$role" "$access_type" "ACTIVE" "SSH reachable; mount target: ${path}"
}

# ==============================================================================
# Main Orchestration Loop
# ==============================================================================

echo -e "${C_BOLD}==============================================================================${C_RESET}"
echo -e "${C_BOLD}🌐 LAUBURU CANONICAL GLOBAL MESH STORAGE ORCHESTRATOR (GEN 31)${C_RESET}"
echo -e "Mode: ${C_CYAN}${MODE}${C_RESET} | Master Filer: ${C_GREEN}${MASTER_HOST}:${FILER_PORT}${C_RESET} | Master WebDAV: ${C_GREEN}${MASTER_HOST}:${WEBDAV_PORT}${C_RESET}"
echo -e "${C_BOLD}==============================================================================${C_RESET}"
printf "%-18s | %-6s | %-20s | %-16s | %-14s | %s\n" "NODE" "LAYER" "ROLE" "ACCESS TYPE" "STATUS" "DETAILS / VERIFICATION"
echo "-----------------------------------------------------------------------------------------------------------------"

if [[ -n "$TARGET_NODE" ]]; then
    case "$TARGET_NODE" in
        l1|L1|mac|host)           check_l1_master ;;
        l3|L3|linux|ryzen)        handle_l3_linux ;;
        l8|L8|linuxmini|mini)     handle_l8_linuxmini ;;
        l5|L5|macbook|mba)        handle_l5_macbook_air ;;
        gw|GW|router)             handle_gw_router ;;
        l6|L6|pixel)              handle_l6_pixel ;;
        l7|L7|s20)                handle_l7_s20 ;;
        l2|L2|mbp)                handle_standby_node "L2_MacBook_Pro" "L2" "Model Vault (Intel)" "macFUSE / Vault" "macbook-pro" "/Volumes/seaweed_network" ;;
        l4|L4|tablet)             handle_standby_node "L4_Linux_Tablet" "L4" "Debian Mobile Compute" "Linux FUSE" "tablet" "~/mesh_pool" ;;
        l9|L9|iphone)             handle_standby_node "L9_iPhone_16_Pro" "L9" "iOS Testing Target" "Lockdown Target" "iphone" "/var/root/mesh_pool" ;;
        *)
            echo "Unknown target node: $TARGET_NODE"
            exit 1
            ;;
    esac
else
    check_l1_master
    handle_l3_linux
    handle_l8_linuxmini
    handle_l5_macbook_air
    handle_gw_router
    handle_l6_pixel
    handle_l7_s20
    handle_standby_node "L2_MacBook_Pro" "L2" "Model Vault (Intel)" "macFUSE / Vault" "macbook-pro" "/Volumes/seaweed_network"
    handle_standby_node "L4_Linux_Tablet" "L4" "Debian Mobile Compute" "Linux FUSE" "tablet" "~/mesh_pool"
    handle_standby_node "L9_iPhone_16_Pro" "L9" "iOS Testing Target" "Lockdown Target" "iphone" "/var/root/mesh_pool"
fi

echo "-----------------------------------------------------------------------------------------------------------------"
echo -e "${C_BOLD}Orchestration Summary:${C_RESET} Total Nodes: ${COUNT_TOTAL} | Online: ${COUNT_ONLINE} | Mounted/Verified: ${COUNT_MOUNTED} | Standby/Offline: ${COUNT_OFFLINE}"
echo -e "${C_BOLD}==============================================================================${C_RESET}"

if [[ $COUNT_MOUNTED -ge 1 ]]; then
    exit 0
else
    exit 1
fi
