#!/usr/bin/env bash
# ==============================================================================
# Master E2E Test Suite Runner for Android Auto AGI Hands-Free Coding Agent
# (`com.lauburu.androidauto.agi`)
# ==============================================================================

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export WORKSPACE_ROOT="$ROOT_DIR"
export TESTS_DIR="$ROOT_DIR/tests"
export VALIDATORS_DIR="$ROOT_DIR/tests/validators"

source "$TESTS_DIR/test_helpers.sh"

# Default flags
RUN_TIER_1=0
RUN_TIER_2=0
RUN_TIER_3=0
RUN_TIER_4=0
RUN_ALL=1
OUTPUT_JSON=0

show_help() {
    echo "Usage: ./test_e2e_suite.sh [options]"
    echo ""
    echo "Options:"
    echo "  --all              Run all test tiers (Tier 1 to 4) [default]"
    echo "  --tier <1|2|3|4>   Run a specific tier (can specify multiple times)"
    echo "  --verbose, -v      Enable verbose test output"
    echo "  --quiet, -q        Suppress individual test lines, show only summary"
    echo "  --json             Output test results in JSON format"
    echo "  --help, -h         Display this help message"
    echo ""
    echo "Tiers:"
    echo "  Tier 1: Feature Coverage (F1 through F11, ≥55 tests)"
    echo "  Tier 2: Boundary & Corner Cases (≥55 tests)"
    echo "  Tier 3: Cross-Feature Combinations (≥11 pairwise tests)"
    echo "  Tier 4: Real-World In-Vehicle Hands-Free Coding Scenarios (≥5 workloads)"
    echo "  Total: ≥126 test cases"
}

# Parse command line arguments
if [ $# -gt 0 ]; then
    RUN_ALL=0
    while [ $# -gt 0 ]; do
        case "$1" in
            --all)
                RUN_ALL=1
                shift
                ;;
            --tier)
                shift
                case "$1" in
                    1) RUN_TIER_1=1 ;;
                    2) RUN_TIER_2=1 ;;
                    3) RUN_TIER_3=1 ;;
                    4) RUN_TIER_4=1 ;;
                    *) echo "Error: Unknown tier '$1'. Must be 1, 2, 3, or 4."; exit 1 ;;
                esac
                shift
                ;;
            --verbose|-v)
                set_verbosity 2
                shift
                ;;
            --quiet|-q)
                set_verbosity 0
                shift
                ;;
            --json)
                OUTPUT_JSON=1
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                echo "Error: Unknown argument '$1'"
                show_help
                exit 1
                ;;
        esac
    done
fi

if [ $RUN_ALL -eq 1 ]; then
    RUN_TIER_1=1
    RUN_TIER_2=1
    RUN_TIER_3=1
    RUN_TIER_4=1
fi

echo -e "${CLR_BOLD}================================================================================${CLR_RESET}"
echo -e "${CLR_BOLD}   ANDROID AUTO AGI HANDS-FREE CODING AGENT - E2E TEST SUITE RUNNER            ${CLR_RESET}"
echo -e "${CLR_BOLD}   Target: com.lauburu.androidauto.agi | Workspace: ${WORKSPACE_ROOT}${CLR_RESET}"
echo -e "${CLR_BOLD}================================================================================${CLR_RESET}"

# Execute Tiers
if [ $RUN_TIER_1 -eq 1 ]; then
    source "$TESTS_DIR/test_tier1_features.sh"
    run_tier1_tests
fi

if [ $RUN_TIER_2 -eq 1 ]; then
    source "$TESTS_DIR/test_tier2_boundaries.sh"
    run_tier2_tests
fi

if [ $RUN_TIER_3 -eq 1 ]; then
    source "$TESTS_DIR/test_tier3_combinations.sh"
    run_tier3_tests
fi

if [ $RUN_TIER_4 -eq 1 ]; then
    source "$TESTS_DIR/test_tier4_scenarios.sh"
    run_tier4_tests
fi

# Print final suite summary
print_suite_summary
FINAL_EXIT_CODE=$?

if [ $OUTPUT_JSON -eq 1 ]; then
    echo "$JSON_RESULTS" > "$WORKSPACE_ROOT/test_results.json"
    echo -e "JSON test results written to ${CLR_CYAN}$WORKSPACE_ROOT/test_results.json${CLR_RESET}"
fi

exit $FINAL_EXIT_CODE
