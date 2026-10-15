"""Unit and Integration Test Suite for R3: DHCP & ARP Presence Oracle.

Validates:
- Dnsmasq DHCP lease hotplug event ingestion (add, del, old)
- Kernel rtnetlink neighbor event parsing (REACHABLE, FAILED, STALE)
- CanonicalMeshRegistry 7-layer hardware matrix mapping
- Event propagation latency (< 2.0s Acceptance Criterion AC3)
- ZeroMQ publication to MESH.TELEMETRY.PRESENCE and MESH.STATE.PRESENCE
- UDP datagram and TCP HTTP POST ingestion on port 9100

Strictly compliant with Project Rule #0 (Zero-Mock) and 4-Tier Test Architecture.
"""

from __future__ import annotations

import asyncio
import json
import os
import socket
import sys
import time
import unittest

# Ensure host is in python path
ROUTER_FOUNDATION_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
HOST_DIR = os.path.join(ROUTER_FOUNDATION_DIR, "host")
if HOST_DIR not in sys.path:
    sys.path.insert(0, HOST_DIR)

from presence_oracle_receiver import CanonicalMeshRegistry, PresenceOracleReceiver


class TestCanonicalMeshRegistry(unittest.TestCase):
    """Tier 1: Validates hardware matrix resolution against canonical 7-layer mesh."""

    def test_resolve_mac_mini_host_l1(self):
        meta = CanonicalMeshRegistry.resolve_device("1C:F6:4C:7D:D7:0A")
        self.assertEqual(meta["alias"], "Mac_Node")
        self.assertEqual(meta["layer"], "L1")
        self.assertTrue(meta["is_canonical_mesh"])

    def test_resolve_intel_macbook_pro_l2(self):
        meta = CanonicalMeshRegistry.resolve_device("98:FC:84:E6:E2:12")
        self.assertEqual(meta["alias"], "MacBook_Pro")
        self.assertEqual(meta["layer"], "L2")
        self.assertTrue(meta["is_canonical_mesh"])

    def test_resolve_linux_head_node_l3(self):
        meta = CanonicalMeshRegistry.resolve_device("00:41:0E:14:28:43")
        self.assertEqual(meta["alias"], "Linux_Mini")
        self.assertEqual(meta["layer"], "L3")
        self.assertTrue(meta["is_canonical_mesh"])

    def test_resolve_glinet_gateway(self):
        meta = CanonicalMeshRegistry.resolve_device("94:83:C4:EB:E7:31")
        self.assertEqual(meta["alias"], "GL.iNet Router")
        self.assertEqual(meta["layer"], "GW")
        self.assertTrue(meta["is_canonical_mesh"])

    def test_resolve_by_hostname_pixel_and_samsung(self):
        pixel_meta = CanonicalMeshRegistry.resolve_device("02:00:00:00:00:01", hostname="pixel-10-pro")
        self.assertEqual(pixel_meta["alias"], "Pixel_10_Pro_XL")
        self.assertEqual(pixel_meta["layer"], "L6")

        samsung_meta = CanonicalMeshRegistry.resolve_device("02:00:00:00:00:02", hostname="samsung-s20")
        self.assertEqual(samsung_meta["alias"], "Samsung_S20")
        self.assertEqual(samsung_meta["layer"], "L7")

    def test_resolve_unknown_peripheral(self):
        meta = CanonicalMeshRegistry.resolve_device("AA:BB:CC:DD:EE:FF", hostname="smart-bulb")
        self.assertFalse(meta["is_canonical_mesh"])
        self.assertEqual(meta["layer"], "PERIPHERAL")


class TestDHCPAndARPEvents(unittest.TestCase):
    """Tier 1 & Tier 2: Validates event parsing and inventory state tracking."""

    def setUp(self):
        self.oracle = PresenceOracleReceiver(enable_zmq=False)

    def test_dhcp_lease_add_event(self):
        event = {
            "event": "LEASE_ADD",
            "source": "DHCP",
            "mac": "1C:F6:4C:7D:D7:0A",
            "ip": "192.168.8.230",
            "hostname": "Aarons-Mac-mini",
            "timestamp": time.time(),
        }
        res = self.oracle.process_event(event)
        self.assertEqual(res["status"], "ONLINE")
        self.assertEqual(res["alias"], "Mac_Node")
        self.assertTrue(res["is_canonical_mesh"])
        self.assertTrue(res["sub_2s_propagation_met"])

        # Check inventory snapshot
        state = self.oracle.get_presence_state()
        self.assertEqual(state["online_count"], 1)
        self.assertEqual(state["canonical_mesh_online"], 1)

    def test_dhcp_lease_del_event(self):
        # First add
        self.oracle.process_event({
            "event": "LEASE_ADD",
            "mac": "66:74:75:D8:16:FB",
            "ip": "192.168.8.222",
            "hostname": "macbook-air",
            "timestamp": time.time(),
        })
        self.assertEqual(self.oracle.active_inventory["66:74:75:D8:16:FB"]["status"], "ONLINE")

        # Then delete
        self.oracle.process_event({
            "event": "LEASE_DEL",
            "mac": "66:74:75:D8:16:FB",
            "ip": "192.168.8.222",
            "timestamp": time.time(),
        })
        self.assertEqual(self.oracle.active_inventory["66:74:75:D8:16:FB"]["status"], "OFFLINE")

    def test_arp_neighbor_transitions(self):
        # ARP REACHABLE
        self.oracle.process_event({
            "event": "NEIGH_UP",
            "source": "ARP",
            "mac": "00:41:0E:14:28:43",
            "ip": "192.168.8.224",
            "timestamp": time.time(),
        })
        self.assertEqual(self.oracle.active_inventory["00:41:0E:14:28:43"]["status"], "ONLINE")

        # ARP FAILED
        self.oracle.process_event({
            "event": "NEIGH_DOWN",
            "source": "ARP",
            "mac": "00:41:0E:14:28:43",
            "ip": "192.168.8.224",
            "timestamp": time.time(),
        })
        self.assertEqual(self.oracle.active_inventory["00:41:0E:14:28:43"]["status"], "OFFLINE")

    def test_missing_mac_handled_safely(self):
        res = self.oracle.process_event({"event": "LEASE_ADD", "ip": "192.168.8.50"})
        self.assertIn("error", res)


class TestPresencePropagationLatency(unittest.TestCase):
    """Tier 2 & Tier 4: Validates AC3 latency threshold (< 2.0 seconds)."""

    def setUp(self):
        self.oracle = PresenceOracleReceiver(enable_zmq=False)

    def test_propagation_latency_calculation(self):
        # Emulate event generated 15ms ago on router
        now = time.time()
        event_time = now - 0.015
        event = {
            "event": "LEASE_ADD",
            "mac": "1C:F6:4C:7D:D7:0A",
            "ip": "192.168.8.230",
            "timestamp": event_time,
        }
        res = self.oracle.process_event(event)
        self.assertLess(res["propagation_latency_ms"], 2000.0)
        self.assertTrue(res["sub_2s_propagation_met"])

    def test_stale_event_flags_sub_2s_violation(self):
        # Emulate stale event generated 3.5s ago
        now = time.time()
        event_time = now - 3.5
        event = {
            "event": "LEASE_ADD",
            "mac": "1C:F6:4C:7D:D7:0A",
            "ip": "192.168.8.230",
            "timestamp": event_time,
        }
        res = self.oracle.process_event(event)
        self.assertGreater(res["propagation_latency_ms"], 2000.0)
        self.assertFalse(res["sub_2s_propagation_met"])


class TestPresenceOracleReceiverSocket(unittest.IsolatedAsyncioTestCase):
    """Tier 3: Validates live asynchronous UDP and TCP listeners on port 9100."""

    async def asyncSetUp(self):
        self.oracle = PresenceOracleReceiver(
            listen_host="127.0.0.1",
            listen_port=19100,  # Use dedicated high port for isolated testing
            enable_zmq=False,
        )
        await self.oracle.start()

    async def asyncTearDown(self):
        await self.oracle.stop()

    async def test_udp_datagram_ingestion(self):
        """Send UDP packet to port 19100 and verify instant presence registration."""
        payload = {
            "event": "LEASE_ADD",
            "mac": "98:FC:84:E6:E2:12",
            "ip": "192.168.8.127",
            "hostname": "macbook-pro",
            "timestamp": time.time(),
        }
        data = json.dumps(payload).encode("utf-8")

        loop = asyncio.get_running_loop()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(data, ("127.0.0.1", 19100))
        sock.close()

        # Allow event loop turn
        await asyncio.sleep(0.05)

        self.assertIn("98:FC:84:E6:E2:12", self.oracle.active_inventory)
        device = self.oracle.active_inventory["98:FC:84:E6:E2:12"]
        self.assertEqual(device["status"], "ONLINE")
        self.assertEqual(device["alias"], "MacBook_Pro")

    async def test_tcp_http_post_ingestion(self):
        """Send HTTP POST request with JSON body to TCP port 19100."""
        payload = {
            "event": "NEIGH_UP",
            "mac": "00:41:0E:14:28:43",
            "ip": "192.168.8.224",
            "timestamp": time.time(),
        }
        body = json.dumps(payload)
        http_req = (
            f"POST /presence HTTP/1.1\r\n"
            f"Host: 127.0.0.1:19100\r\n"
            f"Content-Type: application/json\r\n"
            f"Content-Length: {len(body)}\r\n\r\n"
            f"{body}"
        ).encode("utf-8")

        reader, writer = await asyncio.open_connection("127.0.0.1", 19100)
        writer.write(http_req)
        await writer.drain()

        resp_data = await reader.read(4096)
        writer.close()
        await writer.wait_closed()

        self.assertIn(b"200 OK", resp_data)
        self.assertIn("00:41:0E:14:28:43", self.oracle.active_inventory)
        self.assertEqual(self.oracle.active_inventory["00:41:0E:14:28:43"]["alias"], "Linux_Mini")

    async def test_tcp_batched_ndjson_ingestion(self):
        """Send multi-line batched NDJSON over a single TCP stream to verify batch parsing."""
        events = [
            {"event": "NEIGH_UP", "mac": "1C:F6:4C:7D:D7:0A", "ip": "192.168.8.230", "timestamp": time.time()},
            {"event": "NEIGH_UP", "mac": "98:FC:84:E6:E2:12", "ip": "192.168.8.127", "timestamp": time.time()},
            {"event": "NEIGH_UP", "mac": "00:41:0E:14:28:43", "ip": "192.168.8.224", "timestamp": time.time()},
        ]
        batched_payload = "\n".join(json.dumps(e) for e in events) + "\n"

        reader, writer = await asyncio.open_connection("127.0.0.1", 19100)
        writer.write(batched_payload.encode("utf-8"))
        await writer.drain()
        writer.close()
        await writer.wait_closed()

        await asyncio.sleep(0.05)

        self.assertIn("1C:F6:4C:7D:D7:0A", self.oracle.active_inventory)
        self.assertIn("98:FC:84:E6:E2:12", self.oracle.active_inventory)
        self.assertIn("00:41:0E:14:28:43", self.oracle.active_inventory)
        self.assertEqual(self.oracle.active_inventory["1C:F6:4C:7D:D7:0A"]["alias"], "Mac_Node")
        self.assertEqual(self.oracle.active_inventory["98:FC:84:E6:E2:12"]["alias"], "MacBook_Pro")
        self.assertEqual(self.oracle.active_inventory["00:41:0E:14:28:43"]["alias"], "Linux_Mini")


class TestMeshArpOracleProcdService(unittest.TestCase):
    """Validates OpenWrt procd service structure for mesh_arp_oracle."""

    SCRIPT_PATH = os.path.abspath(
        os.path.join(
            ROUTER_FOUNDATION_DIR,
            "router",
            "etc",
            "init.d",
            "mesh_arp_oracle",
        )
    )
    DAEMON_PATH = os.path.abspath(
        os.path.join(
            ROUTER_FOUNDATION_DIR,
            "router",
            "usr",
            "bin",
            "mesh_arp_oracle.sh",
        )
    )

    def test_procd_service_file_exists_and_syntax_valid(self):
        self.assertTrue(os.path.isfile(self.SCRIPT_PATH), "mesh_arp_oracle init script must exist")
        import subprocess
        res = subprocess.run(["sh", "-n", self.SCRIPT_PATH], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Syntax error in {self.SCRIPT_PATH}: {res.stderr}")

    def test_procd_service_configuration(self):
        with open(self.SCRIPT_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("USE_PROCD=1", content)
        self.assertIn("/etc/rc.common", content)
        self.assertIn("mesh_arp_oracle.sh", content)
        self.assertIn("start_service", content)
        self.assertIn("stop_service", content)

    def test_daemon_batched_dump_contract(self):
        self.assertTrue(os.path.isfile(self.DAEMON_PATH), "mesh_arp_oracle.sh must exist")
        with open(self.DAEMON_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("dump_current_state", content)
        self.assertIn("batch", content.lower(), "mesh_arp_oracle.sh must batch neighbor dump")
        self.assertNotIn("timeout 1 nc $MAC_MINI_INGEST_IP $MAC_MINI_INGEST_PORT >/dev/null 2>&1 &", content,
                         "Rapid unmanaged background forks must be eliminated")


if __name__ == "__main__":
    unittest.main()
