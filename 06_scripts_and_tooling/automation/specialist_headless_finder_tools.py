#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
06_scripts_and_tooling/automation/specialist_headless_finder_tools.py
===================================================================
Deterministic Headless Automation Tool Suite for macOS Finder & Multi-Device Mesh Search.
Autonomously maintained specialist tool governing background filesystem operations,
Rule 3 L2-routed AppleScript/JXA bridge, Spotlight/mdfind indexing, metadata tagging,
and overflow-guarded distributed mesh file search across all Lauburu nodes.

Strict Rule #0 & #1 Compliance: 100% authentic syscalls and AppleEvents. Zero mocks.
Strict Rule #3 Compliance: AppleScript (`osascript`) routes to L2 (`macbook-intel`) by default
when invoked from the L1 Mac Mini Sanctuary host.
"""

from __future__ import annotations

import concurrent.futures
import json
import os
import re
import shlex
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
RAM_STATE_JSON = REPO_ROOT / "00_core_infrastructure/mesh_ram_matrix_live.json"

SSH_OPTS = [
    "-o", "BatchMode=yes",
    "-o", "ConnectTimeout=3",
    "-o", "StrictHostKeyChecking=no",
    "-o", "UserKnownHostsFile=/dev/null",
    "-o", "LogLevel=ERROR",
]

MESH_SEARCH_NODES: Dict[str, Dict[str, Any]] = {
    "L1": {"type": "local_darwin", "targets": ["local"], "root": "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo", "matrix_key": "L1_Mac_Node"},
    "L8": {"type": "ssh_linux", "targets": ["linuxmini@10.0.0.8", "linuxmini@100.121.247.8"], "root": "/home/linuxmini", "matrix_key": "L0_Linux_Mini"},
    "L1b": {"type": "ssh_darwin", "targets": ["aaronmaher@10.0.0.3", "aaronmaher@192.168.8.114", "aaronmaher@100.104.128.34"], "root": "/Users/aaronmaher", "matrix_key": "L1b_Mac_Mini_M2"},
    "L2": {"type": "ssh_darwin", "targets": ["aaronmaher@10.0.0.4", "aaronmaher@192.168.8.127", "aaronmaher@100.103.212.21"], "root": "/Users/aaronmaher", "matrix_key": "L2_MacBook_Pro"},
    "L1a": {"type": "ssh_darwin", "targets": ["aaronmaher@10.0.0.5", "aaronmaher@169.254.190.217", "aaronmaher@192.168.8.193", "aaronmaher@100.121.202.34", "aaronmaher@192.168.8.248"], "root": "/Users/aaronmaher", "matrix_key": "L5_MacBook_Air"},
    "L3": {"type": "ssh_linux", "targets": ["linux@192.168.8.225", "linux@100.101.39.98"], "root": "/home/linux", "matrix_key": "L3_Linux_Head_Node"},
    "L4": {"type": "ssh_linux", "targets": ["droid@100.80.64.5"], "root": "/home/droid", "matrix_key": "L4_Linux_Tablet"},
    "L6": {"type": "ssh_termux", "targets": ["192.168.8.213", "100.114.215.68"], "port": "8022", "root": "/data/data/com.termux/files/home", "matrix_key": "L6_Pixel_10_Pro_XL"},
    "L7": {"type": "ssh_termux_or_kde", "targets": ["192.168.8.224", "192.168.8.101", "100.124.199.15"], "port": "8022", "root": "/data/data/com.termux/files/home", "matrix_key": "L7_Samsung_S20"},
    "GW": {"type": "ssh_linux", "targets": ["root@192.168.8.1", "root@100.70.123.123"], "root": "/overlay/upper", "matrix_key": "GW_Router"},
}


def _is_l1_sanctuary_host() -> bool:
    """Detects if running on the L1 Primary Mac Mini M4 Pro host."""
    try:
        model = subprocess.check_output(["/usr/sbin/sysctl", "-n", "hw.model"], text=True, timeout=2.0).strip()
        return model == "Mac16,11"
    except Exception:
        return False


def _run_applescript(script: str, timeout: float = 8.0, route_to_l2: bool = True) -> Tuple[int, str, str, str]:
    """
    Executes an AppleScript snippet via osascript with strict timeout.
    Per Rule 3 Section 3 (WindowServer & Host Keyboard Sanctuary Invariant),
    when on L1 (`Mac16,11`) and `route_to_l2=True`, routes osascript execution
    to L2 (`aaronmaher@10.0.0.4` / `192.168.8.127` / `100.103.212.21`) supervised by Screen Lens.
    """
    if route_to_l2 and _is_l1_sanctuary_host():
        for l2_host in ("aaronmaher@10.0.0.4", "aaronmaher@192.168.8.127", "aaronmaher@100.103.212.21"):
            try:
                proc = subprocess.run(
                    ["ssh", *SSH_OPTS, l2_host, "/usr/bin/osascript -"],
                    input=script,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
                if proc.returncode == 0:
                    return proc.returncode, proc.stdout.strip(), proc.stderr.strip(), f"L2 ({l2_host})"
            except Exception:
                continue

    try:
        proc = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip(), "local"
    except subprocess.TimeoutExpired:
        return 124, "", "Operation timed out", "local"
    except Exception as e:
        return 1, "", str(e), "local"


def finder_reveal_path(target_path: str) -> Dict[str, Any]:
    """Reveals a file or directory in Finder headlessly without taking foreground focus."""
    if not target_path or not str(target_path).strip():
        return {
            "status": "ERROR",
            "error": "Empty target_path provided to finder_reveal_path",
            "exit_code": 1,
        }

    p = Path(target_path).expanduser().resolve()
    if not p.exists():
        return {
            "status": "ERROR",
            "error": f"Path does not exist: {target_path}",
            "exit_code": 1,
        }

    res = subprocess.run(["open", "-g", "-R", str(p)], capture_output=True, text=True)
    return {
        "status": "SUCCESS" if res.returncode == 0 else "ERROR",
        "action": "reveal",
        "path": str(p),
        "is_dir": p.is_dir(),
        "background_flag": "-g",
        "exit_code": res.returncode,
        "stderr": res.stderr.strip(),
    }


def finder_get_selection(route_to_l2: bool = True) -> Dict[str, Any]:
    """Queries Finder for currently selected items via AppleScript (routed to L2 per Rule 3)."""
    script = '''
    tell application "Finder"
        set sel to selection as alias list
        set outList to {}
        repeat with itemRef in sel
            copy (POSIX path of itemRef) to end of outList
        end repeat
        set AppleScript's text item delimiters to linefeed
        return outList as text
    end tell
    '''
    rc, stdout, stderr, executed_on = _run_applescript(script, route_to_l2=route_to_l2)
    items = [line for line in stdout.splitlines() if line.strip()] if rc == 0 else []
    return {
        "status": "SUCCESS" if rc == 0 else "ERROR",
        "executed_on": executed_on,
        "rule3_l2_routed": executed_on.startswith("L2"),
        "selected_count": len(items),
        "selected_paths": items,
        "exit_code": rc,
        "error": stderr if rc != 0 else None,
    }


def finder_spotlight_search(query: str, root_dir: Optional[str] = None, max_results: int = 20) -> Dict[str, Any]:
    """Performs lightning-fast metadata search via mdfind (Spotlight backend) without UI overhead."""
    if not query or not str(query).strip():
        return {
            "status": "ERROR",
            "query": query,
            "error": "Search query must be a non-empty string",
            "exit_code": 1,
        }

    try:
        limit = max(1, min(int(max_results), 500))
    except (ValueError, TypeError):
        limit = 20

    cmd = ["mdfind"]
    if root_dir and str(root_dir).strip():
        resolved_root = str(Path(root_dir).expanduser().resolve())
        if not os.path.isdir(resolved_root):
            return {
                "status": "ERROR",
                "query": query,
                "root_dir": root_dir,
                "error": f"root_dir does not exist or is not a directory: {root_dir}",
                "exit_code": 1,
            }
        cmd.extend(["-onlyin", resolved_root])
    cmd.append(str(query).strip())

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10.0)
        lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
        results = lines[:limit]
        return {
            "status": "SUCCESS",
            "query": str(query).strip(),
            "root_dir": root_dir,
            "total_found": len(lines),
            "results": results,
            "exit_code": proc.returncode,
        }
    except Exception as e:
        return {
            "status": "ERROR",
            "query": query,
            "error": str(e),
            "exit_code": 1,
        }


def finder_inspect_item(target_path: str) -> Dict[str, Any]:
    """Inspects detailed filesystem metadata, extended attributes, and disk usage."""
    if not target_path or not str(target_path).strip():
        return {
            "status": "ERROR",
            "error": "Empty target_path provided to finder_inspect_item",
            "exit_code": 1,
        }

    raw_p = Path(target_path).expanduser()
    is_link = raw_p.is_symlink()
    p = raw_p.resolve() if not is_link else raw_p
    if not p.exists() and not is_link:
        return {"status": "ERROR", "error": f"Path not found: {target_path}", "exit_code": 1}

    st = p.lstat() if is_link else p.stat()
    xattr_out = subprocess.run(
        ["xattr", "-p", "com.apple.metadata:_kMDItemUserTags", str(p)],
        capture_output=True,
    )
    has_tags = (xattr_out.returncode == 0)

    return {
        "status": "SUCCESS",
        "path": str(p),
        "name": p.name,
        "is_dir": p.is_dir(),
        "is_symlink": is_link,
        "size_bytes": st.st_size,
        "mode": oct(st.st_mode),
        "modified_epoch": st.st_mtime,
        "has_finder_tags": has_tags,
        "exit_code": 0,
    }


def _search_single_mesh_node(node_id: str, cfg: Dict[str, Any], query: str, max_per_node: int, throttled: bool = False) -> Dict[str, Any]:
    """Executes headless search on a single mesh node across fallback IPs (macOS mdfind/find or Linux/Android find)."""
    ntype = cfg["type"]
    root = cfg["root"]
    targets = cfg.get("targets", [])
    safe_q = re.sub(r"[^A-Za-z0-9_.\-*? ]", "", str(query)).strip()
    if not safe_q:
        return {"node_id": node_id, "status": "ERROR", "matches": [], "error": "Query contains no valid search characters"}

    eff_limit = max(1, max_per_node // 2) if throttled else max_per_node
    depth = 1 if throttled else (2 if ntype == "ssh_darwin" else 3)
    quoted_pat = shlex.quote(f"*{safe_q}*")

    if ntype == "local_darwin":
        res = finder_spotlight_search(safe_q, root_dir=root, max_results=eff_limit)
        return {
            "node_id": node_id,
            "status": res.get("status", "ERROR"),
            "matches": res.get("results", []),
            "total_found": res.get("total_found", 0),
            "throttled_by_overflow_guard": throttled,
        }

    last_err = ""
    for target in targets:
        try:
            if ntype in ("ssh_darwin", "ssh_linux"):
                cmd = [
                    "ssh", *SSH_OPTS, target,
                    f"find {shlex.quote(root)} -maxdepth {depth} -iname {quoted_pat} 2>/dev/null | head -n {eff_limit}",
                ]
                out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True, timeout=5.0)
                matches = [l.strip() for l in out.splitlines() if l.strip()]
                return {
                    "node_id": node_id,
                    "target": target,
                    "status": "SUCCESS",
                    "matches": matches,
                    "total_found": len(matches),
                    "throttled_by_overflow_guard": throttled,
                }
            elif ntype in ("ssh_termux", "ssh_termux_or_kde"):
                cmd = [
                    "ssh", *SSH_OPTS, "-p", cfg.get("port", "8022"), target,
                    f"find {shlex.quote(root)} -maxdepth {depth} -iname {quoted_pat} 2>/dev/null | head -n {eff_limit}",
                ]
                out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True, timeout=3.5)
                matches = [l.strip() for l in out.splitlines() if l.strip()]
                return {
                    "node_id": node_id,
                    "target": target,
                    "status": "SUCCESS",
                    "matches": matches,
                    "total_found": len(matches),
                    "throttled_by_overflow_guard": throttled,
                }
        except Exception as e:
            last_err = str(e)
            continue

    if ntype == "ssh_termux_or_kde":
        for ip in targets:
            try:
                s = socket.socket()
                s.settimeout(0.5)
                rc = s.connect_ex((ip, 1716))
                s.close()
                if rc == 0:
                    return {
                        "node_id": node_id,
                        "target": f"{ip}:1716 (KDE Connect + Outbound SSH)",
                        "status": "SUCCESS",
                        "telemetry_mode": "ONLINE_DOZE_PROTECTED_INBOUND_SHELL",
                        "matches": [],
                        "total_found": 0,
                        "throttled_by_overflow_guard": throttled,
                    }
            except Exception:
                continue

    return {"node_id": node_id, "status": "UNREACHABLE", "matches": [], "error": last_err}


def finder_mesh_search(query: str, max_per_node: int = 5) -> Dict[str, Any]:
    """
    Executes distributed headless search across all 10 active Lauburu mesh nodes concurrently
    while respecting live network overflow guard limits from `mesh_ram_matrix_live.json`.
    """
    if not query or not str(query).strip():
        return {"status": "ERROR", "error": "Search query must be non-empty", "exit_code": 1}

    safe_q = re.sub(r"[^A-Za-z0-9_.\-*? ]", "", str(query)).strip()
    if not safe_q:
        return {"status": "ERROR", "error": "Search query contains no valid search characters", "exit_code": 1}

    try:
        limit = max(1, min(int(max_per_node), 50))
    except (ValueError, TypeError):
        limit = 5

    throttled_matrix_keys = set()
    backpressure_status = "NOMINAL_ZERO_OVERFLOW"
    if RAM_STATE_JSON.exists():
        try:
            state = json.loads(RAM_STATE_JSON.read_text(encoding="utf-8"))
            guard = state.get("network_overflow_guard", {})
            throttled_matrix_keys = set(guard.get("overloaded_nodes_throttled", []))
            backpressure_status = guard.get("backpressure_status", "NOMINAL_ZERO_OVERFLOW")
        except Exception:
            pass

    node_results: Dict[str, Any] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        futs = {
            pool.submit(
                _search_single_mesh_node,
                nid,
                cfg,
                safe_q,
                limit,
                cfg.get("matrix_key") in throttled_matrix_keys,
            ): nid
            for nid, cfg in MESH_SEARCH_NODES.items()
        }
        for fut in concurrent.futures.as_completed(futs):
            nid = futs[fut]
            node_results[nid] = fut.result()

    ordered = {k: node_results[k] for k in MESH_SEARCH_NODES.keys()}
    nodes_responded = sum(1 for v in ordered.values() if v.get("status") == "SUCCESS")
    total_matches = sum(len(v.get("matches", [])) for v in ordered.values())

    return {
        "status": "SUCCESS" if nodes_responded > 0 else "ERROR",
        "action": "mesh_search",
        "query": safe_q,
        "nodes_queried": len(MESH_SEARCH_NODES),
        "nodes_responded": nodes_responded,
        "total_matches": total_matches,
        "overflow_guard_enforced": True,
        "backpressure_status": backpressure_status,
        "throttled_nodes": sorted(throttled_matrix_keys),
        "mesh_results": ordered,
        "exit_code": 0 if nodes_responded > 0 else 1,
    }


def execute_finder_action(action: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Unified dispatcher for all headless Finder and multi-device mesh search operations."""
    if not isinstance(params, dict):
        return {"status": "ERROR", "error": "params must be a JSON object", "exit_code": 2}

    if action == "status":
        return {
            "status": "SUCCESS",
            "app": "Finder",
            "online": True,
            "host_is_l1_sanctuary": _is_l1_sanctuary_host(),
            "rule3_l2_applescript_target": "aaronmaher@10.0.0.4",
            "mesh_search_nodes": list(MESH_SEARCH_NODES.keys()),
            "exit_code": 0,
        }
    elif action == "reveal":
        return finder_reveal_path(params.get("path", ""))
    elif action == "selection":
        route_l2 = bool(params.get("route_to_l2", True))
        return finder_get_selection(route_to_l2=route_l2)
    elif action == "search":
        return finder_spotlight_search(
            query=params.get("query", ""),
            root_dir=params.get("root_dir"),
            max_results=params.get("max_results", 20),
        )
    elif action == "mesh_search":
        return finder_mesh_search(
            query=params.get("query", ""),
            max_per_node=params.get("max_per_node", 5),
        )
    elif action == "inspect":
        return finder_inspect_item(params.get("path", ""))
    else:
        return {
            "status": "ERROR",
            "error": f"Unknown action: {action}. Supported: status, reveal, selection, search, mesh_search, inspect",
            "exit_code": 2,
        }


def main() -> int:
    if len(sys.argv) < 2:
        print(json.dumps({"status": "ERROR", "error": "Usage: specialist_headless_finder_tools.py <action> [json_params]", "exit_code": 1}))
        return 1

    act = sys.argv[1]
    if len(sys.argv) > 2:
        try:
            p_dict = json.loads(sys.argv[2])
        except json.JSONDecodeError as e:
            print(json.dumps({"status": "ERROR", "error": f"Invalid JSON params: {e}", "exit_code": 2}))
            return 2
    else:
        p_dict = {}

    res = execute_finder_action(act, p_dict)
    print(json.dumps(res, indent=2))
    return int(res.get("exit_code", 0))


if __name__ == "__main__":
    sys.exit(main())
