#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Canonical Multi-Transport Mesh Ping & Connectivity Engine (Generation 31)
========================================================================
Implements the 6-tier Physical Transport & Actuation Hierarchy:
  Tier 1: Bluetooth RFCOMM / RFConnect (Layer 0 IP-less serial control plane)
  Tier 2: Bluetooth PAN (Layer 1 IP tethering / bnep0)
  Tier 3: Ethernet Cables (Layer 2 physical twisted pair RJ45 / LAN)
  Tier 4: Thunderbolt Cables (Layer 2 40Gbps DMA bridge)
  Tier 5: SSH Actuation Plane (Multi-Transport Secure Shell with ControlMaster)
  Tier 6: Application & Service Plane (RPC 50052, Qdrant 6333, Models 8081-8085, Lens 4003)

Features:
  - Fast-Path Carrier Probing (<1ms kernel carrier check + 50ms socket micro-probe)
    bypassing Bluetooth head-of-line blocking when physical links are carrier-active.
  - Strict Sequential Fallback (Layer 0 RFCOMM -> Layer 1 PAN -> Layer 2 Ethernet -> Layer 2 Thunderbolt)
    when carrier is down or --strict-recovery flag is asserted.
  - Interface Contract compliance with PROJECT.md:
      resolve_node(node_name, fast_path=True, timeout=0.5) -> dict
      probe_physical_tier(node_name, tier) -> bool
"""

import argparse
import fcntl
import json
import os
import socket
import struct
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

MATRIX_PATH = os.path.join(os.path.dirname(__file__), "mesh_ip_matrix.json")
BLUEUTIL_PATH = "/Users/aaron/.local/bin/blueutil"

ALIAS_MAP = {
    "desktop_q4si00p": "L4_Linux_Tablet",
    "tablet": "L4_Linux_Tablet",
    "macbook_pro_vault": "L2_MacBook_Pro",
    "macbook-pro": "L2_MacBook_Pro",
    "mbp": "L2_MacBook_Pro",
    "linux_head_node": "L3_Linux_Hub",
    "linux-ts": "L3_Linux_Hub",
    "macbook_air": "L5_MacBook_Air",
    "macbook-air": "L5_MacBook_Air",
    "mba": "L5_MacBook_Air",
    "pixel_10": "L6_Pixel_10_Edge",
    "pixel": "L6_Pixel_10_Edge",
    "samsung_s20": "L7_Samsung_S20",
    "s20": "L7_Samsung_S20",
    "gl_travel_router": "GW_Router",
    "router": "GW_Router",
    "mac_mini_host": "L1_Mac_Host",
    "mac-mini": "L1_Mac_Host",
    "mac-mini-m4": "L1",
    "localhost": "L1_Mac_Host",
    "linux_mini": "L8_Linux_Mini",
    "linuxmini": "L8_Linux_Mini",
    "linux-mini-cpu": "L8",
    "lauburu": "L8",
    "mac-mini-m2": "L1b",
    "mac_mini_m2": "L1b",
    "l1": "L1",
    "l1b": "L1b",
    "l2": "L2",
    "l3": "L3",
    "l4": "L4",
    "l5": "L5",
    "l6": "L6",
    "l7": "L7",
    "l8": "L8",
    "gw": "GW",
}


def load_matrix() -> Dict[str, Any]:
    """Loads the canonical mesh IP matrix."""
    if not os.path.exists(MATRIX_PATH):
        return {}
    try:
        with open(MATRIX_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict) and "nodes" in data and isinstance(data["nodes"], dict):
                merged = dict(data)
                merged.update(data["nodes"])
                return merged
            return data
    except Exception:
        return {}


def resolve_alias(name: str, matrix: Dict[str, Any]) -> Optional[str]:
    """Resolves arbitrary aliases, casing, and legacy keys to canonical matrix keys."""
    if not name or not isinstance(name, str):
        return None
    raw = name.strip()
    if raw in matrix and not raw.startswith("_"):
        return raw
    norm = raw.lower().replace("-", "_").replace(" ", "_")
    if norm in ALIAS_MAP:
        return ALIAS_MAP[norm]
    raw_lower = raw.lower()
    if raw_lower in ALIAS_MAP:
        return ALIAS_MAP[raw_lower]
    for k in matrix:
        if k.startswith("_"):
            continue
        if k.lower() == raw_lower or k.lower().replace("-", "_") == norm:
            return k
    return None


def check_interface_carrier(ifname: str) -> bool:
    """
    Sub-millisecond kernel carrier check (<1ms) via OS ioctl / sysfs.
    Uses SIOCGIFMEDIA ioctl on macOS and /sys/class/net operstate on Linux,
    with subprocess ifconfig / ip fallback.
    """
    if sys.platform == "darwin":
        # SIOCGIFMEDIA ioctl (_IOWR('i', 56, struct ifmediareq))
        SIOCGIFMEDIA = 0xC0286938
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                req = struct.pack("16siiiiiP", ifname.encode("utf-8"), 0, 0, 0, 0, 0, 0)
                res = fcntl.ioctl(s.fileno(), SIOCGIFMEDIA, req)
                status = struct.unpack("16siiiiiP", res)[3]
                # IFM_AVALID = 0x00000001, IFM_ACTIVE = 0x00000002
                return bool((status & 1) and (status & 2))
            finally:
                s.close()
        except Exception:
            pass
        try:
            res = subprocess.run(["ifconfig", ifname], capture_output=True, text=True, timeout=0.2)
            if res.returncode == 0:
                return "status: active" in res.stdout
        except Exception:
            pass
    elif sys.platform.startswith("linux"):
        try:
            operstate = f"/sys/class/net/{ifname}/operstate"
            if os.path.exists(operstate):
                with open(operstate, "r") as f:
                    return f.read().strip() in ("up", "unknown")
            carrier = f"/sys/class/net/{ifname}/carrier"
            if os.path.exists(carrier):
                with open(carrier, "r") as f:
                    return f.read().strip() == "1"
            res = subprocess.run(["ip", "link", "show", ifname], capture_output=True, text=True, timeout=0.2)
            if res.returncode == 0:
                return "state UP" in res.stdout
        except Exception:
            pass
    return False


def ping_port_rtt(host: str, port: int, timeout: float = 0.5) -> Tuple[bool, float]:
    """
    Attempts connection and measures round-trip time in milliseconds.
    Supports IPv4, scoped link-local IPv6 (e.g. fe80::...%bridge0), and standard IPv6.
    """
    t0 = time.perf_counter()
    try:
        if "%" in host:
            addr, ifname = host.split("%")
            scope_idx = socket.if_nametoindex(ifname)
            s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            s.settimeout(timeout)
            res = s.connect_ex((addr, port, 0, scope_idx))
            s.close()
            rtt = (time.perf_counter() - t0) * 1000.0
            return (res == 0, rtt)
        elif ":" in host and not host.startswith("127."):
            s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            s.settimeout(timeout)
            res = s.connect_ex((host, port))
            s.close()
            rtt = (time.perf_counter() - t0) * 1000.0
            return (res == 0, rtt)
        else:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            res = s.connect_ex((host, port))
            s.close()
            rtt = (time.perf_counter() - t0) * 1000.0
            return (res == 0, rtt)
    except OSError:
        rtt = (time.perf_counter() - t0) * 1000.0
        return (False, rtt)


def ping_port(host: str, port: int, timeout: float = 2.0) -> bool:
    """Backward-compatible boolean port ping."""
    connected, _ = ping_port_rtt(host, port, timeout=timeout)
    return connected


def ping_icmp_rtt(ip: str, timeout: float = 1.0) -> Tuple[bool, float]:
    """
    Sends a single ICMP echo request with strict timeout and measures authentic
    elapsed round-trip execution time in milliseconds via time.perf_counter().
    """
    t0 = time.perf_counter()
    try:
        cmd = ["ping", "-c", "1", "-W", str(max(1, int(timeout * 1000))), ip]
        res = subprocess.run(cmd, capture_output=True, timeout=timeout + 0.5)
        elapsed = (time.perf_counter() - t0) * 1000.0
        return (res.returncode == 0, elapsed)
    except Exception:
        elapsed = (time.perf_counter() - t0) * 1000.0
        return (False, elapsed)


def ping_icmp(ip: str, timeout: float = 1.0) -> bool:
    """Sends a single ICMP echo request with strict timeout."""
    ok, _ = ping_icmp_rtt(ip, timeout=timeout)
    return ok


def check_bluetooth_presence(rf_mac: str, timeout: float = 1.0, try_connect: bool = False) -> bool:
    """
    Checks if a Bluetooth device is connected via blueutil.
    If try_connect is True, actively attempts a connection handshake.
    """
    if not rf_mac:
        return False
    bt_addr = rf_mac.replace(":", "-").lower()
    if os.path.exists(BLUEUTIL_PATH):
        try:
            res = subprocess.run([BLUEUTIL_PATH, "--is-connected", bt_addr], capture_output=True, text=True, timeout=timeout)
            if res.returncode == 0 and res.stdout.strip() == "1":
                return True
            if try_connect:
                res = subprocess.run([BLUEUTIL_PATH, "--connect", bt_addr], capture_output=True, text=True, timeout=timeout)
                if res.returncode == 0:
                    return True
        except Exception:
            pass
    return False


def check_ssh_execution(
    host_alias_or_ip: str,
    timeout: float = 2.0,
    user: Optional[str] = None,
    port: int = 22
) -> Tuple[bool, float]:
    """
    Executes a fast remote actuation check via SSH utilizing ControlMaster multiplexing.
    Returns (success: bool, latency_ms: float).
    """
    t0 = time.perf_counter()
    target = host_alias_or_ip
    cmd = [
        "ssh",
        "-o", "BatchMode=yes",
        "-o", f"ConnectTimeout={max(1, int(timeout))}",
        "-o", "StrictHostKeyChecking=no",
        "-o", "ControlMaster=auto",
        "-o", "ControlPath=~/.ssh/sockets/%r@%h:%p",
        "-o", "ControlPersist=10m",
    ]
    if port != 22:
        cmd.extend(["-p", str(port)])
    if user and "@" not in target:
        cmd.append(f"{user}@{target}")
    else:
        cmd.append(target)
    cmd.append("echo MESH_PING_OK")

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 1.0)
        latency = (time.perf_counter() - t0) * 1000.0
        success = (res.returncode == 0 and "MESH_PING_OK" in res.stdout)
        return (success, latency)
    except Exception:
        latency = (time.perf_counter() - t0) * 1000.0
        return (False, latency)


def probe_physical_tier(node_name: str, tier: int) -> bool:
    """
    Directly probes a specific physical or actuation tier for the given node.
    Tiers:
      1: RFCOMM (Layer 0 IP-less serial, BLE MAC, device nodes)
      2: BT PAN (Layer 1 IP tethering bnep0)
      3: Ethernet (Layer 2 RJ45 twisted pair / LAN)
      4: Thunderbolt (Layer 2 40Gbps DMA bridge)
      5: SSH (Remote actuation plane)
      6: Services (Application daemon ports)
    Returns True if the tier is active/reachable, False otherwise.
    """
    matrix = load_matrix()
    canonical_name = resolve_alias(node_name, matrix)
    if not canonical_name or canonical_name not in matrix:
        return False
    node_data = matrix[canonical_name]
    if node_data.get("status") == "RETIRED":
        return False

    if tier == 1:
        # Tier 1: RFCOMM / BLE SPP
        t1 = node_data.get("tier1_rfcomm") or {}
        rf_mac = t1.get("rf_mac") or node_data.get("rf_mac") or node_data.get("mac")
        if rf_mac and check_bluetooth_presence(rf_mac, timeout=1.0):
            return True
        serial_dev = t1.get("serial_dev")
        if serial_dev and os.path.exists(serial_dev):
            return True
        rf_proxy = t1.get("rf_plugin_proxy") or node_data.get("rf_plugin_proxy")
        if rf_proxy:
            if ":" in rf_proxy:
                phost, pport = rf_proxy.split(":")
                if ping_port(phost, int(pport), timeout=0.1):
                    return True
            else:
                if ping_port(rf_proxy, 19000, timeout=0.1):
                    return True
        return False

    elif tier == 2:
        # Tier 2: BT PAN
        t2 = node_data.get("tier2_bt_pan") or {}
        pan_ip = t2.get("pan_ip") or t2.get("pan_tether") or node_data.get("pan") or node_data.get("pan_tether")
        if pan_ip:
            target_port = node_data.get("ssh_port", 22)
            if ping_port(pan_ip, target_port, timeout=0.2) or ping_icmp(pan_ip, timeout=0.2):
                return True
        return False

    elif tier == 3:
        # Tier 3: Ethernet / LAN
        t3 = node_data.get("tier3_ethernet") or {}
        candidates = []
        for k in ("ip", "lan_ip", "ethernet", "wired_wol", "lan_10gbe", "wifi", "alt_wifi"):
            val = t3.get(k) or node_data.get(k)
            if val and val not in candidates:
                candidates.append(val)
        if canonical_name == "L1_Mac_Host":
            candidates.append("127.0.0.1")
        target_port = node_data.get("ssh_port", 22)
        for cand in candidates:
            if ping_port(cand, target_port, timeout=0.2) or ping_icmp(cand, timeout=0.2):
                return True
        return False

    elif tier == 4:
        # Tier 4: Thunderbolt DMA Bridge
        t4 = node_data.get("tier4_thunderbolt") or {}
        candidates = []
        for k in ("tb4_ip", "tb4_ipv6", "tb3_ipv6", "tb4_bridge", "tb3_bridge", "ip", "link_local"):
            val = t4.get(k) or node_data.get(k)
            if val and val not in candidates:
                candidates.append(val)
        target_port = node_data.get("ssh_port", 22)
        for cand in candidates:
            if ping_port(cand, target_port, timeout=0.05):
                return True
        return False

    elif tier == 5:
        # Tier 5: SSH Actuation Plane
        DEFAULT_SSH_USERS = {
            "L1": "aaron",
            "L1_Mac_Host": "aaron",
            "L1b": "aaronmaher",
            "L2": "aaronmaher",
            "L2_MacBook_Pro": "aaronmaher",
            "L3": "linux",
            "L3_Linux_Hub": "linux",
            "L4": "aaron",
            "L4_Linux_Tablet": "aaron",
            "L5": "aaronmaher",
            "L5_MacBook_Air": "aaronmaher",
            "L6": "u0_a363",
            "L6_Pixel_10_Edge": "u0_a363",
            "L7": "u0_a358",
            "L7_Samsung_S20": "u0_a358",
            "L8": "linuxmini",
            "L8_Linux_Mini": "linuxmini",
            "GW": "root",
            "GW_Router": "root",
        }
        t5 = node_data.get("tier5_ssh") or {}
        user = t5.get("user") or node_data.get("user") or node_data.get("ssh_user") or DEFAULT_SSH_USERS.get(canonical_name)
        port = t5.get("port", node_data.get("ssh_port", 22))
        candidates = []
        for k in ("host", "tb4_ip", "tb_ip", "lan_ip", "tailscale_ip", "tailscale", "ip"):
            val = t5.get(k) or node_data.get(k)
            if val and val not in candidates:
                candidates.append(val)
        for k in ("lan", "wifi", "ethernet"):
            val = node_data.get(k)
            if val and val not in candidates:
                candidates.append(val)
        if not candidates:
            return False
        for cand in candidates:
            success, _ = check_ssh_execution(cand, timeout=2.0, user=user, port=port)
            if success:
                return True
        return False

    elif tier == 6:
        # Tier 6: Services Plane
        t6 = node_data.get("tier6_services") or {}
        ports = t6.get("ports", [])
        if not ports:
            return False
        svc_ip = "127.0.0.1" if canonical_name == "L1_Mac_Host" else (
            node_data.get("tailscale") or node_data.get("wifi") or node_data.get("ethernet") or node_data.get("lan")
        )
        if not svc_ip:
            return False
        for p in ports:
            if ping_port(svc_ip, p, timeout=0.2):
                return True
        return False

    return False


def resolve_node(
    node_name: str,
    fast_path: bool = True,
    timeout: float = 0.5,
    port: Optional[int] = None,
    strict_recovery: bool = False,
    **kwargs
) -> Dict[str, Any]:
    """
    Resolves node reachability across the canonical transport hierarchy.
    Adheres to PROJECT.md Interface Contract:
      Returns dict: {
        "node": str,
        "status": "CONNECTED" | "OFFLINE",
        "stage": int,
        "transport": str,
        "endpoint": str,
        "rtt_ms": float,
        "carrier": bool
      }

    When fast_path=True and strict_recovery=False:
      Probes active hardware carriers (<1ms kernel check) and micro-probes
      responsive physical cable endpoints (50ms timeout) to bypass Bluetooth HOL blocking.

    When fast_path=False or strict_recovery=True:
      Strictly sequences attempts in canonical recovery order:
        Tier 1: Layer 0 Bluetooth RFCOMM
        Tier 2: Layer 1 Bluetooth PAN
        Tier 3: Layer 2 Ethernet
        Tier 4: Layer 2 Thunderbolt
        (and Tier 5 SSH / Tier 6 Services if requested)
    """
    # Backward compatibility: if port was passed as second positional argument
    if type(fast_path) is int:
        port = fast_path
        fast_path = True

    matrix = load_matrix()
    canonical_name = resolve_alias(node_name, matrix)
    if not canonical_name or canonical_name not in matrix:
        return {
            "node": node_name,
            "status": "OFFLINE",
            "stage": 0,
            "transport": "none",
            "endpoint": "",
            "rtt_ms": 0.0,
            "carrier": False,
        }

    node_data = matrix[canonical_name]
    if node_data.get("status") == "RETIRED":
        return {
            "node": canonical_name,
            "status": "OFFLINE",
            "stage": 0,
            "transport": "retired",
            "endpoint": "",
            "rtt_ms": 0.0,
            "carrier": False,
        }

    target_port = port or node_data.get("ssh_port", 22)

    # -------------------------------------------------------------------------
    # 1. Fast-Path Carrier Probing (Bypasses Bluetooth HOL Blocking)
    # -------------------------------------------------------------------------
    if fast_path and not strict_recovery:
        # A. Localhost Fast-Path
        if canonical_name == "L1_Mac_Host":
            ok, rtt = ping_port_rtt("127.0.0.1", target_port, timeout=min(0.05, timeout))
            if ok:
                return {
                    "node": canonical_name,
                    "status": "CONNECTED",
                    "stage": 3,
                    "transport": "localhost",
                    "endpoint": f"127.0.0.1:{target_port}",
                    "rtt_ms": round(rtt, 3),
                    "carrier": True,
                }

        # B. Thunderbolt Carrier Fast-Path (<1ms kernel carrier check + 50ms micro-probe)
        tb_carrier = check_interface_carrier("bridge0")
        if tb_carrier:
            t4 = node_data.get("tier4_thunderbolt") or {}
            candidates = []
            for k in ("tb4_ipv6", "tb3_ipv6", "tb4_bridge", "tb3_bridge", "ip", "link_local"):
                val = t4.get(k) or node_data.get(k)
                if val and val not in candidates:
                    candidates.append(val)
            for cand in candidates:
                ok, rtt = ping_port_rtt(cand, target_port, timeout=min(0.05, timeout))
                if ok:
                    return {
                        "node": canonical_name,
                        "status": "CONNECTED",
                        "stage": 4,
                        "transport": "thunderbolt",
                        "endpoint": f"{cand}:{target_port}",
                        "rtt_ms": round(rtt, 3),
                        "carrier": True,
                    }

        # C. Ethernet Carrier Fast-Path (<1ms kernel carrier check + 50ms micro-probe)
        eth_carrier = check_interface_carrier("en0")
        if eth_carrier:
            t3 = node_data.get("tier3_ethernet") or {}
            candidates = []
            for k in ("ip", "lan_ip", "ethernet", "lan_10gbe", "wired_wol"):
                val = t3.get(k) or node_data.get(k)
                if val and val not in candidates:
                    candidates.append(val)
            for cand in candidates:
                ok, rtt = ping_port_rtt(cand, target_port, timeout=min(0.05, timeout))
                if ok:
                    return {
                        "node": canonical_name,
                        "status": "CONNECTED",
                        "stage": 3,
                        "transport": "ethernet",
                        "endpoint": f"{cand}:{target_port}",
                        "rtt_ms": round(rtt, 3),
                        "carrier": True,
                    }

        # D. Wi-Fi / Tailscale Overlay Fast-Path (100ms probe)
        overlay_candidates = []
        t3 = node_data.get("tier3_ethernet") or {}
        for k in ("wifi", "alt_wifi"):
            val = t3.get(k) or node_data.get(k)
            if val and val not in overlay_candidates:
                overlay_candidates.append((val, "wifi"))
        ts_val = node_data.get("tailscale") or (node_data.get("tier5_ssh") or {}).get("tailscale_ip")
        if ts_val and (ts_val, "tailscale") not in overlay_candidates:
            overlay_candidates.append((ts_val, "tailscale"))

        for cand, trans in overlay_candidates:
            ok, rtt = ping_port_rtt(cand, target_port, timeout=min(0.1, timeout))
            if ok:
                return {
                    "node": canonical_name,
                    "status": "CONNECTED",
                    "stage": 3,
                    "transport": trans,
                    "endpoint": f"{cand}:{target_port}",
                    "rtt_ms": round(rtt, 3),
                    "carrier": eth_carrier,
                }

    # -------------------------------------------------------------------------
    # 2. Strict Sequential Fallback (Canonical Recovery Hierarchy)
    # -------------------------------------------------------------------------
    # Tier 1: Layer 0 Bluetooth RFCOMM
    t1 = node_data.get("tier1_rfcomm") or {}
    rf_mac = t1.get("rf_mac") or node_data.get("rf_mac") or node_data.get("mac")
    if rf_mac:
        t_bt0 = time.perf_counter()
        if check_bluetooth_presence(rf_mac, timeout=1.0, try_connect=strict_recovery):
            rtt_bt = (time.perf_counter() - t_bt0) * 1000.0
            return {
                "node": canonical_name,
                "status": "CONNECTED",
                "stage": 1,
                "transport": "rfcomm",
                "endpoint": f"bluetooth://{rf_mac}",
                "rtt_ms": round(rtt_bt, 3),
                "carrier": False,
            }
    serial_dev = t1.get("serial_dev")
    if serial_dev:
        t_dev0 = time.perf_counter()
        if os.path.exists(serial_dev):
            rtt_dev = (time.perf_counter() - t_dev0) * 1000.0
            return {
                "node": canonical_name,
                "status": "CONNECTED",
                "stage": 1,
                "transport": "rfcomm",
                "endpoint": serial_dev,
                "rtt_ms": round(rtt_dev, 3),
                "carrier": False,
            }
    rf_proxy = t1.get("rf_plugin_proxy") or node_data.get("rf_plugin_proxy")
    if rf_proxy:
        if ":" in rf_proxy:
            phost, pport = rf_proxy.split(":")
            ok, rtt = ping_port_rtt(phost, int(pport), timeout=0.1)
            if ok:
                return {
                    "node": canonical_name,
                    "status": "CONNECTED",
                    "stage": 1,
                    "transport": "rfcomm",
                    "endpoint": rf_proxy,
                    "rtt_ms": round(rtt, 3),
                    "carrier": False,
                }

    # Tier 2: Layer 1 Bluetooth PAN
    t2 = node_data.get("tier2_bt_pan") or {}
    pan_ip = t2.get("pan_ip") or t2.get("pan_tether") or node_data.get("pan") or node_data.get("pan_tether")
    if pan_ip:
        ok, rtt = ping_port_rtt(pan_ip, target_port, timeout=timeout)
        if ok:
            return {
                "node": canonical_name,
                "status": "CONNECTED",
                "stage": 2,
                "transport": "bt_pan",
                "endpoint": f"{pan_ip}:{target_port}",
                "rtt_ms": round(rtt, 3),
                "carrier": False,
            }

    # Tier 3: Layer 2 Ethernet & LAN
    t3 = node_data.get("tier3_ethernet") or {}
    eth_carrier = check_interface_carrier("en0")
    eth_candidates = []
    for k in ("ip", "lan_ip", "ethernet", "lan_10gbe", "wired_wol", "wifi", "alt_wifi", "alt_ip", "usb_lan"):
        val = t3.get(k) or node_data.get(k)
        if val and val not in eth_candidates:
            eth_candidates.append(val)
    # Also check tier5_ssh host and alt IPs
    t5_probe = node_data.get("tier5_ssh") or {}
    for k in ("host", "lan_ip", "tailscale_ip"):
        val = t5_probe.get(k)
        if val and val not in eth_candidates:
            eth_candidates.append(val)
    if canonical_name == "L1_Mac_Host":
        eth_candidates.append("127.0.0.1")
    ts_val = node_data.get("tailscale") or (node_data.get("tier5_ssh") or {}).get("tailscale_ip")
    if ts_val and ts_val not in eth_candidates:
        eth_candidates.append(ts_val)

    icmp_fallback_cand = None
    icmp_fallback_rtt = 0.0

    for cand in eth_candidates:
        ok, rtt = ping_port_rtt(cand, target_port, timeout=timeout)
        if ok:
            return {
                "node": canonical_name,
                "status": "CONNECTED",
                "stage": 3,
                "transport": "ethernet",
                "endpoint": f"{cand}:{target_port}",
                "rtt_ms": round(rtt, 3),
                "carrier": eth_carrier,
            }
        elif not icmp_fallback_cand:
            ok_icmp, rtt_icmp = ping_icmp_rtt(cand, timeout=timeout)
            if ok_icmp:
                icmp_fallback_cand = cand
                icmp_fallback_rtt = rtt_icmp

    # Tier 4: Layer 2 Thunderbolt DMA Bridge
    t4 = node_data.get("tier4_thunderbolt") or {}
    tb_carrier = check_interface_carrier("bridge0")
    tb_candidates = []
    for k in ("tb4_ipv6", "tb3_ipv6", "tb4_bridge", "tb3_bridge", "ip", "link_local"):
        val = t4.get(k) or node_data.get(k)
        if val and val not in tb_candidates:
            tb_candidates.append(val)
    for cand in tb_candidates:
        ok, rtt = ping_port_rtt(cand, target_port, timeout=timeout)
        if ok:
            return {
                "node": canonical_name,
                "status": "CONNECTED",
                "stage": 4,
                "transport": "thunderbolt",
                "endpoint": f"{cand}:{target_port}",
                "rtt_ms": round(rtt, 3),
                "carrier": tb_carrier,
            }

    # Tier 5: Stage 5 SSH Actuation Plane
    t5 = node_data.get("tier5_ssh") or {}
    ssh_candidates = []
    for k in ("host", "lan_ip", "tailscale_ip", "tb_ip"):
        val = t5.get(k)
        if val and val not in ssh_candidates:
            ssh_candidates.append(val)
    ts_node = node_data.get("tailscale")
    if ts_node and ts_node not in ssh_candidates:
        ssh_candidates.append(ts_node)
    for k in ("lan", "wifi", "ethernet"):
        val = node_data.get(k)
        if val and val not in ssh_candidates:
            ssh_candidates.append(val)

    if ssh_candidates and (port is None or port == node_data.get("ssh_port", 22)):
        ssh_user = t5.get("user")
        ssh_port = t5.get("port", target_port)
        for cand in ssh_candidates:
            ok_ssh, rtt_ssh = check_ssh_execution(cand, timeout=timeout, user=ssh_user, port=ssh_port)
            if ok_ssh:
                return {
                    "node": canonical_name,
                    "status": "CONNECTED",
                    "stage": 5,
                    "transport": "ssh",
                    "endpoint": f"{cand}:{ssh_port}",
                    "rtt_ms": round(rtt_ssh, 3),
                    "carrier": eth_carrier,
                }

    # Tier 6: Stage 6 Application & Service Plane
    t6 = node_data.get("tier6_services") or {}
    for p in t6.get("ports", []):
        for h in (("127.0.0.1" if canonical_name == "L1_Mac_Host" else None), node_data.get("tailscale"), node_data.get("wifi"), node_data.get("ethernet")):
            if h:
                ok_svc, rtt_svc = ping_port_rtt(h, p, timeout=timeout)
                if ok_svc:
                    return {
                        "node": canonical_name,
                        "status": "CONNECTED",
                        "stage": 6,
                        "transport": "services",
                        "endpoint": f"{h}:{p}",
                        "rtt_ms": round(rtt_svc, 3),
                        "carrier": False,
                    }

    # Exhausted port candidates. If no explicit port was requested and host answered ICMP, report ICMP reachability honestly.
    if icmp_fallback_cand and not port:
        return {
            "node": canonical_name,
            "status": "CONNECTED",
            "stage": 3,
            "transport": "ethernet_icmp",
            "endpoint": f"{icmp_fallback_cand}:icmp",
            "rtt_ms": round(icmp_fallback_rtt, 3),
            "carrier": eth_carrier,
        }

    return {
        "node": canonical_name,
        "status": "OFFLINE",
        "stage": 0,
        "transport": "none",
        "endpoint": "",
        "rtt_ms": 0.0,
        "carrier": False,
    }


def main():
    parser = argparse.ArgumentParser(description="Canonical Multi-Transport Mesh Ping (Gen 31)")
    parser.add_argument("node", nargs="?", help="Node name or alias (e.g. L1_Mac_Host, L2_MacBook_Pro, router)")
    parser.add_argument("port", nargs="?", type=int, help="Optional target port (e.g. 22, 50052, 8022)")
    parser.add_argument("--fast-path", "--fast", action="store_true", default=True, help="Enable Fast-Path Carrier Probing (default)")
    parser.add_argument("--strict-recovery", "--canonical", action="store_true", help="Enforce strict sequential fallback (RFCOMM -> PAN -> Ethernet -> TB4)")
    parser.add_argument("--tier", type=int, choices=[1, 2, 3, 4, 5, 6], help="Directly probe a specific physical tier (1-6)")
    parser.add_argument("--all", action="store_true", help="Probe all canonical mesh nodes")
    parser.add_argument("--json", action="store_true", help="Output machine-parsable JSON")
    args = parser.parse_args()

    matrix = load_matrix()

    # Direct tier probe
    if args.tier and args.node:
        alive = probe_physical_tier(args.node, args.tier)
        tier_names = {1: "RFCOMM", 2: "BT_PAN", 3: "Ethernet", 4: "Thunderbolt", 5: "SSH", 6: "Services"}
        tname = tier_names.get(args.tier, str(args.tier))
        if args.json:
            print(json.dumps({"node": args.node, "tier": args.tier, "tier_name": tname, "alive": alive}))
        else:
            status_str = "ALIVE" if alive else "UNREACHABLE"
            print(f"[{status_str}] Node {args.node} Tier {args.tier} ({tname}): {status_str}")
        sys.exit(0 if alive else 1)

    # Probe all nodes
    if args.all:
        results = []
        nodes = [k for k in matrix.keys() if not k.startswith("_") and isinstance(matrix[k], dict) and matrix[k].get("status") != "RETIRED"]
        for n in nodes:
            res = resolve_node(n, fast_path=not args.strict_recovery, strict_recovery=args.strict_recovery, port=args.port)
            results.append(res)
            if not args.json:
                if res["status"] == "CONNECTED":
                    carrier_str = "CARRIER_UP" if res["carrier"] else "NO_CARRIER"
                    print(f"[SUCCESS] {res['node']:18s} Stage {res['stage']} ({res['transport']:11s}) -> {res['endpoint']:35s} [{res['rtt_ms']:.2f}ms, {carrier_str}]")
                else:
                    print(f"[OFFLINE] {res['node']:18s} Exhausted all fallback routes")
        if args.json:
            print(json.dumps(results, indent=2))
        any_offline = any(r["status"] == "OFFLINE" for r in results)
        sys.exit(0 if not any_offline else 0)  # Status report exits cleanly

    # Single node resolution
    if not args.node:
        parser.print_help()
        sys.exit(1)

    res = resolve_node(
        args.node,
        fast_path=not args.strict_recovery,
        strict_recovery=args.strict_recovery,
        port=args.port,
    )

    if args.json:
        print(json.dumps(res, indent=2))
    else:
        if res["status"] == "CONNECTED":
            carrier_str = "UP" if res["carrier"] else "DOWN"
            print(
                f"[SUCCESS] {res['node']} is ALIVE on {res['transport']} "
                f"({res['endpoint']}) [Stage {res['stage']}, RTT: {res['rtt_ms']:.2f}ms, Carrier: {carrier_str}]"
            )
        else:
            print(f"[OFFLINE] Exhausted all fallback routes for {res['node']}.")

    sys.exit(0 if res["status"] == "CONNECTED" else 1)


if __name__ == "__main__":
    main()
