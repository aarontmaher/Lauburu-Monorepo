#!/usr/bin/env python3
"""
Multi-WAN Speedify-Like Bond Manager
Lauburu Immortal Swarm — Generation 75
Scores and ranks all available WAN transport paths for optimal llama.cpp tensor shard routing.
Includes TP-Link Extender Ethernet (enx98fc84e6e212) dynamic fitness scoring and sysfs link probing.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# ─── Monorepo root detection ────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parents[2]
NETWORK_DATA_DIR = REPO_ROOT / "data" / "network"
LORA_DIR = REPO_ROOT / "data" / "lora_datasets"
OUTPUT_FILE = NETWORK_DATA_DIR / "wan_fitness_scores.json"
LORA_FILE = LORA_DIR / "network_decisions.jsonl"

NETWORK_DATA_DIR.mkdir(parents=True, exist_ok=True)
LORA_DIR.mkdir(parents=True, exist_ok=True)

# ─── Known WAN transport paths ───────────────────────────────────────────────
WAN_PATHS = [
    {
        "name": "TPLink_Extender_Ethernet",
        "interface": "enx98fc84e6e212",
        "interface_candidates": ["enx98fc84e6e212", "eth0", "en0"],
        "mac_address": "98:fc:84:e6:e2:12",
        "type": "extender_ethernet",
        "max_theoretical_mbps": 1000,
        "fallback_mbps": 100,
        "probe_host": "192.168.8.1",
        "route_metric": 100,
        "routing_table": 200,
        "table_name": "tplink_mesh",
        "description": "TP-Link Range Extender Layer 2 Client Bridge Ethernet on enx98fc84e6e212",
    },
    {
        "name": "Ethernet",
        "interface": "eth0",
        "interface_candidates": ["eth0", "en0", "enp3s0"],
        "type": "wired",
        "max_theoretical_mbps": 1000,
        "probe_host": "192.168.8.1",
    },
    {
        "name": "WiFi_6E_GLiNet",
        "ssid": "GL-MT3600BE-a0f-MLO",
        "gateway": "192.168.8.1",
        "type": "wifi6e",
        "max_theoretical_mbps": 1200,
        "probe_host": "192.168.8.1",
    },
    {
        "name": "AbsoluteMesh_2_4GHz",
        "ssid": "Absolute Mesh",
        "password": "W0rshipDan",
        "band": "2.4GHz",
        "type": "wifi",
        "max_theoretical_mbps": 300,
        "probe_host": "192.168.8.1",
    },
    {
        "name": "AbsoluteMesh_5GHz",
        "ssid": "Absolute Mesh",
        "password": "W0rshipDan",
        "band": "5GHz",
        "type": "wifi5",
        "max_theoretical_mbps": 867,
        "probe_host": "192.168.8.1",
    },
    {
        "name": "AbsoluteMesh_WiFi7_6GHz",
        "ssid": "Absolute Mesh",
        "password": "W0rshipDan",
        "band": "6GHz",
        "type": "wifi7",
        "max_theoretical_mbps": 2400,
        "probe_host": "192.168.8.1",
    },
    {
        "name": "Pixel_Hotspot_5GHz",
        "host": "100.73.38.87",
        "type": "hotspot",
        "band": "5GHz",
        "max_theoretical_mbps": 600,
        "probe_host": "100.73.38.87",
    },
    {
        "name": "Pixel_Hotspot_6GHz",
        "host": "100.73.38.87",
        "type": "hotspot",
        "band": "6GHz",
        "max_theoretical_mbps": 1200,
        "probe_host": "100.73.38.87",
    },
]


def resolve_interface_and_speed(path_def: dict) -> Tuple[Optional[str], float, bool]:
    """
    Dynamically resolves interface presence, operational state, carrier status,
    and negotiated link speed from Linux sysfs (/sys/class/net/).
    """
    candidates = path_def.get("interface_candidates", [])
    primary_iface = path_def.get("interface")
    if primary_iface and primary_iface not in candidates:
        candidates = [primary_iface] + candidates
        
    nominal_bw = float(path_def.get("max_theoretical_mbps", 1000))
    fallback_bw = float(path_def.get("fallback_mbps", 100))
    
    # 1. Linux sysfs inspection
    for iface in candidates:
        sysfs_dir = Path(f"/sys/class/net/{iface}")
        if sysfs_dir.exists():
            carrier = False
            carrier_file = sysfs_dir / "carrier"
            if carrier_file.exists():
                try:
                    carrier = (carrier_file.read_text().strip() == "1")
                except Exception:
                    carrier = False
                    
            speed_file = sysfs_dir / "speed"
            bw = nominal_bw
            if speed_file.exists():
                try:
                    detected_speed = float(speed_file.read_text().strip())
                    if detected_speed > 0:
                        bw = detected_speed
                except Exception:
                    bw = nominal_bw if carrier else fallback_bw
            return iface, bw, carrier

    # 2. macOS / Darwin fallback
    if sys.platform == "darwin":
        for iface in candidates:
            res = subprocess.run(["ifconfig", iface], capture_output=True, text=True)
            if res.returncode == 0 and "status: active" in res.stdout:
                return iface, nominal_bw, True

    # 3. Default return
    return primary_iface, nominal_bw, False


def ping_rtt(host: str, interface: Optional[str] = None, count: int = 3, timeout: int = 2) -> Tuple[bool, Optional[float], float]:
    """
    Ping a host (optionally bound to an interface) and return (reachable, avg_rtt_ms, packet_loss_pct).
    """
    cmd = ["ping", "-c", str(count)]
    if sys.platform == "darwin":
        cmd.extend(["-W", str(timeout * 1000)])
    else:
        cmd.extend(["-W", str(timeout)])
        
    if interface:
        cmd.extend(["-I", interface])
        
    cmd.append(host)
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=count * (timeout + 1) + 2,
        )
        if result.returncode != 0:
            if interface:
                fallback_cmd = ["ping", "-c", str(count)]
                if sys.platform == "darwin":
                    fallback_cmd.extend(["-W", str(timeout * 1000)])
                else:
                    fallback_cmd.extend(["-W", str(timeout)])
                fallback_cmd.append(host)
                fb_res = subprocess.run(fallback_cmd, capture_output=True, text=True, timeout=count * (timeout + 1) + 2)
                if fb_res.returncode == 0:
                    times = re.findall(r"time=([\d.]+)\s*ms", fb_res.stdout)
                    avg = sum(float(t) for t in times) / len(times) if times else None
                    return True, avg, 0.0
            return False, None, 100.0
            
        loss = 0.0
        loss_match = re.search(r"(\d+(?:\.\d+)?)%\s+packet loss", result.stdout)
        if loss_match:
            loss = float(loss_match.group(1))
            
        match = re.search(r"(?:min/avg/max/(?:stddev|mdev)|round-trip)\s*=\s*[\d.]+/([\d.]+)/", result.stdout)
        if match:
            return True, float(match.group(1)), loss
            
        times = re.findall(r"time=([\d.]+)\s*ms", result.stdout)
        if times:
            avg = sum(float(t) for t in times) / len(times) if times else None
            return True, avg, loss
            
        return True, None, loss
    except subprocess.TimeoutExpired:
        return False, None, 100.0
    except Exception:
        return False, None, 100.0


def compute_score(bandwidth_theoretical: float, rtt_ms: Optional[float], reachable: bool, packet_loss_pct: float = 0.0) -> float:
    """WAN fitness score (0-100)."""
    bw_score = (min(bandwidth_theoretical, 1000.0) / 1000.0) * 50.0
    loss_factor = max(0.0, 1.0 - (packet_loss_pct / 100.0))
    
    if reachable and rtt_ms is not None:
        lat_score = max(0.0, 1.0 - rtt_ms / 200.0) * 30.0 * loss_factor
    else:
        lat_score = 0.0
        
    reach_score = 20.0 if reachable else 0.0
    return round(bw_score + lat_score + reach_score, 2)


def assign_roles(scored_paths: list) -> list:
    """Sort by score desc and assign PRIMARY/SECONDARY/TERTIARY/FALLBACK roles."""
    active = sorted(
        [p for p in scored_paths if p["status"] == "ACTIVE"],
        key=lambda x: x["score"],
        reverse=True,
    )
    pending = [p for p in scored_paths if p["status"] == "PENDING_HARDWARE_VERIFICATION"]
    roles = ["PRIMARY", "SECONDARY", "TERTIARY", "FALLBACK"]
    for i, path in enumerate(active):
        path["recommended_role"] = roles[min(i, len(roles) - 1)]
    for path in pending:
        path["recommended_role"] = "FALLBACK"
    return active + pending


def check_mlvpn_installed() -> dict:
    """Check if mlvpn is installed."""
    result = subprocess.run(["which", "mlvpn"], capture_output=True)
    if result.returncode != 0:
        return {"installed": False, "note": "mlvpn not found — true bonding unavailable"}
    return {"installed": True, "path": result.stdout.decode().strip()}


def check_openmptcprouter() -> dict:
    """Check if OpenMPTCProuter is available."""
    result = subprocess.run(["which", "openmptcprouter"], capture_output=True)
    if result.returncode != 0:
        return {"installed": False, "note": "OpenMPTCProuter not found"}
    return {"installed": True, "path": result.stdout.decode().strip()}


def build_test_command(path: dict, resolved_iface: Optional[str] = None) -> str:
    """Return the exact shell command to manually verify this path."""
    host = path.get("probe_host") or path.get("host") or path.get("gateway", "")
    if path["type"] in ("hotspot",):
        return f"ping -c 5 {host} && curl -s --interface <hotspot_iface> http://speedtest.net"
    if path["type"] in ("wired", "extender_ethernet"):
        iface = resolved_iface or path.get("interface", "enx98fc84e6e212")
        return f"ip link show {iface} && ping -c 5 -I {iface} {host}"
    ssid = path.get("ssid", "")
    band = path.get("band", "")
    pw = path.get("password", "")
    return f"networksetup -setairportnetwork en0 '{ssid}' '{pw}' # Connect to {ssid} ({band}) then: ping -c 5 {host}"


def measure_paths(verbose: bool = True) -> list:
    """Probe all WAN paths and return scored results."""
    results = []
    for path_def in WAN_PATHS:
        name = path_def["name"]
        host = path_def.get("probe_host") or path_def.get("host") or path_def.get("gateway", "")
        
        # Resolve dynamic interface and bandwidth
        resolved_iface, effective_bw, carrier_active = resolve_interface_and_speed(path_def)
        test_cmd = build_test_command(path_def, resolved_iface)

        if verbose:
            iface_str = f" via {resolved_iface}" if resolved_iface else ""
            print(f"  Probing [{name}{iface_str}] -> {host} ...", end=" ", flush=True)

        reachable, rtt_ms, loss = ping_rtt(host, interface=resolved_iface)
        score = compute_score(effective_bw, rtt_ms, reachable, packet_loss_pct=loss)

        if reachable:
            status = "ACTIVE"
            if verbose:
                rtt_str = f"{rtt_ms:.1f}ms" if rtt_ms is not None else "RTT-parse-failed"
                loss_str = f" loss={loss:.0f}%" if loss > 0 else ""
                print(f"ACTIVE  RTT={rtt_str}{loss_str}  BW={effective_bw:.0f}Mbps  score={score}")
        else:
            status = "PENDING_HARDWARE_VERIFICATION"
            if verbose:
                print(f"PENDING_HARDWARE_VERIFICATION  score={score}")

        entry = {
            "name": name,
            "type": path_def["type"],
            "status": status,
            "rtt_ms": rtt_ms,
            "packet_loss_pct": loss,
            "max_theoretical_mbps": effective_bw,
            "score": score,
            "recommended_role": "FALLBACK",
            "test_command": test_cmd,
        }
        if "interface" in path_def:
            entry["interface"] = path_def["interface"]
        if resolved_iface:
            entry["resolved_interface"] = resolved_iface
        if "mac_address" in path_def:
            entry["mac_address"] = path_def["mac_address"]
        if "route_metric" in path_def:
            entry["route_metric"] = path_def["route_metric"]
            
        if status == "PENDING_HARDWARE_VERIFICATION":
            entry["verification_note"] = f"Path unreachable from this host. Run: {test_cmd}"
        results.append(entry)
    return results


def build_recommendation(scored_paths: list) -> dict:
    """Build routing recommendation block."""
    active_sorted = sorted(
        [p for p in scored_paths if p["status"] == "ACTIVE"],
        key=lambda x: x["score"],
        reverse=True,
    )
    names = [p["name"] for p in active_sorted]
    return {
        "primary": names[0] if len(names) > 0 else "NONE_ACTIVE",
        "secondary": names[1] if len(names) > 1 else "NONE_ACTIVE",
        "tertiary": names[2] if len(names) > 2 else "NONE_ACTIVE",
        "llama_rpc_routing": (
            "Route tensor shards across PRIMARY + SECONDARY simultaneously for maximum throughput. "
            "Use TERTIARY for KV cache overflow. FALLBACK paths engage only on PRIMARY+SECONDARY failure."
        ),
    }


def serialize_lora(paths: list, recommendation: dict) -> None:
    """Append scoring decisions as LoRA training pairs."""
    path_summary = "; ".join(
        f"{p['name']}={p['status']}(score={p['score']},role={p['recommended_role']})"
        for p in paths
    )
    entry = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "instruction": (
            "Given a set of WAN transport paths with their bandwidth and RTT measurements, "
            "compute WAN fitness scores and assign routing roles for llama.cpp tensor shard distribution."
        ),
        "input": path_summary,
        "output": (
            f"Primary: {recommendation['primary']}, "
            f"Secondary: {recommendation['secondary']}, "
            f"Tertiary: {recommendation['tertiary']}. "
            f"Routing: {recommendation['llama_rpc_routing']}"
        ),
    }
    with open(LORA_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


def run_once(verbose: bool = True) -> dict:
    """Single measurement cycle."""
    if verbose:
        print(f"\n[multiwan_bond_manager] Measuring WAN paths -- {datetime.now(timezone.utc).isoformat()}")
        print("-" * 70)

    mlvpn = check_mlvpn_installed()
    omr = check_openmptcprouter()

    paths = measure_paths(verbose=verbose)
    paths = assign_roles(paths)
    recommendation = build_recommendation(paths)

    result = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "host": "linux-1" if Path("/sys/class/net/enx98fc84e6e212").exists() else "Development_Host",
        "bonding_tools": {"mlvpn": mlvpn, "openmptcprouter": omr},
        "paths": paths,
        "recommendation": recommendation,
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(result, f, indent=2)

    serialize_lora(paths, recommendation)

    if verbose:
        print(f"\n[OK] Written -> {OUTPUT_FILE}")
        print(f"[OK] LoRA entry appended -> {LORA_FILE}")
        print(f"\nRecommendation:")
        print(f"  PRIMARY   -> {recommendation['primary']}")
        print(f"  SECONDARY -> {recommendation['secondary']}")
        print(f"  TERTIARY  -> {recommendation['tertiary']}")
        print(f"  ROUTING   -> {recommendation['llama_rpc_routing']}")

    return result


def main():
    parser = argparse.ArgumentParser(description="Multi-WAN Bond Manager -- Lauburu Swarm Gen 75")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--once", action="store_true", help="Single measurement run")
    group.add_argument("--daemon", action="store_true", help="Continuous daemon mode (60s interval)")
    parser.add_argument("--quiet", action="store_true", help="Suppress verbose output")
    args = parser.parse_args()

    verbose = not args.quiet

    if args.once:
        run_once(verbose=verbose)
    elif args.daemon:
        print("[multiwan_bond_manager] Daemon mode (60s) -- Ctrl+C to stop")
        cycle = 0
        while True:
            cycle += 1
            if verbose:
                print(f"\n{'='*70}\n  DAEMON CYCLE #{cycle}")
            try:
                run_once(verbose=verbose)
            except Exception as e:
                print(f"[ERROR] Cycle {cycle}: {e}", file=sys.stderr)
            time.sleep(60)


if __name__ == "__main__":
    main()
