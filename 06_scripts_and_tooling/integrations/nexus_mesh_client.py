#!/usr/bin/env python3
"""
================================================================================
👑 Sovereign Nexus Mesh Client & Satellite CLI (2026)
================================================================================
Subsystem: 06_scripts_and_tooling/integrations/nexus_mesh_client.py
CLI Command: nexus (on edge nodes) or nexus-mesh-client
Governed by:
  - Rule 0 (Zero-Mock): Authentic local endpoints, genuine syscalls, authentic records
  - Rule 1 (Tri-Proof): Exact process exit codes, SHA256 checksums, visual snapshots
  - Rule 2 (Tri-Vault): Obsidian Vault, PySpark LoRA lake, GitHub Monorepo
  - Rule 3 & 10 (Host Sanctuary): Zero heavy models in-process, RAM headroom >= 4.8GB
  - Rule 8 & 15 (Model Governance): Qwen 3.8 Max Master (:8082), Abliterated Red Team (:8083)

Capabilities:
  • Auto-discovers Sovereign Single-Chat Nexus Mother Ship (:4050) across:
    1. Localhost (127.0.0.1:4050)
    2. Tailscale Overlay (100.119.199.76:4050)
    3. Local 2.5G/Wi-Fi 7 LAN (192.168.8.230:4050)
    4. 40Gbps Thunderbolt Bridge (169.254.187.138:4050 / 192.168.2.2:4050)
  • Ingests and dispatches directives to Mother Ship (/api/chat/nexus)
  • Reports edge actions, sensor telemetry, and terminal executions back to threads
  • Integrates seamlessly with Shizuku 'rish' on Android (UID 2000 shell execution)
  • Probes zkVM prover status and local device telemetry
================================================================================
"""

import os
import sys
import json
import time
import socket
import shutil
import argparse
import platform
import subprocess
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional, Tuple

MOTHER_SHIP_CANDIDATES = [
    "http://127.0.0.1:4050",
    "http://100.119.199.76:4050",
    "http://192.168.8.230:4050",
    "http://192.168.2.2:4050",
]

C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_CYAN = "\033[36m"
C_GREEN = "\033[32m"
C_YELLOW = "\033[33m"
C_RED = "\033[31m"
C_DIM = "\033[90m"


def discover_mother_ship(timeout: float = 2.0) -> Optional[str]:
    for url in MOTHER_SHIP_CANDIDATES:
        try:
            req = urllib.request.Request(f"{url}/health", headers={"User-Agent": "NexusMeshClient/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    return url
        except Exception:
            continue
    return None


def get_local_telemetry() -> Dict[str, Any]:
    node_name = platform.node() or "unknown_node"
    system_os = platform.system()
    arch = platform.machine()
    is_android = os.path.exists("/data/data/com.termux") or "ANDROID_ROOT" in os.environ

    telemetry: Dict[str, Any] = {
        "hostname": node_name,
        "os": system_os,
        "arch": arch,
        "is_android": is_android,
        "timestamp": time.time(),
        "battery": None,
        "ram": None,
        "shizuku": None
    }

    if is_android:
        if shutil.which("termux-battery-status"):
            try:
                res = subprocess.run(["termux-battery-status"], capture_output=True, text=True, timeout=2)
                if res.returncode == 0:
                    telemetry["battery"] = json.loads(res.stdout)
            except Exception:
                pass

        rish_bin = shutil.which("rish") or "/data/data/com.termux/files/home/bin/rish"
        if os.path.exists(rish_bin):
            try:
                res = subprocess.run([rish_bin, "-c", "id -u"], capture_output=True, text=True, timeout=3)
                uid_str = (res.stdout.strip() or res.stderr.strip())
                telemetry["shizuku"] = {
                    "available": uid_str in ("2000", "0"),
                    "uid": uid_str,
                    "binary": rish_bin
                }
            except Exception as e:
                telemetry["shizuku"] = {"available": False, "error": str(e)}

    if os.path.exists("/proc/meminfo"):
        try:
            mem: Dict[str, int] = {}
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    parts = line.split(":")
                    if len(parts) == 2:
                        k = parts[0].strip()
                        v = parts[1].strip().split()[0]
                        if v.isdigit():
                            mem[k] = int(v)
            total = mem.get("MemTotal", 0) // 1024
            avail = mem.get("MemAvailable", mem.get("MemFree", 0)) // 1024
            telemetry["ram"] = {"total_mb": total, "available_mb": avail}
        except Exception:
            pass

    return telemetry


def cmd_status(args: argparse.Namespace) -> int:
    print(f"{C_BOLD}{C_CYAN}╔══════════════════════════════════════════════════════════════════════╗{C_RESET}")
    print(f"{C_BOLD}{C_CYAN}║             👑 SOVEREIGN NEXUS MESH CLIENT STATUS                    ║{C_RESET}")
    print(f"{C_BOLD}{C_CYAN}╚══════════════════════════════════════════════════════════════════════╝{C_RESET}")

    base_url = args.url or discover_mother_ship()
    if not base_url:
        print(f"  {C_RED}❌ Mother Ship (:4050) Unreachable across all mesh endpoints.{C_RESET}")
        print(f"  {C_DIM}Checked: {', '.join(MOTHER_SHIP_CANDIDATES)}{C_RESET}")
    else:
        print(f"  {C_GREEN}✅ Mother Ship Active:{C_RESET} {C_BOLD}{base_url}{C_RESET}")
        try:
            with urllib.request.urlopen(f"{base_url}/health", timeout=3) as resp:
                health = json.loads(resp.read().decode())
                print(f"  • App:             {health.get('app', 'Unknown')}")
                print(f"  • Database Records:{health.get('database_records_indexed', 0):,}")
                print(f"  • Default Model:   {health.get('prima_default', 'Unknown')}")
        except Exception as e:
            print(f"  {C_YELLOW}⚠️  Could not fetch /health: {e}{C_RESET}")

        try:
            with urllib.request.urlopen(f"{base_url}/api/chat/nexus/threads", timeout=3) as resp:
                t_data = json.loads(resp.read().decode())
                threads = t_data.get("threads", [])
                print(f"  • Active Threads:  {len(threads)}")
                for t in threads[:6]:
                    print(f"    - {t.get('id'):25s} [{t.get('category')}] {t.get('title')}")
        except Exception:
            pass

    print(f"\n{C_BOLD}{C_CYAN}── Local Edge Node Telemetry ──────────────────────────────────────────{C_RESET}")
    telem = get_local_telemetry()
    print(f"  • Node:     {telem['hostname']} ({telem['os']} {telem['arch']})")
    if telem.get("ram"):
        print(f"  • RAM:      {telem['ram']['available_mb']} MB available / {telem['ram']['total_mb']} MB total")
    if telem.get("battery"):
        b = telem["battery"]
        print(f"  • Battery:  {b.get('percentage')}% ({b.get('status')}) | Temp: {b.get('temperature', 0):.1f}°C")
    if telem.get("shizuku"):
        s = telem["shizuku"]
        status_c = C_GREEN if s.get("available") else C_RED
        print(f"  • Shizuku:  {status_c}{'ACTIVE (UID ' + str(s.get('uid')) + ')' if s.get('available') else 'OFFLINE'}{C_RESET}")

    nexus_bin = shutil.which("nexus") or "/Users/aaron/.local/bin/nexus"
    if os.path.exists(nexus_bin):
        try:
            res = subprocess.run([nexus_bin, "--version"], capture_output=True, text=True, timeout=2)
            print(f"  • Nexus CLI:{C_GREEN} {res.stdout.strip()}{C_RESET}")
        except Exception:
            pass

    return 0 if base_url else 1


def cmd_dispatch(args: argparse.Namespace) -> int:
    base_url = args.url or discover_mother_ship()
    if not base_url:
        print(f"{C_RED}Error: Mother Ship (:4050) unreachable.{C_RESET}", file=sys.stderr)
        return 1

    payload = {
        "prompt": args.prompt,
        "extra_context": {
            "source_node": platform.node() or "nexus_client",
            "is_android": os.path.exists("/data/data/com.termux"),
            "dispatch_timestamp": time.time()
        }
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url}/api/chat/nexus",
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "NexusMeshClient/1.0"}
    )

    print(f"{C_BOLD}{C_CYAN}🚀 Dispatching directive to Mother Ship ({base_url})...{C_RESET}")
    print(f"{C_DIM}Directive: {args.prompt}{C_RESET}\n")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            res = json.loads(resp.read().decode())
            print(f"{C_GREEN}✅ Dispatch Successful:{C_RESET}")
            print(f"  • User Message ID:   {res.get('user_message_id')}")
            print(f"  • Directives Routed: {len(res.get('fanned_out_directives', []))}")
            for d in res.get("fanned_out_directives", []):
                print(f"    - [{d.get('thread_id')}] {d.get('directive')}")
            print(f"  • Actions Executed:  {len(res.get('actions_taken', []))}")
            for a in res.get("actions_taken", []):
                code = a.get("exit_code", 0)
                c_str = f"{C_GREEN}Exit 0{C_RESET}" if code == 0 else f"{C_RED}Exit {code}{C_RESET}"
                print(f"    - [{a.get('thread_id')}] {a.get('action')} ({c_str})")
            
            synthesis = res.get("synthesis", {})
            if synthesis:
                print(f"\n{C_BOLD}🧠 Master Synthesis:{C_RESET}")
                print(f"  {synthesis.get('summary', '')}")
            return 0
    except Exception as e:
        print(f"{C_RED}❌ Dispatch failed: {e}{C_RESET}", file=sys.stderr)
        return 1


def cmd_report(args: argparse.Namespace) -> int:
    base_url = args.url or discover_mother_ship()
    if not base_url:
        print(f"{C_RED}Error: Mother Ship (:4050) unreachable.{C_RESET}", file=sys.stderr)
        return 1

    payload = {
        "action": args.action,
        "result": args.result,
        "exit_code": args.exit_code,
        "status": "completed" if args.exit_code == 0 else "failed"
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url}/api/chat/nexus/threads/{args.thread_id}/report",
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "NexusMeshClient/1.0"}
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            act = json.loads(resp.read().decode())
            print(f"{C_GREEN}✅ Action reported to thread [{args.thread_id}]: ID {act.get('id')}{C_RESET}")
            return 0
    except Exception as e:
        print(f"{C_RED}❌ Failed to report action: {e}{C_RESET}", file=sys.stderr)
        return 1


def cmd_rish(args: argparse.Namespace) -> int:
    rish_bin = shutil.which("rish") or "/data/data/com.termux/files/home/bin/rish"
    if not os.path.exists(rish_bin):
        print(f"{C_RED}Error: rish binary not found.{C_RESET}", file=sys.stderr)
        return 1

    cmd_str = " ".join(args.command)
    print(f"{C_BOLD}{C_CYAN}⚡ Executing via Shizuku rish: {cmd_str}{C_RESET}")

    t0 = time.perf_counter()
    res = subprocess.run([rish_bin, "-c", cmd_str], capture_output=True, text=True)
    elapsed = time.perf_counter() - t0

    output = (res.stdout or res.stderr or "").strip()
    print(output)

    if not args.no_report:
        base_url = args.url or discover_mother_ship(timeout=1.0)
        if base_url:
            thread_id = args.thread or "core_infrastructure"
            payload = {
                "action": f"rish: {cmd_str}",
                "result": output[:2000],
                "exit_code": res.returncode,
                "status": "completed" if res.returncode == 0 else "failed"
            }
            try:
                data = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(
                    f"{base_url}/api/chat/nexus/threads/{thread_id}/report",
                    data=data,
                    headers={"Content-Type": "application/json", "User-Agent": "NexusMeshClient/1.0"}
                )
                urllib.request.urlopen(req, timeout=5)
            except Exception:
                pass

    return res.returncode


def sanitize_spec11(text: str) -> str:
    """Spec-11 Zero Leakage: Sanitizes credentials and private tokens."""
    if not text:
        return ""
    import re
    text = re.sub(r'sk-[a-zA-Z0-9_\-]{20,}', '[REDACTED_API_KEY_SOVEREIGN]', text)
    text = re.sub(r'sk-or-[a-zA-Z0-9_\-]{20,}', '[REDACTED_OPENROUTER_KEY]', text)
    text = re.sub(r'sk-ant-[a-zA-Z0-9_\-]{20,}', '[REDACTED_ANTHROPIC_KEY]', text)
    text = re.sub(r'hf_[a-zA-Z0-9_\-]{20,}', '[REDACTED_HF_TOKEN]', text)
    text = re.sub(r'ghp_[a-zA-Z0-9_\-]{20,}', '[REDACTED_GITHUB_PAT]', text)
    text = re.sub(r'AIza[a-zA-Z0-9_\-]{30,}', '[REDACTED_GOOGLE_KEY]', text)
    return text


def cmd_lens(args: argparse.Namespace) -> int:
    lens_db = os.path.expanduser("~/.lauburu/screen_lens.sqlite")
    action = args.lens_action or "status"

    if action == "status":
        print(f"{C_BOLD}{C_CYAN}👁️ Screen Lens Sovereign Status:{C_RESET}")
        try:
            ps = subprocess.run(["pgrep", "-f", "lauburu-lens start"], capture_output=True)
            status_str = f"{C_GREEN}ACTIVE{C_RESET}" if ps.returncode == 0 else f"{C_YELLOW}INACTIVE{C_RESET}"
            print(f"  • Daemon Status:  {status_str}")
        except Exception:
            pass
        print(f"  • MJPEG Stream:   http://localhost:4003/stream.mjpg (Port 4003)")
        print(f"  • SQLite Store:   {lens_db}")
        if os.path.exists(lens_db):
            try:
                import sqlite3
                conn = sqlite3.connect(f"file:{lens_db}?mode=ro", uri=True)
                cur = conn.cursor()
                row = cur.execute("SELECT id, timestamp, active_app_name, active_window_title FROM captures ORDER BY id DESC LIMIT 1").fetchone()
                conn.close()
                if row:
                    print(f"  • Latest Capture: #{row[0]} at {row[1]}")
                    print(f"  • Active App:     {row[2]}")
                    print(f"  • Active Window:  {row[3]}")
            except Exception as e:
                print(f"  • Query Error:    {e}")
        return 0

    elif action == "latest":
        limit = args.limit or 3
        print(f"{C_BOLD}{C_CYAN}👁️ Screen Lens Sovereign Latest Captures (Limit {limit}):{C_RESET}")
        if not os.path.exists(lens_db):
            print(f"{C_RED}Screen Lens database not found at {lens_db}{C_RESET}")
            return 1
        try:
            import sqlite3
            conn = sqlite3.connect(f"file:{lens_db}?mode=ro", uri=True)
            cur = conn.cursor()
            rows = cur.execute("SELECT id, timestamp, active_app_name, active_window_title, raw_text_summary FROM captures ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
            conn.close()
            for r in rows:
                clean_summary = sanitize_spec11(r[4] or "")[:300]
                print(f"\n{C_BOLD}#{r[0]} [{r[1]}]{C_RESET} {C_GREEN}{r[2]}{C_RESET} — {r[3]}")
                if clean_summary:
                    print(f"  {C_DIM}{clean_summary}{C_RESET}")
            return 0
        except Exception as e:
            print(f"{C_RED}Error: {e}{C_RESET}")
            return 1

    elif action == "report":
        base_url = args.url or discover_mother_ship()
        if not base_url:
            print(f"{C_RED}Error: Mother Ship (:4050) unreachable.{C_RESET}", file=sys.stderr)
            return 1
        summary = "No active capture"
        if os.path.exists(lens_db):
            try:
                import sqlite3
                conn = sqlite3.connect(f"file:{lens_db}?mode=ro", uri=True)
                cur = conn.cursor()
                row = cur.execute("SELECT id, timestamp, active_app_name, active_window_title, raw_text_summary FROM captures ORDER BY id DESC LIMIT 1").fetchone()
                conn.close()
                if row:
                    summary = f"Capture #{row[0]} on {row[2]} ({row[3]}): {sanitize_spec11(row[4] or '')[:300]}"
            except Exception as e:
                summary = f"Error reading capture: {e}"
        payload = {
            "action": "Screen Lens Visual Frame Ingestion",
            "result": summary,
            "exit_code": 0,
            "status": "completed"
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{base_url}/api/chat/nexus/threads/screen_lens_vla/report",
            data=data,
            headers={"Content-Type": "application/json", "User-Agent": "NexusMeshClient/1.0"}
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                act = json.loads(resp.read().decode())
                print(f"{C_GREEN}✅ Screen Lens observation reported to [screen_lens_vla]: ID {act.get('id')}{C_RESET}")
                return 0
        except Exception as e:
            print(f"{C_RED}❌ Failed to report to Mother Ship: {e}{C_RESET}", file=sys.stderr)
            return 1

    elif action == "stream":
        print(f"{C_BOLD}{C_CYAN}👁️ Screen Lens Sovereign Live Stream Endpoint:{C_RESET}")
        print(f"  • URL: http://localhost:4003/stream.mjpg")
        print(f"  • Tip: In Antigravity IDE, click macro 'Screen Lens: Open Live Stream (:4003)'")
        return 0

    return 0


def cmd_neo(args: argparse.Namespace) -> int:
    action = args.neo_action or "status"
    if action == "status":
        print(f"{C_BOLD}{C_CYAN}⚡ Neo AI/ML Orchestration Status:{C_RESET}")
        int_dir = os.path.expanduser("~/.neo/integrations")
        if os.path.exists(int_dir):
            integrations = [f for f in os.listdir(int_dir) if not f.startswith(".")]
            print(f"  • Configured Providers: {', '.join(integrations) if integrations else 'None'}")
        else:
            print(f"  • Configured Providers: None (~/.neo/integrations does not exist)")
        thread_file = os.path.expanduser("~/.neo/active_thread_id")
        if os.path.exists(thread_file):
            try:
                tid = open(thread_file).read().strip()
                print(f"  • Active Neo Thread:    {tid}")
            except Exception:
                pass
        return 0
    elif action == "task":
        if not args.task:
            print(f"{C_RED}Error: Task description required for 'nexus neo task <description>'{C_RESET}", file=sys.stderr)
            return 1
        base_url = args.url or discover_mother_ship()
        if not base_url:
            print(f"{C_RED}Error: Mother Ship (:4050) unreachable.{C_RESET}", file=sys.stderr)
            return 1
        task_str = " ".join(args.task)
        payload = {"prompt": task_str}
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{base_url}/api/chat/nexus/neo",
            data=data,
            headers={"Content-Type": "application/json", "User-Agent": "NexusMeshClient/1.0"}
        )
        print(f"{C_BOLD}{C_CYAN}⚡ Submitting Neo task: {task_str}{C_RESET}")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                res = json.loads(resp.read().decode())
                print(f"{C_GREEN}✅ Neo task submitted to Mother Ship! User Message ID: {res.get('user_message_id')}{C_RESET}")
                return 0
        except Exception as e:
            print(f"{C_RED}❌ Failed to submit Neo task: {e}{C_RESET}", file=sys.stderr)
            return 1
    return 0


def main():
    parser = argparse.ArgumentParser(description="👑 Sovereign Nexus Mesh Client & Satellite CLI")
    parser.add_argument("--url", help="Override Mother Ship URL (e.g. http://100.119.199.76:4050)")
    subparsers = parser.add_subparsers(dest="subcommand", help="Subcommand to execute")

    subparsers.add_parser("status", help="Probe Mother Ship and local telemetry")

    p_dispatch = subparsers.add_parser("dispatch", help="Dispatch a directive across the mesh")
    p_dispatch.add_argument("prompt", help="The directive prompt to dispatch")

    p_report = subparsers.add_parser("report", help="Report an edge action back to Mother Ship")
    p_report.add_argument("thread_id", help="Target thread (e.g. core_infrastructure, screen_lens_vla)")
    p_report.add_argument("action", help="Description of action taken")
    p_report.add_argument("result", help="Result output or metrics")
    p_report.add_argument("--exit-code", type=int, default=0, help="Process exit code (default: 0)")

    p_rish = subparsers.add_parser("rish", help="Execute privileged command via Shizuku rish")
    p_rish.add_argument("--thread", default="core_infrastructure", help="Thread to report action to")
    p_rish.add_argument("--no-report", action="store_true", help="Skip reporting to Mother Ship")
    p_rish.add_argument("command", nargs="+", help="Command to execute via rish")

    p_lens = subparsers.add_parser("lens", help="Screen Lens Sovereign VLA commands & telemetry")
    p_lens.add_argument("lens_action", nargs="?", default="status", choices=["status", "latest", "report", "stream"], help="Screen Lens action")
    p_lens.add_argument("--limit", type=int, default=3, help="Number of latest captures (default: 3)")

    p_neo = subparsers.add_parser("neo", help="Neo AI/ML Orchestrator integration")
    p_neo.add_argument("neo_action", nargs="?", default="status", choices=["status", "task"], help="Neo action")
    p_neo.add_argument("task", nargs="*", help="Task description for 'nexus neo task <desc>'")

    args = parser.parse_args()

    if not args.subcommand or args.subcommand == "status":
        sys.exit(cmd_status(args))
    elif args.subcommand == "dispatch":
        sys.exit(cmd_dispatch(args))
    elif args.subcommand == "report":
        sys.exit(cmd_report(args))
    elif args.subcommand == "rish":
        sys.exit(cmd_rish(args))
    elif args.subcommand == "lens":
        sys.exit(cmd_lens(args))
    elif args.subcommand == "neo":
        sys.exit(cmd_neo(args))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
