#!/usr/bin/env bash
# bridge-watch.sh — long-running auto-snapshot loop.
#
# Polls tmux state every $POLL_INTERVAL seconds. Runs the full
# bridge-snapshot-lanes.sh writer when EITHER:
#   (a) any lane's detected status differs from its last-known status,
#       or
#   (b) $HEARTBEAT_INTERVAL seconds have elapsed since the last full
#       writeback (heartbeat refresh — keeps lastSeenAt under the
#       freshness window).
#
# Cost control:
#   - Lightweight check (tmux capture + classifier) every poll, no
#     subprocess fan-out, no Supabase writes.
#   - Full snapshot only on transition or heartbeat — typical day
#     produces 30–60 writes (one per state change + one per minute
#     while terminals are quiet).
#   - Debounced: the script honours $MIN_WRITE_INTERVAL after every
#     full snapshot so a flapping pane can't burn writes.
#
# Anti-rules:
#   - No Supabase write paths beyond what bridge-snapshot-lanes.sh
#     already enforces.
#   - No subprocess command other than the same allowlist that script
#     uses (tmux, git, python3 via the snapshot writer).
#   - Hard-fails on macOS only because the rest of the bridge is
#     macOS-targeted today.
#
# Usage:
#   ./scripts/bridge-watch.sh                            # run forever
#   ./scripts/bridge-watch.sh --once                     # one tick + exit
#   POLL_INTERVAL=10 ./scripts/bridge-watch.sh           # tweak poll
#   HEARTBEAT_INTERVAL=15 ./scripts/bridge-watch.sh      # tweak heartbeat
#
# Stop with Ctrl-C.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SNAPSHOT_SCRIPT="$SCRIPT_DIR/bridge-snapshot-lanes.sh"

if [[ ! -x "$SNAPSHOT_SCRIPT" ]]; then
  echo "::error::$SNAPSHOT_SCRIPT missing or not executable."
  exit 1
fi
if ! command -v tmux >/dev/null 2>&1; then
  echo "::error::tmux not installed. brew install tmux"
  exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "::error::python3 not installed."
  exit 1
fi

POLL_INTERVAL="${POLL_INTERVAL:-10}"
HEARTBEAT_INTERVAL="${HEARTBEAT_INTERVAL:-15}"
MIN_WRITE_INTERVAL="${MIN_WRITE_INTERVAL:-5}"
ONCE=0
for arg in "$@"; do
  case "$arg" in
    --once) ONCE=1 ;;
    --poll-interval=*) POLL_INTERVAL="${arg#*=}" ;;
    --heartbeat-interval=*) HEARTBEAT_INTERVAL="${arg#*=}" ;;
    --min-write-interval=*) MIN_WRITE_INTERVAL="${arg#*=}" ;;
    --help|-h)
      sed -n '2,40p' "$0"
      exit 0
      ;;
  esac
done

STATE_DIR="$ROOT/data/agent-status/lanes"
mkdir -p "$STATE_DIR"
WATCH_STATE_FILE="$STATE_DIR/.bridge-watch-state.json"

run_classifier() {
  # Print "lane_id status marker_hash" lines for every session in the
  # SESSION_MAP. A change in EITHER the status OR the marker_hash
  # triggers a fresh snapshot in the watch loop above.
  python3 - "$ROOT" <<'PY'
import os
import subprocess
import sys

ROOT = sys.argv[1]
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from bridge_snapshot_classifier import detect_status, marker_hash, parse_mcp_markers

SESSION_MAP = [
    ("lauburu", "claude"),
    ("codex-lauburu", "codex"),
]


def run(args):
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=5)
        return r.stdout if r.returncode == 0 else ""
    except (subprocess.TimeoutExpired, OSError, FileNotFoundError):
        return ""


def list_sessions():
    out = run(["tmux", "list-sessions", "-F", "#{session_name}"])
    return {line.strip() for line in out.splitlines() if line.strip()}


def capture_pane(session):
    return run(["tmux", "capture-pane", "-t", f"{session}:0.0", "-p", "-S", "-200"])


def git_clean():
    out = run(["git", "status", "--short", "--no-renames"])
    return out.strip() == ""


sessions = list_sessions()
clean = git_clean()
for session, lane in SESSION_MAP:
    if session not in sessions:
        print(f"{lane}\tidle\t")
        continue
    pane = capture_pane(session)
    status = detect_status(pane, clean)
    h = marker_hash(parse_mcp_markers(pane))
    print(f"{lane}\t{status}\t{h}")
PY
}

read_known_state() {
  if [[ ! -f "$WATCH_STATE_FILE" ]]; then
    echo ""
    return
  fi
  cat "$WATCH_STATE_FILE"
}

write_known_state() {
  local current_state="$1"
  printf '%s' "$current_state" > "$WATCH_STATE_FILE"
}

# Returns 0 if state changed, 1 if unchanged.
state_changed() {
  local prev="$1"
  local curr="$2"
  [[ "$prev" != "$curr" ]]
}

run_full_snapshot() {
  local reason="$1"
  echo "[$(date -u +%FT%TZ)] bridge-watch: full snapshot ($reason)"
  bash "$SNAPSHOT_SCRIPT" >/dev/null 2>&1 || {
    echo "[$(date -u +%FT%TZ)] bridge-watch: snapshot FAILED — see scripts/bridge-snapshot-lanes.sh logs."
    return 1
  }
  echo "[$(date -u +%FT%TZ)] bridge-watch: snapshot ok."
  return 0
}

epoch_seconds() { date -u +%s; }

last_write_at=0

tick() {
  local now
  now="$(epoch_seconds)"

  local current_state
  current_state="$(run_classifier 2>/dev/null || true)"
  if [[ -z "$current_state" ]]; then
    echo "[$(date -u +%FT%TZ)] bridge-watch: classifier produced no state; skipping tick."
    return 0
  fi

  local prev_state
  prev_state="$(read_known_state)"

  local since_write=$((now - last_write_at))
  local must_write=0
  local reason=""

  if [[ -z "$prev_state" ]]; then
    must_write=1
    reason="first-tick / no prior state"
  elif state_changed "$prev_state" "$current_state"; then
    if (( since_write < MIN_WRITE_INTERVAL )); then
      echo "[$(date -u +%FT%TZ)] bridge-watch: state changed, but $since_write s < min-write $MIN_WRITE_INTERVAL s; will retry next tick."
    else
      must_write=1
      reason="state change: $(echo "$prev_state" | tr '\n' ',')→$(echo "$current_state" | tr '\n' ',')"
    fi
  elif (( since_write >= HEARTBEAT_INTERVAL )); then
    must_write=1
    reason="heartbeat ($since_write s ≥ $HEARTBEAT_INTERVAL s)"
  fi

  if (( must_write )); then
    if run_full_snapshot "$reason"; then
      write_known_state "$current_state"
      last_write_at="$now"
    fi
  fi
}

# Trap so Ctrl-C exits cleanly.
trap 'echo "[$(date -u +%FT%TZ)] bridge-watch: stopped."; exit 0' INT TERM

if (( ONCE )); then
  tick
  exit 0
fi

echo "[$(date -u +%FT%TZ)] bridge-watch: starting loop (poll=${POLL_INTERVAL}s, heartbeat=${HEARTBEAT_INTERVAL}s, min-write=${MIN_WRITE_INTERVAL}s)."
while :; do
  tick
  sleep "$POLL_INTERVAL"
done
