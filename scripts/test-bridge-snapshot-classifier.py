#!/usr/bin/env python3
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from bridge_snapshot_classifier import (  # noqa: E402
    JSON_MARKER_NAME,
    MARKER_NAMES,
    compute_state_change_at,
    detect_status,
    heartbeat_envelope,
    marker_hash,
    parse_mcp_markers,
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

    # ── Marker parser ───────────────────────────────────────────────

    empty = parse_mcp_markers("")
    if empty["marker_count"] != 0 or empty["newest_line"] != -1:
        print(f"✗ parse_mcp_markers: empty input should yield no markers; got {empty}")
        return 1

    if parse_mcp_markers(None)["marker_count"] != 0:
        print("✗ parse_mcp_markers: None input should not crash")
        return 1

    pane = """
shell prompt
some text
MCP_RESULT: shipped FS-020 import parser
MCP_TESTS: 14/14 passed
MCP_COMMIT: c193ef6
unrelated chatter
MCP_NEXT: bundle FS-021 with v21
MCP_RESULT: superseded earlier result, latest one wins
""".strip()
    parsed = parse_mcp_markers(pane)
    if parsed["MCP_RESULT"] != "superseded earlier result, latest one wins":
        print(f"✗ parse_mcp_markers: latest occurrence should win; got {parsed['MCP_RESULT']}")
        return 1
    if parsed["MCP_TESTS"] != "14/14 passed":
        print(f"✗ parse_mcp_markers: MCP_TESTS missing; got {parsed['MCP_TESTS']}")
        return 1
    if parsed["MCP_COMMIT"] != "c193ef6":
        print(f"✗ parse_mcp_markers: MCP_COMMIT missing; got {parsed['MCP_COMMIT']}")
        return 1
    if parsed["MCP_NEXT"] != "bundle FS-021 with v21":
        print(f"✗ parse_mcp_markers: MCP_NEXT missing; got {parsed['MCP_NEXT']}")
        return 1
    if parsed["MCP_BLOCKER"] is not None:
        print(f"✗ parse_mcp_markers: MCP_BLOCKER should be None; got {parsed['MCP_BLOCKER']}")
        return 1
    if parsed["MCP_EVENT"] is not None:
        print(f"✗ parse_mcp_markers: MCP_EVENT should be None when absent; got {parsed['MCP_EVENT']}")
        return 1
    if parsed["marker_count"] != 5:
        print(f"✗ parse_mcp_markers: expected 5 markers; got {parsed['marker_count']}")
        return 1
    if parsed["newest_line"] < 0:
        print("✗ parse_mcp_markers: newest_line not recorded")
        return 1

    event = parse_mcp_markers("MCP_EVENT: tests_started\nMCP_TESTS: running")
    if event["MCP_EVENT"] != "tests_started" or event["marker_count"] != 2:
        print(f"✗ parse_mcp_markers: MCP_EVENT should be parsed for immediate writeback; got {event}")
        return 1

    # AGENT_QA_RESULT_JSON inline
    pane_inline = 'AGENT_QA_RESULT_JSON: {"status": "pass", "gate": "release_gate", "platform": "android"}'
    inline = parse_mcp_markers(pane_inline)
    qa = inline.get(JSON_MARKER_NAME)
    if not isinstance(qa, dict) or qa.get("status") != "pass":
        print(f"✗ parse_mcp_markers: inline AGENT_QA_RESULT_JSON not parsed; got {qa}")
        return 1

    # AGENT_QA_RESULT_JSON multi-line
    pane_multi = """
AGENT_QA_RESULT_JSON:
{
  "status": "partial",
  "gate": "release_gate",
  "platform": "ios"
}
trailing line
""".strip()
    multi = parse_mcp_markers(pane_multi)
    qa_multi = multi.get(JSON_MARKER_NAME)
    if not isinstance(qa_multi, dict) or qa_multi.get("platform") != "ios":
        print(f"✗ parse_mcp_markers: multi-line AGENT_QA_RESULT_JSON not parsed; got {qa_multi}")
        return 1

    # Bad JSON should not crash and should not populate the marker.
    pane_bad = "AGENT_QA_RESULT_JSON: {not json}"
    bad = parse_mcp_markers(pane_bad)
    if bad.get(JSON_MARKER_NAME) is not None:
        print("✗ parse_mcp_markers: invalid JSON marker should yield None")
        return 1

    # Cap on long marker values
    long_value = "x" * 600
    capped = parse_mcp_markers(f"MCP_RESULT: {long_value}")
    if capped["MCP_RESULT"] is None or len(capped["MCP_RESULT"]) > 280:
        print(f"✗ parse_mcp_markers: long value should be capped to 280 chars; got len={len(capped['MCP_RESULT'] or '')}")
        return 1
    if not capped["MCP_RESULT"].endswith("…"):
        print("✗ parse_mcp_markers: capped value should end with ellipsis")
        return 1

    # Whitespace/empty values
    blank = parse_mcp_markers("MCP_RESULT:    \nMCP_BLOCKER:")
    if blank["MCP_RESULT"] is not None or blank["MCP_BLOCKER"] is not None:
        print("✗ parse_mcp_markers: empty/whitespace values should be dropped")
        return 1

    # marker_hash stability
    h1 = marker_hash(parse_mcp_markers(pane))
    h2 = marker_hash(parse_mcp_markers(pane))
    if h1 != h2:
        print("✗ marker_hash: identical input should produce identical hash")
        return 1
    h3 = marker_hash(parse_mcp_markers(pane + "\nMCP_RESULT: changed"))
    if h3 == h1:
        print("✗ marker_hash: changed marker should change hash")
        return 1

    # marker_hash on missing input
    if marker_hash(None) != "":
        print("✗ marker_hash: None should hash to empty string")
        return 1
    if marker_hash({}) == "":
        print("✗ marker_hash: empty dict should still produce a hash")
        return 1

    # All marker names exposed in MARKER_NAMES
    if len(MARKER_NAMES) != 6:
        print(f"✗ MARKER_NAMES: expected 6 names; got {len(MARKER_NAMES)}")
        return 1

    print("✓ marker parser rules passed.")

    print("Bridge snapshot classifier fixtures passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
