"""
Unit Tests for Mesh Healer Protocol, OOB Framing, Deframer, and Anti-Tunneling Guard.
Adheres strictly to Cardinal Rule #0: 0 mock imports, authentic data flows.
"""

import sys
from pathlib import Path
import pytest

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mesh_healer.protocol import (
    NUS_RX_UUID,
    NUS_SERVICE_UUID,
    NUS_TX_UUID,
    NusStreamDeframer,
    OOBMessage,
    assert_not_tunneling,
    calculate_chunk_size,
    chunk_payload,
    is_tunneling_payload,
    validate_oob_command,
)


def test_oob_message_serialization_deserialization():
    """Verifies round-trip JSON-L serialization without field loss or delimiter corruption."""
    msg = OOBMessage(
        id="oob_test_01",
        cmd="ENABLE_PAN",
        params={"subnet": "192.168.44.0/24", "stage": 2},
        timestamp=1726600000.5,
    )
    raw_bytes = msg.serialize()
    assert raw_bytes.endswith(b"\n")
    assert b"ENABLE_PAN" in raw_bytes

    parsed = OOBMessage.deserialize(raw_bytes)
    assert parsed is not None
    assert parsed.id == "oob_test_01"
    assert parsed.cmd == "ENABLE_PAN"
    assert parsed.params["subnet"] == "192.168.44.0/24"
    assert parsed.params["stage"] == 2
    assert parsed.timestamp == 1726600000.5


def test_oob_message_deserialize_null_and_malformed_params():
    """
    Verifies that OOBMessage.deserialize safely coerces null, omitted,
    or non-dict 'params' fields into an empty dictionary ({}), preserving
    the Dict[str, Any] contract and preventing downstream AttributeErrors.
    """
    # 1. Explicit null params
    payload_null = '{"id": "null_p", "cmd": "PING", "params": null}\n'
    msg_null = OOBMessage.deserialize(payload_null)
    assert msg_null is not None
    assert msg_null.id == "null_p"
    assert msg_null.cmd == "PING"
    assert msg_null.params == {}
    assert isinstance(msg_null.params, dict)
    assert msg_null.params.get("anything", "default") == "default"

    # 2. Omitted params
    payload_omitted = '{"id": "omit_p", "cmd": "WOL"}\n'
    msg_omitted = OOBMessage.deserialize(payload_omitted)
    assert msg_omitted is not None
    assert msg_omitted.params == {}
    assert isinstance(msg_omitted.params, dict)

    # 3. Non-dict primitives (list, string, int, boolean)
    for invalid_params in ["[1, 2, 3]", '"string_val"', "12345", "true", "false"]:
        payload_invalid = f'{{"id": "bad_p", "cmd": "PING", "params": {invalid_params}}}\n'
        msg_invalid = OOBMessage.deserialize(payload_invalid)
        assert msg_invalid is not None
        assert msg_invalid.params == {}
        assert isinstance(msg_invalid.params, dict)

    # 4. Valid dict params preserved intact
    payload_valid = '{"id": "valid_p", "cmd": "CYCLE_NET", "params": {"interface": "wlan0", "delay": 5}}\n'
    msg_valid = OOBMessage.deserialize(payload_valid)
    assert msg_valid is not None
    assert msg_valid.params == {"interface": "wlan0", "delay": 5}
    assert msg_valid.params.get("interface") == "wlan0"


def test_oob_command_catalog_validation():
    """Verifies supported OOB command catalog recognition and rejection of illegal commands."""
    supported = ["WOL", "RESTART_DAEMON", "CYCLE_NET", "TELEMETRY_REQ", "ENABLE_PAN", "PING", "PONG"]
    for cmd in supported:
        assert validate_oob_command(cmd) is True
        assert validate_oob_command(cmd.lower()) is True

    unsupported = ["SHELL_EXEC", "BASH_INTERACTIVE", "RM_RF", "OPEN_SOCKET"]
    for cmd in unsupported:
        assert validate_oob_command(cmd) is False


def test_deframer_multi_chunk_assembly():
    """Verifies that split BLE notifications across packet boundaries reassemble cleanly without stream tearing."""
    deframer = NusStreamDeframer(max_buffer_size=1024)

    # Frame 1 split across two chunks
    msg1_part1 = b'{"id":"m1","cmd":"PING"'
    msg1_part2 = b',"ts":1.0}\n'

    # Frame 2 complete
    msg2 = b'{"id":"m2","cmd":"PONG","ts":2.0}\n'

    # Frame 3 split
    msg3_part1 = b'{"id":"m3","cmd":"WOL"'
    msg3_part2 = b',"params":{"mac":"AA:BB:CC"}}\n'

    frames1 = deframer.feed(msg1_part1)
    assert frames1 == []  # Incomplete frame
    assert deframer.buffered_bytes == len(msg1_part1)

    frames2 = deframer.feed(msg1_part2 + msg2 + msg3_part1)
    assert len(frames2) == 2
    assert "PING" in frames2[0]
    assert "PONG" in frames2[1]

    frames3 = deframer.feed(msg3_part2)
    assert len(frames3) == 1
    assert "WOL" in frames3[0]
    assert deframer.buffered_bytes == 0


def test_deframer_buffer_overflow_protection():
    """Verifies that un-delimited streams are bounded to 64KB to prevent memory exhaustion."""
    max_buf = 512
    deframer = NusStreamDeframer(max_buffer_size=max_buf)

    # Feed 1000 bytes with no newline
    junk = b"X" * 1000
    frames = deframer.feed(junk)
    assert frames == []
    assert deframer.buffered_bytes <= max_buf


def test_mtu_chunking_formula():
    """Verifies dynamic MTU-aware payload chunk calculation."""
    # Under-spec or unnegotiated MTUs
    assert calculate_chunk_size(None) == 20
    assert calculate_chunk_size(15) == 20
    assert calculate_chunk_size(23) == 20  # 23 - 3 = 20

    # Intermediate MTUs
    assert calculate_chunk_size(64) == 61  # 64 - 3 = 61
    assert calculate_chunk_size(185) == 182  # 185 - 3 = 182

    # Upper bound cap (240 bytes)
    assert calculate_chunk_size(243) == 240
    assert calculate_chunk_size(512) == 240  # Capped at 240


def test_chunk_payload_slicing():
    """Verifies byte slicing into chunks of exact size."""
    payload = b"0123456789" * 10  # 100 bytes
    chunks = chunk_payload(payload, 30)
    assert len(chunks) == 4
    assert len(chunks[0]) == 30
    assert len(chunks[1]) == 30
    assert len(chunks[2]) == 30
    assert len(chunks[3]) == 10
    assert b"".join(chunks) == payload


def test_anti_tunneling_guard_size_and_content():
    """Verifies that large bulk data and interactive PTY payloads are strictly barred on Layer 0."""
    # Valid small OOB control
    safe_data = b'{"cmd":"WOL","mac":"11:22:33:44:55:66"}'
    assert is_tunneling_payload(safe_data) is False
    assert_not_tunneling(safe_data)

    # Payload exceeding 512 bytes
    large_bulk = b"A" * 513
    assert is_tunneling_payload(large_bulk) is True
    with pytest.raises(ValueError, match="Anti-Tunneling Guard"):
        assert_not_tunneling(large_bulk)

    # Interactive PTY or shell forbidden signatures
    shell_attempt = b'{"cmd":"EXEC","path":"/bin/bash -i"}'
    assert is_tunneling_payload(shell_attempt) is True
    with pytest.raises(ValueError, match="Anti-Tunneling Guard"):
        assert_not_tunneling(shell_attempt)

    pty_attempt = b"\x1b[?1049hWelcome to Interactive Terminal"
    assert is_tunneling_payload(pty_attempt) is True
    with pytest.raises(ValueError, match="Anti-Tunneling Guard"):
        assert_not_tunneling(pty_attempt)
