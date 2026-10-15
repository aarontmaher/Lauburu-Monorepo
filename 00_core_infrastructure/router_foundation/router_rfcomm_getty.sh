#!/usr/bin/env bash
# ==============================================================================
# Lauburu Mesh - Router Headless Recovery Getty on /dev/rfcomm0
# Subsystem: 00_core_infrastructure/router_foundation/router_rfcomm_getty.sh
# Target: GL-BE14000 OpenWrt Sovereign Gateway (192.168.8.1)
# ==============================================================================
# Configures /usr/bin/rfcomm watch 0 1 /usr/libexec/login.sh on the router so
# incoming RFCOMM connections on channel 1 spawn a headless serial login shell.
# Serial fallback: /sbin/getty -L 115200 rfcomm0 vt100
# Segregation: RFCOMM channel 1 is strictly isolated from BLE data port 9002.
# ==============================================================================

set -euo pipefail

ROUTER_HOST="${ROUTER_HOST:-192.168.8.1}"
ROUTER_USER="${ROUTER_USER:-root}"
SSH_OPTS="-o ConnectTimeout=3 -o BatchMode=yes -o StrictHostKeyChecking=no"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INIT_FILE="$SCRIPT_DIR/router_rfcomm_getty.init"

RFCOMM_BIN="/usr/bin/rfcomm"
LOGIN_SCRIPT="/usr/libexec/login.sh"
GETTY_BIN="/sbin/getty"
DEVICE_INDEX="0"
DEVICE_NODE="/dev/rfcomm0"
DEVICE_NAME="rfcomm0"
CHANNEL="1"
BAUD_RATE="115200"
TERM_TYPE="vt100"
BLE_DATA_PORT="9002"

CANONICAL_WATCH_CMD="$RFCOMM_BIN watch $DEVICE_INDEX $CHANNEL $LOGIN_SCRIPT"
SERIAL_GETTY_CMD="$RFCOMM_BIN watch 0 1 /sbin/getty -L 115200 rfcomm0 vt100"

log_info() {
    echo -e "\033[1;34m[INFO]\033[0m $1"
}

log_success() {
    echo -e "\033[1;32m[SUCCESS]\033[0m $1"
}

log_error() {
    echo -e "\033[1;31m[ERROR]\033[0m $1"
}

# Run locally on the router if executed in OpenWrt environment
run_on_router() {
    local action="${1:-status}"
    case "$action" in
        start|watch)
            log_info "Starting RFCOMM headless recovery watcher on $DEVICE_NODE (Channel $CHANNEL)..."
            killall rfcomm 2>/dev/null || true
            $RFCOMM_BIN release $DEVICE_INDEX 2>/dev/null || true
            if [ -x "$LOGIN_SCRIPT" ]; then
                log_info "Executing canonical command: $CANONICAL_WATCH_CMD"
                exec $CANONICAL_WATCH_CMD
            elif [ -x "$GETTY_BIN" ]; then
                log_info "Executing serial getty command: $SERIAL_GETTY_CMD"
                exec $RFCOMM_BIN watch $DEVICE_INDEX $CHANNEL $GETTY_BIN -L $BAUD_RATE $DEVICE_NAME $TERM_TYPE
            else
                log_info "Fallback to /bin/login on $DEVICE_NODE"
                exec $RFCOMM_BIN watch $DEVICE_INDEX $CHANNEL /bin/login
            fi
            ;;
        stop)
            log_info "Stopping RFCOMM watcher..."
            killall rfcomm 2>/dev/null || true
            $RFCOMM_BIN release $DEVICE_INDEX 2>/dev/null || true
            log_success "RFCOMM watcher stopped."
            ;;
        status)
            if ps | grep -v grep | grep -q "rfcomm watch"; then
                log_success "RFCOMM watcher is active: $(ps | grep -v grep | grep 'rfcomm watch')"
                exit 0
            else
                log_info "RFCOMM watcher is not running."
                exit 1
            fi
            ;;
        *)
            echo "Usage: $0 {start|stop|status|watch}"
            exit 1
            ;;
    esac
}

# Remote management via SSH to router from host
deploy_to_router() {
    log_info "Deploying router_rfcomm_getty to $ROUTER_USER@$ROUTER_HOST..."
    if [ ! -f "$INIT_FILE" ]; then
        log_error "Init file not found: $INIT_FILE"
        exit 1
    fi

    # 1. Transfer init script
    log_info "Copying init script to /etc/init.d/router_rfcomm_getty..."
    ssh $SSH_OPTS "$ROUTER_USER@$ROUTER_HOST" "cat > /etc/init.d/router_rfcomm_getty" < "$INIT_FILE"
    ssh $SSH_OPTS "$ROUTER_USER@$ROUTER_HOST" "chmod 755 /etc/init.d/router_rfcomm_getty"

    # 2. Enable and restart service
    log_info "Enabling and starting service via procd..."
    ssh $SSH_OPTS "$ROUTER_USER@$ROUTER_HOST" "
        /etc/init.d/router_rfcomm_getty enable
        /etc/init.d/router_rfcomm_getty restart
    "

    # 3. Verify process
    log_info "Verifying RFCOMM getty process on router..."
    sleep 1
    ssh $SSH_OPTS "$ROUTER_USER@$ROUTER_HOST" "
        if ps | grep -v grep | grep -q 'rfcomm watch'; then
            echo 'SUCCESS: rfcomm watch is running on router:'
            ps | grep -v grep | grep 'rfcomm watch'
            exit 0
        else
            echo 'ERROR: rfcomm watch is not running on router'
            exit 1
        fi
    "
    log_success "router_rfcomm_getty successfully deployed and running on GL-BE14000!"
}

status_remote() {
    log_info "Querying RFCOMM watcher status on $ROUTER_USER@$ROUTER_HOST..."
    ssh $SSH_OPTS "$ROUTER_USER@$ROUTER_HOST" "
        if ps | grep -v grep | grep -q 'rfcomm watch'; then
            echo 'ONLINE: rfcomm watch active'
            ps | grep -v grep | grep 'rfcomm watch'
            exit 0
        else
            echo 'OFFLINE: rfcomm watch not running'
            exit 1
        fi
    "
}

start_remote() {
    log_info "Starting router_rfcomm_getty on $ROUTER_USER@$ROUTER_HOST..."
    ssh $SSH_OPTS "$ROUTER_USER@$ROUTER_HOST" "/etc/init.d/router_rfcomm_getty start"
}

stop_remote() {
    log_info "Stopping router_rfcomm_getty on $ROUTER_USER@$ROUTER_HOST..."
    ssh $SSH_OPTS "$ROUTER_USER@$ROUTER_HOST" "/etc/init.d/router_rfcomm_getty stop"
}

main() {
    # Check if running natively on OpenWrt Linux router
    if [ -f /etc/openwrt_release ] || [ -f /etc/openwrt_version ]; then
        run_on_router "${1:-status}"
        return
    fi

    # Running on management host
    local cmd="${1:---status}"
    case "$cmd" in
        --deploy|deploy)
            deploy_to_router
            ;;
        --status|status)
            status_remote
            ;;
        --start|start)
            start_remote
            ;;
        --stop|stop)
            stop_remote
            ;;
        --restart|restart)
            stop_remote || true
            start_remote
            ;;
        --help|-h)
            echo "Usage: $0 [--deploy|--status|--start|--stop|--restart]"
            echo "  --deploy   Deploy init script to router and start procd service"
            echo "  --status   Check status of rfcomm watch on router"
            echo "  --start    Start router_rfcomm_getty on router"
            echo "  --stop     Stop router_rfcomm_getty on router"
            echo "  --restart  Restart router_rfcomm_getty on router"
            ;;
        *)
            status_remote
            ;;
    esac
}

main "$@"
