#!/bin/bash
# ==============================================================================
# Sovereign Screen Lens (lauburu-lens) — Comprehensive Integration Test Suite
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BIN_PATH="$APP_DIR/bin/lauburu-lens"
CLI_PATH="/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/lauburu_cli.sh"
TEST_PORT=3035
DB_PATH="$HOME/.lauburu/screen_lens.sqlite"

PASSED_COUNT=0
FAILED_COUNT=0

log_pass() {
    echo "  ✅ PASS: $1"
    PASSED_COUNT=$((PASSED_COUNT + 1))
}

log_fail() {
    echo "  ❌ FAIL: $1"
    FAILED_COUNT=$((FAILED_COUNT + 1))
}

echo "======================================================================"
echo "🧪 STARTING SCREEN LENS (lauburu-lens) INTEGRATION TEST SUITE"
echo "======================================================================"

# Ensure binary is compiled
if [ ! -x "$BIN_PATH" ]; then
    echo "🔨 Compiling binary first..."
    "$APP_DIR/build.sh"
fi

# Ensure any previous test daemon is stopped
"$BIN_PATH" stop >/dev/null 2>&1 || true

# Test 1: CLI Help and Basic Invocation
echo ""
echo "[Test 1/8] Verifying CLI help and argument dispatcher..."
HELP_OUT=$("$BIN_PATH" help)
if echo "$HELP_OUT" | grep -q "LAUBURU SCREEN LENS"; then
    log_pass "Help banner displayed successfully"
else
    log_fail "Help banner missing"
fi

# Test 2: On-screen Window Inspection
echo ""
echo "[Test 2/8] Verifying window enumeration..."
WIN_JSON=$("$BIN_PATH" windows --json)
WIN_COUNT=$(echo "$WIN_JSON" | grep -o '"count"' || true)
if [ -n "$WIN_COUNT" ]; then
    log_pass "Window inspector returned valid JSON with active on-screen windows"
else
    log_fail "Window inspector failed"
fi

# Test 3: One-shot ScreenCaptureKit + Vision OCR Capture
echo ""
echo "[Test 3/8] Executing live ScreenCaptureKit frame capture & Apple Vision OCR..."
CAP_JSON=$("$BIN_PATH" capture --mode fast --json)
if echo "$CAP_JSON" | grep -q '"text_count"'; then
    TEXT_COUNT=$(echo "$CAP_JSON" | python3 -c "import json, sys; d=json.load(sys.stdin); print(d.get('text_count', 0))")
    CONF_AVG=$(echo "$CAP_JSON" | python3 -c "import json, sys; d=json.load(sys.stdin); print(f\"{d.get('confidence_avg', 0):.2f}\")")
    log_pass "Direct capture successful: $TEXT_COUNT text blocks detected (Mean confidence: $CONF_AVG)"
else
    log_fail "Direct capture JSON output invalid"
fi

# Test 4: SQLite Database Invariants & Schema
echo ""
echo "[Test 4/8] Verifying SQLite database schema and FTS5 synchronization..."
if [ -f "$DB_PATH" ]; then
    REC_COUNT=$(sqlite3 "$DB_PATH" "SELECT count(*) FROM captures;")
    FTS_COUNT=$(sqlite3 "$DB_PATH" "SELECT count(*) FROM captures_fts;")
    BLOCKS_COUNT=$(sqlite3 "$DB_PATH" "SELECT count(*) FROM ocr_text_blocks;")
    if [ "$REC_COUNT" -gt 0 ] && [ "$FTS_COUNT" -eq "$REC_COUNT" ]; then
        log_pass "SQLite integrity verified: $REC_COUNT captures, $FTS_COUNT FTS rows, $BLOCKS_COUNT spatial blocks"
    else
        log_fail "SQLite FTS sync mismatch: $REC_COUNT captures vs $FTS_COUNT FTS rows"
    fi
else
    log_fail "SQLite database file not found at $DB_PATH"
fi

# Test 5: Full-Text Search (FTS5) Querying
echo ""
echo "[Test 5/8] Testing SQLite FTS5 search queries..."
QUERY_OUT=$("$BIN_PATH" query "File" --limit 5 --json)
TOTAL_MATCHES=$(echo "$QUERY_OUT" | python3 -c "import json, sys; d=json.load(sys.stdin); print(d.get('total', 0))")
if [ "$TOTAL_MATCHES" -ge 1 ]; then
    log_pass "FTS search returned $TOTAL_MATCHES matching records"
else
    log_fail "FTS query returned 0 matches for term 'File'"
fi

# Test 6: Background Daemon Lifecycle & Embedded HTTP Server on Port 3035
echo ""
echo "[Test 6/8] Starting background daemon and verifying embedded HTTP REST endpoints..."
"$BIN_PATH" start --port "$TEST_PORT" --interval 2.0 --daemon
sleep 2

# Verify PID file exists
PID_FILE="$HOME/.lauburu/screen_lens.pid"
if [ -f "$PID_FILE" ]; then
    DAEMON_PID=$(cat "$PID_FILE")
    log_pass "Daemon running with PID $DAEMON_PID"
else
    log_fail "Daemon PID file not created"
fi

# Test GET /health
HEALTH_RESP=$(curl -s "http://127.0.0.1:$TEST_PORT/health")
if echo "$HEALTH_RESP" | grep -q '"status" : "ok"'; then
    log_pass "Endpoint GET /health returned 200 OK"
else
    log_fail "Endpoint GET /health failed"
fi

# Test GET /api/status
STATUS_RESP=$(curl -s "http://127.0.0.1:$TEST_PORT/api/status")
if echo "$STATUS_RESP" | grep -q '"running" : true'; then
    log_pass "Endpoint GET /api/status returned active capture state"
else
    log_fail "Endpoint GET /api/status failed"
fi

# Test POST /api/capture
API_CAP_RESP=$(curl -s -X POST "http://127.0.0.1:$TEST_PORT/api/capture")
if echo "$API_CAP_RESP" | grep -q '"text_count"'; then
    log_pass "Endpoint POST /api/capture triggered on-demand snapshot"
else
    log_fail "Endpoint POST /api/capture failed"
fi

# Test GET /api/latest
LATEST_RESP=$(curl -s "http://127.0.0.1:$TEST_PORT/api/latest")
if echo "$LATEST_RESP" | grep -q '"text_blocks"'; then
    log_pass "Endpoint GET /api/latest returned latest frame with spatial text blocks"
else
    log_fail "Endpoint GET /api/latest failed"
fi

# Test GET /api/windows
WIN_RESP=$(curl -s "http://127.0.0.1:$TEST_PORT/api/windows")
if echo "$WIN_RESP" | grep -q '"windows"'; then
    log_pass "Endpoint GET /api/windows returned active windows list"
else
    log_fail "Endpoint GET /api/windows failed"
fi

# Test Stop Daemon
"$BIN_PATH" stop
sleep 1
if [ ! -f "$PID_FILE" ]; then
    log_pass "Daemon stopped cleanly and PID file removed"
else
    log_fail "Daemon failed to remove PID file on stop"
fi

# Test 7: Global Master CLI Integration (lauburu_cli.sh lens)
echo ""
echo "[Test 7/8] Verifying global CLI routing via lauburu_cli.sh lens..."
CLI_STATUS=$("$CLI_PATH" lens status --json)
if echo "$CLI_STATUS" | grep -q '"total_captures"'; then
    log_pass "lauburu_cli.sh lens status correctly dispatched to native binary"
else
    log_fail "lauburu_cli.sh lens status failed"
fi

# Test 8: Rolling Prune Mechanism
echo ""
echo "[Test 8/8] Testing historical capture prune retention..."
PRUNE_OUT=$("$BIN_PATH" prune --days 30)
if echo "$PRUNE_OUT" | grep -q "Pruned"; then
    log_pass "Prune command executed successfully"
else
    log_fail "Prune command failed"
fi

echo ""
echo "======================================================================"
echo "📊 TEST RESULTS: $PASSED_COUNT Passed, $FAILED_COUNT Failed"
echo "======================================================================"

if [ "$FAILED_COUNT" -eq 0 ]; then
    echo "🎉 ALL TESTS PASSED WITH 100% SUCCESS!"
    exit 0
else
    echo "💥 SOME TESTS FAILED."
    exit 1
fi
