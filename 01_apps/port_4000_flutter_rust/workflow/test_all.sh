#!/usr/bin/env bash
# ==============================================================================
# Lauburu Port 4000 Console: Unified Test Suite
# Runs Rust Unit Tests + Dart Unit & Integration Tests + FFI Verifications
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

export PATH="/Users/aaron/.cargo/bin:/Users/aaron/.homebrew/Cellar/dart-sdk/3.13.3/bin:$PATH"

echo "======================================================================"
echo "🧪 LAUBURU PORT 4000: RUNNING UNIFIED TEST SUITE"
echo "======================================================================"

# 1. Run Rust Core Unit Tests
echo "🦀 1/2 Running Rust Backend Tests (Pan-Tompkins, DFA-alpha1, C-FFI, Server REST)..."
cd "$ROOT_DIR/rust_backend"
cargo test -- --nocapture

# 2. Run Dart / Flutter UI Tests
echo ""
echo "🎯 2/2 Running Dart / Flutter UI Tests (Models, FFI Bridge, Reactive State)..."
cd "$ROOT_DIR/flutter_ui"
dart run lib/main.dart
dart test

echo ""
echo "======================================================================"
echo "✅ ALL TESTS PASSED! 100% Zero-Mock Verification Complete."
echo "======================================================================"
