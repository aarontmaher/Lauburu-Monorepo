# -*- coding: utf-8 -*-
"""
Verification Tests for Qwen-Math Formal Optimization Verifier
============================================================
Subsystem: 01_apps/glinet_web_optimizer/test_qwen_math_verifier.py
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

_math_mod = _load_module("qwen_math_verifier", _curr_dir / "qwen_math_verifier.py")
QwenMathVerifier = _math_mod.QwenMathVerifier
MathProofCertificate = _math_mod.MathProofCertificate


def test_cake_aqm_bufferbloat_proof():
    """Verifies that Cake AQM mathematically bounds queue delay to 5ms."""
    verifier = QwenMathVerifier()
    cert = verifier.prove_bufferbloat_aqm_bound(
        bandwidth_mbps=450.0,
        queue_limit_packets=1024,
        target_delay_ms=5.0,
        interval_ms=100.0,
    )
    assert cert.is_valid is True
    assert cert.empirical_value == 5.0
    assert cert.safety_margin_pct > 80.0  # Over 80% latency reduction
    assert "D_queue <= 5.0 ms" in cert.theoretical_bound


def test_xor_fec_packet_recovery_math():
    """Verifies binomial packet recovery probability for (K=10, N=4) XOR FEC."""
    verifier = QwenMathVerifier()
    cert = verifier.prove_xor_fec_packet_recovery(
        k_data_packets=10,
        n_parity_packets=4,
        raw_packet_loss_rate=0.05,
    )
    assert cert.is_valid is True
    assert cert.empirical_value < 0.001  # Residual loss drops to <0.001
    assert cert.diagnostics["residual_loss_pct"] < 0.05
    assert cert.diagnostics["improvement_factor"] > 100.0


def test_multipath_waterfilling_convex_optimization():
    """Verifies proportional BDP water-filling optimization for multi-WAN bonding."""
    verifier = QwenMathVerifier()
    links = {
        "wifi7": (500.0, 2.5),   # 500 Mbps, 2.5 ms RTT
        "eth0": (1000.0, 1.0),   # 1000 Mbps, 1.0 ms RTT
        "usb0_5g": (150.0, 25.0) # 150 Mbps, 25.0 ms RTT
    }
    cert = verifier.prove_multipath_waterfilling_weights(links=links)
    assert cert.is_valid is True
    weights = cert.diagnostics["calculated_weights"]
    assert abs(sum(weights.values()) - 1.0) < 1e-3
    assert weights["eth0"] > weights["wifi7"] > weights["usb0_5g"]


def test_500mb_router_zero_oom_memory_invariant():
    """Verifies strict mathematical proof of 500 MB (492 MB usable) zero-OOM partitioning."""
    verifier = QwenMathVerifier()
    cert = verifier.prove_500mb_router_memory_invariants(
        kernel_base_mb=166.0,
        daemons_rss_mb=7.0,
        ai_cgroup_mb=120.0,
        total_usable_ram_mb=492.0,
    )
    assert cert.is_valid is True
    assert cert.diagnostics["free_headroom_mb"] >= 199.0
    assert cert.safety_margin_pct >= 40.0
    assert cert.diagnostics["committed_mb"] == 293.0
