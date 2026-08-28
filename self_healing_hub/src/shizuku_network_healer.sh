#!/usr/bin/env bash
# ==============================================================================
# Lauburu Self-Healing Hub - Autonomous Shizuku Network Healer
# ==============================================================================
# Executes privileged self-healing routines across Android nodes (Pixel 10 / S20)
# via Shizuku Binder IPC (rish) or ADB without requiring physical USB tethers.
#
# Core Self-Healing Pathways:
# 1. Tailscale Daemon Force Restart (am force-stop -> am start)
# 2. Radio Interface Bouncing (svc wifi / svc data toggle)
# 3. Wireless ADB Persistence (setprop service.adb.tcp.port 5555 & adbd supervisor)
# 4. Doze Mode Whitelisting (dumpsys deviceidle & cmd appops)
# 5. Phantom Process Monitor Disablement (settings put global)
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Action flags
ACTION_HEAL_ALL=0
ACTION_TAILSCALE=0
ACTION_WIFI=0
ACTION_CELLULAR=0
ACTION_ADB_PERSIST=0
ACTION_DOZE_WHITELIST=0
ACTION_PHANTOM_BYPASS=0
ACTION_STATUS=0

# Configuration & mode flags
DRY_RUN=0
MOCK_MODE=0
JSON_OUTPUT=0
VERBOSE=0
TRACE_MODE=0

# Log destinations
LORA_DATASET="${REPO_ROOT}/data/lora_datasets/shizuku_healing_actions.jsonl"
STATUS_FILE="${REPO_ROOT}/data/network/shizuku_healing_status.json"

# Target constants
TAILSCALE_PKG="com.tailscale.ipn"
TERMUX_PKG="com.termux"
TERMUX_BOOT_PKG="com.termux.boot"
OPENCLAW_PKG="com.openclaw.agent"
ADB_TCP_PORT="5555"

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
Usage: shizuku_network_healer.sh [ACTION] [OPTIONS]

Privileged Android Network Self-Healing Engine (Shizuku Binder IPC / Untethered ADB).

Actions:
  --heal-all            Execute all self-healing pathways in sequence
  --tailscale-restart   Force restart Tailscale IPN VPN daemon
  --wifi-bounce         Cycle Wi-Fi radio interface (disable -> enable)
  --cellular-bounce     Cycle Cellular mobile data interface
  --adb-persist         Enforce wireless ADB TCP port 5555 & restart adbd
  --doze-whitelist      Whitelist Termux & Tailscale from Android Doze battery optimizations
  --phantom-bypass      Disable Android Phantom Process Killer monitor
  --status              Inspect and display health status of all subsystems

Options:
  --dry-run             Simulate actions without executing mutating commands
  --mock                Execute in synthetic mock testbed mode
  --trace               Print detailed command trace during execution
  --json                Output structured JSON summary
  -v, --verbose         Enable verbose debug logging
  -h, --help            Show this help message
USG
    exit 0
}

# Parse CLI arguments
if [[ $# -eq 0 ]]; then
    ACTION_HEAL_ALL=1
fi

while [[ $# -gt 0 ]]; do
    case "$1" in
        --heal-all)
            ACTION_HEAL_ALL=1
            shift
            ;;
        --tailscale-restart)
            ACTION_TAILSCALE=1
            shift
            ;;
        --wifi-bounce)
            ACTION_WIFI=1
            shift
            ;;
        --cellular-bounce)
            ACTION_CELLULAR=1
            shift
            ;;
        --adb-persist)
            ACTION_ADB_PERSIST=1
            shift
            ;;
        --doze-whitelist)
            ACTION_DOZE_WHITELIST=1
            shift
            ;;
        --phantom-bypass)
            ACTION_PHANTOM_BYPASS=1
            shift
            ;;
        --status)
            ACTION_STATUS=1
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
        --trace)
            TRACE_MODE=1
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

# Default to heal-all if no specific action or status requested
if [[ "$ACTION_STATUS" -eq 0 && "$ACTION_TAILSCALE" -eq 0 && "$ACTION_WIFI" -eq 0 && "$ACTION_CELLULAR" -eq 0 && "$ACTION_ADB_PERSIST" -eq 0 && "$ACTION_DOZE_WHITELIST" -eq 0 && "$ACTION_PHANTOM_BYPASS" -eq 0 ]]; then
    ACTION_HEAL_ALL=1
fi

# Initialize Action History Tracking
declare -a EXECUTED_ACTIONS=()
declare -a COMMAND_TRACES=()

record_lora_action() {
    local pathway="$1"
    local command="$2"
    local exit_code="$3"
    local duration_ms="$4"
    local output_snippet="$5"

    mkdir -p "$(dirname "$LORA_DATASET")" "$(dirname "$STATUS_FILE")"

    local timestamp
    timestamp="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"

    # Clean strings for JSON embedding
    local safe_cmd="${command//\"/\\\"}"
    local safe_out="${output_snippet//\"/\\\"}"
    safe_out="${safe_out//$'\n'/\\n}"

    local json_line
    json_line=$(cat << LORA_EOF
{"timestamp":"${timestamp}","subsystem":"shizuku_network_healer","pathway":"${pathway}","command":"${safe_cmd}","exit_code":${exit_code},"duration_ms":${duration_ms},"output":"${safe_out}"}
LORA_EOF
)
    echo "$json_line" >> "$LORA_DATASET"
}

# Privileged Executor Dispatcher
detect_privileged_executor() {
    if [[ "$MOCK_MODE" -eq 1 ]]; then
        EXECUTOR="mock"
        EXECUTOR_NAME="Synthetic Mock Executor"
        return 0
    fi

    # 1. Check for local rish (Shizuku binder client)
    if command -v rish >/dev/null 2>&1; then
        if rish -c "id" 2>/dev/null | grep -q -E "uid=2000|uid=0"; then
            EXECUTOR="rish"
            EXECUTOR_NAME="Shizuku Binder IPC (rish)"
            return 0
        fi
    fi

    # 2. Check standard rish paths
    for rish_path in "${PREFIX:-/data/local/tmp}/bin/rish" "/data/local/tmp/rish" "/system/bin/rish"; do
        if [[ -x "$rish_path" ]]; then
            if "$rish_path" -c "id" 2>/dev/null | grep -q -E "uid=2000|uid=0"; then
                EXECUTOR="$rish_path"
                EXECUTOR_NAME="Shizuku Binder IPC ($rish_path)"
                return 0
            fi
        fi
    done

    # 3. Check for direct ADB shell access (host or loopback)
    if command -v adb >/dev/null 2>&1; then
        if adb shell "id" 2>/dev/null | grep -q -E "uid=2000|uid=0"; then
            EXECUTOR="adb"
            EXECUTOR_NAME="Android Debug Bridge (adb shell)"
            return 0
        fi
    fi

    # 4. Check for root su
    if command -v su >/dev/null 2>&1; then
        if su -c "id" 2>/dev/null | grep -q "uid=0"; then
            EXECUTOR="su"
            EXECUTOR_NAME="Direct Root Superuser (su)"
            return 0
        fi
    fi

    # Fallback to standard shell with warning
    EXECUTOR="sh"
    EXECUTOR_NAME="Standard POSIX Shell (Limited Privileges)"
    log_warn "No elevated Shizuku (rish) or ADB daemon found; running in standard user mode."
}

exec_privileged() {
    local pathway="$1"
    local privileged_cmd="$2"
    local start_time
    start_time="$(date +%s%N 2>/dev/null || date +%s000000000)"

    if [[ "$TRACE_MODE" -eq 1 ]]; then
        echo "[TRACE] [$pathway] -> $privileged_cmd"
    fi
    COMMAND_TRACES+=("[$pathway] $privileged_cmd")

    if [[ "$DRY_RUN" -eq 1 ]]; then
        log_info "[DRY-RUN] Would execute ($EXECUTOR_NAME): $privileged_cmd"
        record_lora_action "$pathway" "$privileged_cmd" 0 10 "[DRY-RUN SIMULATION]"
        return 0
    fi

    local out=""
    local code=0

    if [[ "$MOCK_MODE" -eq 1 ]]; then
        # Synthetic mock dispatch with simulated responses
        code=0
        if [[ "$privileged_cmd" == *"getprop service.adb.tcp.port"* ]]; then
            out="5555"
        elif [[ "$privileged_cmd" == *"settings get global settings_enable_monitor_phantom_procs"* ]]; then
            out="false"
        elif [[ "$privileged_cmd" == *"dumpsys deviceidle whitelist"* ]]; then
            out="whitelisted: com.termux, com.tailscale.ipn, com.termux.boot"
        elif [[ "$privileged_cmd" == *"dumpsys wifi"* ]]; then
            out="Wi-Fi is enabled, mNetworkInfo [type: WIFI[], state: CONNECTED/CONNECTED]"
        else
            out="Success [mock: $privileged_cmd]"
        fi
    else
        case "$EXECUTOR" in
            rish)
                out=$(rish -c "$privileged_cmd" 2>&1) || code=$?
                ;;
            adb)
                out=$(adb shell "$privileged_cmd" 2>&1) || code=$?
                ;;
            su)
                out=$(su -c "$privileged_cmd" 2>&1) || code=$?
                ;;
            sh)
                out=$(eval "$privileged_cmd" 2>&1) || code=$?
                ;;
            *)
                if [[ -x "$EXECUTOR" ]]; then
                    out=$("$EXECUTOR" -c "$privileged_cmd" 2>&1) || code=$?
                else
                    out=$(eval "$privileged_cmd" 2>&1) || code=$?
                fi
                ;;
        esac
    fi

    local end_time
    end_time="$(date +%s%N 2>/dev/null || date +%s000000000)"
    local duration_ms=$(( (end_time - start_time) / 1000000 ))
    if [[ $duration_ms -lt 0 ]]; then duration_ms=1; fi

    record_lora_action "$pathway" "$privileged_cmd" "$code" "$duration_ms" "$out"
    log_debug "[$pathway] ($duration_ms ms, exit $code): $out"

    EXEC_OUTPUT="$out"
    return "$code"
}

# ==============================================================================
# Pathway 1: Tailscale Daemon Force Restart
# ==============================================================================
heal_tailscale_daemon() {
    log_info "=== [Pathway 1] Executing Tailscale Daemon Force Restart ==="
    local step_success=1

    # 1. Force stop existing hung Tailscale process
    log_info "Stopping $TAILSCALE_PKG daemon..."
    if ! exec_privileged "tailscale_restart" "am force-stop $TAILSCALE_PKG"; then
        log_warn "Failed to force-stop $TAILSCALE_PKG"
        step_success=0
    fi

    # Brief settle delay
    if [[ "$MOCK_MODE" -eq 0 && "$DRY_RUN" -eq 0 ]]; then
        sleep 1
    fi

    # 2. Restart Tailscale background service & launch Activity
    log_info "Restarting $TAILSCALE_PKG service..."
    exec_privileged "tailscale_restart" "am start-service $TAILSCALE_PKG/.IPNService" 2>/dev/null || true
    exec_privileged "tailscale_restart" "am start -n $TAILSCALE_PKG/com.tailscale.ipn.ui.MainActivity" 2>/dev/null || \
    exec_privileged "tailscale_restart" "am start -n $TAILSCALE_PKG/.ui.MainActivity" 2>/dev/null || \
    exec_privileged "tailscale_restart" "am start -n $TAILSCALE_PKG/.IPNActivity" 2>/dev/null || true

    EXECUTED_ACTIONS+=("tailscale_restart:$step_success")
    return $(( 1 - step_success ))
}

# ==============================================================================
# Pathway 2: Radio Interface Bouncing (Wi-Fi & Cellular Data)
# ==============================================================================
heal_radio_wifi() {
    log_info "=== [Pathway 2a] Bouncing Wi-Fi Radio Interface ==="
    local step_success=1

    log_info "Disabling Wi-Fi radio..."
    if ! exec_privileged "wifi_bounce" "svc wifi disable"; then
        log_warn "Failed to disable Wi-Fi radio"
        step_success=0
    fi

    if [[ "$MOCK_MODE" -eq 0 && "$DRY_RUN" -eq 0 ]]; then
        sleep 2
    fi

    log_info "Enabling Wi-Fi radio..."
    if ! exec_privileged "wifi_bounce" "svc wifi enable"; then
        log_warn "Failed to enable Wi-Fi radio"
        step_success=0
    fi

    EXECUTED_ACTIONS+=("wifi_bounce:$step_success")
    return $(( 1 - step_success ))
}

heal_radio_cellular() {
    log_info "=== [Pathway 2b] Bouncing Cellular Data Interface ==="
    local step_success=1

    log_info "Disabling Cellular data..."
    if ! exec_privileged "cellular_bounce" "svc data disable"; then
        log_warn "Failed to disable Cellular data"
        step_success=0
    fi

    if [[ "$MOCK_MODE" -eq 0 && "$DRY_RUN" -eq 0 ]]; then
        sleep 1
    fi

    log_info "Enabling Cellular data..."
    if ! exec_privileged "cellular_bounce" "svc data enable"; then
        log_warn "Failed to enable Cellular data"
        step_success=0
    fi

    EXECUTED_ACTIONS+=("cellular_bounce:$step_success")
    return $(( 1 - step_success ))
}

# ==============================================================================
# Pathway 3: Wireless ADB Port 5555 Persistence
# ==============================================================================
heal_adb_persistence() {
    log_info "=== [Pathway 3] Enforcing Wireless ADB TCP Port 5555 Persistence ==="
    local step_success=1

    log_info "Setting ADB TCP port property to $ADB_TCP_PORT..."
    if ! exec_privileged "adb_persist" "setprop service.adb.tcp.port $ADB_TCP_PORT"; then
        log_warn "Failed to set ADB TCP port property"
        step_success=0
    fi

    log_info "Restarting adbd daemon..."
    exec_privileged "adb_persist" "stop adbd && start adbd" 2>/dev/null || \
    exec_privileged "adb_persist" "restart adbd" 2>/dev/null || true

    EXECUTED_ACTIONS+=("adb_persist:$step_success")
    return $(( 1 - step_success ))
}

# ==============================================================================
# Pathway 4: Doze Mode Whitelisting & AppOps Grants
# ==============================================================================
heal_doze_whitelisting() {
    log_info "=== [Pathway 4] Whitelisting Core Packages from Android Doze Mode ==="
    local step_success=1

    # 1. DeviceIdle Whitelist
    log_info "Adding packages to deviceidle whitelist..."
    exec_privileged "doze_whitelist" "dumpsys deviceidle whitelist +$TERMUX_PKG +$TAILSCALE_PKG +$TERMUX_BOOT_PKG +$OPENCLAW_PKG" || step_success=0

    # 2. AppOps background execution permissions
    log_info "Granting AppOps background execution rights..."
    exec_privileged "doze_whitelist" "cmd appops set $TERMUX_PKG RUN_IN_BACKGROUND allow" 2>/dev/null || true
    exec_privileged "doze_whitelist" "cmd appops set $TERMUX_PKG RUN_ANY_IN_BACKGROUND allow" 2>/dev/null || true
    exec_privileged "doze_whitelist" "cmd appops set $TAILSCALE_PKG RUN_IN_BACKGROUND allow" 2>/dev/null || true
    exec_privileged "doze_whitelist" "cmd appops set $TAILSCALE_PKG RUN_ANY_IN_BACKGROUND allow" 2>/dev/null || true

    # 3. Termux wake lock reinforcement
    exec_privileged "doze_whitelist" "svc power stayon usb" 2>/dev/null || true

    EXECUTED_ACTIONS+=("doze_whitelist:$step_success")
    return $(( 1 - step_success ))
}

# ==============================================================================
# Pathway 5: Phantom Process Monitor Disablement
# ==============================================================================
heal_phantom_process_bypass() {
    log_info "=== [Pathway 5] Disabling Android Phantom Process Monitor ==="
    local step_success=1

    log_info "Setting settings_enable_monitor_phantom_procs to false..."
    if ! exec_privileged "phantom_bypass" "settings put global settings_enable_monitor_phantom_procs false"; then
        log_warn "Failed to set settings_enable_monitor_phantom_procs"
        step_success=0
    fi

    log_info "Maximizing phantom process limit..."
    exec_privileged "phantom_bypass" "settings put global max_phantom_processes 2147483647" 2>/dev/null || true

    EXECUTED_ACTIONS+=("phantom_bypass:$step_success")
    return $(( 1 - step_success ))
}

# ==============================================================================
# Subsystem Status Inspection
# ==============================================================================
inspect_subsystem_status() {
    log_info "=== Inspecting Shizuku & Android Subsystems Status ==="

    exec_privileged "status_check" "getprop service.adb.tcp.port" || true
    local current_adb_port="$EXEC_OUTPUT"

    exec_privileged "status_check" "settings get global settings_enable_monitor_phantom_procs" || true
    local current_phantom_setting="$EXEC_OUTPUT"

    exec_privileged "status_check" "dumpsys deviceidle whitelist" || true
    local current_doze_whitelist="$EXEC_OUTPUT"

    exec_privileged "status_check" "dumpsys wifi | grep -i 'Wi-Fi is'" || true
    local current_wifi_state="$EXEC_OUTPUT"

    local is_termux_whitelisted=false
    if [[ "$current_doze_whitelist" == *"$TERMUX_PKG"* ]]; then
        is_termux_whitelisted=true
    fi

    local is_tailscale_whitelisted=false
    if [[ "$current_doze_whitelist" == *"$TAILSCALE_PKG"* ]]; then
        is_tailscale_whitelisted=true
    fi

    mkdir -p "$(dirname "$STATUS_FILE")"
    cat << STATUS_JSON > "$STATUS_FILE"
{
  "timestamp": "$(date -u +'%Y-%m-%dT%H:%M:%SZ')",
  "executor": "$EXECUTOR_NAME",
  "adb_tcp_port": "${current_adb_port:-unknown}",
  "phantom_monitor_disabled": $([[ "$current_phantom_setting" == *"false"* ]] && echo "true" || echo "false"),
  "termux_doze_whitelisted": $is_termux_whitelisted,
  "tailscale_doze_whitelisted": $is_tailscale_whitelisted,
  "wifi_status": "${current_wifi_state:-unknown}"
}
STATUS_JSON

    if [[ "$JSON_OUTPUT" -eq 1 ]]; then
        cat "$STATUS_FILE"
    else
        log_info "Executor: $EXECUTOR_NAME"
        log_info "ADB TCP Port: ${current_adb_port:-unknown}"
        log_info "Phantom Process Monitor Disabled: $([[ "$current_phantom_setting" == *"false"* ]] && echo 'YES' || echo 'NO')"
        log_info "Termux Doze Whitelisted: $is_termux_whitelisted"
        log_info "Tailscale Doze Whitelisted: $is_tailscale_whitelisted"
    fi
}

# ==============================================================================
# Main Orchestration
# ==============================================================================
detect_privileged_executor

OVERALL_SUCCESS=1

if [[ "$ACTION_STATUS" -eq 1 ]]; then
    inspect_subsystem_status
    exit 0
fi

if [[ "$ACTION_HEAL_ALL" -eq 1 || "$ACTION_TAILSCALE" -eq 1 ]]; then
    heal_tailscale_daemon || OVERALL_SUCCESS=0
fi

if [[ "$ACTION_HEAL_ALL" -eq 1 || "$ACTION_WIFI" -eq 1 ]]; then
    heal_radio_wifi || OVERALL_SUCCESS=0
fi

if [[ "$ACTION_HEAL_ALL" -eq 1 || "$ACTION_CELLULAR" -eq 1 ]]; then
    heal_radio_cellular || OVERALL_SUCCESS=0
fi

if [[ "$ACTION_HEAL_ALL" -eq 1 || "$ACTION_ADB_PERSIST" -eq 1 ]]; then
    heal_adb_persistence || OVERALL_SUCCESS=0
fi

if [[ "$ACTION_HEAL_ALL" -eq 1 || "$ACTION_DOZE_WHITELIST" -eq 1 ]]; then
    heal_doze_whitelisting || OVERALL_SUCCESS=0
fi

if [[ "$ACTION_HEAL_ALL" -eq 1 || "$ACTION_PHANTOM_BYPASS" -eq 1 ]]; then
    heal_phantom_process_bypass || OVERALL_SUCCESS=0
fi

if [[ "$JSON_OUTPUT" -eq 1 ]]; then
    local_actions_json=""
    if [[ ${#EXECUTED_ACTIONS[@]} -gt 0 ]]; then
        local_actions_json=$(printf '"%s",' "${EXECUTED_ACTIONS[@]}" | sed 's/,$//')
    fi
    cat << JSON_RES
{
  "timestamp": "$(date -u +'%Y-%m-%dT%H:%M:%SZ')",
  "executor": "$EXECUTOR_NAME",
  "overall_success": $([[ $OVERALL_SUCCESS -eq 1 ]] && echo "true" || echo "false"),
  "executed_actions": [${local_actions_json}],
  "lora_dataset_path": "$LORA_DATASET",
  "status_path": "$STATUS_FILE"
}
JSON_RES
else
    log_info "=== Self-Healing Run Complete ==="
    log_info "Overall Success: $([[ $OVERALL_SUCCESS -eq 1 ]] && echo 'YES' || echo 'NO')"
    if [[ ${#EXECUTED_ACTIONS[@]} -gt 0 ]]; then
        log_info "Actions Executed: ${EXECUTED_ACTIONS[*]}"
    else
        log_info "Actions Executed: none"
    fi
fi

if [[ "$OVERALL_SUCCESS" -eq 1 || "$MOCK_MODE" -eq 1 || "$DRY_RUN" -eq 1 ]]; then
    exit 0
else
    exit 1
fi
