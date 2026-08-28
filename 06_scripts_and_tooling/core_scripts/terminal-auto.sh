#!/usr/bin/env bash
set -euo pipefail

# Bootstrap the laptop terminal workspace from one command.
# Intended for Termius startup snippets or a local Terminal tab.
#
# Starts:
#   - mcp-auto      MCP automation bundle (dry-run prompt dispatch by default)
#   - codex-lauburu Codex / Claude / Agent workspace if missing
#   - lauburu       standalone Claude Code session if missing
#
# Then attaches to the requested session.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ATTACH_TARGET="${TERMINAL_AUTO_ATTACH:-codex-lauburu}"
DISPATCH_MODE="dry-run"
ATTACH=1

usage() {
  cat <<'EOF'
Usage: scripts/terminal-auto.sh [flags]

Flags:
  --attach <name>      session to attach after boot (default codex-lauburu)
                       known: codex-lauburu, lauburu, mcp-auto
  --dispatch           start mcp-auto with real prompt dispatch
  --dry-run            start mcp-auto with dry-run prompt dispatch (default)
  --no-attach          boot sessions only
  --help               print this help

Recommended Termius startup snippet:
  cd /Users/aaronmaher/LauburuGrapplingMap-mobile && npm run terminal:auto

Switch inside codex-lauburu:
  Ctrl-b 0  Codex
  Ctrl-b 1  Claude Code
  Ctrl-b 2  Agent
  Ctrl-b 6  Shell
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --attach)
      ATTACH_TARGET="${2:-}"
      if [[ -z "$ATTACH_TARGET" ]]; then echo "--attach requires a session name" >&2; exit 2; fi
      shift 2
      ;;
    --dispatch) DISPATCH_MODE="dispatch"; shift ;;
    --dry-run) DISPATCH_MODE="dry-run"; shift ;;
    --no-attach) ATTACH=0; shift ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown flag: $1" >&2; usage >&2; exit 2 ;;
  esac
done

ensure_codex_workspace() {
  if tmux has-session -t codex-lauburu 2>/dev/null; then
    return
  fi

  tmux new-session -d -s codex-lauburu -n codex -c "$ROOT" 'codex --dangerously-bypass-approvals-and-sandbox'
  tmux new-window -t codex-lauburu -n claude -c "$ROOT" 'claude --dangerously-skip-permissions'
  tmux new-window -t codex-lauburu -n agent -c "$ROOT"
  tmux new-window -t codex-lauburu -n codex-spare -c "$ROOT"
  tmux new-window -t codex-lauburu -n claude-spare -c "$ROOT"
  tmux new-window -t codex-lauburu -n agent-spare -c "$ROOT"
  tmux new-window -t codex-lauburu -n shell -c "$ROOT"
  tmux select-window -t codex-lauburu:0
}

ensure_claude_standalone() {
  if tmux has-session -t lauburu 2>/dev/null; then
    return
  fi
  tmux new-session -d -s lauburu -c "$ROOT" 'claude --dangerously-skip-permissions'
}

ensure_mcp_auto() {
  if [[ "$DISPATCH_MODE" == "dispatch" ]]; then
    "$ROOT/scripts/mcp-auto.sh" --dispatch --no-attach
  else
    "$ROOT/scripts/mcp-auto.sh" --dry-run --no-attach
  fi
}

ensure_codex_workspace
ensure_claude_standalone
ensure_mcp_auto

echo "terminal-auto: sessions ready"
tmux list-sessions

if [[ "$ATTACH" == "1" ]]; then
  exec tmux attach -t "$ATTACH_TARGET"
fi
