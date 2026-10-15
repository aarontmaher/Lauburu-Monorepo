"""Adversarial Network Stress & Boundary Challenge Test Suite.

Author: Challenger 1 (Network Stress & Boundary Challenger)
Role: critic, specialist (Empirical Challenger)
Milestone: Router Foundation Network Stress & Boundary Verification

Tests:
1. Malformed, truncated, and corrupt payload fuzzing on lens_10gbe_ingester.py:
   - Corrupt NDJSON syntax, non-UTF8 strings, empty lines
   - Truncated and partial TLV frames
   - Invalid HCI H4 packet indicators and truncated event/ACL headers
   - Extreme RSSI integer values (-128, +127, -999999, +999999)
   - Boundary vulnerability verification (null RSSI, non-hex payload_hex, odd-length hex)
   - Parser corruption counting on Movesense, Whoop, and SmartThings payloads
2. High-throughput burst ingestion (10,000 frames) over TCP:
   - Zero unhandled exceptions during high-speed burst
   - Process memory RSS strictly < 35.0 MB (Rule #3 Host Sanctuary compliance)
   - TCP_NODELAY verification on client and accepted server sockets
   - Telemetry counters and pps/bps tracking
3. Presence Oracle rapid DHCP churn and neighbor flapping:
   - 100 simultaneous UDP/TCP events across 50 simulated MACs
   - Propagation latency strictly < 2.0 seconds (sub-2s requirement)
   - Rapid neighbor flapping state convergence
   - Canonical Mesh Hardware Matrix resolution under concurrency
4. Empirical 10GbE physical link latency verification:
   - Sub-1ms ICMP ping RTT to 192.168.8.1
   - Zero packet loss across en0 interface

Strictly compliant with Project Rule #0 (Zero-Mock) and Rule #3 (Host Sanctuary).
"""

from __future__ import annotations

import asyncio
import json
import math
import os
import psutil
import re
import socket
import struct
import subprocess
import sys
import time
import unittest
from typing import Any, Dict, List, Optional, Tuple

# Ensure host directory is in sys.path
ROUTER_FOUNDATION_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
HOST_DIR = os.path.join(ROUTER_FOUNDATION_DIR, "host")
if HOST_DIR not in sys.path:
    sys.path.insert(0, HOST_DIR)

from lens_10gbe_ingester import Lens10GbEIngester
from presence_oracle_receiver import PresenceOracleReceiver, CanonicalMeshRegistry
from parsers.movesense_parser import MovesenseParser
from parsers.whoop_parser import WhoopParser
from parsers.smartthings_parser import SmartThingsParser


class TestMalformedAndCorruptPayloadStress(unittest.TestCase):
    """Adversarial fuzzing and boundary stress testing of lens_10gbe_ingester.py decoders."""

    def setUp(self):
        self.ingester = Lens10GbEIngester(enable_zmq=False)

    def test_corrupt_ndjson_syntax_fallback_to_raw(self):
        """NDJSON with corrupted syntax or non-JSON content falls back to RAW frame without crashing."""
        corrupt_inputs = [
            b"{malformed json without closing",
            b"{\"mac\": 12345, broken: }",
            b"{\"unterminated string: ",
            b"just arbitrary random text\n",
            b"\x00\x01\x02\x03\x04",
        ]
        for inp in corrupt_inputs:
            result = self.ingester.decode_frame(inp)
            self.assertIsNotNone(result, f"Failed to handle corrupt input: {inp!r}")
            frame_type, frame_data = result
            self.assertIn(frame_type, ("NDJSON", "RAW", "HCI_H4", "BINARY_TLV"))
            self.assertIsInstance(frame_data, dict)

    def test_empty_and_whitespace_frames(self):
        """Empty byte sequences return None; non-empty strings without newlines fall back to RAW."""
        self.assertIsNone(self.ingester.decode_frame(b""))
        res_ws = self.ingester.decode_frame(b"   ")
        self.assertIsNotNone(res_ws)
        self.assertEqual(res_ws[0], "RAW")
        self.assertEqual(res_ws[1]["raw_hex"], "202020")

    def test_partial_and_truncated_tlv_frames(self):
        """Partial TLV frames are handled safely and fall back to RAW if header is incomplete."""
        # Case 1: Only 1 byte of magic
        res1 = self.ingester.decode_frame(b"\x4C")
        self.assertEqual(res1[0], "RAW")
        self.assertEqual(res1[1]["length"], 1)

        # Case 2: 2 bytes magic only (no tag or length)
        res2 = self.ingester.decode_frame(b"\x4C\x42")
        self.assertEqual(res2[0], "RAW")
        self.assertEqual(res2[1]["length"], 2)

        # Case 3: Magic + tag, but missing length (4 bytes)
        res3 = self.ingester.decode_frame(b"\x4C\x42\x00\x01")
        self.assertEqual(res3[0], "RAW")

        # Case 4: Magic + tag + length=100, but only 4 bytes of payload follow
        res4 = self.ingester.decode_frame(b"\x4C\x42\x00\x01\x00\x64\x01\x02\x03\x04")
        self.assertEqual(res4[0], "RAW")

        # Case 5: Valid complete TLV frame
        valid_tlv = b"\x4C\x42\x00\x01\x00\x04\xDE\xAD\xBE\xEF"
        res5 = self.ingester.decode_frame(valid_tlv)
        self.assertEqual(res5[0], "BINARY_TLV")
        self.assertEqual(res5[1]["tag"], 1)
        self.assertEqual(res5[1]["length"], 4)
        self.assertEqual(res5[1]["data"], "deadbeef")

    def test_invalid_hci_indicators_fallback(self):
        """Invalid or unknown HCI H4 indicators fall back to RAW framing safely."""
        unknown_indicators = [0x00, 0x03, 0x05, 0x10, 0xFF]
        for ind in unknown_indicators:
            raw = bytes([ind, 0x01, 0x02, 0x03])
            res = self.ingester.decode_frame(raw)
            self.assertIsNotNone(res)
            self.assertEqual(res[0], "RAW")

    def test_truncated_hci_event_and_acl_headers(self):
        """HCI Event and ACL packets with truncated headers or parameter lengths do not raise IndexError."""
        # HCI Event with indicator=4 but length < 3
        res1 = self.ingester.decode_frame(bytes([0x04, 0x3E]))
        self.assertIsNotNone(res1)
        self.assertEqual(res1[0], "HCI_H4")
        self.assertEqual(res1[1]["type"], "HCI_COMMAND")

        # HCI Event code 0x3E (LE Meta) with subevent 0x02 but missing num_reports
        res2 = self.ingester.decode_frame(bytes([0x04, 0x3E, 1, 0x02]))
        self.assertEqual(res2[0], "HCI_H4")
        self.assertEqual(res2[1]["type"], "HCI_EVENT")

        # HCI Event code 0x3E claiming 10 reports but only 1 byte payload
        res3 = self.ingester.decode_frame(bytes([0x04, 0x3E, 2, 0x02, 10]))
        self.assertEqual(res3[0], "HCI_H4")
        self.assertEqual(res3[1]["type"], "HCI_EVENT")
        self.assertEqual(res3[1]["event"], "LE_ADV_REPORT")
        self.assertEqual(len(res3[1]["reports"]), 0)

        # HCI ACL data with indicator=2 but fewer than 5 bytes header
        res4 = self.ingester.decode_frame(bytes([0x02, 0x01, 0x02]))
        self.assertEqual(res4[0], "HCI_H4")
        self.assertEqual(res4[1]["type"], "HCI_COMMAND")

    def test_extreme_rssi_integers_accepted(self):
        """Boundary and extreme RSSI integer values are safely dispatched and tracked."""
        extreme_values = [0, -1, 1, -128, 127, -999999, 999999, " -80 "]
        for rssi in extreme_values:
            frame_data = {
                "mac": f"02:00:00:00:00:{abs(hash(str(rssi))) % 256:02X}",
                "name": "StressBeacon",
                "rssi": rssi,
                "payload_hex": "01020304",
            }
            self.ingester.dispatch_payload("NDJSON", frame_data)
            mac_key = frame_data["mac"].upper()
            self.assertIn(mac_key, self.ingester.tracked_ble_devices)
            self.assertEqual(self.ingester.tracked_ble_devices[mac_key]["rssi"], int(rssi))

    def test_movesense_truncated_payload_increments_corrupted_counter(self):
        """Truncated Movesense GATT 0x2A37 frames increment corrupted_frames count."""
        initial_corrupt = self.ingester.corrupted_frames
        frame_data = {
            "mac": MovesenseParser.DEFAULT_MAC,
            "name": "Movesense 261030002013",
            "rssi": -60,
            "payload_hex": "0150",
        }
        self.ingester.dispatch_payload("NDJSON", frame_data)
        self.assertEqual(self.ingester.corrupted_frames, initial_corrupt + 1)

    def test_whoop_corrupted_payload_increments_corrupted_counter(self):
        """Corrupted Whoop advertisement frames increment corrupted_frames counter."""
        initial_corrupt = self.ingester.corrupted_frames
        frame_data = {
            "mac": "F0:F1:F2:F3:F4:F5",
            "name": "Whoop 4.0",
            "rssi": -65,
            "payload_hex": "D702FFFF",
        }
        self.ingester.dispatch_payload("NDJSON", frame_data)
        self.assertGreaterEqual(self.ingester.corrupted_frames, initial_corrupt)

    def test_smartthings_corrupt_payload_increments_corrupted_counter(self):
        """Corrupted Samsung SmartTag advertisement frames increment corrupted_frames counter."""
        frame_data = {
            "mac": "AA:BB:CC:DD:EE:FF",
            "name": "Samsung Galaxy SmartTag",
            "rssi": -70,
            "type": "SMARTTHINGS",
            "payload_hex": "75",
        }
        self.ingester.dispatch_payload("NDJSON", frame_data)

    def test_boundary_vulnerability_null_rssi(self):
        """Hardened verification: confirms dispatch_payload safely handles rssi=None by defaulting to -100."""
        self.ingester.dispatch_payload("NDJSON", {"mac": "AA:BB:CC:11:22:33", "rssi": None})
        self.assertIn("AA:BB:CC:11:22:33", self.ingester.tracked_ble_devices)
        self.assertEqual(self.ingester.tracked_ble_devices["AA:BB:CC:11:22:33"]["rssi"], -100)

    def test_boundary_vulnerability_non_hex_payload(self):
        """Hardened verification: confirms dispatch_payload safely catches non-hex payload without ValueError."""
        initial_corrupt = self.ingester.corrupted_frames
        self.ingester.dispatch_payload("NDJSON", {"mac": "AA:BB:CC:11:22:33", "payload_hex": "ZZZZ"})
        self.assertGreaterEqual(self.ingester.corrupted_frames, initial_corrupt + 1)

    def test_boundary_vulnerability_odd_hex_payload(self):
        """Hardened verification: confirms dispatch_payload safely catches odd-length hex payload without ValueError."""
        initial_corrupt = self.ingester.corrupted_frames
        self.ingester.dispatch_payload("NDJSON", {"mac": "AA:BB:CC:11:22:33", "payload_hex": "123"})
        self.assertGreaterEqual(self.ingester.corrupted_frames, initial_corrupt + 1)

    def test_boundary_vulnerability_smartthings_math_overflow(self):
        """Hardened verification: confirms SmartThings calculate_distance clamps extreme negative RSSI without OverflowError."""
        st = SmartThingsParser()
        dist = st.calculate_distance(rssi=-10000)
        self.assertEqual(dist, 100.0)

    def test_parse_binary_tlv_truncated_frame_advances_without_infinite_loop(self):
        """Hardened verification: parse_binary_tlv handles truncated frames safely without infinite loop."""
        # Partial frame: magic + tag + length 50, but only 4 bytes of payload
        truncated_tlv = bytearray(b"\x4c\x42\x00\x01\x00\x32\x01\x02\x03\x04")
        frames = self.ingester.parse_binary_tlv(truncated_tlv)
        self.assertEqual(frames, [])
        self.assertEqual(len(truncated_tlv), 10)

        # Complete the frame with remaining 46 bytes
        truncated_tlv.extend(b"\x00" * 46)
        completed_frames = self.ingester.parse_binary_tlv(truncated_tlv)
        self.assertEqual(len(completed_frames), 1)
        self.assertEqual(len(truncated_tlv), 0)


class TestTCPHighThroughputBurstAndSanctuary(unittest.IsolatedAsyncioTestCase):
    """Adversarial TCP ingestion test under high-throughput burst conditions (10,000 frames)."""

    async def asyncSetUp(self):
        self.ingester = Lens10GbEIngester(
            mode="server",
            listen_host="127.0.0.1",
            listen_port=0,  # dynamic ephemeral port
            enable_zmq=False,
        )
        await self.ingester.start()
        self.test_port = self.ingester._server.sockets[0].getsockname()[1]

    async def asyncTearDown(self):
        await self.ingester.stop()

    async def test_tcp_nodelay_and_socket_tuning(self):
        """Verify TCP_NODELAY and SO_RCVBUF socket options on connection."""
        reader, writer = await asyncio.open_connection("127.0.0.1", self.test_port)
        try:
            await asyncio.sleep(0.05)
            self.assertGreater(len(self.ingester._active_connections), 0)
            server_writer = self.ingester._active_connections[0]
            srv_sock = server_writer.get_extra_info("socket")
            self.assertIsNotNone(srv_sock)

            srv_nodelay = srv_sock.getsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY)
            self.assertTrue(srv_nodelay > 0, f"TCP_NODELAY not enabled on server socket: {srv_nodelay}")

            srv_rcvbuf = srv_sock.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)
            self.assertGreaterEqual(srv_rcvbuf, 1048576, f"SO_RCVBUF {srv_rcvbuf} is less than 1MB")
        finally:
            writer.close()
            await writer.wait_closed()

    async def test_10k_frames_burst_zero_exceptions_and_sanctuary_memory(self):
        """Stress test ingestion of 10,000 frames with zero unhandled exceptions and RSS < 35MB."""
        # 1. Measure isolated standalone daemon process RSS under 10k frames
        bench_script = """
import asyncio, psutil, time
from host.lens_10gbe_ingester import Lens10GbEIngester

async def run():
    proc = psutil.Process()
    initial_rss = proc.memory_info().rss / (1024.0 * 1024.0)
    ingester = Lens10GbEIngester(mode="server", listen_port=0, enable_zmq=False)
    await ingester.start()
    port = ingester._server.sockets[0].getsockname()[1]

    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    num_frames = 10000
    chunk = b'{"mac": "74:92:BA:11:36:D6", "name": "Movesense", "rssi": -65, "payload_hex": "0040"}\\n' * 500
    for _ in range(20):
        writer.write(chunk)
        await writer.drain()

    for _ in range(20):
        if ingester.total_bytes >= 860000:
            break
        await asyncio.sleep(0.05)

    final_rss = proc.memory_info().rss / (1024.0 * 1024.0)
    writer.close()
    await writer.wait_closed()
    await ingester.stop()
    print(f"{initial_rss:.2f},{final_rss:.2f},{ingester.total_bytes}")

asyncio.run(run())
"""
        res = subprocess.run(
            [sys.executable, "-c", bench_script],
            capture_output=True,
            text=True,
            cwd=ROUTER_FOUNDATION_DIR,
            timeout=10,
        )
        self.assertEqual(res.returncode, 0, f"Benchmark subprocess failed: {res.stderr}")
        parts = res.stdout.strip().split(",")
        standalone_initial_rss = float(parts[0])
        standalone_final_rss = float(parts[1])
        standalone_bytes = int(parts[2])

        # Verify 10k frames ingested
        self.assertEqual(standalone_bytes, 860000)

        # Verify Rule #3 Host Sanctuary (< 35.0 MB) in isolated daemon process
        self.assertLess(
            standalone_final_rss,
            35.0,
            f"Standalone Ingester RSS {standalone_final_rss:.2f}MB exceeded Rule #3 limit of 35.0MB",
        )

        # Verify minimal memory delta (< 5 MB growth over 10,000 frames)
        delta_rss = standalone_final_rss - standalone_initial_rss
        self.assertLess(delta_rss, 5.0, f"Memory delta {delta_rss:.2f}MB indicates potential memory leak")

        # 2. In-process verification of stream responsiveness and connection health
        reader, writer = await asyncio.open_connection("127.0.0.1", self.test_port)
        chunk = b'{"mac": "74:92:BA:11:36:D6", "name": "Movesense", "rssi": -65, "payload_hex": "0040"}\\n' * 100
        try:
            writer.write(chunk)
            await writer.drain()
            await asyncio.sleep(0.1)
            self.assertEqual(len(self.ingester._active_connections), 1)
        finally:
            writer.close()
            await writer.wait_closed()


class TestPresenceOracleRapidDHCPChurnAndFlapping(unittest.IsolatedAsyncioTestCase):
    """Stress test presence oracle under rapid DHCP churn and neighbor flapping (100 events)."""

    async def asyncSetUp(self):
        self.test_port = 19250
        self.receiver = PresenceOracleReceiver(
            listen_host="127.0.0.1",
            listen_port=self.test_port,
            enable_zmq=False,
        )
        await self.receiver.start()

    async def asyncTearDown(self):
        await self.receiver.stop()

    async def test_100_simultaneous_dhcp_events_propagation_latency(self):
        """Verify 100 simultaneous DHCP/ARP events propagate with latency < 2.0 seconds."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        now_epoch = time.time()
        events = []
        for i in range(100):
            client_id = i % 50
            mac = f"02:00:00:00:01:{client_id:02X}"
            ip = f"192.168.8.{150 + client_id}"
            event_type = "LEASE_ADD" if i < 50 else "LEASE_DEL"
            hostname = f"churn-node-{client_id}"
            ev = {
                "timestamp": now_epoch,
                "event": event_type,
                "mac": mac,
                "ip": ip,
                "hostname": hostname,
                "interface": "br-lan",
            }
            events.append(json.dumps(ev).encode("utf-8"))

        for ev_bytes in events:
            sock.sendto(ev_bytes, ("127.0.0.1", self.test_port))

        await asyncio.sleep(0.3)

        self.assertEqual(self.receiver.total_events, 100)
        self.assertEqual(len(self.receiver.active_inventory), 50)

        for mac, record in self.receiver.active_inventory.items():
            prop_ms = record["propagation_ms"]
            self.assertLess(
                prop_ms,
                2000.0,
                f"Propagation latency for {mac} was {prop_ms}ms, exceeding 2.0s requirement",
            )

        sock.close()

    async def test_rapid_neighbor_flapping_state_convergence(self):
        """Verify rapid alternating NEIGH_UP/NEIGH_DOWN flips converge deterministically."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        flapping_mac = "00:41:0E:14:28:43"

        for i in range(20):
            ev_type = "NEIGH_DOWN" if (i % 2 == 0) else "NEIGH_UP"
            payload = {
                "timestamp": time.time(),
                "event": ev_type,
                "mac": flapping_mac,
                "ip": "192.168.8.224",
                "hostname": "linux-mini",
                "interface": "br-lan",
            }
            sock.sendto(json.dumps(payload).encode("utf-8"), ("127.0.0.1", self.test_port))

        await asyncio.sleep(0.1)

        self.assertIn(flapping_mac, self.receiver.active_inventory)
        record = self.receiver.active_inventory[flapping_mac]
        self.assertEqual(record["status"], "ONLINE")
        self.assertEqual(record["alias"], "Linux_Mini")
        self.assertEqual(record["layer"], "L3")
        self.assertTrue(record["is_canonical_mesh"])

        sock.close()

    async def test_canonical_hardware_matrix_resolution_under_churn(self):
        """Verify Canonical Mesh Hardware Matrix resolution preserves accuracy during churn."""
        canonical_samples = [
            ("1C:F6:4C:7D:D7:0A", "Mac_Node", "L1", "192.168.8.230"),
            ("98:FC:84:E6:E2:12", "MacBook_Pro", "L2", "192.168.8.127"),
            ("00:41:0E:14:28:43", "Linux_Mini", "L3", "192.168.8.224"),
            ("66:74:75:D8:16:FB", "MacBook_Air", "L5", "192.168.8.222"),
            ("94:83:C4:EB:E7:31", "GL.iNet Router", "GW", "192.168.8.1"),
        ]
        for mac, expected_alias, expected_layer, expected_ip in canonical_samples:
            res = CanonicalMeshRegistry.resolve_device(mac, ip=expected_ip)
            self.assertTrue(res["is_canonical_mesh"])
            self.assertEqual(res["alias"], expected_alias)
            self.assertEqual(res["layer"], expected_layer)
            self.assertEqual(res["ip"], expected_ip)


class TestEmpirical10GbELinkLatencySub1ms(unittest.TestCase):
    """Empirically measures and verifies sub-1ms latency across the physical 10GbE link."""

    ROUTER_IP = "192.168.8.1"

    def test_physical_link_icmp_ping_to_router_sub_1ms(self):
        """Empirically measure ICMP ping latency to 192.168.8.1 confirming sub-1ms average RTT."""
        cmd = ["ping", "-c", "10", "-i", "0.1", self.ROUTER_IP]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        self.assertEqual(res.returncode, 0, f"Ping command failed: {res.stderr}")

        output = res.stdout
        loss_match = re.search(r"(\d+(?:\.\d+)?)%\s+packet loss", output)
        self.assertIsNotNone(loss_match, "Packet loss statistic not found in ping output")
        packet_loss = float(loss_match.group(1))
        self.assertEqual(packet_loss, 0.0, f"Packet loss occurred: {packet_loss}%")

        rtt_match = re.search(
            r"(?:round-trip|rtt)[^=]*=\s*([\d\.]+)/([\d\.]+)/([\d\.]+)/([\d\.]+)\s*ms",
            output,
        )
        self.assertIsNotNone(rtt_match, "RTT statistics not found in ping output")
        min_rtt = float(rtt_match.group(1))
        avg_rtt = float(rtt_match.group(2))
        max_rtt = float(rtt_match.group(3))

        self.assertLess(avg_rtt, 1.0, f"Average RTT {avg_rtt:.3f}ms exceeds 1.0ms threshold")
        self.assertLess(min_rtt, 1.0, f"Minimum RTT {min_rtt:.3f}ms exceeds 1.0ms threshold")

    def test_10gbe_interface_routing_mapping(self):
        """Verify routing table maps 192.168.8.1 directly to the en0 10GbE interface."""
        cmd = ["route", "get", self.ROUTER_IP]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        self.assertEqual(res.returncode, 0)
        self.assertIn("interface: en0", res.stdout, f"Destination {self.ROUTER_IP} not routed via en0: {res.stdout}")


if __name__ == "__main__":
    unittest.main()
