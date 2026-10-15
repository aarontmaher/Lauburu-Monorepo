# -*- coding: utf-8 -*-
"""
Verification Tests for GL.iNet Beryl AX (512MB) Active Watchdog & TinyLM Benchmark
==================================================================================
Subsystem: 01_apps/glinet_web_optimizer/test_beryl_ax_tinylm.py
Lauburu Mesh Ecosystem — 2026
"""

import importlib.util
import sys
import pytest
from pathlib import Path

_curr_dir = Path(__file__).resolve().parent

def _load_module(name: str, path: Path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

# Import Active Watchdog & TinyLM Benchmark
_watchdog_mod = _load_module("active_health_watchdog", _curr_dir / "active_health_watchdog.py")
BerylAXActiveHealthWatchdog = _watchdog_mod.BerylAXActiveHealthWatchdog

_bench_mod = _load_module("beryl_ax_tinylm_benchmark", _curr_dir / "beryl_ax_tinylm_benchmark.py")
BerylAXTinyLMBenchmark = _bench_mod.BerylAXTinyLMBenchmark


def test_beryl_ax_active_watchdog_triggers():
    """Verifies that the Beryl AX watchdog correctly identifies anomalies and dispatches self-healing."""
    watchdog = BerylAXActiveHealthWatchdog()

    # 1. Normal telemetry pass
    events_clean = watchdog.evaluate_system_health({
        "wan_rtt_ms": 12.0,
        "packet_loss_pct": 0.0,
        "tailscale_handshake_age_s": 15,
        "wifi_airtime_congestion_pct": 8.0,
        "memory_available_mb": 220.0,
    })
    assert len(events_clean) == 0

    # 2. Tailscale drop trigger (Path 1)
    events_ts = watchdog.evaluate_system_health({
        "wan_rtt_ms": 12.0,
        "packet_loss_pct": 0.0,
        "tailscale_handshake_age_s": 150,  # > 120s threshold
        "wifi_airtime_congestion_pct": 8.0,
        "memory_available_mb": 220.0,
    })
    assert len(events_ts) == 1
    assert events_ts[0].metric_name == "tailscale_handshake_age_s"
    assert events_ts[0].healing_success is True
    assert "Path 1" in events_ts[0].healing_pathway_dispatched

    # 3. Wi-Fi Congestion trigger
    events_wifi = watchdog.evaluate_system_health({
        "wan_rtt_ms": 12.0,
        "packet_loss_pct": 0.0,
        "tailscale_handshake_age_s": 20,
        "wifi_airtime_congestion_pct": 32.0,  # > 20% threshold
        "memory_available_mb": 220.0,
    })
    assert len(events_wifi) == 1
    assert events_wifi[0].metric_name == "wifi_airtime_congestion_pct"
    assert events_wifi[0].healing_success is True


def test_beryl_ax_tinylm_capability_benchmark():
    """Verifies that SmolLM-135M satisfies all 5 production criteria on the 512MB Beryl AX profile."""
    bench = BerylAXTinyLMBenchmark(model_name="SmolLM2-135M-Instruct-Q4_K_M")
    report = bench.run_full_capability_suite(num_runs=20)

    # 1. Check RAM budget
    assert report.total_router_ram_mb == 512
    assert report.usable_router_ram_mb == 492
    assert report.total_rss_footprint_mb <= report.cgroup_ai_cap_mb  # <= 120 MB
    assert report.diagnostics["free_buffer_headroom_mb"] >= 180.0

    # 2. Check Token Generation Velocity on Cortex-A53
    assert report.token_generation_rate_tps >= 15.0

    # 3. Check GBNF JSON Schema Conformance
    assert report.gbnf_schema_conformance_pct == 100.0

    # 4. Check Forwarding Jitter under CPU Load
    assert report.p99_rfc3393_udp_jitter_ms < 0.05

    # 5. Check Overall Production Certification
    assert report.autonomous_healing_accuracy_pct >= 95.0
    assert report.is_production_certified is True
