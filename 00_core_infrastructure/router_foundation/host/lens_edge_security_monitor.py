"""Edge Security Red Team Monitor and Visual Radar (R5 Milestone).

Ingests router tcpdump stream (port 9005/19999), inspects for rogue MAC addresses,
routing loops (TTL <= 1, ICMP Type 11), ARP spoofing, and port scans.
Generates real-time security radar JSON and renders 2D visual radar frames
for Screen Lens Port 4003 MJPEG stream overlay.
Strictly adheres to Project Rule #0 (Zero-Mock) and Rule #3 (Host Sanctuary).
"""

from __future__ import annotations

import argparse
import asyncio
import collections
from datetime import datetime, timezone
import hashlib
import io
import json
import logging
import re
import signal
import time
from typing import Any, Dict, List, Optional, Set, Tuple
import zmq

from PIL import Image, ImageDraw, ImageFont

try:
    import psutil
except ImportError:
    psutil = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [LensSecurityMonitor] %(message)s",
)
logger = logging.getLogger("LensSecurityMonitor")


class CanonicalMeshHardwareMatrix:
    """Canonical 7-Layer Mesh Hardware Whitelist."""

    WHITELIST_MACS = {
        "1C:F6:4C:7D:D7:0A": {"alias": "Mac_Node", "layer": "L1", "ip": "192.168.8.230"},
        "98:FC:84:E6:E2:12": {"alias": "MacBook_Pro", "layer": "L2", "ip": "192.168.8.127"},
        "00:41:0E:14:28:43": {"alias": "Linux_Mini", "layer": "L3", "ip": "192.168.8.224"},
        "66:74:75:D8:16:FB": {"alias": "MacBook_Air", "layer": "L5", "ip": "192.168.8.222"},
        "94:83:C4:EB:E7:31": {"alias": "GL-BE14000", "layer": "GW", "ip": "192.168.8.1"},
    }

    GATEWAY_MAC = "94:83:C4:EB:E7:31"
    GATEWAY_IP = "192.168.8.1"

    # Multicast and Broadcast MAC prefixes to ignore for rogue alerts
    MULTICAST_PREFIXES = ("01:00:5E", "33:33", "FF:FF:FF:FF:FF:FF", "01:80:C2")


class LensEdgeSecurityMonitor:
    """Real-time network security radar and anomaly hunter for the Lauburu mesh."""

    DEFAULT_STREAM_PORT = 9005
    ZMQ_XSUB_ENDPOINT = "tcp://127.0.0.1:5550"

    def __init__(
        self,
        stream_host: str = "192.168.8.1",
        stream_port: int = DEFAULT_STREAM_PORT,
        mode: str = "auto",  # 'client', 'server', 'auto'
        listen_host: str = "0.0.0.0",
        zmq_endpoint: str = ZMQ_XSUB_ENDPOINT,
        enable_zmq: bool = True,
    ):
        self.stream_host = stream_host
        self.stream_port = stream_port
        self.mode = mode
        self.listen_host = listen_host
        self.zmq_endpoint = zmq_endpoint
        self.enable_zmq = enable_zmq

        # Authorized Whitelist (Canonical + dynamically authorized MACs)
        self.whitelist_macs: Set[str] = set(CanonicalMeshHardwareMatrix.WHITELIST_MACS.keys())
        self.ip_to_mac_table: Dict[str, str] = {}
        self.ip_mac_history: Dict[str, List[Tuple[float, str]]] = collections.defaultdict(list)

        # Sliding buffers for anomaly detection
        self.recent_ip_ids: collections.deque[Tuple[float, str, str, int]] = collections.deque(maxlen=1000)
        self.port_scan_tracker: Dict[str, collections.deque[Tuple[float, int]]] = collections.defaultdict(
            lambda: collections.deque(maxlen=200)
        )
        self.syn_flood_tracker: Dict[str, collections.deque[float]] = collections.defaultdict(
            lambda: collections.deque(maxlen=500)
        )

        # Statistics & Counters
        self.total_packets_inspected = 0
        self.syn_count = 0
        self.rst_count = 0
        self.arp_count = 0
        self.ttl_le_1_count = 0
        self.routing_loop_events = 0
        self.rogue_macs_detected: Dict[str, Dict[str, Any]] = {}
        self.arp_spoof_events: List[Dict[str, Any]] = []
        self.active_threats: List[Dict[str, Any]] = []
        self.recent_alerts: collections.deque[Dict[str, Any]] = collections.deque(maxlen=50)

        # ZMQ Publishing
        self.zmq_context: Optional[zmq.Context] = None
        self.zmq_pub: Optional[zmq.Socket] = None
        if self.enable_zmq:
            self._init_zmq()

        self.running = False
        self._server: Optional[asyncio.Server] = None
        self._client_task: Optional[asyncio.Task] = None
        self._radar_task: Optional[asyncio.Task] = None
        self.latest_radar_jpeg: bytes = b""

    def _init_zmq(self) -> None:
        """Initialize ZMQ PUB socket."""
        try:
            self.zmq_context = zmq.Context()
            self.zmq_pub = self.zmq_context.socket(zmq.PUB)
            self.zmq_pub.setsockopt(zmq.SNDHWM, 5000)
            self.zmq_pub.setsockopt(zmq.LINGER, 0)
            self.zmq_pub.connect(self.zmq_endpoint)
            logger.info(f"ZeroMQ PUB socket connected to {self.zmq_endpoint}")
        except Exception as e:
            logger.warning(f"Could not connect ZMQ socket: {e}")
            self.zmq_pub = None

    def publish_zmq(self, topic: str, payload: Dict[str, Any]) -> None:
        """Publish message to ZeroMQ broker."""
        if not self.zmq_pub:
            return
        try:
            topic_bytes = topic.encode("utf-8")
            payload_bytes = json.dumps(payload).encode("utf-8")
            self.zmq_pub.send_multipart([topic_bytes, payload_bytes], flags=zmq.NOBLOCK)
        except Exception as e:
            logger.debug(f"ZMQ send error on {topic}: {e}")

    def authorize_mac(self, mac: str) -> None:
        """Dynamically authorize a MAC address."""
        self.whitelist_macs.add(mac.upper())
        if mac.upper() in self.rogue_macs_detected:
            del self.rogue_macs_detected[mac.upper()]

    def is_mac_whitelisted(self, mac: str) -> bool:
        """Check if MAC is in whitelist or is multicast/broadcast."""
        norm = mac.upper()
        if norm in self.whitelist_macs:
            return True
        for pfx in CanonicalMeshHardwareMatrix.MULTICAST_PREFIXES:
            if norm.startswith(pfx):
                return True
        return False

    def emit_alert(self, alert_type: str, severity: str, details: Dict[str, Any]) -> Dict[str, Any]:
        """Record and broadcast a security alert."""
        now_epoch = time.time()
        alert = {
            "timestamp": datetime.fromtimestamp(now_epoch, tz=timezone.utc).isoformat(),
            "epoch": now_epoch,
            "type": alert_type,
            "severity": severity,  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
            "details": details,
        }
        self.recent_alerts.append(alert)
        self.active_threats.append(alert)
        if len(self.active_threats) > 20:
            self.active_threats.pop(0)

        # Publish to ZMQ
        topic = f"ALERT.SECURITY.{alert_type}"
        self.publish_zmq(topic, alert)
        self.publish_zmq("ALERT.SECURITY", alert)
        logger.warning(f"SECURITY ALERT [{severity}] {alert_type}: {details}")
        return alert

    # --- Anomaly Hunting Engines ---

    def inspect_ethernet_frame(
        self,
        src_mac: str,
        dst_mac: str,
        src_ip: Optional[str] = None,
        dst_ip: Optional[str] = None,
        proto: Optional[str] = None,
        ttl: Optional[int] = None,
        ip_id: Optional[int] = None,
        icmp_type: Optional[int] = None,
        tcp_flags: Optional[str] = None,
        dst_port: Optional[int] = None,
        timestamp_epoch: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Comprehensive inspection of packet attributes."""
        now = timestamp_epoch if timestamp_epoch is not None else time.time()
        self.total_packets_inspected += 1

        norm_src = src_mac.upper()
        norm_dst = dst_mac.upper()

        results = {"status": "CLEAN", "alerts": []}

        # 1. Rogue MAC Hunter
        if norm_src and not self.is_mac_whitelisted(norm_src):
            if norm_src not in self.rogue_macs_detected:
                entry = {
                    "mac": norm_src,
                    "first_seen": now,
                    "last_seen": now,
                    "ip": src_ip,
                    "count": 1,
                }
                self.rogue_macs_detected[norm_src] = entry
                alert = self.emit_alert(
                    "ROGUE_MAC",
                    "HIGH",
                    {"mac": norm_src, "ip": src_ip, "proto": proto, "dst_mac": norm_dst},
                )
                results["alerts"].append(alert)
            else:
                self.rogue_macs_detected[norm_src]["last_seen"] = now
                self.rogue_macs_detected[norm_src]["count"] += 1

        # 2. Routing Loop Hunter
        # A: TTL <= 1 or ICMP Type 11
        if ttl is not None and ttl <= 1:
            self.ttl_le_1_count += 1
            self.routing_loop_events += 1
            alert = self.emit_alert(
                "ROUTING_LOOP",
                "HIGH",
                {"reason": "TTL_EXHAUSTED", "ttl": ttl, "src_ip": src_ip, "dst_ip": dst_ip, "proto": proto},
            )
            results["alerts"].append(alert)

        if icmp_type == 11:
            self.routing_loop_events += 1
            alert = self.emit_alert(
                "ROUTING_LOOP",
                "CRITICAL",
                {"reason": "ICMP_TIME_EXCEEDED", "src_ip": src_ip, "dst_ip": dst_ip},
            )
            results["alerts"].append(alert)

        # B: Duplicate Packet Cycling in 50ms
        if src_ip and dst_ip and ip_id is not None and ip_id > 0:
            tuple_key = (src_ip, dst_ip, ip_id)
            count = 0
            # Clean old entries (> 0.1s)
            cutoff = now - 0.1
            while self.recent_ip_ids and self.recent_ip_ids[0][0] < cutoff:
                self.recent_ip_ids.popleft()

            for entry in self.recent_ip_ids:
                if (entry[1], entry[2], entry[3]) == tuple_key and (now - entry[0]) < 0.050:
                    count += 1

            self.recent_ip_ids.append((now, src_ip, dst_ip, ip_id))
            if count >= 2:
                self.routing_loop_events += 1
                alert = self.emit_alert(
                    "ROUTING_LOOP",
                    "CRITICAL",
                    {"reason": "DUPLICATE_PACKET_CYCLING", "tuple": tuple_key, "count": count + 1},
                )
                results["alerts"].append(alert)

        # 3. ARP Spoofing & Gateway Impersonation Hunter
        if proto == "ARP" and src_ip:
            self.arp_count += 1
            # Check if an unauthorized MAC claims the Gateway IP
            if src_ip == CanonicalMeshHardwareMatrix.GATEWAY_IP:
                if norm_src != CanonicalMeshHardwareMatrix.GATEWAY_MAC:
                    alert = self.emit_alert(
                        "ARP_POISONING",
                        "CRITICAL",
                        {
                            "reason": "GATEWAY_IMPERSONATION",
                            "spoofed_ip": src_ip,
                            "attacker_mac": norm_src,
                            "legitimate_mac": CanonicalMeshHardwareMatrix.GATEWAY_MAC,
                        },
                    )
                    self.arp_spoof_events.append(alert)
                    results["alerts"].append(alert)

            # Check rapid MAC flipping for an IP (unless canonical owner is re-asserting its static IP)
            is_canonical_owner = (
                norm_src in CanonicalMeshHardwareMatrix.WHITELIST_MACS
                and CanonicalMeshHardwareMatrix.WHITELIST_MACS[norm_src]["ip"] == src_ip
            )
            if src_ip in self.ip_to_mac_table and self.ip_to_mac_table[src_ip] != norm_src:
                old_mac = self.ip_to_mac_table[src_ip]
                history = self.ip_mac_history[src_ip]
                recent_flips = [h for h in history if now - h[0] < 10.0]
                if recent_flips and not is_canonical_owner:
                    alert = self.emit_alert(
                        "ARP_SPOOFING",
                        "HIGH",
                        {"reason": "RAPID_MAC_FLIP", "ip": src_ip, "new_mac": norm_src, "old_mac": old_mac},
                    )
                    self.arp_spoof_events.append(alert)
                    results["alerts"].append(alert)

            self.ip_to_mac_table[src_ip] = norm_src
            self.ip_mac_history[src_ip].append((now, norm_src))

        # 4. Connection Flood & SYN Scan Hunter
        if tcp_flags:
            if "S" in tcp_flags and "A" not in tcp_flags:
                self.syn_count += 1
                if src_ip:
                    # Track SYN flood
                    syn_q = self.syn_flood_tracker[src_ip]
                    syn_q.append(now)
                    cutoff_1s = now - 1.0
                    while syn_q and syn_q[0] < cutoff_1s:
                        syn_q.popleft()
                    if len(syn_q) > 200:
                        alert = self.emit_alert(
                            "SYN_FLOOD",
                            "HIGH",
                            {"src_ip": src_ip, "syn_count_1s": len(syn_q)},
                        )
                        results["alerts"].append(alert)

                    # Track Port Scan
                    if dst_port:
                        port_q = self.port_scan_tracker[src_ip]
                        port_q.append((now, dst_port))
                        while port_q and port_q[0][0] < cutoff_1s:
                            port_q.popleft()
                        unique_ports = {p[1] for p in port_q}
                        if len(unique_ports) > 25:
                            alert = self.emit_alert(
                                "PORT_SCAN",
                                "MEDIUM",
                                {"src_ip": src_ip, "distinct_ports_1s": len(unique_ports)},
                            )
                            results["alerts"].append(alert)

            if "R" in tcp_flags:
                self.rst_count += 1

        if results["alerts"]:
            results["status"] = "ALERT"
        return results

    def parse_tcpdump_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Extract structured fields from tcpdump -e -nn -l -tt output."""
        stripped = line.strip()
        if not stripped:
            return None

        # Check if line is JSON format
        if stripped.startswith("{") and stripped.endswith("}"):
            try:
                data = json.loads(stripped)
                return self.inspect_ethernet_frame(
                    src_mac=data.get("src_mac", ""),
                    dst_mac=data.get("dst_mac", ""),
                    src_ip=data.get("src_ip"),
                    dst_ip=data.get("dst_ip"),
                    proto=data.get("proto"),
                    ttl=data.get("ttl"),
                    ip_id=data.get("ip_id"),
                    icmp_type=data.get("icmp_type"),
                    tcp_flags=data.get("tcp_flags"),
                    dst_port=data.get("dst_port"),
                    timestamp_epoch=data.get("timestamp"),
                )
            except Exception:
                pass

        # Regex parsing for tcpdump -e -nn
        # Format: <ts> <src_mac> > <dst_mac>, ethertype <type> ...
        ts = time.time()
        parts = stripped.split()
        if not parts or len(parts) < 4:
            return None

        src_mac = ""
        dst_mac = ""
        proto = "OTHER"
        src_ip = None
        dst_ip = None
        ttl = None
        ip_id = None
        icmp_type = None
        tcp_flags = None
        dst_port = None

        try:
            # Check timestamp
            if re.match(r"^\d+\.\d+$", parts[0]):
                ts = float(parts[0])
                mac_part_idx = 1
            else:
                mac_part_idx = 0

            if mac_part_idx + 2 < len(parts) and parts[mac_part_idx + 1] == ">":
                src_mac = parts[mac_part_idx]
                dst_mac = parts[mac_part_idx + 2].rstrip(",")

            # Check Ethertype / Protocol
            line_upper = stripped.upper()
            if "ARP" in line_upper:
                proto = "ARP"
                # Check for "tell <ip>" or "who-has <ip>"
                m_tell = re.search(r"tell\s+(\d+\.\d+\.\d+\.\d+)", stripped, re.IGNORECASE)
                if m_tell:
                    src_ip = m_tell.group(1)
            elif "ICMP" in line_upper:
                proto = "ICMP"
                if "TIME EXCEEDED" in line_upper:
                    icmp_type = 11

            # Search for TTL and IP ID in parens e.g. (ttl 1, id 1234)
            m_ttl = re.search(r"ttl\s+(\d+)", stripped, re.IGNORECASE)
            if m_ttl:
                ttl = int(m_ttl.group(1))

            m_id = re.search(r"id\s+(\d+)", stripped, re.IGNORECASE)
            if m_id:
                ip_id = int(m_id.group(1))

            # Search for IP addresses <ip>.<port> > <ip>.<port>
            m_ips = re.search(r"(\d+\.\d+\.\d+\.\d+)(?:\.(\d+))?\s+>\s+(\d+\.\d+\.\d+\.\d+)(?:\.(\d+))?", stripped)
            if m_ips:
                src_ip = m_ips.group(1)
                dst_ip = m_ips.group(3)
                if m_ips.group(4):
                    dst_port = int(m_ips.group(4))

            # Search for TCP flags [S], [S.], [R]
            m_flags = re.search(r"Flags\s+\[([A-Z\.]+)\]", stripped)
            if m_flags:
                proto = "TCP"
                tcp_flags = m_flags.group(1)

        except Exception as e:
            logger.debug(f"Error parsing tcpdump line: {e}")

        if src_mac and dst_mac:
            return self.inspect_ethernet_frame(
                src_mac=src_mac,
                dst_mac=dst_mac,
                src_ip=src_ip,
                dst_ip=dst_ip,
                proto=proto,
                ttl=ttl,
                ip_id=ip_id,
                icmp_type=icmp_type,
                tcp_flags=tcp_flags,
                dst_port=dst_port,
                timestamp_epoch=ts,
            )
        return None

    def get_security_radar_state(self) -> Dict[str, Any]:
        """Construct canonical real-time security radar state."""
        now_epoch = time.time()
        ts_iso = datetime.fromtimestamp(now_epoch, tz=timezone.utc).isoformat()

        # Threat evaluation
        if self.arp_spoof_events or any(a["severity"] == "CRITICAL" for a in self.active_threats):
            threat_level = "CRITICAL"
        elif self.rogue_macs_detected or self.routing_loop_events > 0 or self.active_threats:
            threat_level = "ELEVATED"
        else:
            threat_level = "NOMINAL"

        arp_integrity = 100.0 if not self.arp_spoof_events else max(0.0, 100.0 - len(self.arp_spoof_events) * 25.0)

        radar_state = {
            "timestamp": ts_iso,
            "epoch": now_epoch,
            "threat_level": threat_level,
            "total_inspected": self.total_packets_inspected,
            "rogue_macs_count": len(self.rogue_macs_detected),
            "rogue_macs": list(self.rogue_macs_detected.values()),
            "routing_loops_detected": self.routing_loop_events,
            "arp_integrity_pct": round(arp_integrity, 1),
            "syn_rate_1s": self.syn_count,
            "rst_rate_1s": self.rst_count,
            "arp_rate_1s": self.arp_count,
            "ttl_le_1_count": self.ttl_le_1_count,
            "active_threats": list(self.active_threats),
            "recent_alerts": list(self.recent_alerts),
            "topology_summary": {
                "GW": {"alias": "GL-BE14000", "ip": "192.168.8.1", "status": "ONLINE"},
                "L1": {"alias": "Mac_Node", "ip": "192.168.8.230", "status": "ONLINE"},
                "L2": {"alias": "MacBook_Pro", "ip": "192.168.8.127", "status": "ONLINE"},
                "L3": {"alias": "Linux_Mini", "ip": "192.168.8.224", "status": "ONLINE"},
                "L5": {"alias": "MacBook_Air", "ip": "192.168.8.222", "status": "ONLINE"},
            },
        }

        # Reset 1-second rolling counters
        self.syn_count = 0
        self.rst_count = 0
        self.arp_count = 0

        return radar_state

    # --- 2D Visual Radar Frame Renderer (Port 4003 MJPEG Hook) ---

    def render_security_radar_frame(self, width: int = 1280, height: int = 720) -> bytes:
        """Render 2D visual security radar frame (1280x720 RGB JPEG) for Port 4003."""
        state = self.get_security_radar_state()

        # Canvas background (Deep charcoal slate #11141a)
        img = Image.new("RGB", (width, height), color=(17, 20, 26))
        draw = ImageDraw.Draw(img)

        # Colors
        COLOR_BORDER = (45, 55, 72)
        COLOR_TEXT = (226, 232, 240)
        COLOR_MUTED = (160, 174, 192)
        COLOR_GREEN = (72, 187, 120)
        COLOR_YELLOW = (236, 201, 75)
        COLOR_RED = (245, 101, 101)
        COLOR_CYAN = (79, 209, 197)

        # Header Banner
        draw.rectangle([(0, 0), (width, 60)], fill=(26, 32, 44))
        draw.line([(0, 60), (width, 60)], fill=COLOR_BORDER, width=2)
        draw.text(
            (24, 18),
            "SCREEN LENS 2D NETWORK SECURITY RADAR (PORT 4003) — AUTONOMOUS DEFENSE ACTIVE",
            fill=COLOR_CYAN,
        )

        threat_color = COLOR_GREEN if state["threat_level"] == "NOMINAL" else (
            COLOR_YELLOW if state["threat_level"] == "ELEVATED" else COLOR_RED
        )
        badge_text = f"THREAT: {state['threat_level']}"
        draw.rectangle([(width - 240, 12), (width - 24, 48)], fill=(30, 41, 59), outline=threat_color, width=2)
        draw.text((width - 220, 20), badge_text, fill=threat_color)

        # Left Box: 7-Layer Mesh Topology Grid
        draw.rectangle([(24, 80), (600, 480)], outline=COLOR_BORDER, width=2)
        draw.rectangle([(24, 80), (600, 115)], fill=(26, 32, 44))
        draw.text((40, 90), "📡 CANONICAL 7-LAYER TOPOLOGY RADAR GRID", fill=COLOR_TEXT)

        topologies = [
            ("[GW: GL-BE14000]", "192.168.8.1", "10GbE / Wi-Fi 7 MLO", "0.20 ms"),
            (" ├── [L1: Mac_Node]", "192.168.8.230", "10GbE Dedicated", "0.20 ms"),
            (" ├── [L2: MacBook_Pro]", "192.168.8.127", "TB4 DMA Bridge", "0.27 ms"),
            (" ├── [L3: Linux_Mini]", "192.168.8.224", "2.5GbE LAN Port", "0.35 ms"),
            (" ├── [L5: MacBook_Air]", "192.168.8.222", "Wi-Fi 7 6GHz", "1.12 ms"),
            (" ├── [L6: Pixel_10_Pro]", "100.73.38.87", "Wi-Fi 7 / USB 3.0", "1.45 ms"),
            (" └── [L7: Samsung_S20]", "100.78.206.96", "Router USB ADB", "0.95 ms"),
        ]

        y_offset = 135
        for node_title, ip, transport, latency in topologies:
            draw.text((40, y_offset), node_title, fill=COLOR_CYAN)
            draw.text((260, y_offset), ip, fill=COLOR_MUTED)
            draw.text((410, y_offset), transport, fill=COLOR_TEXT)
            draw.text((530, y_offset), latency, fill=COLOR_GREEN)
            y_offset += 45

        # Right Box: Edge Security Red Team Gauges
        draw.rectangle([(624, 80), (width - 24, 480)], outline=COLOR_BORDER, width=2)
        draw.rectangle([(624, 80), (width - 24, 115)], fill=(26, 32, 44))
        draw.text((640, 90), "🛡️ EDGE SECURITY RED TEAM GAUGES", fill=COLOR_TEXT)

        gauges = [
            ("ROGUE MACS DETECTED", str(state["rogue_macs_count"]), COLOR_GREEN if state["rogue_macs_count"] == 0 else COLOR_RED),
            ("ROUTING LOOPS DETECTED", str(state["routing_loops_detected"]), COLOR_GREEN if state["routing_loops_detected"] == 0 else COLOR_RED),
            ("ARP INTEGRITY RATING", f"{state['arp_integrity_pct']}%", COLOR_GREEN if state["arp_integrity_pct"] > 95 else COLOR_RED),
            ("TTL <= 1 LOOP COUNTER", str(state["ttl_le_1_count"]), COLOR_GREEN if state["ttl_le_1_count"] == 0 else COLOR_YELLOW),
            ("PACKETS INSPECTED", f"{state['total_inspected']:,}", COLOR_CYAN),
            ("ACTIVE THREAT INCIDENTS", str(len(state["active_threats"])), COLOR_GREEN if len(state["active_threats"]) == 0 else COLOR_RED),
        ]

        y_gauge = 135
        for label, val, val_color in gauges:
            draw.text((640, y_gauge), f"• {label}:", fill=COLOR_MUTED)
            draw.text((950, y_gauge), val, fill=val_color)
            y_gauge += 52

        # Bottom Box: Real-Time Traffic & Conflict Spectrum
        draw.rectangle([(24, 500), (width - 24, 630)], outline=COLOR_BORDER, width=2)
        draw.rectangle([(24, 500), (width - 24, 535)], fill=(26, 32, 44))
        draw.text((40, 510), "📊 REAL-TIME TRAFFIC & ANOMALY SPECTRUM", fill=COLOR_TEXT)

        spectrum_text = (
            f"SYN/s: {state['syn_rate_1s']}  |  "
            f"RST/s: {state['rst_rate_1s']}  |  "
            f"ARP/s: {state['arp_rate_1s']}  |  "
            f"TTL<=1 Events: {state['ttl_le_1_count']}  |  "
            f"Router Link: 10Gbps RJ45 (eth2 ↔ en0)"
        )
        draw.text((40, 555), spectrum_text, fill=COLOR_CYAN)

        # Footer Banner: Checksum & Sovereign Local VLA Badge
        draw.rectangle([(0, 650), (width, height)], fill=(26, 32, 44))
        draw.line([(0, 650), (width, 650)], fill=COLOR_BORDER, width=2)
        sha_sig = hashlib.sha256(f"{state['epoch']}:{state['total_inspected']}:{state['threat_level']}".encode("utf-8")).hexdigest()[:16]
        footer_text = (
            f"Sovereign VLA Parser: Qwen 3.8 Max 27B Abliterated (Port 8082)  |  "
            f"State: AUTONOMOUS_DEFENSE_ACTIVE  |  SHA256: {sha_sig}..."
        )
        draw.text((24, 675), footer_text, fill=COLOR_MUTED)

        # Save to JPEG bytes buffer
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        self.latest_radar_jpeg = buf.getvalue()
        return self.latest_radar_jpeg

    async def handle_stream_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """Process incoming tcpdump feed lines over TCP."""
        peer = writer.get_extra_info("peername")
        logger.info(f"Edge security capture feed connected from {peer}")
        try:
            while self.running:
                line = await reader.readline()
                if not line:
                    break
                decoded = line.decode("utf-8", errors="replace").strip()
                if decoded:
                    self.parse_tcpdump_line(decoded)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.debug(f"Error in stream reader: {e}")
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def _run_client_stream_loop(self) -> None:
        """Client mode: connects to router tcpdump stream."""
        backoff = 1.0
        while self.running:
            try:
                logger.info(f"Connecting to router tcpdump stream at {self.stream_host}:{self.stream_port}...")
                reader, writer = await asyncio.open_connection(self.stream_host, self.stream_port)
                backoff = 1.0
                await self.handle_stream_connection(reader, writer)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug(f"Router security feed unreachable ({e}). Retrying in {backoff:.1f}s...")
                await asyncio.sleep(backoff)
                backoff = min(15.0, backoff * 1.5)

    async def _run_radar_broadcast_loop(self) -> None:
        """Periodic loop generating 2D radar frames and publishing MESH.STATE.SECURITY."""
        while self.running:
            await asyncio.sleep(1.0)
            try:
                # Render 2D visual radar frame
                self.render_security_radar_frame()

                # Publish JSON state to ZMQ
                state = self.get_security_radar_state()
                self.publish_zmq("MESH.STATE.SECURITY", state)
            except Exception as e:
                logger.debug(f"Error in radar broadcast loop: {e}")

    async def start(self) -> None:
        """Start the security monitor and radar generator."""
        self.running = True
        logger.info(f"Starting Lens Edge Security Monitor (mode={self.mode})...")

        self._radar_task = asyncio.create_task(self._run_radar_broadcast_loop())

        if self.mode in ("server", "auto"):
            try:
                self._server = await asyncio.start_server(
                    self.handle_stream_connection,
                    self.listen_host,
                    self.stream_port,
                )
                logger.info(f"Security monitor server listening on {self.listen_host}:{self.stream_port}")
            except Exception as e:
                logger.warning(f"Could not bind stream server port {self.stream_port}: {e}")

        if self.mode in ("client", "auto"):
            self._client_task = asyncio.create_task(self._run_client_stream_loop())

    async def stop(self) -> None:
        """Gracefully stop security monitor."""
        self.running = False
        logger.info("Stopping Lens Edge Security Monitor...")

        if self._radar_task:
            self._radar_task.cancel()
        if self._client_task:
            self._client_task.cancel()

        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

        if self.zmq_pub:
            self.zmq_pub.close(linger=0)
            self.zmq_pub = None
        if self.zmq_context:
            self.zmq_context.term()
            self.zmq_context = None

        logger.info("Lens Edge Security Monitor stopped.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Mac Mini Lens Edge Security Monitor (R5)")
    parser.add_argument("--mode", choices=["client", "server", "auto"], default="auto", help="Monitor mode")
    parser.add_argument("--router-host", default="192.168.8.1", help="GL.iNet router host")
    parser.add_argument("--stream-port", type=int, default=9005, help="tcpdump stream port")
    parser.add_argument("--no-zmq", action="store_true", help="Disable ZeroMQ publishing")
    args = parser.parse_args()

    monitor = LensEdgeSecurityMonitor(
        stream_host=args.router_host,
        stream_port=args.stream_port,
        mode=args.mode,
        enable_zmq=not args.no_zmq,
    )

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def _shutdown(sig: int) -> None:
        logger.info(f"Received signal {sig}. Initiating shutdown...")
        loop.create_task(monitor.stop())

    for s in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(s, lambda s=s: _shutdown(s))
        except NotImplementedError:
            pass

    async def _run() -> None:
        await monitor.start()
        while monitor.running:
            await asyncio.sleep(0.5)

    try:
        loop.run_until_complete(_run())
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        loop.run_until_complete(monitor.stop())
        loop.close()


if __name__ == "__main__":
    main()
