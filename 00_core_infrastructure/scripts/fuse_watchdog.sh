#!/usr/bin/env bash
# ==============================================================================
# LAUBURU FUSE MOUNT ZOMBIE WATCHDOG DAEMON (Universal macOS & Linux)
# Subsystem: 00_core_infrastructure/scripts
# Target: 7-Node Tailscale Mesh (Linux Head, Mac Host, MacBook Pro Vault)
# Default Filers: 100.101.39.98:8888,100.119.199.76:8888,100.103.212.21:8888
# Default Mount: /mnt/dfs_unified (Linux) | /Volumes/dfs_unified (macOS)
# ==============================================================================
set -u

# --- Color Formatting Helpers ---
RED="\033[0;31m"
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
BLUE="\033[0;34m"
CYAN="\033[0;36m"
BOLD="\033[1m"
NC="\033[0m" # No Color

OS_TYPE="$(uname -s)"

# --- Default Configurations ---
DEFAULT_LINUX_MOUNT="/mnt/dfs_unified"
DEFAULT_DARWIN_MOUNT="/Volumes/dfs_unified"

if [ "$OS_TYPE" = "Darwin" ]; then
    DEFAULT_MOUNT="$DEFAULT_DARWIN_MOUNT"
else
    DEFAULT_MOUNT="$DEFAULT_LINUX_MOUNT"
fi

MOUNT_POINT="${DFS_MOUNT_POINT:-$DEFAULT_MOUNT}"
FILER_ENDPOINTS="${DFS_FILER_PEERS:-${FILER_ENDPOINTS:-100.101.39.98:8888,100.119.199.76:8888,100.103.212.21:8888}}"
POLL_INTERVAL="${POLL_INTERVAL:-5}"
PROBE_TIMEOUT="${PROBE_TIMEOUT:-3}"
MAX_FAILURES="${MAX_FAILURES:-2}"
RUN_ONCE=false
RUN_TEST=false
VERBOSE=false

# --- Logging Helper ---
log_info() {
    echo -e "${CYAN}$(date -u +'%Y-%m-%dT%H:%M:%SZ') [FUSE_WATCHDOG] [INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}$(date -u +'%Y-%m-%dT%H:%M:%SZ') [FUSE_WATCHDOG] [SUCCESS]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}$(date -u +'%Y-%m-%dT%H:%M:%SZ') [FUSE_WATCHDOG] [WARN]${NC} $*"
}

log_error() {
    echo -e "${RED}$(date -u +'%Y-%m-%dT%H:%M:%SZ') [FUSE_WATCHDOG] [ERROR]${NC} $*" >&2
}

log() {
    echo "$(date -u +'%Y-%m-%dT%H:%M:%SZ') [FUSE_WATCHDOG] $*"
}

# --- Usage & Help Display ---
show_help() {
    cat << HELP_EOF
Usage: $(basename "$0") [OPTIONS] [MOUNT_POINT] [FILER_ENDPOINTS]

Universal, lightweight, aggressive FUSE Mount Zombie Watchdog daemon for SeaweedFS HA.
Detects kernel I/O freezes, executes forceful lazy detachment, and remounts against HA filers.

Positional Arguments:
  MOUNT_POINT        Filesystem path to monitor (Default: $DEFAULT_MOUNT)
  FILER_ENDPOINTS    Comma-separated list of Filer IP:PORT endpoints
                     (Default: 100.101.39.98:8888,100.119.199.76:8888,100.103.212.21:8888)

Options:
  -m, --mount-point PATH     Override target FUSE mount point path
  -f, --filers LIST          Comma-separated list of HA Filer endpoints
  -i, --interval SECONDS     Polling interval in seconds (Default: 5)
  -t, --timeout SECONDS      Non-blocking probe timeout in seconds (Default: 3)
      --max-failures NUM     Consecutive failure threshold before teardown (Default: 2)
  -1, --once                 Run a single health probe cycle and exit
      --test                 Execute non-destructive self-test / diagnostics and exit
  -v, --verbose              Enable verbose diagnostic output
  -h, --help                 Display this help message and exit

Environment Variables:
  DFS_MOUNT_POINT            Default target mount path
  DFS_FILER_PEERS            Comma-separated HA filer list
  POLL_INTERVAL              Seconds between poll cycles
  PROBE_TIMEOUT              Canary probe timeout limit in seconds
  MAX_FAILURES               Failure threshold count

Examples:
  $(basename "$0") --once
  $(basename "$0") --test
  $(basename "$0") --mount-point /mnt/dfs_unified --filers 100.101.39.98:8888,100.119.199.76:8888
HELP_EOF
}

# --- CLI Parameter Parsing ---
POSITIONAL_ARGS=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)
            show_help
            exit 0
            ;;
        -m|--mount-point)
            MOUNT_POINT="$2"
            shift 2
            ;;
        -f|--filers|--filer-endpoints)
            FILER_ENDPOINTS="$2"
            shift 2
            ;;
        -i|--interval)
            POLL_INTERVAL="$2"
            shift 2
            ;;
        -t|--timeout)
            PROBE_TIMEOUT="$2"
            shift 2
            ;;
        --max-failures)
            MAX_FAILURES="$2"
            shift 2
            ;;
        -1|--once)
            RUN_ONCE=true
            shift
            ;;
        --test)
            RUN_TEST=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        --)
            shift
            POSITIONAL_ARGS+=("$@")
            break
            ;;
        -*)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
        *)
            POSITIONAL_ARGS+=("$1")
            shift
            ;;
    esac
done

# Handle positional arguments if provided
if [ ${#POSITIONAL_ARGS[@]} -ge 1 ]; then
    MOUNT_POINT="${POSITIONAL_ARGS[0]}"
fi
if [ ${#POSITIONAL_ARGS[@]} -ge 2 ]; then
    FILER_ENDPOINTS="${POSITIONAL_ARGS[1]}"
fi

# Clean & normalize parameters
while [[ "$MOUNT_POINT" == */ && "$MOUNT_POINT" != "/" ]]; do
    MOUNT_POINT="${MOUNT_POINT%/}"
done
[ -z "$MOUNT_POINT" ] && MOUNT_POINT="/"

# Calculate unique lock name per mount point
LOCK_HASH="$(echo -n "$MOUNT_POINT" | md5sum 2>/dev/null | awk "{print \$1}" || echo -n "$MOUNT_POINT" | md5 2>/dev/null || echo "dfs_unified")"
LOCK_FILE="/tmp/fuse_watchdog_${LOCK_HASH}.lock"
LOCK_DIR="/tmp/fuse_watchdog_${LOCK_HASH}.lock.d"
CLEAN_NAME="$(basename "$MOUNT_POINT")"
[ -z "$CLEAN_NAME" ] && CLEAN_NAME="root"

# --- Process Locking & Concurrency Control ---
acquire_lock() {
    if [ "$OS_TYPE" = "Darwin" ]; then
        # Atomic directory lock for macOS
        if ! mkdir "$LOCK_DIR" 2>/dev/null; then
            local existing_pid
            existing_pid="$(cat "$LOCK_DIR/pid" 2>/dev/null || echo "")"
            if [ -n "$existing_pid" ] && kill -0 "$existing_pid" 2>/dev/null; then
                log_warn "Another watchdog instance is actively running (PID: $existing_pid) for mount point $MOUNT_POINT. Exiting."
                exit 0
            else
                log_warn "Stale lock directory detected ($LOCK_DIR). Re-acquiring lock..."
                rm -rf "$LOCK_DIR" 2>/dev/null || true
                if ! mkdir "$LOCK_DIR" 2>/dev/null; then
                    log_error "Failed to acquire directory lock ($LOCK_DIR). Exiting."
                    exit 1
                fi
            fi
        fi
        echo "$$" > "$LOCK_DIR/pid"
        trap "rm -rf "$LOCK_DIR" 2>/dev/null; exit 0" EXIT INT TERM HUP
    else
        # flock process lock on Linux / BSD
        exec 200>"$LOCK_FILE"
        if ! flock -n 200 2>/dev/null; then
            log_warn "Another watchdog instance holds exclusive lock on $LOCK_FILE for $MOUNT_POINT. Exiting."
            exit 0
        fi
        echo "$$" > "$LOCK_FILE"
        trap "rm -f "$LOCK_FILE" 2>/dev/null; exit 0" EXIT INT TERM HUP
    fi
}

# --- Core VFS Mount State Inspector ---
is_mounted() {
    if [ "$OS_TYPE" = "Darwin" ]; then
        mount | grep -q " on ${MOUNT_POINT} " || mount | grep -q " on ${MOUNT_POINT} ("
    else
        if [ -r /proc/mounts ]; then
            grep -qs " ${MOUNT_POINT} " /proc/mounts
        elif command -v findmnt >/dev/null 2>&1; then
            findmnt -M "$MOUNT_POINT" >/dev/null 2>&1
        else
            mount | grep -q " on ${MOUNT_POINT} "
        fi
    fi
}

# --- Universal Non-Blocking Canary Probe ---
probe_mount_io() {
    local timeout_val="${1:-$PROBE_TIMEOUT}"
    
    # 1. Primary: GNU timeout / macOS coreutils gtimeout
    if command -v timeout >/dev/null 2>&1; then
        timeout -k 1s -s KILL "${timeout_val}s" stat -t "$MOUNT_POINT" >/dev/null 2>&1
        return $?
    elif command -v gtimeout >/dev/null 2>&1; then
        gtimeout -k 1s -s KILL "${timeout_val}s" stat -t "$MOUNT_POINT" >/dev/null 2>&1
        return $?
    fi

    # 2. Universal Subshell Timer Watchdog fallback (POSIX safe)
    ( stat "$MOUNT_POINT" >/dev/null 2>&1 ) &
    local sub_pid=$!
    local elapsed=0
    local max_ticks=$(( timeout_val * 10 ))
    
    while kill -0 "$sub_pid" 2>/dev/null; do
        sleep 0.1
        elapsed=$(( elapsed + 1 ))
        if [ "$elapsed" -ge "$max_ticks" ]; then
            kill -9 "$sub_pid" 2>/dev/null || true
            wait "$sub_pid" 2>/dev/null || true
            return 124
        fi
    done
    wait "$sub_pid" 2>/dev/null
    return $?
}

# --- Pre-Flight Filer Reachability Check ---
check_filer_reachability() {
    local raw_endpoints="$1"
    local IFS=","
    read -ra ADDR_ARRAY <<< "$raw_endpoints"
    
    for endpoint in "${ADDR_ARRAY[@]}"; do
        local ep="$(echo "$endpoint" | tr -d "[:space:]")"
        [ -z "$ep" ] && continue
        
        local check_url="http://${ep}/"
        if curl -s --connect-timeout 2 --max-time 3 -I "$check_url" >/dev/null 2>&1 ||            curl -s --connect-timeout 2 --max-time 3 "$check_url" >/dev/null 2>&1; then
            echo "$ep"
            return 0
        fi
    done
    return 1
}

# --- Forceful Lazy Detachment & Process Eviction ---
force_unmount() {
    log_warn "Initiating forceful teardown of hung mount: $MOUNT_POINT"
    
    # 1. Kill lingering weed mount processes targeting this mount
    log_info "Evicting lingering "weed mount" processes for $MOUNT_POINT..."
    pkill -9 -f "weed mount.*${MOUNT_POINT}" 2>/dev/null || true
    pkill -9 -f "weed mount.*-dir=${MOUNT_POINT}" 2>/dev/null || true
    sleep 0.5

    # 2. Platform-Specific Forced/Lazy Unmount
    if [ "$OS_TYPE" = "Darwin" ]; then
        log_info "Executing Darwin forced detachment (diskutil unmount force / umount -f)..."
        diskutil unmount force "$MOUNT_POINT" >/dev/null 2>&1 ||         umount -f "$MOUNT_POINT" >/dev/null 2>&1 || true
    else
        log_info "Executing Linux lazy forced detachment (umount -l -f / fusermount3 -u -z)..."
        umount -l -f "$MOUNT_POINT" >/dev/null 2>&1 ||         fusermount3 -u -z "$MOUNT_POINT" >/dev/null 2>&1 ||         fusermount -u -z "$MOUNT_POINT" >/dev/null 2>&1 ||         umount -f "$MOUNT_POINT" >/dev/null 2>&1 || true

        # Abort active FUSE connections if kernel interface exposed
        if [ -d /sys/fs/fuse/connections ]; then
            for conn_abort in /sys/fs/fuse/connections/*/abort; do
                if [ -w "$conn_abort" ]; then
                    echo 1 > "$conn_abort" 2>/dev/null || true
                fi
            done
        fi
    fi
    
    sleep 0.8
}

# --- Locate SeaweedFS Binary ---
find_weed_binary() {
    if [ -x "/usr/local/bin/weed" ]; then
        echo "/usr/local/bin/weed"
    elif [ -x "/usr/bin/weed" ]; then
        echo "/usr/bin/weed"
    elif [ -x "$HOME/.local/bin/weed" ]; then
        echo "$HOME/.local/bin/weed"
    elif [ -x "/opt/homebrew/bin/weed" ]; then
        echo "/opt/homebrew/bin/weed"
    elif command -v weed >/dev/null 2>&1; then
        command -v weed
    else
        echo ""
    fi
}

# --- Clean Remount Execution ---
remount() {
    log_info "Evaluating Filer reachability across: $FILER_ENDPOINTS"
    local active_filer
    active_filer="$(check_filer_reachability "$FILER_ENDPOINTS" || echo "")"
    
    if [ -z "$active_filer" ]; then
        log_warn "No SeaweedFS Filers reachable across mesh ($FILER_ENDPOINTS). Deferring remount until network restores."
        return 1
    fi

    log_success "Active Filer endpoint confirmed: $active_filer. Launching clean remount on $MOUNT_POINT..."
    mkdir -p "$MOUNT_POINT" 2>/dev/null || true

    if [ "$OS_TYPE" = "Darwin" ]; then
        if [ ! -d "/Library/Filesystems/macfuse.fs" ] && [ ! -d "/Library/Filesystems/osxfuse.fs" ] && ! command -v mount_macfuse >/dev/null 2>&1; then
            log_warn "macFUSE / OSXFUSE kernel extension not installed on macOS. FUSE mount unavailable. Storage will use direct APFS / WebDAV layer."
            return 1
        fi
    fi

    local weed_bin
    weed_bin="$(find_weed_binary)"
    if [ -z "$weed_bin" ]; then
        log_error "SeaweedFS executable \"weed\" not found in PATH or standard binary locations."
        return 1
    fi

    local log_out="/tmp/weed_mount_${CLEAN_NAME}.log"
    log_info "Executing: $weed_bin mount -filer=$FILER_ENDPOINTS -dir=$MOUNT_POINT"
    
    nohup "$weed_bin" mount \
        -filer="$FILER_ENDPOINTS" \
        -dir="$MOUNT_POINT" \
        -filer.path=/ \
        -cacheCapacityMB=1024 \
        -chunkSizeLimitMB=16 \
        -concurrentWriters=32 \
        -allowOthers=true \
        -umask=000 \
        -readOnly=false >> "$log_out" 2>&1 &

    local weed_pid=$!
    log_info "Spawned "weed mount" daemon (PID: $weed_pid). Waiting for VFS mount readiness..."

    local wait_count=0
    while [ $wait_count -lt 6 ]; do
        sleep 0.5
        if is_mounted; then
            probe_mount_io 2
            if [ $? -eq 0 ]; then
                log_success "FUSE mount at $MOUNT_POINT is mounted, responsive, and healthy."
                return 0
            fi
        fi
        wait_count=$((wait_count + 1))
    done

    if is_mounted; then
        log_success "FUSE mount at $MOUNT_POINT successfully established."
        return 0
    else
        log_error "Remount command executed, but $MOUNT_POINT is not visible in mount table. Inspect $log_out"
        return 1
    fi
}

# --- Self-Test / Diagnostics Mode ---
run_self_test() {
    echo -e "${BOLD}${BLUE}================================================================${NC}"
    echo -e "${BOLD}${BLUE}     LAUBURU FUSE WATCHDOG SELF-TEST & DIAGNOSTICS SUITE        ${NC}"
    echo -e "${BOLD}${BLUE}================================================================${NC}"
    echo "Host OS:           $OS_TYPE ($(uname -m))"
    echo "Target Mount:      $MOUNT_POINT"
    echo "Target Filers:     $FILER_ENDPOINTS"
    echo "Probe Timeout:     ${PROBE_TIMEOUT}s"
    echo "Failure Limit:     $MAX_FAILURES consecutive cycles"
    echo "Lock File:         $LOCK_FILE"
    echo "----------------------------------------------------------------"

    # 1. Check required tools
    log_info "[1/5] Checking diagnostic tools..."
    local tools=("stat" "curl" "pkill")
    for t in "${tools[@]}"; do
        if command -v "$t" >/dev/null 2>&1; then
            log_success "Found utility: $t ($(command -v "$t"))"
        else
            log_warn "Missing utility: $t"
        fi
    done

    # 2. Check timeout mechanism
    log_info "[2/5] Checking non-blocking probe timeout engine..."
    if command -v timeout >/dev/null 2>&1; then
        log_success "Native "timeout" command available."
    elif command -v gtimeout >/dev/null 2>&1; then
        log_success "GNU "gtimeout" command available."
    else
        log_info "Using POSIX subshell timer fallback."
    fi

    # 3. Test non-blocking probe on /tmp
    log_info "[3/5] Testing non-blocking canary probe on local filesystem (/tmp)..."
    local orig_mount="$MOUNT_POINT"
    MOUNT_POINT="/tmp"
    probe_mount_io 2
    local probe_res=$?
    MOUNT_POINT="$orig_mount"
    if [ "$probe_res" -eq 0 ]; then
        log_success "Canary probe on /tmp succeeded (exit code: 0)."
    else
        log_error "Canary probe on /tmp returned unexpected code: $probe_res"
    fi

    # 4. Check Filer connectivity
    log_info "[4/5] Checking SeaweedFS Filer HA reachability..."
    local reachable_filer
    reachable_filer="$(check_filer_reachability "$FILER_ENDPOINTS" || echo "")"
    if [ -n "$reachable_filer" ]; then
        log_success "Reachable Filer found: $reachable_filer"
    else
        log_warn "No Filers currently reachable at ($FILER_ENDPOINTS). Offline mode operational."
    fi

    # 5. Check "weed" binary
    log_info "[5/5] Checking SeaweedFS "weed" binary availability..."
    local weed_bin
    weed_bin="$(find_weed_binary)"
    if [ -n "$weed_bin" ]; then
        log_success "Found SeaweedFS binary: $weed_bin"
    else
        log_warn "SeaweedFS "weed" binary not found in standard system paths (expected in production containers)."
    fi

    echo "----------------------------------------------------------------"
    log_success "Self-test diagnostics completed successfully."
    exit 0
}

# --- Main Watchdog Execution Routine ---
main() {
    if [ "$RUN_TEST" = true ]; then
        run_self_test
    fi

    # Acquire exclusive single-instance lock
    acquire_lock

    log_info "Starting FUSE Mount Watchdog Daemon..."
    log_info "Target Mount: $MOUNT_POINT | Filers: $FILER_ENDPOINTS"
    log_info "Poll Interval: ${POLL_INTERVAL}s | Probe Timeout: ${PROBE_TIMEOUT}s | Max Failures: $MAX_FAILURES"

    local consecutive_failures=0

    while true; do
        if is_mounted; then
            probe_mount_io "$PROBE_TIMEOUT"
            local probe_code=$?

            if [ "$probe_code" -eq 0 ]; then
                if [ "$consecutive_failures" -gt 0 ]; then
                    log_success "Mount point $MOUNT_POINT returned to healthy state. Resetting failure counter."
                elif [ "$VERBOSE" = true ]; then
                    log_info "Mount point $MOUNT_POINT is responsive and healthy."
                fi
                consecutive_failures=0
            else
                consecutive_failures=$((consecutive_failures + 1))
                log_warn "Mount probe on $MOUNT_POINT failed (exit code: $probe_code). Failures: $consecutive_failures/$MAX_FAILURES"

                if [ "$consecutive_failures" -ge "$MAX_FAILURES" ]; then
                    log_error "CRITICAL: Mount point $MOUNT_POINT frozen or deadlocked ($consecutive_failures consecutive failures). Initiating teardown & recovery..."
                    force_unmount
                    remount
                    consecutive_failures=0
                fi
            fi
        else
            log_warn "Mount point $MOUNT_POINT is not mounted in VFS table. Attempting auto-mount..."
            remount || true
            consecutive_failures=0
        fi

        if [ "$RUN_ONCE" = true ]; then
            log_info "Single-run cycle (--once) complete. Exiting."
            break
        fi

        sleep "$POLL_INTERVAL"
    done
}

main "$@"
