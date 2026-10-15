#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$SCRIPT_DIR/src"
BIN_DIR="$SCRIPT_DIR/bin"
TARGET_BIN="$BIN_DIR/lauburu-lens"

mkdir -p "$BIN_DIR"

echo "🔨 Compiling native macOS Screen Lens (lauburu-lens) with Swift 6..."
xcrun swiftc -O -whole-module-optimization -parse-as-library \
    "$SRC_DIR/WindowInspector.swift" \
    "$SRC_DIR/VisionOCR.swift" \
    "$SRC_DIR/CaptureEngine.swift" \
    "$SRC_DIR/DatabaseManager.swift" \
    "$SRC_DIR/HttpServer.swift" \
    "$SRC_DIR/DaemonManager.swift" \
    "$SRC_DIR/main.swift" \
    -framework ScreenCaptureKit \
    -framework Vision \
    -framework AppKit \
    -framework ApplicationServices \
    -framework Network \
    -framework CoreGraphics \
    -framework CoreVideo \
    -lsqlite3 \
    -o "$TARGET_BIN"

chmod +x "$TARGET_BIN"
echo "✅ Compilation successful: $TARGET_BIN"
