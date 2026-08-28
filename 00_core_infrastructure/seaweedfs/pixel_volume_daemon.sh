#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# LAUBURU SEAWEEDFS PIXEL 10 PRO XL VOLUME DAEMON (Termux & Android 15)
# Subsystem: 00_core_infrastructure/seaweedfs
# Hardware: Google Pixel 10 Pro XL (Tensor G5, 16GB RAM, Android 15)
# Mesh Layer: Layer 6 (Pixel 10 Pro XL)
# Tailscale IP: 100.73.38.87
# Target Master: Mac Mini M4 Pro Host (100.119.199.76:9333)
# Storage Partition: 500GB partition at /data/data/com.termux/files/home/storage/shared/seaweedfs
# ==============================================================================

# Ensure bash execution environment with POSIX fallback
if [ -z "${BASH_VERSION:-}" ]; then
    if [ -x "/data/data/com.termux/files/usr/bin/bash" ]; then
        exec /data/data/com.termux/files/usr/bin/bash "$0" "$@"
    elif [ -x "/bin/bash" ]; then
        exec /bin/bash "$0" "$@"
    elif command -v bash >/dev/null 2>&1; then
        exec bash "$0" "$@"
    fi
fi

set -u

# --- Color Formatting Helpers ---
RED="\033[0;31m"
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
BLUE="\033[0;34m"
CYAN="\033[0;36m"
BOLD="\033[1m"
NC="\033[0m" # No Color

# --- Ensure Termux and System PATHs are available ---
export PATH="/data/data/com.termux/files/usr/bin:/data/data/com.termux/files/usr/bin/applets:${HOME:-/data/data/com.termux/files/home}/bin:/usr/local/bin:/usr/bin:/bin:${PATH:-}"

# --- Environment & Default Configurations ---
DEFAULT_STORAGE_DIR="/data/data/com.termux/files/home/storage/shared/seaweedfs"
DEFAULT_MASTER="100.119.199.76:9333"
DEFAULT_NODE_IP="100.73.38.87"
DEFAULT_BIND_IP="0.0.0.0"
DEFAULT_VOLUME_PORT=8080
DEFAULT_MAX_VOLUMES=500
DEFAULT_MIN_FREE_SPACE=5
DEFAULT_DATACENTER="Android"
DEFAULT_RACK="Pixel10ProXL"
DEFAULT_INDEX="memory"

STORAGE_DIR="${DFS_VOLUME_DIR:-$DEFAULT_STORAGE_DIR}"
MASTER_SERVER="${DFS_MASTER:-${DFS_MASTER_PEERS:-$DEFAULT_MASTER}}"
NODE_IP="${NODE_IP:-$DEFAULT_NODE_IP}"
BIND_IP="${BIND_IP:-$DEFAULT_BIND_IP}"
VOLUME_PORT="${VOLUME_PORT:-$DEFAULT_VOLUME_PORT}"
VOLUME_PORT_GRPC="${VOLUME_PORT_GRPC:-$((VOLUME_PORT + 10000))}"
PUBLIC_URL="${PUBLIC_URL:-${NODE_IP}:${VOLUME_PORT}}"
MAX_VOLUMES="${MAX_VOLUMES:-$DEFAULT_MAX_VOLUMES}"
MIN_FREE_SPACE="${MIN_FREE_SPACE_PERCENT:-$DEFAULT_MIN_FREE_SPACE}"
DATA_CENTER="${DATA_CENTER:-$DEFAULT_DATACENTER}"
RACK="${RACK:-$DEFAULT_RACK}"
INDEX_TYPE="${INDEX_TYPE:-$DEFAULT_INDEX}"

PID_FILE="${DFS_PID_FILE:-${HOME:-/tmp}/.seaweed_pixel_volume.pid}"
LOG_FILE="${DFS_LOG_FILE:-${HOME:-/tmp}/seaweed_volume.log}"

# Action Mode Flags
ACTION="start"
IS_DAEMON=false
IS_FOREGROUND=false

# --- Logging Helpers ---
log_info() {
    echo -e "${CYAN}$(date -u +'%Y-%m-%dT%H:%M:%SZ') [PIXEL_VOLUME] [INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}$(date -u +'%Y-%m-%dT%H:%M:%SZ') [PIXEL_VOLUME] [SUCCESS]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}$(date -u +'%Y-%m-%dT%H:%M:%SZ') [PIXEL_VOLUME] [WARN]${NC} $*"
}

log_error() {
    echo -e "${RED}$(date -u +'%Y-%m-%dT%H:%M:%SZ') [PIXEL_VOLUME] [ERROR]${NC} $*" >&2
}

# --- Usage & Help Display ---
show_help() {
    cat << HELP_EOF
Usage: $(basename "$0") [ACTION] [OPTIONS]

Termux-compatible SeaweedFS Volume Daemon for Google Pixel 10 Pro XL (Layer 6).
Manages background volume brick serving over Tailscale mesh to Mac Mini Master.

Actions:
  start                      Start daemon in background (default)
  stop, --stop               Stop running daemon and release wake lock
  status, --status           Check daemon process status and HTTP health
  restart, --restart         Restart daemon
  foreground, -f             Run directly in foreground
  test, --test               Execute pre-flight diagnostics without starting daemon
  help, -h, --help           Display this help message and exit

Options:
  -d, --daemon               Run as detached background daemon
  -dir, --dir PATH           Storage directory path (Default: $DEFAULT_STORAGE_DIR)
  -mserver, --mserver ADDR   SeaweedFS Master server address (Default: $DEFAULT_MASTER)
  -ip, --ip ADDR             Tailscale IP advertised by this node (Default: $DEFAULT_NODE_IP)
  -port, --port PORT         HTTP volume server port (Default: $DEFAULT_VOLUME_PORT)
  -port.grpc PORT            gRPC companion port (Default: 18080)
  -max, --max NUM            Maximum volume count (Default: $DEFAULT_MAX_VOLUMES)
  --pid-file PATH            Path to PID tracking file
  --log-file PATH            Path to stdout/stderr log file

Environment Variables:
  DFS_VOLUME_DIR             Override storage partition directory
  DFS_MASTER                 Override SeaweedFS Master endpoint
  NODE_IP                    Override node Tailscale IP address
  VOLUME_PORT                Override HTTP volume port
  MAX_VOLUMES                Override max volume count allocation
  DFS_PID_FILE               Override PID lock file path
  DFS_LOG_FILE               Override log file path

Examples:
  $(basename "$0") start
  $(basename "$0") --status
  $(basename "$0") --test
  $(basename "$0") stop
HELP_EOF
}

# --- Locate SeaweedFS Binary ---
find_weed_binary() {
    local candidates=(
        "${PREFIX:-/data/data/com.termux/files/usr}/bin/weed"
        "${HOME:-/data/data/com.termux/files/home}/bin/weed"
        "/data/data/com.termux/files/usr/bin/weed"
        "/data/data/com.termux/files/usr/local/bin/weed"
        "/usr/local/bin/weed"
        "/usr/bin/weed"
        "/opt/homebrew/bin/weed"
    )

    for bin in "${candidates[@]}"; do
        if [ -x "$bin" ]; then
            echo "$bin"
            return 0
        fi
    done

    if command -v weed >/dev/null 2>&1; then
        command -v weed
        return 0
    fi

    echo ""
    return 1
}

# --- Wake-Lock Management for Android Keepalive ---
acquire_wake_lock() {
    if command -v termux-wake-lock >/dev/null 2>&1; then
        log_info "Acquiring Android Termux wake-lock (CPU keepalive)..."
        termux-wake-lock 2>/dev/null || log_warn "termux-wake-lock returned non-zero; continuing."
    else
        log_warn "termux-wake-lock utility not found in PATH. Proceeding without Termux API wake-lock."
    fi
}

release_wake_lock() {
    if command -v termux-wake-unlock >/dev/null 2>&1; then
        log_info "Releasing Android Termux wake-lock..."
        termux-wake-unlock 2>/dev/null || true
    fi
}

# --- Storage Directory Validation ---
validate_storage_directory() {
    local target_dir="$1"
    
    if [ ! -d "$target_dir" ]; then
        log_info "Creating SeaweedFS volume storage directory: $target_dir"
        if ! mkdir -p "$target_dir" 2>/dev/null; then
            log_error "Failed to create storage directory: $target_dir"
            log_error "Android storage permission may not be granted."
            log_error "Run 'termux-setup-storage' in Termux and grant storage access in Android settings."
            return 1
        fi
    fi

    local test_file="${target_dir}/.seaweed_write_test_$$"
    if ! touch "$test_file" 2>/dev/null; then
        log_error "Storage directory $target_dir is not writable!"
        log_error "Please execute 'termux-setup-storage' to grant shared storage permissions."
        return 1
    fi
    rm -f "$test_file" 2>/dev/null || true

    return 0
}

# --- PID & Process Helpers ---
get_running_pid() {
    if [ -f "$PID_FILE" ]; then
        local pid
        pid="$(cat "$PID_FILE" 2>/dev/null || echo "")"
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            echo "$pid"
            return 0
        fi
    fi
    echo ""
    return 1
}

# --- Clean Cleanup & Signal Trapping ---
cleanup() {
    local exit_code=$?
    log_info "Caught exit/termination signal. Cleaning up resources..."
    
    if [ -n "${WEED_CHILD_PID:-}" ] && kill -0 "$WEED_CHILD_PID" 2>/dev/null; then
        log_info "Terminating child weed volume process (PID: $WEED_CHILD_PID)..."
        kill -TERM "$WEED_CHILD_PID" 2>/dev/null || true
        wait "$WEED_CHILD_PID" 2>/dev/null || true
    fi

    if [ -f "$PID_FILE" ]; then
        rm -f "$PID_FILE" 2>/dev/null || true
    fi

    release_wake_lock
    exit "$exit_code"
}

# --- Pre-Flight Self-Test Mode ---
run_preflight_test() {
    echo -e "${BOLD}${BLUE}================================================================${NC}"
    echo -e "${BOLD}${BLUE}   LAUBURU SEAWEEDFS PIXEL VOLUME DAEMON PRE-FLIGHT TEST        ${NC}"
    echo -e "${BOLD}${BLUE}================================================================${NC}"
    echo "Host Node:         Pixel 10 Pro XL (Layer 6)"
    echo "Advertised IP:     $NODE_IP"
    echo "Target Master:     $MASTER_SERVER"
    echo "Storage Directory: $STORAGE_DIR"
    echo "Volume Port:       $VOLUME_PORT (gRPC: $VOLUME_PORT_GRPC)"
    echo "Max Volumes:       $MAX_VOLUMES"
    echo "PID File:          $PID_FILE"
    echo "Log File:          $LOG_FILE"
    echo "----------------------------------------------------------------"

    local errors=0
    local warnings=0

    # 1. Check weed binary
    log_info "[1/5] Checking SeaweedFS 'weed' binary..."
    local weed_bin
    weed_bin="$(find_weed_binary || true)"
    if [ -n "$weed_bin" ]; then
        log_success "Found SeaweedFS executable: $weed_bin"
    else
        log_warn "SeaweedFS 'weed' binary not found in standard paths. (Install via Termux or package manager)."
        warnings=$((warnings + 1))
    fi

    # 2. Check wake-lock tools
    log_info "[2/5] Checking Termux API utilities..."
    if command -v termux-wake-lock >/dev/null 2>&1; then
        log_success "Termux wake-lock support detected."
    else
        log_warn "termux-wake-lock utility missing. (Install via 'pkg install termux-api')."
        warnings=$((warnings + 1))
    fi

    # 3. Check storage directory
    log_info "[3/5] Validating volume partition access ($STORAGE_DIR)..."
    if validate_storage_directory "$STORAGE_DIR"; then
        log_success "Storage partition writable and ready (500GB target pool)."
    else
        log_error "Storage partition check failed."
        errors=$((errors + 1))
    fi

    # 4. Check Tailscale & Network connectivity to Master
    log_info "[4/5] Testing Master server reachability ($MASTER_SERVER)..."
    local master_ip="${MASTER_SERVER%%:*}"
    local master_port="${MASTER_SERVER##*:}"
    
    if command -v curl >/dev/null 2>&1; then
        if curl -s --connect-timeout 2 --max-time 3 "http://${MASTER_SERVER}/cluster/status" >/dev/null 2>&1 || \
           curl -s --connect-timeout 2 --max-time 3 -I "http://${MASTER_SERVER}/" >/dev/null 2>&1; then
            log_success "SeaweedFS Master is reachable at http://${MASTER_SERVER}."
        else
            log_warn "Master http://${MASTER_SERVER} currently unreachable or offline. Volume daemon will retry over Tailscale."
            warnings=$((warnings + 1))
        fi
    elif command -v nc >/dev/null 2>&1; then
        if nc -z -w 2 "$master_ip" "$master_port" 2>/dev/null; then
            log_success "Master TCP port $master_port reachable on $master_ip."
        else
            log_warn "Master port $master_port on $master_ip unreachable."
            warnings=$((warnings + 1))
        fi
    else
        log_warn "Neither curl nor nc available for network reachability testing."
        warnings=$((warnings + 1))
    fi

    # 5. Check active process / PID status
    log_info "[5/5] Checking daemon lock state..."
    local active_pid
    active_pid="$(get_running_pid || true)"
    if [ -n "$active_pid" ]; then
        log_info "Volume daemon is currently running (PID: $active_pid)."
    else
        log_success "No conflicting daemon instance detected. System ready to start."
    fi

    echo "----------------------------------------------------------------"
    if [ "$errors" -eq 0 ]; then
        log_success "Pre-flight test completed successfully ($warnings warnings, $errors errors)."
        return 0
    else
        log_error "Pre-flight test completed with $errors fatal error(s)."
        return 1
    fi
}

# --- Daemon Status Query ---
check_status() {
    local running_pid
    running_pid="$(get_running_pid || true)"

    if [ -n "$running_pid" ]; then
        log_success "SeaweedFS Pixel Volume Daemon is RUNNING (PID: $running_pid)."
        echo "Storage Dir:  $STORAGE_DIR"
        echo "Master:       $MASTER_SERVER"
        echo "Advertised:   http://${PUBLIC_URL}"
        echo "PID File:     $PID_FILE"
        echo "Log File:     $LOG_FILE"

        if command -v curl >/dev/null 2>&1; then
            echo -e "\n--- HTTP Status Query (http://127.0.0.1:${VOLUME_PORT}/status) ---"
            curl -s --connect-timeout 2 --max-time 3 "http://127.0.0.1:${VOLUME_PORT}/status" 2>/dev/null || \
                log_warn "Local HTTP status endpoint not responding."
            echo ""
        fi
        return 0
    else
        log_info "SeaweedFS Pixel Volume Daemon is STOPPED."
        if [ -f "$PID_FILE" ]; then
            log_warn "Stale PID file detected ($PID_FILE). Process is not active."
        fi
        return 3
    fi
}

# --- Daemon Stop Routine ---
stop_daemon() {
    local running_pid
    running_pid="$(get_running_pid || true)"

    if [ -z "$running_pid" ]; then
        log_info "No active SeaweedFS Volume Daemon running."
        if [ -f "$PID_FILE" ]; then
            rm -f "$PID_FILE" 2>/dev/null || true
        fi
        release_wake_lock
        return 0
    fi

    log_info "Stopping SeaweedFS Pixel Volume Daemon (PID: $running_pid)..."
    kill -TERM "$running_pid" 2>/dev/null || true

    local count=0
    while kill -0 "$running_pid" 2>/dev/null; do
        sleep 0.5
        count=$((count + 1))
        if [ $count -ge 10 ]; then
            log_warn "Process did not terminate gracefully within 5s. Sending SIGKILL..."
            kill -9 "$running_pid" 2>/dev/null || true
            break
        fi
    done

    rm -f "$PID_FILE" 2>/dev/null || true
    release_wake_lock
    log_success "SeaweedFS Pixel Volume Daemon stopped successfully."
    return 0
}

# --- Daemon Start Routine ---
start_daemon() {
    local running_pid
    running_pid="$(get_running_pid || true)"

    if [ -n "$running_pid" ]; then
        log_warn "SeaweedFS Pixel Volume Daemon is already running (PID: $running_pid). Exiting."
        return 0
    fi

    # 1. Locate weed binary
    local weed_bin
    weed_bin="$(find_weed_binary || true)"
    if [ -z "$weed_bin" ]; then
        log_error "SeaweedFS executable 'weed' not found in PATH or standard Termux locations."
        log_error "Please compile or copy 'weed' to \$PREFIX/bin/weed or \$HOME/bin/weed."
        return 1
    fi

    # 2. Validate storage partition
    if ! validate_storage_directory "$STORAGE_DIR"; then
        log_error "Storage directory validation failed. Cannot start volume daemon."
        return 1
    fi

    # 3. Acquire wake lock
    acquire_wake_lock

    # 4. Prepare command arguments
    local cmd=(
        "$weed_bin" volume
        "-dir=${STORAGE_DIR}"
        "-mserver=${MASTER_SERVER}"
        "-ip=${NODE_IP}"
        "-ip.bind=${BIND_IP}"
        "-port=${VOLUME_PORT}"
        "-port.grpc=${VOLUME_PORT_GRPC}"
        "-publicUrl=${PUBLIC_URL}"
        "-max=${MAX_VOLUMES}"
        "-minFreeSpacePercent=${MIN_FREE_SPACE}"
        "-dataCenter=${DATA_CENTER}"
        "-rack=${RACK}"
        "-index=${INDEX_TYPE}"
    )

    log_info "Launching SeaweedFS Volume Server:"
    log_info "Command: ${cmd[*]}"

    # 5. Handle foreground vs daemon mode
    if [ "$IS_FOREGROUND" = true ]; then
        trap cleanup SIGINT SIGTERM SIGHUP EXIT
        echo "$$" > "$PID_FILE"
        exec "${cmd[@]}"
    else
        mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null || true
        mkdir -p "$(dirname "$PID_FILE")" 2>/dev/null || true

        nohup "${cmd[@]}" >> "$LOG_FILE" 2>&1 &
        local spawned_pid=$!
        echo "$spawned_pid" > "$PID_FILE"

        sleep 1
        if kill -0 "$spawned_pid" 2>/dev/null; then
            log_success "SeaweedFS Pixel Volume Daemon started in background (PID: $spawned_pid)."
            log_info "Logs streaming to: $LOG_FILE"
            return 0
        else
            log_error "SeaweedFS Volume Daemon failed to stay alive after spawn."
            log_error "Inspect logs at $LOG_FILE for details."
            rm -f "$PID_FILE" 2>/dev/null || true
            release_wake_lock
            return 1
        fi
    fi
}

# --- CLI Argument Parsing ---
parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            start)
                ACTION="start"
                shift
                ;;
            stop|--stop)
                ACTION="stop"
                shift
                ;;
            status|--status)
                ACTION="status"
                shift
                ;;
            restart|--restart)
                ACTION="restart"
                shift
                ;;
            foreground|-f|--foreground)
                ACTION="start"
                IS_FOREGROUND=true
                shift
                ;;
            -d|--daemon)
                ACTION="start"
                IS_DAEMON=true
                IS_FOREGROUND=false
                shift
                ;;
            test|--test)
                ACTION="test"
                shift
                ;;
            -h|--help|help)
                show_help
                exit 0
                ;;
            -dir|--dir)
                STORAGE_DIR="$2"
                shift 2
                ;;
            -mserver|--mserver)
                MASTER_SERVER="$2"
                shift 2
                ;;
            -ip|--ip)
                NODE_IP="$2"
                PUBLIC_URL="${NODE_IP}:${VOLUME_PORT}"
                shift 2
                ;;
            -port|--port)
                VOLUME_PORT="$2"
                VOLUME_PORT_GRPC=$((VOLUME_PORT + 10000))
                PUBLIC_URL="${NODE_IP}:${VOLUME_PORT}"
                shift 2
                ;;
            -port.grpc)
                VOLUME_PORT_GRPC="$2"
                shift 2
                ;;
            -max|--max)
                MAX_VOLUMES="$2"
                shift 2
                ;;
            --pid-file)
                PID_FILE="$2"
                shift 2
                ;;
            --log-file)
                LOG_FILE="$2"
                shift 2
                ;;
            *)
                log_error "Unknown argument: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# --- Main Dispatcher ---
main() {
    parse_args "$@"

    case "$ACTION" in
        start)
            start_daemon
            ;;
        stop)
            stop_daemon
            ;;
        status)
            check_status
            ;;
        restart)
            stop_daemon
            sleep 1
            start_daemon
            ;;
        test)
            run_preflight_test
            ;;
        *)
            log_error "Invalid action: $ACTION"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
