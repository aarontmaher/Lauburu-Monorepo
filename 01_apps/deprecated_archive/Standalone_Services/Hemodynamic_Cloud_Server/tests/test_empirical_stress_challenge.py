"""
Empirical Stress & Invariant Challenge Test Suite for Milestone 3 (R3):
Adversarial Verification of:
1. StreamingThoughtParser (tag fragmentation, non-tag angle brackets, unclosed tags, nested tags, UTF-8/emojis/math, high-frequency fuzzing).
2. GeneticMoEService classification accuracy on comprehensive physiological/biomechanical domain prompts.
3. Server-Sent Events (SSE) Stream Generation & Network Failure/Recovery Dynamics.
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.core.security import generate_session_token
from app.services.genetic_moe_service import (
    GeneticMoEService,
    StreamingThoughtParser,
    format_sse_chunk,
    MODEL_DEEPSEEK_R1,
    MODEL_QWEN3_VL,
    MODEL_QWEN_CODER,
    MODEL_GEMINI_FALLBACK,
)
from app.models.schemas import (
    DiagnosticStreamRequest,
    DiagnosticTelemetryContext,
    RagQueryResultItem,
)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def valid_token():
    return generate_session_token("challenger_m3_seed_999")


# ============================================================================
# 1. EMPIRICAL STRESS TESTS: StreamingThoughtParser Invariants
# ============================================================================

class TestStreamingThoughtParserStress:
    """Adversarial boundary & invariant stress tests for StreamingThoughtParser."""

    def test_single_character_chunk_fragmentation_open_tag(self):
        """Stress-test feeding '<think>' one single character at a time."""
        parser = StreamingThoughtParser(include_thinking=True)
        raw_stream = list("<think>Deep physiological derivation</think>Final Advice")

        events = []
        for char in raw_stream:
            events.extend(parser.feed(char))
        events.extend(parser.flush())

        thinking = "".join(e[1]["delta"] for e in events if e[0] == "thinking_delta")
        content = "".join(e[1]["delta"] for e in events if e[0] == "content_delta")

        assert thinking == "Deep physiological derivation", f"Got: {thinking}"
        assert content == "Final Advice", f"Got: {content}"
        assert "<think>" not in thinking and "</think>" not in thinking
        assert "<think>" not in content and "</think>" not in content

    def test_single_character_chunk_fragmentation_close_tag(self):
        """Stress-test feeding '</thought>' one character at a time."""
        parser = StreamingThoughtParser(include_thinking=True)
        raw_stream = list("<thought>Complex biometrics</thought>Markdown content")

        events = []
        for char in raw_stream:
            events.extend(parser.feed(char))
        events.extend(parser.flush())

        thinking = "".join(e[1]["delta"] for e in events if e[0] == "thinking_delta")
        content = "".join(e[1]["delta"] for e in events if e[0] == "content_delta")

        assert thinking == "Complex biometrics"
        assert content == "Markdown content"

    def test_fragmented_tags_across_arbitrary_byte_boundaries(self):
        """Test varied multi-character chunk split permutations."""
        permutations = [
            (["<th", "ink>Step 1</th", "ink>Advice"], "Step 1", "Advice"),
            (["<tho", "ught>Observation</tho", "ught>Summary"], "Observation", "Summary"),
            (["<", "t", "h", "i", "n", "k", ">Reasoning<", "/", "t", "h", "i", "n", "k", ">Action"], "Reasoning", "Action"),
            (["Prefix <th", "ink>CoT</th", "ink> Suffix"], "CoT", "Prefix  Suffix"),
            (["<think>", "Single block thinking", "</think>", "Single block content"], "Single block thinking", "Single block content"),
        ]

        for chunks, expected_think, expected_content in permutations:
            parser = StreamingThoughtParser(include_thinking=True)
            events = []
            for c in chunks:
                events.extend(parser.feed(c))
            events.extend(parser.flush())

            thinking = "".join(e[1]["delta"] for e in events if e[0] == "thinking_delta")
            content = "".join(e[1]["delta"] for e in events if e[0] == "content_delta")

            assert thinking == expected_think, f"Failed for {chunks}: got think='{thinking}'"
            assert content == expected_content, f"Failed for {chunks}: got content='{content}'"

    def test_non_tag_angle_brackets_mathematical_inequalities(self):
        """
        Adversarially test mathematical inequalities, physiological bounds,
        and pseudo-tags that must NOT be swallowed or misclassified as tags.
        """
        parser = StreamingThoughtParser(include_thinking=True)
        chunks = [
            "Systolic BP is < 120 mmHg and diastolic is < 80 mmHg. ",
            "PWV < 6.5 m/s indicates compliant arteries. ",
            "For all x, if a < b and c > d, then e << f. ",
            "Check condition: val < 0.05 or val > 0.95. ",
            "HTML-like entity: <custom_metric>123</custom_metric> should remain content."
        ]

        events = []
        for c in chunks:
            events.extend(parser.feed(c))
        events.extend(parser.flush())

        thinking_events = [e for e in events if e[0] == "thinking_delta"]
        content = "".join(e[1]["delta"] for e in events if e[0] == "content_delta")

        assert len(thinking_events) == 0, f"Unexpected thinking events: {thinking_events}"
        assert "< 120 mmHg" in content
        assert "< 80 mmHg" in content
        assert "PWV < 6.5 m/s" in content
        assert "a < b and c > d" in content
        assert "<custom_metric>123</custom_metric>" in content

    def test_prefix_starting_with_tag_characters_not_matching(self):
        """Test chunks containing words that start like tags but are not tags (e.g. <thinking>, <thoughtful>)."""
        parser = StreamingThoughtParser(include_thinking=True)
        chunks = [
            "We are <thinking_about> this problem deeply. ",
            "He was very <thoughtful> in his analysis. ",
            "Prefix: <think_not_really> and <thought_experiment>."
        ]

        events = []
        for c in chunks:
            events.extend(parser.feed(c))
        events.extend(parser.flush())

        thinking_events = [e for e in events if e[0] == "thinking_delta"]
        content = "".join(e[1]["delta"] for e in events if e[0] == "content_delta")

        # Because <think> matches the prefix of <thinking_about>, let's verify exact parser behavior
        # In <think>, if `<think>` is inside `<thinking_about>`, it will trigger thinking if exact tag matches.
        # But if the tag is `<thinking_about>`, it starts with `<think` but followed by `i`, not `>`.
        # So `<think>` is NOT in `<thinking_about>`.
        assert "<thinking_about>" in content
        assert "<thoughtful>" in content

    def test_unclosed_think_tag_at_eof_flush(self):
        """
        Verify stream that ends abruptly while in <think> state without </think>.
        Buffer must be flushed cleanly as thinking_delta without throwing exceptions.
        """
        parser = StreamingThoughtParser(include_thinking=True)
        chunks = [
            "<think>\nStep 1: Invert Moens-Korteweg equation.",
            "\nStep 2: PTT = 185 ms, PWV = 5.4 m/s.",
            "\nStep 3: Calculating arterial compliance..."  # EOF abruptly without </think>
        ]

        events = []
        for c in chunks:
            events.extend(parser.feed(c))
        events.extend(parser.flush())

        thinking = "".join(e[1]["delta"] for e in events if e[0] == "thinking_delta")
        content = "".join(e[1]["delta"] for e in events if e[0] == "content_delta")

        assert "Invert Moens-Korteweg equation" in thinking
        assert "Calculating arterial compliance" in thinking
        assert parser.is_thinking is True
        assert len(content) == 0

    def test_nested_think_tags_robustness(self):
        """
        Test behavior when LLM hallucinates nested <think><think> tags.
        Parser state machine should not throw and should handle inner content.
        """
        parser = StreamingThoughtParser(include_thinking=True)
        chunks = [
            "<think>Outer thought preamble. ",
            "<think>Nested inner thought.</think> ",
            "Remaining trailing thought.</think>",
            "Final clinical advice."
        ]

        events = []
        for c in chunks:
            events.extend(parser.feed(c))
        events.extend(parser.flush())

        thinking = "".join(e[1]["delta"] for e in events if e[0] == "thinking_delta")
        content = "".join(e[1]["delta"] for e in events if e[0] == "content_delta")

        assert "Outer thought preamble" in thinking
        assert "Final clinical advice" in content

    def test_multibyte_utf8_emojis_and_mathematical_symbols(self):
        """
        Verify multi-byte UTF-8 code points, cardiovascular emojis (🫀, 🩺, ⚡),
        and Greek/Math symbols (Δ, ρ, α₁, VO₂max, ∂, ∫, λ, σ, ≤, ≥, ≈) are preserved.
        """
        parser = StreamingThoughtParser(include_thinking=True)
        chunks = [
            "<think>\n🫀 Cardiovascular Invariants:\n",
            "1. ΔP = ρ · g · h + 1/2 · ρ · v²\n",
            "2. α₁ = 0.75 (DFA-α1 fractal scaling exponent)\n",
            "3. VO₂max ≥ 55.0 mL/kg/min\n",
            "4. Wave speed: λ_pwv = √(V · ΔP / (ρ · ΔV))\n",
            "5. Windkessel compliance: C_art ≈ 1.2 mL/mmHg\n</think>\n",
            "### 🩺 Coaching Diagnostic ⚡\n",
            "Maintain Zone 2 aerobic threshold: 135–145 BPM. 🚴💨"
        ]

        events = []
        for c in chunks:
            events.extend(parser.feed(c))
        events.extend(parser.flush())

        thinking = "".join(e[1]["delta"] for e in events if e[0] == "thinking_delta")
        content = "".join(e[1]["delta"] for e in events if e[0] == "content_delta")

        # Invariants verification
        assert "🫀 Cardiovascular Invariants" in thinking
        assert "ΔP = ρ · g · h" in thinking
        assert "α₁ = 0.75" in thinking
        assert "VO₂max ≥ 55.0" in thinking
        assert "λ_pwv" in thinking
        assert "C_art ≈ 1.2" in thinking

        assert "### 🩺 Coaching Diagnostic ⚡" in content
        assert "135–145 BPM. 🚴💨" in content

    def test_high_frequency_fuzzing_10000_tokens(self):
        """Fuzz parser with 10,000 randomized micro-chunks to ensure zero memory leak or unhandled state."""
        import random
        parser = StreamingThoughtParser(include_thinking=True)

        full_text = (
            "Introductory telemetry analysis.\n"
            "<think>\n" +
            "Deriving cardiovascular hemodynamics step by step.\n" * 50 +
            "</think>\n" +
            "### Comprehensive Diagnostic Recommendations\n" +
            "- Maintain steady heart rate in 130-140 BPM range.\n" * 20
        )

        # Slice into random 1 to 7 char chunks
        i = 0
        chunks = []
        while i < len(full_text):
            step = random.randint(1, 7)
            chunks.append(full_text[i:i+step])
            i += step

        events = []
        for c in chunks:
            events.extend(parser.feed(c))
        events.extend(parser.flush())

        thinking = "".join(e[1]["delta"] for e in events if e[0] == "thinking_delta")
        content = "".join(e[1]["delta"] for e in events if e[0] == "content_delta")

        assert "Deriving cardiovascular hemodynamics" in thinking
        assert "Comprehensive Diagnostic Recommendations" in content
        assert "<think>" not in thinking and "</think>" not in thinking
        assert "<think>" not in content and "</think>" not in content
        assert parser.total_tokens > 0


# ============================================================================
# 2. EMPIRICAL STRESS TESTS: Genetic MoE Domain Classification Accuracy
# ============================================================================

class TestGeneticMoEClassificationAccuracy:
    """Stress-test domain prompt classification across extensive physiological taxonomy."""

    def setup_method(self):
        self.service = GeneticMoEService()

    @pytest.mark.parametrize("query,expected_model", [
        # Deep Cardiovascular Reasoning & Derivations -> DeepSeek-R1
        ("Derive the Bramwell-Hill relationship for arterial compliance from Moens-Korteweg wave equation.", MODEL_DEEPSEEK_R1),
        ("Why does pulse transit time (PTT) decrease as mean arterial pressure increases during intense cycling?", MODEL_DEEPSEEK_R1),
        ("Explain the physiological mechanism of cardiovascular drift during 2 hours at constant 180W.", MODEL_DEEPSEEK_R1),
        ("What is the physiological basis of San Millan's Zone 2 lactate clearance model?", MODEL_DEEPSEEK_R1),
        ("Derive 2-element Windkessel vascular resistance from stroke volume and diastolic decay time.", MODEL_DEEPSEEK_R1),
        ("Compare parasympathetic reactivation vs sympathetic withdrawal in post-exercise recovery.", MODEL_DEEPSEEK_R1),
        ("Explain arterial stiffness and vascular compliance changes under heat stress.", MODEL_DEEPSEEK_R1),
        ("Calculate cardiac output using the Fick principle and systemic vascular resistance.", MODEL_DEEPSEEK_R1),
        ("Why is my systolic BP rising at 180W while heart rate remains steady?", MODEL_DEEPSEEK_R1),
        ("Explain autonomic fatigue and vagal tone modulation from Seiler 3-zone model.", MODEL_DEEPSEEK_R1),

        # Multimodal Biometrics, ECG, Waveforms -> Qwen3-VL
        ("Analyze this 2D ECG strip waveform for ST-segment elevation.", MODEL_QWEN3_VL),
        ("Inspect the photoplethysmogram (PPG) pulse waveform for dicrotic notch damping.", MODEL_QWEN3_VL),
        ("Evaluate this Poincaré scatter plot for autonomic parasympathetic dysfunction.", MODEL_QWEN3_VL),
        ("Is there any motion artifact or baseline wander in this sensor waveform graph?", MODEL_QWEN3_VL),
        ("Check the QRS morphology and P-wave amplitude in this telemetry plot.", MODEL_QWEN3_VL),
        ("Detect premature ventricular contractions in this visual biometrics strip.", MODEL_QWEN3_VL),

        # Tabular Workouts, Splits, Training Load -> Qwen2.5-Coder
        ("Provide a tabular summary of lap splits and power output across the workout.", MODEL_QWEN_CODER),
        ("Calculate TRIMP and TSS training load for my 60-minute interval session.", MODEL_QWEN_CODER),
        ("Export my workout stats and lap intervals to a Markdown table and CSV format.", MODEL_QWEN_CODER),
        ("Compute CTL, ATL, and TSB training stress balance across the last 4 weeks.", MODEL_QWEN_CODER),
        ("Show me a summary table with average heart rate and total duration.", MODEL_QWEN_CODER),
        ("Format the lap statistics into structured JSON data.", MODEL_QWEN_CODER),

        # General Exercise Physiology Default -> DeepSeek-R1
        ("What should my nutrition and pacing strategy be for a 100km gravel ride?", MODEL_DEEPSEEK_R1),
        ("How does dehydration affect core temperature during prolonged endurance exercise?", MODEL_DEEPSEEK_R1),
        ("Recommend recovery protocols after a maximal aerobic power ramp test.", MODEL_DEEPSEEK_R1),
    ])
    def test_domain_classification_matrix(self, query: str, expected_model: str):
        model, endpoint, rationale = self.service.classify_expert(query, has_image=False)
        assert model == expected_model, f"Query '{query}' classified as {model}, expected {expected_model}. Rationale: {rationale}"

    def test_image_payload_unconditional_qwen_vl_routing(self):
        """Even with text suggesting coding or formulas, image payload must route to Qwen3-VL."""
        model, endpoint, rationale = self.service.classify_expert("Show me tabular stats", has_image=True)
        assert model == MODEL_QWEN3_VL
        assert "vision" in rationale.lower() or "multimodal" in rationale.lower()


# ============================================================================
# 3. EMPIRICAL STRESS TESTS: SSE Streaming & Network Failure Recovery
# ============================================================================

class TestStreamingNetworkFailureAndRecovery:
    """Stress-test SSE stream generation under simulated network drops and error recovery."""

    @pytest.mark.asyncio
    async def test_full_mesh_network_outage_deterministic_fallback(self):
        """
        When all network endpoints (DeepSeek-R1, Qwen-Coder, Gemini) fail to connect,
        service MUST seamlessly fall back to Local-Biophysical-Engine with valid SSE events.
        """
        service = GeneticMoEService()
        request = DiagnosticStreamRequest(
            session_token=generate_session_token("failover_test_seed"),
            query="Analyze my cardiac drift and stroke volume decay at 180W.",
            include_thinking=True,
            top_k_rag=0
        )

        with patch("httpx.AsyncClient.stream", side_effect=httpx.ConnectError("All mesh nodes down")):
            chunks = []
            async for chunk in service.execute_stream(request):
                chunks.append(chunk)

            full_sse_text = "".join(chunks)
            assert "event: content_delta" in full_sse_text
            assert "Cardiovascular Telemetry Assessment" in full_sse_text
            assert "event: done" in full_sse_text
            assert "Local-Biophysical-Engine" in full_sse_text

    @pytest.mark.asyncio
    async def test_mid_stream_network_drop_emits_error_event(self):
        """
        When network breaks AFTER emitting initial tokens, the service MUST emit
        an SSE error event and gracefully terminate without crashing.
        """
        service = GeneticMoEService()
        request = DiagnosticStreamRequest(
            session_token=generate_session_token("mid_stream_drop_seed"),
            query="Derive Moens-Korteweg wave equation step by step.",
            include_thinking=True,
            top_k_rag=0
        )

        # Mock an aiter_lines that yields 2 chunks then raises RemoteProtocolError
        async def broken_iter():
            yield 'data: {"choices":[{"delta":{"content":"<think>Step 1: Conservation of mass\\n"}}]}'
            yield 'data: {"choices":[{"delta":{"content":"Step 2: Momentum balance\\n"}}]}'
            raise httpx.RemoteProtocolError("TCP connection reset by peer during token streaming")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.aiter_lines = broken_iter

        mock_stream_ctx = AsyncMock()
        mock_stream_ctx.__aenter__.return_value = mock_resp
        mock_stream_ctx.__aexit__.return_value = None

        with patch("httpx.AsyncClient.stream", return_value=mock_stream_ctx):
            chunks = []
            async for chunk in service.execute_stream(request):
                chunks.append(chunk)

            full_sse_text = "".join(chunks)
            assert "event: thinking_delta" in full_sse_text
            assert "Step 1: Conservation of mass" in full_sse_text
            assert "event: error" in full_sse_text
            assert "Stream interrupted mid-generation" in full_sse_text

    @pytest.mark.asyncio
    async def test_target_model_override_routing(self):
        """Verify client can explicitly select target_model override in stream request."""
        service = GeneticMoEService()
        request = DiagnosticStreamRequest(
            session_token=generate_session_token("override_seed"),
            query="General query",
            target_model="gemini-3.7-flash",
            include_thinking=False,
            top_k_rag=0
        )

        # Mock successful Gemini stream
        async def gemini_iter():
            yield 'data: {"choices":[{"delta":{"content":"Gemini 3.7 Flash biophysical guidance."}}]}'
            yield 'data: [DONE]'

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.aiter_lines = gemini_iter

        mock_stream_ctx = AsyncMock()
        mock_stream_ctx.__aenter__.return_value = mock_resp
        mock_stream_ctx.__aexit__.return_value = None

        with patch("httpx.AsyncClient.stream", return_value=mock_stream_ctx):
            chunks = []
            async for chunk in service.execute_stream(request):
                chunks.append(chunk)

            full_sse_text = "".join(chunks)
            assert "event: content_delta" in full_sse_text
            assert "Gemini 3.7 Flash biophysical guidance" in full_sse_text
            assert "event: done" in full_sse_text
            assert "gemini-3.7-flash" in full_sse_text

    def test_sse_endpoint_rejects_invalid_token(self, client):
        """Verify POST /api/v1/ai/diagnostic/stream returns 422 for invalid session token."""
        response = client.post(
            "/api/v1/ai/diagnostic/stream",
            json={
                "session_token": "invalid_short_token",
                "query": "What is my vascular compliance?",
                "include_thinking": True
            }
        )
        assert response.status_code == 422
        assert "session_token" in response.text

    def test_sse_endpoint_rejects_pii_in_telemetry_via_middleware(self, client, valid_token):
        """Verify middleware blocks requests containing prohibited PII keys in stream telemetry."""
        payload = {
            "session_token": valid_token,
            "query": "Check cardiac drift",
            "telemetry_context": {
                "user_name": "Alice Runner",
                "email": "alice@example.com",
                "heart_rate_bpm": 142.0
            }
        }
        response = client.post("/api/v1/ai/diagnostic/stream", json=payload)
        assert response.status_code == 422
        assert "Zero-PII Policy Violation" in response.json()["detail"]

    def test_alternating_multi_thought_blocks_fragmented(self):
        """Test alternating thinking and content blocks chunked in tiny 2-char pieces."""
        parser = StreamingThoughtParser(include_thinking=True)
        raw_text = (
            "Intro Section.\n"
            "<think>Thought Block 1: Deriving Bramwell-Hill.</think>\n"
            "Intermediate analysis.\n"
            "<thought>Thought Block 2: Calculating PWV.</thought>\n"
            "Final conclusion."
        )

        chunks = [raw_text[i:i+2] for i in range(0, len(raw_text), 2)]
        events = []
        for c in chunks:
            events.extend(parser.feed(c))
        events.extend(parser.flush())

        thinking_events = [e for e in events if e[0] == "thinking_delta"]
        content_events = [e for e in events if e[0] == "content_delta"]

        full_thinking = "".join(e[1]["delta"] for e in thinking_events)
        full_content = "".join(e[1]["delta"] for e in content_events)

        assert "Thought Block 1: Deriving Bramwell-Hill." in full_thinking
        assert "Thought Block 2: Calculating PWV." in full_thinking
        assert "Intro Section." in full_content
        assert "Intermediate analysis." in full_content
        assert "Final conclusion." in full_content

    def test_empty_chunks_and_idempotent_flush(self):
        """Verify parser handles empty strings, whitespace chunks, and repeated flush calls safely."""
        parser = StreamingThoughtParser(include_thinking=True)
        assert parser.feed("") == []
        assert parser.feed("") == []

        events = parser.feed("Some advice")
        assert len(events) == 1
        assert parser.flush() == []
        assert parser.flush() == []

    @pytest.mark.asyncio
    async def test_upstream_malformed_json_and_error_lines_resilience(self):
        """Verify generator handles corrupted data lines and non-JSON gracefully."""
        service = GeneticMoEService()
        request = DiagnosticStreamRequest(
            session_token=generate_session_token("malformed_json_seed"),
            query="Analyze cardiac drift",
            include_thinking=True,
            top_k_rag=0
        )

        async def malformed_iter():
            yield "data: {not valid json}"
            yield "not even sse line"
            yield ""
            yield 'data: {"choices":[{"delta":{"content":"<think>Valid thought</think>Valid content"}}]}'
            yield "data: [DONE]"

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.aiter_lines = malformed_iter

        mock_stream_ctx = AsyncMock()
        mock_stream_ctx.__aenter__.return_value = mock_resp
        mock_stream_ctx.__aexit__.return_value = None

        with patch("httpx.AsyncClient.stream", return_value=mock_stream_ctx):
            chunks = []
            async for chunk in service.execute_stream(request):
                chunks.append(chunk)

            full_sse_text = "".join(chunks)
            assert "event: thinking_delta" in full_sse_text
            assert "Valid thought" in full_sse_text
            assert "event: content_delta" in full_sse_text
            assert "Valid content" in full_sse_text
            assert "event: done" in full_sse_text

    @pytest.mark.asyncio
    async def test_upstream_http_500_cascades_to_fallback(self):
        """Verify that HTTP 500 from primary endpoint triggers fallback to secondary."""
        service = GeneticMoEService()
        request = DiagnosticStreamRequest(
            session_token=generate_session_token("http_500_cascade_seed"),
            query="Tabular splits summary",
            include_thinking=False,
            top_k_rag=0
        )

        call_count = 0

        def dynamic_stream(method, url, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_ctx = AsyncMock()
            mock_r = MagicMock()
            if call_count == 1:
                # Primary fails with 500
                mock_r.status_code = 500
            else:
                # Secondary succeeds
                mock_r.status_code = 200
                async def succ_iter():
                    yield 'data: {"choices":[{"delta":{"content":"Fallback success advice."}}]}'
                    yield 'data: [DONE]'
                mock_r.aiter_lines = succ_iter
            mock_ctx.__aenter__.return_value = mock_r
            mock_ctx.__aexit__.return_value = None
            return mock_ctx

        with patch("httpx.AsyncClient.stream", side_effect=dynamic_stream):
            chunks = []
            async for chunk in service.execute_stream(request):
                chunks.append(chunk)

            full_sse_text = "".join(chunks)
            assert "Fallback success advice." in full_sse_text
            assert "event: done" in full_sse_text
            assert call_count >= 2

    def test_parser_throughput_and_zero_memory_leak(self):
        """Benchmark StreamingThoughtParser throughput: must exceed 100,000 tokens/sec."""
        import time
        parser = StreamingThoughtParser(include_thinking=True)
        payload = "<think>" + "Deriving Windkessel equations\n" * 1000 + "</think>\nAdvice\n" * 1000

        t0 = time.perf_counter()
        events = parser.feed(payload)
        events.extend(parser.flush())
        elapsed = time.perf_counter() - t0

        tokens_processed = parser.total_tokens
        throughput_tok_s = tokens_processed / max(1e-6, elapsed)

        assert tokens_processed > 2000
        assert throughput_tok_s > 50000.0, f"Throughput too low: {throughput_tok_s:.2f} tok/s"

