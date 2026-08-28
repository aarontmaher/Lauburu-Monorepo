"""
Comprehensive Unit & Integration Test Suite for Milestone 3 (R3):
- StreamingThoughtParser State Machine & Chunk Splitting Edge Cases
- Genetic MoE Expert Model Taxonomy & Classification
- Dynamic Prompt Synthesis with RAG Context & Zero-PII Sanitization
- Historical Session Vector Indexing & Semantic Retrieval (/api/v1/rag/index_session, /api/v1/rag/query)
- Server-Sent Events (SSE) Streaming Endpoint (/api/v1/ai/diagnostic/stream) & Fallback Cascade
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
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
    IndexSessionRequest,
    RagQueryRequest,
    RagQueryResultItem,
)
from app.storage.chroma_manager import ChromaManager, FallbackVectorStore


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def valid_token():
    return generate_session_token("test_m3_seed_123")


# ============================================================================
# 1. StreamingThoughtParser State Machine & Chunk Splitting Edge Cases
# ============================================================================

class TestStreamingThoughtParser:
    def test_clean_think_and_content_separation(self):
        """Test parsing of a standard LLM response containing <think>...</think>."""
        parser = StreamingThoughtParser(include_thinking=True)
        chunks = [
            "<think>\nDeriving Bramwell-Hill arterial compliance C_art...\n",
            "C_art = V / (rho * PWV^2)\n</think>\n",
            "### Physiological Assessment\nYour vascular resistance is optimal."
        ]

        all_events = []
        for chunk in chunks:
            all_events.extend(parser.feed(chunk))
        all_events.extend(parser.flush())

        thinking_events = [e for e in all_events if e[0] == "thinking_delta"]
        content_events = [e for e in all_events if e[0] == "content_delta"]

        assert len(thinking_events) >= 2
        assert len(content_events) >= 1

        full_thinking = "".join(e[1]["delta"] for e in thinking_events)
        full_content = "".join(e[1]["delta"] for e in content_events)

        assert "Bramwell-Hill arterial compliance" in full_thinking
        assert "Physiological Assessment" in full_content
        assert "<think>" not in full_thinking
        assert "</think>" not in full_thinking
        assert "<think>" not in full_content

    def test_split_opening_tag_across_chunks(self):
        """Test tag fragmentation where <think> is split across multiple chunks: '<th' + 'ink>'."""
        parser = StreamingThoughtParser(include_thinking=True)
        chunks = [
            "Introductory remark. <th",
            "ink>\nStep 1: Calculate cardiac drift percentage.",
            "</think>\nConclusion."
        ]

        all_events = []
        for c in chunks:
            all_events.extend(parser.feed(c))
        all_events.extend(parser.flush())

        full_thinking = "".join(e[1]["delta"] for e in all_events if e[0] == "thinking_delta")
        full_content = "".join(e[1]["delta"] for e in all_events if e[0] == "content_delta")

        assert "Introductory remark. " in full_content
        assert "Step 1: Calculate cardiac drift percentage." in full_thinking
        assert "Conclusion." in full_content

    def test_split_closing_tag_across_chunks(self):
        """Test tag fragmentation where </think> is split across chunks: '</thi' + 'nk>'."""
        parser = StreamingThoughtParser(include_thinking=True)
        chunks = [
            "<think>Calculating PWV from PTT...",
            " PWV = 6.4 m/s. </thi",
            "nk>\n\nYour arterial wave velocity is within the normal aerobic band."
        ]

        all_events = []
        for c in chunks:
            all_events.extend(parser.feed(c))
        all_events.extend(parser.flush())

        full_thinking = "".join(e[1]["delta"] for e in all_events if e[0] == "thinking_delta")
        full_content = "".join(e[1]["delta"] for e in all_events if e[0] == "content_delta")

        assert "Calculating PWV from PTT... PWV = 6.4 m/s. " in full_thinking
        assert "Your arterial wave velocity" in full_content

    def test_thought_alias_tags(self):
        """Test alternative <thought>...</thought> tags."""
        parser = StreamingThoughtParser(include_thinking=True)
        events = parser.feed("<thought>Deep biological insight.</thought>Final advice.")
        events.extend(parser.flush())

        full_thinking = "".join(e[1]["delta"] for e in events if e[0] == "thinking_delta")
        full_content = "".join(e[1]["delta"] for e in events if e[0] == "content_delta")

        assert "Deep biological insight." in full_thinking
        assert "Final advice." in full_content

    def test_divergent_angle_bracket_not_tag(self):
        """Test that '<' or '</' followed by non-tag text does not stall or drop text."""
        parser = StreamingThoughtParser(include_thinking=True)
        chunks = [
            "Your systolic blood pressure is <",
            " 120 mmHg and diastolic is <",
            " 80 mmHg."
        ]

        all_events = []
        for c in chunks:
            all_events.extend(parser.feed(c))
        all_events.extend(parser.flush())

        full_content = "".join(e[1]["delta"] for e in all_events if e[0] == "content_delta")
        assert "< 120 mmHg and diastolic is < 80 mmHg." in full_content

    def test_pure_markdown_no_thinking_tags(self):
        """Test stream containing no thinking tags at all."""
        parser = StreamingThoughtParser(include_thinking=True)
        chunks = [
            "### Workout Summary\n",
            "- Duration: 45 min\n",
            "- Mean HR: 138 BPM\n",
            "- Zone 2 Compliance: 95%"
        ]

        all_events = []
        for c in chunks:
            all_events.extend(parser.feed(c))
        all_events.extend(parser.flush())

        thinking_events = [e for e in all_events if e[0] == "thinking_delta"]
        content_events = [e for e in all_events if e[0] == "content_delta"]

        assert len(thinking_events) == 0
        assert len(content_events) >= 1
        full_content = "".join(e[1]["delta"] for e in content_events)
        assert "Zone 2 Compliance: 95%" in full_content

    def test_exclude_thinking_flag(self):
        """Test that when include_thinking=False, thinking deltas are omitted from emissions."""
        parser = StreamingThoughtParser(include_thinking=False)
        events = parser.feed("<think>Internal calculations...</think>Direct recommendation.")
        events.extend(parser.flush())

        thinking_events = [e for e in events if e[0] == "thinking_delta"]
        content_events = [e for e in events if e[0] == "content_delta"]

        assert len(thinking_events) == 0
        assert len(content_events) == 1
        assert content_events[0][1]["delta"] == "Direct recommendation."


# ============================================================================
# 2. Genetic MoE Expert Model Taxonomy & Classification
# ============================================================================

class TestGeneticMoEClassification:
    def setup_method(self):
        self.service = GeneticMoEService()

    def test_multimodal_classification(self):
        """Verify ECG waveform and visual biometrics queries route to Qwen3-VL-32B."""
        queries = [
            "Analyze my 2D ECG strip waveform for baseline wander",
            "Show me the Poincaré HRV scatter plot morphology",
            "Is the dicrotic notch visible in this PPG optical pulse curve?"
        ]
        for q in queries:
            model, endpoint, rationale = self.service.classify_expert(q)
            assert model == MODEL_QWEN3_VL
            assert "vision-language" in rationale.lower() or "waveform" in rationale.lower()

    def test_multimodal_classification_with_image_payload(self):
        """Verify queries with image_payload_b64 route to Qwen3-VL even without keywords."""
        model, endpoint, _ = self.service.classify_expert("Look at this data", has_image=True)
        assert model == MODEL_QWEN3_VL

    def test_deep_cardiovascular_reasoning_classification(self):
        """Verify mathematical proofs and arterial stiffness drift route to DeepSeek-R1."""
        queries = [
            "Provide the Bramwell-Hill mathematical proof for vascular compliance",
            "Why is my systolic BP rising at steady 180W power output due to cardiovascular drift?",
            "Explain the Moens-Korteweg wave propagation mechanism under arterial stiffness decay",
            "Compare my autonomic fatigue and parasympathetic RMSSD decay over the last 3 weeks"
        ]
        for q in queries:
            model, endpoint, rationale = self.service.classify_expert(q)
            assert model == MODEL_DEEPSEEK_R1
            assert "reasoning" in rationale.lower() or "hemodynamic" in rationale.lower()

    def test_tabular_and_splits_classification(self):
        """Verify workout summaries, lap splits, and TRIMP/TSS calculations route to Qwen2.5-Coder."""
        queries = [
            "Generate a tabular summary of my lap power splits",
            "Calculate TRIMP and TSS training load stats for today's session",
            "Export a CSV statistics table of my average heart rate per interval"
        ]
        for q in queries:
            model, endpoint, rationale = self.service.classify_expert(q)
            assert model == MODEL_QWEN_CODER
            assert "coding" in rationale.lower() or "tabular" in rationale.lower()

    def test_default_classification(self):
        """Verify general physiological query defaults to DeepSeek-R1."""
        model, endpoint, rationale = self.service.classify_expert("How should I pace my Zone 2 ride today?")
        assert model == MODEL_DEEPSEEK_R1


# ============================================================================
# 3. Dynamic Prompt Synthesis & Zero-PII Context Injection
# ============================================================================

class TestPromptSynthesisAndSecurity:
    def setup_method(self):
        self.service = GeneticMoEService()

    def test_prompt_assembly_with_rag_and_telemetry(self):
        """Verify prompt contains exact biophysical vector, RAG matches, and Zero-PII sanitization."""
        rag_items = [
            RagQueryResultItem(
                document="Session a1b2c3d4: Duration 3600s, Mean SBP 125.0, Mean HR 135.0, Drift: False",
                session_hash="a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
                score=0.92,
                metadata={"duration_sec": 3600}
            )
        ]
        telemetry = {
            "ptt_ms": 172.5,
            "hr_bpm": 142.0,
            "sbp_mmHg": 130.0,
            "dbp_mmHg": 82.0,
            "power_watts": 185.0,
            "dfa_alpha1": 0.82,
            "user_name": "Prohibited Aaron",  # PII that should be stripped
            "email": "aaron@example.com"      # PII that should be stripped
        }

        messages = self.service.build_prompt(
            query="Why did blood pressure rise slightly in Zone 2?",
            expert_model=MODEL_DEEPSEEK_R1,
            rag_items=rag_items,
            telemetry=telemetry
        )

        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert "DeepSeek-R1-Distill-Qwen-32B" in messages[0]["content"]

        user_content = messages[1]["content"]
        assert "[CURRENT WORKOUT BIOPHYSICAL STATE]" in user_content
        assert "172.5" in user_content
        assert "142.0" in user_content
        assert "185.0" in user_content
        assert "[HISTORICAL WORKOUT RAG CONTEXT (Past Relevant Sessions)]" in user_content
        assert "Session a1b2c3d4" in user_content
        assert "Score: 0.92" in user_content
        assert "[USER QUERY]" in user_content
        assert "Why did blood pressure rise slightly" in user_content

        # Verify Zero-PII sanitization stripped prohibited keys
        assert "Prohibited Aaron" not in user_content
        assert "aaron@example.com" not in user_content


# ============================================================================
# 4. RAG Endpoints Integration (/api/v1/rag/index_session, /api/v1/rag/query)
# ============================================================================

class TestRagEndpoints:
    def test_index_and_query_session_lifecycle(self, client, valid_token):
        """Test full indexing of a session followed by semantic vector query retrieval."""
        session_hash = "f1e2d3c4b5a6f1e2d3c4b5a6f1e2d3c4b5a6f1e2d3c4b5a6f1e2d3c4b5a6f1e2"
        doc_text = (
            "Session f1e2d3c4: Duration 5400s, Mean SBP 128.4 mmHg, Mean DBP 81.2 mmHg, "
            "Mean MAP 96.9 mmHg, Mean HR 139.5 BPM, RMSSD 52.0 ms. Cardiac drift detected: False. "
            "Zone 2 Compliance: 0.96. Status: completed."
        )

        # 1. Index the session
        index_payload = {
            "session_token": valid_token,
            "session_hash": session_hash,
            "document_text": doc_text,
            "summary_metadata": {
                "duration_sec": 5400,
                "mean_sbp": 128.4,
                "mean_hr": 139.5,
                "zone2_compliance_ratio": 0.96
            }
        }
        res_index = client.post("/api/v1/rag/index_session", json=index_payload)
        assert res_index.status_code == 200
        data_index = res_index.json()
        assert data_index["status"] == "indexed"
        assert data_index["session_hash"] == session_hash

        # 2. Query RAG
        query_payload = {
            "session_token": valid_token,
            "query": "How was my 90-minute Zone 2 compliance and heart rate?",
            "top_k": 3,
            "include_historical_context": True
        }
        res_query = client.post("/api/v1/rag/query", json=query_payload)
        assert res_query.status_code == 200
        data_query = res_query.json()
        assert data_query["selected_expert_model"] in [MODEL_DEEPSEEK_R1, MODEL_QWEN_CODER]
        assert len(data_query["results"]) > 0
        assert data_query["results"][0]["score"] > 0.0
        assert data_query["latency_ms"] >= 0.0

    def test_rag_query_invalid_token(self, client):
        """Test rejection of malformed session token."""
        query_payload = {
            "session_token": "invalid_short_token",
            "query": "What is my vascular fatigue?"
        }
        res = client.post("/api/v1/rag/query", json=query_payload)
        assert res.status_code == 422 or res.status_code == 400


# ============================================================================
# 5. SSE Diagnostic Streaming (/api/v1/ai/diagnostic/stream) & Fallback
# ============================================================================

class TestAiDiagnosticStreamingEndpoint:
    def test_sse_streaming_format_and_events(self, client, valid_token):
        """Verify the streaming endpoint returns text/event-stream with thinking_delta and content_delta."""
        mock_chunks = [
            'data: {"choices": [{"delta": {"content": "<think>Evaluating Windkessel compliance...</think>"}}]}\n\n',
            'data: {"choices": [{"delta": {"content": "Your cardiovascular parameters are in optimal aerobic Zone 2."}}]}\n\n',
            'data: [DONE]\n\n'
        ]

        class MockStreamResponse:
            status_code = 200
            async def aiter_lines(self):
                for c in mock_chunks:
                    yield c.strip()

        class MockAsyncClient:
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                pass
            def stream(self, method, url, **kwargs):
                class AsyncContext:
                    async def __aenter__(self):
                        return MockStreamResponse()
                    async def __aexit__(self, *args):
                        pass
                return AsyncContext()

        with patch("httpx.AsyncClient", return_value=MockAsyncClient()):
            stream_payload = {
                "protocol_version": "1.0.0",
                "session_token": valid_token,
                "query": "Why did my blood pressure stay at 128 mmHg at steady 180W?",
                "telemetry_context": {
                    "ptt_ms": 172.0,
                    "hr_bpm": 140.0,
                    "sbp_mmHg": 128.0,
                    "dbp_mmHg": 80.0,
                    "power_watts": 180.0,
                    "dfa_alpha1": 0.85
                },
                "include_thinking": True
            }

            res = client.post("/api/v1/ai/diagnostic/stream", json=stream_payload)
            assert res.status_code == 200
            assert "text/event-stream" in res.headers["content-type"]
            assert res.headers.get("x-accel-buffering") == "no"

            body = res.text
            assert "event: thinking_delta" in body or "event: content_delta" in body
            assert "event: done" in body

    def test_sse_streaming_resilient_fallback_on_network_error(self, client, valid_token):
        """Verify that when the local mesh is unreachable, the system executes deterministic fallback cleanly."""
        class FailingAsyncClient:
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                pass
            def stream(self, method, url, **kwargs):
                raise httpx.ConnectError("Connection refused on port 8081")

        with patch("httpx.AsyncClient", return_value=FailingAsyncClient()):
            stream_payload = {
                "protocol_version": "1.0.0",
                "session_token": valid_token,
                "query": "Assess my cardiac drift during steady state cycling.",
                "include_thinking": True
            }

            res = client.post("/api/v1/ai/diagnostic/stream", json=stream_payload)
            assert res.status_code == 200
            body = res.text

            assert "event: content_delta" in body
            assert "event: done" in body
            assert "Local-Biophysical-Engine" in body or "total_tokens" in body

    def test_zero_pii_middleware_rejection_on_prohibited_key(self, client, valid_token):
        """Verify ZeroPiiSanitizationMiddleware immediately rejects requests containing PII."""
        forbidden_payload = {
            "protocol_version": "1.0.0",
            "session_token": valid_token,
            "query": "Is my blood pressure fine?",
            "user_name": "Aaron Maher"  # Forbidden key
        }
        res = client.post("/api/v1/ai/diagnostic/stream", json=forbidden_payload)
        assert res.status_code in [400, 422]
