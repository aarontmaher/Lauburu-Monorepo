"""
multi_wan/discovery.py - Dynamic Interface & Tailscale Mesh Discovery Engine.

Detects local physical & logical network interfaces (Wi-Fi, Ethernet, USB Tethering, Wi-Fi Direct/AWDL,
Bluetooth PAN) and Tailscale mesh nodes (MacBook, Google Pixel, Samsung Tablet).
Maintains health, latency (RTT ping), throughput, and status (ACTIVE, DEGRADED, DOWN).

STRICT MANDATE: ZERO SIMULATED DATA. All throughput, latency, and interface states
are measured directly via real OS socket probes, interface counters, and system commands.
"""

import asyncio
import json
import logging
import os
import socket
import subprocess
import time
from typing import Any, Callable, Dict, List, Optional

try:
    import psutil
except ImportError:
    psutil = None

logger = logging.getLogger("multi_wan.discovery")


class NetworkInterface:
    def __init__(
        self,
        name: str,
        ip: str,
        iface_type: str = "wifi",
        status: str = "ACTIVE",
        latency_ms: float = 0.0,
        throughput_mbps: float = 0.0,
        is_tailscale: bool = False,
        mac: str = "00:00:00:00:00:00",
    ):
        self.name = name
        self.ip = ip
        self.type = iface_type
        self.status = status
        self.latency_ms = latency_ms
        self.throughput_mbps = throughput_mbps
        self.is_tailscale = is_tailscale
        self.mac = mac
        self.last_seen = time.time()
        self.failure_count = 0
        self.bytes_sent = 0
        self.bytes_recv = 0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "ip": self.ip,
            "type": self.type,
            "status": self.status,
            "latency_ms": round(self.latency_ms, 2),
            "throughput_mbps": round(self.throughput_mbps, 2),
            "is_tailscale": self.is_tailscale,
            "mac": self.mac,
            "last_seen": self.last_seen,
            "failure_count": self.failure_count,
        }

    def __repr__(self):
        return f"<NetworkInterface {self.name} ({self.ip}) type={self.type} status={self.status} latency={self.latency_ms:.1f}ms throughput={self.throughput_mbps:.1f}Mbps>"


class InterfaceTracker:
    def __init__(self, check_interval: float = 3.0):
        self.check_interval = check_interval
        self.interfaces: Dict[str, NetworkInterface] = {}
        self.live_port_registry: Dict[str, Any] = {}
        self._cached_scanned_data: Optional[Dict[str, Any]] = None
        self._last_scan_time: float = 0.0
        self._monitoring_task: Optional[asyncio.Task] = None
        self._port_scan_task: Optional[asyncio.Task] = None
        self._running = False
        self._status_callbacks: List[Callable[[NetworkInterface, str, str], None]] = []

        # Pure dynamic discovery from OS kernel & live Tailscale daemon
        self.discover_local_interfaces()
        self.discover_tailscale_nodes()
        self.scan_live_ports()

    def register_status_callback(self, callback: Callable[[NetworkInterface, str, str], None]):
        """Registers a callback(interface, old_status, new_status) called on status change."""
        self._status_callbacks.append(callback)

    def discover_local_interfaces(self) -> List[NetworkInterface]:
        """Discovers physical & virtual network interfaces directly from OS kernel via psutil."""
        discovered = []
        if psutil:
            try:
                if_addrs = psutil.net_if_addrs()
                if_stats = psutil.net_if_stats()
                io_counters = psutil.net_io_counters(pernic=True)

                for nic_name, addrs in if_addrs.items():
                    # Filter loopback and special filter interfaces
                    if nic_name.startswith("lo") or nic_name.startswith("gif") or nic_name.startswith("stf"):
                        continue

                    ipv4 = "0.0.0.0"
                    mac = "00:00:00:00:00:00"
                    for a in addrs:
                        if a.family == socket.AF_INET:
                            ipv4 = a.address
                        elif getattr(a, "family", None) in (18, 17) or "link" in str(getattr(a, "family", "")).lower():
                            mac = a.address

                    stats = if_stats.get(nic_name)
                    is_up = stats.isup if stats else (ipv4 != "0.0.0.0")

                    # Determine interface classification dynamically
                    iface_type = "ethernet"
                    if nic_name.startswith("en0") or nic_name.startswith("wl") or "wifi" in nic_name.lower():
                        iface_type = "wifi"
                    elif nic_name.startswith("en") and nic_name != "en0":
                        iface_type = "usb_tether" if (stats and stats.speed == 0) else "ethernet"
                    elif nic_name.startswith("awdl") or nic_name.startswith("p2p"):
                        iface_type = "wifi_direct"
                    elif nic_name.startswith("utun") or nic_name.startswith("tailscale"):
                        iface_type = "tailscale"
                    elif nic_name.startswith("bnep"):
                        iface_type = "bluetooth_pan"

                    status = "ACTIVE" if (is_up and ipv4 != "0.0.0.0") else "OFFLINE"

                    # Format friendly descriptive display name
                    if nic_name == "en0":
                        display_name = "en0 (Wi-Fi)"
                    elif nic_name == "en6":
                        display_name = "en6 (USB Tethering)"
                    elif nic_name.startswith("awdl"):
                        display_name = f"{nic_name} (Wi-Fi Direct P2P)"
                    else:
                        display_name = f"{nic_name} ({iface_type.upper()})"

                    if display_name in self.interfaces:
                        iface = self.interfaces[display_name]
                        iface.ip = ipv4
                        iface.mac = mac
                        iface.status = status
                    else:
                        iface = NetworkInterface(
                            name=display_name,
                            ip=ipv4,
                            iface_type=iface_type,
                            status=status,
                            latency_ms=0.0,
                            throughput_mbps=0.0,
                            is_tailscale=(iface_type == "tailscale"),
                            mac=mac,
                        )
                        self.interfaces[display_name] = iface

                    # Store hardware byte counter baseline
                    if nic_name in io_counters:
                        cnt = io_counters[nic_name]
                        iface.bytes_sent = cnt.bytes_sent
                        iface.bytes_recv = cnt.bytes_recv

                    discovered.append(iface)
            except Exception as e:
                logger.debug(f"Dynamic local interface discovery error: {e}")
        else:
            try:
                hostname = socket.gethostname()
                _, _, ips = socket.gethostbyname_ex(hostname)
                for idx, ip in enumerate(ips):
                    if ip != "127.0.0.1" and not ip.startswith("169.254"):
                        name = f"local_if_{idx} ({ip})"
                        if name not in self.interfaces:
                            iface = NetworkInterface(
                                name=name,
                                ip=ip,
                                iface_type="wifi",
                                status="ACTIVE",
                                latency_ms=0.0,
                                throughput_mbps=0.0,
                            )
                            self.interfaces[name] = iface
                            discovered.append(iface)
            except Exception as e:
                logger.debug(f"Socket IP resolution error: {e}")

        return discovered

    def discover_tailscale_nodes(self) -> List[NetworkInterface]:
        """Discovers Tailscale mesh nodes dynamically via Tailscale CLI JSON output."""
        ts_nodes = []
        try:
            result = subprocess.run(
                ["tailscale", "status", "--json"],
                capture_output=True,
                text=True,
                timeout=2.5,
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)

                # Track Self Node
                self_node = data.get("Self", {})
                if self_node:
                    self_host = self_node.get("HostName", "LocalHost")
                    self_ips = self_node.get("TailscaleIPs", [])
                    self_ip = self_ips[0] if self_ips else "0.0.0.0"
                    self_name = f"{self_host} (Tailscale Self)"
                    if self_name in self.interfaces:
                        self_iface = self.interfaces[self_name]
                        self_iface.ip = self_ip
                        self_iface.status = "ACTIVE"
                    else:
                        self_iface = NetworkInterface(
                            name=self_name,
                            ip=self_ip,
                            iface_type="tailscale",
                            status="ACTIVE",
                            latency_ms=0.1,
                            throughput_mbps=0.0,
                            is_tailscale=True,
                        )
                        self.interfaces[self_name] = self_iface
                    ts_nodes.append(self_iface)

                # Track Remote Peers
                peers = data.get("Peer", {})
                for peer_id, peer in peers.items():
                    hostname = peer.get("HostName", "Tailscale Peer")
                    os_type = peer.get("OS", "").lower()
                    tailscale_ips = peer.get("TailscaleIPs", [])
                    ip = tailscale_ips[0] if tailscale_ips else "0.0.0.0"
                    online = peer.get("Online", False)

                    iface_type = "mobile" if (os_type in ("android", "ios") or "pixel" in hostname.lower() or "iphone" in hostname.lower() or "samsung" in hostname.lower()) else "wifi"
                    name = f"{hostname} (Tailscale)"
                    status = "ACTIVE" if online else "DOWN"

                    if name in self.interfaces:
                        iface = self.interfaces[name]
                        iface.ip = ip
                        iface.status = status
                    else:
                        iface = NetworkInterface(
                            name=name,
                            ip=ip,
                            iface_type=iface_type,
                            status=status,
                            latency_ms=0.0,
                            throughput_mbps=0.0,
                            is_tailscale=True,
                        )
                        self.interfaces[name] = iface
                    ts_nodes.append(iface)
        except Exception as e:
            logger.debug(f"Tailscale discovery error: {e}")

        return ts_nodes

    async def probe_interface(self, iface: NetworkInterface, probe_target: str = "8.8.8.8", probe_port: int = 53):
        """Probes real RTT latency and computes empirical throughput capability of an interface via socket connection."""
        start_time = time.perf_counter()
        success = False
        measured_rtt = 0.0

        loop = asyncio.get_event_loop()
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setblocking(False)

            if not iface.is_tailscale and iface.ip != "0.0.0.0" and not iface.ip.startswith("100."):
                try:
                    sock.bind((iface.ip, 0))
                except Exception:
                    pass

            await asyncio.wait_for(
                loop.sock_connect(sock, (probe_target, probe_port)),
                timeout=1.0,
            )
            measured_rtt = (time.perf_counter() - start_time) * 1000.0
            success = True
        except Exception:
            success = False
            measured_rtt = 999.9
        finally:
            if sock:
                try:
                    sock.close()
                except Exception:
                    pass

        old_status = iface.status
        if success:
            iface.failure_count = 0
            iface.latency_ms = max(0.1, measured_rtt)
            # Query real interface delta throughput from OS counters if available, otherwise 0.0 when idle
            measured_tp = 0.0
            try:
                import psutil
                io_counters = psutil.net_io_counters(pernic=True)
                for nic_name, cnt in io_counters.items():
                    if nic_name in iface.name or iface.name.startswith(nic_name):
                        if hasattr(iface, "_last_bytes") and hasattr(iface, "_last_bytes_time"):
                            dt = max(0.001, time.time() - iface._last_bytes_time)
                            delta = (cnt.bytes_sent + cnt.bytes_recv) - iface._last_bytes
                            if delta > 0:
                                measured_tp = round((delta * 8 / (1024 * 1024)) / dt, 2)
                        iface._last_bytes = cnt.bytes_sent + cnt.bytes_recv
                        iface._last_bytes_time = time.time()
                        break
            except Exception:
                pass
            iface.throughput_mbps = measured_tp

            if measured_rtt > 200.0:
                new_status = "DEGRADED"
            else:
                new_status = "ACTIVE"
        else:
            iface.failure_count += 1
            if iface.failure_count >= 3:
                new_status = "DOWN"
                iface.latency_ms = 999.9
                iface.throughput_mbps = 0.0
            else:
                new_status = "DEGRADED"

        if new_status != old_status:
            iface.status = new_status
            logger.info(f"Interface '{iface.name}' status changed: {old_status} -> {new_status}")
            for cb in self._status_callbacks:
                try:
                    cb(iface, old_status, new_status)
                except Exception as e:
                    logger.error(f"Callback error for {iface.name}: {e}")

        iface.last_seen = time.time()

    def update_interface_status(self, name: str, status: str, latency_ms: Optional[float] = None, throughput_mbps: Optional[float] = None):
        """Allows explicit update of interface status for test verification & dynamic events."""
        if name in self.interfaces:
            iface = self.interfaces[name]
            old_status = iface.status
            iface.status = status
            if latency_ms is not None:
                iface.latency_ms = latency_ms
            if throughput_mbps is not None:
                iface.throughput_mbps = throughput_mbps
            if old_status != status:
                for cb in self._status_callbacks:
                    try:
                        cb(iface, old_status, status)
                    except Exception as e:
                        logger.error(f"Callback error for {iface.name}: {e}")

    def get_active_interfaces(self) -> List[NetworkInterface]:
        """Returns list of interfaces currently in ACTIVE or DEGRADED state."""
        return [iface for iface in self.interfaces.values() if iface.status != "DOWN"]

    def get_all_interfaces(self) -> List[NetworkInterface]:
        """Returns list of all tracked interfaces."""
        return list(self.interfaces.values())

    def _resolve_mesh_nodes(self) -> List[Dict[str, str]]:
        """Dynamically resolves IP addresses from live discovered interfaces without hardcoded IP fallbacks."""
        resolved = []

        # Always include localhost
        resolved.append({"name": "Local Host", "ip": "127.0.0.1"})

        # Extract all discovered interfaces with valid routable IPv4 addresses
        for iface_name, iface in self.interfaces.items():
            if iface.ip and iface.ip not in ("0.0.0.0", "127.0.0.1") and not iface.ip.startswith("169.254"):
                resolved.append({
                    "name": iface.name,
                    "ip": iface.ip,
                })

        # Allow environment overrides if explicitly provided
        for key, val in os.environ.items():
            if key.endswith("_TAILSCALE_IP") and val:
                device_name = key.replace("_TAILSCALE_IP", "").replace("_", " ").title()
                existing = next((r for r in resolved if r["name"] == device_name), None)
                if existing:
                    existing["ip"] = val
                else:
                    resolved.append({"name": device_name, "ip": val})

        return resolved

    async def _port_scan_daemon(self):
        """Background periodic port scanning daemon loop (every 2.0s)."""
        while self._running:
            try:
                await self.scan_live_ports_async()
            except Exception as e:
                logger.error(f"Error in background port scan daemon: {e}")
            await asyncio.sleep(2.0)

    async def _monitoring_loop(self):
        """Periodic background monitoring loop."""
        while self._running:
            try:
                self.discover_local_interfaces()
                self.discover_tailscale_nodes()
                tasks = [self.probe_interface(iface) for iface in list(self.interfaces.values())]
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
                await self.scan_live_ports_async()
            except Exception as e:
                logger.error(f"Error in discovery monitoring loop: {e}")
            await asyncio.sleep(self.check_interval)

    def start_monitoring(self, loop: Optional[asyncio.AbstractEventLoop] = None) -> asyncio.Task:
        """Starts the background monitoring loop task."""
        if not self._running:
            self._running = True
            if loop is None:
                loop = asyncio.get_event_loop()
            self._monitoring_task = loop.create_task(self._monitoring_loop())
            self._port_scan_task = loop.create_task(self._port_scan_daemon())
        return self._monitoring_task

    def stop_monitoring(self):
        """Stops the background monitoring loop task."""
        self._running = False
        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()
        if self._port_scan_task and not self._port_scan_task.done():
            self._port_scan_task.cancel()

    async def scan_live_ports_async(self, ports: Optional[List[int]] = None) -> Dict[str, Any]:
        """
        Asynchronously scans all 5 mesh nodes for live active listening ports in < 200ms.
        Uses asyncio.gather with non-blocking socket probes (0.2s timeout).
        Updates self.live_port_registry and self._cached_scanned_data and returns scanned status dictionary.
        """
        now_val = time.time()
        if ports is None and self._cached_scanned_data is not None and (now_val - self._last_scan_time < 2.0):
            return self._cached_scanned_data

        if ports is None:
            ports = [50052, 8095, 8900, 9090, 9091, 5050, 8888, 11434, 8088]

        nodes = self._resolve_mesh_nodes()
        live_registry: Dict[str, Any] = {}

        async def check_target(name: str, ip: str, port: int):
            try:
                _, writer = await asyncio.wait_for(asyncio.open_connection(ip, port), timeout=0.2)
                writer.close()
                try:
                    await writer.wait_closed()
                except Exception:
                    pass
                return name, port, True
            except Exception:
                return name, port, False

        tasks = []
        for node in nodes:
            name = node["name"]
            ip = node["ip"]
            live_registry[name] = {"ip": ip, "open_ports": [], "active_services": {}}
            for p in ports:
                tasks.append(check_target(name, ip, p))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for res in results:
            if isinstance(res, tuple) and len(res) == 3:
                name, p, is_open = res
                if is_open and name in live_registry:
                    live_registry[name]["open_ports"].append(p)
                    live_registry[name]["active_services"][str(p)] = "ACTIVE"

        for name in live_registry:
            live_registry[name]["open_ports"].sort()

        now_val = time.time()
        scanned_data = {
            "status": "ok",
            "timestamp": now_val,
            "timestamp_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now_val)),
            "scanned_nodes_count": len(nodes),
            "ports_scanned": ports,
            "nodes": [node for node in nodes],
            "ports": {name: live_registry[name]["open_ports"] for name in live_registry},
            "live_port_registry": live_registry,
        }
        self.live_port_registry = live_registry
        self._cached_scanned_data = scanned_data
        self._last_scan_time = now_val
        return scanned_data

    async_scan_live_ports = scan_live_ports_async

    def scan_live_ports(self, ports: Optional[List[int]] = None) -> Dict[str, Any]:
        """
        Scans all 5 hardware mesh nodes for live active listening ports.
        Returns cached background scan data when available, or executes fast socket scan.
        """
        if ports is None and self._cached_scanned_data is not None:
            return self._cached_scanned_data

        if ports is None:
            ports = [50052, 8095, 8900, 9090, 9091, 5050, 8888, 11434, 8088]

        nodes = self._resolve_mesh_nodes()
        live_registry: Dict[str, Any] = {}
        for node in nodes:
            live_registry[node["name"]] = {"ip": node["ip"], "open_ports": [], "active_services": {}}

        def check_port_sync(node_name: str, ip: str, port: int):
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                timeout_val = 0.02 if (ip == "127.0.0.1" or ip == "localhost") else 0.05
                s.settimeout(timeout_val)
                res = s.connect_ex((ip, port))
                s.close()
                return node_name, port, (res == 0)
            except Exception:
                return node_name, port, False

        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(50, len(nodes) * len(ports))) as executor:
            futures = [
                executor.submit(check_port_sync, node["name"], node["ip"], p)
                for node in nodes
                for p in ports
            ]
            concurrent.futures.wait(futures, timeout=0.15)

            for f in futures:
                if f.done():
                    try:
                        node_name, port, is_open = f.result()
                        if is_open and node_name in live_registry:
                            live_registry[node_name]["open_ports"].append(port)
                            live_registry[node_name]["active_services"][str(port)] = "ACTIVE"
                    except Exception:
                        pass

        for name in live_registry:
            live_registry[name]["open_ports"].sort()

        now_val = time.time()
        scanned_data = {
            "status": "ok",
            "timestamp": now_val,
            "timestamp_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now_val)),
            "scanned_nodes_count": len(nodes),
            "ports_scanned": ports,
            "nodes": [node for node in nodes],
            "ports": {name: live_registry[name]["open_ports"] for name in live_registry},
            "live_port_registry": live_registry,
        }
        self.live_port_registry = live_registry
        self._cached_scanned_data = scanned_data
        self._last_scan_time = now_val
        return scanned_data
