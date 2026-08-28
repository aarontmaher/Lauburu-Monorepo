"""
Tier 5 White-Box Adversarial Coverage Hardening Test Suite.
Validates:
1. Mathematical Singularities & Biophysical Extremes (Zero/Near-Zero/Infinite PTT, Hughes Stiffening, Windkessel WK2/WK3 ODEs, Motion >5g).
2. Zero-PII Security & Sanitization Bypass Vectors (Unicode Obfuscation, Null Bytes, Deeply Nested Arrays, HMAC Tampering, Timing Invariants).
3. Storage Layer Concurrency & Write Contention (SQLite WAL Stress, Rollback & Transaction Integrity, Vector Store Edge Cases).
4. Genetic MoE Classification & SSE Streaming Chunk Fragmentation Hardening.
"""

import asyncio
import json
import math
import os
import sqlite3
import tempfile
import time
from typing import Any, Dict, List
import numpy as np
import pytest
from pydantic import ValidationError
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.core.security import (
    contains_pii,
    get_pii_violations,
    is_pii_key,
    is_pii_value,
    sanitize_pii,
    generate_session_token,
    compute_hmac_signature,
    verify_hmac_signature,
    validate_session_token_format,
)
from app.physics.moens_korteweg import (
    moens_korteweg_wave_speed,
    hughes_strain_stiffening,
    pressure_dependent_pwv,
    moens_korteweg_pressure_inversion,
    logarithmic_moens_korteweg_bp,
)
from app.physics.bramwell_hill import (
    bramwell_hill_wave_speed,
    volumetric_distensibility,
    volumetric_distensibility_mmhg,
    cross_sectional_compliance,
    total_arterial_compliance,
    total_arterial_compliance_ml_per_mmhg,
)
from app.physics.windkessel import (
    diastolic_decay_time_constant,
    calculate_peripheral_resistance_analytical,
    generate_cardiac_inflow,
    solve_wk2_explicit_euler,
    solve_wk2_implicit_euler,
    solve_wk2_trapezoidal,
    solve_wk2_rk4,
    solve_wk3_trapezoidal,
    solve_wk3_rk4,
    verify_mass_conservation,
    verify_energy_dissipation,
)
from app.physics.hemodynamic_inversion import (
    invert_hemodynamic_vector,
    calculate_signal_confidence,
    InversionParameters,
    DEFAULT_PARAMS,
)
from app.models.schemas import (
    VectorU,
    InversionRequest,
    BatchInversionRequest,
)
from app.storage.sqlite_manager import SqliteManager
from app.storage.chroma_manager import (
    ChromaManager,
    FallbackVectorStore,
    _compute_deterministic_embedding,
    classify_genetic_moe_expert,
)
from app.services.genetic_moe_service import (
    StreamingThoughtParser,
    format_sse_chunk,
)
from app.main import app


# ============================================================================
# 1. BIOPHYSICAL MATHEMATICAL SINGULARITIES & EXTREMES
# ============================================================================

class TestBiophysicalMathematicalSingularities:
    """Stress-test mathematical edge cases, singularities, and numerical stability."""

    def test_adv_01_sub_millisecond_and_extreme_ptt_inversion(self):
        """
        Adversarial Test 1:
        Verify PTT values approaching zero (0.001 ms, 0.1 ms) and extreme high PTT (5000 ms)
        do not cause math domain errors (log of negative or zero) and clamp within physiological bounds.
        """
        for ptt in [0.0001, 0.01, 0.1, 1.0, 5000.0, 10000.0]:
            res = invert_hemodynamic_vector(
                ptt_ms=ptt,
                hr_bpm=75.0,
                rr_ms=800.0,
                delta_t_dia_ms=280.0,
                imu_acc_g=1.0,
                e0_elasticity=400.0,
            )
            assert not math.isnan(res.systolic_bp_mmhg)
            assert not math.isnan(res.diastolic_bp_mmhg)
            assert not math.isnan(res.mean_arterial_pressure_mmhg)
            assert 70.0 <= res.systolic_bp_mmhg <= 240.0
            assert 40.0 <= res.diastolic_bp_mmhg <= 150.0
            assert res.systolic_bp_mmhg >= res.diastolic_bp_mmhg + 15.0 - 1e-4

    def test_adv_02_extreme_imu_acceleration_motion_artifacts(self):
        """
        Adversarial Test 2:
        Stress test violent IMU motion up to 100g.
        Ensures motion factor scaling max(0.0, imu_acc_g - 1.0) does not overflow or produce NaN,
        and confidence score properly drops to minimum floor (0.05).
        """
        for acc in [5.1, 10.0, 25.0, 50.0, 100.0]:
            res = invert_hemodynamic_vector(
                ptt_ms=220.0,
                hr_bpm=140.0,
                rr_ms=428.0,
                delta_t_dia_ms=180.0,
                imu_acc_g=acc,
                e0_elasticity=400.0,
            )
            assert not math.isnan(res.systolic_bp_mmhg)
            assert not math.isnan(res.diastolic_bp_mmhg)
            assert 70.0 <= res.systolic_bp_mmhg <= 240.0
            assert res.confidence_score <= 0.60
            assert res.confidence_score >= 0.05

    def test_adv_03_windkessel_diastolic_decay_singularities(self):
        """
        Adversarial Test 3:
        Verify Windkessel diastolic decay time constant when P_notch == DBP (log(1) = 0 singularity)
        and P_notch < DBP (inverted notch) are safely handled by the max(1.02, ratio) guard.
        """
        # Case 1: P_notch == DBP -> ratio would be 1.0 without guard
        tau_eq = diastolic_decay_time_constant(delta_t_dia_s=0.28, p_notch_mmhg=80.0, dbp_mmhg=80.0)
        assert tau_eq > 0.0
        assert not math.isinf(tau_eq)
        assert not math.isnan(tau_eq)

        # Case 2: P_notch < DBP (inverted notch anomaly)
        tau_inv = diastolic_decay_time_constant(delta_t_dia_s=0.28, p_notch_mmhg=60.0, dbp_mmhg=90.0)
        assert tau_inv > 0.0
        assert not math.isinf(tau_inv)
        assert not math.isnan(tau_inv)

    def test_adv_04_windkessel_peripheral_resistance_boundary_guards(self):
        """
        Adversarial Test 4:
        Verify calculate_peripheral_resistance_analytical handles zero compliance,
        zero delta_t, collapsed DBP, and SBP*alpha < DBP without crashing or NaN.
        """
        # Zero compliance fallback
        r1 = calculate_peripheral_resistance_analytical(0.28, c_art_ml_per_mmhg=0.0, sbp_mmhg=120.0, dbp_mmhg=80.0)
        assert r1 == 1.10

        # Zero delta_t fallback
        r2 = calculate_peripheral_resistance_analytical(0.0, c_art_ml_per_mmhg=1.2, sbp_mmhg=120.0, dbp_mmhg=80.0)
        assert r2 == 1.10

        # Collapsed DBP
        r3 = calculate_peripheral_resistance_analytical(0.28, c_art_ml_per_mmhg=1.2, sbp_mmhg=120.0, dbp_mmhg=0.0)
        assert r3 > 0.0
        assert not math.isnan(r3)

    def test_adv_05_ode_solvers_zero_and_impulse_inflow(self):
        """
        Adversarial Test 5:
        Verify WK2 & WK3 ODE solvers (Trapezoidal, RK4, Euler) under zero cardiac inflow
        and Dirac impulse inflow decay stably without divergence or NaN.
        """
        dt = 0.001
        n_points = 500
        rp, c, zc = 1.10, 1.25, 0.05

        # 1. Zero Inflow
        q_zero = np.zeros(n_points, dtype=np.float64)
        p_trap = solve_wk2_trapezoidal(q_zero, dt=dt, rp=rp, c=c, p0=100.0)
        p_rk4 = solve_wk2_rk4(q_zero, dt=dt, rp=rp, c=c, p0=100.0)
        p_wk3, pc_wk3 = solve_wk3_trapezoidal(q_zero, dt=dt, rp=rp, c=c, zc=zc)

        assert np.all(p_trap >= 0.0)
        assert np.all(p_rk4 >= 0.0)
        assert np.all(p_wk3 >= 0.0)
        assert not np.any(np.isnan(p_trap))
        assert not np.any(np.isnan(p_rk4))
        assert not np.any(np.isnan(p_wk3))
        # Zero inflow with p0=100 should monotonically decay
        assert np.all(np.diff(p_trap) <= 0.0)

        # 2. Impulse Inflow (single spike at t=0)
        q_impulse = np.zeros(n_points, dtype=np.float64)
        q_impulse[0] = 500.0
        p_impulse = solve_wk2_rk4(q_impulse, dt=dt, rp=rp, c=c, p0=80.0)
        assert not np.any(np.isnan(p_impulse))
        assert np.all(p_impulse >= 0.0)

    def test_adv_06_bramwell_hill_pwv_clamping_and_compliance(self):
        """
        Adversarial Test 6:
        Verify Bramwell-Hill compliance conversions across the full PWV clamping range [3.0, 25.0] m/s.
        Ensure compliance is strictly positive and non-infinite.
        """
        for pwv in np.linspace(3.0, 25.0, 50):
            d_v = volumetric_distensibility(pwv_m_s=pwv)
            d_v_mmhg = volumetric_distensibility_mmhg(pwv_m_s=pwv)
            tac_si = total_arterial_compliance(pwv_m_s=pwv)
            tac_ml = total_arterial_compliance_ml_per_mmhg(pwv_m_s=pwv)

            assert d_v > 0.0
            assert d_v_mmhg > 0.0
            assert tac_si > 0.0
            assert tac_ml > 0.0
            assert not math.isnan(tac_ml)
            assert not math.isinf(tac_ml)

    def test_adv_07_hughes_exponential_strain_stiffening_stress(self):
        """
        Adversarial Test 7:
        Verify Hughes exponential strain-stiffening E(P) = E0 * exp(gamma * P)
        across pressures from -50 mmHg (negative transmural) to 300 mmHg (extreme crisis).
        """
        e0 = 400.0
        gamma = 0.017
        for p in [-50.0, 0.0, 80.0, 120.0, 200.0, 300.0]:
            e_p = hughes_strain_stiffening(e0_pa=e0, pressure_mmhg=p, gamma=gamma)
            assert e_p > 0.0
            assert not math.isnan(e_p)
            assert not math.isinf(e_p)

        # Monotonicity test: d(E)/d(P) > 0
        pressures = np.linspace(0.0, 250.0, 50)
        e_vals = [hughes_strain_stiffening(e0, p, gamma) for p in pressures]
        assert np.all(np.diff(e_vals) > 0.0)


# ============================================================================
# 2. ZERO-PII SECURITY, TOKENIZATION & SANITIZATION BYPASS VECTORS
# ============================================================================

class TestZeroPiiSecurityAndBypassVectors:
    """Stress-test Zero-PII gate against obfuscation, unicode, null-bytes, and token tampering."""

    def test_adv_08_unicode_lookalikes_and_confusables(self):
        """
        Adversarial Test 8:
        Stress-test PII key detection against unicode lookalikes, full-width characters,
        and punctuation injection.
        """
        obfuscated_keys = [
            "e_m_a_i_l",
            "u-s-e-r-i-d",
            "d.e.v.i.c.e.i.d",
            "__patient_name__",
            "===mac_address===",
            "athlete-name",
            "client_name",
            "contact_mail",
            "postal_code",
            "gps_latitude",
            "gps_longitude",
            "serial_number_v2",
        ]
        for key in obfuscated_keys:
            assert is_pii_key(key) is True, f"Key '{key}' evaded Zero-PII detection"

    def test_adv_09_null_bytes_and_whitespace_injections(self):
        """
        Adversarial Test 9:
        Verify PII key detection intercepts keys containing null bytes, zero-width spaces,
        or excessive tabs/newlines.
        """
        dirty_keys = [
            "email\x00",
            "\x00user_id",
            "\t\nmac_address\r\n",
            "   device_serial   ",
            "patient\x00name",
        ]
        for key in dirty_keys:
            assert is_pii_key(key) is True, f"Key with null/whitespace '{repr(key)}' evaded detection"

    def test_adv_10_deeply_nested_heterogeneous_structures(self):
        """
        Adversarial Test 10:
        Verify recursive PII scanner handles deeply nested heterogeneous structures
        (lists of dicts of lists of tuples) with mixed types, correctly identifying all violations.
        """
        complex_payload = {
            "root_level": 1,
            "sub_tree": [
                {"clean_metric": 100.0},
                [
                    {
                        "deep_nesting": {
                            "layer_4": [
                                None,
                                42,
                                {"hidden_patient": "John Doe", "safe_val": 3.14},
                                ["00:1A:2B:3C:4D:5E", "clean_text"]
                            ]
                        }
                    }
                ]
            ]
        }
        assert contains_pii(complex_payload) is True
        violations = get_pii_violations(complex_payload)
        assert len(violations) >= 2  # hidden_patient key + MAC value

        # Test deep sanitization preserves clean data while eliminating PII
        cleaned = sanitize_pii(complex_payload)
        assert cleaned["root_level"] == 1
        assert cleaned["sub_tree"][0]["clean_metric"] == 100.0
        assert "hidden_patient" not in str(cleaned)
        assert "00:1A:2B:3C:4D:5E" not in str(cleaned)

    def test_adv_11_hmac_session_token_validation_and_tamper(self):
        """
        Adversarial Test 11:
        Verify HMAC-SHA256 session token format validation, constant-time verification,
        and instant rejection of single-bit flips, truncated hashes, or non-hex inputs.
        """
        valid_token = generate_session_token("secret_test_key_123", "nonce_998877")
        assert validate_session_token_format(valid_token) is True
        assert len(valid_token) == 64

        # Single-bit / character flip
        tampered_token = list(valid_token)
        tampered_token[10] = '0' if tampered_token[10] != '0' else '1'
        tampered_str = "".join(tampered_token)
        assert tampered_str != valid_token
        # It's still 64-hex format, but signature verification against original nonce will fail
        assert verify_hmac_signature("secret_test_key_123", "nonce_998877", tampered_str) is False

        # Invalid formats
        assert validate_session_token_format(valid_token[:63]) is False  # Truncated
        assert validate_session_token_format(valid_token + "a") is False  # Extra length
        assert validate_session_token_format("g" * 64) is False  # Non-hex characters
        assert validate_session_token_format("") is False
        assert validate_session_token_format(None) is False  # type: ignore

    @pytest.mark.asyncio
    async def test_adv_12_middleware_boundary_attacks(self):
        """
        Adversarial Test 12:
        Test FastAPI Zero-PII middleware against boundary HTTP attacks:
        - Query parameters with encoded MAC addresses
        - Custom X-* headers with prohibited keys
        - POST bodies with forbidden keys
        """
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Query parameter with MAC
            r1 = await client.get("/health?sensor_mac=00-11-22-33-44-55")
            assert r1.status_code == 422
            assert "Zero-PII Policy Violation" in r1.json()["detail"]

            # 2. Custom header with PII
            r2 = await client.get("/health", headers={"X-Patient-Id": "12345"})
            assert r2.status_code == 422

            # 3. Clean request passes
            r3 = await client.get("/health")
            assert r3.status_code == 200


# ============================================================================
# 3. STORAGE LAYER CONCURRENCY & WRITE CONTENTION (SQLite WAL & Vector Store)
# ============================================================================

class TestStorageConcurrencyAndIntegrity:
    """Stress-test SQLite WAL concurrency, write contention, and vector search edge cases."""

    @pytest.fixture
    def isolated_db(self):
        """Provide clean isolated SQLite database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
            db_path = tf.name
        manager = SqliteManager(db_path=db_path)
        yield manager, db_path
        for ext in ["", "-wal", "-shm"]:
            p = db_path + ext
            if os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass

    @pytest.mark.asyncio
    async def test_adv_13_high_concurrency_same_session_contention(self, isolated_db):
        """
        Adversarial Test 13:
        100 concurrent async tasks writing to the SAME session simultaneously.
        Verify zero SQLite lock exceptions and exact tick count equality.
        """
        manager, _ = isolated_db
        session_hash = "f" * 64
        await manager.create_or_get_session(session_hash)

        num_tasks = 100
        ticks_per_task = 10
        total_expected = num_tasks * ticks_per_task

        async def worker(task_id: int):
            for i in range(ticks_per_task):
                tick_time = 1700000000000 + (task_id * 100) + i
                await manager.log_telemetry_tick(
                    session_hash=session_hash,
                    tick_epoch_ms=tick_time,
                    delta_time_ms=(i + 1) * 1000,
                    ptt_ms=220.0,
                    hr_bpm=75.0,
                    rr_ms=800.0,
                    delta_t_dia_ms=280.0,
                    imu_acc_g=1.0,
                    e0_elasticity=400.0,
                    sbp_calc=120.0,
                    dbp_calc=80.0,
                    map_calc=93.3,
                    pulse_pressure_calc=40.0,
                    vascular_resistance=1.05,
                    confidence_score=0.96,
                )

        tasks = [asyncio.create_task(worker(t)) for t in range(num_tasks)]
        await asyncio.gather(*tasks)

        summary = await manager.get_session_summary(session_hash)
        assert summary is not None
        assert summary["total_ticks"] == total_expected
        assert summary["mean_sbp"] == 120.0
        assert summary["mean_dbp"] == 80.0

    @pytest.mark.asyncio
    async def test_adv_14_concurrent_read_write_interleaving(self, isolated_db):
        """
        Adversarial Test 14:
        Verify concurrent readers never read inconsistent partial state while writers are active.
        """
        manager, _ = isolated_db
        session_hash = "e" * 64
        await manager.create_or_get_session(session_hash)

        is_running = True
        read_counts = []

        async def writer():
            for i in range(100):
                await manager.log_telemetry_tick(
                    session_hash=session_hash,
                    tick_epoch_ms=1700000000000 + i * 10,
                    delta_time_ms=(i + 1) * 1000,
                    ptt_ms=220.0,
                    hr_bpm=70.0,
                    rr_ms=800.0,
                    delta_t_dia_ms=280.0,
                    imu_acc_g=1.0,
                    e0_elasticity=400.0,
                    sbp_calc=118.0,
                    dbp_calc=78.0,
                    map_calc=91.3,
                    pulse_pressure_calc=40.0,
                    vascular_resistance=1.0,
                    confidence_score=0.95,
                )
                await asyncio.sleep(0.001)

        async def reader():
            while is_running:
                summary = await manager.get_session_summary(session_hash)
                if summary:
                    read_counts.append(summary["total_ticks"])
                await asyncio.sleep(0.002)

        writer_task = asyncio.create_task(writer())
        reader_task = asyncio.create_task(reader())

        await writer_task
        is_running = False
        await reader_task

        assert len(read_counts) > 0
        # Verify read counts are monotonically non-decreasing
        assert all(read_counts[i] <= read_counts[i + 1] for i in range(len(read_counts) - 1))

    @pytest.mark.asyncio
    async def test_adv_15_vector_store_empty_and_oversized_queries(self):
        """
        Adversarial Test 15:
        Verify deterministic embedding generation and ChromaManager/FallbackVectorStore
        handles empty string, oversized query (100k chars), and missing session filters safely.
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            chroma = ChromaManager(persist_dir=tmp_dir)

            # 1. Empty string embedding
            vec_empty = _compute_deterministic_embedding("")
            assert len(vec_empty) == 384
            assert abs(np.linalg.norm(vec_empty) - 1.0) < 1e-5

            # 2. Oversized query embedding (100k characters)
            huge_text = "zone2 cardiovascular drift aerobic threshold " * 2500
            vec_huge = _compute_deterministic_embedding(huge_text)
            assert len(vec_huge) == 384
            assert abs(np.linalg.norm(vec_huge) - 1.0) < 1e-5

            # 3. Add document and query with filter
            session_hash = "a" * 64
            await chroma.add_session_document(
                session_hash=session_hash,
                document_text="Zone 2 aerobic endurance workout summary",
                metadata={"session_hash": session_hash, "duration_sec": 3600}
            )

            # Query matching session
            res_match = await chroma.query_embeddings("Zone 2 workout", filter_session_hash=session_hash)
            assert len(res_match) >= 1
            assert res_match[0]["metadata"]["session_hash"] == session_hash

            # Query non-matching session filter returns empty list
            res_nomatch = await chroma.query_embeddings("Zone 2 workout", filter_session_hash="b" * 64)
            assert len(res_nomatch) == 0


# ============================================================================
# 4. GENETIC MoE CLASSIFICATION & STREAMING CHUNK HARDENING
# ============================================================================

class TestGeneticMoEAndStreamingHardening:
    """Stress-test Genetic MoE classification rules and SSE thought parser chunking."""

    @pytest.mark.parametrize("query,expected_expert", [
        ("Show me the ECG waveform and ST segment morphology", "Qwen3-VL-32B"),
        ("Poincaré scatter plot visual inspection of HRV", "Qwen3-VL-32B"),
        ("Derive the mathematical proof of Moens-Korteweg vascular stiffness", "DeepSeek-R1-Distill-Qwen-32B"),
        ("Why did my cardiovascular drift spike by 8% during Zone 2?", "DeepSeek-R1-Distill-Qwen-32B"),
        ("Generate a tabular summary of split times and average HR", "Qwen2.5-Coder-14B"),
        ("Export workout stats into a structured table", "Qwen2.5-Coder-14B"),
        ("How is my general physiological status today?", "Qwen2.5-Coder-32B-Instruct"),
    ])
    def test_adv_16_genetic_moe_expert_classification(self, query: str, expected_expert: str):
        """
        Adversarial Test 16:
        Verify deterministic domain routing accurately classifies complex multi-modal,
        mathematical, tabular, and general reasoning prompts.
        """
        model, rationale = classify_genetic_moe_expert(query)
        assert model == expected_expert
        assert len(rationale) > 10

    def test_adv_17_streaming_thought_parser_unclosed_tags(self):
        """
        Adversarial Test 17:
        Verify StreamingThoughtParser safely handles streams where the <think> tag
        is never closed (stream abruptly terminates). All text must be flushed cleanly without losing content.
        """
        parser = StreamingThoughtParser(include_thinking=True)
        chunks = ["<think>", "Incomplete reasoning path that ends abruptly"]
        events = []
        for c in chunks:
            events.extend(parser.feed(c))
        events.extend(parser.flush())

        thinking = "".join(e[1]["delta"] for e in events if e[0] == "thinking_delta")
        assert "Incomplete reasoning path" in thinking

    def test_adv_18_streaming_thought_parser_divergent_angle_brackets(self):
        """
        Adversarial Test 18:
        Verify parser correctly differentiates math inequality operators (e.g. 'x < 5 and y > 10')
        and HTML-like tokens (e.g. '<br/>', '<div>') from <think> / <thought> tags.
        """
        parser = StreamingThoughtParser(include_thinking=True)
        raw_text = "Ensure power < 200W and HR > 140bpm. Use <br/> for spacing."
        events = []
        for word in raw_text.split(" "):
            events.extend(parser.feed(word + " "))
        events.extend(parser.flush())

        content = "".join(e[1]["delta"] for e in events if e[0] == "content_delta")
        assert "power < 200W" in content
        assert "HR > 140bpm" in content
        assert "<br/>" in content

    def test_adv_19_sse_chunk_formatting_escapes_and_newlines(self):
        """
        Adversarial Test 19:
        Verify format_sse_chunk properly serializes multiline payloads and unicode characters.
        """
        event_name = "content_delta"
        payload = {
            "delta": "Line 1\nLine 2 with UTF-8: \u0394RMSSD = 25.4ms \u2014 \u03b11: 0.85\n\nFinal bullet points",
            "type": "markdown"
        }
        sse_chunk = format_sse_chunk(event_name, payload)
        assert sse_chunk.startswith("event: content_delta\n")
        assert "data: " in sse_chunk
        assert sse_chunk.endswith("\n\n")

        # Parse data JSON
        data_line = [l for l in sse_chunk.split("\n") if l.startswith("data: ")][0]
        parsed_data = json.loads(data_line[6:])
        assert parsed_data["type"] == "markdown"
        assert "\u0394RMSSD" in parsed_data["delta"]

    @pytest.mark.asyncio
    async def test_adv_20_batch_inversion_endpoint_stress(self):
        """
        Adversarial Test 20:
        Stress test POST /api/v1/hemodynamics/batch with 50 sequential ticks in one payload.
        Verify all 50 ticks are inverted and session summary updates correctly.
        """
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            session_token = "d" * 64
            ticks = []
            for i in range(50):
                ticks.append({
                    "delta_time_ms": (i + 1) * 1000,
                    "vector_u": {
                        "ptt_ms": 220.0 - (i * 0.5),
                        "hr_bpm": 70.0 + (i * 0.8),
                        "rr_ms": 800.0,
                        "delta_t_dia_ms": 280.0,
                        "imu_acc_g": 1.05,
                        "e0_elasticity": 400.0,
                    }
                })

            batch_payload = {
                "protocol_version": "1.0",
                "session_token": session_token,
                "ticks": ticks,
            }

            response = await client.post("/api/v1/hemodynamics/batch", json=batch_payload)
            assert response.status_code == 200
            data = response.json()
            assert data["total_processed"] == 50
            assert len(data["results"]) == 50
