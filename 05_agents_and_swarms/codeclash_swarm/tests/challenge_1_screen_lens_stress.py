"""
Adversarial Stress Test Harness 1: Screen Lens & SQLite FTS5 Concurrency/Fuzzing.
Empirical Challenger: Challenger 1 (CodeClash Swarm)
"""
import asyncio
import http.client
import json
import os
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Tuple

LENS_BIN = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/screen_lens/bin/lauburu-lens"
DB_PATH = os.path.expanduser("~/.lauburu/screen_lens.sqlite")
HTTP_HOST = "127.0.0.1"
HTTP_PORT = 3035


def ensure_daemon_running():
    """Ensure lauburu-lens daemon is running on port 3035."""
    try:
        conn = http.client.HTTPConnection(HTTP_HOST, HTTP_PORT, timeout=1.0)
        conn.request("GET", "/health")
        resp = conn.getresponse()
        if resp.status == 200:
            return True
    except Exception:
        pass

    # Launch daemon
    print(f"Launching {LENS_BIN} on port {HTTP_PORT}...")
    res = subprocess.run([LENS_BIN, "start", "--port", str(HTTP_PORT), "--interval", "5.0", "--daemon"], capture_output=True, text=True)
    time.sleep(1.0)
    return True


def test_concurrent_http_queries(concurrency: int = 100, total_requests: int = 500) -> Dict[str, Any]:
    """Execute high-concurrency burst HTTP requests against all REST endpoints."""
    endpoints = [
        "/health",
        "/api/status",
        "/api/windows",
        "/api/query?q=code",
        "/api/query?q=terminal&limit=5",
        "/api/latest",
    ]

    latencies: List[float] = []
    successes = 0
    failures = 0

    def make_request(idx: int) -> Tuple[bool, float]:
        ep = endpoints[idx % len(endpoints)]
        start = time.perf_counter()
        try:
            conn = http.client.HTTPConnection(HTTP_HOST, HTTP_PORT, timeout=5.0)
            conn.request("GET", ep)
            resp = conn.getresponse()
            _ = resp.read()
            dur = (time.perf_counter() - start) * 1000.0
            conn.close()
            return (resp.status in (200, 404), dur)
        except Exception as e:
            dur = (time.perf_counter() - start) * 1000.0
            return (False, dur)

    start_total = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        results = list(executor.map(make_request, range(total_requests)))

    total_time = time.perf_counter() - start_total

    for ok, lat in results:
        latencies.append(lat)
        if ok:
            successes += 1
        else:
            failures += 1

    latencies.sort()
    p50 = latencies[int(len(latencies) * 0.50)] if latencies else 0
    p95 = latencies[int(len(latencies) * 0.95)] if latencies else 0
    p99 = latencies[int(len(latencies) * 0.99)] if latencies else 0
    rps = total_requests / total_time if total_time > 0 else 0

    metrics = {
        "concurrency": concurrency,
        "total_requests": total_requests,
        "successes": successes,
        "failures": failures,
        "success_rate": (successes / total_requests) * 100.0,
        "total_time_s": total_time,
        "throughput_rps": rps,
        "p50_latency_ms": p50,
        "p95_latency_ms": p95,
        "p99_latency_ms": p99,
    }
    return metrics


def test_malformed_http_fuzzing() -> Dict[str, Any]:
    """Fuzz HTTP server with malformed, oversized, truncated, and illegal HTTP frames."""
    fuzz_payloads = [
        # 1. Invalid methods
        b"FOOBAR /health HTTP/1.1\r\nHost: localhost\r\n\r\n",
        b"DELETE /api/status HTTP/1.1\r\nHost: localhost\r\n\r\n",
        b"PUT /health HTTP/1.1\r\nHost: localhost\r\n\r\n",
        # 2. Truncated lines
        b"GET\r\n",
        b"GET /",
        b"\r\n\r\n",
        b"   \r\n",
        # 3. Illegal HTTP version
        b"GET /health HTTP/9.9\r\n\r\n",
        b"GET /health NOTHTTP\r\n\r\n",
        # 4. Oversized URLs & headers
        b"GET /" + (b"A" * 4096) + b" HTTP/1.1\r\nHost: localhost\r\n\r\n",
        b"GET /health HTTP/1.1\r\nHost: localhost\r\nX-Long-Header: " + (b"X" * 8192) + b"\r\n\r\n",
        # 5. Null bytes & binary garbage
        b"\x00\x01\x02\x03\x04\x05\r\n\r\n",
        b"GET /\x00/test HTTP/1.1\r\n\r\n",
        b"\xff\xfe\xfd\xfc\r\n\r\n",
        # 6. Malformed URL encodings
        b"GET /api/query?q=% HTTP/1.1\r\nHost: localhost\r\n\r\n",
        b"GET /api/query?q=%GG%ZZ HTTP/1.1\r\nHost: localhost\r\n\r\n",
        b"GET /api/query?q=%00%00 HTTP/1.1\r\nHost: localhost\r\n\r\n",
        # 7. SQL Injection payloads in HTTP query
        b"GET /api/query?q=' OR 1=1; -- HTTP/1.1\r\nHost: localhost\r\n\r\n",
        b"GET /api/query?q=\"; DROP TABLE captures; -- HTTP/1.1\r\nHost: localhost\r\n\r\n",
        # 8. Unicode & emojis in URL
        "GET /api/query?q=🔥🚀🧠✨ HTTP/1.1\r\nHost: localhost\r\n\r\n".encode("utf-8"),
        "GET /api/query?q=测试中文 HTTP/1.1\r\nHost: localhost\r\n\r\n".encode("utf-8"),
        "GET /api/query?q=مرحبا HTTP/1.1\r\nHost: localhost\r\n\r\n".encode("utf-8"),
    ]

    results = []
    server_alive_after_all = True

    for i, payload in enumerate(fuzz_payloads):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2.0)
            s.connect((HTTP_HOST, HTTP_PORT))
            s.sendall(payload)
            response = b""
            try:
                response = s.recv(4096)
            except socket.timeout:
                pass
            s.close()
            results.append({
                "payload_idx": i,
                "payload_snippet": repr(payload[:40]),
                "response_received": len(response) > 0,
                "response_header": response.split(b"\r\n")[0].decode("utf-8", errors="replace") if response else "NO_RESPONSE",
                "crashed": False
            })
        except Exception as e:
            results.append({
                "payload_idx": i,
                "payload_snippet": repr(payload[:40]),
                "response_received": False,
                "response_header": str(e),
                "crashed": False
            })

    # Verify server is still alive after fuzz barrage
    try:
        conn = http.client.HTTPConnection(HTTP_HOST, HTTP_PORT, timeout=2.0)
        conn.request("GET", "/health")
        resp = conn.getresponse()
        server_alive_after_all = (resp.status == 200)
        conn.close()
    except Exception:
        server_alive_after_all = False

    return {
        "total_fuzz_payloads": len(fuzz_payloads),
        "server_alive": server_alive_after_all,
        "details": results,
    }


def test_deep_sqlite_fts_searches() -> Dict[str, Any]:
    """Test SQLite FTS5 full-text search against special characters, wildcards, and edge strings."""
    if not os.path.exists(DB_PATH):
        return {"error": f"DB path {DB_PATH} does not exist"}

    search_cases = [
        # Quotes & delimiters
        '"',
        '""',
        '"""',
        "'",
        "''",
        "`",
        # FTS5 Operators
        "AND",
        "OR",
        "NOT",
        "AND OR NOT",
        "NEAR()",
        "NEAR(a, b, 10)",
        "^prefix",
        "term*",
        "*term*",
        "column:value",
        "raw_text_summary:terminal",
        # Special punctuation
        "%",
        "%%",
        "_",
        "!",
        "?",
        "#",
        "$",
        "(",
        ")",
        "()",
        "{",
        "}",
        "[]",
        "<",
        ">",
        "=",
        ";",
        "--",
        "/* comment */",
        # SQL Injection
        "' OR '1'='1",
        "1; SELECT count(*) FROM sqlite_master;",
        "'; DROP TABLE captures; --",
        "UNION SELECT 1, 2, 3, 4, 5, 6, 7, 8, 9",
        # Unicode & Emojis
        "🧠",
        "⚡",
        "📸",
        "🔍",
        "🔥",
        "🚀",
        "🎉",
        "👩‍💻",
        "العربية",
        "日本語",
        "Русский",
        "\u202e\u202d",
        "\x00",
        # Very long queries
        "a" * 500,
        "long_query_" * 100,
        " ".join([f"term{i}" for i in range(100)]),
    ]

    cli_results = []
    rest_results = []

    # 1. Test via REST API
    for term in search_cases:
        encoded = urllib.parse.quote(term)
        start = time.perf_counter()
        try:
            conn = http.client.HTTPConnection(HTTP_HOST, HTTP_PORT, timeout=3.0)
            conn.request("GET", f"/api/query?q={encoded}&limit=10")
            resp = conn.getresponse()
            body = resp.read().decode("utf-8", errors="replace")
            dur = (time.perf_counter() - start) * 1000.0
            data = json.loads(body)
            rest_results.append({
                "term": term[:30],
                "status": resp.status,
                "total": data.get("total", 0),
                "duration_ms": dur,
                "error": None
            })
            conn.close()
        except Exception as e:
            dur = (time.perf_counter() - start) * 1000.0
            rest_results.append({
                "term": term[:30],
                "status": 500,
                "total": 0,
                "duration_ms": dur,
                "error": str(e)
            })

    # 2. Test via CLI binary
    for term in search_cases[:15]:
        start = time.perf_counter()
        res = subprocess.run([LENS_BIN, "query", term, "--json", "--limit", "5"], capture_output=True, text=True, timeout=5)
        dur = (time.perf_counter() - start) * 1000.0
        try:
            data = json.loads(res.stdout) if res.returncode == 0 and res.stdout.strip() else {}
            cli_results.append({
                "term": term[:30],
                "exit_code": res.returncode,
                "total": data.get("total", 0),
                "duration_ms": dur,
                "error": None if res.returncode == 0 else res.stderr
            })
        except Exception as e:
            cli_results.append({
                "term": term[:30],
                "exit_code": res.returncode,
                "total": 0,
                "duration_ms": dur,
                "error": f"JSON parse error: {e}"
            })

    # 3. Direct SQLite Database Integrity & Invariant Check
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA integrity_check;")
    integrity = cursor.fetchall()
    cursor.execute("PRAGMA foreign_key_check;")
    fk_check = cursor.fetchall()
    cursor.execute("SELECT count(*) FROM captures;")
    total_captures = cursor.fetchone()[0]
    cursor.execute("SELECT count(*) FROM ocr_text_blocks;")
    total_blocks = cursor.fetchone()[0]
    conn.close()

    return {
        "total_search_cases": len(search_cases),
        "rest_success_count": sum(1 for r in rest_results if r["status"] == 200 and r["error"] is None),
        "cli_success_count": sum(1 for r in cli_results if r["exit_code"] == 0 and r["error"] is None),
        "sqlite_integrity": integrity,
        "sqlite_foreign_key_check": fk_check,
        "total_captures_in_db": total_captures,
        "total_ocr_blocks_in_db": total_blocks,
        "rest_details": rest_results,
        "cli_details": cli_results,
    }


def test_daemon_live_captures() -> Dict[str, Any]:
    """Verify live captures accumulated by daemon in background and query status."""
    res = subprocess.run([LENS_BIN, "status", "--json"], capture_output=True, text=True, timeout=5)
    status_data = json.loads(res.stdout) if res.returncode == 0 and res.stdout.strip() else {}

    # Query latest capture via REST
    conn = http.client.HTTPConnection(HTTP_HOST, HTTP_PORT, timeout=3.0)
    conn.request("GET", "/api/latest")
    resp = conn.getresponse()
    latest_data = json.loads(resp.read().decode("utf-8")) if resp.status == 200 else {}
    conn.close()

    return {
        "daemon_running": status_data.get("daemon_running", False),
        "total_captures": status_data.get("total_captures", 0),
        "db_size_mb": status_data.get("db_size_mb", 0.0),
        "front_app": status_data.get("front_app", ""),
        "latest_capture_id": latest_data.get("id"),
        "latest_text_summary_len": len(latest_data.get("raw_text_summary", "")),
        "latest_ocr_mode": latest_data.get("ocr_mode", ""),
    }


def main():
    print("=== STARTING CHALLENGE 1: SCREEN LENS & SQLITE FTS5 STRESS HARNESS ===")
    ensure_daemon_running()

    print("\n[Phase 1] Rapid Concurrent HTTP REST Load Test (100 concurrent workers, 500 requests)...")
    load_metrics = test_concurrent_http_queries(concurrency=100, total_requests=500)
    print(f"  Throughput : {load_metrics['throughput_rps']:.1f} RPS")
    print(f"  Successes  : {load_metrics['successes']}/{load_metrics['total_requests']} ({load_metrics['success_rate']:.1f}%)")
    print(f"  Latency p50: {load_metrics['p50_latency_ms']:.2f} ms")
    print(f"  Latency p95: {load_metrics['p95_latency_ms']:.2f} ms")
    print(f"  Latency p99: {load_metrics['p99_latency_ms']:.2f} ms")

    print("\n[Phase 2] Malformed HTTP Frame Fuzzing & Crash Resilience...")
    fuzz_metrics = test_malformed_http_fuzzing()
    print(f"  Fuzz Payloads Tested : {fuzz_metrics['total_fuzz_payloads']}")
    print(f"  Server Alive Post-Run: {fuzz_metrics['server_alive']}")

    print("\n[Phase 3] Deep SQLite FTS5 Special Characters & Injection Search...")
    fts_metrics = test_deep_sqlite_fts_searches()
    print(f"  Search Cases Tested: {fts_metrics['total_search_cases']}")
    print(f"  REST API Successes : {fts_metrics['rest_success_count']}/{fts_metrics['total_search_cases']}")
    print(f"  CLI Tool Successes : {fts_metrics['cli_success_count']}/15")
    print(f"  SQLite Integrity   : {fts_metrics['sqlite_integrity']}")
    print(f"  Captures in DB     : {fts_metrics['total_captures_in_db']}")

    print("\n[Phase 4] Live Daemon Telemetry & Latest Frame Inspection...")
    daemon_metrics = test_daemon_live_captures()
    print(f"  Daemon Running   : {daemon_metrics['daemon_running']}")
    print(f"  Total Captures   : {daemon_metrics['total_captures']}")
    print(f"  Frontmost App    : {daemon_metrics['front_app']}")
    print(f"  Latest Capture ID: #{daemon_metrics['latest_capture_id']}")

    report = {
        "campaign": "Screen Lens Stress Test",
        "timestamp": time.time(),
        "load_metrics": load_metrics,
        "fuzz_metrics": fuzz_metrics,
        "fts_metrics": fts_metrics,
        "daemon_metrics": daemon_metrics,
    }

    with open("/Users/aaron/.agents/teamwork_preview_challenger_1/screen_lens_stress_results.json", "w") as f:
        json.dump(report, f, indent=2)

    print("\n=== CHALLENGE 1 COMPLETE: Saved to screen_lens_stress_results.json ===")


if __name__ == "__main__":
    main()
