#!/usr/bin/env bash
# ==============================================================================
# connect_l1b.sh — Connect Screen Sharing (VNC) to Mac Mini M2 Pro (L1b)
#
# Interfaces:
#   1. Thunderbolt Bridge: 10.0.0.3 (40 Gb/s, ~0.48 ms RTT) - Highest Priority
#   2. Local Wi-Fi / LAN:  192.168.8.114 (~5.0 ms RTT)       - Primary Fallback
#   3. Tailscale Mesh:     100.104.128.34                    - Remote Fallback
#
# Usage:
#   ./connect_l1b.sh          # Auto-select fastest available interface & connect
#   ./connect_l1b.sh --lan    # Force connect via LAN (192.168.8.114)
#   ./connect_l1b.sh --tb     # Force connect via Thunderbolt (10.0.0.3)
#   ./connect_l1b.sh --ts     # Force connect via Tailscale (100.104.128.34)
#   ./connect_l1b.sh --check  # Probe all interfaces without launching UI
#   ./connect_l1b.sh --wake   # Send WOL packet before connecting
# ==============================================================================

set -euo pipefail

# --- Targets & Configuration ---
TB_IP="10.0.0.3"
LAN_IP="192.168.8.114"
TS_IP="100.104.128.34"
MAC_ADDR="00:c5:85:05:6d:2c"
VNC_PORT=5900
DEFAULT_USER=""

# --- ANSI Formatting ---
BOLD='\033[1m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}ℹ [L1b-Connect]${NC} $*"; }
log_ok()   { echo -e "${GREEN}✓ [L1b-Connect]${NC} $*"; }
log_warn() { echo -e "${YELLOW}⚠ [L1b-Connect]${NC} $*"; }
log_err()  { echo -e "${RED}✗ [L1b-Connect]${NC} $*"; }

check_vnc_port() {
    local ip="$1"
    local timeout="${2:-1}"
    nc -z -G "${timeout}" "${ip}" "${VNC_PORT}" >/dev/null 2>&1
}

ping_latency() {
    local ip="$1"
    local rtt
    rtt=$(ping -c 1 -W 1000 "${ip}" 2>/dev/null | awk -F'/' 'END { if ($5 != "") printf "%.2f ms", $5 }')
    echo "${rtt:-N/A}"
}

send_wake() {
    log_info "Sending Wake-on-LAN magic packet to ${MAC_ADDR}..."
    if command -v wakeonlan >/dev/null 2>&1; then
        wakeonlan "${MAC_ADDR}" >/dev/null 2>&1 || true
    elif command -v /opt/homebrew/bin/wakeonlan >/dev/null 2>&1; then
        /opt/homebrew/bin/wakeonlan "${MAC_ADDR}" >/dev/null 2>&1 || true
    else
        python3 -c "
import socket
mac = bytes.fromhex('${MAC_ADDR}'.replace(':', ''))
payload = b'\xff' * 6 + mac * 16
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
s.sendto(payload, ('255.255.255.255', 9))
" >/dev/null 2>&1 || true
    fi
    ping -c 2 -W 1000 "${TB_IP}" >/dev/null 2>&1 || true
    ping -c 2 -W 1000 "${LAN_IP}" >/dev/null 2>&1 || true
    sleep 2
}

run_diagnostics() {
    echo -e "${BOLD}========================================${NC}"
    echo -e "${BOLD} L1b (Mac Mini M2 Pro) Connectivity Probe${NC}"
    echo -e "${BOLD}========================================${NC}"
    
    # Thunderbolt
    local tb_rtt
    tb_rtt=$(ping_latency "${TB_IP}")
    if check_vnc_port "${TB_IP}" 1; then
        echo -e "Thunderbolt (${TB_IP}):  ${GREEN}ONLINE${NC} (RTT: ${tb_rtt}, Port 5900 OPEN) [40 Gbps Link]"
    else
        echo -e "Thunderbolt (${TB_IP}):  ${RED}OFFLINE${NC} (RTT: ${tb_rtt}, Port 5900 closed/unreachable)"
    fi

    # LAN Wi-Fi
    local lan_rtt
    lan_rtt=$(ping_latency "${LAN_IP}")
    if check_vnc_port "${LAN_IP}" 1; then
        echo -e "LAN Wi-Fi   (${LAN_IP}):  ${GREEN}ONLINE${NC} (RTT: ${lan_rtt}, Port 5900 OPEN)"
    else
        echo -e "LAN Wi-Fi   (${LAN_IP}):  ${RED}OFFLINE${NC} (RTT: ${lan_rtt}, Port 5900 closed/unreachable)"
    fi

    # Tailscale
    local ts_rtt
    ts_rtt=$(ping_latency "${TS_IP}")
    if check_vnc_port "${TS_IP}" 1; then
        echo -e "Tailscale   (${TS_IP}): ${GREEN}ONLINE${NC} (RTT: ${ts_rtt}, Port 5900 OPEN)"
    else
        echo -e "Tailscale   (${TS_IP}): ${YELLOW}OFFLINE / ASLEEP${NC} (RTT: ${ts_rtt})"
    fi
    echo -e "${BOLD}========================================${NC}"
}

open_vnc() {
    local target_ip="$1"
    local desc="$2"
    local url

    if [[ -n "${DEFAULT_USER}" ]]; then
        url="vnc://${DEFAULT_USER}@${target_ip}"
    else
        url="vnc://${target_ip}"
    fi

    log_ok "Connecting via ${desc}: ${BOLD}${url}${NC}"
    open "${url}"
}

# --- CLI Argument Parsing ---
MODE="auto"
DO_WAKE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --tb|--thunderbolt)
            MODE="tb"
            shift
            ;;
        --lan)
            MODE="lan"
            shift
            ;;
        --ts|--tailscale)
            MODE="ts"
            shift
            ;;
        --check|--diag)
            MODE="check"
            shift
            ;;
        --wake)
            DO_WAKE=true
            shift
            ;;
        -u|--user)
            DEFAULT_USER="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [--auto|--tb|--lan|--ts|--check] [--wake] [-u username]"
            echo ""
            echo "Options:"
            echo "  --auto    Auto-select lowest latency link (Thunderbolt > LAN) (default)"
            echo "  --lan     Connect explicitly via LAN IP (${LAN_IP})"
            echo "  --tb      Connect explicitly via Thunderbolt IP (${TB_IP})"
            echo "  --ts      Connect explicitly via Tailscale IP (${TS_IP})"
            echo "  --check   Probe reachability and display port diagnostics"
            echo "  --wake    Send Wake-on-LAN packet prior to connecting"
            echo "  -u, --user Prefill username for Screen Sharing session"
            exit 0
            ;;
        *)
            log_err "Unknown argument: $1. Use --help for usage."
            exit 1
            ;;
    esac
done

if [[ "${DO_WAKE}" == true ]]; then
    send_wake
fi

if [[ "${MODE}" == "check" ]]; then
    run_diagnostics
    exit 0
fi

if [[ "${MODE}" == "tb" ]]; then
    if ! check_vnc_port "${TB_IP}" 1; then
        log_warn "Thunderbolt (${TB_IP}:5900) not responding. Trying wake..."
        send_wake
    fi
    if check_vnc_port "${TB_IP}" 2; then
        open_vnc "${TB_IP}" "Thunderbolt 4 Bridge"
    else
        log_err "Cannot connect to Thunderbolt interface (${TB_IP}:5900)."
        exit 1
    fi
    exit 0
fi

if [[ "${MODE}" == "lan" ]]; then
    if ! check_vnc_port "${LAN_IP}" 1; then
        log_warn "LAN (${LAN_IP}:5900) not responding. Trying wake..."
        send_wake
    fi
    if check_vnc_port "${LAN_IP}" 2; then
        open_vnc "${LAN_IP}" "Local Area Network"
    else
        log_err "Cannot connect to LAN interface (${LAN_IP}:5900)."
        exit 1
    fi
    exit 0
fi

if [[ "${MODE}" == "ts" ]]; then
    if check_vnc_port "${TS_IP}" 2; then
        open_vnc "${TS_IP}" "Tailscale Overlay"
    else
        log_err "Cannot connect to Tailscale interface (${TS_IP}:5900). Machine may be asleep or logged out of Tailscale."
        exit 1
    fi
    exit 0
fi

# --- Default Mode: Auto-Discovery ---
log_info "Auto-detecting best route to L1b..."

# 1. Thunderbolt First (Fastest: ~0.48ms, 40Gbps)
if check_vnc_port "${TB_IP}" 1; then
    rtt=$(ping_latency "${TB_IP}")
    log_ok "Thunderbolt link active (RTT: ${rtt}, 40 Gb/s)."
    open_vnc "${TB_IP}" "Thunderbolt 4 Bridge"
    exit 0
fi

# 2. LAN Wi-Fi Fallback (~5ms)
if check_vnc_port "${LAN_IP}" 1; then
    rtt=$(ping_latency "${LAN_IP}")
    log_ok "LAN Wi-Fi link active (RTT: ${rtt})."
    open_vnc "${LAN_IP}" "Local Area Network"
    exit 0
fi

# 3. If neither responded, attempt wake and retry
log_warn "L1b appears asleep or unresponsive. Attempting wake sequence..."
send_wake

if check_vnc_port "${TB_IP}" 2; then
    open_vnc "${TB_IP}" "Thunderbolt 4 Bridge (woken)"
    exit 0
fi

if check_vnc_port "${LAN_IP}" 2; then
    open_vnc "${LAN_IP}" "Local Area Network (woken)"
    exit 0
fi

log_err "Failed to reach L1b on Thunderbolt (${TB_IP}) and LAN (${LAN_IP})."
log_info "Run with '--check' to inspect link status."
exit 1
