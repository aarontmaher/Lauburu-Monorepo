#!/usr/bin/env bash
# bridge-snapshot-lanes.sh — Stage 1 of the local tmux bridge.
#
# Captures the lauburu (Claude) and codex-lauburu (Codex) tmux
# panes, sanitises the output per docs/CONNECTOR_SANITIZATION_RULES.md,
# classifies the lane via the documented status ladder, and writes a
# CoderLanes payload to data/agent-status/lanes/coder_lanes.json
# (plus per-lane files at data/agent-status/lanes/<laneId>.json).
#
# DOES NOT execute anything from pane content. Subprocess calls are
# fixed-argv only (tmux, git). No shell=True. No eval. No network.
#
# Usage:
#   ./scripts/bridge-snapshot-lanes.sh
#
# Output files:
#   data/agent-status/lanes/coder_lanes.json   — aggregate CoderLanes
#   data/agent-status/lanes/<laneId>.json      — per-lane CoderLaneRow
#
# Read by (planned, separate batch):
#   - chat-app /api/coder_lanes (when Express bridge route lands)
#   - cloudflare-worker /api/coder_lanes (after a POST /admin/lane-status
#     write tool ships)
#
# Lane → tmux session map is hardcoded in the python body below;
# new lanes require a doc commit + a new entry under
# docs/LOCAL_BRIDGE_COMMAND_ALLOWLIST.md.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if ! command -v tmux >/dev/null 2>&1; then
  echo "::error::tmux not installed. Install via: brew install tmux"
  exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "::error::python3 not installed. macOS ships python3 by default."
  exit 1
fi

mkdir -p "$ROOT/data/agent-status/lanes"

exec python3 - "$ROOT" <<'PY'
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

ROOT = sys.argv[1]
OUT_DIR = os.path.join(ROOT, "data", "agent-status", "lanes")
os.makedirs(OUT_DIR, exist_ok=True)

# ── Lane → tmux session map ────────────────────────────────────────────
# Adding a new lane requires adding the LaneId to:
#   chat-app/src/server/types/connector.ts (LaneId union)
#   docs/LOCAL_BRIDGE_COMMAND_ALLOWLIST.md
# before extending this map.
SESSION_MAP = [
    ("lauburu", "claude"),
    ("codex-lauburu", "codex"),
]

ALLOWED_LANES = {"claude", "codex", "claude_chat", "chatgpt", "cowork"}
ALLOWED_STATUSES = {
    "idle", "working", "blocked", "needs_user", "needs_review", "done",
}

# ── Two-pass redactor (mirrors docs/CONNECTOR_SANITIZATION_RULES.md) ──
PRESERVE_LABELS = {
    "commit", "commit_hash", "sha", "head", "ref", "branch", "version",
    "build", "build_number", "version_code", "tag", "prompt_id", "lane",
    "run_id", "submission", "eas_build", "expo_build_id",
    "androidversioncode", "iosbuildnumber", "githubrunid", "easbuildid",
    "playsubmissionid", "testflightsubmissionid",
}

LABEL_RE = re.compile(
    r"(^|[^A-Za-z0-9_])([a-z_]+)(\s*[:=]\s*)([A-Za-z0-9.\-_]+)"
)

STRIKE_PATTERNS = [
    re.compile(r"eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+"),
    re.compile(r"sk-[A-Za-z0-9_\-]{20,}"),
    re.compile(r"ghp_[A-Za-z0-9]{30,}"),
    re.compile(r"gho_[A-Za-z0-9]{30,}"),
    re.compile(r"ghs_[A-Za-z0-9]{30,}"),
    re.compile(r"whsec_[A-Za-z0-9]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"xox[abprs]-[A-Za-z0-9\-]{10,}"),
]

SENTINEL_RE = re.compile(r"\x00PRESERVE_(\d+)\x00")

def redact(text):
    if not isinstance(text, str) or not text:
        return text
    preserved = []

    def stash(m):
        lead, label, sep, value = m.group(1), m.group(2), m.group(3), m.group(4)
        if label.lower() not in PRESERVE_LABELS:
            return m.group(0)
        idx = len(preserved)
        preserved.append(value)
        return f"{lead}{label}{sep}\x00PRESERVE_{idx}\x00"

    tagged = LABEL_RE.sub(stash, text)
    for pat in STRIKE_PATTERNS:
        tagged = pat.sub("<redacted>", tagged)

    def restore(m):
        idx = int(m.group(1))
        return preserved[idx] if 0 <= idx < len(preserved) else ""

    return SENTINEL_RE.sub(restore, tagged)

# ── File-path masking (docs/CONNECTOR_SANITIZATION_RULES.md § 3) ──────
PATH_DROP_PREFIXES = (
    "node_modules/", ".expo/", "ios/build/", "android/.gradle/",
    "android/build/", "android/app/build/", "apps/mobile/ios/Pods/",
    ".cursor/", ".vscode/", ".idea/",
    "data/private-athlete-memory/", "data/agent-queue/",
)
PATH_DROP_BASENAME_RE = re.compile(
    r"^(?:\.env|\.env\.local|\.env\.production|secrets?\.json|"
    r"google-services-key\.json|.*\.pem|.*\.p12|.*\.keystore)$"
)

def mask_path(p):
    p = p.strip()
    if not p:
        return None
    if p.startswith(ROOT + "/"):
        p = p[len(ROOT) + 1:]
    if p.startswith("/Users/") or p.startswith("~") or p.startswith("/"):
        return "<host_path>"
    for prefix in PATH_DROP_PREFIXES:
        if p.startswith(prefix):
            return None
    base = os.path.basename(p)
    if PATH_DROP_BASENAME_RE.match(base):
        return None
    return p

# ── Truncate at word boundary, ≤ cap, append … ────────────────────────
def truncate(text, cap):
    if text is None:
        return None
    if len(text) <= cap:
        return text
    cut = text.rfind(" ", 0, cap)
    if cut < cap // 2:
        cut = cap
    return text[:cut].rstrip() + "…"

# ── Lane-status detection ladder ──────────────────────────────────────
SHELL_PROMPT_RE = re.compile(r"(?:\$|%|>|#|❯)\s*$")
BLOCKED_RE = re.compile(
    r"BLOCK(?:ED|ER):|cannot continue|please clarify|awaiting owner",
    re.IGNORECASE,
)
NEEDS_USER_RE = re.compile(
    r"NEEDS_USER:|awaiting input|confirm before proceeding",
    re.IGNORECASE,
)
NEEDS_REVIEW_RE = re.compile(
    r"NEEDS_REVIEW:|please review|awaiting audit",
    re.IGNORECASE,
)
DONE_HINT_RE = re.compile(
    r"\b(done|complete|completed|landed|merged)\b",
    re.IGNORECASE,
)

def is_shell_prompt(line):
    if not line:
        return True
    stripped = line.rstrip()
    if not stripped:
        return True
    return bool(SHELL_PROMPT_RE.search(stripped))

def detect_status(pane_text, git_clean):
    if not pane_text:
        return "idle"
    lines = pane_text.rstrip("\n").splitlines()
    if not lines:
        return "idle"
    last = lines[-1]
    last_30 = "\n".join(lines[-30:])
    is_prompt = is_shell_prompt(last)
    if is_prompt and BLOCKED_RE.search(last_30):
        return "blocked"
    if is_prompt and NEEDS_USER_RE.search(last_30):
        return "needs_user"
    if is_prompt and NEEDS_REVIEW_RE.search(last_30):
        return "needs_review"
    if is_prompt and DONE_HINT_RE.search(last_30) and git_clean:
        return "done"
    if not is_prompt:
        return "working"
    return "idle"

# ── Subprocess helpers (fixed argv only) ──────────────────────────────
def run(args, cwd=None, timeout=10):
    try:
        r = subprocess.run(
            args, cwd=cwd or ROOT, check=False,
            capture_output=True, text=True, timeout=timeout,
        )
        if r.returncode != 0:
            return None
        return r.stdout
    except (subprocess.TimeoutExpired, OSError, FileNotFoundError):
        return None

def list_sessions():
    out = run(["tmux", "list-sessions", "-F", "#{session_name}"])
    return [s.strip() for s in (out or "").splitlines() if s.strip()]

def capture_pane(session):
    # Last ~200 lines of session window 0 pane 0.
    target = f"{session}:0.0"
    return run(["tmux", "capture-pane", "-t", target, "-p", "-S", "-200"])

PROMPT_ID_RE = re.compile(r"PROMPT[-_]ID[:\s]+([A-Z0-9][A-Z0-9_\-]+)")

def find_prompt_id(text):
    if not text:
        return None
    matches = PROMPT_ID_RE.findall(text)
    return matches[-1] if matches else None

def git_status_dirty():
    out = run(["git", "status", "--short", "--no-renames"])
    if out is None:
        return [], True
    files = []
    clean = True
    for line in out.splitlines():
        if not line.strip():
            continue
        clean = False
        # Porcelain v1: "XY path" — 2 status chars + space + path.
        path = line[3:] if len(line) > 3 else line
        masked = mask_path(path)
        if masked and masked != "<host_path>":
            files.append(masked)
    # Cap dirty list size — schema doesn't enforce but huge lists
    # spam the connector.
    return files[:50], clean

def git_short_head():
    out = run(["git", "rev-parse", "--short", "HEAD"])
    return out.strip() if out else None

# ── Build payload ─────────────────────────────────────────────────────
CAP_SUMMARY = 1200
SUMMARY_TAIL_LINES = 12

now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
sessions_alive = set(list_sessions())
dirty_files, clean = git_status_dirty()
short_head = git_short_head()

rows = []
for session, lane in SESSION_MAP:
    if lane not in ALLOWED_LANES:
        # Defensive: refuse unknown lane id at write time.
        continue

    if session not in sessions_alive:
        rows.append({
            "laneId": lane,
            "status": "idle",
            "lastSeenAt": None,
            "currentPromptId": None,
            "lastPromptId": None,
            "lastSummary": None,
            "lastCommit": short_head,
            "lastTypecheckResult": None,
            "dirtyFiles": [],
            "nextPrompt": None,
        })
        continue

    pane = capture_pane(session) or ""
    status = detect_status(pane, clean)
    if status not in ALLOWED_STATUSES:
        status = "idle"

    prompt_id = find_prompt_id(pane)

    tail_lines = [l for l in pane.rstrip("\n").splitlines() if l.strip()]
    summary_raw = "\n".join(tail_lines[-SUMMARY_TAIL_LINES:]) if tail_lines else ""
    summary = redact(summary_raw)
    summary = truncate(summary, CAP_SUMMARY)

    current_prompt = prompt_id if status in (
        "working", "needs_user", "needs_review", "blocked",
    ) else None

    row = {
        "laneId": lane,
        "status": status,
        "lastSeenAt": now_iso,
        "currentPromptId": current_prompt,
        "lastPromptId": prompt_id,
        "lastSummary": summary if summary else None,
        "lastCommit": short_head,
        "lastTypecheckResult": None,
        # Repo-wide dirty list: per-lane attribution is a Stage 2 concern.
        "dirtyFiles": dirty_files,
        "nextPrompt": None,
    }

    # Defense-in-depth: re-redact every string-shaped field at the
    # response boundary, even though the inputs already passed through
    # redact() above. Cheap; survives a future caller forgetting to.
    for k, v in list(row.items()):
        if isinstance(v, str):
            row[k] = redact(v)
        elif isinstance(v, list):
            row[k] = [redact(x) if isinstance(x, str) else x for x in v]

    rows.append(row)

payload = {
    "schemaVersion": 1,
    "generatedAt": now_iso,
    "lanes": rows,
}

agg_path = os.path.join(OUT_DIR, "coder_lanes.json")
tmp_path = agg_path + ".tmp"
with open(tmp_path, "w") as f:
    json.dump(payload, f, indent=2)
    f.write("\n")
os.replace(tmp_path, agg_path)

for row in rows:
    p = os.path.join(OUT_DIR, f"{row['laneId']}.json")
    tmp = p + ".tmp"
    with open(tmp, "w") as f:
        json.dump(row, f, indent=2)
        f.write("\n")
    os.replace(tmp, p)

print(f"wrote {agg_path}")
for row in rows:
    print(
        f"  lane={row['laneId']} status={row['status']} "
        f"dirty={len(row['dirtyFiles'])} "
        f"currentPrompt={row['currentPromptId']} "
        f"lastPrompt={row['lastPromptId']}"
    )
PY
