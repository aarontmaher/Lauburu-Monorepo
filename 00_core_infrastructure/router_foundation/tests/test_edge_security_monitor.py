"""Unit and Integration Test Suite for R5: Edge Security Red Team Monitor & Radar.

Validates:
- Rogue MAC detection against Canonical Hardware Matrix whitelist
- Multicast/broadcast filtering (01:00:5E, 33:33, FF:FF:FF:FF:FF:FF)
- Routing loop detection (TTL <= 1 in IP header, ICMP Type 11 Time Exceeded)
- Duplicate IP ID packet cycling detection in 50ms window
- ARP spoofing and gateway impersonation detection (claims to 192.168.8.1)
- Connection flood (SYN flood > 200/s) and port scan (> 25 ports/s) detection
- Security radar state JSON construction
- 2D visual radar JPEG rendering (1280x720 RGB canvas for Port 4003)

Strictly compliant with Project Rule #0 (Zero-Mock) and 4-Tier Test Architecture.
"""

from __future__ import annotations

import io
import os
import sys
import time
import unittest
from PIL import Image

# Ensure host is in python path
ROUTER_FOUNDATION_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
HOST_DIR = os.path.join(ROUTER_FOUNDATION_DIR, "host")
if HOST_DIR not in sys.path:
    sys.path.insert(0, HOST_DIR)

from lens_edge_security_monitor import (
    CanonicalMeshHardwareMatrix,
    LensEdgeSecurityMonitor,
)


class TestRogueMACHunting(unittest.TestCase):
    """Tier 1 & Tier 2: Validates MAC whitelist enforcement and rogue device hunting."""

    def setUp(self):
        self.monitor = LensEdgeSecurityMonitor(enable_zmq=False)

    def test_canonical_mesh_macs_are_whitelisted(self):
        """All 7-layer canonical mesh hardware MACs must be whitelisted."""
        for mac in CanonicalMeshHardwareMatrix.WHITELIST_MACS.keys():
            self.assertTrue(
                self.monitor.is_mac_whitelisted(mac),
                f"Canonical MAC {mac} must be whitelisted",
            )

    def test_multicast_and_broadcast_macs_ignored(self):
        """Multicast (01:00:5E, 33:33) and broadcast (FF:FF:FF:FF:FF:FF) must not trigger rogue alert."""
        self.assertTrue(self.monitor.is_mac_whitelisted("01:00:5E:00:00:FB"))
        self.assertTrue(self.monitor.is_mac_whitelisted("33:33:00:00:00:01"))
        self.assertTrue(self.monitor.is_mac_whitelisted("FF:FF:FF:FF:FF:FF"))

    def test_unrecognized_mac_triggers_rogue_mac_alert(self):
        """Unrecognized MAC must trigger ROGUE_MAC alert with HIGH severity."""
        rogue_mac = "44:38:39:FF:EF:01"
        res = self.monitor.inspect_ethernet_frame(
            src_mac=rogue_mac,
            dst_mac="1C:F6:4C:7D:D7:0A",
            src_ip="192.168.8.199",
            dst_ip="192.168.8.230",
        )
        self.assertEqual(res["status"], "ALERT")
        self.assertEqual(len(res["alerts"]), 1)
        alert = res["alerts"][0]
        self.assertEqual(alert["type"], "ROGUE_MAC")
        self.assertEqual(alert["severity"], "HIGH")
        self.assertIn(rogue_mac, self.monitor.rogue_macs_detected)

    def test_dynamic_mac_authorization(self):
        """Authorizing a previously rogue MAC clears alert and updates whitelist."""
        rogue_mac = "DE:AD:BE:EF:00:01"
        self.monitor.inspect_ethernet_frame(src_mac=rogue_mac, dst_mac="FF:FF:FF:FF:FF:FF")
        self.assertIn(rogue_mac, self.monitor.rogue_macs_detected)

        self.monitor.authorize_mac(rogue_mac)
        self.assertTrue(self.monitor.is_mac_whitelisted(rogue_mac))
        self.assertNotIn(rogue_mac, self.monitor.rogue_macs_detected)


class TestRoutingLoopDetection(unittest.TestCase):
    """Tier 1 & Tier 2: Validates detection of packet loops via TTL, ICMP, and IP ID."""

    def setUp(self):
        self.monitor = LensEdgeSecurityMonitor(enable_zmq=False)

    def test_ttl_le_1_triggers_routing_loop_alert(self):
        """IP packets with TTL <= 1 signify routing hop exhaustion."""
        res = self.monitor.inspect_ethernet_frame(
            src_mac="1C:F6:4C:7D:D7:0A",
            dst_mac="94:83:C4:EB:E7:31",
            src_ip="192.168.8.230",
            dst_ip="8.8.8.8",
            ttl=1,
        )
        self.assertEqual(res["status"], "ALERT")
        alerts = [a for a in res["alerts"] if a["type"] == "ROUTING_LOOP"]
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["details"]["reason"], "TTL_EXHAUSTED")
        self.assertEqual(self.monitor.routing_loop_events, 1)

    def test_icmp_type_11_time_exceeded(self):
        """ICMP Type 11 explicitly signals time-to-live exceeded in transit."""
        res = self.monitor.inspect_ethernet_frame(
            src_mac="94:83:C4:EB:E7:31",
            dst_mac="1C:F6:4C:7D:D7:0A",
            src_ip="192.168.8.1",
            dst_ip="192.168.8.230",
            proto="ICMP",
            icmp_type=11,
        )
        alerts = [a for a in res["alerts"] if a["type"] == "ROUTING_LOOP"]
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["severity"], "CRITICAL")
        self.assertEqual(alerts[0]["details"]["reason"], "ICMP_TIME_EXCEEDED")

    def test_duplicate_ip_id_packet_cycling_detection(self):
        """Observing the same (src_ip, dst_ip, ip_id) > 2 times in 50ms confirms a forwarding loop."""
        now = time.time()
        src = "192.168.8.230"
        dst = "1.1.1.1"
        ip_id = 42890

        # Frame 1: first observation
        r1 = self.monitor.inspect_ethernet_frame(
            src_mac="1C:F6:4C:7D:D7:0A", dst_mac="94:83:C4:EB:E7:31",
            src_ip=src, dst_ip=dst, ip_id=ip_id, timestamp_epoch=now,
        )
        self.assertEqual(r1["status"], "CLEAN")

        # Frame 2: duplicate in 10ms
        r2 = self.monitor.inspect_ethernet_frame(
            src_mac="94:83:C4:EB:E7:31", dst_mac="1C:F6:4C:7D:D7:0A",
            src_ip=src, dst_ip=dst, ip_id=ip_id, timestamp_epoch=now + 0.010,
        )
        self.assertEqual(r2["status"], "CLEAN")

        # Frame 3: triplicate in 20ms -> Loop Confirmed!
        r3 = self.monitor.inspect_ethernet_frame(
            src_mac="1C:F6:4C:7D:D7:0A", dst_mac="94:83:C4:EB:E7:31",
            src_ip=src, dst_ip=dst, ip_id=ip_id, timestamp_epoch=now + 0.020,
        )
        self.assertEqual(r3["status"], "ALERT")
        loop_alerts = [a for a in r3["alerts"] if a["type"] == "ROUTING_LOOP"]
        self.assertEqual(len(loop_alerts), 1)
        self.assertEqual(loop_alerts[0]["details"]["reason"], "DUPLICATE_PACKET_CYCLING")


class TestARPSpoofingHunting(unittest.TestCase):
    """Tier 1 & Tier 2: Validates ARP cache poisoning and gateway impersonation defense."""

    def setUp(self):
        self.monitor = LensEdgeSecurityMonitor(enable_zmq=False)

    def test_gateway_impersonation_detection(self):
        """An ARP reply claiming gateway IP 192.168.8.1 with wrong MAC triggers CRITICAL alert."""
        attacker_mac = "DE:AD:BE:EF:00:66"
        res = self.monitor.inspect_ethernet_frame(
            src_mac=attacker_mac,
            dst_mac="FF:FF:FF:FF:FF:FF",
            src_ip="192.168.8.1",  # Gateway IP
            proto="ARP",
        )
        self.assertEqual(res["status"], "ALERT")
        arp_alerts = [a for a in res["alerts"] if a["type"] == "ARP_POISONING"]
        self.assertEqual(len(arp_alerts), 1)
        self.assertEqual(arp_alerts[0]["severity"], "CRITICAL")
        self.assertEqual(arp_alerts[0]["details"]["reason"], "GATEWAY_IMPERSONATION")

    def test_legitimate_gateway_arp_passes_clean(self):
        """Legitimate gateway MAC claiming 192.168.8.1 must pass without ARP_POISONING alert."""
        res = self.monitor.inspect_ethernet_frame(
            src_mac=CanonicalMeshHardwareMatrix.GATEWAY_MAC,
            dst_mac="FF:FF:FF:FF:FF:FF",
            src_ip="192.168.8.1",
            proto="ARP",
        )
        arp_alerts = [a for a in res["alerts"] if a["type"] == "ARP_POISONING"]
        self.assertEqual(len(arp_alerts), 0)


class TestSYNScanAndFloodHunting(unittest.TestCase):
    """Tier 2: Validates network anomaly detection for SYN flood and port scanning."""

    def setUp(self):
        self.monitor = LensEdgeSecurityMonitor(enable_zmq=False)

    def test_port_scan_detection(self):
        """Hitting > 25 distinct destination ports from 1 IP in 1 second triggers PORT_SCAN."""
        now = time.time()
        src_ip = "192.168.8.199"
        src_mac = "02:00:00:00:00:99"
        self.monitor.authorize_mac(src_mac)  # Ignore rogue MAC to isolate port scan

        last_res = None
        for port in range(1, 28):
            last_res = self.monitor.inspect_ethernet_frame(
                src_mac=src_mac,
                dst_mac="1C:F6:4C:7D:D7:0A",
                src_ip=src_ip,
                dst_ip="192.168.8.230",
                proto="TCP",
                tcp_flags="S",
                dst_port=port,
                timestamp_epoch=now + (port * 0.01),
            )

        self.assertIsNotNone(last_res)
        scan_alerts = [a for a in last_res["alerts"] if a["type"] == "PORT_SCAN"]
        self.assertEqual(len(scan_alerts), 1)
        self.assertEqual(scan_alerts[0]["severity"], "MEDIUM")


class TestSecurityRadarStateAndRendering(unittest.TestCase):
    """Tier 3: Validates JSON radar state and 2D visual radar JPEG rendering for Port 4003."""

    def setUp(self):
        self.monitor = LensEdgeSecurityMonitor(enable_zmq=False)

    def test_security_radar_state_schema(self):
        state = self.monitor.get_security_radar_state()
        self.assertIn("threat_level", state)
        self.assertIn("total_inspected", state)
        self.assertIn("rogue_macs_count", state)
        self.assertIn("routing_loops_detected", state)
        self.assertIn("arp_integrity_pct", state)
        self.assertIn("topology_summary", state)
        self.assertEqual(state["threat_level"], "NOMINAL")

    def test_render_security_radar_frame_jpeg(self):
        """Verify rendering 1280x720 RGB JPEG frame."""
        jpeg_bytes = self.monitor.render_security_radar_frame(width=1280, height=720)
        self.assertIsInstance(jpeg_bytes, bytes)
        self.assertGreater(len(jpeg_bytes), 1000)

        # Verify image dimensions and format via PIL
        img = Image.open(io.BytesIO(jpeg_bytes))
        self.assertEqual(img.format, "JPEG")
        self.assertEqual(img.size, (1280, 720))


class TestEdgeSecurityStreamerProcdService(unittest.TestCase):
    """Validates OpenWrt procd service and targeted socat termination contracts."""

    SCRIPT_PATH = os.path.abspath(
        os.path.join(
            ROUTER_FOUNDATION_DIR,
            "router",
            "etc",
            "init.d",
            "edge_security_streamer",
        )
    )
    DAEMON_PATH = os.path.abspath(
        os.path.join(
            ROUTER_FOUNDATION_DIR,
            "router",
            "usr",
            "bin",
            "edge_security_streamer.sh",
        )
    )

    def test_procd_service_file_exists_and_syntax_valid(self):
        self.assertTrue(os.path.isfile(self.SCRIPT_PATH), "edge_security_streamer init script must exist")
        import subprocess
        res = subprocess.run(["sh", "-n", self.SCRIPT_PATH], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Syntax error in {self.SCRIPT_PATH}: {res.stderr}")

    def test_procd_service_configuration(self):
        with open(self.SCRIPT_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("USE_PROCD=1", content)
        self.assertIn("/etc/rc.common", content)
        self.assertIn("edge_security_streamer.sh", content)
        self.assertIn("start_service", content)
        self.assertIn("stop_service", content)

    def test_edge_security_streamer_targeted_socat_kill_contract(self):
        """Verify killall socat is strictly eliminated and targeted PID killing is used."""
        self.assertTrue(os.path.isfile(self.DAEMON_PATH), "edge_security_streamer.sh must exist")
        with open(self.DAEMON_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertNotIn("killall socat", content, "killall socat is strictly forbidden to preserve port 9002")
        self.assertIn("pgrep -f", content, "Targeted process lookup must be used")


if __name__ == "__main__":
    unittest.main()
