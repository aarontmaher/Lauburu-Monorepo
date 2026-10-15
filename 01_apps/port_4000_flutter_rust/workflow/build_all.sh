#!/usr/bin/env bash
# ==============================================================================
# Lauburu Port 4000 Console: Full Build Workflow Script
# Compiles Rust Backend (Dynamic Library & Native Server) + Dart/Flutter UI
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

export PATH="/Users/aaron/.cargo/bin:/Users/aaron/.homebrew/Cellar/dart-sdk/3.13.3/bin:$PATH"

echo "======================================================================"
echo "🚀 LAUBURU PORT 4000: STARTING UNIFIED BUILD WORKFLOW"
echo "======================================================================"

# 1. Build Rust Backend Core
echo "📦 1/3 Compiling Rust Backend Core (cdylib + staticlib + bin)..."
cd "$ROOT_DIR/rust_backend"
cargo build --release

DYLIB="$ROOT_DIR/rust_backend/target/release/liblauburu_core.dylib"
BIN="$ROOT_DIR/rust_backend/target/release/port4000_server"

if [ -f "$DYLIB" ] && [ -f "$BIN" ]; then
    echo "   ✅ liblauburu_core.dylib built: $(ls -lh "$DYLIB" | awk '{print $5}')"
    echo "   ✅ port4000_server binary built: $(ls -lh "$BIN" | awk '{print $5}')"
else
    echo "   ❌ Rust compilation failed to generate expected targets."
    exit 1
fi

# 2. Build Flutter / Dart UI Client
echo "📱 2/3 Building Flutter / Dart UI Console & Web Assets..."
cd "$ROOT_DIR/flutter_ui"
dart pub get
dart run lib/main.dart

INDEX_HTML="$ROOT_DIR/flutter_ui/build/index.html"
if [ -f "$INDEX_HTML" ]; then
    echo "   ✅ Console Web Assets generated: $(ls -lh "$INDEX_HTML" | awk '{print $5}')"
else
    echo "   ❌ Dart build failed to generate build/index.html."
    exit 1
fi

# 3. Verify Dynamic Symbol Exports
echo "🔍 3/3 Verifying C-FFI Symbol Exports in Dynamic Library..."
SYMBOLS=$(nm -gU "$DYLIB" | grep "lauburu_" || true)
echo "$SYMBOLS" | sed 's/^/   → /'

echo ""
echo "======================================================================"
echo "🎉 BUILD SUCCESSFUL! All Rust and Flutter artifacts are ready."
echo "======================================================================"
