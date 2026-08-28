#!/usr/bin/env python3
"""
00_core_infrastructure/seaweedfs/seaweed_tools.py
=================================================
Autonomous Smolagents Tools for SeaweedFS HA & Storage Reflex Arc.
Provides self-healing FUSE mount recovery and Raft consensus auditing.
"""

import json
import os
import platform
import subprocess
import time
import urllib.request
import urllib.error
from typing import Dict, Any, Optional, List, Tuple

# Graceful import of smolagents @tool decorator with fallback wrapper
try:
    from smolagents import tool
except ImportError:
    def tool(func=None, **kwargs):
        """Fallback tool decorator mimicking smolagents @tool when smolagents is not installed."""
        def decorator(f):
            f.name = f.__name__
            f.description = f.__doc__.strip().split("\n\n")[0] if f.__doc__ else ""
            f.func = f
            return f
        if func is not None:
            return decorator(func)
        return decorator


def _normalize_leader_addr(addr: str) -> str:
    """Normalize address string like '100.101.39.98:9333.19333' or '100.101.39.98:9333' to 'ip:http_port'."""
    if not addr:
        return ""
    addr = addr.strip()
    if "." in addr and ":" in addr:
        parts = addr.rsplit(".", 1)
        if len(parts) == 2 and parts[1].isdigit():
            return parts[0]
    return addr


def _parse_peer_endpoint(peer: str) -> Tuple[str, int]:
    """Parse peer address into (ip, http_port). Handles 'ip:port' and 'ip:port.grpc'."""
    peer = peer.strip()
    if not peer:
        return ("", 0)
    if "://" in peer:
        peer = peer.split("://", 1)[1]
    if ":" in peer:
        ip, rest = peer.split(":", 1)
        if "." in rest:
            http_port_str = rest.split(".", 1)[0]
        else:
            http_port_str = rest
        try:
            port = int(http_port_str)
        except ValueError:
            port = 9333
        return (ip, port)
    return (peer, 9333)


@tool
def heal_fuse_mount(
    mount_point: str = "/mnt/dfs_unified",
    filer_endpoints: str = "100.101.39.98:8888,100.119.199.76:8888,100.103.212.21:8888",
    force_lazy: bool = True,
    timeout_seconds: int = 10
) -> str:
    """Detects SeaweedFS FUSE mount health, forcefully dismantles hung mount points, and remounts.

    Args:
        mount_point: Absolute filesystem path to the SeaweedFS mount point.
        filer_endpoints: Comma-separated list of SeaweedFS Filer IP:port endpoints.
        force_lazy: If True, executes platform-specific lazy/force unmounting.
        timeout_seconds: Maximum time in seconds allocated for probe and recovery.

    Returns:
        A JSON-formatted string detailing health status, actions taken, and result.
    """
    system_os = platform.system()
    start_time = time.time()
    actions_taken: List[str] = []
    
    # Normalize mount point path
    mount_point = mount_point.strip() if mount_point else "/mnt/dfs_unified"
    
    # 1. Non-blocking VFS check
    is_mounted = False
    try:
        if system_os == "Darwin":
            res = subprocess.run(["mount"], capture_output=True, text=True, timeout=2.0)
            is_mounted = (
                f" on {mount_point} " in res.stdout
                or f" on {mount_point} (" in res.stdout
                or f" on {mount_point.rstrip('/')} " in res.stdout
                or f" on {mount_point.rstrip('/')} (" in res.stdout
            )
        else:
            if os.path.exists("/proc/mounts"):
                with open("/proc/mounts", "r") as f:
                    is_mounted = any(
                        f" {mount_point} " in line or f" {mount_point.rstrip('/')} " in line
                        for line in f
                    )
            else:
                res = subprocess.run(["mount"], capture_output=True, text=True, timeout=2.0)
                is_mounted = f" {mount_point} " in res.stdout or f" {mount_point.rstrip('/')} " in res.stdout
    except Exception as e:
        actions_taken.append(f"vfs_mount_check_exception: {str(e)}")

    # 2. Non-blocking I/O Probe
    is_frozen = False
    if is_mounted:
        try:
            probe_timeout = min(2.5, max(0.5, float(timeout_seconds)))
            probe_res = subprocess.run(
                ["stat", "-t", mount_point],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=probe_timeout
            )
            if probe_res.returncode == 0:
                actions_taken.append("canary_stat_probe_passed")
            else:
                is_frozen = True
                actions_taken.append(f"canary_stat_probe_failed_exit_{probe_res.returncode}")
        except subprocess.TimeoutExpired:
            is_frozen = True
            actions_taken.append("canary_stat_probe_timed_out")
        except Exception as e:
            is_frozen = True
            actions_taken.append(f"canary_stat_probe_exception: {str(e)}")
    else:
        actions_taken.append("mount_point_not_present_in_vfs")

    # If healthy and not frozen, return nominal status immediately
    if is_mounted and not is_frozen:
        return json.dumps({
            "status": "HEALTHY",
            "mount_point": mount_point,
            "is_mounted": True,
            "is_frozen": False,
            "actions_taken": actions_taken,
            "elapsed_seconds": round(time.time() - start_time, 3)
        })

    # 3. Forceful Teardown
    try:
        # Terminate lingering weed mount processes
        subprocess.run(
            f"pkill -9 -f 'weed mount.*{mount_point}'",
            shell=True,
            capture_output=True,
            timeout=2.0
        )
        actions_taken.append("evicted_lingering_weed_processes")
    except Exception as e:
        actions_taken.append(f"process_eviction_warning: {str(e)}")

    try:
        if system_os == "Darwin":
            subprocess.run(["diskutil", "unmount", "force", mount_point], capture_output=True, timeout=3.0)
            subprocess.run(["umount", "-f", mount_point], capture_output=True, timeout=3.0)
            actions_taken.append("force_unmount_darwin_executed")
        else:
            if force_lazy:
                subprocess.run(["umount", "-l", "-f", mount_point], capture_output=True, timeout=3.0)
                subprocess.run(["fusermount3", "-u", "-z", mount_point], capture_output=True, timeout=3.0)
                actions_taken.append("force_lazy_unmount_executed")
            else:
                subprocess.run(["umount", mount_point], capture_output=True, timeout=3.0)
                actions_taken.append("standard_unmount_executed")
    except Exception as e:
        actions_taken.append(f"unmount_execution_error: {str(e)}")

    # 4. Pre-Flight Filer Reachability Check
    filers = [f.strip() for f in filer_endpoints.split(",") if f.strip()]
    reachable_filers: List[str] = []
    for filer in filers:
        try:
            url = f"http://{filer}/"
            req = urllib.request.Request(url, headers={"User-Agent": "SeaweedHealer/1.0"})
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                if resp.status in (200, 404, 301, 302, 400, 401, 403):
                    reachable_filers.append(filer)
        except urllib.error.HTTPError as e:
            if e.code in (200, 404, 301, 302, 400, 401, 403):
                reachable_filers.append(filer)
        except Exception:
            pass

    if not reachable_filers:
        actions_taken.append("preflight_check_failed_all_filers_unreachable")
        return json.dumps({
            "status": "UNMOUNTED_FILER_OFFLINE",
            "mount_point": mount_point,
            "is_mounted": False,
            "error": "No SeaweedFS Filers reachable across the mesh. Mount cleared to prevent host freeze.",
            "reachable_filers": [],
            "actions_taken": actions_taken,
            "elapsed_seconds": round(time.time() - start_time, 3)
        })

    actions_taken.append(f"preflight_filer_check_passed_endpoint_{reachable_filers[0]}")

    # 5. Clean Remount
    try:
        os.makedirs(mount_point, exist_ok=True)
        remount_cmd = [
            "weed", "mount",
            f"-filer={filer_endpoints}",
            f"-dir={mount_point}",
            "-filer.path=/",
            "-cacheCapacityMB=1024",
            "-chunkSizeLimitMB=16",
            "-concurrentWriters=32",
            "-allowOthers=true",
            "-umask=000",
            "-readOnly=false"
        ]
        log_name = os.path.basename(mount_point.rstrip('/')) or "dfs_unified"
        log_path = f"/tmp/weed_mount_{log_name}.log"
        with open(log_path, "a") as log_file:
            subprocess.Popen(remount_cmd, stdout=log_file, stderr=log_file, start_new_session=True)
        actions_taken.append("remount_command_executed")
        time.sleep(2.0)
    except Exception as e:
        actions_taken.append(f"remount_launch_error: {str(e)}")

    # 6. Post-Remount Verification
    post_mounted = False
    try:
        if system_os == "Darwin":
            res = subprocess.run(["mount"], capture_output=True, text=True, timeout=2.0)
            post_mounted = (
                f" on {mount_point} " in res.stdout
                or f" on {mount_point} (" in res.stdout
                or f" on {mount_point.rstrip('/')} " in res.stdout
                or f" on {mount_point.rstrip('/')} (" in res.stdout
            )
        else:
            if os.path.exists("/proc/mounts"):
                with open("/proc/mounts", "r") as f:
                    post_mounted = any(
                        f" {mount_point} " in line or f" {mount_point.rstrip('/')} " in line
                        for line in f
                    )
            else:
                res = subprocess.run(["mount"], capture_output=True, text=True, timeout=2.0)
                post_mounted = f" {mount_point} " in res.stdout or f" {mount_point.rstrip('/')} " in res.stdout
    except Exception:
        pass

    if post_mounted:
        actions_taken.append("post_remount_stat_probe_verified")
        final_status = "HEALED_SUCCESSFULLY"
    else:
        actions_taken.append("post_remount_verification_failed")
        final_status = "REMOUNT_FAILED"

    return json.dumps({
        "status": final_status,
        "mount_point": mount_point,
        "is_mounted": post_mounted,
        "reachable_filers": reachable_filers,
        "actions_taken": actions_taken,
        "elapsed_seconds": round(time.time() - start_time, 3)
    })


@tool
def check_raft_consensus(
    master_peers: str = "100.101.39.98:9333,100.119.199.76:9333,100.103.212.21:9333",
    timeout_seconds: int = 3
) -> str:
    """Audits Raft consensus health, leader election status, quorum integrity, and volume topology.

    Args:
        master_peers: Comma-separated list of SeaweedFS Master IP:port endpoints to audit.
        timeout_seconds: Network socket timeout in seconds for each master node status probe.

    Returns:
        A JSON-formatted string containing cluster leader, quorum health status, individual peer states, split-brain detection, and storage topology metrics.
    """
    start_time = time.time()
    peers = [p.strip() for p in master_peers.split(",") if p.strip()]
    total_configured = len(peers)
    quorum_required = (total_configured // 2) + 1 if total_configured > 0 else 0
    timeout = max(0.1, float(timeout_seconds))

    peer_reports: Dict[str, Any] = {}
    leaders_reported: Dict[str, List[str]] = {}
    total_free_volumes = 0
    total_max_volumes = 0

    for peer in peers:
        ip, port = _parse_peer_endpoint(peer)
        peer_info: Dict[str, Any] = {"endpoint": peer, "reachable": False}
        
        if not ip or port <= 0:
            peer_info["error"] = "Invalid peer endpoint format"
            peer_reports[peer] = peer_info
            continue

        # 1. Query /cluster/status
        try:
            url_cluster = f"http://{ip}:{port}/cluster/status"
            req = urllib.request.Request(
                url_cluster,
                headers={"User-Agent": "SeaweedAuditor/1.0", "Accept": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    raw_body = resp.read().decode("utf-8")
                    data = json.loads(raw_body)
                    peer_info["reachable"] = True
                    is_leader = bool(data.get("IsLeader", False))
                    raw_leader = data.get("Leader", "")
                    normalized_leader = _normalize_leader_addr(raw_leader) if raw_leader else ""
                    
                    peer_info["is_leader"] = is_leader
                    peer_info["reported_leader"] = normalized_leader
                    peer_info["peers"] = data.get("Peers", [])
                    
                    if normalized_leader:
                        leaders_reported.setdefault(normalized_leader, []).append(peer)
                    elif is_leader:
                        leaders_reported.setdefault(f"{ip}:{port}", []).append(peer)

                    # Extract volume metrics if embedded in cluster status
                    vol_data = data.get("VolumeStatus", {})
                    if isinstance(vol_data, dict):
                        try:
                            peer_info["free_volumes"] = int(vol_data.get("Free", 0))
                            peer_info["max_volumes"] = int(vol_data.get("Max", 0))
                        except (ValueError, TypeError):
                            pass
                else:
                    peer_info["cluster_error"] = f"HTTP_{resp.status}"
        except urllib.error.HTTPError as e:
            peer_info["cluster_error"] = f"HTTP_{e.code}"
        except Exception as e:
            peer_info["cluster_error"] = str(e)

        # 2. Query /dir/status for storage metrics if reachable
        if peer_info.get("reachable", False):
            try:
                url_dir = f"http://{ip}:{port}/dir/status"
                req = urllib.request.Request(
                    url_dir,
                    headers={"User-Agent": "SeaweedAuditor/1.0", "Accept": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    if resp.status == 200:
                        dir_body = resp.read().decode("utf-8")
                        dir_data = json.loads(dir_body)
                        topology = dir_data.get("Topology", {})
                        free_vols = topology.get("Free", 0)
                        max_vols = topology.get("Max", 0)
                        peer_info["free_volumes"] = free_vols
                        peer_info["max_volumes"] = max_vols
            except Exception as e:
                peer_info["dir_error"] = str(e)

        peer_reports[peer] = peer_info

    # 3. Quorum & Consensus calculations
    reachable_count = sum(1 for p in peer_reports.values() if p.get("reachable", False))
    has_quorum = (reachable_count >= quorum_required) if quorum_required > 0 else False

    # Check distinct leaders
    distinct_leaders = [l for l in leaders_reported.keys() if l and l != "UNKNOWN"]
    is_split_brain = len(distinct_leaders) > 1

    if is_split_brain:
        status_str = "SPLIT_BRAIN_DETECTED"
        consensus_leader = ""
    elif reachable_count == 0 or not has_quorum:
        status_str = "QUORUM_LOST_CRITICAL"
        consensus_leader = distinct_leaders[0] if distinct_leaders else ""
    elif len(distinct_leaders) == 0:
        status_str = "NO_LEADER_ELECTED"
        consensus_leader = ""
    else:
        status_str = "QUORUM_HEALTHY"
        consensus_leader = distinct_leaders[0]

    # Calculate total free and max volumes
    leader_entry = next(
        (p for p in peer_reports.values() if p.get("is_leader", False) and "free_volumes" in p),
        None
    )
    if leader_entry is not None:
        total_free_volumes = int(leader_entry.get("free_volumes", 0))
        total_max_volumes = int(leader_entry.get("max_volumes", 0))
    else:
        for p in peer_reports.values():
            if isinstance(p.get("free_volumes"), (int, float)):
                total_free_volumes += int(p["free_volumes"])
            if isinstance(p.get("max_volumes"), (int, float)):
                total_max_volumes += int(p["max_volumes"])

    return json.dumps({
        "status": status_str,
        "has_quorum": has_quorum,
        "quorum_required": quorum_required,
        "reachable_peers_count": reachable_count,
        "total_configured_peers": total_configured,
        "consensus_leader": consensus_leader,
        "is_split_brain": is_split_brain,
        "total_free_volumes": total_free_volumes,
        "total_max_volumes": total_max_volumes,
        "peer_details": peer_reports,
        "elapsed_seconds": round(time.time() - start_time, 3)
    }, indent=2)


if __name__ == "__main__":
    import sys
    print("Testing seaweed_tools functions...")
    res_raft = check_raft_consensus()
    print("check_raft_consensus result:")
    print(res_raft)
