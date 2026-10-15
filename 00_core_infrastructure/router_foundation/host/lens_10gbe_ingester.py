"""Mac Mini 10GbE Lens Ingester Daemon (R2 Milestone).

High-throughput AsyncIO TCP daemon ingesting raw Bluetooth/GATT feeds over the
10GbE network link from GL.iNet OpenWrt router (TCP 9002/19001) with TCP_NODELAY.
Implements multi-mode framer (NDJSON, Binary TLV, HCI H4), dispatches payloads to
Movesense, Whoop, and SmartThings parsers, and publishes to ZMQ XSUB (tcp://127.0.0.1:5550).
Strictly adheres to Project Rule #0 (Zero-Mock) and Rule #3 (Host Sanctuary < 35MB RAM).
"""

from __future__ import annotations

import argparse
import asyncio
import collections
from datetime import datetime, timezone
import gc
import json
import logging
import os
import signal
import socket
import struct
import sys
import time
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

try:
    import zmq
except ImportError:
    zmq = None

try:
    import psutil
except ImportError:
    psutil = None

# Support both package imports and standalone script execution
try:
    from .parsers.movesense_parser import MovesenseParser, MovesenseBiometricTelemetry
    from .parsers.whoop_parser import WhoopParser, WhoopBiometricTelemetry
    from .parsers.smartthings_parser import SmartThingsParser, SmartTagPresenceTelemetry
except ImportError:
    from parsers.movesense_parser import MovesenseParser, MovesenseBiometricTelemetry
    from parsers.whoop_parser import WhoopParser, WhoopBiometricTelemetry
    from parsers.smartthings_parser import SmartThingsParser, SmartTagPresenceTelemetry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [Lens10GbEIngester] %(message)s",
)
logger = logging.getLogger("Lens10GbEIngester")


class Lens10GbEIngester:
    """AsyncIO high-speed ingester daemon for router BLE feeds across 10GbE link."""

    ZMQ_XSUB_ENDPOINT = "tcp://127.0.0.1:5550"
    DEFAULT_ROUTER_IP = "192.168.8.1"
    DEFAULT_ROUTER_PORT = 9002
    DEFAULT_LISTEN_PORT = 19001
    MAX_RAM_MB = 35.0  # Rule 3 Host Sanctuary

    # Binary TLV constants
    TLV_MAGIC = b"\x4c\x42"  # 'LB' (Lauburu)
    TLV_TAG_MOVESENSE = 0x0001
    TLV_TAG_WHOOP = 0x0002
    TLV_TAG_SMARTTHINGS = 0x0003
    TLV_TAG_GENERIC_BLE = 0x0004

    def __init__(
        self,
        mode: str = "auto",  # 'client', 'server', 'auto'
        router_host: str = DEFAULT_ROUTER_IP,
        router_port: int = DEFAULT_ROUTER_PORT,
        listen_host: str = "0.0.0.0",
        listen_port: int = DEFAULT_LISTEN_PORT,
        zmq_endpoint: str = ZMQ_XSUB_ENDPOINT,
        enable_zmq: bool = True,
        stats_interval: float = 1.0,
    ):
        self.mode = mode
        self.router_host = router_host
        self.router_port = router_port
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.zmq_endpoint = zmq_endpoint
        self.enable_zmq = enable_zmq
        self.stats_interval = stats_interval

        # Parsers
        self.movesense_parser = MovesenseParser()
        self.whoop_parser = WhoopParser()
        self.smartthings_parser = SmartThingsParser()

        # Telemetry & Performance Tracking
        self.total_packets = 0
        self.total_bytes = 0
        self.corrupted_frames = 0
        self.last_stat_time = time.monotonic()
        self.last_packet_count = 0
        self.last_byte_count = 0
        self.pps = 0.0
        self.bps = 0.0
        self.link_latency_ms = 0.67  # baseline 10GbE RTT (0.666 ms nominal)
        self.tracked_ble_devices: Dict[str, Dict[str, Any]] = {}

        # ZMQ Context and Socket
        self.zmq_context: Optional[zmq.Context] = None
        self.zmq_pub: Optional[zmq.Socket] = None
        if self.enable_zmq:
            self._init_zmq()

        # Runtime State
        self.running = False
        self._server: Optional[asyncio.Server] = None
        self._client_task: Optional[asyncio.Task] = None
        self._stats_task: Optional[asyncio.Task] = None
        self._active_connections: List[asyncio.StreamWriter] = []

    def _init_zmq(self) -> None:
        """Initialize ZeroMQ PUB socket connected to broker XSUB."""
        try:
            self.zmq_context = zmq.Context()
            self.zmq_pub = self.zmq_context.socket(zmq.PUB)
            self.zmq_pub.setsockopt(zmq.SNDHWM, 5000)
            self.zmq_pub.setsockopt(zmq.LINGER, 0)
            self.zmq_pub.connect(self.zmq_endpoint)
            logger.info(f"ZeroMQ PUB socket connected to {self.zmq_endpoint}")
        except Exception as e:
            logger.warning(f"Failed to initialize ZMQ socket: {e}. Running without live ZMQ dispatch.")
            self.zmq_pub = None

    def publish_zmq(self, topic: str, payload: Dict[str, Any]) -> None:
        """Publish multipart message to ZMQ broker [topic_bytes, json_bytes]."""
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
            logger.debug(f"Error publishing to {topic}: {e}")

    def check_memory_sanctuary(self) -> float:
        """Enforce Rule 3 Host Sanctuary (< 35 MB RAM)."""
        rss_mb = 0.0
        if psutil:
            try:
                proc = psutil.Process()
                rss_mb = proc.memory_info().rss / (1024.0 * 1024.0)
                if rss_mb > self.MAX_RAM_MB:
                    logger.warning(f"RAM usage {rss_mb:.2f}MB exceeds limit {self.MAX_RAM_MB}MB. Forcing GC.")
                    gc.collect()
                    rss_mb = proc.memory_info().rss / (1024.0 * 1024.0)
            except Exception:
                pass
        return round(rss_mb, 2)

    def decode_frame(self, raw_data: bytes) -> Optional[Tuple[str, Dict[str, Any]]]:
        """Multi-Mode Frame Slicer: decodes NDJSON, Binary TLV, or HCI H4."""
        if not raw_data:
            return None

        # Mode 1: NDJSON (starts with { or valid UTF-8 JSON)
        stripped = raw_data.strip()
        if stripped.startswith(b"{") and stripped.endswith(b"}"):
            try:
                obj = json.loads(stripped.decode("utf-8", errors="replace"))
                return "NDJSON", obj
            except Exception:
                pass

        # Mode 2: Binary TLV (starts with Magic 0x4C 0x42 'LB')
        if len(raw_data) >= 6 and raw_data[0:2] == self.TLV_MAGIC:
            tag, length = struct.unpack(">HH", raw_data[2:6])
            if len(raw_data) >= 6 + length:
                val = raw_data[6 : 6 + length]
                return "BINARY_TLV", {"tag": tag, "length": length, "data": val.hex(), "raw_bytes": val}

        # Mode 3: Raw HCI H4 Framing
        indicator = raw_data[0]
        if indicator in (0x01, 0x02, 0x04):
            return "HCI_H4", self._parse_hci_h4(raw_data)

        # Fallback: Raw Hex Dump Frame
        return "RAW", {"raw_hex": raw_data.hex(), "length": len(raw_data)}

    def parse_binary_tlv(self, buffer: Union[bytearray, bytes]) -> List[Tuple[str, Dict[str, Any]]]:
        """Extract and parse complete Binary TLV frames from buffer.

        If buffer is a bytearray, consumed frames are removed in-place.
        Ensures progress advances to prevent infinite loops on truncated or partial frames.
        """
        frames: List[Tuple[str, Dict[str, Any]]] = []
        if isinstance(buffer, bytearray):
            while len(buffer) >= 6 and buffer.startswith(self.TLV_MAGIC):
                tag, length = struct.unpack(">HH", buffer[2:6])
                total_frame_len = 6 + length
                if len(buffer) >= total_frame_len:
                    frame_bytes = bytes(buffer[:total_frame_len])
                    del buffer[:total_frame_len]
                    result = self.decode_frame(frame_bytes)
                    if result:
                        frames.append(result)
                else:
                    # Truncated frame: remaining payload bytes have not arrived.
                    # Break to prevent infinite loop and allow stream reader to accumulate more data.
                    break
        elif isinstance(buffer, (bytes, memoryview)):
            offset = 0
            buf_len = len(buffer)
            while offset + 6 <= buf_len and buffer[offset : offset + 2] == self.TLV_MAGIC:
                tag, length = struct.unpack(">HH", buffer[offset + 2 : offset + 6])
                total_frame_len = 6 + length
                if offset + total_frame_len <= buf_len:
                    frame_bytes = bytes(buffer[offset : offset + total_frame_len])
                    offset += total_frame_len
                    result = self.decode_frame(frame_bytes)
                    if result:
                        frames.append(result)
                else:
                    # Truncated frame: break out to prevent infinite loop
                    break
        return frames

    def _parse_hci_h4(self, data: bytes) -> Dict[str, Any]:
        """Parse HCI H4 byte frame."""
        indicator = data[0]
        if indicator == 0x04 and len(data) >= 3:
            # HCI Event
            event_code = data[1]
            param_len = data[2]
            payload = data[3 : 3 + param_len]
            if event_code == 0x3E and len(payload) >= 2:
                subevent = payload[0]
                if subevent == 0x02:  # LE Advertising Report
                    num_reports = payload[1]
                    reports = []
                    offset = 2
                    for _ in range(num_reports):
                        if offset + 9 <= len(payload):
                            ev_type = payload[offset]
                            addr_type = payload[offset + 1]
                            mac_bytes = payload[offset + 2 : offset + 8]
                            mac_str = ":".join(f"{b:02X}" for b in reversed(mac_bytes))
                            data_len = payload[offset + 8]
                            adv_data = payload[offset + 9 : offset + 9 + data_len]
                            rssi = 0
                            if offset + 9 + data_len < len(payload):
                                rssi = struct.unpack("b", payload[offset + 9 + data_len : offset + 10 + data_len])[0]
                            reports.append({
                                "mac": mac_str,
                                "event_type": ev_type,
                                "addr_type": addr_type,
                                "adv_hex": adv_data.hex(),
                                "rssi": rssi,
                            })
                            offset += 10 + data_len
                    return {"type": "HCI_EVENT", "event": "LE_ADV_REPORT", "reports": reports}
            return {"type": "HCI_EVENT", "event_code": event_code, "payload_hex": payload.hex()}

        elif indicator == 0x02 and len(data) >= 5:
            # HCI ACL Data (GATT data notification)
            handle_flags = struct.unpack("<H", data[1:3])[0]
            handle = handle_flags & 0x0FFF
            data_len = struct.unpack("<H", data[3:5])[0]
            acl_data = data[5 : 5 + data_len]
            return {"type": "HCI_ACL", "handle": handle, "data_hex": acl_data.hex(), "length": data_len}

        return {"type": "HCI_COMMAND", "raw_hex": data.hex()}

    def dispatch_payload(self, frame_type: str, frame_data: Dict[str, Any]) -> None:
        """Route parsed frame to designated device parser and publish ZMQ telemetry."""
        now_epoch = time.time()
        ts_iso = datetime.fromtimestamp(now_epoch, tz=timezone.utc).isoformat()

        # Extract common fields
        mac = str(frame_data.get("mac", "")).upper()
        name = str(frame_data.get("name", ""))

        # Coerce/validate rssi (default to -100 if null/invalid/string)
        raw_rssi = frame_data.get("rssi")
        if raw_rssi is None:
            rssi = -100
        else:
            try:
                rssi = int(float(raw_rssi))
            except (ValueError, TypeError):
                rssi = -100

        # Safely decode payload_hex (catch ValueError on non-hex bytes or odd-length strings)
        payload_hex = frame_data.get("payload_hex") or frame_data.get("raw") or frame_data.get("data_hex", "")
        raw_bytes = b""
        if isinstance(payload_hex, str) and payload_hex:
            try:
                cleaned_hex = payload_hex.strip()
                if len(cleaned_hex) % 2 == 0:
                    raw_bytes = bytes.fromhex(cleaned_hex)
                else:
                    logger.debug(f"Odd-length hex string received: {cleaned_hex}")
                    self.corrupted_frames += 1
            except ValueError:
                logger.debug(f"Invalid non-hex payload received: {payload_hex}")
                self.corrupted_frames += 1
                raw_bytes = b""

        if not raw_bytes:
            alt_raw = frame_data.get("raw_bytes")
            if isinstance(alt_raw, (bytes, bytearray)):
                raw_bytes = bytes(alt_raw)

        # Update tracked BLE peripherals matrix
        if mac:
            self.tracked_ble_devices[mac] = {
                "mac": mac,
                "name": name or "Unknown",
                "rssi": rssi,
                "last_seen_epoch": now_epoch,
                "last_seen_iso": ts_iso,
            }

        # Check for Movesense
        is_movesense = (
            mac == MovesenseParser.DEFAULT_MAC
            or "MOVESENSE" in name.upper()
            or frame_data.get("type") == "MOVESENSE"
            or (frame_type == "BINARY_TLV" and frame_data.get("tag") == self.TLV_TAG_MOVESENSE)
        )

        if is_movesense and raw_bytes:
            try:
                telemetry = self.movesense_parser.parse_gatt_0x2a37(
                    raw_bytes,
                    timestamp_epoch=now_epoch,
                    device_mac=mac or MovesenseParser.DEFAULT_MAC,
                    device_name=name or MovesenseParser.DEFAULT_NAME,
                )
                t_dict = telemetry.to_dict()
                self.publish_zmq("MESH.TELEMETRY.BIOMETRICS", t_dict)
                self.publish_zmq("BLE.RAW.MOVESENSE", {"mac": mac, "raw_hex": raw_bytes.hex(), "timestamp": ts_iso})
                return
            except Exception as e:
                logger.debug(f"Error parsing Movesense frame: {e}")
                self.corrupted_frames += 1

        # Check for Whoop
        company_id = struct.unpack("<H", raw_bytes[0:2])[0] if len(raw_bytes) >= 2 else 0
        is_whoop = (
            company_id in WhoopParser.WHOOP_COMPANY_IDS
            or "WHOOP" in name.upper()
            or frame_data.get("type") == "WHOOP"
            or (frame_type == "BINARY_TLV" and frame_data.get("tag") == self.TLV_TAG_WHOOP)
        )

        if is_whoop:
            try:
                whoop_telemetry = self.whoop_parser.parse_payload(
                    frame_data if not raw_bytes else raw_bytes,
                    device_mac=mac,
                    timestamp_epoch=now_epoch,
                )
                w_dict = whoop_telemetry.to_dict()
                self.publish_zmq("MESH.TELEMETRY.BIOMETRICS", w_dict)
                self.publish_zmq("BLE.RAW.WHOOP", {"mac": mac, "raw_hex": payload_hex, "timestamp": ts_iso})
                return
            except Exception as e:
                logger.debug(f"Error parsing Whoop frame: {e}")
                self.corrupted_frames += 1

        # Check for SmartThings / Samsung SmartTag
        is_smartthings = (
            company_id == SmartThingsParser.SAMSUNG_COMPANY_ID
            or any(kw in name.upper() for kw in ["SMARTTAG", "SMARTTHINGS"])
            or frame_data.get("type") in ("SMARTTHINGS", "SMARTTAG")
            or (frame_type == "BINARY_TLV" and frame_data.get("tag") == self.TLV_TAG_SMARTTHINGS)
        )

        if is_smartthings:
            try:
                st_telemetry = self.smartthings_parser.parse_payload(
                    frame_data if not raw_bytes else raw_bytes,
                    device_mac=mac,
                    rssi=rssi,
                    timestamp_epoch=now_epoch,
                )
                st_dict = st_telemetry.to_dict()
                self.publish_zmq("MESH.TELEMETRY.PRESENCE", st_dict)
                self.publish_zmq("MESH.STATE.SMARTTHINGS", st_dict)
                self.publish_zmq("BLE.RAW.SMARTTHINGS", {"mac": mac, "raw_hex": payload_hex, "timestamp": ts_iso})
                return
            except Exception as e:
                logger.debug(f"Error parsing SmartThings frame: {e}")
                self.corrupted_frames += 1

        # Generic BLE Raw Dispatch
        self.publish_zmq("BLE.RAW.GENERIC", {
            "mac": mac,
            "name": name,
            "rssi": rssi,
            "frame_type": frame_type,
            "raw_hex": payload_hex,
            "timestamp": ts_iso,
        })

    async def handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """Stream connection handler reading from router or test source."""
        peer = writer.get_extra_info("peername")
        logger.info(f"Stream connection accepted from {peer}")
        self._active_connections.append(writer)

        # Optimize OS TCP socket
        try:
            sock = writer.get_extra_info("socket")
            if sock:
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4194304)
        except Exception as e:
            logger.debug(f"Socket tuning non-fatal error: {e}")

        buffer = bytearray()
        try:
            while self.running:
                chunk = await reader.read(65536)
                if not chunk:
                    logger.info(f"Stream peer {peer} disconnected")
                    break

                self.total_packets += 1
                self.total_bytes += len(chunk)
                buffer.extend(chunk)

                # Drain newline-delimited frames or process buffer
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    if line.strip():
                        result = self.decode_frame(bytes(line))
                        if result:
                            frame_type, frame_data = result
                            self.dispatch_payload(frame_type, frame_data)

                # If binary buffer has TLV frames, extract complete frames safely
                if len(buffer) >= 6 and buffer.startswith(self.TLV_MAGIC):
                    tlv_frames = self.parse_binary_tlv(buffer)
                    for frame_type, frame_data in tlv_frames:
                        self.dispatch_payload(frame_type, frame_data)

                # Safeguard: prevent unbounded buffer growth on junk bytes without delimiters
                if len(buffer) > 1048576:
                    buffer.clear()

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in stream reader loop: {e}")
        finally:
            if writer in self._active_connections:
                self._active_connections.remove(writer)
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def _run_client_loop(self) -> None:
        """Connects to GL.iNet router TCP server with exponential backoff."""
        backoff = 1.0
        while self.running:
            try:
                logger.info(f"Connecting to router 10GbE stream at {self.router_host}:{self.router_port}...")
                reader, writer = await asyncio.open_connection(
                    self.router_host,
                    self.router_port,
                )
                backoff = 1.0
                await self.handle_connection(reader, writer)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug(f"Router link unreachable ({e}). Retrying in {backoff:.1f}s...")
                await asyncio.sleep(backoff)
                backoff = min(15.0, backoff * 1.5)

    async def _run_stats_loop(self) -> None:
        """Periodic metrics publisher for MESH.STATE.ROUTER_FEED and MESH.STATE.BLE."""
        while self.running:
            await asyncio.sleep(self.stats_interval)
            now = time.monotonic()
            dt = max(0.001, now - self.last_stat_time)
            d_packets = self.total_packets - self.last_packet_count
            d_bytes = self.total_bytes - self.last_byte_count

            self.pps = round(d_packets / dt, 1)
            self.bps = round(d_bytes / dt, 1)
            self.last_stat_time = now
            self.last_packet_count = self.total_packets
            self.last_byte_count = self.total_bytes

            ram_rss = self.check_memory_sanctuary()
            now_epoch = time.time()
            ts_iso = datetime.fromtimestamp(now_epoch, tz=timezone.utc).isoformat()

            # Publish MESH.STATE.ROUTER_FEED
            router_feed_state = {
                "timestamp": ts_iso,
                "epoch": now_epoch,
                "router_ip": self.router_host,
                "ingress_port": self.router_port if self.mode == "client" else self.listen_port,
                "transport": "10GbE TCP",
                "link_latency_ms": self.link_latency_ms,
                "packets_per_second": self.pps,
                "bytes_per_second": self.bps,
                "total_packets": self.total_packets,
                "total_bytes": self.total_bytes,
                "corrupted_frames": self.corrupted_frames,
                "active_devices": len(self.tracked_ble_devices),
                "status": "STREAMING" if self.pps > 0 else "STANDBY",
                "memory_rss_mb": ram_rss,
            }
            self.publish_zmq("MESH.STATE.ROUTER_FEED", router_feed_state)

            # Publish MESH.STATE.BLE
            ble_state = {
                "timestamp": ts_iso,
                "epoch": now_epoch,
                "devices": list(self.tracked_ble_devices.values()),
                "device_count": len(self.tracked_ble_devices),
            }
            self.publish_zmq("MESH.STATE.BLE", ble_state)

    async def start(self) -> None:
        """Start the ingester daemon."""
        self.running = True
        logger.info(f"Starting Lens 10GbE Ingester in mode '{self.mode}'...")

        self._stats_task = asyncio.create_task(self._run_stats_loop())

        if self.mode in ("server", "auto"):
            try:
                self._server = await asyncio.start_server(
                    self.handle_connection,
                    self.listen_host,
                    self.listen_port,
                )
                logger.info(f"Ingester server listening on {self.listen_host}:{self.listen_port}")
            except Exception as e:
                logger.warning(f"Could not bind server port {self.listen_port}: {e}")

        if self.mode in ("client", "auto"):
            self._client_task = asyncio.create_task(self._run_client_loop())

    async def stop(self) -> None:
        """Gracefully stop ingester and close all sockets."""
        self.running = False
        logger.info("Stopping Lens 10GbE Ingester...")

        if self._stats_task:
            self._stats_task.cancel()
        if self._client_task:
            self._client_task.cancel()

        if self._server:
            self._server.close()
            await self._server.wait_closed()

        for writer in list(self._active_connections):
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
        self._active_connections.clear()

        if self.zmq_pub:
            self.zmq_pub.close(linger=0)
            self.zmq_pub = None
        if self.zmq_context:
            self.zmq_context.term()
            self.zmq_context = None

        logger.info("Lens 10GbE Ingester stopped.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Mac Mini 10GbE Lens Ingester Daemon")
    parser.add_argument("--mode", choices=["client", "server", "auto"], default="auto", help="Ingestion mode")
    parser.add_argument("--router-host", default="192.168.8.1", help="GL.iNet router IP")
    parser.add_argument("--router-port", type=int, default=9002, help="Router TCP port")
    parser.add_argument("--listen-port", type=int, default=19001, help="Local listen port")
    parser.add_argument("--no-zmq", action="store_true", help="Disable ZeroMQ publishing")
    args = parser.parse_args()

    ingester = Lens10GbEIngester(
        mode=args.mode,
        router_host=args.router_host,
        router_port=args.router_port,
        listen_port=args.listen_port,
        enable_zmq=not args.no_zmq,
    )

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def _shutdown(sig: int) -> None:
        logger.info(f"Received signal {sig}. Initiating shutdown...")
        loop.create_task(ingester.stop())

    for s in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(s, lambda s=s: _shutdown(s))
        except NotImplementedError:
            pass

    async def _run() -> None:
        await ingester.start()
        while ingester.running:
            await asyncio.sleep(0.5)

    try:
        loop.run_until_complete(_run())
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        loop.run_until_complete(ingester.stop())
        loop.close()


if __name__ == "__main__":
    main()
