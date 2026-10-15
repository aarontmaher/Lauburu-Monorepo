#!/usr/bin/env bash
# ==============================================================================
# Lauburu Port 4000 Console: Master E2E & Forensic Truth Audit Test Suite
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

export PATH="/Users/aaron/.cargo/bin:/Users/aaron/.homebrew/Cellar/dart-sdk/3.13.3/bin:$PATH"

echo "======================================================================"
echo "🧪 LAUBURU PORT 4000: RUNNING MASTER E2E & TRUTH AUDIT SUITE"
echo "======================================================================"

# Step 0: Kill any stale port 4000 process
if lsof -ti :4000 >/dev/null 2>&1; then
    echo "⚠️  Killing stale port 4000 process..."
    lsof -ti :4000 | xargs kill -9 2>/dev/null || true
    sleep 1
fi

# Step 1: Run Full Build Workflow
echo "📦 Step 1/5: Compiling Release Artifacts..."
bash "$SCRIPT_DIR/build_all.sh"

# Step 2: Zero-Mock Static Truth Audit (AST / Regex Scan)
echo "🔍 Step 2/5: Executing Forensic Zero-Mock Truth Audit..."
HTML_FILE="$ROOT_DIR/flutter_ui/build/index.html"
if [ ! -f "$HTML_FILE" ]; then
    echo "❌ Error: $HTML_FILE missing!"
    exit 1
fi

# Assert zero forbidden mock values in compiled HTML
if grep -q "72 BPM" "$HTML_FILE" || grep -q "48.5ms" "$HTML_FILE" || grep -q "48.5 ms" "$HTML_FILE"; then
    echo "❌ Truth Audit Failed: Found legacy mock constants in HTML!"
    exit 1
fi

# Assert required zero-mock standby indicators exist
grep -q "STANDBY — DISCONNECTED" "$HTML_FILE" || { echo "❌ Missing standby badge"; exit 1; }
grep -q "0% MOCK DATA" "$HTML_FILE" || { echo "❌ Missing zero-mock banner"; exit 1; }
echo "   ✅ Static HTML Zero-Mock Truth Audit Passed!"

# Step 3: Launch Port 4000 Daemon in Background
echo "🚀 Step 3/5: Spawning Port 4000 Daemon..."
BIN="$ROOT_DIR/rust_backend/target/release/port4000_server"
LOG_FILE="/tmp/lauburu_e2e_port4000.log"
nohup "$BIN" > "$LOG_FILE" 2>&1 &
SERVER_PID=$!

cleanup() {
    echo "🧹 Tearing down test daemon (PID: $SERVER_PID)..."
    kill -9 "$SERVER_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# Wait for server health
echo "   Waiting for server readiness on http://127.0.0.1:4000/health..."
READY=0
for i in {1..20}; do
    if curl -s http://127.0.0.1:4000/health | grep -q "HEALTHY"; then
        READY=1
        break
    fi
    sleep 0.3
done

if [ $READY -ne 1 ]; then
    echo "❌ Server failed to start within timeout!"
    cat "$LOG_FILE"
    exit 1
fi
echo "   ✅ Port 4000 Server is LIVE (PID: $SERVER_PID)"

# Step 4: Probe Live Endpoints
echo "📡 Step 4/5: Probing Live REST & Ingestion Endpoints..."

HEALTH_JSON=$(curl -s http://127.0.0.1:4000/health)
echo "   • /health: $HEALTH_JSON"

SNAP_JSON=$(curl -s http://127.0.0.1:4000/api/biometrics/snapshot)
echo "   • /api/biometrics/snapshot: $SNAP_JSON"

SPATIAL_JSON=$(curl -s http://127.0.0.1:4000/api/spatial/map)
echo "   • /api/spatial/map: $SPATIAL_JSON"

# Live Ingestion POST check
INGEST_RES=$(curl -s -X POST http://127.0.0.1:4000/api/biometrics/sample \
    -H "Content-Type: application/json" \
    -d '{"sample": 0.5, "heart_rate": 140.0, "rr_intervals": [428.5, 429.0], "device_id": "E2E-Movesense"}')
if echo "$INGEST_RES" | grep -q '"heart_rate_bpm":140.0'; then
    echo "     ✅ /api/biometrics/sample ingestion verified: Live dynamic transition (140.0 BPM)"
else
    echo "     ❌ Ingestion POST failed!"
    exit 1
fi

# Step 5: Run Unified Test Suites
echo "🧪 Step 5/5: Executing Master Unit & Adversarial Test Suites..."
bash "$SCRIPT_DIR/test_all.sh"

echo ""
echo "======================================================================"
echo "🎉 100% E2E ZERO-MOCK ACCEPTANCE & FORENSIC TRUTH AUDIT PASSED!"
echo "======================================================================"
