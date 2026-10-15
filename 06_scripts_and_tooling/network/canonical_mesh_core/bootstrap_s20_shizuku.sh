#!/usr/bin/env bash
# ==============================================================================
# Canonical Script: bootstrap_s20_shizuku.sh (v3 - Hardened Autonomous Architecture)
# Purpose: Bootstrap and verify Shizuku privileged service on Samsung S20+ (L7)
#          via Host-Native Mac Mini USB ADB with Router & Multi-Transport Fallback.
# Iteration 3 Enhancements:
#   - Phase 1: Interactive & automated --wait polling loop (default 30s, 2s cadence)
#     for seamless Knox screen wake & USB gadget descriptor re-enumeration.
#   - Core: Watchdog timer timing bug resolved (0.2s ticks with sub-second response).
#   - Core: Router SSH commands bounded by run_with_timeout and safe argument quoting.
#   - Core: Prepend mkdir -p /root/.android before router SCP key transfer.
#   - Core: Explicit warning when device is connected via USB in unauthorized state.
#   - Phase 4: Strict Zero-Mock Verification Gate preventing self-certifying bypass
#     (requires physical shizuku_server process in ps -A or verified rish IPC).
# Rule Compliance:
#   - Rule 0 & 1: Zero-Mock Truth & Empirical Tri-Proof Verification
#   - Rule 5: Victory Interceptor Gate & Integrity Verification
#   - Rule 9: Multi-Transport Fallback & Compact Token-Efficient Output
# ==============================================================================

set -euo pipefail

# Configuration with canonical defaults
ROUTER_IP="${ROUTER_IP:-192.168.8.1}"
DEVICE_SERIAL="${DEVICE_SERIAL:-R3CN40CJJ1R}"
DEVICE_WIFI_STATIC_IP="${DEVICE_WIFI_STATIC_IP:-192.168.8.214}"
DEVICE_WIFI_MATRIX_IP="${DEVICE_WIFI_MATRIX_IP:-192.168.8.10}"
DEVICE_TAILSCALE_IP="${DEVICE_TAILSCALE_IP:-10.1.0.14}"
ADB_PORT="${ADB_PORT:-5555}"
BT_MAC="${BT_MAC:-5c-cb-99-05-81-41}"
EXEC_MODE="${EXEC_MODE:-auto}" # auto | host | router
ADB_TIMEOUT="${ADB_TIMEOUT:-10}"
WAIT_TIMEOUT="${WAIT_TIMEOUT:-30}" # seconds to poll in Phase 1 (0 = single-shot)
POLL_INTERVAL=2

# Parse Command-Line Options
while [ $# -gt 0 ]; do
    case "$1" in
        --wait|-w)
            if [ -n "${2:-}" ] && [[ "$2" =~ ^[0-9]+$ ]]; then
                WAIT_TIMEOUT="$2"
                shift 2
            else
                WAIT_TIMEOUT=30
                shift 1
            fi
            ;;
        --no-wait)
            WAIT_TIMEOUT=0
            shift 1
            ;;
        --mode|-m)
            if [ -n "${2:-}" ]; then
                EXEC_MODE="$2"
                shift 2
            else
                echo "Error: --mode requires an argument (auto|host|router)" >&2
                exit 1
            fi
            ;;
        --timeout|-t)
            if [ -n "${2:-}" ] && [[ "$2" =~ ^[0-9]+$ ]]; then
                ADB_TIMEOUT="$2"
                shift 2
            else
                echo "Error: --timeout requires a numeric argument" >&2
                exit 1
            fi
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --wait, -w [SEC]    Wait up to SEC seconds for device to wake/connect (default: 30s)"
            echo "  --no-wait           Do not wait; single-shot probe only (equivalent to --wait 0)"
            echo "  --mode, -m MODE     Execution transport mode: auto | host | router (default: auto)"
            echo "  --timeout, -t SEC   Timeout per individual ADB command (default: 10s)"
            echo "  --help, -h          Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            echo "Run '$0 --help' for usage." >&2
            exit 1
            ;;
    esac
done

# Resolve local binaries
ADB_BIN="${ADB_BIN:-}"
if [ -z "${ADB_BIN}" ]; then
    if [ -x "/Users/aaron/.local/bin/adb" ]; then
        ADB_BIN="/Users/aaron/.local/bin/adb"
    elif command -v adb >/dev/null 2>&1; then
        ADB_BIN="$(command -v adb)"
    else
        ADB_BIN="adb"
    fi
fi

BLUEUTIL_BIN="${BLUEUTIL_BIN:-}"
if [ -z "${BLUEUTIL_BIN}" ]; then
    if [ -x "/Users/aaron/.local/bin/blueutil" ]; then
        BLUEUTIL_BIN="/Users/aaron/.local/bin/blueutil"
    elif command -v blueutil >/dev/null 2>&1; then
        BLUEUTIL_BIN="$(command -v blueutil)"
    fi
fi

# Unified SSH / SCP options for fail-fast safety (polyglot-bash-posix-specialist)
SSH_OPTS=(
    -o BatchMode=yes
    -o ConnectTimeout=5
    -o StrictHostKeyChecking=no
    -o ServerAliveInterval=5
    -o ServerAliveCountMax=2
    -o UserKnownHostsFile=/dev/null
    -o LogLevel=ERROR
)

ssh_cmd() {
    ssh "${SSH_OPTS[@]}" "$@"
}

scp_cmd() {
    scp -O -q "${SSH_OPTS[@]}" "$@"
}

# POSIX-compliant execution with accurate sub-second timeout watchdog
# Fixes Iteration 2 half-time truncation bug by tracking ticks at 0.2s resolution
run_with_timeout() {
    local timeout_sec="$1"
    shift
    "$@" &
    local child_pid=$!
    local ticks=0
    local max_ticks=$((timeout_sec * 5))
    while kill -0 "$child_pid" 2>/dev/null; do
        if [ "$ticks" -ge "$max_ticks" ]; then
            kill -TERM "$child_pid" 2>/dev/null || true
            sleep 0.1
            kill -KILL "$child_pid" 2>/dev/null || true
            wait "$child_pid" 2>/dev/null || true
            return 124
        fi
        sleep 0.2
        ticks=$((ticks + 1))
    done
    wait "$child_pid" 2>/dev/null || return $?
    return $?
}

# Non-blocking TCP port check to prevent hanging adb connect
check_tcp_endpoint() {
    local host="$1"
    local port="${2:-5555}"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        nc -z -G 1 "${host}" "${port}" >/dev/null 2>&1
    else
        nc -z -w 1 "${host}" "${port}" >/dev/null 2>&1
    fi
}

# Secure Temporary Directory with Cleanup Trap
TMP_DIR=""
cleanup() {
    if [ -n "${TMP_DIR:-}" ] && [ -d "${TMP_DIR}" ]; then
        rm -rf "${TMP_DIR}"
    fi
}
trap cleanup EXIT INT TERM

echo "=================================================================="
echo "🚀 BOOTSTRAP SAMSUNG S20+ SHIZUKU (v3 HARDENED MULTI-TRANSPORT)"
echo "Target Device Serial : ${DEVICE_SERIAL}"
echo "Fallback Static IP   : ${DEVICE_WIFI_STATIC_IP}:${ADB_PORT}"
echo "Fallback Matrix IP   : ${DEVICE_WIFI_MATRIX_IP}:${ADB_PORT}"
echo "Fallback Tailscale IP: ${DEVICE_TAILSCALE_IP}:${ADB_PORT}"
echo "Execution Mode       : ${EXEC_MODE}"
echo "Wait Timeout         : ${WAIT_TIMEOUT}s (interval: ${POLL_INTERVAL}s)"
echo "=================================================================="

# Function: Execute ADB command on active target (host-native or router)
ACTIVE_TARGET=""
TRANSPORT_TYPE=""

run_adb() {
    if [ "${TRANSPORT_TYPE}" = "host" ]; then
        run_with_timeout "${ADB_TIMEOUT}" "${ADB_BIN}" -s "${ACTIVE_TARGET}" "$@"
    else
        local quoted_args
        quoted_args=$(printf '%q ' "$@")
        run_with_timeout "${ADB_TIMEOUT}" ssh_cmd "root@${ROUTER_IP}" "adb -s ${ACTIVE_TARGET} ${quoted_args}"
    fi
}

run_adb_shell() {
    local cmd="$1"
    if [ "${TRANSPORT_TYPE}" = "host" ]; then
        run_with_timeout "${ADB_TIMEOUT}" "${ADB_BIN}" -s "${ACTIVE_TARGET}" shell "${cmd}"
    else
        local escaped_cmd="${cmd//\'/\'\\\'\'}"
        run_with_timeout "${ADB_TIMEOUT}" ssh_cmd "root@${ROUTER_IP}" "adb -s ${ACTIVE_TARGET} shell '${escaped_cmd}'"
    fi
}

# ==============================================================================
# PHASE 0: PRE-FLIGHT RADIO WAKE PULSE (BLUETOOTH & WOL)
# ==============================================================================
echo "[0/5] Dispatching pre-flight radio wake pulse (Bluetooth & WoL)..."

# Bluetooth link pulse
if [ -n "${BLUEUTIL_BIN:-}" ] && [ -x "${BLUEUTIL_BIN}" ]; then
    echo "  [WAKE] Dispatching Bluetooth proximity beacon to ${BT_MAC}..."
    ( run_with_timeout 2 "${BLUEUTIL_BIN}" --connect "${BT_MAC}" >/dev/null 2>&1 || true ) || true
fi

# UDP Wake-on-LAN Magic Packet broadcast
python3 -c "
import socket
for mac in ['5c:cb:99:05:81:41', '0a:8f:1b:f1:c8:17']:
    try:
        pkt = b'\xff' * 6 + bytes.fromhex(mac.replace(':', '').replace('-', '')) * 16
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            for bcast in ['192.168.8.255', '255.255.255.255', '169.254.255.255']:
                try:
                    s.sendto(pkt, (bcast, 9))
                    s.sendto(pkt, (bcast, 7))
                except Exception:
                    pass
    except Exception:
        pass
" >/dev/null 2>&1 || true

echo "  [OK] Pre-flight radio wake pulse completed."

# ==============================================================================
# PHASE 1: DISCOVER ACTIVE ADB TRANSPORT (RULE 9 MULTI-TRANSPORT CASCADE)
# ==============================================================================
echo "[1/5] Discovering active ADB transport (Host USB -> Wi-Fi -> Tailscale -> Router)..."
if [ "${WAIT_TIMEOUT}" -gt 0 ]; then
    echo "  [WAIT-MODE] Polling enabled (timeout: ${WAIT_TIMEOUT}s, interval: ${POLL_INTERVAL}s)"
fi

discover_host_transport() {
    local is_quiet="${1:-0}"
    if [ ! -x "${ADB_BIN}" ]; then
        return 1
    fi

    # Ensure local ADB server is running
    "${ADB_BIN}" start-server >/dev/null 2>&1 || true

    # Priority 1: Host Local USB (Direct Mac Mini USB)
    local dev_list
    dev_list=$("${ADB_BIN}" devices 2>/dev/null || true)

    if echo "${dev_list}" | grep -q "${DEVICE_SERIAL}[[:space:]]*device"; then
        ACTIVE_TARGET="${DEVICE_SERIAL}"
        TRANSPORT_TYPE="host"
        echo "  [FOUND] Samsung S20 detected on Host Direct USB: ${ACTIVE_TARGET}"
        return 0
    elif echo "${dev_list}" | grep -q "${DEVICE_SERIAL}[[:space:]]*unauthorized"; then
        echo "  [WARN] Device ${DEVICE_SERIAL} detected on Host USB but UNAUTHORIZED. Confirm RSA prompt on screen!" >&2
    fi

    # Priority 2: Host Local Wi-Fi (Static Lease)
    if [ "${is_quiet}" -eq 0 ]; then
        echo "  [PROBE] Probing Wi-Fi static lease ${DEVICE_WIFI_STATIC_IP}:${ADB_PORT}..."
    fi
    if check_tcp_endpoint "${DEVICE_WIFI_STATIC_IP}" "${ADB_PORT}"; then
        if run_with_timeout "${ADB_TIMEOUT}" "${ADB_BIN}" connect "${DEVICE_WIFI_STATIC_IP}:${ADB_PORT}" 2>/dev/null | grep -iE 'connected|already'; then
            if "${ADB_BIN}" devices | grep -q "${DEVICE_WIFI_STATIC_IP}:${ADB_PORT}[[:space:]]*device"; then
                ACTIVE_TARGET="${DEVICE_WIFI_STATIC_IP}:${ADB_PORT}"
                TRANSPORT_TYPE="host"
                echo "  [FOUND] Samsung S20 connected via Wi-Fi Static Lease: ${ACTIVE_TARGET}"
                return 0
            fi
        fi
    fi

    # Priority 3: Host Local Wi-Fi (Matrix IP)
    if [ "${is_quiet}" -eq 0 ]; then
        echo "  [PROBE] Probing Wi-Fi matrix endpoint ${DEVICE_WIFI_MATRIX_IP}:${ADB_PORT}..."
    fi
    if check_tcp_endpoint "${DEVICE_WIFI_MATRIX_IP}" "${ADB_PORT}"; then
        if run_with_timeout "${ADB_TIMEOUT}" "${ADB_BIN}" connect "${DEVICE_WIFI_MATRIX_IP}:${ADB_PORT}" 2>/dev/null | grep -iE 'connected|already'; then
            if "${ADB_BIN}" devices | grep -q "${DEVICE_WIFI_MATRIX_IP}:${ADB_PORT}[[:space:]]*device"; then
                ACTIVE_TARGET="${DEVICE_WIFI_MATRIX_IP}:${ADB_PORT}"
                TRANSPORT_TYPE="host"
                echo "  [FOUND] Samsung S20 connected via Wi-Fi Matrix: ${ACTIVE_TARGET}"
                return 0
            fi
        fi
    fi

    # Priority 4: Host Local Tailscale
    if [ "${is_quiet}" -eq 0 ]; then
        echo "  [PROBE] Probing Tailscale endpoint ${DEVICE_TAILSCALE_IP}:${ADB_PORT}..."
    fi
    if check_tcp_endpoint "${DEVICE_TAILSCALE_IP}" "${ADB_PORT}"; then
        if run_with_timeout "${ADB_TIMEOUT}" "${ADB_BIN}" connect "${DEVICE_TAILSCALE_IP}:${ADB_PORT}" 2>/dev/null | grep -iE 'connected|already'; then
            if "${ADB_BIN}" devices | grep -q "${DEVICE_TAILSCALE_IP}:${ADB_PORT}[[:space:]]*device"; then
                ACTIVE_TARGET="${DEVICE_TAILSCALE_IP}:${ADB_PORT}"
                TRANSPORT_TYPE="host"
                echo "  [FOUND] Samsung S20 connected via Tailscale: ${ACTIVE_TARGET}"
                return 0
            fi
        fi
    fi

    return 1
}

ROUTER_SETUP_DONE=0
discover_router_transport() {
    local is_quiet="${1:-0}"

    # Verify router SSH accessibility first
    if ! run_with_timeout 5 ssh_cmd "root@${ROUTER_IP}" "uname -a" >/dev/null 2>&1; then
        if [ "${is_quiet}" -eq 0 ]; then
            echo "  [WARN] Router at ${ROUTER_IP} unreachable via SSH."
        fi
        return 1
    fi

    # Ensure router has valid PKCS#1 ADB keys (run once per session)
    if [ "${ROUTER_SETUP_DONE}" -eq 0 ] && [ -f "$HOME/.android/adbkey" ]; then
        TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/s20_shizuku.XXXXXX")"
        chmod 700 "${TMP_DIR}"
        TMP_KEY="${TMP_DIR}/adbkey_pkcs1"

        if openssl rsa -in "$HOME/.android/adbkey" -traditional > "${TMP_KEY}" 2>/dev/null; then
            if grep -q "BEGIN RSA PRIVATE KEY" "${TMP_KEY}"; then
                chmod 600 "${TMP_KEY}"
                run_with_timeout 5 ssh_cmd "root@${ROUTER_IP}" "mkdir -p /root/.android"
                scp_cmd "${TMP_KEY}" "root@${ROUTER_IP}:/root/.android/adbkey"
                scp_cmd "$HOME/.android/adbkey.pub" "root@${ROUTER_IP}:/root/.android/adbkey.pub"
                run_with_timeout 5 ssh_cmd "root@${ROUTER_IP}" "chmod 600 /root/.android/adbkey && chmod 644 /root/.android/adbkey.pub"
            fi
        fi
        ROUTER_SETUP_DONE=1
    fi

    # Check router USB ADB
    local r_state
    r_state=$(run_with_timeout "${ADB_TIMEOUT}" ssh_cmd "root@${ROUTER_IP}" "adb -s ${DEVICE_SERIAL} get-state 2>/dev/null || echo 'unknown'")
    if [ "${r_state}" = "device" ]; then
        ACTIVE_TARGET="${DEVICE_SERIAL}"
        TRANSPORT_TYPE="router"
        echo "  [FOUND] Samsung S20 detected on Router USB: ${ACTIVE_TARGET}"
        return 0
    fi

    # Dynamic USB bus discovery on router (first pass only, NEVER unbind xhci-mtk)
    if [ "${is_quiet}" -eq 0 ]; then
        echo "  [INFO] Attempting dynamic USB discovery & safe power cycling on router..."
        run_with_timeout 10 ssh_cmd "root@${ROUTER_IP}" "
            for auth in /sys/bus/usb/devices/*/authorized; do
                if [ -f \"\$auth\" ]; then
                    echo 1 > \"\$auth\" 2>/dev/null || true
                fi
            done
            if [ -f /sys/class/gpio/usb_power/value ]; then
                echo 0 > /sys/class/gpio/usb_power/value
                sleep 1
                echo 1 > /sys/class/gpio/usb_power/value
                sleep 2
            fi
            adb kill-server 2>/dev/null || true
            sleep 1
            adb start-server 2>/dev/null || true
        " >/dev/null 2>&1 || true

        r_state=$(run_with_timeout "${ADB_TIMEOUT}" ssh_cmd "root@${ROUTER_IP}" "adb -s ${DEVICE_SERIAL} get-state 2>/dev/null || echo 'unknown'")
        if [ "${r_state}" = "device" ]; then
            ACTIVE_TARGET="${DEVICE_SERIAL}"
            TRANSPORT_TYPE="router"
            echo "  [FOUND] Samsung S20 recovered on Router USB: ${ACTIVE_TARGET}"
            return 0
        fi
    fi

    # Router network fallback (Wi-Fi static lease & matrix)
    for net_ip in "${DEVICE_WIFI_STATIC_IP}" "${DEVICE_WIFI_MATRIX_IP}"; do
        if run_with_timeout 5 ssh_cmd "root@${ROUTER_IP}" "nc -z -w 2 ${net_ip} ${ADB_PORT} 2>/dev/null && adb connect ${net_ip}:${ADB_PORT} 2>/dev/null | grep -iE 'connected|already'"; then
            r_state=$(run_with_timeout "${ADB_TIMEOUT}" ssh_cmd "root@${ROUTER_IP}" "adb -s ${net_ip}:${ADB_PORT} get-state 2>/dev/null || echo 'unknown'")
            if [ "${r_state}" = "device" ]; then
                ACTIVE_TARGET="${net_ip}:${ADB_PORT}"
                TRANSPORT_TYPE="router"
                echo "  [FOUND] Samsung S20 connected via Router Wi-Fi: ${ACTIVE_TARGET}"
                return 0
            fi
        fi
    done

    return 1
}

# Execute discovery cascade with polling loop
poll_start_time=$(date +%s)
attempt=0

while true; do
    attempt=$((attempt + 1))
    quiet_flag=0
    if [ "${attempt}" -gt 1 ]; then
        quiet_flag=1
    fi

    case "${EXEC_MODE}" in
        host)
            discover_host_transport "${quiet_flag}" || true
            ;;
        router)
            discover_router_transport "${quiet_flag}" || true
            ;;
        auto|*)
            if ! discover_host_transport "${quiet_flag}"; then
                if [ "${attempt}" -eq 1 ]; then
                    echo "  [INFO] Host transport not detected; probing Router discovery..."
                fi
                discover_router_transport "${quiet_flag}" || true
            fi
            ;;
    esac

    # If transport captured, exit loop
    if [ -n "${ACTIVE_TARGET}" ] && [ -n "${TRANSPORT_TYPE}" ]; then
        break
    fi

    # Check timeout condition
    now=$(date +%s)
    elapsed_wait=$((now - poll_start_time))
    if [ "${elapsed_wait}" -ge "${WAIT_TIMEOUT}" ]; then
        break
    fi

    remaining=$((WAIT_TIMEOUT - elapsed_wait))
    echo "  [WAIT] Device not detected yet (${elapsed_wait}s/${WAIT_TIMEOUT}s elapsed). Touch screen or press power to wake Knox USB..."

    # Nudge Bluetooth connection every ~10 seconds
    if [ $((elapsed_wait % 10)) -lt "${POLL_INTERVAL}" ] && [ -n "${BLUEUTIL_BIN:-}" ] && [ -x "${BLUEUTIL_BIN}" ]; then
        run_with_timeout 2 "${BLUEUTIL_BIN}" --connect "${BT_MAC}" >/dev/null 2>&1 || true
    fi

    sleep "${POLL_INTERVAL}"
done

# Validate transport selection
if [ -z "${ACTIVE_TARGET}" ] || [ -z "${TRANSPORT_TYPE}" ]; then
    echo "" >&2
    echo "  [ERROR] No active ADB transport found across Host USB, Wi-Fi, Tailscale, or Router after ${WAIT_TIMEOUT}s." >&2
    echo "  [DIAGNOSTIC] Samsung Galaxy S20 (L7) was not detected:" >&2
    echo "    1. Knox USB Lockout: The screen is sleeping with USB data descriptors suspended." >&2
    echo "       Action: Touch the phone screen or press the power button to wake the display." >&2
    echo "    2. Host USB Cable: Ensure the USB-C cable is connected directly to the Mac Mini host." >&2
    echo "    3. Developer Options: Verify USB Debugging is turned ON in Settings -> Developer options." >&2
    echo "    4. Authorization: Check the phone screen for an 'Allow USB debugging?' RSA prompt." >&2
    echo "  [HINT] Re-run with '--wait 60' to extend the wake-up window." >&2
    exit 1
fi

echo "  [OK] Transport established: Type=${TRANSPORT_TYPE} | Target=${ACTIVE_TARGET}"

# ==============================================================================
# PHASE 2: VERIFY DEVICE STATE & WAKE SCREEN
# ==============================================================================
echo "[2/5] Verifying target device authorization state & waking screen..."
DEV_STATE=$(run_adb get-state 2>/dev/null || echo "unknown")
if [ "${DEV_STATE}" != "device" ]; then
    echo "  [ERROR] Target ${ACTIVE_TARGET} state is '${DEV_STATE}' (expected 'device')" >&2
    if [ "${DEV_STATE}" = "unauthorized" ]; then
        echo "  [ACTION REQUIRED] Please tap 'Allow' on the Samsung S20 screen to authorize this host." >&2
    fi
    exit 1
fi
echo "  [OK] Device state confirmed: 'device'"

# Pre-flight screen wake and permanent sleep prevention
run_adb_shell "
    input keyevent 224 >/dev/null 2>&1 || true
    wm dismiss-keyguard >/dev/null 2>&1 || true
    svc power stayon true >/dev/null 2>&1 || true
    settings put global stay_on_while_plugged_in 3 >/dev/null 2>&1 || true
    settings put system screen_off_timeout 2147483647 >/dev/null 2>&1 || true
"
echo "  [OK] Screen awakened, keyguard dismissed, stay-on while plugged in enforced."

# ==============================================================================
# PHASE 3: BOOTSTRAP SHIZUKU PRIVILEGED SERVICE
# ==============================================================================
echo "[3/5] Bootstrapping Shizuku privileged API service..."
START_CMD="sh /sdcard/Android/data/moe.shizuku.privileged.api/start.sh || sh /storage/emulated/0/Android/data/moe.shizuku.privileged.api/start.sh || sh /sdcard/Android/data/moe.shizuku.privileged.api/files/start.sh"

START_OUTPUT=$(run_adb_shell "${START_CMD}" 2>&1 || true)
echo "${START_OUTPUT}"

STARTER_CONFIRMED=0
if echo "${START_OUTPUT}" | grep -qiE "starter exit with 0|shizuku_starter exit with 0|already running|shizuku_server verified running"; then
    echo "  [OK] Shizuku starter execution confirmed (Exit Code 0 / service active)."
    STARTER_CONFIRMED=1
else
    echo "  [INFO] Starter did not output explicit completion token; checking process table..."
    sleep 2
fi

# ==============================================================================
# PHASE 4: STRICT ZERO-MOCK VERIFICATION GATE (ACCEPTANCE CRITERIA)
# ==============================================================================
echo "[4/5] Verifying privileged execution & Shizuku process status..."

# Verification 4.1: Physical Process Inspection (ps -A)
echo "--- Verification 4.1: Checking shizuku_server process in ps -A ---"
PS_VERIFIED=0
PS_OUTPUT=""
for i in 1 2 3 4 5; do
    PS_OUTPUT=$(run_adb_shell "ps -A | grep [s]hizuku_server || true" 2>/dev/null || true)
    if [ -n "${PS_OUTPUT}" ]; then
        echo "  [FOUND] ${PS_OUTPUT}"
        PS_VERIFIED=1
        break
    fi
    sleep 1
done

if [ ${PS_VERIFIED} -eq 1 ]; then
    echo "  [OK] shizuku_server process verified active in process table."
else
    echo "  [WARN] shizuku_server not detected in ps -A after 5 attempts."
fi

# Verification 4.2: Privileged Client & Identity Check (rish vs adb shell id)
echo "--- Verification 4.2: Privileged Shell Identity Verification ---"
RISH_VERIFIED=0
RISH_OUT=""

for rish_path in "/data/local/tmp/rish_dir/rish" "/data/local/tmp/rish"; do
    if run_adb_shell "[ -x ${rish_path} ]" 2>/dev/null; then
        echo "  [PROBE] Executing privileged identity check via ${rish_path}..."
        RISH_OUT=$(run_adb_shell "${rish_path} -c id" 2>/dev/null || true)
        if echo "${RISH_OUT}" | grep -q "uid=2000(shell)"; then
            echo "  [OK] rish verified privileged execution: ${RISH_OUT}"
            RISH_VERIFIED=1
            break
        else
            echo "  [WARN] rish at ${rish_path} returned: ${RISH_OUT}"
        fi
    fi
done

# Verification 4.3: ServiceManager Binder Registration Check
echo "--- Verification 4.3: ServiceManager Binder Registration ---"
SM_CHECK=$(run_adb_shell "service check moe.shizuku.privileged.api.service 2>&1" 2>/dev/null || true)
echo "  ServiceManager check: ${SM_CHECK}"
SM_FOUND=0
if echo "${SM_CHECK}" | grep -iE ": found\$|status: 0|is running" | grep -vqi "not found"; then
    SM_FOUND=1
fi

# STRICT INTEGRITY GATE ENFORCEMENT
# Rule 1 & Rule 5 Invariant:
# Under NO circumstances may standard adb shell id alone certify Shizuku if
# shizuku_server is NOT running and rish is absent/failing.
echo "--- Integrity Gate Evaluation ---"
echo "  - Starter Status       : $([ ${STARTER_CONFIRMED} -eq 1 ] && echo 'CONFIRMED' || echo 'NOT EXPLICIT')"
echo "  - Process (ps -A)      : $([ ${PS_VERIFIED} -eq 1 ] && echo 'PASS (running)' || echo 'NOT FOUND')"
echo "  - rish Binder IPC      : $([ ${RISH_VERIFIED} -eq 1 ] && echo 'PASS (uid=2000)' || echo 'NOT DETECTED')"
echo "  - ServiceManager       : $([ ${SM_FOUND} -eq 1 ] && echo 'PASS (registered)' || echo 'UNKNOWN')"

GATE_PASSED=0

if [ ${RISH_VERIFIED} -eq 1 ]; then
    # Tier 1 (Gold Standard): rish Binder IPC executed and confirmed UID 2000
    GATE_PASSED=1
    echo "  [GATE PASS] Full Shizuku Binder IPC confirmed via rish (uid=2000)."
elif [ ${PS_VERIFIED} -eq 1 ] || [ ${SM_FOUND} -eq 1 ]; then
    # Tier 2 (Silver Standard): shizuku_server verified active on OS, verify UID 2000
    ADB_ID_OUT=$(run_adb_shell "id" 2>/dev/null || true)
    echo "  Identity Output: ${ADB_ID_OUT}"
    if echo "${ADB_ID_OUT}" | grep -q "uid=2000(shell)"; then
        GATE_PASSED=1
        echo "  [GATE PASS] Shizuku server active on OS and shell UID 2000 confirmed."
    else
        echo "  [ERROR] Shell process did not return uid=2000: ${ADB_ID_OUT}" >&2
    fi
else
    # Tier 3 (Integrity Rejection): Neither rish nor shizuku_server in ps -A
    echo "" >&2
    echo "  [GATE FAIL] Shizuku privileged service is NOT running on device." >&2
    echo "  [ERROR] Self-certifying fallback rejected: vanilla adb shell id cannot certify a missing Shizuku service." >&2
    echo "  [DIAGNOSTIC] Shizuku starter output:" >&2
    echo "${START_OUTPUT}" >&2
    exit 1
fi

if [ ${GATE_PASSED} -ne 1 ]; then
    echo "  [ERROR] Acceptance Criteria verification failed." >&2
    exit 1
fi

# ==============================================================================
# PHASE 5: PERSISTENCE & ANTI-DOZE ENFORCEMENT
# ==============================================================================
echo "[5/5] Enforcing mesh persistence & anti-doze whitelisting..."

# Enable wireless debugging port 5555 for zero-touch wireless survival
run_adb tcpip "${ADB_PORT}" >/dev/null 2>&1 || true

# Whitelist mesh components from Android battery saver / doze mode
run_adb_shell "
    dumpsys deviceidle whitelist +moe.shizuku.privileged.api >/dev/null 2>&1 || true
    dumpsys deviceidle whitelist +com.termux >/dev/null 2>&1 || true
    dumpsys deviceidle whitelist +com.tailscale.ipn >/dev/null 2>&1 || true
    cmd appops set moe.shizuku.privileged.api RUN_IN_BACKGROUND allow >/dev/null 2>&1 || true
    cmd appops set com.termux RUN_IN_BACKGROUND allow >/dev/null 2>&1 || true
"

echo "  [OK] Anti-doze whitelisting and TCP/IP port ${ADB_PORT} armed."

echo "=================================================================="
echo "✅ SAMSUNG S20+ SHIZUKU BOOTSTRAP COMPLETE (EXIT CODE 0)"
echo "Transport: ${TRANSPORT_TYPE} (${ACTIVE_TARGET}) | Privileged UID: 2000"
echo "=================================================================="
exit 0
