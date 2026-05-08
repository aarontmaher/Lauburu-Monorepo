#!/usr/bin/env python3
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from bridge_snapshot_classifier import (  # noqa: E402
    compute_state_change_at,
    detect_status,
    heartbeat_envelope,
    summarize_pane,
)

FIXTURE_DIR = os.path.join(ROOT, "scripts", "fixtures", "bridge-snapshot-classifier")

EXPECTED = {
    "claude-idle-with-suggestion.txt": "idle",
    "claude-active-thinking.txt": "working",
    "claude-active-shell.txt": "working",
    "claude-completed-summary-awaiting-input.txt": "idle",
    "codex-idle.txt": "idle",
    "codex-active.txt": "working",
}


def main() -> int:
    for name, expected in EXPECTED.items():
        path = os.path.join(FIXTURE_DIR, name)
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        actual = detect_status(text, git_clean=False)
        if actual != expected:
            print(f"✗ {name}: expected {expected}, got {actual}")
            return 1
        summary = summarize_pane(text, actual)
        if expected == "idle" and summary is not None:
            print(f"✗ {name}: idle fixture should not emit active task summary")
            return 1
        if expected == "working" and not summary:
            print(f"✗ {name}: working fixture should keep active task summary")
            return 1
        print(f"✓ {name}: {actual}")
    # ── Heartbeat / state-change rules ──────────────────────────────
    NOW_A = "2026-05-09T12:00:00Z"
    NOW_B = "2026-05-09T12:00:30Z"

    # First-ever observation: set lastStateChangeAt = now.
    if compute_state_change_at(None, "working", None, NOW_A) != NOW_A:
        print("✗ compute_state_change_at: first observation should snap to now")
        return 1

    # Same status: carry the previous lastStateChangeAt forward.
    if compute_state_change_at("working", "working", NOW_A, NOW_B) != NOW_A:
        print("✗ compute_state_change_at: same status should carry forward")
        return 1

    # Status change: snap to now.
    if compute_state_change_at("working", "idle", NOW_A, NOW_B) != NOW_B:
        print("✗ compute_state_change_at: status change should snap to now")
        return 1

    # Same status without prior lastStateChangeAt: seed to now.
    if compute_state_change_at("working", "working", None, NOW_B) != NOW_B:
        print("✗ compute_state_change_at: missing prior change-at should seed to now")
        return 1

    # Empty / missing now is rejected.
    if compute_state_change_at("working", "idle", NOW_A, "") is not None:
        print("✗ compute_state_change_at: empty now should return None")
        return 1

    # heartbeat_envelope shape and provenance.
    env = heartbeat_envelope(NOW_B, NOW_A, "working", "idle")
    if env != {"lastSeenAt": NOW_B, "lastStateChangeAt": NOW_B, "source": "tmux_bridge"}:
        print(f"✗ heartbeat_envelope on transition: got {env}")
        return 1

    env = heartbeat_envelope(NOW_B, NOW_A, "working", "working")
    if env != {"lastSeenAt": NOW_B, "lastStateChangeAt": NOW_A, "source": "tmux_bridge"}:
        print(f"✗ heartbeat_envelope carry-forward: got {env}")
        return 1

    env = heartbeat_envelope(NOW_B, None, None, "idle", source="bridge_watch")
    if env != {"lastSeenAt": NOW_B, "lastStateChangeAt": NOW_B, "source": "bridge_watch"}:
        print(f"✗ heartbeat_envelope custom source: got {env}")
        return 1

    print("✓ heartbeat / state-change rules passed.")

    print("Bridge snapshot classifier fixtures passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
