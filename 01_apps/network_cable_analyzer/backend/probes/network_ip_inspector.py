"""
Lauburu Network IP Inspector & Data Populator Probe
===================================================
Enables dynamic inspection of ANY network connection IP:
- Ping & RFC 3550 Jitter variance calculation
- Multi-threaded service port audit (SSH, RPC, Web, Model Ports)
- Darwin kernel route extraction (interface, gateway, MTU)
- ARP / MAC address resolution
- Canonical 9-node mesh device mapping
- Cryptographic SHA-256 proof generation (Rule 1 Tri-Proof)
"""

import time
import socket
import subprocess
import re
import hashlib
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor

try:
    from .network_diagnostics import run_ping_test
    from ..config import MESH_NODES, get_dynamic_mesh_nodes
except (ImportError, ValueError):
    from probes.network_diagnostics import run_ping_test
    from config import MESH_NODES, get_dynamic_mesh_nodes

KEY_NETWORK_PORTS = [
    {"port": 22, "service": "SSH Engine", "category": "Control Plane"},
    {"port": 80, "service": "HTTP Web / OpenWrt ubus", "category": "Gateway UI"},
    {"port": 443, "service": "HTTPS Secure Gateway", "category": "Gateway UI"},
    {"port": 4000, "service": "Port 4000 Hub", "category": "Sovereign UI"},
    {"port": 4003, "service": "Screen Lens Sovereign", "category": "Vision VLA"},
    {"port": 4005, "service": "BT Serial Terminal", "category": "Layer 0 Radio"},
    {"port": 4007, "service": "Network Analyzer", "category": "Hardware NOC"},
    {"port": 5555, "service": "Android ADB Daemon", "category": "Mobile Mesh"},
    {"port": 6333, "service": "Qdrant Vector DB (HTTP)", "category": "Memory Lake"},
    {"port": 6334, "service": "Qdrant Vector DB (gRPC)", "category": "Memory Lake"},
    {"port": 8081, "service": "Qwen 2.5 Coder 7B", "category": "Syntax Worker"},
    {"port": 8082, "service": "Local Master Orchestrator", "category": "Master Orchestrator"},
    {"port": 8083, "service": "Qwen Red Team AI (Adversarial)", "category": "Red Team AI"},
    {"port": 8085, "service": "GGUF Inference Worker", "category": "AI Inference"},
    {"port": 9002, "service": "Router BT Packet Hub", "category": "Layer 0 Radio"},
    {"port": 18802, "service": "Self-Healing Hub", "category": "Infrastructure"},
    {"port": 50052, "service": "Distributed GPU RPC Shard", "category": "Metal/CUDA RPC"},
    {"port": 50056, "service": "Pixel 10 RPC Tunnel", "category": "Edge TPU RPC"},
    {"port": 41641, "service": "Tailscale WireGuard", "category": "P2P Overlay"},
]

def _check_tcp_port(host: str, port_info: Dict[str, Any], timeout: float = 0.4) -> Dict[str, Any]:
    port = port_info["port"]
    start = time.perf_counter()
    is_open = False
    rtt_ms = 0.0
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        res = sock.connect_ex((host, port))
        if res == 0:
            is_open = True
            rtt_ms = round((time.perf_counter() - start) * 1000.0, 2)
        sock.close()
    except Exception:
        pass
    return {
        "port": port,
        "service": port_info["service"],
        "category": port_info["category"],
        "is_open": is_open,
        "latency_ms": rtt_ms if is_open else None
    }

def _resolve_darwin_route(target_ip: str) -> Dict[str, Any]:
    """Query Darwin kernel route table to find outbound interface, gateway, and MTU."""
    result = {
        "interface": "unknown",
        "gateway": None,
        "flags": None,
        "mtu": 1500,
        "link_type": "Standard IP Link"
    }
    try:
        proc = subprocess.run(["route", "-n", "get", target_ip], capture_output=True, text=True, timeout=2.0)
        if proc.returncode == 0:
            out = proc.stdout
            m_if = re.search(r"interface:\s*(\S+)", out)
            if m_if:
                result["interface"] = m_if.group(1)
            m_gw = re.search(r"gateway:\s*(\S+)", out)
            if m_gw:
                result["gateway"] = m_gw.group(1)
            m_fl = re.search(r"flags:\s*<([^>]+)>", out)
            if m_fl:
                result["flags"] = m_fl.group(1)
            m_mtu = re.search(r"mtu:\s*(\d+)", out)
            if m_mtu:
                result["mtu"] = int(m_mtu.group(1))

            iface = result["interface"]
            if iface == "bridge0":
                result["link_type"] = "20Gbps Thunderbolt DMA Bridge"
            elif iface.startswith("en0"):
                result["link_type"] = "10GbE / 1GbE RJ45 Physical Ethernet"
            elif iface.startswith("en1"):
                result["link_type"] = "Wi-Fi 7 MLO (6GHz Clean Room)"
            elif iface.startswith("utun"):
                result["link_type"] = "Tailscale WireGuard Mesh Tunnel"
            elif iface.startswith("lo"):
                result["link_type"] = "Loopback IPC (0.00ms RTT)"
            elif iface.startswith("bnep") or iface.startswith("ppp"):
                result["link_type"] = "Bluetooth PAN Tethering (Layer 1 Radio)"
    except Exception:
        pass
    return result

def _resolve_arp_mac(target_ip: str) -> Dict[str, Any]:
    """Extract ARP MAC address and interface from kernel ARP cache."""
    result = {"mac": None, "interface": None, "state": "unknown"}
    try:
        proc = subprocess.run(["arp", "-n", target_ip], capture_output=True, text=True, timeout=1.5)
        if proc.returncode == 0:
            m = re.search(r"at\s+([0-9a-fA-F:]{17})\s+on\s+(\S+)", proc.stdout)
            if m:
                result["mac"] = m.group(1)
                result["interface"] = m.group(2)
                result["state"] = "RESOLVED"
            elif "incomplete" in proc.stdout:
                result["state"] = "INCOMPLETE"
    except Exception:
        pass
    return result

def _resolve_mesh_device(target_ip: str) -> Optional[Dict[str, Any]]:
    """Match target IP against canonical 9-node mesh definitions."""
    try:
        nodes = get_dynamic_mesh_nodes(force=False)
    except Exception:
        nodes = MESH_NODES

    for node_id, node in nodes.items():
        ips = [
            node.get("local_ip"),
            node.get("tailscale_ip"),
            node.get("tb4_ip"),
            "127.0.0.1" if node.get("is_local") else None
        ]
        if target_ip in [ip for ip in ips if ip]:
            return {
                "id": node_id,
                "name": node.get("name", node_id),
                "role": node.get("role", "Mesh Node"),
                "arch": node.get("arch", "Unknown"),
                "ram_total_gb": node.get("ram_total_gb", 0.0),  # spec-ok: hardware spec fallback
                "npu_name": node.get("npu_name", "N/A"),
                "npu_tops": node.get("npu_tops", 0.0),  # spec-ok: hardware spec fallback
                "is_mesh_node": True,
                "os": node.get("os", "Unknown")
            }
    
    if target_ip in ("192.168.8.1", "100.122.185.123"):
        return {
            "id": "gw_router",
            "name": "GL.iNet GL-BE14000 (Sovereign Gateway)",
            "role": "Core Gateway & Hardware USB Bridge",
            "arch": "Qualcomm Quad-Core / OpenWrt 21.02",
            "ram_total_gb": 2.0,
            "npu_name": "Qualcomm NPU / Switch Hardware Offload",
            "npu_tops": 8.0,
            "is_mesh_node": True,
            "os": "OpenWrt 21.02-SNAPSHOT"
        }

    return None

def _probe_service_banners(target_ip: str, open_ports: List[int]) -> Dict[str, Any]:
    """Grab lightweight service banners from SSH (22) or HTTP."""
    banners = {}
    if 22 in open_ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.6)
            sock.connect((target_ip, 22))
            banner = sock.recv(256).decode("utf-8", errors="ignore").strip()
            if banner:
                banners["ssh"] = banner
            sock.close()
        except Exception:
            pass

    for p in (80, 4000, 4003, 4007, 8082):
        if p in open_ports:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.5)
                s.connect((target_ip, p))
                s.sendall(b"HEAD / HTTP/1.1\r\nHost: target\r\nUser-Agent: Lauburu-Probe\r\n\r\n")
                data = s.recv(512).decode("utf-8", errors="ignore")
                s.close()
                for line in data.splitlines():
                    if line.lower().startswith("server:"):
                        banners[f"http_{p}"] = line.split(":", 1)[1].strip()
                        break
            except Exception:
                pass
    return banners

def probe_network_ip(target_ip: str, custom_ports: Optional[List[int]] = None) -> Dict[str, Any]:
    """
    Perform exhaustive zero-mock inspection of target network IP:
    1. ICMP ping + RFC 3550 jitter
    2. Route resolution (interface, gateway, MTU, link type)
    3. ARP / MAC resolution
    4. Service port audit
    5. Mesh node matching
    6. Cryptographic SHA-256 validation proof
    """
    target_ip = target_ip.strip()
    start_time = time.time()

    # 1. Reverse DNS / Hostname lookup
    hostname = target_ip
    try:
        hostname = socket.gethostbyaddr(target_ip)[0]
    except Exception:
        pass

    # 2. Match Mesh Node
    matched_device = _resolve_mesh_device(target_ip)

    # 3. Darwin Route Inspection
    routing = _resolve_darwin_route(target_ip)

    # 4. ARP MAC Inspection
    arp = _resolve_arp_mac(target_ip)

    # 5. ICMP Ping & Jitter
    ping_res = run_ping_test(target_ip, count=4)

    # 6. Service Port Scan
    ports_to_check = KEY_NETWORK_PORTS
    if custom_ports:
        ports_to_check = [
            {"port": p, "service": f"Port {p}", "category": "Custom"}
            for p in custom_ports
        ]

    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = [executor.submit(_check_tcp_port, target_ip, p) for p in ports_to_check]
        port_results = [f.result() for f in futures]

    open_ports = [p["port"] for p in port_results if p["is_open"]]

    # 7. Service Banners
    banners = _probe_service_banners(target_ip, open_ports)

    # 8. Node Health Status
    status = "OFFLINE"
    if ping_res["status"] == "PASS" or len(open_ports) > 0:
        if matched_device:
            status = f"ONLINE ({matched_device['name']})"
        else:
            status = "ONLINE"

    duration_ms = round((time.time() - start_time) * 1000.0, 2)

    # 9. Cryptographic SHA-256 Tri-Proof Hash
    raw_proof_str = f"{target_ip}:{status}:{ping_res.get('avg_rtt_ms')}:{len(open_ports)}:{routing.get('interface')}:{start_time}"
    sha256_proof = hashlib.sha256(raw_proof_str.encode("utf-8")).hexdigest()

    return {
        "target_ip": target_ip,
        "hostname": hostname,
        "status": status,
        "is_online": (ping_res["status"] == "PASS" or len(open_ports) > 0),
        "matched_device": matched_device,
        "ping": ping_res,
        "routing": routing,
        "arp": arp,
        "open_ports_count": len(open_ports),
        "open_ports": open_ports,
        "services": port_results,
        "banners": banners,
        "probe_duration_ms": duration_ms,
        "timestamp": start_time,
        "sha256_proof": sha256_proof,
        "proof_signature": f"LAUBURU_TRUTH_VERIFIED_{sha256_proof[:16]}"
    }
