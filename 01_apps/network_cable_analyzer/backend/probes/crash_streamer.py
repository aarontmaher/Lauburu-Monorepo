"""
Lauburu Crash & Network Health Streamer Probe
=============================================
Inspects authentic Darwin crash logs, kernel panics, Jetsam memory pressure kills,
and mesh service state drops, streaming live telemetry to the Network Health UI.

Features:
- Scans /Library/Logs/DiagnosticReports and ~/Library/Logs/DiagnosticReports
- Parses .panic (Kernel / ACIO2 panics) and .ips (process crashes, JetsamEvents)
- Audits live service listening ports (8082, 50052, 4003, 4007, 9002)
- Server-Sent Events (SSE) live streaming generator for Network Health App
"""

import time
import os
import glob
import json
import re
import socket
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

DIAG_SYSTEM_DIR = Path("/Library/Logs/DiagnosticReports")
DIAG_USER_DIR = Path(os.path.expanduser("~/Library/Logs/DiagnosticReports"))

WATCHED_SERVICES = [
    {"name": "Master Orchestrator (PRP Leader)", "port": 8082, "criticality": "CRITICAL"},
    {"name": "Distributed GPU RPC Shard", "port": 50052, "criticality": "CRITICAL"},
    {"name": "Screen Lens Sovereign Hub", "port": 4003, "criticality": "HIGH"},
    {"name": "Network Analyzer Backend", "port": 4007, "criticality": "HIGH"},
    {"name": "Local Red Team AI", "port": 8083, "criticality": "HIGH"},
    {"name": "Router BT Raw Hub", "host": "192.168.8.1", "port": 9002, "criticality": "MEDIUM"},
]

def _check_port_quick(host: str, port: int, timeout: float = 0.25) -> bool:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        res = s.connect_ex((host, port))
        s.close()
        return res == 0
    except Exception:
        return False

def _parse_panic_file(path: Path) -> Optional[Dict[str, Any]]:
    """Parse Darwin .contents.panic or .panic file."""
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
        if "Debugger message: panic" not in content and "Kernel Extensions in backtrace" not in content:
            return None

        # Extract kernel version & faulting thread
        k_ver = re.search(r"Kernel version:\s*([^\n]+)", content)
        panic_task = re.search(r"Panicked task\s*([^\n]+)", content)
        kexts = re.search(r"Kernel Extensions in backtrace:\s*([^\n]+)", content)
        m_acio = "ACIO2" in content or "Thunderbolt" in content or "AppleA7IOP" in content
        
        stat = path.stat()
        mtime = stat.st_mtime
        iso_time = datetime.fromtimestamp(mtime).isoformat()

        component = "Darwin Kernel (Apple Silicon)"
        if "IOSlaveProcessor" in content or "RTBuddy" in content:
            component = "Darwin Coprocessor (RTBuddy / A7IOP)"
        elif m_acio:
            component = "Darwin ACIO2 Controller"

        return {
            "id": f"panic_{int(mtime)}_{path.name}",
            "filename": path.name,
            "timestamp": iso_time,
            "epoch": mtime,
            "severity": "CRITICAL",
            "event_type": "KERNEL_PANIC",
            "component": component,
            "reason": panic_task.group(1).strip() if panic_task else "Hardware / Kernel Exception",
            "kext_backtrace": kexts.group(1).strip() if kexts else "Internal XNU Kernel Panic",
            "details": f"Darwin XNU Panic recorded in {path.name}. Memory dump captured.",
            "remedy": "Dynamic RAM Governor enforces >=4.8GB headroom to prevent ACIO2/RTBuddy panics."
        }
    except Exception:
        return None

def _parse_ips_file(path: Path) -> Optional[Dict[str, Any]]:
    """Parse macOS .ips crash report (JSON / JSONL format)."""
    try:
        stat = path.stat()
        mtime = stat.st_mtime
        iso_time = datetime.fromtimestamp(mtime).isoformat()

        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            first_line = f.readline().strip()
            second_line = f.readline().strip()

        meta = {}
        if first_line.startswith("{") and first_line.endswith("}"):
            try:
                meta = json.loads(first_line)
            except Exception:
                pass

        details_json = {}
        if second_line.startswith("{"):
            try:
                details_json = json.loads(second_line)
            except Exception:
                pass

        app_name = meta.get("app_name") or path.stem.split("-")[0]
        bug_type = meta.get("bug_type", "Crash")
        incident_id = meta.get("incident_id", path.stem)

        # Determine severity & event type
        is_jetsam = "Jetsam" in path.name or bug_type == "309" and "jetsam" in app_name.lower()
        if "JetsamEvent" in path.name:
            severity = "WARNING"
            event_type = "JETSAM_MEMORY_PRESSURE"
            component = "Darwin Memory Manager"
            reason = "Jetsam memory pressure kill"
            remedy = "Active memory reaper triggers auto-evacuation of peripheral processes."
        else:
            severity = "ERROR"
            event_type = "PROCESS_CRASH"
            component = f"Process ({app_name})"
            reason = details_json.get("termination", {}).get("reason", f"Terminated by signal ({bug_type})")
            remedy = "Self-healing daemon restarts dead processes automatically."

        return {
            "id": f"ips_{incident_id[:8]}_{int(mtime)}",
            "filename": path.name,
            "timestamp": iso_time,
            "epoch": mtime,
            "severity": severity,
            "event_type": event_type,
            "component": component,
            "app_name": app_name,
            "reason": str(reason),
            "details": f"Diagnostic report bug_type={bug_type} for {app_name}.",
            "remedy": remedy
        }
    except Exception:
        return None

def get_recent_crashes(limit: int = 25) -> List[Dict[str, Any]]:
    """Scan system and user diagnostic report folders for authentic crash records."""
    crashes: List[Dict[str, Any]] = []

    # 1. Check for kernel panic reports
    panic_files = list(DIAG_SYSTEM_DIR.glob("*.panic"))
    if (DIAG_SYSTEM_DIR / ".contents.panic").exists():
        panic_files.append(DIAG_SYSTEM_DIR / ".contents.panic")

    for pf in panic_files:
        p_info = _parse_panic_file(pf)
        if p_info:
            crashes.append(p_info)

    # 2. Check for recent .ips and .diag crash reports in user dir
    if DIAG_USER_DIR.exists():
        user_files = sorted(
            DIAG_USER_DIR.glob("*.ips"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )[:30]
        for uf in user_files:
            u_info = _parse_ips_file(uf)
            if u_info:
                crashes.append(u_info)

    # 3. Check live service degradation
    for svc in WATCHED_SERVICES:
        host = svc.get("host", "127.0.0.1")
        port = svc["port"]
        is_up = _check_port_quick(host, port)
        if not is_up:
            crashes.append({
                "id": f"svc_drop_{port}_{int(time.time())}",
                "filename": f"port_{port}_listener",
                "timestamp": datetime.now().isoformat(),
                "epoch": time.time(),
                "severity": "CRITICAL" if svc["criticality"] == "CRITICAL" else "WARNING",
                "event_type": "SERVICE_DEGRADED",
                "component": f"{svc['name']} (Port {port})",
                "reason": f"TCP socket :{port} on {host} is unreachable / offline",
                "details": f"Process listener dropped on port {port}.",
                "remedy": f"Self-healing protocol triggers restart of {svc['name']} daemon."
            })

    # Sort descending by epoch
    crashes.sort(key=lambda x: x.get("epoch", 0), reverse=True)
    return crashes[:limit]

async def stream_crash_events(request):
    """SSE generator streaming live crash and service drop events."""
    last_check_time = time.time()
    seen_ids = set()

    # Initial batch
    initial = get_recent_crashes(limit=15)
    for c in initial:
        seen_ids.add(c["id"])

    yield f"event: initial_crashes\ndata: {json.dumps(initial)}\n\n"

    while True:
        if await request.is_disconnected():
            break
        try:
            current = get_recent_crashes(limit=25)
            new_events = [c for c in current if c["id"] not in seen_ids]
            for ne in new_events:
                seen_ids.add(ne["id"])
                yield f"event: crash_alert\ndata: {json.dumps(ne)}\n\n"

            # Periodic health heartbeat every 5s
            heartbeat = {
                "timestamp": datetime.now().isoformat(),
                "total_monitored_services": len(WATCHED_SERVICES),
                "healthy_services": sum(1 for s in WATCHED_SERVICES if _check_port_quick(s.get("host", "127.0.0.1"), s["port"])),
                "recent_incident_count": len(current)
            }
            yield f"event: health_heartbeat\ndata: {json.dumps(heartbeat)}\n\n"

        except Exception as e:
            yield f": error {str(e)}\n\n"

        await asyncio.sleep(4.0)
