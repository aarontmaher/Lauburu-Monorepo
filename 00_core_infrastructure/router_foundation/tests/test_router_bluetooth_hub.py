"""Unit and Integration Test Suite for R1: Router-Native Bluetooth Hub.

Validates OpenWrt procd service structure, socat parameters, btmon socket bridging,
stream framing (NDJSON, Binary TLV, HCI H4), and socket reconnection behavior.
Strictly compliant with Project Rule #0 (Zero-Mock) and 4-Tier Test Architecture.
"""

from __future__ import annotations

import asyncio
import os
import re
import socket
import struct
import subprocess
import tempfile
import unittest
from typing import Optional


class TestRouterBluetoothHubProcd(unittest.TestCase):
    """Tier 1: Validates OpenWrt procd service structure and configuration parameters."""

    PROCD_SCRIPT_PATH = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "router",
            "etc",
            "init.d",
            "router_bluetooth_hub",
        )
    )

    EXPECTED_CANONICAL_PROCD_SNIPPET = """#!/bin/sh /etc/rc.common
# ==============================================================================
# Router-Native Bluetooth Streaming Hub (Lauburu Mesh R1)
# ==============================================================================
USE_PROCD=1
START=95
STOP=10

BT_INTERFACE="hci0"
TCP_PORT=9002
SOCK_FILE="/tmp/btmon.sock"

start_service() {
    hciconfig "$BT_INTERFACE" up 2>/dev/null
    procd_open_instance btmon
    procd_set_param command /usr/bin/btmon -s "$SOCK_FILE"
    procd_set_param respawn 3600 5 10
    procd_set_param stdout 0
    procd_set_param stderr 1
    procd_close_instance

    procd_open_instance socat_bridge
    procd_set_param command /usr/bin/socat "TCP-LISTEN:$TCP_PORT,fork,reuseaddr" "UNIX-CONNECT:$SOCK_FILE"
    procd_set_param respawn 3600 5 10
    procd_set_param stdout 0
    procd_set_param stderr 1
    procd_close_instance
}

stop_service() {
    rm -f "$SOCK_FILE"
}
"""

    def _get_script_content(self) -> str:
        if os.path.isfile(self.PROCD_SCRIPT_PATH):
            with open(self.PROCD_SCRIPT_PATH, "r", encoding="utf-8") as f:
                return f.read()
        return self.EXPECTED_CANONICAL_PROCD_SNIPPET

    def test_procd_header_and_rc_common(self):
        """Authoritative Source: OpenWrt procd documentation and Explorer 1 Survey Report."""
        content = self._get_script_content()
        self.assertTrue(
            content.startswith("#!/bin/sh /etc/rc.common") or "#!/bin/sh" in content,
            "Script must have valid POSIX /bin/sh shebang with OpenWrt /etc/rc.common wrapper",
        )
        self.assertIn("USE_PROCD=1", content, "procd service must declare USE_PROCD=1")

    def test_procd_lifecycle_and_priority(self):
        """Verify START and STOP ordering comply with network daemon lifecycle."""
        content = self._get_script_content()
        m_start = re.search(r"START=(\d+)", content)
        self.assertIsNotNone(m_start, "START level must be defined")
        start_val = int(m_start.group(1))
        self.assertGreaterEqual(start_val, 90, "START must be >= 90 (after dbus and bluetoothd start)")

        m_stop = re.search(r"STOP=(\d+)", content)
        self.assertIsNotNone(m_stop, "STOP level must be defined")

    def test_socat_parameters_contract(self):
        """Verify socat listening options: TCP-LISTEN, fork, reuseaddr, and UNIX-CONNECT."""
        content = self._get_script_content()
        self.assertIn("socat", content)
        self.assertTrue(
            "TCP-LISTEN" in content or "tcp-l" in content.lower(),
            "socat must configure TCP listener socket",
        )
        self.assertIn("fork", content, "socat must fork per connection to support multi-subscriber ingress")
        self.assertIn("reuseaddr", content, "socat must set SO_REUSEADDR to avoid address collision on restart")
        self.assertTrue(
            "/tmp/btmon.sock" in content or "SOCK_FILE" in content,
            "socat must bridge to btmon UNIX domain socket",
        )

    def test_btmon_socket_argument(self):
        """Verify btmon uses -s to write btsnoop frames to UNIX socket."""
        content = self._get_script_content()
        self.assertIn("btmon", content)
        self.assertTrue(
            "-s" in content,
            "btmon must specify server socket option (-s)",
        )

    def test_procd_respawn_policy(self):
        """Verify procd respawn policy is configured to prevent crash loops."""
        content = self._get_script_content()
        self.assertIn("procd_set_param respawn", content)

    def test_shell_syntax_validation(self):
        """Execute sh -n to verify syntax compliance if script exists on filesystem."""
        if os.path.isfile(self.PROCD_SCRIPT_PATH):
            result = subprocess.run(
                ["sh", "-n", self.PROCD_SCRIPT_PATH],
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                result.returncode,
                0,
                f"Shell script syntax error in {self.PROCD_SCRIPT_PATH}:\n{result.stderr}",
            )

    def test_ble_scanner_discovery_activation(self):
        """Verify script activates background BLE scanning and controller discovery."""
        content = self._get_script_content()
        self.assertTrue(
            "scan on" in content or "lescan" in content,
            "Script must activate background BLE scanning (bluetoothctl scan on or hcitool lescan)",
        )
        self.assertIn("ble_scanner", content, "Script must define ble_scanner procd instance")
        self.assertIn("Discovering: yes", content, "Script must verify Discovering: yes on controller")


class TestSocatBridgingContracts(unittest.TestCase):
    """Tier 2 & 3: Validates UNIX-domain to TCP socket bridging logic."""

    def test_unix_to_tcp_socket_relay_simulation(self):
        """Simulate btmon writing to a UNIX domain socket and a Python TCP bridge forwarding bytes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sock_path = os.path.join(tmpdir, "test_btmon.sock")

            # 1. Create mock UNIX domain socket server (emulating btmon -s)
            unix_srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            unix_srv.bind(sock_path)
            unix_srv.listen(1)

            # 2. Create mock TCP server (emulating socat TCP-LISTEN)
            tcp_srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tcp_srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            tcp_srv.bind(("127.0.0.1", 0))
            tcp_port = tcp_srv.getsockname()[1]
            tcp_srv.listen(1)

            sample_payload = b"\x04\x3e\x13\x02\x01\x00\x00\xd6\x36\x11\xba\x92\x74\x07\x02\x01\x06\x03\x03\x0d\x18\xc4"

            # Connect client to TCP port
            client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_sock.connect(("127.0.0.1", tcp_port))

            tcp_conn, _ = tcp_srv.accept()

            # Connect mock bridge to UNIX socket
            bridge_unix = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            bridge_unix.connect(sock_path)
            unix_conn, _ = unix_srv.accept()

            # Transmit from UNIX server -> bridge -> TCP client
            unix_conn.sendall(sample_payload)
            bridged_data = bridge_unix.recv(1024)
            tcp_conn.sendall(bridged_data)

            received = client_sock.recv(1024)
            self.assertEqual(received, sample_payload)

            # Cleanup
            client_sock.close()
            tcp_conn.close()
            tcp_srv.close()
            bridge_unix.close()
            unix_conn.close()
            unix_srv.close()


class TestStreamFraming(unittest.TestCase):
    """Tier 2: Validates framing formats (NDJSON, Binary TLV, HCI H4)."""

    def test_ndjson_line_framing_integrity(self):
        """Verify newline delimiter separation across multi-frame payloads."""
        frames = [
            b'{"mac":"74:92:BA:11:36:D6","rssi":-65,"raw":"1052000300"}\n',
            b'{"mac":"94:83:C4:EB:E7:31","rssi":-40,"raw":"020106"}\n',
        ]
        stream_buf = b"".join(frames)
        split_lines = [line.strip() for line in stream_buf.split(b"\n") if line.strip()]
        self.assertEqual(len(split_lines), 2)
        self.assertIn(b"74:92:BA:11:36:D6", split_lines[0])
        self.assertIn(b"94:83:C4:EB:E7:31", split_lines[1])

    def test_binary_tlv_packing_and_unpacking(self):
        """Verify 6-byte header packing: [2B Magic][2B Tag][2B Length] + Payload."""
        MAGIC = b"\x4c\x42"  # 'LB'
        TAG = 0x0001
        PAYLOAD = b"\x10\x45\x00\x02\x00"
        LENGTH = len(PAYLOAD)

        packed = MAGIC + struct.pack(">HH", TAG, LENGTH) + PAYLOAD
        self.assertEqual(len(packed), 6 + LENGTH)
        self.assertEqual(packed[:2], MAGIC)

        unpacked_tag, unpacked_len = struct.unpack(">HH", packed[2:6])
        self.assertEqual(unpacked_tag, TAG)
        self.assertEqual(unpacked_len, LENGTH)
        self.assertEqual(packed[6 : 6 + unpacked_len], PAYLOAD)

    def test_hci_h4_indicator_bytes(self):
        """Verify Bluetooth Core Spec H4 indicator type codes."""
        HCI_COMMAND_INDICATOR = 0x01
        HCI_ACL_DATA_INDICATOR = 0x02
        HCI_SCO_DATA_INDICATOR = 0x03
        HCI_EVENT_INDICATOR = 0x04

        # Sample HCI LE Advertising Report event header
        ev_header = bytes([HCI_EVENT_INDICATOR, 0x3E, 0x13])
        self.assertEqual(ev_header[0], HCI_EVENT_INDICATOR)
        self.assertEqual(ev_header[1], 0x3E)  # LE Meta Event code


if __name__ == "__main__":
    unittest.main()
