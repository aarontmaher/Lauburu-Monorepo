#!/usr/bin/env bash
# ==============================================================================
# Lauburu Port 4000 Console: Start Daemon & Live Console Runner
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

export PATH="/Users/aaron/.cargo/bin:/Users/aaron/.homebrew/Cellar/dart-sdk/3.13.3/bin:$PATH"

echo "======================================================================"
echo "⚡ LAUBURU PORT 4000: STARTING DAEMON & CONSOLE"
echo "======================================================================"

# Check if port 4000 is already in use, kill old zombie if present
if lsof -iTCP:4000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  Port 4000 occupied. Killing existing listening process..."
    lsof -iTCP:4000 -sTCP:LISTEN -t | xargs kill -9 2>/dev/null || true
    sleep 1
fi

# 1. Start Rust Backend Server
BIN="$ROOT_DIR/rust_backend/target/release/port4000_server"
if [ ! -f "$BIN" ]; then
    echo "📦 Compiling release binary first..."
    cd "$ROOT_DIR/rust_backend"
    cargo build --release --bin port4000_server
fi

LOG_FILE="/tmp/lauburu_port4000_backend.log"
nohup "$BIN" > "$LOG_FILE" 2>&1 &
SERVER_PID=$!

echo "🚀 Rust Backend Server started with PID: $SERVER_PID (listening on 0.0.0.0:4000)"
echo "   Logs: $LOG_FILE"

# Wait for health endpoint
echo "⏳ Verifying server health..."
READY=0
for i in {1..20}; do
    if curl -s http://127.0.0.1:4000/health | grep -q "HEALTHY"; then
        echo "   ✅ Port 4000 Server is LIVE and HEALTHY!"
        READY=1
        break
    fi
    sleep 0.5
done

if [ "$READY" -ne 1 ]; then
    echo "❌ Port 4000 Server failed to report healthy status within timeout!"
    cat "$LOG_FILE"
    exit 1
fi

# Pull live health
HEALTH_JSON=$(curl -s http://127.0.0.1:4000/health)
echo "   Status: $HEALTH_JSON"

# 2. Generate updated Flutter Console Web Dashboard
cd "$ROOT_DIR/flutter_ui"
dart run lib/main.dart >/dev/null 2>&1

echo ""
echo "======================================================================"
echo "🎉 LAUBURU PORT 4000 CONSOLE IS READY"
echo "   • Local Loopback:    http://127.0.0.1:4000/  (UI + REST)"
echo "   • Tailscale Mesh:    http://100.119.199.76:4000/ (Pixel: 100.73.38.87)"
echo "   • Backend REST API:  http://127.0.0.1:4000/health"
echo "   • Live Biometrics:   http://127.0.0.1:4000/api/biometrics/snapshot"
echo "   • Real-Time WS:      ws://127.0.0.1:4000/ws/telemetry & /ws/spatial"
echo "   • Console UI HTML:   $ROOT_DIR/flutter_ui/build/index.html"
echo "======================================================================"
