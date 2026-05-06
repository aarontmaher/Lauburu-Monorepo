#!/usr/bin/env bash
# mark-agent-done.sh — write a structured agent-status file so the
# mobile Admin/Dev surface can show "Claude finished X" or "Codex
# blocked on Y" without anyone having to ask.
#
# Owner-only by convention — the file is read by an admin-token-
# gated backend route. Never accepts free-form shell input.
#
# Usage:
#   ./scripts/mark-agent-done.sh <agent> <status> "<task>" "<summary>" "<verification>" "<nextAction>"
#
# agent           : claude | codex | claude-code-guide | other
# status          : done | blocked | needs_review | in_progress
# task            : short label, ≤120 chars
# summary         : 1–3 sentences, no secrets
# verification    : tsc result / curl result / "n/a"
# nextAction      : one sentence
#
# Output file: data/agent-status/<agent>.json on Railway disk
# (or local repo if running locally without the backend up).
#
# Example:
#   ./scripts/mark-agent-done.sh claude done \
#     "Health Connect handler split" \
#     "Android Connect button now routes through HC handlers; Apple Health alert no longer fires on Android." \
#     "tsc clean" \
#     "Wait for v16/Build 17 device confirmation."
set -euo pipefail

AGENT="${1:-}"
STATUS="${2:-}"
TASK="${3:-}"
SUMMARY="${4:-}"
VERIFICATION="${5:-n/a}"
NEXT_ACTION="${6:-n/a}"

if [ -z "$AGENT" ] || [ -z "$STATUS" ] || [ -z "$TASK" ] || [ -z "$SUMMARY" ]; then
  cat <<EOF
Usage: $0 <agent> <status> "<task>" "<summary>" "<verification>" "<nextAction>"
  agent  : claude | codex | claude-code-guide | other
  status : done | blocked | needs_review | in_progress
EOF
  exit 1
fi

# Validate agent + status against the allowlist so a typo can't
# pollute the surface.
case "$AGENT" in
  claude|codex|claude-code-guide|other) ;;
  *) echo "::error::agent must be one of: claude codex claude-code-guide other (got '$AGENT')"; exit 1;;
esac
case "$STATUS" in
  done|blocked|needs_review|in_progress) ;;
  *) echo "::error::status must be one of: done blocked needs_review in_progress (got '$STATUS')"; exit 1;;
esac

# Resolve repo root + status dir.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
STATUS_DIR="$ROOT/data/agent-status"
mkdir -p "$STATUS_DIR"

NOW="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
OUT="$STATUS_DIR/${AGENT}.json"

# Write JSON via printf so a quote inside any field can't break the
# file (we %q each free-text value before substituting).
escape() { printf '%s' "$1" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'; }

A_TASK="$(escape "$TASK")"
A_SUMMARY="$(escape "$SUMMARY")"
A_VERIFICATION="$(escape "$VERIFICATION")"
A_NEXT="$(escape "$NEXT_ACTION")"

cat > "$OUT" <<EOF
{
  "agent": "$AGENT",
  "status": "$STATUS",
  "task": $A_TASK,
  "summary": $A_SUMMARY,
  "verification": $A_VERIFICATION,
  "nextAction": $A_NEXT,
  "updatedAt": "$NOW"
}
EOF

echo "wrote $OUT"
