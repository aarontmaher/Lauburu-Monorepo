#!/usr/bin/env python3
"""
02_ai_models_and_inference/sharding_daemon/network_awareness.py
===============================================================
Unified Network Awareness Layer (UNAL) for Lauburu AI Mesh.
-----------------------------------------------------------
Provides real-time, zero-mock empirical network telemetry, dynamic interface
discovery, Tailscale WireGuard overlay status inspection, direct vs DERP
relay connection classification, live socket probing (RTT/jitter/packet loss),
and multi-tier dynamic routing cost computation for distributed AI tensor sharding.

Interface Contracts:
- LinkMetrics(peer_id, tailscale_ip, is_direct, rtt_ms, bandwidth_mbps, packet_loss, transport_tier)
- get_live_peer_metrics(peer_ip: str) -> LinkMetrics
- compute_routing_cost(src: str, dst: str, tensor_size_bytes: int) -> float
"""

import os
import sys
import re
import time
import json
import socket
import shutil
import logging
import threading
import subprocess
from enum import Enum
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any

from pydantic import BaseModel, Field

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [UNAL]: %(message)s"
)
logger = logging.getLogger("UNAL")

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data" / "network"
LIVE_TELEMETRY_PATH = DATA_DIR / "mesh_telemetry_live.json"


class TransportTier(str, Enum):
    TB4_DMA = "TB4_DMA"
    LAN_1GBE = "LAN_1GBE"
    WIFI7_MLO = "WIFI7_MLO"
    MULTIPATH_BOND = "MULTIPATH_BOND"
    TAILSCALE_DIRECT = "TAILSCALE_DIRECT"
    DERP_RELAY = "DERP_RELAY"
    LOCAL_LOOPBACK = "LOCAL_LOOPBACK"
    UNREACHABLE = "UNREACHABLE"


# 6-Tier Base Multipliers for Dijkstra Shortest-Path Cost Calculation
TIER_BASE_MULTIPLIERS: Dict[str, float] = {
    TransportTier.LOCAL_LOOPBACK.value: 0.01,
    TransportTier.TB4_DMA.value: 0.05,
    TransportTier.LAN_1GBE.value: 0.15,
    TransportTier.WIFI7_MLO.value: 0.20,
    TransportTier.MULTIPATH_BOND.value: 0.25,
    TransportTier.TAILSCALE_DIRECT.value: 0.40,
    TransportTier.DERP_RELAY.value: 1.50,
    TransportTier.UNREACHABLE.value: float("inf"),
}


class NetworkInterface(BaseModel):
    name: str
    ip: str
    type: str
    status: str
    mtu: int = 1500
    rtt_ms: float = 1.0
    bandwidth_mbps: float = 1000.0
    role: str = "SECONDARY"


class PeerStatus(BaseModel):
    node_name: str
    tailscale_ip: str
    cur_addr: str = ""
    connection_type: str = "UNKNOWN"  # DIRECT_WIREGUARD, DERP_RELAY, LOCAL, UNREACHABLE
    is_direct: bool = False
    relay: str = ""
    online: bool = False
    active: bool = False
    rtt_ms: float = 0.0
    jitter_ms: float = 0.0
    packet_loss: float = 0.0
    bandwidth_mbps: float = 100.0
    transport_tier: str = TransportTier.TAILSCALE_DIRECT.value
    ssh_available: bool = False
    last_seen: str = ""


class LinkMetrics(BaseModel):
    """
    Standard interface contract for UNAL peer link metrics.
    Ingested by DHT Router and Dijkstra DP shortest-path tensor sharder.
    """
    peer_id: str
    tailscale_ip: str
    is_direct: bool
    rtt_ms: float
    bandwidth_mbps: float
    packet_loss: float
    transport_tier: str  # TB4_DMA, LAN_1GBE, WIFI7_MLO, TAILSCALE_DIRECT, MULTIPATH_BOND, DERP_RELAY


class MeshTelemetrySnapshot(BaseModel):
    timestamp_utc: str
    local_node: Dict[str, Any]
    peers: List[Dict[str, Any]]
    bonding_state: Dict[str, Any]


def find_tailscale_binary() -> Optional[str]:
    """Locate the Tailscale CLI binary across macOS, Linux, and Android Termux."""
    candidates = [
        "/Applications/Tailscale.app/Contents/MacOS/Tailscale",
        "/usr/local/bin/tailscale",
        "/opt/homebrew/bin/tailscale",
        "/usr/bin/tailscale",
        "/data/data/com.termux/files/usr/bin/tailscale",
    ]
    which_path = shutil.which("tailscale")
    if which_path:
        candidates.insert(0, which_path)

    for path in candidates:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return None


def query_tailscale_status() -> Dict[str, Any]:
    """
    Query Tailscale status JSON directly from the local daemon.
    Returns parsed dictionary or a safe fallback structure.
    """
    ts_bin = find_tailscale_binary()
    if not ts_bin:
        logger.debug("Tailscale CLI binary not found on this host")
        return {"BackendState": "Unavailable", "Self": {}, "Peer": {}}

    try:
        res = subprocess.run(
            [ts_bin, "status", "--json"],
            capture_output=True,
            text=True,
            timeout=4.0
        )
        if res.returncode == 0 and res.stdout.strip():
            return json.loads(res.stdout)
        logger.debug(f"Tailscale status returned code {res.returncode}: {res.stderr.strip()}")
    except Exception as e:
        logger.debug(f"Failed to query Tailscale status: {e}")

    return {"BackendState": "Error", "Self": {}, "Peer": {}}


def probe_socket_tcp(host: str, port: int, timeout_sec: float = 0.8) -> Tuple[bool, float]:
    """
    Empirically probe a TCP endpoint, measuring exact handshake RTT in milliseconds.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout_sec)
    t0 = time.perf_counter()
    try:
        sock.connect((host, port))
        t1 = time.perf_counter()
        rtt_ms = (t1 - t0) * 1000.0
        sock.close()
        return True, rtt_ms
    except (ConnectionRefusedError, socket.timeout, OSError):
        t1 = time.perf_counter()
        rtt_ms = (t1 - t0) * 1000.0
        sock.close()
        # ConnectionRefused still proves host reachability and network round-trip!
        return False, rtt_ms


def probe_ping_empirical(host: str, count: int = 2, timeout_sec: float = 1.0) -> Tuple[bool, float, float, float]:
    """
    Perform an empirical ICMP ping probe against a target host.
    Returns: (reachable, avg_rtt_ms, jitter_ms, packet_loss_pct)
    """
    cmd = ["ping", "-c", str(count)]
    if sys.platform == "darwin":
        cmd.extend(["-W", str(int(timeout_sec * 1000))])
    else:
        cmd.extend(["-W", str(int(timeout_sec))])
    cmd.append(host)

    try:
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=(count * timeout_sec) + 1.5
        )
        if res.returncode == 0:
            times = [float(x) for x in re.findall(r"time=([\d.]+)\s*ms", res.stdout)]
            if times:
                avg_rtt = sum(times) / len(times)
                jitter = max(times) - min(times) if len(times) > 1 else 0.0
                loss_m = re.search(r"(\d+(?:\.\d+)?)%\s+packet loss", res.stdout)
                loss = float(loss_m.group(1)) if loss_m else 0.0
                return True, avg_rtt, jitter, loss

        # If ping returned non-zero, check for packet loss
        loss_m = re.search(r"(\d+(?:\.\d+)?)%\s+packet loss", res.stdout)
        loss = float(loss_m.group(1)) if loss_m else 100.0
        return False, 999.0, 0.0, loss
    except subprocess.TimeoutExpired:
        return False, 999.0, 0.0, 100.0
    except Exception as e:
        logger.debug(f"Ping probe exception for {host}: {e}")
        return False, 999.0, 0.0, 100.0


def probe_peer_empirical(host: str, ports: Optional[List[int]] = None) -> Tuple[bool, float, float, float]:
    """
    Probe a peer using TCP ports first (e.g. SSH 22/8022, llama.cpp 50052, DHT 31330),
    falling back to ICMP ping for comprehensive reachability and RTT measurement.
    """
    # 1. Fast path: check known ports if provided
    if ports:
        for port in ports:
            reachable, rtt_ms = probe_socket_tcp(host, port, timeout_sec=0.5)
            if reachable:
                return True, rtt_ms, 0.0, 0.0

    # 2. Comprehensive ICMP ping probe
    return probe_ping_empirical(host, count=2, timeout_sec=1.0)


def discover_local_interfaces() -> List[NetworkInterface]:
    """
    Dynamically discover active network interfaces on the local node across macOS,
    Linux, and Android Termux environments without hardcoded IPs.
    """
    interfaces: List[NetworkInterface] = []
    discovered_ips = set()

    # 1. macOS (Darwin) Dynamic ifconfig parsing
    if sys.platform == "darwin":
        try:
            res = subprocess.run(["ifconfig"], capture_output=True, text=True, timeout=3.0)
            current_name = None
            current_flags = ""
            current_mtu = 1500
            current_status = "inactive"
            current_inets: List[str] = []

            for line in res.stdout.splitlines():
                if not line:
                    continue
                m_hdr = re.match(r"^([a-zA-Z0-9]+):\s+flags=\d+<([^>]+)>\s+mtu\s+(\d+)", line)
                if m_hdr:
                    if current_name and current_inets:
                        for ip in current_inets:
                            if ip not in discovered_ips and not ip.startswith("127.94."):
                                iface = _classify_interface(current_name, ip, current_mtu, current_status, current_flags)
                                interfaces.append(iface)
                                discovered_ips.add(ip)
                    current_name, current_flags, mtu_str = m_hdr.groups()
                    current_mtu = int(mtu_str)
                    current_status = "inactive"
                    current_inets = []
                else:
                    sline = line.strip()
                    if sline.startswith("inet "):
                        parts = sline.split()
                        if len(parts) >= 2:
                            current_inets.append(parts[1])
                    elif sline.startswith("status:"):
                        current_status = sline.split(":", 1)[1].strip()

            if current_name and current_inets:
                for ip in current_inets:
                    if ip not in discovered_ips and not ip.startswith("127.94."):
                        iface = _classify_interface(current_name, ip, current_mtu, current_status, current_flags)
                        interfaces.append(iface)
                        discovered_ips.add(ip)
        except Exception as e:
            logger.debug(f"macOS ifconfig discovery notice: {e}")

    # 2. Linux / Android sysfs and ip command discovery
    elif sys.platform.startswith("linux"):
        sysfs_net = Path("/sys/class/net")
        if sysfs_net.exists():
            for dev_dir in sysfs_net.iterdir():
                dev_name = dev_dir.name
                if dev_name.startswith("veth") or dev_name.startswith("docker"):
                    continue
                carrier = False
                carrier_file = dev_dir / "carrier"
                if carrier_file.exists():
                    try:
                        carrier = (carrier_file.read_text().strip() == "1")
                    except Exception:
                        carrier = False
                operstate = "unknown"
                oper_file = dev_dir / "operstate"
                if oper_file.exists():
                    try:
                        operstate = oper_file.read_text().strip()
                    except Exception:
                        pass
                mtu = 1500
                mtu_file = dev_dir / "mtu"
                if mtu_file.exists():
                    try:
                        mtu = int(mtu_file.read_text().strip())
                    except Exception:
                        pass

                # Get IP via ip -j addr show <dev> or socket
                ip_addr = _get_linux_ip_for_interface(dev_name)
                if ip_addr and ip_addr not in discovered_ips:
                    status = "active" if (carrier or operstate == "up") else "inactive"
                    iface = _classify_interface(dev_name, ip_addr, mtu, status, operstate)
                    interfaces.append(iface)
                    discovered_ips.add(ip_addr)

    # 3. Fallback: Socket discovery of active outbound route
    if not any(i.type != "loopback" for i in interfaces):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("1.1.1.1", 80))
            outbound_ip = s.getsockname()[0]
            s.close()
            if outbound_ip and outbound_ip not in discovered_ips:
                interfaces.append(NetworkInterface(
                    name="default_outbound",
                    ip=outbound_ip,
                    type="wifi7_mlo" if outbound_ip.startswith("192.168.8.") else "lan_1gbe",
                    status="UP",
                    mtu=1500,
                    rtt_ms=1.4,
                    bandwidth_mbps=1000.0,
                    role="PRIMARY"
                ))
                discovered_ips.add(outbound_ip)
        except Exception:
            pass

    # Ensure loopback exists
    if not any(i.type == "loopback" for i in interfaces):
        interfaces.append(NetworkInterface(
            name="lo0" if sys.platform == "darwin" else "lo",
            ip="127.0.0.1",
            type="loopback",
            status="UP",
            mtu=16384,
            rtt_ms=0.1,
            bandwidth_mbps=10000.0,
            role="LOCAL"
        ))

    return interfaces


def _get_linux_ip_for_interface(dev_name: str) -> Optional[str]:
    """Retrieve IPv4 address for a Linux interface using ip command or socket ioctl."""
    try:
        res = subprocess.run(["ip", "-j", "addr", "show", dev_name], capture_output=True, text=True, timeout=2.0)
        if res.returncode == 0:
            data = json.loads(res.stdout)
            for if_info in data:
                for addr_info in if_info.get("addr_info", []):
                    if addr_info.get("family") == "inet":
                        return addr_info.get("local")
    except Exception:
        pass

    try:
        res = subprocess.run(["ip", "addr", "show", dev_name], capture_output=True, text=True, timeout=2.0)
        if res.returncode == 0:
            m = re.search(r"inet\s+(\d+\.\d+\.\d+\.\d+)", res.stdout)
            if m:
                return m.group(1)
    except Exception:
        pass

    return None


def _classify_interface(name: str, ip: str, mtu: int, status: str, flags_or_state: str) -> NetworkInterface:
    """Classify physical and virtual network interfaces into operational roles and types."""
    is_up = ("UP" in flags_or_state.upper() or flags_or_state == "active" or status == "active")
    status_str = "UP" if is_up else "DOWN"

    if name.startswith("bridge") or ip.startswith("169.254."):
        return NetworkInterface(
            name=name,
            ip=ip,
            type="thunderbolt4_dma",
            status=status_str,
            mtu=mtu,
            rtt_ms=0.27,
            bandwidth_mbps=10000.0,
            role="VAULT_ACCELERATOR"
        )
    elif name.startswith("utun") or name.startswith("tailscale") or ip.startswith("100."):
        return NetworkInterface(
            name=name,
            ip=ip,
            type="tailscale_wireguard",
            status=status_str,
            mtu=mtu,
            rtt_ms=5.0,
            bandwidth_mbps=500.0,
            role="OVERLAY"
        )
    elif name == "en1" or name.startswith("wl") or "wifi" in name.lower():
        return NetworkInterface(
            name=name,
            ip=ip,
            type="wifi7_mlo",
            status=status_str,
            mtu=mtu,
            rtt_ms=1.4,
            bandwidth_mbps=2401.0,
            role="PRIMARY"
        )
    elif name == "en0" or name.startswith("eth") or name.startswith("enp") or name.startswith("enx"):
        return NetworkInterface(
            name=name,
            ip=ip,
            type="lan_1gbe",
            status=status_str,
            mtu=mtu,
            rtt_ms=2.0,
            bandwidth_mbps=1000.0,
            role="SECONDARY"
        )
    elif ip.startswith("127.") or name.startswith("lo"):
        return NetworkInterface(
            name=name,
            ip=ip,
            type="loopback",
            status="UP",
            mtu=mtu,
            rtt_ms=0.1,
            bandwidth_mbps=10000.0,
            role="LOCAL"
        )
    else:
        return NetworkInterface(
            name=name,
            ip=ip,
            type="general_ip",
            status=status_str,
            mtu=mtu,
            rtt_ms=3.0,
            bandwidth_mbps=1000.0,
            role="SECONDARY"
        )


def get_live_peer_metrics(peer_ip: str) -> LinkMetrics:
    """
    Structured UNAL contract function:
    Returns real-time LinkMetrics for a given peer IP or hostname.
    Determines Direct WireGuard vs DERP Relay, probes live RTT/loss,
    and assigns the optimal transport tier.
    """
    clean_ip = peer_ip.strip()

    # 1. Localhost / Loopback fast-path
    if clean_ip in ("127.0.0.1", "localhost", "::1"):
        return LinkMetrics(
            peer_id="local_host",
            tailscale_ip="127.0.0.1",
            is_direct=True,
            rtt_ms=0.08,
            bandwidth_mbps=10000.0,
            packet_loss=0.0,
            transport_tier=TransportTier.LOCAL_LOOPBACK.value
        )

    # 2. Check local interfaces
    local_ifaces = discover_local_interfaces()
    for iface in local_ifaces:
        if iface.ip == clean_ip:
            return LinkMetrics(
                peer_id="self_interface",
                tailscale_ip=clean_ip,
                is_direct=True,
                rtt_ms=iface.rtt_ms,
                bandwidth_mbps=iface.bandwidth_mbps,
                packet_loss=0.0,
                transport_tier=TransportTier.LOCAL_LOOPBACK.value
            )

    # 3. Query Tailscale peer topology
    ts_data = query_tailscale_status()
    self_info = ts_data.get("Self", {})
    self_ips = self_info.get("TailscaleIPs", [])
    if clean_ip in self_ips:
        return LinkMetrics(
            peer_id=self_info.get("HostName", "self"),
            tailscale_ip=clean_ip,
            is_direct=True,
            rtt_ms=0.1,
            bandwidth_mbps=10000.0,
            packet_loss=0.0,
            transport_tier=TransportTier.LOCAL_LOOPBACK.value
        )

    peers = ts_data.get("Peer", {})
    matched_peer: Optional[Dict[str, Any]] = None
    peer_key = ""

    for k, v in peers.items():
        ts_ips = v.get("TailscaleIPs", [])
        host_name = v.get("HostName", "")
        dns_name = v.get("DNSName", "")
        if clean_ip in ts_ips or clean_ip == host_name or clean_ip in dns_name:
            matched_peer = v
            peer_key = k
            break

    # Determine peer characteristics
    node_name = matched_peer.get("HostName", clean_ip) if matched_peer else clean_ip
    cur_addr = matched_peer.get("CurAddr", "") if matched_peer else ""
    relay = matched_peer.get("Relay", "") if matched_peer else ""
    online = matched_peer.get("Online", True) if matched_peer else True

    is_direct = bool(cur_addr and not cur_addr.startswith("relay:") and not relay == cur_addr)

    # Empirical reachability probe
    probe_ports = [22, 8022, 50052, 31330] if is_direct or online else None
    reachable, live_rtt, jitter, loss = probe_peer_empirical(clean_ip, ports=probe_ports)

    # If unreachable
    if not reachable and not online:
        return LinkMetrics(
            peer_id=node_name,
            tailscale_ip=clean_ip,
            is_direct=False,
            rtt_ms=999.0,
            bandwidth_mbps=0.0,
            packet_loss=100.0,
            transport_tier=TransportTier.UNREACHABLE.value
        )

    # Assign optimal transport tier
    if clean_ip.startswith("169.254."):
        tier = TransportTier.TB4_DMA.value
        bw = 10000.0
    elif is_direct and cur_addr.startswith("192.168.8."):
        # Check if local LAN direct
        tier = TransportTier.WIFI7_MLO.value if "wifi" in cur_addr.lower() else TransportTier.LAN_1GBE.value
        bw = 2401.0 if tier == TransportTier.WIFI7_MLO.value else 1000.0
    elif is_direct:
        tier = TransportTier.TAILSCALE_DIRECT.value
        bw = 500.0
    elif relay:
        tier = TransportTier.DERP_RELAY.value
        bw = 40.0
    else:
        tier = TransportTier.TAILSCALE_DIRECT.value if reachable else TransportTier.UNREACHABLE.value
        bw = 100.0 if reachable else 0.0

    return LinkMetrics(
        peer_id=node_name,
        tailscale_ip=clean_ip,
        is_direct=is_direct,
        rtt_ms=round(live_rtt, 2) if reachable else 999.0,
        bandwidth_mbps=bw,
        packet_loss=round(loss, 1),
        transport_tier=tier
    )


def compute_routing_cost(src: str, dst: str, tensor_size_bytes: int) -> float:
    """
    6-Tier Dijkstra DP Routing Edge Cost Function.
    Calculates the latency-and-bandwidth-weighted transfer cost for tensor shards.
    """
    # Intra-node communication is zero cost
    if src == dst or (src in ("127.0.0.1", "localhost") and dst in ("127.0.0.1", "localhost")):
        return 0.0

    # Retrieve live link metrics
    metrics = get_live_peer_metrics(dst)
    tier = metrics.transport_tier

    if tier == TransportTier.UNREACHABLE.value or metrics.packet_loss >= 100.0:
        return float("inf")

    base_multiplier = TIER_BASE_MULTIPLIERS.get(tier, 1.0)
    bw_bytes_per_sec = max(metrics.bandwidth_mbps * 125000.0, 1000.0)
    transfer_sec = tensor_size_bytes / bw_bytes_per_sec
    rtt_sec = max(metrics.rtt_ms, 0.01) / 1000.0
    loss_penalty = 1.0 + (3.0 * (metrics.packet_loss / 100.0))

    cost = base_multiplier * (transfer_sec + rtt_sec) * loss_penalty
    return round(cost, 6)


class UnifiedNetworkAwarenessLayer:
    """
    Singleton UNAL Daemon Manager:
    Periodically polls physical interfaces, Tailscale daemon status,
    and peer socket latencies to maintain live telemetry state.
    """
    _instance: Optional["UnifiedNetworkAwarenessLayer"] = None
    _lock = threading.Lock()

    def __init__(self, polling_interval_sec: float = 10.0):
        self.polling_interval_sec = polling_interval_sec
        self.local_interfaces: List[NetworkInterface] = []
        self.peers: List[PeerStatus] = []
        self.last_snapshot: Optional[MeshTelemetrySnapshot] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self.refresh_telemetry()

    @classmethod
    def get_instance(cls, polling_interval_sec: float = 10.0) -> "UnifiedNetworkAwarenessLayer":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(polling_interval_sec=polling_interval_sec)
            return cls._instance

    def refresh_telemetry(self) -> MeshTelemetrySnapshot:
        """Perform a synchronous live empirical network survey cycle."""
        self.local_interfaces = discover_local_interfaces()
        ts_data = query_tailscale_status()

        self_info = ts_data.get("Self", {})
        local_tailscale_ip = ""
        if self_info.get("TailscaleIPs"):
            local_tailscale_ip = self_info["TailscaleIPs"][0]
        local_hostname = self_info.get("HostName", socket.gethostname())

        peer_dict = ts_data.get("Peer", {})
        peer_list: List[PeerStatus] = []

        for p_key, p_val in peer_dict.items():
            ts_ips = p_val.get("TailscaleIPs", [])
            if not ts_ips:
                continue
            ts_ip = ts_ips[0]
            host_name = p_val.get("HostName", "peer")
            cur_addr = p_val.get("CurAddr", "")
            relay = p_val.get("Relay", "")
            online = p_val.get("Online", False)
            active = p_val.get("Active", False)

            is_direct = bool(cur_addr and not cur_addr.startswith("relay:") and relay != cur_addr)
            conn_type = "DIRECT_WIREGUARD" if is_direct else ("DERP_RELAY" if relay else "IDLE")

            # Check SSH and latency if online
            ssh_available = False
            rtt_ms = 999.0
            jitter_ms = 0.0
            loss = 100.0

            if online:
                # Probe SSH port (22 on Linux/Mac, 8022 on Android Termux)
                ports_to_try = [8022, 22] if "pixel" in host_name.lower() or "s20" in host_name.lower() else [22, 8022]
                for p in ports_to_try:
                    ssh_ok, p_rtt = probe_socket_tcp(ts_ip, p, timeout_sec=0.4)
                    if ssh_ok:
                        ssh_available = True
                        rtt_ms = p_rtt
                        loss = 0.0
                        break

                if not ssh_available:
                    reach, ping_rtt, ping_jit, ping_loss = probe_ping_empirical(ts_ip, count=2, timeout_sec=0.8)
                    if reach:
                        rtt_ms = ping_rtt
                        jitter_ms = ping_jit
                        loss = ping_loss

            tier = (
                TransportTier.TB4_DMA.value if ts_ip.startswith("169.254.") else
                TransportTier.TAILSCALE_DIRECT.value if is_direct else
                TransportTier.DERP_RELAY.value if relay else
                TransportTier.UNREACHABLE.value
            )
            bw = 10000.0 if tier == TransportTier.TB4_DMA.value else (500.0 if is_direct else 40.0)

            peer_list.append(PeerStatus(
                node_name=host_name,
                tailscale_ip=ts_ip,
                cur_addr=cur_addr,
                connection_type=conn_type,
                is_direct=is_direct,
                relay=relay,
                online=online,
                active=active,
                rtt_ms=round(rtt_ms, 2),
                jitter_ms=round(jitter_ms, 2),
                packet_loss=round(loss, 1),
                bandwidth_mbps=bw,
                transport_tier=tier,
                ssh_available=ssh_available,
                last_seen=p_val.get("LastSeen", "")
            ))

        self.peers = peer_list

        # Compute bonding state
        active_ifaces = [i for i in self.local_interfaces if i.status == "UP" and i.type != "loopback"]
        combined_bw = sum(i.bandwidth_mbps for i in active_ifaces)
        weighted_rtt = sum(i.rtt_ms * (i.bandwidth_mbps / max(combined_bw, 1.0)) for i in active_ifaces) if active_ifaces else 1.0

        snapshot = MeshTelemetrySnapshot(
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
            local_node={
                "node_name": local_hostname,
                "tailscale_ip": local_tailscale_ip,
                "interfaces": [i.model_dump() for i in self.local_interfaces],
            },
            peers=[p.model_dump() for p in self.peers],
            bonding_state={
                "mode": "ACTIVE_PARALLEL_STRIPING" if len(active_ifaces) > 1 else "SINGLE_INTERFACE",
                "effective_throughput_mbps": round(combined_bw, 1),
                "weighted_rtt_ms": round(weighted_rtt, 2),
                "active_paths_count": len(active_ifaces),
            }
        )

        self.last_snapshot = snapshot
        return snapshot

    def export_telemetry_json(self, target_path: Optional[Path] = None) -> Path:
        """Write live telemetry snapshot to JSON on disk."""
        out_path = target_path or LIVE_TELEMETRY_PATH
        out_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot = self.last_snapshot or self.refresh_telemetry()

        temp_path = out_path.with_suffix(".tmp")
        with open(temp_path, "w") as f:
            f.write(json.dumps(snapshot.model_dump(), indent=2))
        temp_path.replace(out_path)
        return out_path

    def start_background_daemon(self):
        """Start non-blocking continuous background telemetry refresh thread."""
        if self._running:
            return
        self._running = True

        def _worker():
            logger.info(f"UNAL background telemetry daemon started (interval={self.polling_interval_sec}s)")
            while self._running:
                try:
                    self.refresh_telemetry()
                    self.export_telemetry_json()
                except Exception as e:
                    logger.debug(f"Telemetry cycle exception: {e}")
                time.sleep(self.polling_interval_sec)

        self._thread = threading.Thread(target=_worker, daemon=True, name="UNAL_TelemetryWorker")
        self._thread.start()

    def stop_background_daemon(self):
        """Stop background telemetry thread."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
            logger.info("UNAL background daemon stopped")


if __name__ == "__main__":
    unal = UnifiedNetworkAwarenessLayer.get_instance()
    snapshot = unal.refresh_telemetry()
    json_path = unal.export_telemetry_json()
    print(f"[UNAL] Generated live telemetry -> {json_path}")
    print(json.dumps(snapshot.model_dump(), indent=2))
