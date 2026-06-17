import re

SHELL_PROMPT_RE = re.compile(r"(?:\$|%|>|#|❯|›)\s*$")
IDLE_FOOTER_RE = re.compile(
    r"(?:bypass permissions on\s*·\s*\d+\s+shells\s*·\s*esc to|tokens.*context|ctrl\+r to)",
    re.IGNORECASE,
)
CODEX_ACTIVE_RE = re.compile(r"\bWorking\s*\([^)]*esc to interrupt", re.IGNORECASE)
THINKING_RE = re.compile(
    r"(?:✶|✽|Prestidigitating|thinking|thought for\s+\d+s)",
    re.IGNORECASE,
)
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


def _nonempty_lines(pane_text):
    return [line.rstrip() for line in (pane_text or "").splitlines() if line.strip()]


def is_shell_prompt(line):
    if not line:
        return True
    stripped = line.rstrip()
    if not stripped:
        return True
    return bool(SHELL_PROMPT_RE.search(stripped))


def has_idle_prompt_boundary(lines):
    """Claude/Codex idle UI can end with a footer after the prompt line.

    The old bridge looked only at the last line. Claude Code often renders:
      ❯
      ⏵⏵ bypass permissions on · 4 shells · esc to inte…
    That final footer is not a command. It is a strong idle boundary.
    """
    if not lines:
        return True
    last = lines[-1]
    if is_shell_prompt(last):
        return True
    if IDLE_FOOTER_RE.search(last):
        for previous in reversed(lines[:-1]):
            if is_shell_prompt(previous):
                return True
            # Stop if there is real content between prompt and footer.
            if previous.strip("─ ").strip():
                break
    # Codex input prompt with typed text but no active "Working" footer.
    if re.match(r"^\s*›\s+.+", last) and not CODEX_ACTIVE_RE.search(last):
        return True
    return False


def has_active_marker_after_idle_boundary(lines):
    last_boundary_index = -1
    for idx, line in enumerate(lines):
        if is_shell_prompt(line) or IDLE_FOOTER_RE.search(line):
            last_boundary_index = idx
    tail = "\n".join(lines[last_boundary_index + 1 :])
    if not tail:
        return False
    return bool(CODEX_ACTIVE_RE.search(tail) or THINKING_RE.search(tail))


def detect_status(pane_text, git_clean):
    if not pane_text:
        return "idle"
    lines = _nonempty_lines(pane_text)
    if not lines:
        return "idle"
    last_30 = "\n".join(lines[-30:])
    idle_boundary = has_idle_prompt_boundary(lines)

    if idle_boundary:
        if BLOCKED_RE.search(last_30):
            return "blocked"
        if NEEDS_USER_RE.search(last_30):
            return "needs_user"
        if NEEDS_REVIEW_RE.search(last_30):
            return "needs_review"
        if DONE_HINT_RE.search(last_30) and git_clean:
            return "done"
        return "idle"

    recent = "\n".join(lines[-12:])
    if CODEX_ACTIVE_RE.search(recent):
        return "working"
    if THINKING_RE.search(recent) or has_active_marker_after_idle_boundary(lines):
        return "working"
    return "working"


def summarize_pane(pane_text, status, tail_lines=12):
    if status == "idle":
        return None
    lines = _nonempty_lines(pane_text)
    return "\n".join(lines[-tail_lines:]) if lines else None


def compute_state_change_at(prev_status, current_status, prev_state_change_at, now_iso):
    """Carry the per-lane lastStateChangeAt field forward unless the status
    actually changed.

    Pure helper so the bridge writer + tests share the same rule:
      - prev_status missing OR != current_status → lastStateChangeAt = now_iso
      - otherwise carry the previous value forward (or seed to now_iso if
        there is no previous value, e.g. brand-new lane file).

    Returns a string. Never raises.
    """
    if not isinstance(now_iso, str) or not now_iso:
        return None
    if not isinstance(prev_status, str) or not prev_status:
        return now_iso
    if not isinstance(current_status, str) or not current_status:
        return prev_state_change_at if isinstance(prev_state_change_at, str) and prev_state_change_at else now_iso
    if prev_status != current_status:
        return now_iso
    if isinstance(prev_state_change_at, str) and prev_state_change_at:
        return prev_state_change_at
    return now_iso


MARKER_NAMES = (
    "MCP_EVENT",
    "MCP_RESULT",
    "MCP_BLOCKER",
    "MCP_COMMIT",
    "MCP_TESTS",
    "MCP_NEXT",
)
JSON_MARKER_NAME = "AGENT_QA_RESULT_JSON"
MARKER_VALUE_CAP = 280
JSON_MARKER_CAP = 6000

_MARKER_LINE_RE = re.compile(
    r"^\s*(MCP_EVENT|MCP_RESULT|MCP_BLOCKER|MCP_COMMIT|MCP_TESTS|MCP_NEXT)\s*:\s*(.+?)\s*$",
)
_JSON_MARKER_RE = re.compile(r"^\s*AGENT_QA_RESULT_JSON\s*:\s*(.*)$")


def _strip_markers(value):
    """Cap a marker value to MARKER_VALUE_CAP and strip whitespace."""
    if not isinstance(value, str):
        return None
    text = value.replace("\r", "").strip()
    if not text:
        return None
    return text if len(text) <= MARKER_VALUE_CAP else text[: MARKER_VALUE_CAP - 1].rstrip() + "…"


def parse_mcp_markers(pane_text):
    """Pure helper: extract structured terminal markers from pane text.

    Markers are single-line key/value pairs the agent writes to its
    own stdout — never interpreted as commands, never echoed back to
    the shell. Recognised marker names live in MARKER_NAMES plus the
    multi-line JSON_MARKER_NAME (AGENT_QA_RESULT_JSON).

    Returns a dict of the form:

        {
          "MCP_RESULT":   "<sanitised string|None>",
          "MCP_BLOCKER":  "<...>",
          "MCP_COMMIT":   "<...>",
          "MCP_TESTS":    "<...>",
          "MCP_NEXT":     "<...>",
          "AGENT_QA_RESULT_JSON": <parsed dict|None>,
          "marker_count": <int>,
          "newest_line": <int — 0-based line index of the last marker, or -1 if none>,
        }

    For each non-JSON marker, the LAST occurrence wins (so a coder
    can overwrite an earlier value by emitting a fresh line).
    AGENT_QA_RESULT_JSON parses the FIRST JSON object that follows the
    label — agents are expected to emit the marker once per cycle.

    The function never raises; bad inputs return an empty marker
    dict so callers can guard cheaply.
    """
    out = {name: None for name in MARKER_NAMES}
    out[JSON_MARKER_NAME] = None
    out["marker_count"] = 0
    out["newest_line"] = -1
    if not isinstance(pane_text, str) or not pane_text:
        return out
    lines = pane_text.splitlines()
    json_buffer = None
    json_buffer_start = -1
    for idx, line in enumerate(lines):
        if json_buffer is not None:
            json_buffer.append(line)
            joined = "\n".join(json_buffer)
            try:
                import json as _json
                parsed = _json.loads(joined)
            except (ValueError, TypeError):
                if len(joined) > JSON_MARKER_CAP:
                    json_buffer = None
                continue
            if isinstance(parsed, dict):
                out[JSON_MARKER_NAME] = parsed
                out["marker_count"] += 1
                out["newest_line"] = idx
            json_buffer = None
            continue
        m = _MARKER_LINE_RE.match(line)
        if m:
            name, value = m.group(1), m.group(2)
            sanitised = _strip_markers(value)
            if sanitised:
                out[name] = sanitised
                out["marker_count"] += 1
                out["newest_line"] = idx
            continue
        j = _JSON_MARKER_RE.match(line)
        if j:
            tail = j.group(1).strip()
            if tail.startswith("{") and tail.endswith("}"):
                try:
                    import json as _json
                    parsed = _json.loads(tail)
                except (ValueError, TypeError):
                    parsed = None
                if isinstance(parsed, dict):
                    out[JSON_MARKER_NAME] = parsed
                    out["marker_count"] += 1
                    out["newest_line"] = idx
                continue
            if tail.startswith("{"):
                json_buffer = [tail]
                json_buffer_start = idx
                continue
            json_buffer = []
            json_buffer_start = idx
    return out


def marker_hash(markers):
    """Stable short hash of the non-JSON marker values + a count.

    Used by bridge-watch.sh to fire a fresh snapshot when ANY
    marker value changes between ticks. Cheap (deterministic
    string concat) and intentionally NOT cryptographic — the
    only consumers are local watch loops.
    """
    if not isinstance(markers, dict):
        return ""
    parts = []
    for name in MARKER_NAMES:
        v = markers.get(name)
        parts.append(f"{name}={v if isinstance(v, str) else ''}")
    qa = markers.get(JSON_MARKER_NAME)
    if isinstance(qa, dict):
        parts.append(f"qa.status={qa.get('status') or ''}")
        parts.append(f"qa.gate={qa.get('gate') or ''}")
        parts.append(f"qa.platform={qa.get('platform') or ''}")
    seed = " || ".join(parts)
    h = 0x811c9dc5
    for ch in seed:
        h ^= ord(ch)
        h = (h * 0x01000193) & 0xFFFFFFFF
    return f"{h:08x}"


def heartbeat_envelope(now_iso, prev_state_change_at, prev_status, current_status, source="tmux_bridge"):
    """Build the heartbeat fields the bridge attaches to every lane row.

    Schema:
      - lastSeenAt        — bumped on every snapshot regardless of state
      - lastStateChangeAt — bumped only when status changes (carry-forward
        otherwise)
      - source            — provenance, defaults to "tmux_bridge"
    """
    return {
        "lastSeenAt": now_iso,
        "lastStateChangeAt": compute_state_change_at(prev_status, current_status, prev_state_change_at, now_iso),
        "source": source,
    }
