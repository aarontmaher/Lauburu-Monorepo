#!/usr/bin/env bash
# ==============================================================================
# E2E Test Helpers & Assertion Framework for Android Auto AGI
# ==============================================================================

# ANSI Color Codes
CLR_RESET="\033[0m"
CLR_RED="\033[1;31m"
CLR_GREEN="\033[1;32m"
CLR_YELLOW="\033[1;33m"
CLR_BLUE="\033[1;34m"
CLR_MAGENTA="\033[1;35m"
CLR_CYAN="\033[1;36m"
CLR_BOLD="\033[1m"
CLR_DIM="\033[2m"

# Guard counters from being reset on multiple sources
if [ -z "$_TEST_HELPERS_LOADED" ]; then
    export _TEST_HELPERS_LOADED=1
    export TOTAL_TESTS=0
    export PASSED_TESTS=0
    export FAILED_TESTS=0
    export SKIPPED_TESTS=0
    export JSON_RESULTS="[]"
    export SUITE_START_TIME=$(date +%s)
    export VERBOSE_LEVEL=1
fi

set_verbosity() {
    export VERBOSE_LEVEL=$1
}

get_timestamp() {
    date -u +"%Y-%m-%dT%H:%M:%SZ"
}

print_tier_header() {
    local tier_num="$1"
    local tier_title="$2"
    echo ""
    echo -e "${CLR_BLUE}================================================================================${CLR_RESET}"
    echo -e "${CLR_BLUE}${CLR_BOLD}  TIER ${tier_num}: ${tier_title}${CLR_RESET}"
    echo -e "${CLR_BLUE}================================================================================${CLR_RESET}"
}

print_feature_header() {
    local feat_id="$1"
    local feat_title="$2"
    echo ""
    echo -e "${CLR_CYAN}--- [${feat_id}] ${feat_title} ---${CLR_RESET}"
}

record_test() {
    local test_id="$1"
    local status="$2" # PASS, FAIL, SKIP
    local description="$3"
    local detail="$4"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    if [ "$status" = "PASS" ]; then
        PASSED_TESTS=$((PASSED_TESTS + 1))
        if [ "$VERBOSE_LEVEL" -ge 1 ]; then
            printf "  ${CLR_GREEN}✓ PASS${CLR_RESET} [${CLR_BOLD}%-10s${CLR_RESET}] %s\n" "$test_id" "$description"
        fi
        if [ -n "$detail" ] && [ "$VERBOSE_LEVEL" -ge 2 ]; then
            echo -e "         ${CLR_DIM}${detail}${CLR_RESET}"
        fi
    elif [ "$status" = "FAIL" ]; then
        FAILED_TESTS=$((FAILED_TESTS + 1))
        printf "  ${CLR_RED}✗ FAIL${CLR_RESET} [${CLR_BOLD}%-10s${CLR_RESET}] %s\n" "$test_id" "$description"
        if [ -n "$detail" ]; then
            echo -e "         ${CLR_RED}Reason: ${detail}${CLR_RESET}"
        fi
    else
        SKIPPED_TESTS=$((SKIPPED_TESTS + 1))
        printf "  ${CLR_YELLOW}⚠ SKIP${CLR_RESET} [${CLR_BOLD}%-10s${CLR_RESET}] %s\n" "$test_id" "$description"
        if [ -n "$detail" ]; then
            echo -e "         ${CLR_YELLOW}Reason: ${detail}${CLR_RESET}"
        fi
    fi

    local safe_desc=$(echo "$description" | sed 's/"/\\"/g')
    local safe_detail=$(echo "$detail" | sed 's/"/\\"/g')
    
    JSON_RESULTS=$(python3 -c "
import json, sys
try:
    data = json.loads('''$JSON_RESULTS''')
except:
    data = []
data.append({
    'id': sys.argv[1],
    'status': sys.argv[2],
    'description': sys.argv[3],
    'detail': sys.argv[4]
})
print(json.dumps(data))
" "$test_id" "$status" "$safe_desc" "$safe_detail" 2>/dev/null || echo "$JSON_RESULTS")
}

assert_file_exists() {
    local test_id="$1"
    local filepath="$2"
    local desc="$3"

    if [ -f "$filepath" ]; then
        record_test "$test_id" "PASS" "$desc" "File exists: $filepath"
        return 0
    else
        record_test "$test_id" "FAIL" "$desc" "File not found: $filepath"
        return 1
    fi
}

assert_file_contains() {
    local test_id="$1"
    local filepath="$2"
    local regex="$3"
    local desc="$4"

    if [ ! -f "$filepath" ]; then
        record_test "$test_id" "FAIL" "$desc" "File not found: $filepath"
        return 1
    fi

    if grep -E -q "$regex" "$filepath" 2>/dev/null; then
        record_test "$test_id" "PASS" "$desc" "Found match '$regex' in $filepath"
        return 0
    else
        record_test "$test_id" "FAIL" "$desc" "Pattern '$regex' not found in $filepath"
        return 1
    fi
}

assert_executable() {
    local test_id="$1"
    local filepath="$2"
    local desc="$3"

    if [ -x "$filepath" ]; then
        record_test "$test_id" "PASS" "$desc" "File is executable: $filepath"
        return 0
    else
        record_test "$test_id" "FAIL" "$desc" "File is not executable: $filepath"
        return 1
    fi
}

assert_eq() {
    local test_id="$1"
    local expected="$2"
    local actual="$3"
    local desc="$4"

    if [ "$expected" = "$actual" ]; then
        record_test "$test_id" "PASS" "$desc" "Value equals: $expected"
        return 0
    else
        record_test "$test_id" "FAIL" "$desc" "Expected '$expected' but got '$actual'"
        return 1
    fi
}

assert_cmd_success() {
    local test_id="$1"
    local cmd="$2"
    local desc="$3"

    local output
    output=$(eval "$cmd" 2>&1)
    local status=$?

    if [ $status -eq 0 ]; then
        record_test "$test_id" "PASS" "$desc" "Command succeeded (exit 0)"
        return 0
    else
        local trimmed_output=$(echo "$output" | head -n 3 | tr '\n' ' ')
        record_test "$test_id" "FAIL" "$desc" "Command failed with exit code $status. Output: $trimmed_output"
        return 1
    fi
}

assert_cmd_fails() {
    local test_id="$1"
    local cmd="$2"
    local desc="$3"

    local output
    output=$(eval "$cmd" 2>&1)
    local status=$?

    if [ $status -ne 0 ]; then
        record_test "$test_id" "PASS" "$desc" "Command correctly rejected (exit code $status)"
        return 0
    else
        record_test "$test_id" "FAIL" "$desc" "Command unexpectedly succeeded (exit code 0)"
        return 1
    fi
}

assert_validator() {
    local test_id="$1"
    local script_path="$2"
    local args="$3"
    local desc="$4"

    if [ ! -f "$script_path" ]; then
        record_test "$test_id" "FAIL" "$desc" "Validator script not found: $script_path"
        return 1
    fi

    local output
    output=$(python3 "$script_path" $args 2>&1)
    local status=$?

    if [ $status -eq 0 ]; then
        record_test "$test_id" "PASS" "$desc" "$output"
        return 0
    else
        local err_line=$(echo "$output" | tail -n 2 | tr '\n' ' ')
        record_test "$test_id" "FAIL" "$desc" "Validation failed: $err_line"
        return 1
    fi
}

print_suite_summary() {
    local suite_end_time=$(date +%s)
    local duration=$((suite_end_time - SUITE_START_TIME))

    echo ""
    echo -e "${CLR_BOLD}================================================================================${CLR_RESET}"
    echo -e "${CLR_BOLD}                     E2E TEST EXECUTION SUMMARY                                 ${CLR_RESET}"
    echo -e "${CLR_BOLD}================================================================================${CLR_RESET}"
    printf "  ${CLR_BOLD}Total Tests Run:${CLR_RESET}   %d\n" "$TOTAL_TESTS"
    printf "  ${CLR_GREEN}Passed:${CLR_RESET}           %d\n" "$PASSED_TESTS"
    printf "  ${CLR_RED}Failed:${CLR_RESET}           %d\n" "$FAILED_TESTS"
    printf "  ${CLR_YELLOW}Skipped:${CLR_RESET}          %d\n" "$SKIPPED_TESTS"
    printf "  ${CLR_BLUE}Duration:${CLR_RESET}         %d seconds\n" "$duration"
    
    local pass_rate=0
    if [ $TOTAL_TESTS -gt 0 ]; then
        pass_rate=$(( (PASSED_TESTS * 100) / TOTAL_TESTS ))
    fi
    printf "  ${CLR_BOLD}Pass Rate:${CLR_RESET}        %d%%\n" "$pass_rate"
    echo -e "${CLR_BOLD}================================================================================${CLR_RESET}"

    if [ $FAILED_TESTS -gt 0 ]; then
        echo -e "${CLR_RED}${CLR_BOLD}RESULT: FAILED (${FAILED_TESTS} tests failed)${CLR_RESET}"
        return 1
    else
        echo -e "${CLR_GREEN}${CLR_BOLD}RESULT: ALL TESTS PASSED (${PASSED_TESTS}/${TOTAL_TESTS})${CLR_RESET}"
        return 0
    fi
}

export -f print_tier_header print_feature_header record_test assert_file_exists assert_file_contains assert_executable assert_eq assert_cmd_success assert_cmd_fails assert_validator print_suite_summary
