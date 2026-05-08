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
