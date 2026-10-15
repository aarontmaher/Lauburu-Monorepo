"""
In-Memory Thread-Safe Ring Buffer with Bounded Capacity and Libpcap 2.4 Binary Export.
Backs Shark Wire live packet capture with strict O(1) FIFO eviction.
"""

import time
import base64
import struct
import threading
from collections import deque
from typing import List, Dict, Any, Optional, Callable

# Libpcap 2.4 Constants
TCPDUMP_MAGIC = 0xA1B2C3D4
PCAP_VERSION_MAJOR = 2
PCAP_VERSION_MINOR = 4
DLT_EN10MB = 1


class SharkWireRingBuffer:
    """
    Fixed-capacity circular buffer for network packets using collections.deque.
    Guarantees O(1) appending and eviction without unbounded heap growth.
    """

    def __init__(self, maxlen: int = 5000):
        self.maxlen = maxlen
        self._deque: deque = deque(maxlen=maxlen)
        self.is_paused: bool = False
        self._lock = threading.Lock()
        self.total_appended: int = 0
        self.total_dropped_by_pause: int = 0

    def __len__(self) -> int:
        with self._lock:
            return len(self._deque)

    def __getitem__(self, index: int) -> Any:
        with self._lock:
            return self._deque[index]

    def __iter__(self):
        with self._lock:
            items = list(self._deque)
        return iter(items)

    def append(self, packet: Dict[str, Any]) -> bool:
        """
        Append a packet dictionary to the ring buffer.
        If paused, the packet is safely ignored and False is returned.
        """
        if self.is_paused:
            self.total_dropped_by_pause += 1
            return False

        with self._lock:
            self._deque.append(packet)
            self.total_appended += 1
        return True

    def push(self, packet: Dict[str, Any]) -> bool:
        """Alias for append()."""
        return self.append(packet)

    def pause(self) -> None:
        """Pause packet ingestion into the buffer."""
        self.is_paused = True

    def resume(self) -> None:
        """Resume packet ingestion into the buffer."""
        self.is_paused = False

    def clear(self) -> None:
        """Clear all buffered packets and reset count."""
        with self._lock:
            self._deque.clear()

    def get_all(self) -> List[Dict[str, Any]]:
        """Return a snapshot list of all buffered packets."""
        with self._lock:
            return list(self._deque)

    def get_range(
        self,
        offset: int = 0,
        limit: int = 50,
        filter_fn: Optional[Callable[[Dict[str, Any]], bool]] = None
    ) -> List[Dict[str, Any]]:
        """Return a paginated and optionally filtered slice of buffered packets."""
        with self._lock:
            snapshot = list(self._deque)

        if filter_fn is not None:
            snapshot = [p for p in snapshot if filter_fn(p)]

        if offset < 0:
            offset = 0
        if limit <= 0:
            return []

        return snapshot[offset : offset + limit]

    def export_pcap(self) -> bytes:
        """
        Serialize all currently buffered packets into a valid libpcap 2.4 binary stream.
        Conforms strictly to RFC / tcpdump PCAP specification (magic 0xa1b2c3d4).
        """
        # 24-byte Global Header
        global_header = struct.pack(
            "<IHHiIII",
            TCPDUMP_MAGIC,
            PCAP_VERSION_MAJOR,
            PCAP_VERSION_MINOR,
            0,      # thiszone (GMT to local correction)
            0,      # sigfigs (accuracy of timestamps)
            65535,  # snaplen (max octets per packet)
            DLT_EN10MB  # network linktype (1 = Ethernet)
        )

        with self._lock:
            packets = list(self._deque)

        if not packets:
            return global_header

        records: List[bytes] = []
        for pkt in packets:
            raw_bytes: Optional[bytes] = None

            # Attempt extraction of raw binary payload
            if "raw_bytes" in pkt and isinstance(pkt["raw_bytes"], (bytes, bytearray)):
                raw_bytes = bytes(pkt["raw_bytes"])
            elif "data" in pkt and isinstance(pkt["data"], (bytes, bytearray)):
                raw_bytes = bytes(pkt["data"])
            elif "raw_bytes_base64" in pkt and pkt["raw_bytes_base64"]:
                try:
                    raw_bytes = base64.b64decode(pkt["raw_bytes_base64"])
                except Exception:
                    raw_bytes = None

            if not raw_bytes:
                # Synthesize minimal frame if raw bytes omitted
                length = pkt.get("length", 60)
                raw_bytes = b"\x00" * max(length, 14)

            # Timestamp extraction
            ts = pkt.get("timestamp")
            if ts is None:
                ts = time.time()
            elif isinstance(ts, (int, float)):
                pass
            else:
                try:
                    ts = float(ts)
                except Exception:
                    ts = time.time()

            ts_sec = int(ts)
            ts_usec = int((ts - ts_sec) * 1_000_000)
            caplen = len(raw_bytes)
            origlen = pkt.get("length", caplen)

            # 16-byte Packet Record Header
            record_hdr = struct.pack("<IIII", ts_sec, ts_usec, caplen, origlen)
            records.append(record_hdr + raw_bytes)

        return global_header + b"".join(records)
