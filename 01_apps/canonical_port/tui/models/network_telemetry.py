"""
Network Telemetry Data Models
Structured, decoupled dataclasses representing the 7-node Lauburu mesh topology,
WAN failover states, Tailscale WireGuard overlay, 10Gbps TB4 DMA Bridge, and llama.cpp Port 50052 RPC matrix.
Provides .to_dict() and .to_json() methods for direct headless AGI ingestion (Rule #0 & R3).
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
import json
import datetime


@dataclass
class WanRoute:
    """Represents a primary, secondary, or fallback WAN route."""
    interface: str           # e.g., "en0_wifi_wan", "en6_usb_tether", "utun1_tailscale"
    status: str              # "ACTIVE", "STANDBY", "DEGRADED", "OFFLINE"
    rtt_ms: Optional[float]  # EWMA RTT in ms (None if offline/waiting)
    drop_rate: float         # Sliding-window packet drop rate (0.0 - 1.0)
    circuit_state: str       # "CLOSED", "OPEN", "HALF_OPEN"
    bandwidth: str           # e.g., "2.4 Gbps (Wi-Fi 7 MLO)", "120 Mbps (5G Hotspot)"
    priority: str = "P0"     # "P0", "P1", "P2", "P3"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TailscalePeer:
    """Represents a peer node in the 7-node Tailscale WireGuard overlay mesh."""
    node_name: str           # e.g., "Mac_Node", "MacBook_Pro", "Linux_Head_Node"
    ip: str                  # Tailscale 100.x.y.z IP
    status: str              # "ONLINE", "IDLE", "OFFLINE"
    relay: str               # "Direct WireGuard", "DERP Relay"
    layer: str = ""          # "L1", "L2", "L3", "L4", "L5", "L6", "L7"
    os: str = ""             # "macOS Darwin ARM64", "Debian Linux", "Android 15"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Tb4DmaInterconnect:
    """Represents the 10Gbps Thunderbolt 4 PCIe DMA high-speed bridge link."""
    ip: str                  # "169.254.187.138"
    status: str              # "CONNECTED", "OFFLINE", "DEGRADED"
    rtt_ms: float            # 0.277 ms nominal
    throughput_gbps: float   # 38.4 Gbps nominal
    interface: str = "bridge0 / tb0"
    zero_copy_active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LlamaRpcNode:
    """Represents a GGML-RPC sharding node on Port 50052."""
    node_name: str           # e.g., "Linux Head Node", "MacBook Pro", "Mac Mini Host"
    endpoint: str            # e.g., "100.101.39.98:50052", "169.254.187.138:50052", "127.0.0.1:50052"
    layers_sharded: int      # e.g., 28, 28, 24 for Kimi 88B Tandem Titan (-ts 28,28,24)
    vram_used_gb: float      # e.g., 13.5, 13.5, 12.0
    status: str              # "ONLINE", "ACTIVE", "OFFLINE"
    latency_ms: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class InternetSpeedMetrics:
    """Internet Speed Metrics via /usr/bin/networkQuality -c -M 5."""
    download_mbps: Optional[float] = None
    upload_mbps: Optional[float] = None
    responsiveness_rpm: Optional[int] = None
    latency_ms: Optional[float] = None
    timestamp: Optional[str] = None
    command: str = "/usr/bin/networkQuality -c -M 5"
    cycle_seconds: int = 300
    last_tested_iso: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class NodeSshStatus:
    """SSH Daemon Fleet Status per node."""
    node_id: str
    host: str
    port: int
    status: str = "OFFLINE"       # "OPEN", "CLOSED", "TIMEOUT", "OFFLINE"
    banner: Optional[str] = None  # e.g. "SSH-2.0-OpenSSH_9.8"
    key_type: str = "ssh-ed25519"
    latency_ms: Optional[float] = None
    last_auth_iso: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RouterSystemInfo:
    """Represents GL.iNet / OpenWrt router system status and hardware telemetry."""
    model: str = "GL-MT3600BE"
    hostname: str = "GL-MT3600BE"
    release: str = "OpenWrt 23.05 / GL.iNet 4.5.0"
    kernel: str = "5.15.150"
    uptime: int = 0
    uptime_formatted: str = "0s"
    load_average: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    memory_total_mb: float = 512.0
    memory_free_mb: float = 0.0
    memory_used_mb: float = 0.0
    memory_percent: float = 0.0
    status: str = "OFFLINE"       # "ONLINE", "OFFLINE", "DEGRADED"
    ip: str = "192.168.8.1"
    tailscale_ip: str = "100.122.185.123"
    last_seen: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


@dataclass
class RouterInterfaceStats:
    """Represents interface status and traffic stats from ubus network.interface dump."""
    interface: str
    name: str
    up: bool = False
    ip_addresses: List[str] = field(default_factory=list)
    mac_address: str = ""
    rx_bytes: int = 0
    tx_bytes: int = 0
    rx_packets: int = 0
    tx_packets: int = 0
    rx_errors: int = 0
    tx_errors: int = 0
    rx_mbps: Optional[float] = None
    tx_mbps: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ConnectedClient:
    """Represents a client device connected to GL.iNet router (Wi-Fi or LAN)."""
    mac: str
    ip: str = ""
    hostname: Optional[str] = None
    interface: str = "wlan0"
    rssi_dbm: Optional[int] = None
    tx_rate_mbps: Optional[float] = None
    rx_rate_mbps: Optional[float] = None
    connected_time_seconds: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RouterCommandResult:
    """Result of an executed UCI, ubus, or raw shell command on GL.iNet router."""
    command: str
    success: bool = False
    output: str = ""
    error: Optional[str] = None
    execution_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SpeedtestState:
    """Live Speedtest State & Progress for TUI Card and Telemetry Store."""
    stage: str = "IDLE"           # "IDLE", "INITIALIZING", "DOWNLINK", "UPLINK", "RESPONSIVENESS", "COMPLETED", "ERROR", "CANCELLED"
    download_mbps: float = 0.0
    upload_mbps: float = 0.0
    current_mbps: float = 0.0
    percent: float = 0.0
    responsiveness_rpm: Optional[int] = None
    base_rtt_ms: Optional[float] = None
    peak_download_mbps: float = 0.0
    peak_upload_mbps: float = 0.0
    error_message: Optional[str] = None
    timestamp: str = ""
    is_running: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class NetworkTelemetrySnapshot:
    """
    Decoupled Headless State Snapshot for Master AGI and UI rendering.
    Enables Master AGI (Kimi 88B, Qwen 3.8 Max, Gemini Flash) to query raw structured state
    without parsing HTML or ANSI strings (R3).
    """
    timestamp: str
    wan_routes: List[WanRoute] = field(default_factory=list)
    tailscale_peers: List[TailscalePeer] = field(default_factory=list)
    tb4_dma: Tb4DmaInterconnect = field(default_factory=lambda: Tb4DmaInterconnect(
        ip="169.254.187.138",
        status="CONNECTED",
        rtt_ms=0.277,
        throughput_gbps=38.4
    ))
    llama_rpc_nodes: List[LlamaRpcNode] = field(default_factory=list)
    internet_speed: InternetSpeedMetrics = field(default_factory=InternetSpeedMetrics)
    ssh_fleet: List[NodeSshStatus] = field(default_factory=list)
    router_info: Optional[RouterSystemInfo] = None
    router_interfaces: List[RouterInterfaceStats] = field(default_factory=list)
    router_clients: List[ConnectedClient] = field(default_factory=list)
    speedtest_state: Optional[SpeedtestState] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize state snapshot to standard Python dict."""
        return {
            "timestamp": self.timestamp,
            "wan_routes": [r.to_dict() for r in self.wan_routes],
            "tailscale_peers": [p.to_dict() for p in self.tailscale_peers],
            "tb4_dma": self.tb4_dma.to_dict(),
            "llama_rpc_nodes": [n.to_dict() for n in self.llama_rpc_nodes],
            "internet_speed": self.internet_speed.to_dict(),
            "ssh_fleet": [s.to_dict() for s in self.ssh_fleet],
            "router_info": self.router_info.to_dict() if self.router_info else None,
            "router_interfaces": [i.to_dict() for i in self.router_interfaces],
            "router_clients": [c.to_dict() for c in self.router_clients],
            "speedtest_state": self.speedtest_state.to_dict() if self.speedtest_state else None
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize state snapshot to formatted JSON string for Master AGI ingestion."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NetworkTelemetrySnapshot":
        """Deserialize from raw dictionary."""
        wan_routes = [WanRoute(**r) for r in data.get("wan_routes", [])]
        tailscale_peers = [TailscalePeer(**p) for p in data.get("tailscale_peers", [])]
        
        tb4_raw = data.get("tb4_dma", {})
        tb4_dma = Tb4DmaInterconnect(**tb4_raw) if tb4_raw else Tb4DmaInterconnect(
            ip="169.254.187.138", status="OFFLINE", rtt_ms=0.0, throughput_gbps=0.0
        )
        
        rpc_nodes = [LlamaRpcNode(**n) for n in data.get("llama_rpc_nodes", [])]
        
        speed_raw = data.get("internet_speed", {})
        internet_speed = InternetSpeedMetrics(**speed_raw) if speed_raw else InternetSpeedMetrics()
        
        ssh_fleet = [NodeSshStatus(**s) for s in data.get("ssh_fleet", [])]
        
        router_raw = data.get("router_info")
        router_info = RouterSystemInfo(**router_raw) if router_raw else None
        
        router_interfaces = [RouterInterfaceStats(**i) for i in data.get("router_interfaces", [])]
        router_clients = [ConnectedClient(**c) for c in data.get("router_clients", [])]
        
        speedtest_raw = data.get("speedtest_state")
        speedtest_state = SpeedtestState(**speedtest_raw) if speedtest_raw else None
        
        return cls(
            timestamp=data.get("timestamp", datetime.datetime.now().strftime("%H:%M:%S")),
            wan_routes=wan_routes,
            tailscale_peers=tailscale_peers,
            tb4_dma=tb4_dma,
            llama_rpc_nodes=rpc_nodes,
            internet_speed=internet_speed,
            ssh_fleet=ssh_fleet,
            router_info=router_info,
            router_interfaces=router_interfaces,
            router_clients=router_clients,
            speedtest_state=speedtest_state
        )

    @classmethod
    def create_canonical_default(cls) -> "NetworkTelemetrySnapshot":
        """Generate canonical default state matching 7-node mesh topology and Port 50052 RPC split."""
        now = datetime.datetime.now().strftime("%H:%M:%S")
        
        wan_routes = [
            WanRoute(
                interface="en0_wifi_wan",
                status="ACTIVE",
                rtt_ms=1.84,
                drop_rate=0.00,
                circuit_state="CLOSED",
                bandwidth="2.4 Gbps (Wi-Fi 7 MLO)",
                priority="P1"
            ),
            WanRoute(
                interface="en6_usb_tether",
                status="STANDBY",
                rtt_ms=24.50,
                drop_rate=0.00,
                circuit_state="CLOSED",
                bandwidth="120 Mbps (5G Hotspot)",
                priority="P3"
            ),
            WanRoute(
                interface="utun1_tailscale",
                status="ACTIVE",
                rtt_ms=4.12,
                drop_rate=0.00,
                circuit_state="CLOSED",
                bandwidth="1.0 Gbps (WireGuard Overlay)",
                priority="P2"
            )
        ]
        
        tailscale_peers = [
            TailscalePeer(node_name="Mac_Node", ip="100.119.199.76", status="ONLINE", relay="Direct WireGuard", layer="L1", os="macOS Darwin ARM64"),
            TailscalePeer(node_name="MacBook_Pro", ip="100.103.212.21", status="ONLINE", relay="Direct WireGuard", layer="L2", os="macOS Darwin ARM64"),
            TailscalePeer(node_name="Linux_Head_Node", ip="100.101.39.98", status="ONLINE", relay="Direct WireGuard", layer="L3", os="Debian Linux x86_64"),
            TailscalePeer(node_name="Linux_Tablet", ip="100.81.92.125", status="ONLINE", relay="Direct WireGuard", layer="L4", os="Debian Linux ARM64"),
            TailscalePeer(node_name="MacBook_Air", ip="100.93.158.96", status="ONLINE", relay="Direct WireGuard", layer="L5", os="macOS Darwin ARM64"),
            TailscalePeer(node_name="Pixel_10_Pro_XL", ip="100.73.38.87", status="ONLINE", relay="Direct WireGuard", layer="L6", os="Android 15 (Tensor G5)"),
            TailscalePeer(node_name="Samsung_S20", ip="100.84.40.95", status="IDLE", relay="Direct WireGuard", layer="L7", os="Android 13 (Exynos 990)")
        ]
        
        tb4_dma = Tb4DmaInterconnect(
            ip="169.254.187.138",
            status="CONNECTED",
            rtt_ms=0.277,
            throughput_gbps=38.4,
            interface="bridge0 / tb0",
            zero_copy_active=True
        )

        llama_rpc_nodes = [
            LlamaRpcNode(
                node_name="Mac_Node (Host M4 Pro)",
                endpoint="127.0.0.1:50052",
                layers_sharded=28,
                vram_used_gb=13.5,
                status="ACTIVE",
                latency_ms=0.05
            ),
            LlamaRpcNode(
                node_name="MacBook_Pro (TB4 Bridge)",
                endpoint="169.254.187.138:50052",
                layers_sharded=28,
                vram_used_gb=13.5,
                status="ACTIVE",
                latency_ms=0.28
            ),
            LlamaRpcNode(
                node_name="Linux_Head_Node (Ryzen 7)",
                endpoint="100.101.39.98:50052",
                layers_sharded=24,
                vram_used_gb=12.0,
                status="ACTIVE",
                latency_ms=1.20
            )
        ]
        
        internet_speed = InternetSpeedMetrics(
            download_mbps=482.0,
            upload_mbps=48.0,
            responsiveness_rpm=1420,
            latency_ms=12.4,
            timestamp=now,
            last_tested_iso=now
        )
        
        ssh_fleet = [
            NodeSshStatus(node_id="L1", host="192.168.8.155", port=22, status="OPEN", banner="SSH-2.0-OpenSSH_9.8", key_type="ssh-ed25519", latency_ms=0.05),
            NodeSshStatus(node_id="L2", host="192.168.8.127", port=22, status="OPEN", banner="SSH-2.0-OpenSSH_9.8", key_type="ssh-ed25519", latency_ms=0.28),
            NodeSshStatus(node_id="L3", host="192.168.8.224", port=22, status="OPEN", banner="SSH-2.0-OpenSSH_9.6p1", key_type="ssh-ed25519", latency_ms=1.20),
            NodeSshStatus(node_id="L4", host="192.168.8.173", port=22, status="OPEN", banner="SSH-2.0-OpenSSH_9.2p1", key_type="ssh-ed25519", latency_ms=4.10),
            NodeSshStatus(node_id="L5", host="192.168.8.222", port=22, status="OPEN", banner="SSH-2.0-OpenSSH_9.8", key_type="ssh-ed25519", latency_ms=1.45),
            NodeSshStatus(node_id="L6", host="192.168.8.160", port=8022, status="OPEN", banner="SSH-2.0-OpenSSH_9.8 (Termux)", key_type="ssh-ed25519", latency_ms=3.80),
            NodeSshStatus(node_id="L7", host="192.168.8.158", port=8022, status="OPEN", banner="SSH-2.0-OpenSSH_9.8 (Termux)", key_type="ssh-ed25519", latency_ms=4.20),
            NodeSshStatus(node_id="GW", host="192.168.8.1", port=22, status="OPEN", banner="SSH-2.0-dropbear_2023.83", key_type="ssh-ed25519", latency_ms=0.95)
        ]
        
        router_info = RouterSystemInfo(
            model="GL-MT3600BE",
            hostname="GL-MT3600BE",
            release="OpenWrt 23.05 / GL.iNet 4.5.0",
            kernel="5.15.150",
            uptime=1232810,
            uptime_formatted="14d 06:26:50",
            load_average=[0.12, 0.08, 0.05],
            memory_total_mb=512.0,
            memory_free_mb=184.0,
            memory_used_mb=328.0,
            memory_percent=64.0,
            status="ONLINE",
            ip="192.168.8.1",
            tailscale_ip="100.122.185.123",
            last_seen=now
        )
        
        router_interfaces = [
            RouterInterfaceStats(
                interface="eth0",
                name="wan",
                up=True,
                ip_addresses=["192.168.1.105/24"],
                mac_address="00:0C:43:36:00:BE",
                rx_bytes=1048576000,
                tx_bytes=524288000,
                rx_packets=750000,
                tx_packets=420000,
                rx_errors=0,
                tx_errors=0,
                rx_mbps=482.5,
                tx_mbps=48.0
            ),
            RouterInterfaceStats(
                interface="br-lan",
                name="lan",
                up=True,
                ip_addresses=["192.168.8.1/24"],
                mac_address="00:0C:43:36:00:BF",
                rx_bytes=524288000,
                tx_bytes=1048576000,
                rx_packets=420000,
                tx_packets=750000,
                rx_errors=0,
                tx_errors=0,
                rx_mbps=48.0,
                tx_mbps=482.5
            )
        ]
        
        router_clients = [
            ConnectedClient(
                mac="A4:83:E7:XX:XX:01",
                ip="192.168.8.230",
                hostname="Mac_Node",
                interface="wlan0",
                rssi_dbm=-42,
                tx_rate_mbps=2400.0,
                rx_rate_mbps=2400.0,
                connected_time_seconds=123000
            ),
            ConnectedClient(
                mac="3C:06:30:XX:XX:02",
                ip="192.168.8.127",
                hostname="MacBook_Pro",
                interface="wlan0",
                rssi_dbm=-45,
                tx_rate_mbps=1200.0,
                rx_rate_mbps=1200.0,
                connected_time_seconds=98000
            )
        ]
        
        speedtest_state = SpeedtestState(
            stage="IDLE",
            download_mbps=482.0,
            upload_mbps=48.0,
            current_mbps=0.0,
            percent=100.0,
            responsiveness_rpm=1420,
            base_rtt_ms=12.4,
            peak_download_mbps=512.0,
            peak_upload_mbps=52.4,
            error_message=None,
            timestamp=now,
            is_running=False
        )
        
        return cls(
            timestamp=now,
            wan_routes=wan_routes,
            tailscale_peers=tailscale_peers,
            tb4_dma=tb4_dma,
            llama_rpc_nodes=llama_rpc_nodes,
            internet_speed=internet_speed,
            ssh_fleet=ssh_fleet,
            router_info=router_info,
            router_interfaces=router_interfaces,
            router_clients=router_clients,
            speedtest_state=speedtest_state
        )
