#!/usr/bin/env python3
"""
06_scripts_and_tooling/export_and_close_chrome_tabs.py
=====================================================
Zero-Loss Chrome Tab Archiver & Cognitive Preserver.
Queries all active Google Chrome windows and tabs via AppleScript,
exports titles, URLs, and timestamps directly into the Obsidian Vault,
and provides safe closure options without losing cognitive ideas.
Strictly complies with soul.md Cardinal Law #1 (Zero-Mock / Zero-Simulation).
"""

import os
import sys
import time
import subprocess
import argparse
from datetime import datetime, timezone
from pathlib import Path

OBSIDIAN_DIR = Path("/Volumes/Lauburu-Monorepo/obsidian_vault/APPS_AND_FEATURES")
OBSIDIAN_DIR.mkdir(parents=True, exist_ok=True)


def get_chrome_tabs():
    scpt = '''
    tell application "Google Chrome"
        set outList to {}
        repeat with w in every window
            repeat with t in every tab of w
                set end of outList to (title of t) & "|||" & (URL of t)
            end repeat
        end repeat
        set AppleScript's text item delimiters to linefeed
        return outList as text
    end tell
    '''
    try:
        out = subprocess.check_output(["osascript", "-e", scpt], text=True)
        tabs = []
        for line in out.splitlines():
            line = line.strip()
            if "|||" in line:
                title, url = line.split("|||", 1)
                tabs.append({"title": title.strip(), "url": url.strip()})
        return tabs
    except Exception as e:
        return []


def archive_tabs(tabs, close_after=False):
    if not tabs:
        print("ℹ️ No active Google Chrome tabs found.")
        return None

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
    target_file = OBSIDIAN_DIR / f"CHROME_ARCHIVED_SESSION_{now_str}.md"

    lines = [
        "---",
        f"title: 'Archived Chrome Tabs Session - {now_str}'",
        f"date: '{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}'",
        "tags: [chrome, archived_tabs, zero_loss, obsidian_vault]",
        "---",
        "",
        f"# 🌐 Archived Chrome Tabs ({len(tabs)} Tabs Preserved)",
        "",
        "> All tabs preserved with zero loss of cognitive context prior to closing.",
        "",
        "## 📑 Preserved Tab Manifest",
        ""
    ]

    for i, t in enumerate(tabs, 1):
        lines.append(f"{i}. [{t['title'] or 'Untitled'}]({t['url']})")

    target_file.write_text("\n".join(lines))
    print(f"✅ Preserved {len(tabs)} tabs to: {target_file}")

    if close_after:
        print("🛑 Closing tabs via AppleScript...")
        close_scpt = '''
        tell application "Google Chrome"
            repeat with w in (every window)
                close (tabs of w whose URL is not "chrome://newtab/")
            end repeat
        end tell
        '''
        subprocess.run(["osascript", "-e", close_scpt])
        print("✨ Chrome tabs safely closed. Memory reclaimed!")

    return str(target_file)


def main():
    parser = argparse.ArgumentParser(description="Zero-Loss Chrome Tab Archiver")
    parser.add_argument("--close", action="store_true", help="Close tabs after saving to Obsidian")
    args = parser.parse_args()

    tabs = get_chrome_tabs()
    print(f"🔍 Discovered {len(tabs)} active tabs in Google Chrome.")
    archive_tabs(tabs, close_after=args.close)


if __name__ == "__main__":
    main()
