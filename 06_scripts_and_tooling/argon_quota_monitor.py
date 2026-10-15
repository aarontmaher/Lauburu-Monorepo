#!/usr/bin/env python3
"""
Live Antigravity Quota & Argon Swarm Telemetry Monitor.
Auto-discovers the local Antigravity `language_server` port and CSRF token,
queries `RetrieveUserQuotaSummary` (with `forceRefresh: true`) and
`GetCascadeModelConfigData`, and prints exact 7-decimal-place quota metrics.
"""

import argparse
import json
import re
import ssl
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone


def discover_language_server():
    """Auto-discover the running Antigravity language_server HTTPS port and CSRF token."""
    ps_out = subprocess.check_output(["ps", "aux"], text=True)
    pid = None
    csrf_token = None
    for line in ps_out.splitlines():
        if "language_server" in line and "--csrf_token" in line:
            parts = line.split()
            pid = parts[1]
            m = re.search(r"--csrf_token\s+([0-9a-fA-F-]+)", line)
            if m:
                csrf_token = m.group(1)
            break
    if not pid or not csrf_token:
        raise RuntimeError("Could not locate running Antigravity language_server process.")

    lsof_out = subprocess.check_output(
        ["lsof", "-a", "-p", str(pid), "-iTCP", "-sTCP:LISTEN", "-P", "-n"],
        text=True,
    )
    ports = []
    for line in lsof_out.splitlines():
        m = re.search(r"127\.0\.0\.1:(\d+)\s+\(LISTEN\)", line)
        if m:
            ports.append(int(m.group(1)))
    if not ports:
        raise RuntimeError(f"No listening TCP ports found for language_server PID {pid}.")
    return min(ports), csrf_token


def call_rpc(port: int, csrf_token: str, method: str, payload: dict) -> dict:
    url = f"https://127.0.0.1:{port}/exa.language_server_pb.LanguageServerService/{method}"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Connect-Protocol-Version": "1",
            "x-codeium-csrf-token": csrf_token,
        },
        method="POST",
    )
    ctx = ssl._create_unverified_context()
    with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    parser = argparse.ArgumentParser(description="Monitor live Antigravity model & Argon quota.")
    parser.add_argument("--no-refresh", action="store_true", help="Read cached quota without forcing upstream refresh.")
    parser.add_argument("--json", action="store_true", help="Emit raw JSON output.")
    args = parser.parse_args()

    port, csrf_token = discover_language_server()
    summary = call_rpc(port, csrf_token, "RetrieveUserQuotaSummary", {"forceRefresh": not args.no_refresh})
    models = call_rpc(port, csrf_token, "GetCascadeModelConfigData", {})

    if args.json:
        print(json.dumps({"quotaSummary": summary, "modelConfigs": models}, indent=2))
        return

    now_str = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    print(f"=== Antigravity Live Quota Telemetry ({now_str}) ===")
    print(f"Endpoint: https://127.0.0.1:{port} (forceRefresh={not args.no_refresh})\n")

    for group in summary.get("response", {}).get("groups", []):
        print(f"[{group.get('displayName')}] — Tooltip: \"{group.get('description')}\"")
        for b in group.get("buckets", []):
            frac = b.get("remainingFraction", 0.0) * 100.0
            ui_pct = round(frac)
            print(
                f"  • {b.get('displayName')} ({b.get('bucketId')}): "
                f"{frac:.5f}% (UI shows: {ui_pct}%) | Reset: {b.get('resetTime')}"
            )
        print()

    print("[Active Model Quota Bindings (GetCascadeModelConfigData)]")
    for m in models.get("clientModelConfigs", []):
        label = m.get("label", "")
        model_id = m.get("modelId", "")
        q = m.get("quotaInfo", {})
        rem = q.get("remainingFraction")
        rem_str = f"{rem * 100:.5f}%" if rem is not None else "0.00000% (Exhausted/Weekly Cap)"
        print(f"  • {label:<28} ({model_id:<24}) -> 5h Pool: {rem_str} | Reset: {q.get('resetTime')}")


if __name__ == "__main__":
    main()
