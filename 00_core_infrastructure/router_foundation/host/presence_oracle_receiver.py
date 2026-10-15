"""DHCP & ARP Presence Oracle Receiver (Mac Mini Host - R3 Milestone).

High-speed AsyncIO UDP and TCP listener on port 9100 ingesting router DHCP lease
and ARP neighbor notifications, resolving nodes against the Canonical Mesh Hardware
Matrix, and publishing sub-2-second presence state to the ZeroMQ broker (tcp://127.0.0.1:5550)
on topics MESH.TELEMETRY.PRESENCE and MESH.STATE.PRESENCE.
Strictly adheres to Project Rule #0 (Zero-Mock) and Rule #3 (Host Sanctuary).
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import json
import logging
import signal
import time
from typing import Any, Dict, List, Optional, Tuple
import zmq

try:
    import psutil
except ImportError:
    psutil = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [PresenceOracle] %(message)s",
)
logger = logging.getLogger("PresenceOracle")


class CanonicalMeshRegistry:
    """Canonical 7-Layer Mesh Hardware Matrix Registry for instant MAC/IP mapping."""

    CANONICAL_MATRIX = {
        "1C:F6:4C:7D:D7:0A": {"alias": "Mac_Node", "layer": "L1", "role": "Primary Host & Memory Governor", "ip": "192.168.8.230"},
        "98:FC:84:E6:E2:12": {"alias": "MacBook_Pro", "layer": "L2", "role": "Metal GPU RPC & Storage Vault", "ip": "192.168.8.127"},
        "00:41:0E:14:28:43": {"alias": "Linux_Mini", "layer": "L3", "role": "Gateway Ingress & Compute Hub", "ip": "192.168.8.224"},
        "66:74:75:D8:16:FB": {"alias": "MacBook_Air", "layer": "L5", "role": "Secondary High-Speed Metal Worker", "ip": "192.168.8.222"},
        "94:83:C4:EB:E7:31": {"alias": "GL.iNet Router", "layer": "GW", "role": "Core Gateway & Hardware USB Bridge", "ip": "192.168.8.1"},
    }

    # Common edge devices with known hostnames or partial OUI prefixes
    KNOWN_HOSTNAMES = {
        "pixel-10": {"alias": "Pixel_10_Pro_XL", "layer": "L6", "role": "8K Vision Stream & Edge TPU"},
        "pixel10": {"alias": "Pixel_10_Pro_XL", "layer": "L6", "role": "8K Vision Stream & Edge TPU"},
        "samsung-s20": {"alias": "Samsung_S20", "layer": "L7", "role": "Dedicated Automated UI Tester"},
        "galaxy-s20": {"alias": "Samsung_S20", "layer": "L7", "role": "Dedicated Automated UI Tester"},
        "linux-tablet": {"alias": "Linux_Tablet", "layer": "L4", "role": "Mobile Linux Compute & Touch DSP"},
    }

    @classmethod
    def resolve_device(cls, mac: str, hostname: str = "", ip: str = "") -> Dict[str, Any]:
        """Resolve MAC/hostname/IP to canonical mesh node metadata."""
        norm_mac = mac.upper()
        if norm_mac in cls.CANONICAL_MATRIX:
            entry = dict(cls.CANONICAL_MATRIX[norm_mac])
            entry["is_canonical_mesh"] = True
            return entry

        # Check hostname
        norm_host = (hostname or "").lower()
        for k, v in cls.KNOWN_HOSTNAMES.items():
            if k in norm_host:
                entry = dict(v)
                entry["is_canonical_mesh"] = True
                entry["ip"] = ip
                return entry

        # Check IP
        for entry_mac, entry_val in cls.CANONICAL_MATRIX.items():
            if ip and entry_val.get("ip") == ip:
                e = dict(entry_val)
                e["is_canonical_mesh"] = True
                return e

        return {
            "alias": hostname or f"Client_{norm_mac[-5:].replace(':', '')}",
            "layer": "PERIPHERAL",
            "role": "General Network Client",
            "ip": ip,
            "is_canonical_mesh": False,
        }


class PresenceOracleReceiver(asyncio.DatagramProtocol):
    """Dual UDP & TCP listener for DHCP/ARP presence events with ZMQ publication."""

    DEFAULT_PORT = 9100
    ZMQ_XSUB_ENDPOINT = "tcp://127.0.0.1:5550"

    def __init__(
        self,
        listen_host: str = "0.0.0.0",
        listen_port: int = DEFAULT_PORT,
        zmq_endpoint: str = ZMQ_XSUB_ENDPOINT,
        enable_zmq: bool = True,
    ):
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.zmq_endpoint = zmq_endpoint
        self.enable_zmq = enable_zmq

        self.running = False
        self.total_events = 0
        self.last_event_time: Optional[float] = None
        self.active_inventory: Dict[str, Dict[str, Any]] = {}

        # ZMQ Context
        self.zmq_context: Optional[zmq.Context] = None
        self.zmq_pub: Optional[zmq.Socket] = None
        if self.enable_zmq:
            self._init_zmq()

        # Server handles
        self.udp_transport: Optional[asyncio.DatagramTransport] = None
        self.tcp_server: Optional[asyncio.Server] = None
        self._periodic_task: Optional[asyncio.Task] = None

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
        """Send multipart message to ZMQ broker [topic_bytes, json_bytes]."""
        if not self.zmq_pub:
            return
        try:
            topic_bytes = topic.encode("utf-8")
            payload_bytes = json.dumps(payload).encode("utf-8")
            self.zmq_pub.send_multipart([topic_bytes, payload_bytes], flags=zmq.NOBLOCK)
        except zmq.ZMQError as e:
            if e.errno != zmq.EAGAIN:
                logger.debug(f"ZMQ send error on {topic}: {e}")
        except Exception as e:
            logger.debug(f"Error publishing {topic}: {e}")

    def process_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming DHCP/ARP presence event, update inventory, and emit telemetry."""
        now_epoch = time.time()
        event_epoch = float(event_data.get("timestamp") or now_epoch)
        propagation_ms = round(max(0.0, (now_epoch - event_epoch) * 1000.0), 2)

        event_type = str(event_data.get("event", "UNKNOWN")).upper()
        mac = str(event_data.get("mac", "")).upper()
        ip = str(event_data.get("ip", ""))
        hostname = str(event_data.get("hostname", ""))
        interface = str(event_data.get("interface", "br-lan"))

        if not mac:
            return {"error": "missing mac address"}

        # Resolve Canonical Mesh device
        device_meta = CanonicalMeshRegistry.resolve_device(mac, hostname=hostname, ip=ip)
        is_online = event_type in ("LEASE_ADD", "NEIGH_UP", "ONLINE", "ACTIVE", "NEIGH_CHANGE")

        # Update inventory record
        inventory_record = {
            "mac": mac,
            "ip": ip or device_meta.get("ip", ""),
            "hostname": hostname,
            "alias": device_meta.get("alias", ""),
            "layer": device_meta.get("layer", ""),
            "role": device_meta.get("role", ""),
            "is_canonical_mesh": device_meta.get("is_canonical_mesh", False),
            "interface": interface,
            "status": "ONLINE" if is_online else "OFFLINE",
            "last_event": event_type,
            "last_seen_epoch": now_epoch,
            "last_seen_iso": datetime.fromtimestamp(now_epoch, tz=timezone.utc).isoformat(),
            "propagation_ms": propagation_ms,
        }
        self.active_inventory[mac] = inventory_record
        self.total_events += 1
        self.last_event_time = now_epoch

        # Construct Canonical ZMQ Telemetry Frame
        presence_telemetry = {
            "timestamp": datetime.fromtimestamp(now_epoch, tz=timezone.utc).isoformat(),
            "epoch": now_epoch,
            "event": event_type,
            "mac": mac,
            "ip": inventory_record["ip"],
            "hostname": hostname,
            "interface": interface,
            "alias": inventory_record["alias"],
            "layer": inventory_record["layer"],
            "role": inventory_record["role"],
            "is_canonical_mesh": inventory_record["is_canonical_mesh"],
            "status": inventory_record["status"],
            "propagation_latency_ms": propagation_ms,
            "sub_2s_propagation_met": propagation_ms < 2000.0,
        }

        # 1. Publish immediate event to MESH.TELEMETRY.PRESENCE
        self.publish_zmq("MESH.TELEMETRY.PRESENCE", presence_telemetry)

        # 2. Publish updated inventory snapshot to MESH.STATE.PRESENCE
        mesh_state = self.get_presence_state()
        self.publish_zmq("MESH.STATE.PRESENCE", mesh_state)

        logger.info(
            f"Presence Event [{event_type}]: {inventory_record['alias']} ({mac} -> {inventory_record['ip']}) "
            f"State: {inventory_record['status']} (Latency: {propagation_ms}ms)"
        )
        return presence_telemetry

    def get_presence_state(self) -> Dict[str, Any]:
        """Returns consolidated snapshot of all active and tracked mesh nodes."""
        now_epoch = time.time()
        online_nodes = [v for v in self.active_inventory.values() if v.get("status") == "ONLINE"]
        mesh_nodes_online = [v for v in online_nodes if v.get("is_canonical_mesh")]

        return {
            "timestamp": datetime.fromtimestamp(now_epoch, tz=timezone.utc).isoformat(),
            "epoch": now_epoch,
            "total_tracked": len(self.active_inventory),
            "online_count": len(online_nodes),
            "canonical_mesh_online": len(mesh_nodes_online),
            "nodes": list(self.active_inventory.values()),
        }

    # --- UDP Protocol Callbacks ---
    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self.udp_transport = transport  # type: ignore

    def datagram_received(self, data: bytes, addr: Tuple[str, int]) -> None:
        """Handle incoming UDP datagram from OpenWrt dnsmasq/arp hook."""
        try:
            line = data.decode("utf-8", errors="replace").strip()
            if line:
                payload = json.loads(line)
                self.process_event(payload)
        except Exception as e:
            logger.debug(f"Failed to decode UDP datagram from {addr}: {e}")

    def error_received(self, exc: Exception) -> None:
        logger.warning(f"UDP socket error: {exc}")

    # --- TCP Protocol Handler ---
    async def handle_tcp_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """Handle TCP connections (e.g. HTTP POST or NDJSON stream) on port 9100."""
        try:
            buffer = bytearray()
            while self.running:
                chunk = await reader.read(4096)
                if not chunk:
                    break
                buffer.extend(chunk)

                # Check if HTTP POST request
                if buffer.startswith(b"POST ") or buffer.startswith(b"GET "):
                    if b"\r\n\r\n" in buffer:
                        header_part, body_part = buffer.split(b"\r\n\r\n", 1)
                        header_text = header_part.decode("utf-8", errors="replace")
                        
                        if header_text.startswith("GET"):
                            # HTTP GET Status Query
                            state = self.get_presence_state()
                            body_resp = json.dumps(state).encode("utf-8")
                            header_resp = (
                                f"HTTP/1.1 200 OK\r\n"
                                f"Content-Type: application/json\r\n"
                                f"Content-Length: {len(body_resp)}\r\n"
                                f"Connection: close\r\n\r\n"
                            ).encode("utf-8")
                            resp = header_resp + body_resp
                            writer.write(resp)
                            await writer.drain()
                            break

                        # Parse Content-Length for POST
                        content_len = 0
                        for line in header_text.split("\r\n"):
                            if line.lower().startswith("content-length:"):
                                content_len = int(line.split(":")[1].strip())

                        if len(body_part) >= content_len:
                            post_json = json.loads(body_part[:content_len].decode("utf-8", errors="replace"))
                            result = self.process_event(post_json)
                            resp_body = json.dumps(result).encode("utf-8")
                            header_resp = (
                                f"HTTP/1.1 200 OK\r\n"
                                f"Content-Type: application/json\r\n"
                                f"Content-Length: {len(resp_body)}\r\n"
                                f"Connection: close\r\n\r\n"
                            ).encode("utf-8")
                            resp = header_resp + resp_body
                            writer.write(resp)
                            await writer.drain()
                            break

                # Raw NDJSON stream handling
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    if line.strip():
                        try:
                            payload = json.loads(line.decode("utf-8", errors="replace"))
                            self.process_event(payload)
                        except Exception:
                            pass
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.debug(f"Error handling TCP client on 9100: {e}")
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def _run_periodic_heartbeat(self) -> None:
        """Publishes periodic snapshot of presence state to keep downstream UI fresh."""
        while self.running:
            await asyncio.sleep(5.0)
            mesh_state = self.get_presence_state()
            self.publish_zmq("MESH.STATE.PRESENCE", mesh_state)

    async def start(self) -> None:
        """Start UDP and TCP listeners on port 9100."""
        self.running = True
        logger.info(f"Starting Presence Oracle Receiver on port {self.listen_port} (UDP/TCP)...")

        loop = asyncio.get_running_loop()

        # 1. Bind UDP Listener
        try:
            transport, _ = await loop.create_datagram_endpoint(
                lambda: self,
                local_addr=(self.listen_host, self.listen_port),
            )
            self.udp_transport = transport
            logger.info(f"Presence Oracle UDP listening on {self.listen_host}:{self.listen_port}")
        except Exception as e:
            logger.warning(f"Failed to bind UDP port {self.listen_port}: {e}")

        # 2. Bind TCP Listener
        try:
            self.tcp_server = await asyncio.start_server(
                self.handle_tcp_client,
                self.listen_host,
                self.listen_port,
            )
            logger.info(f"Presence Oracle TCP listening on {self.listen_host}:{self.listen_port}")
        except Exception as e:
            logger.warning(f"Failed to bind TCP port {self.listen_port}: {e}")

        self._periodic_task = asyncio.create_task(self._run_periodic_heartbeat())

    async def stop(self) -> None:
        """Gracefully stop listeners and release sockets."""
        self.running = False
        logger.info("Stopping Presence Oracle Receiver...")

        if self._periodic_task:
            self._periodic_task.cancel()

        if self.udp_transport:
            self.udp_transport.close()
            self.udp_transport = None

        if self.tcp_server:
            self.tcp_server.close()
            await self.tcp_server.wait_closed()
            self.tcp_server = None

        if self.zmq_pub:
            self.zmq_pub.close(linger=0)
            self.zmq_pub = None
        if self.zmq_context:
            self.zmq_context.term()
            self.zmq_context = None

        logger.info("Presence Oracle Receiver stopped.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Mac Mini Presence Oracle Receiver (R3)")
    parser.add_argument("--host", default="0.0.0.0", help="Listen address")
    parser.add_argument("--port", type=int, default=9100, help="Listen port")
    parser.add_argument("--no-zmq", action="store_true", help="Disable ZeroMQ output")
    args = parser.parse_args()

    receiver = PresenceOracleReceiver(
        listen_host=args.host,
        listen_port=args.port,
        enable_zmq=not args.no_zmq,
    )

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def _shutdown(sig: int) -> None:
        logger.info(f"Received signal {sig}. Initiating shutdown...")
        loop.create_task(receiver.stop())

    for s in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(s, lambda s=s: _shutdown(s))
        except NotImplementedError:
            pass

    async def _run() -> None:
        await receiver.start()
        while receiver.running:
            await asyncio.sleep(0.5)

    try:
        loop.run_until_complete(_run())
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        loop.run_until_complete(receiver.stop())
        loop.close()


if __name__ == "__main__":
    main()
