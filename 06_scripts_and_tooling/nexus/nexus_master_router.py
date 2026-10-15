#!/usr/bin/env python3
"""
Sovereign Master Nexus Unified CLI Router
Seamlessly bridges:
1. Lauburu Sovereign Mesh Orchestration commands (dispatch, status, verify, start, stop, restart, mesh, chat)
2. Sovereign Specialist Integrations (lens, neo, rish, report, threads)
3. Upstream Nexus Exchange / zkVM commands (markets, balance, orders, ws, keys, etc.).
"""

import sys
import os
import subprocess

REPO_ORCHESTRATOR = "/Volumes/Lauburu-Monorepo/06_scripts_and_tooling/install_nexus.py"
REPO_CLIENT = "/Volumes/Lauburu-Monorepo/06_scripts_and_tooling/integrations/nexus_mesh_client.py"
NEXUS_BIN = "/Users/aaron/.local/bin/nexus-bin"

SOVEREIGN_COMMANDS = {
    "dispatch",
    "status",
    "verify",
    "init",
    "start",
    "stop",
    "restart",
    "mesh",
    "chat"
}

CLIENT_COMMANDS = {
    "lens",
    "neo",
    "rish",
    "report",
    "threads"
}

def clean_args(args):
    """Cleans trailing newline characters or literal \\n escape sequences from args."""
    cleaned = []
    for a in args:
        val = a.replace("\\n", "").rstrip("\n")
        cleaned.append(val)
    return cleaned

def main():
    raw_args = sys.argv[1:]
    args = clean_args(raw_args)

    if not args:
        # If no arguments provided, show unified help or invoke upstream
        if os.path.exists(NEXUS_BIN):
            subprocess.run([NEXUS_BIN, "--help"])
        else:
            subprocess.run([sys.executable, REPO_ORCHESTRATOR, "--help"])
        sys.exit(0)

    cmd = args[0].lower()

    if cmd in CLIENT_COMMANDS:
        cmd_line = [sys.executable, REPO_CLIENT] + args
        res = subprocess.run(cmd_line)
        sys.exit(res.returncode)

    if cmd in SOVEREIGN_COMMANDS:
        cmd_line = [sys.executable, REPO_ORCHESTRATOR] + args
        res = subprocess.run(cmd_line)
        sys.exit(res.returncode)

    if cmd in ("--help", "-h", "help") and len(args) == 1:
        print("╔══════════════════════════════════════════════════════════════════════╗")
        print("║          👑 UNIFIED MASTER NEXUS CLI ROUTER (SOVEREIGN + BIN)        ║")
        print("╚══════════════════════════════════════════════════════════════════════╝")
        print("Sovereign Mesh & Specialist Commands:")
        print("  dispatch    Dispatch directive to Mother Ship (:4050) & satellite threads")
        print("  lens        Screen Lens Sovereign status, latest OCR captures, and stream")
        print("  neo         Neo AI/ML task orchestration and backend submission")
        print("  status      Show 7-layer mesh & Single-Chat Nexus health status")
        print("  verify      Execute 6-stage Tri-Proof verification gate")
        print("  rish        Execute Shizuku rish on Android nodes & auto-report to Nexus")
        print("  report      Report action receipts directly into a satellite chat thread")
        print("  start/stop  Manage Single-Chat Nexus server daemon (:4050)")
        print("  mesh        Deploy and verify Sovereign Nexus across mesh nodes")
        print("\nUpstream Nexus Exchange Commands:")
        if os.path.exists(NEXUS_BIN):
            subprocess.run([NEXUS_BIN, "--help"])
        sys.exit(0)

    # Forward to upstream native binary if recognized or fallback to orchestrator
    if os.path.exists(NEXUS_BIN):
        res = subprocess.run([NEXUS_BIN] + args)
        sys.exit(res.returncode)
    else:
        res = subprocess.run([sys.executable, REPO_ORCHESTRATOR] + args)
        sys.exit(res.returncode)

if __name__ == "__main__":
    main()
