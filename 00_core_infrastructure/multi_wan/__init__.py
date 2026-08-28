"""
multi_wan - Multi-WAN Aggregation & Accumulative VPN Bandwidth Pooling Package.

Modules:
- discovery: Dynamic interface & Tailscale mesh discovery engine (InterfaceTracker).
- proxy: Accumulative bonding & multiplexing proxy daemon on port 8888 (BondingProxyServer, StreamMultiplexer, SocketBinder).
- dashboard: HTTP monitoring API and dashboard web server on port 5050 (DashboardServer).
- benchmark: Comparative speedtest & benchmark runner (BenchmarkRunner).
- connectivity: Device-to-device connectivity optimizer (DeviceConnectivityOptimizer).
"""

from .discovery import InterfaceTracker, NetworkInterface
from .proxy import BondingProxyServer, StreamMultiplexer, SocketBinder
from .dashboard import DashboardServer
from .benchmark import BenchmarkRunner
from .agi_bridge import LocalAGIBridge
from .storage import StorageManager
from .pixel_nano import PixelNanoBridge
from .connectivity import DeviceConnectivityOptimizer, TransportMethod
from .hardware_telemetry import HardwareTelemetryMonitor
from .service_keepalive import ServiceKeepAliveManager, ManagedService
from .dynamic_port_scanner import DynamicPortScanner, DiscoveredAIService
from .gateway_router import GatewayRouter, AGIComputeNode
from .hybrid_mesh import HybridMeshOrchestrator, TokenBucket, BANDWIDTH_CAPS_MBPS
from .agi_offload import AGIOffloadEngine, ShardedNodeConfig
from .gateway_fallback import LatencyAwareGatewayFallback, GatewayMetrics

__version__ = "1.0.0"
__all__ = [
    "InterfaceTracker",
    "NetworkInterface",
    "BondingProxyServer",
    "StreamMultiplexer",
    "SocketBinder",
    "DashboardServer",
    "BenchmarkRunner",
    "LocalAGIBridge",
    "StorageManager",
    "PixelNanoBridge",
    "DeviceConnectivityOptimizer",
    "TransportMethod",
    "HardwareTelemetryMonitor",
    "HybridMeshOrchestrator",
    "TokenBucket",
    "BANDWIDTH_CAPS_MBPS",
    "AGIOffloadEngine",
    "ShardedNodeConfig",
    "LatencyAwareGatewayFallback",
    "GatewayMetrics",
    "GatewayRouter",
    "AGIComputeNode",
]

