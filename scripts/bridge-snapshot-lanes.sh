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
import urllib.error
import urllib.request
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

# ── mark-agent-done.sh ingest (terminal_summary source) ───────────────
# scripts/mark-agent-done.sh writes data/agent-status/<agent>.json with
# { agent, status, task, summary, verification, nextAction, updatedAt }.
# That's the canonical owner-tap "I just finished X" trail; we lift
# those rows into TerminalSummaryEntry[] so the same data feeds the
# connector terminal_summary surface.

MARK_DONE_DIR = os.path.join(ROOT, "data", "agent-status")
AGENT_TO_LANE = {
    "claude": "claude",
    "codex": "codex",
    "claude-code-guide": "claude_chat",
    # "other" is intentionally NOT mapped — refuse unknown lanes at
    # write time per docs/CONNECTOR_SECURITY_MODEL.md.
}

def load_terminal_entries():
    entries = []
    if not os.path.isdir(MARK_DONE_DIR):
        return entries
    for name in sorted(os.listdir(MARK_DONE_DIR)):
        if not name.endswith(".json"):
            continue
        agent = name[:-5]  # strip ".json"
        lane = AGENT_TO_LANE.get(agent)
        if lane is None:
            continue
        path = os.path.join(MARK_DONE_DIR, name)
        try:
            with open(path) as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        at = data.get("updatedAt")
        if not isinstance(at, str) or not at:
            continue
        entry = {
            "laneId": lane,
            "at": at,
            "summary": redact(truncate(str(data.get("summary") or ""), 1200) or ""),
            "verification": redact(truncate(str(data.get("verification") or ""), 240) or ""),
            "nextAction": redact(truncate(str(data.get("nextAction") or ""), 240) or ""),
            "exitCode": None,
        }
        entries.append(entry)
    # Most recent first; cap 50 entries.
    entries.sort(key=lambda e: e["at"], reverse=True)
    return entries[:50]

def load_latest_agent_status():
    """Return the newest mark-agent-done status row, sanitized.

    This feeds connector_work_status so project.get_work_status reflects
    the last meaningful lane update instead of a hardcoded bridge line.
    """
    rows = []
    if not os.path.isdir(MARK_DONE_DIR):
        return None
    for name in sorted(os.listdir(MARK_DONE_DIR)):
        if not name.endswith(".json"):
            continue
        path = os.path.join(MARK_DONE_DIR, name)
        try:
            with open(path) as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        updated_at = data.get("updatedAt")
        task = data.get("task")
        if not isinstance(updated_at, str) or not isinstance(task, str) or not task:
            continue
        rows.append({
            "agent": str(data.get("agent") or name[:-5]),
            "status": str(data.get("status") or "working"),
            "task": redact(truncate(task, 280) or ""),
            "summary": redact(truncate(str(data.get("summary") or ""), 200) or ""),
            "verification": redact(truncate(str(data.get("verification") or ""), 200) or ""),
            "nextAction": redact(truncate(str(data.get("nextAction") or ""), 280) or ""),
            "updatedAt": updated_at,
        })
    rows.sort(key=lambda r: r["updatedAt"], reverse=True)
    return rows[0] if rows else None

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

coder_lanes_payload = {
    "schemaVersion": 1,
    "generatedAt": now_iso,
    "lanes": rows,
}

# ── terminal_summary ──────────────────────────────────────────────────
terminal_entries = load_terminal_entries()
latest_agent_status = load_latest_agent_status()
terminal_summary_payload = {
    "schemaVersion": 1,
    "generatedAt": now_iso,
    "entries": terminal_entries,
}

# ── handoff (bridge-derived; owner-only fields stay null/empty) ───────
def lane_row(lane_id):
    for r in rows:
        if r["laneId"] == lane_id:
            return r
    return None

claude_row = lane_row("claude")
codex_row = lane_row("codex")

handoff_payload = {
    "schemaVersion": 1,
    "generatedAt": now_iso,
    "latestClaudePrompt": (claude_row or {}).get("lastPromptId"),
    "latestCodexPrompt": (codex_row or {}).get("lastPromptId"),
    # Owner-only fields. The bridge MUST NOT fabricate these — they
    # gate the in-app Dispatch button. See docs/CHATGPT_CONNECTOR_STATE_CONTRACT.md.
    "manualSteps": [],
    "doNotTouch": [],
    "safeToBuild": False,
    "safeToBuildReason":
        "Bridge-derived handoff. Owner has not flipped safeToBuild=true via the in-app Admin/Dev surface.",
}

# Defense-in-depth: redact every string in the bridge-derived payloads.
def deep_redact(value):
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, list):
        return [deep_redact(v) for v in value]
    if isinstance(value, dict):
        return {k: deep_redact(v) for k, v in value.items()}
    return value

handoff_payload = deep_redact(handoff_payload)
terminal_summary_payload = deep_redact(terminal_summary_payload)

# ── Atomic-replace writers ────────────────────────────────────────────
def write_json(path, payload):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")
    os.replace(tmp, path)

agg_path = os.path.join(OUT_DIR, "coder_lanes.json")
write_json(agg_path, coder_lanes_payload)

terminal_path = os.path.join(OUT_DIR, "terminal_summary.json")
write_json(terminal_path, terminal_summary_payload)

handoff_path = os.path.join(OUT_DIR, "handoff.json")
write_json(handoff_path, handoff_payload)

for row in rows:
    write_json(os.path.join(OUT_DIR, f"{row['laneId']}.json"), row)

print(f"wrote {agg_path}")
for row in rows:
    print(
        f"  lane={row['laneId']} status={row['status']} "
        f"dirty={len(row['dirtyFiles'])} "
        f"currentPrompt={row['currentPromptId']} "
        f"lastPrompt={row['lastPromptId']}"
    )
print(f"wrote {terminal_path} (entries={len(terminal_entries)})")
print(f"wrote {handoff_path}")

# ── Optional Supabase upsert (gated on env vars) ──────────────────────
# Bridge stays local-only unless SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY
# are present in the writer env or a local ignored env file. The
# service-role key bypasses RLS, so callers MUST keep these vars only on
# Aaron's Mac/server writer (never in CI, never in mobile EXPO_PUBLIC_*,
# never in shell history).
#
# Hardcoded targets only — no caller-supplied table names. The five
# connector_* tables in supabase/migrations/0003_connector_status_tables.sql
# are the only write paths.

WRITER_ENV_FILES = [
    os.path.join(ROOT, ".env.local"),
    os.path.join(ROOT, ".env.writer"),
    os.path.join(ROOT, ".env"),
    os.path.join(ROOT, "cloudflare-worker", ".dev.vars"),
]
WRITER_ENV_KEYS = {"SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"}

def load_writer_env_files():
    """Load WRITER_ENV_KEYS from local gitignored env files.

    Earlier-listed files take priority (do NOT override an already-set
    env). Only key NAMES are logged; values never reach stdout. Returns
    a dict mapping each WRITER_ENV_KEYS key to the relative file path
    it came from (or 'env' / 'missing').
    """
    provenance = {k: ("env" if os.environ.get(k) else "missing") for k in WRITER_ENV_KEYS}
    for env_path in WRITER_ENV_FILES:
        if not os.path.isfile(env_path):
            continue
        try:
            with open(env_path) as f:
                lines = f.readlines()
        except OSError:
            continue
        for line in lines:
            raw = line.strip()
            if not raw or raw.startswith("#") or "=" not in raw:
                continue
            key, value = raw.split("=", 1)
            key = key.strip()
            if key not in WRITER_ENV_KEYS or os.environ.get(key):
                continue
            value = value.strip().strip('"').strip("'")
            if value:
                os.environ[key] = value
                rel = os.path.relpath(env_path, ROOT)
                provenance[key] = rel
    return provenance

WRITER_ENV_PROVENANCE = load_writer_env_files()
print("supabase writer env (names only, never values):")
for key in sorted(WRITER_ENV_KEYS):
    src = WRITER_ENV_PROVENANCE.get(key, "missing")
    print(f"  {key}: {src}")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

def _supabase_request(method, path, body):
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("apikey", SUPABASE_KEY)
    req.add_header("Authorization", f"Bearer {SUPABASE_KEY}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    req.add_header("Prefer", "resolution=merge-duplicates,return=minimal")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, ""
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")[:200]
    except Exception as e:  # noqa: BLE001
        return 0, str(e)[:200]

def upsert_supabase():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("supabase: skip (env_missing)")
        return
    if not SUPABASE_URL.startswith("https://"):
        print("supabase: skip (env_url_invalid)")
        return
    if not (SUPABASE_KEY.startswith("eyJ") or SUPABASE_KEY.startswith("sb_secret_")):
        print("supabase: skip (env_key_invalid)")
        return

    print("supabase: upserting to configured project")

    # work_status (single row, id='current').
    current_priority = latest_agent_status["task"] if latest_agent_status else "MCP terminal bridge live; Worker reads Supabase."
    next_action = latest_agent_status["nextAction"] if latest_agent_status and latest_agent_status["nextAction"] else "Owner-tap workflow dispatch when ready."
    current_blocker = latest_agent_status["summary"] if latest_agent_status and latest_agent_status["status"] == "blocked" else None
    last_commit_message = latest_agent_status["summary"] if latest_agent_status else ""
    work_status_payload = {
        "schemaVersion": 1,
        "generatedAt": now_iso,
        "currentPriority": current_priority,
        "currentBlocker": current_blocker,
        "liveStatus": {
            "androidVersionCode": None,
            "iosBuildNumber": None,
            "androidPlayTrack": None,
            "iosTestflightGroup": None,
            "lastRailwayDeployAt": None,
            "cloudflareWorkerDeployed": True,
        },
        "repoStatus": {
            "head": short_head or "unknown",
            "branch": "main",
            "dirtyFileCount": len(dirty_files),
            "untrackedFileCount": 0,
            "lastCommitAt": now_iso,
            "lastCommitMessage": last_commit_message,
        },
        "nextAction": next_action,
    }
    s, body = _supabase_request("POST", "connector_work_status", [{
        "id": "current",
        "generated_at": now_iso,
        "source": "bridge",
        "payload": work_status_payload,
    }])
    print(f"  connector_work_status: HTTP {s}{(' ' + body) if s >= 400 else ''}")

    # coder_lanes (one row per lane_id).
    lane_rows = [{
        "lane_id": row["laneId"],
        "generated_at": row["lastSeenAt"] or now_iso,
        "source": "bridge",
        "payload": row,
    } for row in rows]
    s, body = _supabase_request("POST", "connector_coder_lanes", lane_rows)
    print(f"  connector_coder_lanes: HTTP {s}{(' ' + body) if s >= 400 else ''}")

    # handoff (single row, id='current').
    s, body = _supabase_request("POST", "connector_handoff", [{
        "id": "current",
        "generated_at": now_iso,
        "source": "bridge",
        "payload": handoff_payload,
    }])
    print(f"  connector_handoff: HTTP {s}{(' ' + body) if s >= 400 else ''}")

    # terminal_summary (append-only). Only insert entries newer than the
    # most recent existing entry to avoid duplicate inserts on every
    # bridge run. For Stage 1 we just push every entry on the wire and
    # rely on the retention sweep to trim — the entries are already
    # capped at 50 in load_terminal_entries().
    if terminal_entries:
        ts_rows = [{
            "lane_id": e["laneId"],
            "generated_at": e["at"],
            "source": "bridge",
            "payload": e,
        } for e in terminal_entries]
        s, body = _supabase_request("POST", "connector_terminal_summary", ts_rows)
        print(f"  connector_terminal_summary: HTTP {s}{(' ' + body) if s >= 400 else ''} (entries={len(ts_rows)})")
    else:
        print("  connector_terminal_summary: skip (0 entries)")

upsert_supabase()
PY
