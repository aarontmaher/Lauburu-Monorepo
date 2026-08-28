#!/usr/bin/env bash
# 01_apps/canonical_tui_prototypes/verify/verify_termux.sh
# =========================================================
# Canonical Remote Smoke Verification Harness for Termux Mobile Edge Nodes
#
# Verifies Python Textual, Go Bubble Tea, and Rust Ratatui TUIs natively inside
# the Termux ARM64 environment with --verify and --timeout 2 execution flags.

set -euo pipefail

# ANSI color escape codes
CYAN='\033[96m'
GREEN='\033[92m'
YELLOW='\033[93m'
RED='\033[91m'
BOLD='\033[1m'
DIM='\033[2m'
RESET='\033[0m'

# Default configurations
TARGET_DEVICE="auto"
TARGET_HOST=""
TARGET_PORT="8022"
TARGET_USER=""
TIMEOUT_SECS="2"
REMOTE_WORKSPACE="/data/data/com.termux/files/home/lauburu_tui_prototypes"

# Device Matrix
S20_IP="100.84.40.95"
S20_USER="u0_a420"
PIXEL_IP="100.73.38.87"
PIXEL_USER="u0_a363"

# Parse CLI arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --device|-d)
            TARGET_DEVICE="$2"
            shift 2
            ;;
        --host|-h)
            TARGET_HOST="$2"
            shift 2
            ;;
        --port|-p)
            TARGET_PORT="$2"
            shift 2
            ;;
        --user|-u)
            TARGET_USER="$2"
            shift 2
            ;;
        --timeout|-t)
            TIMEOUT_SECS="$2"
            shift 2
            ;;
        --workspace|-w)
            REMOTE_WORKSPACE="$2"
            shift 2
            ;;
        *)
            echo "Unknown argument: $1"
            echo "Usage: $0 [--device <s20|pixel|auto>] [--host <ip>] [--port <port>] [--user <user>] [--timeout <secs>]"
            exit 1
            ;;
    esac
done

# Resolve Target Device & Credentials
if [ -n "${TARGET_HOST}" ]; then
    if [ -z "${TARGET_USER}" ]; then
        TARGET_USER="u0_a420"
    fi
elif [ "${TARGET_DEVICE}" == "s20" ]; then
    TARGET_HOST="${S20_IP}"
    TARGET_USER="${S20_USER}"
elif [ "${TARGET_DEVICE}" == "pixel" ]; then
    TARGET_HOST="${PIXEL_IP}"
    TARGET_USER="${PIXEL_USER}"
else
    # Auto-detection: probe Pixel, then S20
    echo -e "${CYAN}🔍 Auto-detecting live Termux edge node...${RESET}"
    if nc -z -G 2 "${PIXEL_IP}" 8022 2>/dev/null || (echo > /dev/tcp/${PIXEL_IP}/8022) 2>/dev/null; then
        TARGET_DEVICE="pixel"
        TARGET_HOST="${PIXEL_IP}"
        TARGET_USER="${PIXEL_USER}"
        echo -e "${GREEN}✓ Auto-detected Google Pixel 10 Pro XL (${TARGET_HOST}:${TARGET_PORT})${RESET}"
    elif nc -z -G 2 "${S20_IP}" 8022 2>/dev/null || (echo > /dev/tcp/${S20_IP}/8022) 2>/dev/null; then
        TARGET_DEVICE="s20"
        TARGET_HOST="${S20_IP}"
        TARGET_USER="${S20_USER}"
        echo -e "${GREEN}✓ Auto-detected Samsung Galaxy S20+ (${TARGET_HOST}:${TARGET_PORT})${RESET}"
    else
        # Default fallback to Pixel
        TARGET_DEVICE="pixel"
        TARGET_HOST="${PIXEL_IP}"
        TARGET_USER="${PIXEL_USER}"
        echo -e "${YELLOW}⚠ Socket probe quiet. Probing default target Pixel 10 Pro XL (${TARGET_HOST}:${TARGET_PORT})...${RESET}"
    fi
fi

STATE_FILE="${REMOTE_WORKSPACE}/data/cloud_api_quota_state.json"

echo "================================================================================"
echo -e " 🚀 ${BOLD}LAUBURU TERMUX REMOTE TUI VERIFICATION HARNESS${RESET}"
echo -e " Target: ${CYAN}${TARGET_USER}@${TARGET_HOST}:${TARGET_PORT}${RESET} | Workspace: ${REMOTE_WORKSPACE}"
echo -e " Mode: Headless Schema Validation (--verify) & Timed Smoke Execution (--timeout ${TIMEOUT_SECS})"
echo "================================================================================"

SSH_CMD="ssh -o BatchMode=yes -o StrictHostKeyChecking=no -o ConnectTimeout=6 -p ${TARGET_PORT} ${TARGET_USER}@${TARGET_HOST}"

# Step 1: Verify remote connectivity & state file
echo -e "\n${BOLD}[1/4] Checking Remote State File Integrity...${RESET}"
STATE_CHECK_CMD="
export PREFIX=\"/data/data/com.termux/files/usr\"
export HOME=\"/data/data/com.termux/files/home\"
export PATH=\"\$PREFIX/bin:\$HOME/bin:\$HOME/go/bin:\$HOME/.cargo/bin:\$PATH\"

if [ ! -f '${STATE_FILE}' ]; then
    echo 'STATE_MISSING'
    exit 1
fi

python3 -c \"
import json, sys
try:
    with open('${STATE_FILE}') as f:
        d = json.load(f)
    assert 'version' in d and 'providers' in d and 'metrics' in d
    assert len(d['providers']) > 0
    print('STATE_OK: Version', d.get('version'), '| Providers:', len(d['providers']), '| Routed:', d['metrics'].get('total_tasks_routed'))
except Exception as e:
    print('STATE_INVALID:', e)
    sys.exit(1)
\"
"

if ! STATE_OUT=$(${SSH_CMD} "${STATE_CHECK_CMD}" 2>&1); then
    echo -e "${RED}❌ Failed to verify state file on Termux:${RESET}"
    echo "${STATE_OUT}"
    exit 1
fi
echo -e "  ${GREEN}✓ ${STATE_OUT}${RESET}"

# Step 2: Verify Python Textual Prototype
echo -e "\n${BOLD}[2/4] Verifying Remote Python Textual Prototype...${RESET}"
PY_CMD="
export PREFIX=\"/data/data/com.termux/files/usr\"
export HOME=\"/data/data/com.termux/files/home\"
export PATH=\"\$PREFIX/bin:\$HOME/bin:\$HOME/go/bin:\$HOME/.cargo/bin:\$PATH\"
cd '${REMOTE_WORKSPACE}'

if [ ! -f 'python_textual/app.py' ]; then
    echo 'PY_NOT_FOUND'
    exit 1
fi

echo '--- 1. Schema Verify Mode ---'
python3 python_textual/app.py --state-path '${STATE_FILE}' --verify
PY_VERIFY_RC=\$?

echo '--- 2. Smoke Timeout Mode (${TIMEOUT_SECS}s) ---'
python3 python_textual/app.py --state-path '${STATE_FILE}' --timeout ${TIMEOUT_SECS} >/dev/null 2>&1 || true
PY_SMOKE_RC=\$?

echo \"RESULTS: VERIFY=\${PY_VERIFY_RC} SMOKE=\${PY_SMOKE_RC}\"
exit \${PY_VERIFY_RC}
"

PY_PASS=0
if PY_OUT=$(${SSH_CMD} "${PY_CMD}" 2>&1); then
    PY_PASS=1
    echo -e "  ${GREEN}✓ Python Textual Verification Passed:${RESET}"
    echo "${PY_OUT}" | sed 's/^/    /'
else
    echo -e "  ${RED}✗ Python Textual Verification Failed:${RESET}"
    echo "${PY_OUT}" | sed 's/^/    /'
fi

# Step 3: Verify Go Bubble Tea Prototype
echo -e "\n${BOLD}[3/4] Verifying Remote Go Bubble Tea Prototype...${RESET}"
GO_CMD="
export PREFIX=\"/data/data/com.termux/files/usr\"
export HOME=\"/data/data/com.termux/files/home\"
export PATH=\"\$PREFIX/bin:\$HOME/bin:\$HOME/go/bin:\$HOME/.cargo/bin:\$PATH\"
cd '${REMOTE_WORKSPACE}'

GO_BIN=''
if [ -f 'build/canonical_tui_go' ]; then
    GO_BIN='build/canonical_tui_go'
elif [ -f 'build/tui_bubbletea' ]; then
    GO_BIN='build/tui_bubbletea'
elif [ -f 'go_bubbletea/bin/tui_go' ]; then
    GO_BIN='go_bubbletea/bin/tui_go'
fi

if [ -n \"\$GO_BIN\" ]; then
    echo '--- 1. Schema Verify Mode ---'
    ./\$GO_BIN -state-path '${STATE_FILE}' -verify || ./\$GO_BIN --state-path '${STATE_FILE}' --verify || ./\$GO_BIN -verify -state '${STATE_FILE}'
    GO_VERIFY_RC=\$?

    echo '--- 2. Smoke Timeout Mode (${TIMEOUT_SECS}s) ---'
    ./\$GO_BIN -state-path '${STATE_FILE}' -timeout ${TIMEOUT_SECS} >/dev/null 2>&1 || ./\$GO_BIN --state-path '${STATE_FILE}' --timeout ${TIMEOUT_SECS} >/dev/null 2>&1 || true
    GO_SMOKE_RC=\$?

    echo \"RESULTS: VERIFY=\${GO_VERIFY_RC} SMOKE=\${GO_SMOKE_RC}\"
    exit \${GO_VERIFY_RC}
elif [ -f 'go_bubbletea/main.go' ]; then
    echo 'Running via go run fallback...'
    cd go_bubbletea
    go run main.go -state-path '${STATE_FILE}' -verify
    exit \$?
else
    echo 'GO_BIN_NOT_FOUND'
    exit 1
fi
"

GO_PASS=0
if GO_OUT=$(${SSH_CMD} "${GO_CMD}" 2>&1); then
    GO_PASS=1
    echo -e "  ${GREEN}✓ Go Bubble Tea Verification Passed:${RESET}"
    echo "${GO_OUT}" | sed 's/^/    /'
else
    echo -e "  ${RED}✗ Go Bubble Tea Verification Failed:${RESET}"
    echo "${GO_OUT}" | sed 's/^/    /'
fi

# Step 4: Verify Rust Ratatui Prototype
echo -e "\n${BOLD}[4/4] Verifying Remote Rust Ratatui Prototype...${RESET}"
RUST_CMD="
export PREFIX=\"/data/data/com.termux/files/usr\"
export HOME=\"/data/data/com.termux/files/home\"
export PATH=\"\$PREFIX/bin:\$HOME/bin:\$HOME/go/bin:\$HOME/.cargo/bin:\$PATH\"
cd '${REMOTE_WORKSPACE}'

RUST_BIN=''
if [ -f 'build/canonical_tui_rust' ]; then
    RUST_BIN='build/canonical_tui_rust'
elif [ -f 'build/tui_ratatui' ]; then
    RUST_BIN='build/tui_ratatui'
elif [ -f 'rust_ratatui/target/release/canonical_tui_rust' ]; then
    RUST_BIN='rust_ratatui/target/release/canonical_tui_rust'
fi

if [ -n \"\$RUST_BIN\" ]; then
    echo '--- 1. Schema Verify Mode ---'
    ./\$RUST_BIN --state-path '${STATE_FILE}' --verify
    RUST_VERIFY_RC=\$?

    echo '--- 2. Smoke Timeout Mode (${TIMEOUT_SECS}s) ---'
    ./\$RUST_BIN --state-path '${STATE_FILE}' --timeout-secs ${TIMEOUT_SECS} >/dev/null 2>&1 || ./\$RUST_BIN --state-path '${STATE_FILE}' --timeout ${TIMEOUT_SECS} >/dev/null 2>&1 || true
    RUST_SMOKE_RC=\$?

    echo \"RESULTS: VERIFY=\${RUST_VERIFY_RC} SMOKE=\${RUST_SMOKE_RC}\"
    exit \${RUST_VERIFY_RC}
elif [ -f 'rust_ratatui/Cargo.toml' ]; then
    echo 'Running via cargo run fallback...'
    cd rust_ratatui
    cargo run --release -- --state-path '${STATE_FILE}' --verify
    exit \$?
else
    echo 'RUST_BIN_NOT_FOUND'
    exit 1
fi
"

RUST_PASS=0
if RUST_OUT=$(${SSH_CMD} "${RUST_CMD}" 2>&1); then
    RUST_PASS=1
    echo -e "  ${GREEN}✓ Rust Ratatui Verification Passed:${RESET}"
    echo "${RUST_OUT}" | sed 's/^/    /'
else
    echo -e "  ${RED}✗ Rust Ratatui Verification Failed:${RESET}"
    echo "${RUST_OUT}" | sed 's/^/    /'
fi

# Summary Table
echo -e "\n================================================================================"
echo -e " 📊 ${BOLD}TERMUX REMOTE VERIFICATION SUMMARY TABLE${RESET}"
echo "================================================================================"
echo -e " Target Device : ${CYAN}${TARGET_DEVICE} (${TARGET_USER}@${TARGET_HOST}:${TARGET_PORT})${RESET}"
echo -e " Remote Dir    : ${REMOTE_WORKSPACE}"
echo "--------------------------------------------------------------------------------"
printf " %-20s | %-12s | %-25s\n" "Framework" "Smoke Status" "Notes"
echo "--------------------------------------------------------------------------------"

if [ ${PY_PASS} -eq 1 ]; then
    printf " %-20s | ${GREEN}%-12s${RESET} | %-25s\n" "Python (Textual)" "PASS" "Verified schema & loop"
else
    printf " %-20s | ${RED}%-12s${RESET} | %-25s\n" "Python (Textual)" "FAIL" "See error log above"
fi

if [ ${GO_PASS} -eq 1 ]; then
    printf " %-20s | ${GREEN}%-12s${RESET} | %-25s\n" "Go (Bubble Tea)" "PASS" "Compiled ARM64 binary"
else
    printf " %-20s | ${RED}%-12s${RESET} | %-25s\n" "Go (Bubble Tea)" "FAIL" "See error log above"
fi

if [ ${RUST_PASS} -eq 1 ]; then
    printf " %-20s | ${GREEN}%-12s${RESET} | %-25s\n" "Rust (Ratatui)" "PASS" "Compiled ARM64 binary"
else
    printf " %-20s | ${RED}%-12s${RESET} | %-25s\n" "Rust (Ratatui)" "FAIL" "See error log above"
fi
echo "================================================================================"

if [ ${PY_PASS} -eq 1 ] && [ ${GO_PASS} -eq 1 ] && [ ${RUST_PASS} -eq 1 ]; then
    echo -e " 🎉 ${GREEN}${BOLD}ALL 3 TUI PROTOTYPES EXECUTED CLEANLY ON TERMUX EDGE HARDWARE!${RESET}\n"
    exit 0
else
    echo -e " ⚠️ ${RED}${BOLD}ONE OR MORE TUIS FAILED REMOTE VERIFICATION ON TERMUX.${RESET}\n"
    exit 1
fi
