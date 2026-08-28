#!/usr/bin/env python3
"""
Zero-Mock Active Fault Injector
===============================
Simulates network partitions, blackholes, port closures, and service crashes
to assert that telemetry pipelines and API clients produce genuine explicit
null/error states rather than falling back to synthetic mock data.

Key Invariants Enforced:
1. When target is down -> must report None / null / OFFLINE / DISCONNECTED.
2. Must NEVER return canned fallback data (e.g. 10.0 Mbps or devices_active: 6).
3. Latency must be None or 0.0, throughput must be None or 0.0.
"""

import json
import socket
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, asdict, field
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from threading import Thread
from typing import List, Dict, Any, Optional, Callable


PROHIBITED_MOCK_STRINGS = {
    "100.0 mbps", "100 mbps", "1000 mbps", "0.28ms", "0.45ms", "1.2ms",
    "mock_speed", "simulated_data", "fake_active", "dummy_payload", "0.28ms (dma)"
}

FORBIDDEN_FALLBACK_SIGNATURES = [
    {"status": "FLEET_DARK_ACTIVE", "devices_active": 6},
    {"status": "FLEET_DARK_ACTIVE"},
    {"devices_active": 6},
    {"latency": "0.28ms"},
    {"latency": "0.45ms"},
    {"throughput": 10.0},
    {"throughput_mbps": 10.0},
    {"single_tp_mbps": 10.0},
]


@dataclass
class FaultInjectionResult:
    scenario_id: str
    scenario_name: str
    target: str
    fault_type: str
    passed: bool
    returned_mock_fallback: bool
    returned_explicit_null: bool
    status_code_or_error: str
    observed_payload: Any
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class QuietHTTPServer(HTTPServer):
    """HTTPServer that silently handles BrokenPipeError and ConnectionResetError on socket aborts."""

    def handle_error(self, request, client_address):
        exc_type, exc_val, _ = sys.exc_info()
        if exc_type in (BrokenPipeError, ConnectionResetError, OSError):
            return
        super().handle_error(request, client_address)


class FaultSimulationServer:
    """Ephemeral HTTP server used to inject specific HTTP fault codes (500, 503, corrupt JSON, dropped socket)."""

    def __init__(self, host: str = "127.0.0.1", port: int = 0):
        self.host = host
        self.port = port
        self.server: Optional[QuietHTTPServer] = None
        self.thread: Optional[Thread] = None
        self.fault_mode: str = "503_SERVICE_UNAVAILABLE"
        self.response_body: str = ""

    def start(self, fault_mode: str = "503_SERVICE_UNAVAILABLE", custom_body: str = ""):
        self.fault_mode = fault_mode
        self.response_body = custom_body
        parent = self

        class Handler(BaseHTTPRequestHandler):
            def handle(self):
                try:
                    super().handle()
                except (BrokenPipeError, ConnectionResetError, OSError):
                    pass

            def finish(self):
                try:
                    super().finish()
                except (BrokenPipeError, ConnectionResetError, OSError):
                    pass

            def do_GET(self):
                try:
                    if parent.fault_mode == "503_SERVICE_UNAVAILABLE":
                        self.send_response(503)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(b'{"error": "Service Unavailable", "upstream": "offline"}')
                    elif parent.fault_mode == "500_INTERNAL_ERROR":
                        self.send_response(500)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(b'{"error": "Internal Server Error"}')
                    elif parent.fault_mode == "CORRUPT_JSON":
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(b'{"incomplete_json": [1, 2, ')
                    elif parent.fault_mode == "FALLBACK_MOCK":
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(b'{"status": "FLEET_DARK_ACTIVE", "devices_active": 6, "latency": "0.28ms"}')
                    elif parent.fault_mode == "EXPLICIT_NULL":
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(b'{"status": "OFFLINE", "devices_active": 0, "latency_ms": null, "throughput_mbps": 0.0}')
                    else:
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(parent.response_body.encode("utf-8") if parent.response_body else b'{}')
                except (BrokenPipeError, ConnectionResetError, OSError):
                    pass

            def log_message(self, format, *args):
                pass

        self.server = QuietHTTPServer((self.host, self.port), Handler)
        self.port = self.server.server_port
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def get_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def stop(self):
        if self.server:
            try:
                self.server.shutdown()
                self.server.server_close()
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass
            finally:
                self.server = None


class ZeroMockFaultInjector:
    """Active fault injection test runner."""

    def __init__(self):
        self.results: List[FaultInjectionResult] = []

    def verify_no_mock_fallback(self, component: str, fault_type: str, output: Any, valid_empty_or_error_checks: Optional[Callable[[Any], bool]] = None) -> FaultInjectionResult:
        """
        Validates that `output` returned during an active fault is legitimate
        error/null representation and not a synthetic mock fallback.
        """
        out_str = str(output).lower()
        for mock_str in PROHIBITED_MOCK_STRINGS:
            if mock_str in out_str:
                res = FaultInjectionResult(
                    scenario_id="FI-FALLBACK-SCAN",
                    scenario_name=f"Fallback Mock Scan ({component})",
                    target=component,
                    fault_type=fault_type,
                    passed=False,
                    returned_mock_fallback=True,
                    returned_explicit_null=False,
                    status_code_or_error="MOCK_LITERAL_DETECTED",
                    observed_payload=output,
                    message=f"Component fell back to prohibited mock literal '{mock_str}' during {fault_type}."
                )
                self.results.append(res)
                return res

        if valid_empty_or_error_checks:
            try:
                is_valid = valid_empty_or_error_checks(output)
            except Exception:
                is_valid = False
        else:
            is_valid = False
            if output is None or output == 0.0 or output == {} or output == []:
                is_valid = True
            elif isinstance(output, str) and any(k in output.upper() for k in ["DOWN", "OFFLINE", "UNREACHABLE", "ERROR", "AWAITING", "DEGRADED", "FAIL", "STANDBY", "NONE", "--"]):
                is_valid = True
            elif isinstance(output, dict):
                status = str(output.get("status", "")).upper()
                tp = output.get("throughput_mbps", output.get("down_mbps", 0.0))
                if status in ["DOWN", "OFFLINE", "UNREACHABLE", "DEGRADED", "STANDBY", "ERROR"] or tp == 0.0:
                    is_valid = True

        verdict = "PASS" if is_valid else "FAIL_FALLBACK_TO_MOCK"
        msg = "Explicit error/null state cleanly returned without fallback mocks." if is_valid else f"Unexpected active/non-zero response during {fault_type}: {output}"

        res = FaultInjectionResult(
            scenario_id="FI-VERIFY-NULL",
            scenario_name=f"Verify Explicit Null ({component})",
            target=component,
            fault_type=fault_type,
            passed=is_valid,
            returned_mock_fallback=not is_valid,
            returned_explicit_null=is_valid,
            status_code_or_error=verdict,
            observed_payload=output,
            message=msg
        )
        self.results.append(res)
        return res

    def test_closed_port(self, host: str = "127.0.0.1", port: int = 59998) -> FaultInjectionResult:
        """Injects a connection refusal by querying a closed port."""
        target_url = f"http://{host}:{port}/api/stats"
        scenario_id = "FI-01-PORT-CLOSED"
        scenario_name = "Closed Port Connection Refused"

        try:
            req = urllib.request.Request(target_url)
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                data = json.loads(resp.read().decode())
                is_mock = self._check_is_mock_payload(data)
                res = FaultInjectionResult(
                    scenario_id=scenario_id,
                    scenario_name=scenario_name,
                    target=target_url,
                    fault_type="PORT_CLOSED",
                    passed=False,
                    returned_mock_fallback=is_mock,
                    returned_explicit_null=False,
                    status_code_or_error="UNEXPECTED_200",
                    observed_payload=data,
                    message="Unexpected connection success on closed port."
                )
        except (urllib.error.URLError, ConnectionRefusedError, socket.timeout, OSError) as e:
            res = FaultInjectionResult(
                scenario_id=scenario_id,
                scenario_name=scenario_name,
                target=target_url,
                fault_type="PORT_CLOSED",
                passed=True,
                returned_mock_fallback=False,
                returned_explicit_null=True,
                status_code_or_error=type(e).__name__,
                observed_payload=None,
                message=f"Connection cleanly refused ({type(e).__name__}); zero fake fallback returned."
            )
        self.results.append(res)
        return res

    def test_blackhole_ip(self, blackhole_ip: str = "192.0.2.1", port: int = 8080) -> FaultInjectionResult:
        """Probes RFC 5737 TEST-NET-1 non-routable IP to verify strict timeout handling."""
        target_url = f"http://{blackhole_ip}:{port}/api/telemetry"
        scenario_id = "FI-02-BLACKHOLE-TIMEOUT"
        scenario_name = "Blackhole Network Route Timeout"

        t0 = time.time()
        try:
            req = urllib.request.Request(target_url)
            with urllib.request.urlopen(req, timeout=0.8) as resp:
                data = json.loads(resp.read().decode())
                is_mock = self._check_is_mock_payload(data)
                res = FaultInjectionResult(
                    scenario_id=scenario_id,
                    scenario_name=scenario_name,
                    target=target_url,
                    fault_type="NETWORK_BLACKHOLE",
                    passed=False,
                    returned_mock_fallback=is_mock,
                    returned_explicit_null=False,
                    status_code_or_error="UNEXPECTED_RESPONSE",
                    observed_payload=data,
                    message="Blackhole returned data unexpectedly."
                )
        except (urllib.error.URLError, socket.timeout, TimeoutError, OSError) as e:
            elapsed = time.time() - t0
            res = FaultInjectionResult(
                scenario_id=scenario_id,
                scenario_name=scenario_name,
                target=target_url,
                fault_type="NETWORK_BLACKHOLE",
                passed=True,
                returned_mock_fallback=False,
                returned_explicit_null=True,
                status_code_or_error=f"{type(e).__name__} ({elapsed:.2f}s)",
                observed_payload=None,
                message=f"Socket timeout handled gracefully in {elapsed:.2f}s without fallback mock values."
            )
        self.results.append(res)
        return res

    def test_client_fallback_handler(self, client_fn: Callable[[], Any], scenario_name: str = "Custom Client Fallback") -> FaultInjectionResult:
        """
        Executes a client function under simulated network failure and inspects the return value.
        Passes if client returns None, raises error, or returns explicit null/error dict.
        Fails if client returns canned mock values (e.g. 10.0 or 6 active devices).
        """
        scenario_id = "FI-03-CLIENT-FALLBACK"
        try:
            res = client_fn()
            is_mock = self._check_is_mock_payload(res)
            is_null = (res is None) or (
                isinstance(res, dict)
                and (
                    (str(res.get("status", "")).upper() in ("OFFLINE", "ERROR", "DISCONNECTED", "DOWN", "UNREACHABLE", "STANDBY") and res.get("devices_active", 0) == 0)
                    or (res == {})
                    or ("error" in res and str(res.get("status", "")).upper() in ("", "NONE", "OFFLINE", "ERROR", "DISCONNECTED", "DOWN", "UNREACHABLE", "STANDBY"))
                )
            )

            if is_mock:
                res_obj = FaultInjectionResult(
                    scenario_id=scenario_id,
                    scenario_name=scenario_name,
                    target="client_callable",
                    fault_type="CLIENT_FAILURE_FALLBACK",
                    passed=False,
                    returned_mock_fallback=True,
                    returned_explicit_null=False,
                    status_code_or_error="RETURNED_MOCK_DATA",
                    observed_payload=res,
                    message=f"VIOLATION: Client returned synthetic fallback data: {res}"
                )
            elif is_null:
                res_obj = FaultInjectionResult(
                    scenario_id=scenario_id,
                    scenario_name=scenario_name,
                    target="client_callable",
                    fault_type="CLIENT_FAILURE_FALLBACK",
                    passed=True,
                    returned_mock_fallback=False,
                    returned_explicit_null=True,
                    status_code_or_error="EXPLICIT_NULL_STATE",
                    observed_payload=res,
                    message="Client returned truthful null/offline state."
                )
            else:
                res_obj = FaultInjectionResult(
                    scenario_id=scenario_id,
                    scenario_name=scenario_name,
                    target="client_callable",
                    fault_type="CLIENT_FAILURE_FALLBACK",
                    passed=False,
                    returned_mock_fallback=True,
                    returned_explicit_null=False,
                    status_code_or_error="UNEXPECTED_ACTIVE_STATE_DURING_FAULT",
                    observed_payload=res,
                    message=f"VIOLATION: Client returned unexpected active/non-null state during network fault: {res}"
                )
        except Exception as e:
            res_obj = FaultInjectionResult(
                scenario_id=scenario_id,
                scenario_name=scenario_name,
                target="client_callable",
                fault_type="CLIENT_FAILURE_FALLBACK",
                passed=True,
                returned_mock_fallback=False,
                returned_explicit_null=True,
                status_code_or_error=f"RAISED_{type(e).__name__}",
                observed_payload=None,
                message=f"Client cleanly raised {type(e).__name__} without swallowing into mock data."
            )
        self.results.append(res_obj)
        return res_obj

    def _check_is_mock_payload(self, data: Any) -> bool:
        """Inspects if data contains any forbidden mock fallback signature."""
        if not isinstance(data, dict):
            return False

        for sig in FORBIDDEN_FALLBACK_SIGNATURES:
            match = True
            for k, v in sig.items():
                if data.get(k) != v:
                    match = False
                    break
            if match:
                return True

        if "devices" in data and isinstance(data["devices"], list):
            for dev in data["devices"]:
                if isinstance(dev, dict) and dev.get("latency") in ("0.28ms", "0.45ms", "0.28ms (DMA)"):
                    return True

        return False

    def run_standard_fault_suite(self) -> List[FaultInjectionResult]:
        """Runs baseline standard fault injection suite."""
        results: List[FaultInjectionResult] = []

        # Test 1: Closed port connection
        results.append(self.test_closed_port())

        # Test 2: Blackhole IP route timeout
        results.append(self.test_blackhole_ip())

        # Test 3: Ephemeral 503 Server verification
        srv_503 = FaultSimulationServer()
        srv_503.start("503_SERVICE_UNAVAILABLE")
        url_503 = srv_503.get_url()
        try:
            req = urllib.request.Request(url_503)
            urllib.request.urlopen(req, timeout=1.0)
            res_503 = FaultInjectionResult(
                scenario_id="FI-04-HTTP-503",
                scenario_name="HTTP 503 Service Unavailable Injection",
                target=url_503,
                fault_type="HTTP_503",
                passed=False,
                returned_mock_fallback=False,
                returned_explicit_null=False,
                status_code_or_error="200_UNEXPECTED",
                observed_payload=None,
                message="Expected HTTP 503 but got 200."
            )
        except urllib.error.HTTPError as e:
            res_503 = FaultInjectionResult(
                scenario_id="FI-04-HTTP-503",
                scenario_name="HTTP 503 Service Unavailable Injection",
                target=url_503,
                fault_type="HTTP_503",
                passed=(e.code == 503),
                returned_mock_fallback=False,
                returned_explicit_null=True,
                status_code_or_error=f"HTTP_{e.code}",
                observed_payload=None,
                message=f"HTTP 503 correctly propagated without mock synthesis."
            )
        finally:
            srv_503.stop()
        results.append(res_503)

        # Test 4: Ephemeral Mock Server (Assert judge flags mock data properly)
        srv_mock = FaultSimulationServer()
        srv_mock.start("FALLBACK_MOCK")
        url_mock = srv_mock.get_url()
        try:
            req = urllib.request.Request(url_mock)
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                mock_payload = json.loads(resp.read().decode())
                is_mock = self._check_is_mock_payload(mock_payload)
                res_mock = FaultInjectionResult(
                    scenario_id="FI-05-MOCK-DETECTION-GATE",
                    scenario_name="Mock Detection Calibration Test",
                    target=url_mock,
                    fault_type="SYNTHETIC_MOCK_PAYLOAD",
                    passed=is_mock,
                    returned_mock_fallback=is_mock,
                    returned_explicit_null=False,
                    status_code_or_error="HTTP_200",
                    observed_payload=mock_payload,
                    message="Mock detector successfully identified synthetic fallback signature." if is_mock else "FAILED to detect mock payload."
                )
        finally:
            srv_mock.stop()
        results.append(res_mock)

        return results

    def generate_report(self) -> Dict[str, Any]:
        """Generates structured fault injection compliance report."""
        passed = [r for r in self.results if r.passed]
        failed = [r for r in self.results if not r.passed]
        total = len(self.results)
        compliance_pct = round((len(passed) / total * 100.0), 2) if total > 0 else 100.0

        return {
            "total_fault_tests": total,
            "passed_count": len(passed),
            "failed_count": len(failed),
            "compliance_percentage": compliance_pct,
            "verdict": "ZERO_MOCK_FAULT_CERTIFIED" if len(failed) == 0 else "FALLBACK_VIOLATIONS_DETECTED",
            "results": [r.to_dict() for r in self.results]
        }
