#!/bin/bash
# ==============================================================================
# Comprehensive Test Runner: GL.iNet Router Foundation (Omni-Lens Sovereign Mesh)
# Executes all 4 tiers of test suites and validates all 5 Acceptance Criteria.
# ==============================================================================
set -e
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROUTER_FOUNDATION_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TESTS_DIR="$ROUTER_FOUNDATION_DIR/tests"
PROJECT_ROOT="$(cd "$ROUTER_FOUNDATION_DIR/../.." && pwd)"

# ANSI Color codes
BOLD="\033[1m"
GREEN="\033[32m"
RED="\033[31m"
YELLOW="\033[33m"
CYAN="\033[36m"
RESET="\033[0m"

echo -e "${BOLD}${CYAN}==============================================================================${RESET}"
echo -e "${BOLD}${CYAN}   GL.iNet Router Bluetooth & Network Foundation - Test Runner${RESET}"
echo -e "${BOLD}${CYAN}==============================================================================${RESET}"
echo -e "Project Root: ${PROJECT_ROOT}"
echo -e "Router Foundation: ${ROUTER_FOUNDATION_DIR}"
echo -e "Tests Directory: ${TESTS_DIR}"
echo ""

TOTAL_TESTS=0
FAILED_SUITES=0
PASSED_SUITES=0

run_suite() {
    local suite_name="$1"
    local suite_file="$2"
    local description="$3"

    echo -e "${BOLD}▶ Running [${suite_name}] - ${description}${RESET}"
    
    if [ ! -f "$TESTS_DIR/$suite_file" ]; then
        echo -e "${RED}  ✖ Error: Test file $suite_file not found!${RESET}"
        FAILED_SUITES=$((FAILED_SUITES + 1))
        return 1
    fi

    local log_file
    log_file=$(mktemp /tmp/router_test_XXXXXX.log)
    local start_time
    start_time=$(python3 -c "import time; print(time.time())")

    local test_exit=0
    set +e
    python3 -m unittest "$TESTS_DIR/$suite_file" 2>&1 | tee "$log_file"
    test_exit=${PIPESTATUS[0]}
    set -e

    local elapsed
    elapsed=$(python3 -c "import time; print(round(time.time() - $start_time, 3))")

    # Evaluate test_exit and verify output log confirms success without failures
    if [ "$test_exit" -eq 0 ] && grep -q "OK" "$log_file" && ! grep -q "FAILED" "$log_file"; then
        local count
        count=$(grep -E "Ran [0-9]+ test" "$log_file" | awk '{print $2}')
        [ -z "$count" ] && count="0"
        TOTAL_TESTS=$((TOTAL_TESTS + count))
        PASSED_SUITES=$((PASSED_SUITES + 1))
        echo -e "${GREEN}  ✔ PASSED: ${count} tests in ${elapsed}s${RESET}\n"
    else
        echo -e "${RED}  ✖ FAILED: Test suite ${suite_file} failed with exit code ${test_exit}!${RESET}\n"
        FAILED_SUITES=$((FAILED_SUITES + 1))
    fi
    rm -f "$log_file"
}

# 1. Validate shell scripts syntax with sh -n
echo -e "${BOLD}▶ Validating Router Shell Scripts & Procd Services Syntax (sh -n)...${RESET}"
SHELL_ERRORS=0
for sh_file in "$ROUTER_FOUNDATION_DIR"/router/usr/bin/*.sh \
              "$ROUTER_FOUNDATION_DIR"/router/etc/init.d/* \
              "$ROUTER_FOUNDATION_DIR"/router/etc/hotplug.d/dhcp/* \
              "$ROUTER_FOUNDATION_DIR"/deploy/*.sh; do
    if [ -f "$sh_file" ]; then
        if sh -n "$sh_file"; then
            echo -e "  ✔ Syntax OK: $(basename "$sh_file")"
        else
            echo -e "${RED}  ✖ Syntax ERROR: $sh_file${RESET}"
            SHELL_ERRORS=$((SHELL_ERRORS + 1))
        fi
    fi
done

if [ "$SHELL_ERRORS" -gt 0 ]; then
    echo -e "${RED}Shell syntax errors detected. Aborting runner.${RESET}"
    exit 1
fi
echo -e "${GREEN}All router shell scripts validated successfully.${RESET}\n"

# 2. Run Individual Automated Test Suites
run_suite "R1: Router Bluetooth Hub" "test_router_bluetooth_hub.py" "Procd, socat parameters, btmon sockets"
run_suite "R2: Lens 10GbE Ingester & DSP" "test_lens_10gbe_ingester.py" "Movesense, Whoop, SmartThings, Kamath filter, RMSSD"
run_suite "R3: DHCP/ARP Presence Oracle" "test_presence_oracle.py" "Dnsmasq hotplug, rtnetlink, < 2.0s propagation"
run_suite "R4: Out-Of-Band WAN Healer" "test_oob_wan_healer.py" "6-state FSM transitions, Layer 3 ICMP, route generation"
run_suite "R5: Edge Security Red Team" "test_edge_security_monitor.py" "Rogue MACs, routing loops, ARP spoofing, 2D radar"
run_suite "E2E: Acceptance Criteria Suite" "test_e2e_router_foundation.py" "AC1–AC5 Master Acceptance Verification"
run_suite "ADV: Adversarial Network Stress" "test_adversarial_network_stress.py" "High-throughput bursts, boundary hardening, truncated TLV"

# 3. Final Summary Report
TOTAL_SUITES_PLANNED=$((PASSED_SUITES + FAILED_SUITES))
echo -e "${BOLD}${CYAN}==============================================================================${RESET}"
echo -e "${BOLD}${CYAN}                           TEST EXECUTION SUMMARY${RESET}"
echo -e "${BOLD}${CYAN}==============================================================================${RESET}"
echo -e "Total Test Suites Passed: ${GREEN}${PASSED_SUITES} / ${TOTAL_SUITES_PLANNED}${RESET}"
echo -e "Total Individual Tests:   ${GREEN}${TOTAL_TESTS}${RESET}"
echo -e "Failed Suites:            ${FAILED_SUITES}"

if [ "$FAILED_SUITES" -eq 0 ]; then
    echo -e "\n${BOLD}${GREEN}✔ ALL TEST SUITES PASSED! 100% SPECIFICATION AND ACCEPTANCE COMPLIANCE.${RESET}"
    exit 0
else
    echo -e "\n${BOLD}${RED}✖ SOME TEST SUITES FAILED! Check output above.${RESET}"
    exit 1
fi
