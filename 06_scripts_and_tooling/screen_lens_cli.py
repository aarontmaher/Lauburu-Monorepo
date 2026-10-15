#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Screen Lens CLI Tool (screen-lens)
==================================
Subsystem: 06_scripts_and_tooling/screen_lens_cli.py
Lauburu Mesh Ecosystem — 2026

Empirical CLI runner and query tool for Lauburu Screen Lens.
Resolves direct SQLite execution attempts by providing an ergonomic,
zero-lock terminal interface to the active Screen Lens SQLite store (~/.lauburu/screen_lens.sqlite).
"""

import os
import sys
import argparse
import sqlite3
import subprocess
import time
from pathlib import Path

DB_PATH = Path(os.path.expanduser("~/.lauburu/screen_lens.sqlite"))
PID_FILE = Path(os.path.expanduser("~/.lauburu/screen_lens.pid"))
BINARY_PATH = Path("/Volumes/Lauburu-Monorepo/01_apps/screen_lens/bin/lauburu-lens")

def _init_local_db_schema():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS captures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            active_app_name TEXT,
            active_window_title TEXT,
            raw_text_summary TEXT
        );
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ocr_text_blocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            capture_id INTEGER,
            text TEXT
        );
        """
    )
    conn.commit()
    conn.close()


def _proxy_to_l1():
    import shlex
    remote_script = "/Volumes/Lauburu-Monorepo/06_scripts_and_tooling/screen_lens_cli.py"
    quoted_args = " ".join(shlex.quote(a) for a in sys.argv[1:])
    for host in ("aaronmaher@100.119.199.76", "aaron@100.119.199.76", "aaron@192.168.8.143"):
        ssh_cmd = [
            "ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=accept-new", "-o", "ConnectTimeout=2",
            host,
            f"python3 {remote_script} {quoted_args}"
        ]
        res = subprocess.run(ssh_cmd, stderr=subprocess.DEVNULL)
        if res.returncode == 0:
            sys.exit(0)
    _init_local_db_schema()


def get_db_connection():
    if not DB_PATH.exists():
        _proxy_to_l1()
    _init_local_db_schema()
    # Open in URI read-only mode to prevent write contention with active daemon
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    return conn

def get_daemon_pid():
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
            # Check if alive
            os.kill(pid, 0)
            return pid
        except (ValueError, OSError):
            return None
    # Fallback to pgrep (macOS/Linux lauburu-lens or Android lauburu_lens_android.py)
    for pattern in ("lauburu-lens start", "lauburu_lens_android.py start"):
        try:
            res = subprocess.check_output(["pgrep", "-f", pattern], text=True).strip()
            if res:
                return int(res.splitlines()[0])
        except Exception:
            pass
    return None

def cmd_status(args):
    pid = get_daemon_pid()
    conn = get_db_connection()
    cur = conn.cursor()
    
    captures_count = cur.execute("SELECT COUNT(*) FROM captures;").fetchone()[0]
    ocr_count = cur.execute("SELECT COUNT(*) FROM ocr_text_blocks;").fetchone()[0]
    db_size_mb = DB_PATH.stat().st_size / (1024 * 1024)
    
    latest_row = cur.execute(
        "SELECT id, timestamp, active_app_name, active_window_title FROM captures ORDER BY id DESC LIMIT 1;"
    ).fetchone()
    
    conn.close()

    print("=" * 66)
    print("🔍 LAUBURU SCREEN LENS — TERMINAL CONTROLLER (screen-lens)")
    print("=" * 66)
    if pid:
        print(f"Daemon Status   : 🟢 ACTIVE (PID: {pid})")
    else:
        print(f"Daemon Status   : 🟡 INACTIVE (Use 'screen-lens start' to launch)")
    print(f"Database Path   : {DB_PATH}")
    print(f"Database Size   : {db_size_mb:.2f} MB")
    print(f"Total Captures  : {captures_count:,}")
    print(f"Total OCR Blocks: {ocr_count:,}")
    print(f"Live MJPEG Port : http://localhost:4003/stream.mjpg (Port 4003)")
    print("-" * 66)
    if latest_row:
        cap_id, ts, app, title = latest_row
        print(f"Latest Capture  : #{cap_id} at {ts}")
        print(f"Active App      : {app}")
        print(f"Window Title    : {title}")
    print("=" * 66)

def cmd_latest(args):
    conn = get_db_connection()
    cur = conn.cursor()
    limit = args.limit or 3
    
    rows = cur.execute(
        """
        SELECT id, timestamp, active_app_name, active_window_title, raw_text_summary
        FROM captures
        ORDER BY id DESC
        LIMIT ?;
        """,
        (limit,)
    ).fetchall()
    conn.close()

    if not rows:
        print("No captures found.")
        return

    print(f"--- Showing latest {len(rows)} Screen Lens captures ---")
    for r in rows:
        cap_id, ts, app, title, text = r
        clean_text = " ".join((text or "").split())
        excerpt = clean_text[:args.excerpt_len] + ("..." if len(clean_text) > args.excerpt_len else "")
        print(f"\n[Capture #{cap_id}] {ts} | App: {app} | Title: {title}")
        print(f"  OCR Summary: {excerpt}")

def cmd_query(args):
    if not args.search_term:
        print("Error: query requires search text.")
        sys.exit(1)
    
    conn = get_db_connection()
    cur = conn.cursor()
    term = args.search_term.strip()
    
    # Try FTS search first
    try:
        rows = cur.execute(
            """
            SELECT c.id, c.timestamp, c.active_app_name, c.active_window_title, c.raw_text_summary
            FROM captures c
            JOIN captures_fts fts ON c.id = fts.rowid
            WHERE captures_fts MATCH ?
            ORDER BY c.id DESC
            LIMIT ?;
            """,
            (term, args.limit)
        ).fetchall()
    except Exception:
        # Fallback to LIKE
        rows = cur.execute(
            """
            SELECT id, timestamp, active_app_name, active_window_title, raw_text_summary
            FROM captures
            WHERE raw_text_summary LIKE ? OR active_window_title LIKE ?
            ORDER BY id DESC
            LIMIT ?;
            """,
            (f"%{term}%", f"%{term}%", args.limit)
        ).fetchall()
        
    conn.close()

    print(f"--- Search Results for '{term}' ({len(rows)} matches) ---")
    for r in rows:
        cap_id, ts, app, title, text = r
        clean_text = " ".join((text or "").split())
        excerpt = clean_text[:200] + ("..." if len(clean_text) > 200 else "")
        print(f"\n[Capture #{cap_id}] {ts} | {app} — {title}")
        print(f"  Excerpt: {excerpt}")

def cmd_harvest(args):
    print("🌾 Triggering Gemini Split-Screen Harvester...")
    harvester_script = Path("/Volumes/Lauburu-Monorepo/01_apps/screen_lens/src/integrations/gemini_split_screen_harvester.py")
    if not harvester_script.exists():
        print(f"Error: Harvester script not found at {harvester_script}")
        sys.exit(1)
    
    from importlib.machinery import SourceFileLoader
    module = SourceFileLoader("gemini_split_screen_harvester", str(harvester_script)).load_module()
    harvester = module.GeminiSplitScreenHarvester()
    res = harvester.process_and_sync()
    print(f"✅ Harvester finished: {res}")

def cmd_daemon(args):
    action = args.action
    if action == "start":
        pid = get_daemon_pid()
        if pid:
            print(f"⚠️ Daemon is already running (PID: {pid})")
            return
        print("🚀 Starting Screen Lens daemon...")
        subprocess.Popen(
            [str(BINARY_PATH), "start", "--port", "3035", "--interval", "2.0", "--mode", "fast", "--daemon"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        time.sleep(1.0)
        new_pid = get_daemon_pid()
        print(f"✅ Started daemon (PID: {new_pid})")
    elif action == "stop":
        pid = get_daemon_pid()
        if not pid:
            print("Daemon is not running.")
            return
        print(f"🛑 Stopping daemon (PID: {pid})...")
        try:
            os.kill(pid, 15)
            time.sleep(1.0)
            print("✅ Stopped.")
        except Exception as e:
            print(f"Error stopping: {e}")
    elif action == "restart":
        args.action = "stop"
        cmd_daemon(args)
        args.action = "start"
        cmd_daemon(args)

def main():
    parser = argparse.ArgumentParser(
        description="Lauburu Screen Lens CLI — Terminal Query & Controller",
        prog="screen-lens"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # status
    p_status = subparsers.add_parser("status", help="Show daemon status, DB stats, and active window")
    p_status.set_defaults(func=cmd_status)

    # latest
    p_latest = subparsers.add_parser("latest", help="Show latest captured screen frames & OCR text")
    p_latest.add_argument("-n", "--limit", type=int, default=3, help="Number of records to display")
    p_latest.add_argument("-l", "--excerpt-len", type=int, default=250, help="Max length of OCR excerpt")
    p_latest.set_defaults(func=cmd_latest)

    # query
    p_query = subparsers.add_parser("query", help="Search OCR records using FTS5 text search")
    p_query.add_argument("search_term", type=str, help="Text term to search")
    p_query.add_argument("-n", "--limit", type=int, default=5, help="Max results")
    p_query.set_defaults(func=cmd_query)

    # harvest
    p_harvest = subparsers.add_parser("harvest", help="Harvest Gemini split-screen research to Obsidian & LoRA")
    p_harvest.set_defaults(func=cmd_harvest)

    # daemon control
    p_daemon = subparsers.add_parser("daemon", help="Manage background screen lens daemon (start/stop/restart)")
    p_daemon.add_argument("action", choices=["start", "stop", "restart"], help="Action to perform")
    p_daemon.set_defaults(func=cmd_daemon)

    for act in ("start", "stop", "restart"):
        p_act = subparsers.add_parser(act, help=f"{act.capitalize()} background screen lens daemon")
        p_act.set_defaults(func=cmd_daemon, action=act)

    if len(sys.argv) > 1 and (sys.argv[1].endswith(".sqlite") or "screen_lens.sqlite" in sys.argv[1]):
        # Intercept direct invocation of sqlite files
        sys.argv = [sys.argv[0], "status"]

    args = parser.parse_args()

    if not args.command:
        # Default behavior: run status and show latest capture
        cmd_status(args)
        class DummyArgs:
            limit = 1
            excerpt_len = 200
        cmd_latest(DummyArgs())
        print("\n💡 Tip: Run 'screen-lens --help' or 'screen-lens latest -n 5' to explore.")
    else:
        args.func(args)

if __name__ == "__main__":
    main()
