#!/usr/bin/env python3
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from bridge_snapshot_classifier import detect_status, summarize_pane  # noqa: E402

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
    print("Bridge snapshot classifier fixtures passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
