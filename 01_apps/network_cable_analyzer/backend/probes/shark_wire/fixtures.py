"""
Authentic PCAP Replay Fixture Provider for Shark Wire.
Loads genuine recorded mesh traffic (WireGuard 41641, Local AI RPC 8082, TCP/UDP)
from tests/fixtures/mesh_traffic.pcap, adhering strictly to Rule 1 (Zero-Mock Truth Rule).
"""

import struct
import logging
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any

from .dissector import dissect_packet

logger = logging.getLogger("shark_wire.fixtures")

FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent.parent / "tests" / "fixtures"
PCAP_FIXTURE_PATH = FIXTURES_DIR / "mesh_traffic.pcap"


def read_pcap_file(filepath: Optional[Path] = None) -> List[Tuple[float, bytes]]:
    """
    Read a standard libpcap 2.4 file and extract raw records with timestamps.
    Returns list of (timestamp_seconds, packet_bytes).
    """
    path = filepath or PCAP_FIXTURE_PATH
    if not path.exists():
        logger.warning(f"PCAP fixture path {path} not found")
        return []

    records: List[Tuple[float, bytes]] = []
    try:
        with open(path, "rb") as f:
            header = f.read(24)
            if len(header) < 24:
                return []
            magic, maj, min_v, _, _, _, _ = struct.unpack("<IHHiIII", header)
            if magic not in (0xA1B2C3D4, 0xD4C3B2A1):
                logger.warning(f"Invalid PCAP magic: 0x{magic:08x}")
                return []

            is_little = (magic == 0xA1B2C3D4)
            endian = "<" if is_little else ">"

            while True:
                rec_hdr = f.read(16)
                if len(rec_hdr) < 16:
                    break
                ts_sec, ts_usec, caplen, _ = struct.unpack(f"{endian}IIII", rec_hdr)
                pkt_data = f.read(caplen)
                if len(pkt_data) < caplen:
                    break
                ts = ts_sec + (ts_usec / 1_000_000.0)
                records.append((ts, pkt_data))
    except Exception as e:
        logger.error(f"Error reading PCAP fixture {path}: {e}")

    return records


def load_authentic_fixture_packets(interface: str = "en0") -> List[Dict[str, Any]]:
    """
    Load and dissect all frames from authentic mesh_traffic.pcap.
    Returns list of canonical packet dictionaries.
    """
    raw_records = read_pcap_file()
    packets: List[Dict[str, Any]] = []
    prev_ts = None

    for i, (ts, raw_bytes) in enumerate(raw_records, start=1):
        pkt = dissect_packet(
            raw_bytes=raw_bytes,
            interface=interface,
            timestamp=ts,
            index=i,
            prev_timestamp=prev_ts,
        )
        packets.append(pkt)
        prev_ts = ts

    return packets
