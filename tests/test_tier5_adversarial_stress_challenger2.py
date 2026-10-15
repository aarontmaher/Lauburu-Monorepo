# -*- coding: utf-8 -*-
"""
Tier 5 Adversarial Stress Testing Suite — Challenger 2
======================================================
Subsystem: tests/test_tier5_adversarial_stress_challenger2.py
Milestone: M6 / Tier 5 Hardening & Adversarial Verification

Comprehensive empirical stress tests targeting:
1. Dual-World Simulation & Lookahead Interceptor (lookahead_interceptor.py, agentworld_driver.py, webworld_driver.py)
   - Dangerous command injection, 30-step trajectory rollouts, CoW VFS isolation, ShadowDOM overflows, route regressions, admission gating.
2. TrainingRollbackWatchdog (training_rollback_watchdog.py)
   - NaN/Inf loss injection, rapid memory leaks, TUI frame drops (>50ms), concurrent metric recording, Obsidian snapshot persistence.
3. Pan-Tompkins 512Hz ECG DSP & Rule #0 (pan_tompkins_qrs.py, ptt_blood_pressure.py, dfa_alpha1.py)
   - Noisy motion artifacts, 50Hz mains hum, flatlines, extreme heart rates (30-220 BPM), Kamath filter, PTT BP clamps, DFA-alpha1.
4. Multi-OS Heterogeneous Sharding (prima_ring_adapter.py)
   - CRC32 chunk verification, corruption detection, latency probes (<0.30ms SLA), layer migration over TB4 DMA.
5. Shopify Gateway (shopify_storefront_gateway.py)
   - Token forgery, HMAC tampering, expired token replay attacks, sliding window rate limiter overflow (429), tier route gating.

Zero-Mock Truth Enforcement: All tests run genuine mathematical computation, authentic algorithms, and strict Rule #0 compliance.
"""

from __future__ import annotations

import ast
import json
import math
import os
import shutil
import sys
import tempfile
import threading
import time
import zlib
from pathlib import Path
from typing import Any, Dict, List

import pytest
import numpy as np

# Ensure project root & subsystem folders are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
for sub_path in [
    str(PROJECT_ROOT),
    str(PROJECT_ROOT / "01_apps" / "commerce"),
    str(PROJECT_ROOT / "02_ai_models_and_inference" / "simulation"),
    str(PROJECT_ROOT / "02_ai_models_and_inference" / "sharding_daemon"),
    str(PROJECT_ROOT / "03_biometrics_and_telemetry" / "dsp"),
    str(PROJECT_ROOT / "04_data_and_memory"),
]:
    if sub_path not in sys.path:
        sys.path.insert(0, sub_path)

# ── Imports for Subsystems under test ──────────────────────────────────────────
from lookahead_interceptor import (
    LookaheadInterceptor,
    AdmissionGateResult,
    MIN_SAFETY_SCORE,
    MAX_REGRESSION_PROB,
    MAX_LAYOUT_OVERFLOWS,
    MIN_SIMULATION_CONFIDENCE,
)
from agentworld_driver import (
    AgentWorldDriver,
    CopyOnWriteVFS,
    AgentWorldStepResult,
    DANGEROUS_COMMAND_PATTERNS,
)
from webworld_driver import (
    WebWorldDriver,
    ShadowDOM,
    ShadowDOMNode,
    WebWorldStepResult,
    calculate_contrast_ratio,
)
from training_rollback_watchdog import (
    TrainingRollbackWatchdog,
    CheckpointRecord,
    StepMetricSnapshot,
)
from pan_tompkins_qrs import (
    PanTompkinsQRSDetector,
    apply_kamath_artifact_filter,
    apply_kamath_filter,
    calculate_rmssd,
    calculate_sdnn,
    calculate_pnn50,
)
from ptt_blood_pressure import (
    PTTBloodPressureModel,
    BloodPressureReading,
    calculate_ptt_from_ecg_ppg,
    calculate_hemodynamics_bp,
)
from dfa_alpha1 import (
    calculate_dfa_alpha1,
    calculate_dfa_scaling_curve,
    classify_zone2_alignment,
    classify_aerobic_threshold,
    RollingDFAAlpha1Tracker,
    DFAScalingResult,
)
from prima_ring_adapter import (
    PrimaTB4OffloadManager,
    _state as prima_ring_state,
    TB4_BRIDGE_IP,
)
from shopify_storefront_gateway import (
    ShopifyStorefrontGraphQLClient,
    MemberAPIGateway,
    CustomerTier,
    CustomerProfile,
    GatewayResponse,
    SlidingWindowRateLimiter,
)


# ==============================================================================
# 1. DUAL-WORLD SIMULATION & LOOKAHEAD INTERCEPTOR ADVERSARIAL TESTS
# ==============================================================================

class TestDualWorldSimulationAdversarial:
    """Stress tests for LookaheadInterceptor, AgentWorldDriver, and WebWorldDriver."""

    @pytest.fixture
    def temp_vfs_root(self):
        tmp_dir = tempfile.mkdtemp(prefix="test_vfs_")
        yield tmp_dir
        shutil.rmtree(tmp_dir, ignore_errors=True)

    @pytest.mark.parametrize("dangerous_cmd", [
        "rm -rf /",
        "rm -rf /*",
        "rm -rf /etc",
        "rm -rf /boot",
        "rm -rf /System",
        "rm -rf /usr",
        "rm -rf /var",
        "rm -rf $HOME",
        "rm -rf ~",
        "mkfs.ext4 /dev/sda1",
        "dd if=/dev/zero of=/dev/disk0",
        ":(){ :|:& };:",
        "> /etc/passwd",
        "> /etc/shadow",
        "chmod -R 777 /",
        "chmod 777 /etc",
        "shutdown -h now",
        "reboot",
        "init 0",
        "rm -rf .",
        "rm -rf ..",
    ])
    def test_dangerous_command_injection_rejection(self, dangerous_cmd):
        """Stress-test dangerous command injection patterns against AgentWorldDriver and LookaheadInterceptor."""
        interceptor = LookaheadInterceptor()
        driver = AgentWorldDriver()

        # 1. Direct driver check
        is_safe, reason = driver.check_command_safety(dangerous_cmd)
        assert is_safe is False, f"Driver failed to flag dangerous command: {dangerous_cmd}"
        assert "Dangerous" in reason or "Destructive" in reason or "rejected" in reason

        # 2. Simulation execution check
        vfs = CopyOnWriteVFS()
        res = driver.simulate_shell_command(dangerous_cmd, vfs=vfs)
        assert res.exit_code == 126
        assert res.safety_score == 0.0
        assert res.regression_probability == 1.0
        assert "[SECURITY_VIOLATION]" in res.stderr

        # 3. Interceptor trajectory rollout check
        callback_called = [False]
        def physical_callback():
            callback_called[0] = True
            return "DESTRUCTIVE_EXECUTED"

        admitted, score, diag, exec_res = interceptor.intercept_and_execute(
            action_type="system_command",
            action_payload={"command": dangerous_cmd},
            execution_callback=physical_callback,
            lookahead_steps=10,
        )

        assert admitted is False
        assert score < 0.70
        assert diag["verdict"] == "REJECTED_GATING_BREACH"
        assert diag["execution_status"] == "BLOCKED_BY_GATING"
        assert callback_called[0] is False, "Dangerous command bypassed admission gating and executed callback!"

    def test_30_step_trajectory_rollout_full_lifecycle(self, temp_vfs_root):
        """Validates complete 30-step trajectory rollout in AgentWorld shadow state."""
        interceptor = LookaheadInterceptor(base_dir=temp_vfs_root)
        
        admitted, composite_score, diagnostics = interceptor.simulate_trajectory(
            action_type="system_command",
            action_payload={"command": "python -c 'print(42)'"},
            lookahead_steps=30,
        )

        assert admitted is True
        assert composite_score >= 0.85
        assert diagnostics["lookahead_steps"] == 30
        assert diagnostics["steps_completed"] == 30
        assert len(diagnostics["step_results"]) == 30
        assert diagnostics["safety_score"] >= 0.90
        assert diagnostics["regression_probability"] <= 0.05
        assert diagnostics["verdict"] == "ADMITTED_CERTIFIED"

    def test_copy_on_write_vfs_complete_isolation(self, temp_vfs_root):
        """Verifies CoW VFS isolates all file creations/modifications/deletions without touching real disk."""
        # Create a real file in temp directory
        real_file = Path(temp_vfs_root) / "real_file.txt"
        real_file.write_text("ORIGINAL_REAL_DATA", encoding="utf-8")

        vfs = CopyOnWriteVFS(base_real_root=temp_vfs_root)
        
        # 1. Read through to real file
        content = vfs.read_file("real_file.txt")
        assert content == "ORIGINAL_REAL_DATA"

        # 2. Virtual write (modification)
        vfs.write_file("real_file.txt", "SHADOW_MUTATION_DATA")
        assert vfs.read_file("real_file.txt") == "SHADOW_MUTATION_DATA"
        # Real disk must remain untouched
        assert real_file.read_text(encoding="utf-8") == "ORIGINAL_REAL_DATA"

        # 3. Virtual file creation
        vfs.write_file("virtual_dir/nested/new_file.py", "x = 10\n")
        assert vfs.exists("virtual_dir/nested/new_file.py") is True
        assert not (Path(temp_vfs_root) / "virtual_dir" / "nested" / "new_file.py").exists()

        # 4. Virtual deletion
        assert vfs.remove_file("real_file.txt") is True
        assert vfs.exists("real_file.txt") is False
        assert vfs.read_file("real_file.txt") is None
        # Real file still exists physically
        assert real_file.exists() is True

        # 5. Clone independence
        cloned_vfs = vfs.clone()
        cloned_vfs.write_file("clone_only.txt", "CLONE_DATA")
        assert cloned_vfs.exists("clone_only.txt") is True
        assert vfs.exists("clone_only.txt") is False

    def test_shadowdom_layout_overflow_and_clipping_detection(self):
        """Tests WebWorld shadow DOM detecting viewport and container clipping overflows."""
        interceptor = LookaheadInterceptor()
        
        # 1. Viewport horizontal overflow: width 1500px in 1280px viewport without overflow-x-auto
        admitted, score, diag = interceptor.simulate_trajectory(
            action_type="dom_update",
            action_payload={
                "mutation": {
                    "tag": "div",
                    "width": 1500.0,
                    "height": 200.0,
                    "classes": ["w-[1500px]"],
                    "styles": {"width": 1500.0},
                }
            },
            lookahead_steps=10,
        )

        assert admitted is False
        assert diag["layout_overflows"] > 0
        assert "Layout overflow count" in " ".join(diag["reasons"])

        # 2. Container clipping overflow: parent width 200px, overflow-hidden, child x=150, width=100 (total 250px)
        dom = ShadowDOM(viewport_width=1280.0, viewport_height=800.0)
        parent_node = ShadowDOMNode(
            tag="div",
            node_id="parent_box",
            width=200.0,
            classes=["overflow-hidden"],
            styles={"overflow": "hidden"},
            x=0.0,
        )
        dom.add_node("root_html", parent_node)
        
        child_node = ShadowDOMNode(
            tag="div",
            node_id="overflowing_child",
            x=150.0,
            width=100.0,
        )
        dom.add_node("parent_box", child_node)

        overflows = dom.evaluate_layout_overflows()
        assert len(overflows) >= 1
        assert overflows[0]["type"] == "CONTAINER_CLIPPING_OVERFLOW"
        assert overflows[0]["overflow_pixels"] == 50.0

    def test_shadowdom_wcag_contrast_and_broken_route_regressions(self):
        """Tests WebWorld WCAG contrast violations and broken internal route (404) detection."""
        dom = ShadowDOM()

        # 1. Low contrast button: #888888 on #777777 (ratio ~ 1.29:1 < 4.5:1)
        btn_node = ShadowDOMNode(
            tag="button",
            node_id="btn_low_contrast",
            text_content="Submit",
            styles={"color": "#888888", "background": "#777777"},
        )
        dom.add_node("root_html", btn_node)
        wcag_issues = dom.evaluate_accessibility_and_contrast()
        contrast_violations = [v for v in wcag_issues if v["type"] == "WCAG_CONTRAST_VIOLATION"]
        assert len(contrast_violations) >= 1
        assert contrast_violations[0]["contrast_ratio"] < 4.5

        # 2. Broken internal route: <a href="/non_existent_dashboard_view">
        link_node = ShadowDOMNode(
            tag="a",
            node_id="broken_link",
            text_content="Broken Link",
            attributes={"href": "/invalid_route_404"},
        )
        dom.add_node("root_html", link_node)
        route_regressions = dom.evaluate_route_and_link_regressions()
        assert len(route_regressions) >= 1
        assert route_regressions[0]["type"] == "BROKEN_INTERNAL_ROUTE_404"
        assert route_regressions[0]["unresolved_target"] == "/invalid_route_404"

    def test_admission_gating_boundary_and_formula_limits(self):
        """Stress-tests admission gating exact threshold boundaries and composite score formula."""
        interceptor = LookaheadInterceptor()

        # Exact boundary: S=0.90, P_reg=0.05, O=0, C=0.85 -> Admitted
        res_exact = interceptor.evaluate_admission_gate(0.90, 0.05, 0, 0.85)
        assert res_exact.admitted is True
        assert res_exact.verdict == "ADMITTED_CERTIFIED"

        # Safety failure: S = 0.8999
        res_s = interceptor.evaluate_admission_gate(0.8999, 0.05, 0, 0.85)
        assert res_s.admitted is False
        assert "Safety score" in res_s.reasons[0]

        # Regression failure: P_reg = 0.0501
        res_p = interceptor.evaluate_admission_gate(0.90, 0.0501, 0, 0.85)
        assert res_p.admitted is False
        assert "Regression probability" in res_p.reasons[0]

        # Layout failure: O = 1
        res_o = interceptor.evaluate_admission_gate(0.90, 0.05, 1, 0.85)
        assert res_o.admitted is False
        assert "Layout overflow" in res_o.reasons[0]

        # Confidence failure: C = 0.8499
        res_c = interceptor.evaluate_admission_gate(0.90, 0.05, 0, 0.8499)
        assert res_c.admitted is False
        assert "Simulation confidence" in res_c.reasons[0]

        # Composite score formula: 0.40*S + 0.30*(1 - P_reg) + 0.20*C + 0.10*layout
        score = interceptor.compute_composite_score(1.0, 0.0, 0, 1.0)
        assert score == 1.0


# ==============================================================================
# 2. TRAINING ROLLBACK WATCHDOG ADVERSARIAL TESTS
# ==============================================================================

class TestTrainingRollbackWatchdogAdversarial:
    """Stress tests for TrainingRollbackWatchdog with NaN/Inf injection, memory leaks, and TUI drops."""

    @pytest.fixture
    def watchdog_env(self):
        tmp_obs = tempfile.mkdtemp(prefix="test_obsidian_")
        tmp_log = Path(tmp_obs) / "events.jsonl"
        wd = TrainingRollbackWatchdog(
            obsidian_dir=tmp_obs,
            rollback_log_file=tmp_log,
            auto_rollback=True,
        )
        yield wd, tmp_obs, tmp_log
        shutil.rmtree(tmp_obs, ignore_errors=True)

    def test_loss_nan_inf_negative_and_spike_divergence(self, watchdog_env):
        """Tests watchdog immediately halts training and triggers rollback on NaN, Inf, negative loss, or 3x spike."""
        wd, obsidian_dir, log_file = watchdog_env
        wd.register_checkpoint("cp_step_100", "/models/cp_100", step=100, loss=1.5, is_certified=True)

        # 1. Warm-up baseline steps
        for s in range(101, 106):
            healthy, msg, _ = wd.record_step_metrics(step=s, loss=1.45)
            assert healthy is True

        # 2. NaN loss injection
        healthy, msg, diag = wd.record_step_metrics(step=106, loss=float("nan"))
        assert healthy is False
        assert "LOSS_DIVERGENCE: Loss is NaN at step 106" in msg
        assert wd.get_status()["is_training_active"] is False

        # Reset & resume
        wd.resume_training()
        assert wd.get_status()["is_training_active"] is True

        # 3. Inf loss injection
        healthy, msg, _ = wd.record_step_metrics(step=107, loss=float("inf"))
        assert healthy is False
        assert "Loss is Inf" in msg

        # Reset & resume
        wd.resume_training()

        # 4. Negative loss injection
        healthy, msg, _ = wd.record_step_metrics(step=108, loss=-0.5)
        assert healthy is False
        assert "Loss is negative" in msg

        # Reset & resume
        wd.resume_training()

        # 5. Loss spike > 3.0x baseline (1.45 * 3.0 = 4.35 -> inject 5.0)
        healthy, msg, _ = wd.record_step_metrics(step=109, loss=5.0)
        assert healthy is False
        assert "spiked > 3.0x above baseline" in msg

    def test_memory_leakage_and_ram_ceiling_breach(self, watchdog_env):
        """Tests watchdog triggers rollback on Host RAM > 85%, Headroom < 2.5GB, or RSS growth > 250 MB/min."""
        wd, _, _ = watchdog_env
        wd.register_checkpoint("cp_step_200", "/models/cp_200", step=200, loss=1.2, is_certified=True)

        # 1. Host RAM usage breach (86.0% > 85.0%)
        healthy, msg, _ = wd.record_step_metrics(step=201, loss=1.2, ram_used_pct=86.0, ram_headroom_gb=3.0)
        assert healthy is False
        assert "Host RAM usage (86.0%) exceeds safety ceiling (85.0%)" in msg

        wd.resume_training()

        # 2. Low Headroom breach (2.10 GB < 2.50 GB)
        healthy, msg, _ = wd.record_step_metrics(step=202, loss=1.2, ram_used_pct=75.0, ram_headroom_gb=2.10)
        assert healthy is False
        assert "Free RAM headroom (2.10 GB) is below minimum (2.50 GB)" in msg

    def test_tui_render_latency_frame_drop_violation(self, watchdog_env):
        """Tests watchdog triggers rollback when TUI frame render latency exceeds 50.0ms."""
        wd, _, _ = watchdog_env
        wd.register_checkpoint("cp_step_300", "/models/cp_300", step=300, loss=1.0, is_certified=True)

        healthy, msg, diag = wd.record_step_metrics(step=301, loss=1.0, tui_latency_ms=58.4)
        assert healthy is False
        assert "TUI_FRAME_DROP: TUI render latency (58.4ms) exceeds 50ms frame budget" in msg
        assert diag["violations"][0].startswith("TUI_FRAME_DROP")

    def test_obsidian_diagnostics_snapshot_and_callback(self, watchdog_env):
        """Tests automatic markdown snapshot persistence to Obsidian and callback invocation."""
        wd, obsidian_dir, log_file = watchdog_env
        wd.register_checkpoint("cp_certified_400", "/models/cp_400", step=400, loss=0.85, is_certified=True)

        callback_invocations = []
        def rollback_cb(payload):
            callback_invocations.append(payload)
            return "ROLLBACK_ACK"

        wd.register_rollback_callback(rollback_cb)

        # Trigger violation
        wd.record_step_metrics(step=401, loss=float("nan"))

        # Verify callback invoked
        assert len(callback_invocations) == 1
        assert callback_invocations[0]["target_checkpoint_id"] == "cp_certified_400"
        assert callback_invocations[0]["target_checkpoint_step"] == 400

        # Verify Obsidian note exists and contains mandatory tags & links
        notes = list(Path(obsidian_dir).glob("ROLLBACK_DIAGNOSTICS_*.md"))
        assert len(notes) >= 1
        note_content = notes[0].read_text(encoding="utf-8")
        assert "[[Index]]" in note_content
        assert "[[CANONICAL_PROJECT_AND_STORAGE_RULE]]" in note_content
        assert "cp_certified_400" in note_content

        # Verify JSONL log
        assert log_file.exists()
        lines = log_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) >= 1
        log_entry = json.loads(lines[-1])
        assert log_entry["event"] == "TRAINING_AUTO_ROLLBACK"
        assert log_entry["target_checkpoint_id"] == "cp_certified_400"

    def test_multithreaded_concurrent_metric_recording(self, watchdog_env):
        """Stress-tests watchdog concurrency with 10 threads recording metrics simultaneously."""
        wd, _, _ = watchdog_env
        wd.register_checkpoint("cp_concurrency", "/models/cp_conc", step=0, loss=2.0)

        errors = []
        def worker(thread_id):
            try:
                for i in range(20):
                    step_num = thread_id * 100 + i
                    wd.record_step_metrics(step=step_num, loss=1.5 + (i * 0.01))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Concurrent watchdog execution raised exceptions: {errors}"
        status = wd.get_status()
        assert status["total_steps_monitored"] == 200


# ==============================================================================
# 3. PAN-TOMPKINS 512Hz ECG DSP & BIOMETRICS ADVERSARIAL TESTS
# ==============================================================================

class TestPanTompkinsBiometricsDSPAdversarial:
    """Stress tests for Pan-Tompkins QRS detector, PTT BP model, and DFA-alpha1."""

    def _generate_synthetic_ecg(
        self,
        duration_sec: float = 10.0,
        fs: int = 512,
        bpm: float = 60.0,
        noise_amplitude: float = 0.05,
        add_mains_hum: bool = False,
    ) -> List[float]:
        """Generates realistic ECG waveform with continuous P-QRS-T complexes."""
        total_samples = int(duration_sec * fs)
        signal = [0.0] * total_samples
        rr_samples = int((60.0 / bpm) * fs)

        peak_positions = list(range(int(0.3 * fs), total_samples - int(0.3 * fs), rr_samples))
        for r_idx in peak_positions:
            # Generate Gaussian QRS complex with realistic duration (~60ms, sigma = 15ms)
            sigma_qrs = int(0.015 * fs)
            for offset in range(-3 * sigma_qrs, 3 * sigma_qrs + 1):
                idx = r_idx + offset
                if 0 <= idx < total_samples:
                    # Gaussian R-wave (1.5 mV)
                    signal[idx] += 1.50 * math.exp(-0.5 * (offset / float(sigma_qrs)) ** 2)

            # Q wave (-0.2 mV)
            q_idx = r_idx - int(0.025 * fs)
            sigma_q = int(0.010 * fs)
            for offset in range(-2 * sigma_q, 2 * sigma_q + 1):
                idx = q_idx + offset
                if 0 <= idx < total_samples:
                    signal[idx] -= 0.20 * math.exp(-0.5 * (offset / float(sigma_q)) ** 2)

            # S wave (-0.3 mV)
            s_idx = r_idx + int(0.025 * fs)
            sigma_s = int(0.010 * fs)
            for offset in range(-2 * sigma_s, 2 * sigma_s + 1):
                idx = s_idx + offset
                if 0 <= idx < total_samples:
                    signal[idx] -= 0.30 * math.exp(-0.5 * (offset / float(sigma_s)) ** 2)

            # T wave (+0.3 mV)
            t_idx = r_idx + int(0.180 * fs)
            sigma_t = int(0.040 * fs)
            for offset in range(-3 * sigma_t, 3 * sigma_t + 1):
                idx = t_idx + offset
                if 0 <= idx < total_samples:
                    signal[idx] += 0.30 * math.exp(-0.5 * (offset / float(sigma_t)) ** 2)

        # Add Gaussian noise / mains hum
        for i in range(total_samples):
            t = i / float(fs)
            if add_mains_hum:
                signal[i] += 0.08 * math.sin(2.0 * math.pi * 50.0 * t)  # 50Hz mains hum
                signal[i] += 0.05 * math.sin(2.0 * math.pi * 0.25 * t)  # 0.25Hz respiration wander
            if noise_amplitude > 0:
                signal[i] += noise_amplitude * (math.sin(i * 1.7) * math.cos(i * 0.3))

        return signal

    def test_pan_tompkins_noisy_artifacts_and_mains_hum(self):
        """Tests Pan-Tompkins QRS detector under high 50Hz mains noise and baseline drift."""
        detector = PanTompkinsQRSDetector(sample_rate_hz=512)
        ecg_noisy = self._generate_synthetic_ecg(duration_sec=10.0, fs=512, bpm=72.0, noise_amplitude=0.08, add_mains_hum=True)
        
        peaks, rr_ms = detector.detect_qrs_peaks(ecg_noisy)
        assert len(peaks) >= 9, f"Detector missed beats under noise (expected >=9, got {len(peaks)})"
        assert len(rr_ms) >= 8, f"Expected >= 8 RR intervals, got {len(rr_ms)}"

        # Expected RR at 72 BPM: ~833 ms
        mean_rr = sum(rr_ms) / len(rr_ms)
        assert 750.0 <= mean_rr <= 920.0, f"Mean RR {mean_rr:.1f}ms deviates from expected ~833ms"

    def test_pan_tompkins_flatline_and_zero_signal(self):
        """Tests Pan-Tompkins with flatline (all zero or constant DC) returns empty peaks (zero false positives)."""
        detector = PanTompkinsQRSDetector(sample_rate_hz=512)
        
        # 1. All zeros
        zero_signal = [0.0] * (512 * 5)
        peaks, rr = detector.detect_qrs_peaks(zero_signal)
        assert peaks == []
        assert rr == []

        # 2. Constant DC offset (500 mV)
        dc_signal = [500.0] * (512 * 5)
        peaks_dc, rr_dc = detector.detect_qrs_peaks(dc_signal)
        assert peaks_dc == []
        assert rr_dc == []

    @pytest.mark.parametrize("target_bpm", [30.0, 45.0, 120.0, 180.0, 220.0])
    def test_pan_tompkins_extreme_heart_rates(self, target_bpm):
        """Stress-tests Pan-Tompkins from severe bradycardia (30 BPM) to extreme tachycardia (220 BPM)."""
        detector = PanTompkinsQRSDetector(sample_rate_hz=512)
        ecg = self._generate_synthetic_ecg(duration_sec=12.0, fs=512, bpm=target_bpm, noise_amplitude=0.02)
        
        peaks, rr_ms = detector.detect_qrs_peaks(ecg)
        assert len(peaks) >= 4, f"Failed detection at {target_bpm} BPM"
        
        expected_rr = (60.0 / target_bpm) * 1000.0
        mean_rr = sum(rr_ms) / len(rr_ms)
        assert abs(mean_rr - expected_rr) / expected_rr < 0.15, f"BPM {target_bpm}: mean RR {mean_rr} vs expected {expected_rr}"

    def test_kamath_artifact_filter_and_hrv_metrics(self):
        """Tests Kamath 20% clinical RR filter correcting ectopic bursts and HRV metric calculations."""
        # Baseline ~800ms with ectopic spikes at index 3 (1300ms) and index 7 (400ms)
        raw_rrs = [800.0, 805.0, 795.0, 1300.0, 800.0, 802.0, 798.0, 400.0, 805.0, 800.0]
        cleaned, art_count = apply_kamath_artifact_filter(raw_rrs, threshold_pct=20.0)
        
        assert art_count == 2
        assert len(cleaned) == len(raw_rrs)
        assert cleaned[3] < 1100.0, "Kamath filter failed to interpolate high ectopic burst"
        assert cleaned[7] > 550.0, "Kamath filter failed to interpolate low ectopic beat"

        # HRV Metrics
        rmssd = calculate_rmssd(cleaned)
        sdnn = calculate_sdnn(cleaned)
        pnn50 = calculate_pnn50(cleaned)
        assert rmssd is not None and rmssd >= 0.0
        assert sdnn is not None and sdnn >= 0.0
        assert pnn50 is not None and 0.0 <= pnn50 <= 100.0

        # Rule #0 compliance: empty or single element returns None
        assert calculate_rmssd([]) is None
        assert calculate_sdnn([800.0]) is None
        assert calculate_pnn50([]) is None

    def test_ptt_blood_pressure_physiological_clamps_and_rule_0(self):
        """Tests PTT blood pressure estimation, physiological clamping (60-240 SBP, 40-140 DBP), and Rule #0."""
        model = PTTBloodPressureModel()

        # 1. Rule #0 compliance on missing / invalid inputs
        standby_reading = model.estimate_blood_pressure(ptt_ms=None, hr_bpm=None)
        assert standby_reading.status == "STANDBY"
        assert standby_reading.systolic_mmhg is None
        assert standby_reading.diastolic_mmhg is None
        assert standby_reading.rule_0_zero_mock is True

        # Unphysiological PTT < 80ms
        unphys_ptt = model.estimate_blood_pressure(ptt_ms=50.0, hr_bpm=70.0)
        assert unphys_ptt.status == "STANDBY"
        assert unphys_ptt.systolic_mmhg is None

        # 2. Nominal physiological reading
        nominal = model.estimate_blood_pressure(ptt_ms=200.0, hr_bpm=70.0)
        assert nominal.status == "NOMINAL"
        assert nominal.systolic_mmhg == 120.0
        assert nominal.diastolic_mmhg == 80.0
        assert nominal.classification == model.CLASSIFICATIONS["NORMAL"]

        # 3. Extreme high stress / hypertensive crisis: PTT = 90ms, HR = 180 BPM
        hyper = model.estimate_blood_pressure(ptt_ms=90.0, hr_bpm=180.0)
        assert hyper.systolic_mmhg > 160.0
        assert hyper.classification in [model.CLASSIFICATIONS["HYPERTENSIVE_STAGE2"], model.CLASSIFICATIONS["HYPERTENSIVE_CRISIS"]]

        # 4. Calibration
        calib_ok = model.calibrate(cuff_sbp=125.0, cuff_dbp=82.0, measured_ptt_ms=195.0, measured_hr_bpm=72.0)
        assert calib_ok is True
        assert model.calibrated is True
        assert model.baseline_sbp == 125.0

    def test_dfa_alpha1_scaling_and_lactate_threshold_zones(self):
        """Tests Detrended Fluctuation Analysis (DFA-alpha1) scaling and zone classification."""
        # 1. Rule #0: Insufficient beats (< 4) returns None
        assert calculate_dfa_alpha1([800.0, 810.0, 790.0]) is None

        # 2. Correlated physiological RR series with stochastic noise
        np.random.seed(42)
        base_rr = 850.0
        correlated_rrs = [base_rr]
        for _ in range(70):
            # AR(1) process simulating fractal HRV
            new_val = 850.0 + 0.75 * (correlated_rrs[-1] - 850.0) + float(np.random.normal(0, 15.0))
            correlated_rrs.append(new_val)

        alpha1 = calculate_dfa_alpha1(correlated_rrs, scale_min=4, scale_max=16)
        assert alpha1 is not None
        assert 0.20 <= alpha1 <= 1.80

        # Complete scaling result
        result = calculate_dfa_scaling_curve(correlated_rrs)
        assert result.alpha1 is not None
        assert result.r_squared is not None
        assert len(result.scales) >= 3

        # 3. Threshold classifications
        assert classify_aerobic_threshold(0.85)["lt_transition"] == "BELOW_LT1"
        assert classify_aerobic_threshold(0.72)["lt_transition"] == "AT_LT1_TRANSITION"
        assert classify_aerobic_threshold(0.62)["lt_transition"] == "BETWEEN_LT1_LT2"
        assert classify_aerobic_threshold(0.50)["lt_transition"] == "AT_LT2_TRANSITION"
        assert classify_aerobic_threshold(0.40)["lt_transition"] == "ABOVE_LT2_ANAEROBIC"

        # 4. Rolling tracker
        tracker = RollingDFAAlpha1Tracker(max_beats=50)
        for rr in correlated_rrs:
            tracker.add_rr_interval(rr)
        assert tracker.get_current_alpha1() is not None


# ==============================================================================
# 4. MULTI-OS HETEROGENEOUS SHARDING (PRIMA RING ADAPTER) ADVERSARIAL TESTS
# ==============================================================================

class TestMultiOSShardingPrimaAdversarial:
    """Stress tests for PrimaRingAdapter TB4 DMA layer offloading and chunk integrity."""

    def test_prima_tb4_crc32_chunk_transfer_and_corruption_detection(self):
        """Tests activation chunk CRC32 verification and dropped chunk accounting on bit corruption."""
        manager = PrimaTB4OffloadManager.get_instance()

        # 1. Valid activation tensor transfer
        tensor_data = np.random.randn(32, 4096).astype(np.float32)
        success, lat_ms, crc = manager.transfer_activation_chunk(
            activation_data=tensor_data,
            layer_idx=12,
            seq_id=1001,
        )

        assert success is True
        assert lat_ms < 0.30, f"TB4 DMA latency {lat_ms:.3f}ms exceeds 0.30ms SLA"
        assert crc == zlib.crc32(tensor_data.tobytes())

        # 2. Raw bytes transfer
        raw_bytes = b"LAUBURU_ACTIVATION_TENSOR_LAYER_13_DATA_BYTES"
        s2, lat2, crc2 = manager.transfer_activation_chunk(raw_bytes, layer_idx=13, seq_id=1002)
        assert s2 is True
        assert crc2 == zlib.crc32(raw_bytes)

    def test_prima_tb4_latency_sla_probe(self):
        """Verifies TB4 DMA latency probe strictly satisfies <0.30ms SLA constraint."""
        manager = PrimaTB4OffloadManager.get_instance()
        
        for _ in range(5):
            lat = manager.probe_tb4_latency()
            assert lat < 0.30, f"Probe latency {lat:.3f}ms exceeded <0.30ms SLA"
            assert lat >= 0.10, f"Unrealistically low latency: {lat:.3f}ms"

        status = manager.get_status()
        assert status["latency_within_sla"] is True
        assert status["bandwidth_gbps"] >= 10.0

    def test_prima_tb4_dynamic_layer_offload_and_partitioning(self):
        """Tests layer partitioning across Mac Mini Host and TB4 MacBook Pro without overlap."""
        manager = PrimaTB4OffloadManager.get_instance()
        
        # Offload layers 12..23 (12 layers)
        target_layers = list(range(12, 24))
        ok = manager.offload_layers(target_layers=target_layers, target_node_ip=TB4_BRIDGE_IP)
        assert ok is True

        status = manager.get_status()
        offloaded = set(status["active_offloaded_layers"])
        host_retained = set(status["host_retained_layers"])

        # Invariants:
        # 1. No overlap between host and offloaded layers
        assert len(offloaded.intersection(host_retained)) == 0
        # 2. Union equals total layers (24)
        assert len(offloaded.union(host_retained)) == 24
        # 3. Offloaded layers match target
        assert sorted(list(offloaded)) == target_layers


# ==============================================================================
# 5. SHOPIFY GATEWAY & COMMERCE ADVERSARIAL TESTS
# ==============================================================================

class TestShopifyGatewayCommerceAdversarial:
    """Stress tests for MemberAPIGateway token verification, rate limiting, and route gating."""

    @pytest.fixture
    def gateway(self):
        return MemberAPIGateway(secret_key="test_adversarial_gateway_key_2026")

    def test_token_tampering_and_forgery_rejection(self, gateway):
        """Tests gateway rejects forged signatures, tampered customer IDs, and altered tiers."""
        valid_pro_token = gateway.issue_api_key("customer_12345", CustomerTier.PRO, expiry_days=7)
        assert gateway.verify_api_key(valid_pro_token) is not None

        # 1. Tampered signature (change last character)
        tampered_sig = valid_pro_token[:-1] + ("a" if valid_pro_token[-1] != "a" else "b")
        assert gateway.verify_api_key(tampered_sig) is None
        res1 = gateway.handle_request("/api/v1/telemetry/ecg", tampered_sig)
        assert res1.status_code == 403
        assert "Forbidden" in res1.error

        # 2. Tampered tier escalation (replace 'lauburu_pro' with 'lauburu_elite')
        tampered_tier = valid_pro_token.replace("lauburu_pro", "lauburu_elite")
        assert gateway.verify_api_key(tampered_tier) is None
        res2 = gateway.handle_request("/api/v1/telemetry/ecg", tampered_tier)
        assert res2.status_code == 403

        # 3. Malformed tokens
        assert gateway.verify_api_key("") is None
        assert gateway.verify_api_key("invalid_token") is None
        assert gateway.verify_api_key("lb_pro_1234") is None

    def test_token_expiration_replay_rejection(self, gateway):
        """Tests expired token replay attacks are rejected."""
        expiry_past = int(time.time()) - 100
        c_hex = "customer_exp".encode("utf-8").hex()[:16]
        msg = f"lauburu_pro:{c_hex}:{expiry_past}".encode("utf-8")
        import hashlib, hmac
        sig = hmac.new(gateway.secret_key, msg, hashlib.sha256).hexdigest()[:16]
        expired_token = f"lb_lauburu_pro_{c_hex}_{expiry_past}_{sig}"

        assert gateway.verify_api_key(expired_token) is None
        res = gateway.handle_request("/api/v1/telemetry/ecg", expired_token)
        assert res.status_code == 403

    def test_sliding_window_rate_limiter_overflow_429(self, gateway):
        """Stress-tests sliding window rate limiter enforcing RPM ceiling and returning HTTP 429."""
        free_token = gateway.issue_api_key("cust_rate_limit", CustomerTier.FREE, expiry_days=1)
        free_rpm_limit = CustomerTier.FREE.rate_limit_rpm  # 60 RPM

        # Exhaust 60 RPM quota
        for i in range(free_rpm_limit):
            resp = gateway.handle_request("/api/v1/telemetry/ecg", free_token)
            assert resp.status_code == 200, f"Request {i+1} unexpectedly failed"
            assert resp.rate_limit_remaining == free_rpm_limit - (i + 1)

        # 61st request in the same minute -> HTTP 429
        overflow_resp = gateway.handle_request("/api/v1/telemetry/ecg", free_token)
        assert overflow_resp.status_code == 429
        assert overflow_resp.success is False
        assert overflow_resp.rate_limit_remaining == 0
        assert overflow_resp.retry_after_sec is not None and overflow_resp.retry_after_sec >= 1
        assert "Rate limit exceeded" in overflow_resp.error

    def test_tier_gating_route_authorization(self, gateway):
        """Tests route authorization gating LoRA distillation to PRO/ELITE while blocking FREE."""
        free_token = gateway.issue_api_key("cust_free", CustomerTier.FREE)
        pro_token = gateway.issue_api_key("cust_pro", CustomerTier.PRO)
        elite_token = gateway.issue_api_key("cust_elite", CustomerTier.ELITE)

        # 1. Telemetry access: FREE gets 128Hz, PRO gets 512Hz
        res_free_tel = gateway.handle_request("/api/v1/telemetry/ecg", free_token)
        assert res_free_tel.status_code == 200
        assert res_free_tel.data["max_sampling_rate_hz"] == 128

        res_pro_tel = gateway.handle_request("/api/v1/telemetry/ecg", pro_token)
        assert res_pro_tel.status_code == 200
        assert res_pro_tel.data["max_sampling_rate_hz"] == 512

        # 2. LoRA distillation: FREE gets 403 Forbidden, PRO/ELITE gets 200 OK
        res_free_lora = gateway.handle_request("/api/v1/lora/distill", free_token)
        assert res_free_lora.status_code == 403
        assert "requires 'lauburu_pro' or 'lauburu_elite'" in res_free_lora.error

        res_pro_lora = gateway.handle_request("/api/v1/lora/distill", pro_token)
        assert res_pro_lora.status_code == 200
        assert res_pro_lora.data["status"] == "QUEUED_FOR_NIGHTLY_DISTILLATION"

        # 3. Unknown route -> 404
        res_404 = gateway.handle_request("/api/v1/invalid/endpoint", pro_token)
        assert res_404.status_code == 404
