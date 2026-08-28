#!/usr/bin/env python3
"""
Lauburu Ultra-Low Latency Voice Bridge Test Harness
===================================================

Automated E2E Latency & Integrity Verification for WebSocket Voice Bridge Daemon.

Acceptance Criteria & Specifications:
1. Target Connectivity: Connects to WebSocket daemon (default ws://127.0.0.1:8765,
   configurable via CLI --url, --host, --port, or env VOICE_BRIDGE_URL / VOICE_BRIDGE_PORT).
2. Binary Transmission: Generates exact 100KB (102,400 bytes) dummy binary payload
   (os.urandom) or custom payload size (--payload-kb).
3. Round-Trip Timing: Uses time.perf_counter() before send and after recv to measure
   exact round-trip time (RTT) with sub-millisecond precision.
4. Data Integrity: Validates 100% byte-for-byte fidelity (assert received == sent_payload).
5. SLA Assertion: Asserts RTT < 500.0ms (fails with exit code 1 if latency exceeds threshold).
6. Dual Execution: Standalone CLI with rich arguments and standard Pytest test runner support.
"""

import os
import sys
import time
import math
import json
import socket
import logging
import asyncio
import threading
import argparse
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any

try:
    import websockets
except ImportError:
    print(
        "Error: 'websockets' library is required. "
        "Run 'uv pip install websockets' or use a Python environment with websockets installed.",
        file=sys.stderr
    )
    sys.exit(1)

# Default configuration constants
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = int(os.environ.get("VOICE_BRIDGE_PORT", 8765))
DEFAULT_URL = os.environ.get("VOICE_BRIDGE_URL", f"ws://{DEFAULT_HOST}:{DEFAULT_PORT}")
DEFAULT_PAYLOAD_KB = 100
DEFAULT_PAYLOAD_BYTES = DEFAULT_PAYLOAD_KB * 1024  # 102,400 bytes
DEFAULT_ITERATIONS = 5
DEFAULT_LATENCY_THRESHOLD_MS = 500.0
DEFAULT_TIMEOUT_SECONDS = 5.0
MAX_FRAME_SIZE = 10 * 1024 * 1024  # 10 MB

# Logger setup
logger = logging.getLogger("VoiceBridgeTest")


@dataclass
class LatencyTestResult:
    """Encapsulates the complete metrics and verification outcome of a latency test run."""
    success: bool
    iterations: int
    payload_bytes: int
    rtts: List[float] = field(default_factory=list)
    min_rtt_ms: float = 0.0
    avg_rtt_ms: float = 0.0
    max_rtt_ms: float = 0.0
    std_dev_ms: float = 0.0
    p95_rtt_ms: float = 0.0
    throughput_mbps: float = 0.0
    byte_match: bool = True
    threshold_ms: float = DEFAULT_LATENCY_THRESHOLD_MS
    url: str = DEFAULT_URL
    error_message: Optional[str] = None

    def calculate_statistics(self) -> None:
        """Computes statistical metrics from recorded RTT samples."""
        if not self.rtts:
            return
        self.min_rtt_ms = min(self.rtts)
        self.max_rtt_ms = max(self.rtts)
        self.avg_rtt_ms = sum(self.rtts) / len(self.rtts)
        
        # Standard deviation (jitter measure)
        if len(self.rtts) > 1:
            variance = sum((x - self.avg_rtt_ms) ** 2 for x in self.rtts) / (len(self.rtts) - 1)
            self.std_dev_ms = math.sqrt(variance)
        else:
            self.std_dev_ms = 0.0
            
        # 95th Percentile
        sorted_rtts = sorted(self.rtts)
        p95_index = int(math.ceil(0.95 * len(sorted_rtts))) - 1
        self.p95_rtt_ms = sorted_rtts[max(0, min(p95_index, len(sorted_rtts) - 1))]
        
        # Effective bi-directional throughput in Megabytes per second
        # (payload sent + payload received) per round-trip
        if self.avg_rtt_ms > 0:
            total_bytes_per_rtt = self.payload_bytes * 2
            seconds_per_rtt = self.avg_rtt_ms / 1000.0
            self.throughput_mbps = (total_bytes_per_rtt / (1024 * 1024)) / seconds_per_rtt
        else:
            self.throughput_mbps = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serializes result to a dictionary."""
        return {
            "success": self.success,
            "url": self.url,
            "iterations": self.iterations,
            "payload_bytes": self.payload_bytes,
            "payload_kb": round(self.payload_bytes / 1024, 2),
            "min_rtt_ms": round(self.min_rtt_ms, 3),
            "avg_rtt_ms": round(self.avg_rtt_ms, 3),
            "max_rtt_ms": round(self.max_rtt_ms, 3),
            "std_dev_ms": round(self.std_dev_ms, 3),
            "p95_rtt_ms": round(self.p95_rtt_ms, 3),
            "throughput_mb_s": round(self.throughput_mbps, 2),
            "byte_match": self.byte_match,
            "threshold_ms": self.threshold_ms,
            "sla_passed": self.success and self.avg_rtt_ms < self.threshold_ms,
            "rtt_samples_ms": [round(r, 3) for r in self.rtts],
            "error_message": self.error_message
        }

    def summary(self) -> str:
        """Returns a formatted human-readable summary string."""
        status_symbol = "✅ PASSED" if self.success else "❌ FAILED"
        lines = [
            f"\n{'=' * 64}",
            f"  VOICE BRIDGE LATENCY & INTEGRITY TEST REPORT: {status_symbol}",
            f"{'=' * 64}",
            f"  Target URL:          {self.url}",
            f"  Payload Size:        {self.payload_bytes} bytes ({self.payload_bytes / 1024:.1f} KB)",
            f"  Completed Samples:   {len(self.rtts)} / {self.iterations}",
            f"  Byte-for-Byte Match: {'100% MATCH (PASSED)' if self.byte_match else 'MISMATCH (FAILED)'}",
            f"  SLA Threshold:       < {self.threshold_ms:.1f} ms",
            f"  Min Latency:         {self.min_rtt_ms:.3f} ms",
            f"  Avg Latency:         {self.avg_rtt_ms:.3f} ms",
            f"  Max Latency:         {self.max_rtt_ms:.3f} ms",
            f"  Jitter (StdDev):     {self.std_dev_ms:.3f} ms",
            f"  P95 Latency:         {self.p95_rtt_ms:.3f} ms",
            f"  Throughput:          {self.throughput_mbps:.2f} MB/s",
        ]
        if self.error_message:
            lines.append(f"  Error:               {self.error_message}")
        lines.append(f"{'=' * 64}\n")
        return "\n".join(lines)


def is_port_open(host: str, port: int, timeout: float = 0.5) -> bool:
    """Checks whether a TCP port or HTTP health endpoint is currently accepting connections."""
    try:
        url = f"http://{host}:{port}/health"
        req = urllib.request.Request(url, headers={"User-Agent": "VoiceBridgeProbe/1.0"})
        with urllib.request.urlopen(req, timeout=timeout):
            return True
    except urllib.error.HTTPError:
        return True
    except Exception:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except (OSError, ConnectionRefusedError):
            return False


def find_free_port() -> int:
    """Finds an available ephemeral TCP port on the local system."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


async def receive_binary_payload(
    ws: Any,
    expected_length: int,
    timeout: float = DEFAULT_TIMEOUT_SECONDS
) -> bytes:
    """
    Receives incoming WebSocket frames, draining any non-binary control frames
    (e.g., initial ready greeting or JSON status), until the binary audio payload is received.
    """
    start_time = time.perf_counter()
    while True:
        elapsed = time.perf_counter() - start_time
        remaining = max(0.01, timeout - elapsed)
        
        msg = await asyncio.wait_for(ws.recv(), timeout=remaining)
        
        if isinstance(msg, (bytes, bytearray, memoryview)):
            return bytes(msg)
        elif isinstance(msg, str):
            # Non-binary control frame received (e.g. greeting {"type": "ready", ...})
            logger.debug("Drained intermediate text/control frame: %s", msg[:120])
            continue
        else:
            logger.warning("Unrecognized frame type received: %s", type(msg))


async def verify_voice_bridge_latency(
    url: str = DEFAULT_URL,
    payload_size: int = DEFAULT_PAYLOAD_BYTES,
    iterations: int = DEFAULT_ITERATIONS,
    threshold_ms: float = DEFAULT_LATENCY_THRESHOLD_MS,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    drain_greeting: bool = True
) -> LatencyTestResult:
    """
    Executes the latency and integrity verification against the Voice Bridge WebSocket daemon.

    Args:
        url: WebSocket URL to connect to.
        payload_size: Exact byte size of the dummy binary payload (default: 102,400 bytes).
        iterations: Number of test iterations to execute.
        threshold_ms: Maximum allowable round-trip latency in milliseconds (default: 500.0ms).
        timeout_seconds: Per-iteration network timeout in seconds.
        drain_greeting: Whether to drain the server's initial greeting frame upon connection.

    Returns:
        LatencyTestResult object containing measured metrics and pass/fail status.
    """
    result = LatencyTestResult(
        success=False,
        iterations=iterations,
        payload_bytes=payload_size,
        threshold_ms=threshold_ms,
        url=url
    )

    logger.info("Connecting to Voice Bridge WebSocket daemon at %s...", url)
    
    # Generate authentic, cryptographically random dummy binary payload
    test_payload = os.urandom(payload_size)

    try:
        async with websockets.connect(
            url,
            max_size=MAX_FRAME_SIZE,
            open_timeout=timeout_seconds,
            close_timeout=timeout_seconds,
            ping_interval=None  # Avoid interference during tight latency measurement
        ) as ws:
            logger.info("✅ Connected to %s. Beginning %d iteration(s) of %d bytes payload...", url, iterations, payload_size)

            rtts = []

            for i in range(iterations):
                # High-resolution monotonic timer start
                t_start = time.perf_counter()

                # Send binary payload (Opcode 0x02)
                await ws.send(test_payload)

                # Receive binary echo with timeout
                try:
                    response_payload = await receive_binary_payload(
                        ws,
                        expected_length=payload_size,
                        timeout=timeout_seconds
                    )
                except asyncio.TimeoutError:
                    err = f"Timeout ({timeout_seconds}s) waiting for binary echo on iteration {i + 1}/{iterations}"
                    logger.error("❌ %s", err)
                    result.error_message = err
                    result.rtts = rtts
                    result.calculate_statistics()
                    return result

                # High-resolution monotonic timer end
                t_end = time.perf_counter()
                rtt_ms = (t_end - t_start) * 1000.0
                rtts.append(rtt_ms)

                # 100% Byte-for-byte fidelity assertion
                if response_payload != test_payload:
                    result.byte_match = False
                    err = (
                        f"Payload data mismatch on iteration {i + 1}/{iterations}! "
                        f"Sent {len(test_payload)} bytes, received {len(response_payload)} bytes."
                    )
                    logger.error("❌ %s", err)
                    result.error_message = err
                    result.rtts = rtts
                    result.calculate_statistics()
                    return result

                logger.info(
                    "Iteration %d/%d: %d KB binary echo RTT = %.3f ms (Fidelity: 100%%)",
                    i + 1, iterations, payload_size // 1024, rtt_ms
                )

                # Latency SLA threshold verification
                if rtt_ms >= threshold_ms:
                    err = (
                        f"Latency SLA violation! Iteration {i + 1}/{iterations} took {rtt_ms:.2f} ms "
                        f"(Threshold SLA: < {threshold_ms:.2f} ms)"
                    )
                    logger.error("❌ %s", err)
                    result.error_message = err
                    result.rtts = rtts
                    result.calculate_statistics()
                    return result

            # All iterations succeeded
            result.rtts = rtts
            result.calculate_statistics()
            result.success = True
            result.byte_match = True
            return result

    except ConnectionRefusedError:
        err = f"Connection refused to {url}. Please ensure the Voice Bridge daemon is running."
        logger.error("❌ %s", err)
        result.error_message = err
        return result
    except websockets.exceptions.InvalidURI:
        err = f"Invalid WebSocket URI: {url}"
        logger.error("❌ %s", err)
        result.error_message = err
        return result
    except Exception as e:
        err = f"Unexpected error during voice bridge test execution: {type(e).__name__}: {str(e)}"
        logger.error("❌ %s", err)
        result.error_message = err
        return result


class EphemeralDaemonServer:
    """
    Dedicated threaded test server running the Voice Bridge daemon on a background event loop.
    Enables concurrent, non-blocking test execution from any thread or asyncio loop.
    """

    def __init__(self, host: str = "127.0.0.1", port: Optional[int] = None):
        self.host = host
        self.port = port or find_free_port()
        self.url = f"ws://{self.host}:{self.port}"
        self.http_url = f"http://{self.host}:{self.port}"
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._shutdown_evt: Optional[asyncio.Event] = None

    def start(self) -> "EphemeralDaemonServer":
        """Starts the daemon on a background thread with its own asyncio event loop."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        src_dir = os.path.join(current_dir, "src")
        for p in (current_dir, src_dir):
            if p not in sys.path:
                sys.path.insert(0, p)

        try:
            from voice_bridge_daemon import run_server
        except ImportError:
            from src.voice_bridge_daemon import run_server

        ready_event = threading.Event()

        def run_thread():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._shutdown_evt = asyncio.Event()

            async def main_coro():
                ready_event.set()
                await run_server(host=self.host, port=self.port, shutdown_event=self._shutdown_evt)

            try:
                self._loop.run_until_complete(main_coro())
            except Exception as e:
                logger.debug("EphemeralDaemonServer thread stopped: %s", e)
            finally:
                self._loop.close()

        self._thread = threading.Thread(target=run_thread, name="EphemeralVoiceBridgeDaemon", daemon=True)
        self._thread.start()
        ready_event.wait(timeout=2.0)

        # Wait until port accepts HTTP / TCP connections
        for _ in range(50):
            if is_port_open(self.host, self.port):
                break
            time.sleep(0.05)
        else:
            raise TimeoutError(f"Failed to start ephemeral daemon on {self.url} within 2.5s")

        logger.info("Ephemeral daemon active on %s", self.url)
        return self

    def stop(self) -> None:
        """Gracefully shuts down the background daemon thread and event loop."""
        if self._loop and self._shutdown_evt:
            try:
                self._loop.call_soon_threadsafe(self._shutdown_evt.set)
            except RuntimeError:
                pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info("Ephemeral daemon stopped on %s", self.url)

    def __enter__(self) -> "EphemeralDaemonServer":
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    async def __aenter__(self) -> "EphemeralDaemonServer":
        return self.start()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.stop()


def test_voice_bridge_pytest():
    """
    Pytest entrypoint for automated CI/CD test runs.
    Automatically connects to live daemon if running, or launches an in-process
    ephemeral daemon instance if not running.
    """
    target_url = os.environ.get("VOICE_BRIDGE_URL", DEFAULT_URL)
    
    # Parse host and port to check if target is live
    host = DEFAULT_HOST
    port = DEFAULT_PORT
    if "://" in target_url:
        netloc = target_url.split("://", 1)[1].split("/")[0]
        if ":" in netloc:
            parts = netloc.split(":")
            host = parts[0]
            port = int(parts[1])
        else:
            host = netloc
            port = 80

    if is_port_open(host, port):
        # Test against live running server
        logger.info("Testing against live voice bridge daemon at %s", target_url)
        result = asyncio.run(verify_voice_bridge_latency(
            url=target_url,
            payload_size=100 * 1024,
            iterations=5,
            threshold_ms=500.0
        ))
    else:
        # Launch ephemeral daemon
        logger.info("No daemon detected on %s:%d. Launching ephemeral in-process daemon...", host, port)
        with EphemeralDaemonServer(host="127.0.0.1") as server:
            result = asyncio.run(verify_voice_bridge_latency(
                url=server.url,
                payload_size=100 * 1024,
                iterations=5,
                threshold_ms=500.0
            ))

    print(result.summary())
    
    assert result.success is True, f"Voice Bridge Latency Verification Failed: {result.error_message}"
    assert result.byte_match is True, "Voice Bridge Payload 100% byte match failed!"
    assert result.avg_rtt_ms < 500.0, f"Latency SLA violation: Avg RTT {result.avg_rtt_ms:.2f}ms >= 500.0ms"
    assert len(result.rtts) == 5, f"Expected 5 iterations, got {len(result.rtts)}"


def main():
    """CLI Argument parser and standalone test runner."""
    parser = argparse.ArgumentParser(
        description="Lauburu Voice Bridge WebSocket Daemon Latency & Integrity Test Harness",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--url", default=None, help="WebSocket URL to test (e.g. ws://127.0.0.1:8765)")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Host to connect to if URL not specified")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port to connect to if URL not specified")
    parser.add_argument("--payload-kb", type=int, default=DEFAULT_PAYLOAD_KB, help="Payload size in Kilobytes")
    parser.add_argument("--iterations", type=int, default=DEFAULT_ITERATIONS, help="Number of test iterations")
    parser.add_argument("--threshold-ms", type=float, default=DEFAULT_LATENCY_THRESHOLD_MS, help="Max allowed RTT in ms")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS, help="Timeout in seconds per iteration")
    parser.add_argument("--start-daemon", action="store_true", help="Launch an in-process ephemeral daemon before testing")
    parser.add_argument("--json", action="store_true", help="Output results strictly as JSON")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose debug logging")
    
    args = parser.parse_args()

    # Logging level
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S"
    )

    # Determine target URL
    if args.url:
        target_url = args.url
    else:
        target_url = f"ws://{args.host}:{args.port}"

    payload_bytes = args.payload_kb * 1024

    if args.start_daemon:
        logger.info("🚀 Launching ephemeral daemon as requested...")
        with EphemeralDaemonServer(host=args.host, port=args.port) as server:
            result = asyncio.run(verify_voice_bridge_latency(
                url=server.url,
                payload_size=payload_bytes,
                iterations=args.iterations,
                threshold_ms=args.threshold_ms,
                timeout_seconds=args.timeout
            ))
    else:
        result = asyncio.run(verify_voice_bridge_latency(
            url=target_url,
            payload_size=payload_bytes,
            iterations=args.iterations,
            threshold_ms=args.threshold_ms,
            timeout_seconds=args.timeout
        ))

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(result.summary())

    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    main()
