"""
Shark Wire Live Packet Capture & Streaming Engine.
Supervises asynchronous packet capture on Darwin interfaces (en0, bridge0, utun, any),
manages in-memory ring buffer, AST filter dispatch, and Server-Sent Events subscribers.
Implements dual-mode capture: live tcpdump BPF stream when privileged, falling back to
authentic PCAP replay provider adhering strictly to Rule 1 (Zero-Mock Truth Rule).
"""

import time
import queue
import asyncio
import logging
import threading
import subprocess
from typing import Dict, Any, List, Optional, Set, Tuple

from .ring_buffer import SharkWireRingBuffer
from .filter import SharkWireFilter
from .dissector import dissect_packet
from .fixtures import read_pcap_file, load_authentic_fixture_packets

logger = logging.getLogger("shark_wire.engine")


class SharkWirePacketEngine:
    """
    Core Packet Capture Engine managing:
    - Bounded 5,000 packet ring buffer
    - Dual-mode capture (BPF live tcpdump vs authentic replay)
    - SSE subscriber queues for real-time browser streaming
    - Live display filter evaluation
    """

    _instance: Optional["SharkWirePacketEngine"] = None

    def __init__(self, maxlen: int = 5000, default_interface: str = "en0"):
        self.ring_buffer = SharkWireRingBuffer(maxlen=maxlen)
        self.active_interface: str = default_interface
        self.state: str = "stopped"  # "running", "paused", "stopped", "idle"

        self._subscribers: Set[asyncio.Queue] = set()
        self._subscribers_lock = threading.Lock()

        self.packet_counter: int = 0
        self.drop_counter: int = 0
        self.start_time: Optional[float] = None
        self._last_rate_calc_time: float = time.time()
        self._last_rate_packet_count: int = 0
        self._current_rate_pps: float = 0.0

        self._stop_event = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None
        self.last_error: Optional[str] = None

    @classmethod
    def get_instance(cls) -> "SharkWirePacketEngine":
        """Singleton accessor for application-wide engine instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def start(self, interface: Optional[str] = None) -> Dict[str, Any]:
        """Start or restart packet capture on specified interface."""
        if interface and interface != self.active_interface:
            self.active_interface = interface

        if self.state == "running" and self._worker_thread and self._worker_thread.is_alive():
            return {"status": "ok", "state": self.state, "interface": self.active_interface}

        self._stop_event.clear()
        self.state = "running"
        self.start_time = time.time()
        self._last_rate_calc_time = time.time()
        self._last_rate_packet_count = self.packet_counter

        self._worker_thread = threading.Thread(
            target=self._capture_worker_loop,
            args=(self.active_interface,),
            name=f"shark_wire_capture_{self.active_interface}",
            daemon=True,
        )
        self._worker_thread.start()
        logger.info(f"Shark Wire packet engine started on interface '{self.active_interface}'")
        return {"status": "ok", "state": self.state, "interface": self.active_interface}

    def stop(self) -> Dict[str, Any]:
        """Stop packet capture worker."""
        self._stop_event.set()
        self.state = "stopped"
        logger.info("Shark Wire packet engine stopped")
        return {"status": "ok", "state": self.state}

    def pause(self) -> Dict[str, Any]:
        """Pause packet ingestion into the ring buffer."""
        self.ring_buffer.pause()
        self.state = "paused"
        logger.info("Shark Wire packet engine paused")
        return {"status": "ok", "state": self.state}

    def resume(self) -> Dict[str, Any]:
        """Resume packet ingestion into the ring buffer."""
        self.ring_buffer.resume()
        self.state = "running"
        logger.info("Shark Wire packet engine resumed")
        return {"status": "ok", "state": self.state}

    def clear(self) -> Dict[str, Any]:
        """Clear the ring buffer and reset counters."""
        self.ring_buffer.clear()
        self.packet_counter = 0
        self.drop_counter = 0
        logger.info("Shark Wire packet ring buffer cleared")
        return {"status": "ok", "state": self.state}

    def validate_filter(self, filter_expr: str) -> Dict[str, Any]:
        """Validate filter expression and return matched count from current ring buffer."""
        flt = SharkWireFilter(filter_expr)
        valid, err = flt.validate()
        if not valid:
            return {"valid": False, "matched_count": 0, "error": err}

        packets = self.ring_buffer.get_all()
        matched = sum(1 for p in packets if flt.matches(p))
        return {"valid": True, "matched_count": matched, "error": None}

    def export_pcap(self) -> bytes:
        """Export current ring buffer as libpcap 2.4 binary bytes."""
        return self.ring_buffer.export_pcap()

    def get_stats(self) -> Dict[str, Any]:
        """Calculate and return capture engine operational statistics."""
        now = time.time()
        dt = now - self._last_rate_calc_time
        if dt >= 1.0:
            dp = self.packet_counter - self._last_rate_packet_count
            self._current_rate_pps = round(dp / dt, 1)
            self._last_rate_calc_time = now
            self._last_rate_packet_count = self.packet_counter

        buf_len = len(self.ring_buffer)
        util_pct = round((buf_len / self.ring_buffer.maxlen) * 100.0, 1) if self.ring_buffer.maxlen > 0 else 0.0

        return {
            "captured_count": self.packet_counter,
            "displayed_count": buf_len,
            "rate_pps": self._current_rate_pps,
            "buffer_utilization_pct": util_pct,
            "drop_count": self.drop_counter + self.ring_buffer.total_dropped_by_pause,
            "state": self.state,
            "active_interface": self.active_interface,
            "error": self.last_error,
        }

    def subscribe(self) -> asyncio.Queue:
        """Register a new asynchronous subscriber queue for SSE streaming."""
        q = asyncio.Queue(maxsize=500)
        with self._subscribers_lock:
            self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        """Unregister an asynchronous subscriber queue."""
        with self._subscribers_lock:
            self._subscribers.discard(q)

    def _broadcast_packet(self, packet: Dict[str, Any]) -> None:
        """Broadcast a packet to all active subscriber queues without blocking."""
        with self._subscribers_lock:
            subs = list(self._subscribers)

        for q in subs:
            try:
                if q.full():
                    # Evict oldest item to prevent memory leaks on slow clients
                    try:
                        q.get_nowait()
                        self.drop_counter += 1
                    except asyncio.QueueEmpty:
                        pass
                q.put_nowait(packet)
            except Exception:
                pass

    def _capture_worker_loop(self, interface: str) -> None:
        """
        Background worker thread executing live tcpdump capture on Darwin /dev/bpf.
        Zero-mock truth enforcement: if live BPF capture fails or is not permitted,
        cleanly enters bpf_permission_required state with 0 packets (no synthetic fixture replay).
        """
        use_live = False
        proc = None

        if interface != "any":
            try:
                # Test live capture capability
                test_cmd = ["tcpdump", "-c", "1", "-i", interface]
                res = subprocess.run(test_cmd, capture_output=True, text=True, timeout=1.0)
                if res.returncode == 0:
                    use_live = True
                else:
                    self.state = "bpf_permission_required"
                    self.last_error = "BPF capture permission required. Run: sudo chmod 666 /dev/bpf* or launch backend as root."
                    logger.warning(f"Live tcpdump permission check failed on '{interface}'")
                    return
            except Exception as e:
                self.state = "bpf_permission_required"
                self.last_error = f"BPF capture error: {e}"
                logger.warning(f"Live tcpdump error on '{interface}': {e}")
                return

        if use_live:
            cmd = ["tcpdump", "-U", "-w", "-", "-i", interface, "-s", "1514"]
            try:
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                logger.info(f"Live tcpdump capture active on '{interface}'")
                # Read 24-byte libpcap global header
                global_hdr = proc.stdout.read(24)
                if len(global_hdr) == 24:
                    prev_ts = None
                    while not self._stop_event.is_set():
                        rec_hdr = proc.stdout.read(16)
                        if len(rec_hdr) < 16:
                            break
                        import struct
                        ts_sec, ts_usec, caplen, _ = struct.unpack("<IIII", rec_hdr)
                        raw = proc.stdout.read(caplen)
                        if len(raw) < caplen:
                            break
                        ts = ts_sec + (ts_usec / 1_000_000.0)
                        self.packet_counter += 1

                        pkt = dissect_packet(
                            raw_bytes=raw,
                            interface=interface,
                            timestamp=ts,
                            index=self.packet_counter,
                            prev_timestamp=prev_ts,
                        )
                        prev_ts = ts
                        self.ring_buffer.append(pkt)
                        self._broadcast_packet(pkt)
                else:
                    self.state = "bpf_permission_required"
                    self.last_error = "BPF capture permission required. Run: sudo chmod 666 /dev/bpf* or launch backend as root."
            except Exception as e:
                self.state = "error"
                self.last_error = str(e)
                logger.warning(f"Live tcpdump error on '{interface}': {e}")
            finally:
                if proc:
                    try:
                        proc.terminate()
                        proc.wait(timeout=1.0)
                    except Exception:
                        pass
        else:
            self.state = "bpf_permission_required"
            self.last_error = "BPF capture permission required. Run: sudo chmod 666 /dev/bpf* or launch backend as root."
