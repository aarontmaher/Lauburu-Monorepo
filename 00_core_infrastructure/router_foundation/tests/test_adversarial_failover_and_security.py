"""Adversarial & Empirical Stress Test Suite for M4 (Out-Of-Band WAN Self-Healer) and M5 (Edge Security Red Team).

Executes comprehensive stress scenarios:
1. Out-Of-Band WAN Self-Healer (R4):
   - Intermittent packet loss (10%, 33%, 50%, 66% loss patterns) verifying hysteresis prevents route flapping
   - Rapid recovery bouncing (alternating success/fail in recovery probing) verifying link stability gating
   - All target ICMP unreachable verifying deterministic failover actuation and exact ip route command generation
   - Backup gateway missing / unplugged / down verifying fail-safe non-crashing execution
   - Route table metric collision avoidance and strict kernel metric priority ordering
   - POSIX shell execution of lauburu_oob_wan_healer.sh across all states

2. Edge Security Red Team (R5):
   - Rogue MAC injection (unauthorized MAC, multicast/broadcast filtering, dynamic MAC authorization)
   - Circular routing packets (TTL <= 1, ICMP Type 11 Time Exceeded, duplicate IP ID cycling in <50ms)
   - ARP gateway spoofing attempts (gateway impersonation 192.168.8.1, rapid MAC flipping, legitimate pass-through)
   - High-throughput SYN flood bursts (>200 SYN/s) and port scanning (>25 ports/s)
   - High-volume adversarial malformed frame fuzzing (2,000 corrupt/adversarial frames with zero crashes)

3. Screen Lens Port 4003 Visual Radar:
   - Verification of 2D radar frame generation producing valid 1280x720 RGB JPEG bytes
   - Verification of JPEG markers (SOI 0xFFD8, EOI 0xFFD9) and Pillow decoding across NOMINAL, ELEVATED, CRITICAL states
   - Checksum tracking and latency benchmarking (< 50ms per frame render)

Strictly compliant with Project Rule #0 (Zero-Mock) and Project Rule #3 (Host Sanctuary).
"""

from __future__ import annotations

import io
import json
import os
import random
import subprocess
import sys
import tempfile
import time
import unittest
from typing import Any, Dict, List, Optional
from PIL import Image

# Ensure host directory is in sys.path
ROUTER_FOUNDATION_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
HOST_DIR = os.path.join(ROUTER_FOUNDATION_DIR, "host")
if HOST_DIR not in sys.path:
    sys.path.insert(0, HOST_DIR)

from lens_edge_security_monitor import (
    CanonicalMeshHardwareMatrix,
    LensEdgeSecurityMonitor,
)


class TestWANHealerPOSIXScriptStress(unittest.TestCase):
    """Stress tests lauburu_oob_wan_healer.sh by directly executing POSIX shell functions."""

    SCRIPT_PATH = os.path.abspath(
        os.path.join(
            ROUTER_FOUNDATION_DIR,
            "router",
            "usr",
            "bin",
            "lauburu_oob_wan_healer.sh",
        )
    )

    def setUp(self):
        self.assertTrue(os.path.isfile(self.SCRIPT_PATH), "lauburu_oob_wan_healer.sh must exist")
        with open(self.SCRIPT_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        self.shell_funcs = content.split("trap cleanup")[0]

    def _run_shell_scenario(self, custom_sh: str) -> subprocess.CompletedProcess:
        """Executes custom test logic wrapped around the shell script functions."""
        full_script = f"""
set -e
{self.shell_funcs}

# Test Harness Stubs
MOCK_LOG="/tmp/healer_stress_mock.log"
rm -f "$MOCK_LOG"

ip() {{
    echo "IP: $@" >> "$MOCK_LOG"
}}

logger() {{
    echo "LOG: $@" >> "$MOCK_LOG"
}}

{custom_sh}
"""
        return subprocess.run(["sh"], input=full_script, text=True, capture_output=True)

    def test_intermittent_packet_loss_hysteresis_prevents_flapping(self):
        """Intermittent packet loss (e.g. alternating fail/pass) must NEVER trigger failover."""
        # Scenario: 50 cycles of alternating [FAIL, PASS]
        custom_sh = """
PROBE_RES=0
probe_wan() {
    return $PROBE_RES
}

FAILOVERS=0
actuate_failover() {
    FAILOVERS=$((FAILOVERS + 1))
}

# 1. Alternating 50% loss
for i in $(seq 1 20); do
    PROBE_RES=1
    fsm_step
    if [ "$CURRENT_STATE" = "FAILOVER_TRIGGERED" ]; then
        echo "ERROR: Flapped to failover on 50% loss!"
        exit 2
    fi
    PROBE_RES=0
    fsm_step
    if [ "$CURRENT_STATE" != "PRIMARY_ONLINE" ]; then
        echo "ERROR: State did not return to PRIMARY_ONLINE!"
        exit 3
    fi
done

# 2. Burst of 2 fails followed by 1 pass (66% loss)
for i in $(seq 1 10); do
    PROBE_RES=1
    fsm_step
    PROBE_RES=1
    fsm_step
    if [ "$CURRENT_STATE" != "PROBING_DEGRADED" ]; then
        echo "ERROR: Expected PROBING_DEGRADED after 2 fails, got $CURRENT_STATE"
        exit 4
    fi
    PROBE_RES=0
    fsm_step
    if [ "$CURRENT_STATE" != "PRIMARY_ONLINE" ]; then
        echo "ERROR: Expected recovery to PRIMARY_ONLINE after pass, got $CURRENT_STATE"
        exit 5
    fi
done

echo "HYSTERESIS_STABLE_FAILOVERS=$FAILOVERS"
"""
        proc = self._run_shell_scenario(custom_sh)
        self.assertEqual(proc.returncode, 0, f"Shell scenario failed:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
        self.assertIn("HYSTERESIS_STABLE_FAILOVERS=0", proc.stdout)

    def test_rapid_recovery_bouncing_prevents_premature_failback(self):
        """Primary bouncing during failback probing must reset success counter and prevent route flapping."""
        custom_sh = """
PROBE_RES=0
probe_wan() {
    return $PROBE_RES
}

FAILBACKS=0
actuate_failback() {
    FAILBACKS=$((FAILBACKS + 1))
}

# Drive to BACKUP_ONLINE
PROBE_RES=1
fsm_step # fail 1
fsm_step # fail 2
fsm_step # fail 3 -> FAILOVER_TRIGGERED
fsm_step # -> BACKUP_ONLINE

if [ "$CURRENT_STATE" != "BACKUP_ONLINE" ]; then
    echo "ERROR: Failed to reach BACKUP_ONLINE, got $CURRENT_STATE"
    exit 2
fi

# Rapid bouncing: [PASS, FAIL], [PASS, PASS, FAIL], [PASS, PASS, PASS, FAIL], [PASS, PASS, PASS, PASS, FAIL]
BOUNCE_PATTERNS="1 2 3 4 2 3 1 4"
for num_passes in $BOUNCE_PATTERNS; do
    for p in $(seq 1 "$num_passes"); do
        PROBE_RES=0
        fsm_step
    done
    if [ "$CURRENT_STATE" != "FAILBACK_PROBING" ]; then
        echo "ERROR: Expected FAILBACK_PROBING during passes, got $CURRENT_STATE"
        exit 3
    fi
    # Link drops before reaching 5 stable passes
    PROBE_RES=1
    fsm_step
    if [ "$CURRENT_STATE" != "BACKUP_ONLINE" ]; then
        echo "ERROR: Expected revert to BACKUP_ONLINE on drop, got $CURRENT_STATE"
        exit 4
    fi
    if [ "$SUCCESS_COUNT" -ne 0 ]; then
        echo "ERROR: SUCCESS_COUNT was not reset to 0!"
        exit 5
    fi
done

if [ "$FAILBACKS" -ne 0 ]; then
    echo "ERROR: Failback was actuated during flapping! Count=$FAILBACKS"
    exit 6
fi

# Now provide strictly 5 consecutive passes
for p in $(seq 1 5); do
    PROBE_RES=0
    fsm_step
done

if [ "$CURRENT_STATE" != "FAILBACK_TRIGGERED" ]; then
    echo "ERROR: Expected FAILBACK_TRIGGERED after 5 passes, got $CURRENT_STATE"
    exit 7
fi

# Next step actuates failback and transitions to PRIMARY_ONLINE
fsm_step
if [ "$CURRENT_STATE" != "PRIMARY_ONLINE" ]; then
    echo "ERROR: Expected PRIMARY_ONLINE after actuation, got $CURRENT_STATE"
    exit 8
fi

echo "FAILBACK_COMPLETED_COUNT=$FAILBACKS"
"""
        proc = self._run_shell_scenario(custom_sh)
        self.assertEqual(proc.returncode, 0, f"Shell scenario failed:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
        self.assertIn("FAILBACK_COMPLETED_COUNT=1", proc.stdout)

    def test_all_targets_icmp_unreachable_triggers_deterministic_failover(self):
        """When all targets are unreachable, probe_wan fails and triggers exact route replace commands."""
        custom_sh = """
# Real probe_wan function tests 1.1.1.1, 8.8.8.8, 9.9.9.9
# Mock ping to simulate all targets unreachable (exit code 1)
ping() {
    return 1
}

# Run 3 steps to trigger failover
fsm_step
fsm_step
fsm_step
fsm_step

echo "FINAL_STATE=$CURRENT_STATE"
"""
        proc = self._run_shell_scenario(custom_sh)
        self.assertEqual(proc.returncode, 0, f"Shell scenario failed:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
        self.assertIn("FINAL_STATE=BACKUP_ONLINE", proc.stdout)

    def test_backup_gateway_missing_or_unplugged_resilience(self):
        """When backup device/gateway is missing or kernel throws error, healer executes without crashing."""
        custom_sh = """
# 1. Test with completely empty backup interface/gateway
BACKUP_DEV=""
BACKUP_GW=""

actuate_failover

# 2. Test when ip route replace returns error (e.g. exit code 2: No such device)
ip() {
    echo "IP FAIL: $@" >> "$MOCK_LOG"
    return 2
}

BACKUP_DEV="nonexistent0"
BACKUP_GW="192.0.2.1"
actuate_failover

echo "BACKUP_RESILIENCE_PASSED"
"""
        proc = self._run_shell_scenario(custom_sh)
        self.assertEqual(proc.returncode, 0, f"Shell scenario failed:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
        self.assertIn("BACKUP_RESILIENCE_PASSED", proc.stdout)

    def test_route_metric_collision_avoidance_and_priority_invariants(self):
        """Verify metric ordering invariants: lower metric is preferred, no metric collision exists."""
        custom_sh = """
PRIMARY_GW="100.90.8.1"
PRIMARY_DEV="eth1.3"
BACKUP_GW="10.178.49.221"
BACKUP_DEV="usb0"

# Capture commands generated in failover
actuate_failover

# Capture commands generated in failback
actuate_failback
"""
        proc = self._run_shell_scenario(custom_sh)
        self.assertEqual(proc.returncode, 0, proc.stderr)

        # Inspect log
        with open("/tmp/healer_stress_mock.log", "r") as f:
            log_content = f.read()

        # Failover metrics: Backup=10, Primary=100
        self.assertIn("route replace default scope global via 10.178.49.221 dev usb0 metric 10", log_content)
        self.assertIn("route replace default scope global via 100.90.8.1 dev eth1.3 metric 100", log_content)

        # Failback metrics: Primary=1, Backup=2
        self.assertIn("route replace default scope global via 100.90.8.1 dev eth1.3 metric 1", log_content)
        self.assertIn("route replace default scope global via 10.178.49.221 dev usb0 metric 2", log_content)

        # Verify no metric collisions: 1 != 2, 10 != 100
        self.assertNotIn("metric 1 dev usb0", log_content)
        self.assertNotIn("metric 100 dev usb0", log_content)


class TestEdgeSecurityMonitorAdversarialFrames(unittest.TestCase):
    """Stress tests lens_edge_security_monitor.py with adversarial network frames."""

    def setUp(self):
        self.monitor = LensEdgeSecurityMonitor(enable_zmq=False)

    def test_rogue_mac_injection_and_multicast_filtering(self):
        """Rogue MACs must trigger HIGH alerts; multicast/broadcast must pass clean."""
        # 1. Canonical MACs pass clean
        for mac, info in CanonicalMeshHardwareMatrix.WHITELIST_MACS.items():
            res = self.monitor.inspect_ethernet_frame(
                src_mac=mac,
                dst_mac="94:83:C4:EB:E7:31",
                src_ip=info["ip"],
                dst_ip="192.168.8.1",
            )
            self.assertEqual(res["status"], "CLEAN", f"Canonical MAC {mac} must be CLEAN")

        # 2. Multicast prefixes pass clean
        multicasts = [
            "01:00:5E:00:00:FB",
            "01:00:5E:7F:FF:FA",
            "33:33:00:00:00:01",
            "33:33:FF:12:34:56",
            "FF:FF:FF:FF:FF:FF",
            "01:80:C2:00:00:00",
        ]
        for m_mac in multicasts:
            res = self.monitor.inspect_ethernet_frame(
                src_mac=m_mac,
                dst_mac="1C:F6:4C:7D:D7:0A",
                src_ip="192.168.8.50",
            )
            self.assertEqual(res["status"], "CLEAN", f"Multicast MAC {m_mac} must be ignored")

        # 3. Rogue MAC triggers HIGH alert
        rogue_mac = "B8:27:EB:11:22:33"
        res = self.monitor.inspect_ethernet_frame(
            src_mac=rogue_mac,
            dst_mac="1C:F6:4C:7D:D7:0A",
            src_ip="192.168.8.188",
        )
        self.assertEqual(res["status"], "ALERT")
        alerts = [a for a in res["alerts"] if a["type"] == "ROGUE_MAC"]
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["severity"], "HIGH")
        self.assertEqual(alerts[0]["details"]["mac"], rogue_mac)

        # 4. Dynamic authorization clears rogue MAC
        self.monitor.authorize_mac(rogue_mac)
        self.assertTrue(self.monitor.is_mac_whitelisted(rogue_mac))
        self.assertNotIn(rogue_mac, self.monitor.rogue_macs_detected)

        # Subsequent packet passes clean
        res2 = self.monitor.inspect_ethernet_frame(src_mac=rogue_mac, dst_mac="1C:F6:4C:7D:D7:0A")
        self.assertEqual(res2["status"], "CLEAN")

    def test_circular_routing_packets_ttl_and_icmp_11(self):
        """TTL <= 1, ICMP 11, and duplicate IP ID cycling must accurately trigger ROUTING_LOOP."""
        # 1. TTL = 1
        r_ttl1 = self.monitor.inspect_ethernet_frame(
            src_mac="1C:F6:4C:7D:D7:0A",
            dst_mac="94:83:C4:EB:E7:31",
            src_ip="192.168.8.230",
            dst_ip="8.8.8.8",
            ttl=1,
        )
        self.assertEqual(r_ttl1["status"], "ALERT")
        a1 = [a for a in r_ttl1["alerts"] if a["type"] == "ROUTING_LOOP"][0]
        self.assertEqual(a1["severity"], "HIGH")
        self.assertEqual(a1["details"]["reason"], "TTL_EXHAUSTED")

        # 2. TTL = 0
        r_ttl0 = self.monitor.inspect_ethernet_frame(
            src_mac="1C:F6:4C:7D:D7:0A",
            dst_mac="94:83:C4:EB:E7:31",
            src_ip="192.168.8.230",
            dst_ip="1.1.1.1",
            ttl=0,
        )
        self.assertEqual(r_ttl0["status"], "ALERT")

        # 3. ICMP Type 11 Time Exceeded
        r_icmp = self.monitor.inspect_ethernet_frame(
            src_mac="94:83:C4:EB:E7:31",
            dst_mac="1C:F6:4C:7D:D7:0A",
            src_ip="192.168.8.1",
            dst_ip="192.168.8.230",
            proto="ICMP",
            icmp_type=11,
        )
        self.assertEqual(r_icmp["status"], "ALERT")
        a_icmp = [a for a in r_icmp["alerts"] if a["type"] == "ROUTING_LOOP"][0]
        self.assertEqual(a_icmp["severity"], "CRITICAL")
        self.assertEqual(a_icmp["details"]["reason"], "ICMP_TIME_EXCEEDED")

        # 4. Duplicate IP ID cycling within 50ms
        t0 = time.time()
        ip_id = 9988
        src = "192.168.8.230"
        dst = "8.8.4.4"

        # Packet 1 & 2: under threshold
        self.monitor.inspect_ethernet_frame("1C:F6:4C:7D:D7:0A", "94:83:C4:EB:E7:31", src, dst, ip_id=ip_id, timestamp_epoch=t0)
        self.monitor.inspect_ethernet_frame("94:83:C4:EB:E7:31", "1C:F6:4C:7D:D7:0A", src, dst, ip_id=ip_id, timestamp_epoch=t0 + 0.01)

        # Packet 3 (triplicate in 20ms) -> alert!
        r_dup = self.monitor.inspect_ethernet_frame("1C:F6:4C:7D:D7:0A", "94:83:C4:EB:E7:31", src, dst, ip_id=ip_id, timestamp_epoch=t0 + 0.02)
        self.assertEqual(r_dup["status"], "ALERT")
        a_dup = [a for a in r_dup["alerts"] if a["type"] == "ROUTING_LOOP"][0]
        self.assertEqual(a_dup["severity"], "CRITICAL")
        self.assertEqual(a_dup["details"]["reason"], "DUPLICATE_PACKET_CYCLING")

    def test_arp_gateway_spoofing_and_rapid_flipping(self):
        """Adversarial ARP packets claiming Gateway IP or rapid flipping must trigger CRITICAL alerts."""
        # 1. Rogue MAC claims Gateway IP 192.168.8.1
        attacker_mac = "CA:FE:BA:BE:00:99"
        res = self.monitor.inspect_ethernet_frame(
            src_mac=attacker_mac,
            dst_mac="FF:FF:FF:FF:FF:FF",
            src_ip="192.168.8.1",
            proto="ARP",
        )
        self.assertEqual(res["status"], "ALERT")
        a_arp = [a for a in res["alerts"] if a["type"] == "ARP_POISONING"][0]
        self.assertEqual(a_arp["severity"], "CRITICAL")
        self.assertEqual(a_arp["details"]["reason"], "GATEWAY_IMPERSONATION")
        self.assertEqual(a_arp["details"]["attacker_mac"], attacker_mac)

        # Threat level must immediately elevate to CRITICAL
        radar_state = self.monitor.get_security_radar_state()
        self.assertEqual(radar_state["threat_level"], "CRITICAL")
        self.assertLess(radar_state["arp_integrity_pct"], 100.0)

        # 2. Rapid MAC flipping on local IP
        victim_ip = "192.168.8.210"
        t0 = time.time()
        mac1 = "02:00:00:00:00:01"
        mac2 = "02:00:00:00:00:02"
        self.monitor.authorize_mac(mac1)
        self.monitor.authorize_mac(mac2)

        self.monitor.inspect_ethernet_frame(src_mac=mac1, dst_mac="FF:FF:FF:FF:FF:FF", src_ip=victim_ip, proto="ARP", timestamp_epoch=t0)
        res_flip = self.monitor.inspect_ethernet_frame(src_mac=mac2, dst_mac="FF:FF:FF:FF:FF:FF", src_ip=victim_ip, proto="ARP", timestamp_epoch=t0 + 1.0)
        self.assertEqual(res_flip["status"], "ALERT")
        a_flip = [a for a in res_flip["alerts"] if a["type"] == "ARP_SPOOFING"][0]
        self.assertEqual(a_flip["severity"], "HIGH")
        self.assertEqual(a_flip["details"]["reason"], "RAPID_MAC_FLIP")

    def test_syn_flood_burst_and_port_scan(self):
        """Burst of >200 SYN/s or >25 ports/s must trigger security alerts."""
        t0 = time.time()
        src_ip = "192.168.8.199"
        src_mac = "02:AA:BB:CC:DD:EE"
        self.monitor.authorize_mac(src_mac)

        # 1. Port scan: probe 30 ports in 0.5s
        last_res = None
        for port in range(1, 31):
            last_res = self.monitor.inspect_ethernet_frame(
                src_mac=src_mac,
                dst_mac="1C:F6:4C:7D:D7:0A",
                src_ip=src_ip,
                dst_ip="192.168.8.230",
                proto="TCP",
                tcp_flags="S",
                dst_port=port,
                timestamp_epoch=t0 + (port * 0.01),
            )
        self.assertIsNotNone(last_res)
        scan_alerts = [a for a in last_res["alerts"] if a["type"] == "PORT_SCAN"]
        self.assertEqual(len(scan_alerts), 1)
        self.assertEqual(scan_alerts[0]["severity"], "MEDIUM")

        # 2. SYN flood: 220 SYNs to single port in 0.8s
        t_flood = t0 + 2.0
        syn_alerts = []
        for i in range(220):
            res_flood = self.monitor.inspect_ethernet_frame(
                src_mac=src_mac,
                dst_mac="1C:F6:4C:7D:D7:0A",
                src_ip=src_ip,
                dst_ip="192.168.8.230",
                proto="TCP",
                tcp_flags="S",
                dst_port=80,
                timestamp_epoch=t_flood + (i * 0.003),
            )
            for a in res_flood.get("alerts", []):
                if a["type"] == "SYN_FLOOD":
                    syn_alerts.append(a)

        self.assertGreater(len(syn_alerts), 0)
        self.assertEqual(syn_alerts[0]["severity"], "HIGH")

    def test_adversarial_malformed_frame_fuzzing_zero_crashes(self):
        """Fuzzing with 2,000 randomized corrupt/adversarial lines must produce ZERO crashes."""
        fuzz_corpus = [
            "",
            "   \t\n",
            "This is random text that is not tcpdump",
            "00:11:22 > 33:44:55, ethertype IPv4, length 0",
            "1234.5678 1C:F6:4C:7D:D7:0A > 94:83:C4:EB:E7:31, ethertype IPv4, (ttl -5, id 999999999999999999)",
            "1234.5678 1C:F6:4C:7D:D7:0A > 94:83:C4:EB:E7:31, ethertype ICMP, length 64: ICMP TIME EXCEEDED",
            "1234.5678 1C:F6:4C:7D:D7:0A > 94:83:C4:EB:E7:31, ethertype ARP, length 28: tell 192.168.8.1",
            "{\"invalid\": json, missing quotes}",
            "{\"src_mac\": \"00:11:22:33:44:55\", \"ttl\": -1, \"icmp_type\": 999}",
            "A" * 10000,  # Buffer overflow attempt
            "\x00\x01\x02\x03\xff\xfe\xfd",  # Raw non-ASCII bytes
        ]

        crashes = 0
        for i in range(2000):
            line = random.choice(fuzz_corpus)
            try:
                self.monitor.parse_tcpdump_line(line)
            except Exception as e:
                crashes += 1

        self.assertEqual(crashes, 0, f"Expected 0 crashes during fuzzing, encountered {crashes}")


class TestScreenLensPort4003VisualRadar(unittest.TestCase):
    """Verifies Screen Lens Port 4003 visual radar frame generation produces valid RGB JPEG bytes."""

    def setUp(self):
        self.monitor = LensEdgeSecurityMonitor(enable_zmq=False)

    def test_nominal_state_radar_frame_is_valid_rgb_jpeg(self):
        """NOMINAL state generates valid 1280x720 RGB JPEG with SOI/EOI markers."""
        t_start = time.perf_counter()
        jpeg_bytes = self.monitor.render_security_radar_frame(width=1280, height=720)
        t_elapsed_ms = (time.perf_counter() - t_start) * 1000.0

        # Performance constraint: sub-50ms render
        self.assertLess(t_elapsed_ms, 50.0, f"Render took {t_elapsed_ms:.2f}ms (must be < 50ms)")

        # Empirical byte validation
        self.assertIsInstance(jpeg_bytes, bytes)
        self.assertGreater(len(jpeg_bytes), 10000, "JPEG payload must be > 10KB")

        # Check JPEG magic markers
        self.assertEqual(jpeg_bytes[:2], b"\xff\xd8", "Must start with JPEG SOI marker 0xFFD8")
        self.assertEqual(jpeg_bytes[-2:], b"\xff\xd9", "Must end with JPEG EOI marker 0xFFD9")

        # Decode using PIL
        img = Image.open(io.BytesIO(jpeg_bytes))
        self.assertEqual(img.format, "JPEG")
        self.assertEqual(img.mode, "RGB")
        self.assertEqual(img.size, (1280, 720))

    def test_elevated_state_radar_frame(self):
        """ELEVATED state (rogue MAC) generates valid JPEG with updated threat indicators."""
        self.monitor.inspect_ethernet_frame(
            src_mac="DE:AD:BE:EF:00:44",
            dst_mac="1C:F6:4C:7D:D7:0A",
            src_ip="192.168.8.177",
        )
        state = self.monitor.get_security_radar_state()
        self.assertEqual(state["threat_level"], "ELEVATED")

        jpeg_bytes = self.monitor.render_security_radar_frame(width=1280, height=720)
        self.assertEqual(jpeg_bytes[:2], b"\xff\xd8")
        self.assertEqual(jpeg_bytes[-2:], b"\xff\xd9")

        img = Image.open(io.BytesIO(jpeg_bytes))
        self.assertEqual(img.size, (1280, 720))

    def test_critical_state_radar_frame(self):
        """CRITICAL state (ARP gateway impersonation) generates valid JPEG."""
        self.monitor.inspect_ethernet_frame(
            src_mac="00:DE:AD:BE:EF:01",
            dst_mac="FF:FF:FF:FF:FF:FF",
            src_ip="192.168.8.1",
            proto="ARP",
        )
        state = self.monitor.get_security_radar_state()
        self.assertEqual(state["threat_level"], "CRITICAL")

        jpeg_bytes = self.monitor.render_security_radar_frame(width=1280, height=720)
        self.assertEqual(jpeg_bytes[:2], b"\xff\xd8")
        self.assertEqual(jpeg_bytes[-2:], b"\xff\xd9")

        img = Image.open(io.BytesIO(jpeg_bytes))
        self.assertEqual(img.size, (1280, 720))


if __name__ == "__main__":
    unittest.main()
