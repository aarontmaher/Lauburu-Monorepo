"""
Mesh Healer Protocol Specification & Stage 1 OOB Lifeline
Part of Canonical Mesh Fallback Terminal (bluetooth_terminal_ide).

Governs:
- Nordic UART Service (NUS) UUID specifications
- OOBMessage serialization / deserialization (\n delimited JSON-L)
- OOB command catalog (WOL, RESTART_DAEMON, CYCLE_NET, TELEMETRY_REQ, ENABLE_PAN, PING, PONG)
- NusStreamDeframer (64KB bounded buffer handling chunked BLE notifications)
- Paced MTU chunking logic (min(MTU - 3, 240) with 18ms pacing delay)
- Anti-Tunneling Guard barring interactive PTY/bulk traffic from Layer 0 BLE NUS
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Set, Union

# Nordic UART Service (NUS) UUIDs
NUS_SERVICE_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
NUS_RX_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"  # Central Write / Write Without Response
NUS_TX_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"  # Central Notify

# Pacing and MTU limits
DEFAULT_ATT_MTU = 23
MIN_CHUNK_SIZE = 20
MAX_CHUNK_SIZE = 240
PACING_DELAY_SECONDS = 0.018  # 18ms delay to avoid BLE controller FIFO overrun
MAX_NUS_PAYLOAD_SIZE = 512  # Anti-tunneling max payload limit for Layer 0 OOB
MAX_DEFRAMER_BUFFER_SIZE = 65536  # 64KB bounded buffer

# Catalog of permitted Out-of-Band (OOB) control commands
SUPPORTED_OOB_COMMANDS: Set[str] = {
    "WOL",
    "RESTART_DAEMON",
    "CYCLE_NET",
    "TELEMETRY_REQ",
    "ENABLE_PAN",
    "PING",
    "PONG",
}

# Patterns indicating forbidden interactive PTY or bulk tunnel traffic on Layer 0
FORBIDDEN_TUNNEL_PATTERNS = [
    b"/bin/sh",
    b"/bin/bash",
    b"/bin/zsh",
    b"mosh-server",
    b"SSH-2.0",
    b"\x1b[?1049h",  # Alternate screen buffer
    b"openpty",
]


@dataclass
class OOBMessage:
    """Out-of-band structured control message for Layer 0 BLE GATT NUS."""
    id: str
    cmd: str
    params: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def serialize(self) -> bytes:
        """Serializes message to a newline-terminated UTF-8 JSON-L byte string."""
        assert_not_tunneling(self.cmd)
        payload = {
            "id": self.id,
            "cmd": self.cmd,
            "params": self.params,
            "ts": self.timestamp,
        }
        raw = json.dumps(payload, separators=(",", ":")) + "\n"
        encoded = raw.encode("utf-8")
        assert_not_tunneling(encoded)
        return encoded

    @classmethod
    def deserialize(cls, data: Union[str, bytes]) -> Optional[OOBMessage]:
        """Safely parses a JSON-L string or bytes into an OOBMessage."""
        if isinstance(data, bytes):
            try:
                data = data.decode("utf-8", errors="replace")
            except Exception:
                return None
        
        data_clean = data.strip()
        if not data_clean:
            return None

        try:
            parsed = json.loads(data_clean)
            if not isinstance(parsed, dict):
                return None
            cmd = parsed.get("cmd")
            msg_id = parsed.get("id")
            if not cmd or not msg_id:
                return None
            
            params_raw = parsed.get("params")
            params = params_raw if isinstance(params_raw, dict) else {}
            return cls(
                id=str(msg_id),
                cmd=str(cmd),
                params=params,
                timestamp=float(parsed.get("ts", time.time())),
            )
        except Exception:
            return None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def validate_oob_command(cmd: str) -> bool:
    """Returns True if cmd is a recognized OOB control command."""
    return cmd.strip().upper() in SUPPORTED_OOB_COMMANDS


def calculate_chunk_size(mtu: Optional[int] = None) -> int:
    """
    Computes optimal chunk size based on BLE ATT MTU.
    Formula: chunk_size = max(20, min(mtu - 3, 240)).
    """
    if mtu is None or mtu < DEFAULT_ATT_MTU:
        return MIN_CHUNK_SIZE
    payload_room = mtu - 3
    return max(MIN_CHUNK_SIZE, min(payload_room, MAX_CHUNK_SIZE))


def chunk_payload(payload: bytes, chunk_size: int) -> List[bytes]:
    """Slices payload into byte chunks strictly bounded by chunk_size."""
    if chunk_size <= 0:
        chunk_size = MIN_CHUNK_SIZE
    return [payload[i : i + chunk_size] for i in range(0, len(payload), chunk_size)]


def is_tunneling_payload(data: Union[bytes, str]) -> bool:
    """
    Anti-Tunneling Guard check.
    Returns True if data exceeds 512 bytes or contains forbidden interactive PTY/bulk tokens.
    """
    raw_bytes = data.encode("utf-8") if isinstance(data, str) else data
    if len(raw_bytes) > MAX_NUS_PAYLOAD_SIZE:
        return True
    for pattern in FORBIDDEN_TUNNEL_PATTERNS:
        if pattern in raw_bytes:
            return True
    return False


def assert_not_tunneling(data: Union[bytes, str]) -> None:
    """Raises ValueError if payload violates Anti-Tunneling Guard constraints."""
    if is_tunneling_payload(data):
        raw_len = len(data) if isinstance(data, bytes) else len(data.encode("utf-8"))
        raise ValueError(
            f"Anti-Tunneling Guard: Interactive PTY or bulk payload rejected on Layer 0 BLE NUS "
            f"(Size: {raw_len}B, Max: {MAX_NUS_PAYLOAD_SIZE}B). Trigger Stage 2 Bluetooth PAN instead."
        )


class NusStreamDeframer:
    """
    64KB bounded stream buffer parsing line-delimited JSON-L frames from BLE notifications.
    Prevents message corruption caused by multi-chunk BLE notifications.
    """

    def __init__(self, max_buffer_size: int = MAX_DEFRAMER_BUFFER_SIZE) -> None:
        self.max_buffer_size = max_buffer_size
        self.buffer = bytearray()

    def feed(self, chunk: Union[bytes, bytearray]) -> List[str]:
        """
        Ingests incoming BLE notification bytes, splits on newline delimiters,
        and returns all complete string frames. Preserves trailing partial fragments.
        """
        if not chunk:
            return []

        # Enforce bounded buffer limit to prevent unbounded memory growth
        if len(chunk) >= self.max_buffer_size:
            self.buffer.clear()
            chunk = chunk[-self.max_buffer_size :]
        elif len(self.buffer) + len(chunk) > self.max_buffer_size:
            overflow = (len(self.buffer) + len(chunk)) - self.max_buffer_size
            del self.buffer[:overflow]

        self.buffer.extend(chunk)

        frames: List[str] = []
        while b"\n" in self.buffer:
            idx = self.buffer.index(b"\n")
            line_bytes = self.buffer[:idx]
            del self.buffer[: idx + 1]

            decoded = line_bytes.decode("utf-8", errors="replace").strip()
            if decoded:
                frames.append(decoded)

        return frames

    def clear(self) -> None:
        """Clears all buffered bytes."""
        self.buffer.clear()

    @property
    def buffered_bytes(self) -> int:
        """Returns the current number of bytes waiting in the buffer."""
        return len(self.buffer)
