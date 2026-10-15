"""
Darwin Network Interface Discovery & Virtual Multiplexer for Shark Wire.
Discovers and classifies physical, virtual, and tunnel network interfaces on macOS Darwin,
mapping each to its canonical Lauburu 7-layer mesh role.
"""

import socket
import logging
from typing import List, Dict, Any

try:
    import psutil
except ImportError:
    psutil = None

logger = logging.getLogger("shark_wire.interfaces")

# Canonical Lauburu Mesh Interface Roles
MESH_INTERFACE_ROLES: Dict[str, Dict[str, str]] = {
    "en0": {
        "type": "10GbE Ethernet",
        "mesh_role": "10GbE Primary Host Link (Mac_Node L1 -> Gateway eth2)",
    },
    "bridge0": {
        "type": "Thunderbolt 4 Bridge",
        "mesh_role": "Thunderbolt 4 DMA Bridge (L1 <-> L2)",
    },
    "en1": {
        "type": "Wi-Fi 7 (802.11be)",
        "mesh_role": "Wi-Fi 7 / 802.11be MLO Clean Room Radio",
    },
    "utun3": {
        "type": "Tunnel (WireGuard)",
        "mesh_role": "WireGuard Mesh Overlay Tunnel (UDP 41641)",
    },
    "utun4": {
        "type": "Tunnel (Tailscale)",
        "mesh_role": "Tailscale Mesh Overlay (100.119.199.76)",
    },
    "lo0": {
        "type": "Loopback",
        "mesh_role": "Darwin Localhost Loopback (Local AI RPC Ports 8081-8084)",
    },
    "any": {
        "type": "Virtual Multiplexer",
        "mesh_role": "Virtual Aggregated Capture Multiplexer (All Interfaces)",
    },
}


def _determine_interface_type(name: str) -> str:
    """Infer interface type from interface naming conventions on Darwin."""
    if name in MESH_INTERFACE_ROLES:
        return MESH_INTERFACE_ROLES[name]["type"]
    if name.startswith("bridge"):
        return "Thunderbolt Bridge"
    if name.startswith("utun"):
        return "Tunnel (VPN/WireGuard)"
    if name.startswith("lo"):
        return "Loopback"
    if name.startswith("en"):
        return "Ethernet / Wi-Fi"
    if name.startswith("ap") or name.startswith("awdl") or name.startswith("llw"):
        return "Apple Wireless Direct"
    return "Network Interface"


def _determine_mesh_role(name: str, ips: List[str]) -> str:
    """Infer Lauburu mesh role based on name and IP bindings."""
    if name in MESH_INTERFACE_ROLES:
        return MESH_INTERFACE_ROLES[name]["mesh_role"]
    for ip in ips:
        if ip.startswith("100."):
            return f"Tailscale / WireGuard Mesh Overlay ({ip})"
        if ip.startswith("192.168.8."):
            return f"Lauburu Primary LAN Subnet ({ip})"
        if ip.startswith("192.168.2.") or ip.startswith("169.254."):
            return f"Thunderbolt P2P Bridge Subnet ({ip})"
    return f"Darwin Network Adapter ({name})"


def discover_darwin_interfaces() -> List[Dict[str, Any]]:
    """
    Discover active and available Darwin interfaces with MAC addresses,
    IP bindings, MTU, operational status, and assigned Lauburu mesh roles.
    Includes the virtual 'any' multiplexer interface.
    """
    interfaces: List[Dict[str, Any]] = []
    seen_names = set()

    if psutil is not None:
        try:
            addrs = psutil.net_if_addrs()
            stats = psutil.net_if_stats()

            # Priority order for interface listing
            preferred_order = ["en0", "bridge0", "en1", "utun4", "utun3", "lo0"]
            all_iface_names = sorted(
                addrs.keys(),
                key=lambda n: (preferred_order.index(n) if n in preferred_order else 100, n)
            )

            for name in all_iface_names:
                mac = ""
                ips = []
                for addr in addrs[name]:
                    # AF_LINK is MAC on BSD/Darwin
                    if hasattr(psutil, "AF_LINK") and addr.family == psutil.AF_LINK:
                        mac = addr.address or ""
                    elif addr.family in (socket.AF_INET, socket.AF_INET6):
                        # Filter out loopback v6 scopes if overly verbose, but keep clean IP
                        clean_ip = addr.address.split("%")[0] if addr.address else ""
                        if clean_ip and clean_ip not in ips:
                            ips.append(clean_ip)

                stat = stats.get(name)
                is_up = stat.isup if stat else True
                mtu = stat.mtu if stat else 1500
                speed = stat.speed if stat else 0

                status = "active" if is_up else "inactive"
                iface_type = _determine_interface_type(name)
                mesh_role = _determine_mesh_role(name, ips)

                interfaces.append({
                    "id": name,
                    "name": name,
                    "type": iface_type,
                    "status": status,
                    "mac": mac,
                    "ips": ips,
                    "mtu": mtu,
                    "speed_mbps": speed,
                    "mesh_role": mesh_role,
                })
                seen_names.add(name)
        except Exception as e:
            logger.warning(f"Error discovering interfaces via psutil: {e}")

    # Check critical Darwin interfaces if omitted by psutil
    fallback_defaults = [
        ("en0", "", [], 1500, "10GbE Ethernet", MESH_INTERFACE_ROLES["en0"]["mesh_role"]),
        ("bridge0", "", [], 1500, "Thunderbolt 4 Bridge", MESH_INTERFACE_ROLES["bridge0"]["mesh_role"]),
        ("utun4", "", [], 1280, "Tunnel (Tailscale)", MESH_INTERFACE_ROLES["utun4"]["mesh_role"]),
        ("utun3", "", [], 1000, "Tunnel (WireGuard)", MESH_INTERFACE_ROLES["utun3"]["mesh_role"]),
    ]
    for name, mac, ips, mtu, iftype, role in fallback_defaults:
        if name not in seen_names:
            interfaces.append({
                "id": name,
                "name": name,
                "type": iftype,
                "status": "inactive",
                "mac": mac,
                "ips": ips,
                "mtu": mtu,
                "speed_mbps": None,
                "mesh_role": role,
            })
            seen_names.add(name)

    # Always append the virtual 'any' multiplexer
    if "any" not in seen_names:
        interfaces.append({
            "id": "any",
            "name": "any",
            "type": "Virtual Multiplexer",
            "status": "active",
            "mac": "",
            "ips": [],
            "mtu": 65535,
            "speed_mbps": 0,
            "mesh_role": MESH_INTERFACE_ROLES["any"]["mesh_role"],
        })

    return interfaces
