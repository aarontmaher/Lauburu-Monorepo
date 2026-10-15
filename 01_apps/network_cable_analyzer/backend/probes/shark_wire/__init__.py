"""
Shark Wire Packet Capture & Dissection Engine.
Provides Wireshark-grade packet capture, pure Python protocol dissection,
in-memory ring buffer, AST filter compilation, and real-time streaming.
"""

from .interfaces import discover_darwin_interfaces, MESH_INTERFACE_ROLES
from .ring_buffer import SharkWireRingBuffer
from .filter import SharkWireFilter
from .dissector import (
    dissect_packet,
    dissect_ethernet,
    dissect_ipv4,
    dissect_ipv6,
    dissect_tcp,
    dissect_udp,
    dissect_icmp,
    dissect_wireguard,
    dissect_local_ai_rpc,
    dissect_darwin_utun,
    format_hex_dump,
)
from .fixtures import read_pcap_file, load_authentic_fixture_packets
from .engine import SharkWirePacketEngine

__all__ = [
    "discover_darwin_interfaces",
    "MESH_INTERFACE_ROLES",
    "SharkWireRingBuffer",
    "SharkWireFilter",
    "dissect_packet",
    "dissect_ethernet",
    "dissect_ipv4",
    "dissect_ipv6",
    "dissect_tcp",
    "dissect_udp",
    "dissect_icmp",
    "dissect_wireguard",
    "dissect_local_ai_rpc",
    "dissect_darwin_utun",
    "format_hex_dump",
    "read_pcap_file",
    "load_authentic_fixture_packets",
    "SharkWirePacketEngine",
]
