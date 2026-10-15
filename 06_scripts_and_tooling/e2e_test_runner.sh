#!/usr/bin/env bash
# e2e_test_runner.sh: Run the Proven 5-Layer UI/UX E2E Testing Suite
set -e
TEST_DIR="/Volumes/Lauburu-Monorepo/01_apps/screen_lens/sandbox_evolution/e2e_testing_studio"
cd "$TEST_DIR"
echo "🔬 [E2E-Studio] Executing Proven 5-Layer UI/UX Testing Testbench..."
python3 -m unittest -v test_proven_e2e_methodology.py
echo "✅ [E2E-Studio] All 5 layers verified. Exit Code 0."
