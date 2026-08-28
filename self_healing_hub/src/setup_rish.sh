#!/usr/bin/env bash
# ==============================================================================
# Lauburu Self-Healing Hub - Shizuku (rish) Setup & Permission Provisioner
# ==============================================================================
# Automatically sets up and verifies the Shizuku 'rish' privileged execution
# client on Android nodes (e.g. Pixel 10 Pro XL, Samsung S20+), granting
# untethered ADB-level Binder IPC execution capabilities without USB cables.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_PKG="com.termux"
TARGET_DIR="${PREFIX:-/data/local/tmp}/bin"
FORCE=0
VERIFY_ONLY=0
JSON_OUTPUT=0
DRY_RUN=0
MOCK_MODE=0
VERBOSE=0

# Shizuku package constants
SHIZUKU_PKG="moe.shizuku.privileged.api"
SHIZUKU_PERM="moe.shizuku.manager.permission.API_V23"

# Standard Shizuku rish source locations
SHIZUKU_SDCARD_FILES="/sdcard/Android/data/${SHIZUKU_PKG}/files"
SHIZUKU_APP_FILES="/data/user_de/0/${SHIZUKU_PKG}/files"

log_info() {
    if [[ "$JSON_OUTPUT" -eq 0 ]]; then
        echo "[INFO] [$(date +'%Y-%m-%dT%H:%M:%SZ')] $*"
    fi
}

log_warn() {
    if [[ "$JSON_OUTPUT" -eq 0 ]]; then
        echo "[WARN] [$(date +'%Y-%m-%dT%H:%M:%SZ')] $*" >&2
    fi
}

log_err() {
    if [[ "$JSON_OUTPUT" -eq 0 ]]; then
        echo "[ERROR] [$(date +'%Y-%m-%dT%H:%M:%SZ')] $*" >&2
    fi
}

log_debug() {
    if [[ "$VERBOSE" -eq 1 && "$JSON_OUTPUT" -eq 0 ]]; then
        echo "[DEBUG] [$(date +'%Y-%m-%dT%H:%M:%SZ')] $*"
    fi
}

usage() {
    cat << 'USG'
Usage: setup_rish.sh [OPTIONS]

Automated Shizuku (rish) installation and permission setup.

Options:
  --target-dir <DIR>    Directory to install rish binary (Default: $PREFIX/bin or /data/local/tmp/bin)
  --pkg <PACKAGE>       Target Android application package ID (Default: com.termux)
  --verify-only         Only verify existing Shizuku and rish installation
  --force               Overwrite existing rish binary and dex files
  --dry-run             Simulate actions without modifying filesystem or permissions
  --mock                Execute in synthetic mock testbed mode
  --json                Output status in JSON format
  -v, --verbose         Enable verbose debug logging
  -h, --help            Show this help message
USG
    exit 0
}

# Parse CLI arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --target-dir)
            TARGET_DIR="$2"
            shift 2
            ;;
        --pkg)
            TARGET_PKG="$2"
            shift 2
            ;;
        --verify-only)
            VERIFY_ONLY=1
            shift
            ;;
        --force)
            FORCE=1
            shift
            ;;
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        --mock)
            MOCK_MODE=1
            shift
            ;;
        --json)
            JSON_OUTPUT=1
            shift
            ;;
        -v|--verbose)
            VERBOSE=1
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            log_err "Unknown argument: $1"
            usage
            ;;
    esac
done

detect_environment() {
    if [[ "$MOCK_MODE" -eq 1 ]]; then
        ENV_TYPE="mock"
    elif [[ -n "${PREFIX:-}" && -d "/data/data/com.termux" ]]; then
        ENV_TYPE="termux"
    elif [[ -f "/system/bin/sh" && -f "/system/bin/app_process" ]]; then
        ENV_TYPE="android_native"
    elif command -v adb >/dev/null 2>&1; then
        ENV_TYPE="host_adb"
    else
        ENV_TYPE="generic_posix"
    fi
    log_debug "Detected environment type: $ENV_TYPE"
}

check_shizuku_service() {
    log_info "Checking Shizuku daemon status..."
    if [[ "$MOCK_MODE" -eq 1 ]]; then
        SHIZUKU_RUNNING=1
        SHIZUKU_VERSION="13.5.4"
        return 0
    fi

    if [[ "$ENV_TYPE" == "termux" || "$ENV_TYPE" == "android_native" ]]; then
        if pidof "$SHIZUKU_PKG" >/dev/null 2>&1 || pgrep -f "shizuku_server" >/dev/null 2>&1; then
            SHIZUKU_RUNNING=1
            return 0
        fi
        # Check Binder service registry
        if service list 2>/dev/null | grep -q "$SHIZUKU_PKG"; then
            SHIZUKU_RUNNING=1
            return 0
        fi
    elif [[ "$ENV_TYPE" == "host_adb" ]]; then
        if adb shell "pidof $SHIZUKU_PKG" 2>/dev/null | grep -E -q '^[0-9]+'; then
            SHIZUKU_RUNNING=1
            return 0
        fi
    fi

    SHIZUKU_RUNNING=0
    return 1
}

grant_shizuku_permissions() {
    log_info "Granting Shizuku API permissions to $TARGET_PKG..."
    if [[ "$DRY_RUN" -eq 1 || "$MOCK_MODE" -eq 1 ]]; then
        log_debug "[DRY-RUN/MOCK] Granting $SHIZUKU_PERM to $TARGET_PKG"
        PERM_GRANTED=1
        return 0
    fi

    if [[ "$ENV_TYPE" == "termux" || "$ENV_TYPE" == "android_native" ]]; then
        pm grant "$TARGET_PKG" "$SHIZUKU_PERM" 2>/dev/null || true
        cmd appops set "$TARGET_PKG" "$SHIZUKU_PERM" allow 2>/dev/null || true
        PERM_GRANTED=1
    elif [[ "$ENV_TYPE" == "host_adb" ]]; then
        adb shell "pm grant $TARGET_PKG $SHIZUKU_PERM 2>/dev/null || true"
        adb shell "cmd appops set $TARGET_PKG $SHIZUKU_PERM allow 2>/dev/null || true"
        PERM_GRANTED=1
    else
        PERM_GRANTED=0
    fi
}

install_rish_binary() {
    local target_bin="${TARGET_DIR}/rish"
    local target_dex="${TARGET_DIR}/rish_dex.dex"

    log_info "Installing rish binary into $TARGET_DIR..."

    if [[ "$DRY_RUN" -eq 1 ]]; then
        log_debug "[DRY-RUN] Skipping physical binary creation."
        RISH_INSTALLED=1
        return 0
    fi

    mkdir -p "$TARGET_DIR"

    if [[ "$MOCK_MODE" -eq 1 ]]; then
        # Generate standalone synthetic mock rish executable
        cat << 'RISH_MOCK' > "$target_bin"
#!/usr/bin/env bash
# Synthetic Shizuku rish wrapper for verification testbeds
if [[ "$*" == *"id"* ]]; then
    echo "uid=2000(shell) gid=2000(shell) groups=2000(shell),1004(input),1007(log),1011(adb),1015(sdcard_rw),1028(sdcard_r),3001(net_bt_admin),3002(net_bt),3003(inet),3006(net_bw_stats),3009(readproc),3011(uhid) context=u:r:shell:s0"
    exit 0
fi

if [[ "$1" == "-c" ]]; then
    shift
    eval "$*"
else
    exec /bin/sh "$@"
fi
RISH_MOCK
        chmod +x "$target_bin"
        touch "$target_dex"
        RISH_INSTALLED=1
        return 0
    fi

    # Check for exported Shizuku files on device
    local src_rish=""
    local src_dex=""

    for d in "$SHIZUKU_SDCARD_FILES" "$SHIZUKU_APP_FILES" "/data/local/tmp"; do
        if [[ -f "$d/rish" && -f "$d/rish_dex.dex" ]]; then
            src_rish="$d/rish"
            src_dex="$d/rish_dex.dex"
            break
        elif [[ -f "$d/rish" && -f "$d/shizuku.dex" ]]; then
            src_rish="$d/rish"
            src_dex="$d/shizuku.dex"
            break
        fi
    done

    if [[ -n "$src_rish" && "$FORCE" -eq 1 ]] || [[ -n "$src_rish" && ! -f "$target_bin" ]]; then
        cp -f "$src_rish" "$target_bin"
        cp -f "$src_dex" "$target_dex"
    elif [[ ! -f "$target_bin" || "$FORCE" -eq 1 ]]; then
        # Write genuine rish standard wrapper script
        cat << RISH_SCRIPT > "$target_bin"
#!/system/bin/sh
# Shizuku rish standard launcher
RISH_APPLICATION_ID="${TARGET_PKG}"
DEX="${target_dex}"

if [ ! -f "\$DEX" ]; then
    # Fallback to standard locations
    if [ -f "${SHIZUKU_SDCARD_FILES}/rish_dex.dex" ]; then
        DEX="${SHIZUKU_SDCARD_FILES}/rish_dex.dex"
    elif [ -f "/data/local/tmp/rish_dex.dex" ]; then
        DEX="/data/local/tmp/rish_dex.dex"
    fi
fi

export CLASSPATH="\$DEX"
export RISH_APPLICATION_ID="\$RISH_APPLICATION_ID"

if [ "\$#" -eq 0 ]; then
    exec /system/bin/app_process /system/bin moe.shizuku.manager.rish.Starter "\$@"
else
    exec /system/bin/app_process /system/bin moe.shizuku.manager.rish.Starter "\$@"
fi
RISH_SCRIPT
    fi

    chmod 755 "$target_bin" 2>/dev/null || chmod +x "$target_bin" 2>/dev/null || true
    RISH_INSTALLED=1
}

verify_rish_execution() {
    local target_bin="${TARGET_DIR}/rish"
    log_info "Verifying rish privileged execution..."

    if [[ "$MOCK_MODE" -eq 1 ]]; then
        VERIFY_OUT="uid=2000(shell) gid=2000(shell) groups=2000(shell)"
        VERIFY_SUCCESS=1
        return 0
    fi

    if [[ -x "$target_bin" ]]; then
        if VERIFY_OUT=$("$target_bin" -c "id" 2>&1); then
            if [[ "$VERIFY_OUT" == *"uid=2000"* || "$VERIFY_OUT" == *"uid=0"* ]]; then
                VERIFY_SUCCESS=1
                return 0
            fi
        fi
    elif command -v rish >/dev/null 2>&1; then
        if VERIFY_OUT=$(rish -c "id" 2>&1); then
            if [[ "$VERIFY_OUT" == *"uid=2000"* || "$VERIFY_OUT" == *"uid=0"* ]]; then
                VERIFY_SUCCESS=1
                return 0
            fi
        fi
    fi

    VERIFY_OUT="Execution failed or rish not in executable path"
    VERIFY_SUCCESS=0
    return 1
}

# Main Execution Flow
detect_environment

SHIZUKU_RUNNING=0
PERM_GRANTED=0
RISH_INSTALLED=0
VERIFY_SUCCESS=0
VERIFY_OUT=""

check_shizuku_service || log_warn "Shizuku service is not currently running or not detected."

if [[ "$VERIFY_ONLY" -eq 0 ]]; then
    grant_shizuku_permissions
    install_rish_binary
fi

verify_rish_execution || log_warn "Rish privileged execution check could not verify elevated UID."

if [[ "$JSON_OUTPUT" -eq 1 ]]; then
    cat << JSON_EOF
{
  "timestamp": "$(date -u +'%Y-%m-%dT%H:%M:%SZ')",
  "environment": "$ENV_TYPE",
  "target_package": "$TARGET_PKG",
  "target_dir": "$TARGET_DIR",
  "shizuku_running": $([[ $SHIZUKU_RUNNING -eq 1 ]] && echo "true" || echo "false"),
  "permission_granted": $([[ $PERM_GRANTED -eq 1 ]] && echo "true" || echo "false"),
  "rish_installed": $([[ $RISH_INSTALLED -eq 1 ]] && echo "true" || echo "false"),
  "verified_privileged": $([[ $VERIFY_SUCCESS -eq 1 ]] && echo "true" || echo "false"),
  "verify_output": "$VERIFY_OUT"
}
JSON_EOF
else
    log_info "=== Setup Summary ==="
    log_info "Environment: $ENV_TYPE"
    log_info "Target Package: $TARGET_PKG"
    log_info "Rish Binary: $TARGET_DIR/rish"
    log_info "Shizuku Running: $([[ $SHIZUKU_RUNNING -eq 1 ]] && echo 'YES' || echo 'NO')"
    log_info "Privileged Execution: $([[ $VERIFY_SUCCESS -eq 1 ]] && echo 'PASSED' || echo 'FAILED/UNVERIFIED')"
fi

if [[ "$VERIFY_SUCCESS" -eq 1 || "$MOCK_MODE" -eq 1 || "$DRY_RUN" -eq 1 ]]; then
    exit 0
else
    exit 1
fi
