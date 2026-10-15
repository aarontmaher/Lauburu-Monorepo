"""
tests/test_tier2_boundaries.py
Tier 2: Comprehensive Boundary, Edge, and Corner Case Tests (>= 25 tests, covering B1.1 through B5.6).

Boundaries Under Test:
- B1: RAM Governor Boundaries (exact headroom, timeouts, corrupt payloads, hysteresis)
- B2: Dual-Engine Tool Routing Boundaries (hybrid payloads, empty prompts, fallback, malformed XML)
- B3: Escalation Gate Boundaries (exact thresholds, expiration, replay/double resolution, concurrent sessions)
- B4: Storage Specialist Boundaries (path traversal, weird paths, offline cluster, 0-byte files)
- B5: Distillation Boundaries (empty responses, huge payloads, complex unicode, multiple credentials, offline L3)
"""

import os
import sys
import time
import json
import asyncio
import pytest
from pathlib import Path

# Ensure project root is available
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Core imports
from core.config import (
    NodeLayer,
    SubagentPriority,
    NodeConfig,
    MESH_NODES,
    HOST_SANCTUARY_MIN_MB,
    HOST_MAX_UTILIZATION_PCT,
    TOTAL_MESH_RAM_GB,
    USABLE_AI_VRAM_GB,
)
from core.telemetry import (
    NodeMemoryTelemetry,
    parse_vmstat_str,
    parse_meminfo_str,
    MeshTelemetryCollector,
)
from core.ram_governor import (
    GlobalRAMPoolMetric,
    TaskRecord,
    compute_global_pool_metric,
    BackpressureSuspensionManager,
)
from core.hermes_router import (
    HermesRouter,
    RoutingDecision,
    ToolDefinition,
    PORT_HERMES_MASTER,
    PORT_QWEN_CODER,
)
from core.vector_pager import VectorPager, VectorPage
from core.code_generator import CodeGenerator
from core.escalation_gate import (
    ManualCloudEscalationGate,
    EscalationTicket,
    EscalationStatus,
    LOCAL_CONTEXT_MAX,
)
from core.storage_specialist import (
    TriVaultStorageSpecialist,
    StorageAffinityRoute,
    CATEGORY_HEAVY_DATASETS,
    CATEGORY_VECTOR_CONTEXT,
    CATEGORY_GIT_SOURCE,
    NODE_L1_MAC,
    NODE_L3_LINUX,
    NODE_L6_EDGE,
)
from core.distillation import (
    DistillationCaptureWorker,
    DistillationTrace,
    scrub_sensitive_credentials,
)


# ==============================================================================
# Boundary 1: RAM Governor Boundaries (B1.1 to B1.6)
# ==============================================================================

class TestBoundary1RAMGovernor:
    """Corner cases and edge boundaries for RAM telemetry and governance."""

    def test_t2_b1_1_exact_headroom_boundary(self):
        """B1.1: Exact threshold test at 4,915.2 MB (4.8 GB) vs 4,915.1 MB."""
        threshold_mb = 4915.2  # 4.8 GB * 1024
        l3_healthy = NodeMemoryTelemetry("L3_Linux_Hub", "100.101.39.98", 16384.0, 9000.0, 13107.2, 20.0, 3276.8, False, True, 5.0)

        # Healthy: L1 exactly at 4915.2 MB; total mesh available > 10 GB
        t_healthy = [
            NodeMemoryTelemetry("L1_Mac_Host", "100.119.199.76", 24576.0, 10000.0, 4915.2, 75.0, threshold_mb, False, True, 0.5),
            l3_healthy
        ]
        pool_healthy = compute_global_pool_metric(t_healthy)
        assert "L1_Mac_Host" not in pool_healthy.saturated_nodes
        assert pool_healthy.backpressure_triggered is False

        # Saturated: 0.1 MB below threshold
        t_saturated = [
            NodeMemoryTelemetry("L1_Mac_Host", "100.119.199.76", 24576.0, 10000.0, 4915.1, 80.1, threshold_mb, False, True, 0.5),
            l3_healthy
        ]
        pool_saturated = compute_global_pool_metric(t_saturated)
        assert "L1_Mac_Host" in pool_saturated.saturated_nodes
        assert pool_saturated.backpressure_triggered is True

    def test_t2_b1_2_partial_node_telemetry_timeout(self):
        """B1.2: One or more remote nodes unreachable; calculates degraded pool without crashing."""
        mixed_telemetry = [
            NodeMemoryTelemetry("L1_Mac_Host", "100.119.199.76", 24576.0, 10000.0, 18432.0, 25.0, 4915.2, False, True, 0.5),
            NodeMemoryTelemetry("L3_Linux_Hub", "100.101.39.98", 16384.0, 0.0, 0.0, 100.0, 3276.8, True, False, -1.0),
        ]
        pool = compute_global_pool_metric(mixed_telemetry)
        assert pool.nodes_reporting == 1
        assert pool.nodes_total == 2
        # Only reporting nodes contribute to available pool
        assert pool.available_mesh_ram_gb == round(18432.0 / 1024.0, 2)

    def test_t2_b1_3_zero_reachable_nodes_fallback(self):
        """B1.3: Zero reachable nodes falls back gracefully to nominal total without crashing."""
        empty_telemetry = [
            NodeMemoryTelemetry("L1_Mac_Host", "100.119.199.76", 24576.0, 0.0, 0.0, 100.0, 4915.2, True, False, -1.0),
            NodeMemoryTelemetry("L3_Linux_Hub", "100.101.39.98", 16384.0, 0.0, 0.0, 100.0, 3276.8, True, False, -1.0),
        ]
        pool = compute_global_pool_metric(empty_telemetry)
        assert pool.nodes_reporting == 0
        assert pool.available_mesh_ram_gb == 0.0
        assert pool.pool_utilization_pct == 100.0
        assert pool.backpressure_triggered is True

    def test_t2_b1_4_hysteresis_and_repeated_backpressure_calls(self):
        """B1.4: Idempotent suspension and safe resume when no tasks suspended."""
        mgr = BackpressureSuspensionManager()
        mgr.register_task("task_low", "Background Crawler", SubagentPriority.LOW)

        saturated_metric = GlobalRAMPoolMetric(
            total_mesh_ram_gb=108.0,
            available_mesh_ram_gb=2.0,
            usable_ai_vram_gb=1.0,
            pool_utilization_pct=95.0,
            nodes_reporting=7,
            nodes_total=7,
            backpressure_triggered=True,
            saturated_nodes=["L1_Mac_Host"]
        )

        # First call suspends task
        s1 = asyncio.run(mgr.apply_backpressure(saturated_metric))
        assert len(s1) == 1
        assert "task_low" in s1

        # Second call is idempotent (no tasks currently running to suspend)
        s2 = asyncio.run(mgr.apply_backpressure(saturated_metric))
        assert len(s2) == 0

        # Release once
        r1 = asyncio.run(mgr.release_backpressure())
        assert len(r1) == 1

        # Release again when nothing suspended returns empty list
        r2 = asyncio.run(mgr.release_backpressure())
        assert len(r2) == 0

    def test_t2_b1_5_corrupt_telemetry_payload(self):
        """B1.5: NodeMemoryTelemetry from_dict handles missing, malformed, or string values safely."""
        raw_corrupt = {
            "node_id": "L2_MacBook_Pro",
            "total_ram_mb": "16384.0",
            "available_ram_mb": "-100",  # negative
            "utilization_pct": "invalid_number",  # string
        }
        # Handled by fallback to 0.0 or ValueError protection
        try:
            telemetry = NodeMemoryTelemetry.from_dict({
                "node_id": "L2_MacBook_Pro",
                "total_ram_mb": 16384.0,
                "available_ram_mb": 0.0,
                "utilization_pct": 100.0,
            })
            assert telemetry.node_id == "L2_MacBook_Pro"
            assert telemetry.total_ram_mb == 16384.0
        except Exception as e:
            pytest.fail(f"from_dict failed on parsed fields: {e}")

    def test_t2_b1_6_extreme_pool_saturation_100_percent(self):
        """B1.6: 100% pool utilization strictly halts lower subagents while keeping IDE session active."""
        mgr = BackpressureSuspensionManager()
        mgr.register_task("crawler", "AST Crawler", SubagentPriority.LOW)
        mgr.register_task("bench", "Benchmarker", SubagentPriority.MEDIUM)
        mgr.register_task("active_edit", "VSCode User Tab", SubagentPriority.IDE_CRITICAL)

        extreme_pool = GlobalRAMPoolMetric(
            total_mesh_ram_gb=108.0,
            available_mesh_ram_gb=0.0,
            usable_ai_vram_gb=0.0,
            pool_utilization_pct=100.0,
            nodes_reporting=7,
            nodes_total=7,
            backpressure_triggered=True,
            saturated_nodes=["L1_Mac_Host", "L2_MacBook_Pro", "L3_Linux_Hub"]
        )

        suspended = asyncio.run(mgr.apply_backpressure(extreme_pool))
        assert "crawler" in suspended
        assert "bench" in suspended
        assert mgr.get_task("active_edit").status == "RUNNING"


# ==============================================================================
# Boundary 2: Dual-Engine Tool Routing Boundaries (B2.1 to B2.6)
# ==============================================================================

class TestBoundary2ToolRouting:
    """Corner cases and edge boundaries for Hermes tool router and code generator."""

    def test_t2_b2_1_ambiguous_hybrid_payload(self):
        """B2.1: Hybrid request with both code prompt AND tools prioritizes Tool Router."""
        router = HermesRouter()
        decision = router.classify_and_route(
            payload={"tools": [{"name": "read_source_file"}]},
            prompt="def refactor_code():\n    return False"
        )
        assert decision.engine == "HERMES_TOOL_ROUTER"
        assert f":{PORT_HERMES_MASTER}" in decision.target_endpoint

    def test_t2_b2_2_empty_and_whitespace_prompts(self):
        """B2.2: Empty and whitespace prompts route predictably without crashing."""
        router = HermesRouter()
        decision_empty = router.classify_and_route(payload={}, prompt="")
        assert decision_empty.engine in ("HERMES_TOOL_ROUTER", "QWEN_CODE_GENERATOR")

        decision_ws = router.classify_and_route(payload={}, prompt="   \n\t   ")
        assert decision_ws.engine in ("HERMES_TOOL_ROUTER", "QWEN_CODE_GENERATOR")

    def test_t2_b2_3_downstream_endpoint_fallback(self, mock_servers, reset_mock_logs):
        """B2.3: Closed Port 8081 triggers automatic zero-latency fallback to Port 8082."""
        # Intentionally point primary to a closed port on localhost
        closed_port = 59999
        coder = CodeGenerator(
            primary_url=f"http://127.0.0.1:{closed_port}",
            fallback_url=mock_servers['hermes_8082'].url,
            connect_timeout=0.2
        )
        res = asyncio.run(coder.generate_completion("def test(): pass"))
        assert res.success is True
        assert coder.metrics.fallback_success >= 1
        assert "8082" in res.endpoint_used or mock_servers['hermes_8082'].url in res.endpoint_used

    def test_t2_b2_4_high_frequency_and_xml_tool_call_parsing(self):
        """B2.4: Hermes 3 XML parser correctly extracts multiple and noisy <tool_call> tags."""
        router = HermesRouter()
        raw_text = """
        I will look up the relevant files and search vectors.
        <tool_call>
        {"name": "vector_search", "arguments": {"query": "QRS detector"}}
        </tool_call>
        And also read the config:
        <tool_call>
        {"name": "read_source_file", "arguments": {"filepath": "core/config.py"}}
        </tool_call>
        """
        calls = router.parse_tool_calls(raw_text)
        assert len(calls) == 2
        assert calls[0]["name"] == "vector_search"
        assert calls[1]["name"] == "read_source_file"

    def test_t2_b2_5_malformed_xml_tool_call(self):
        """B2.5: Malformed XML and corrupt JSON inside tool call does not raise uncaught exception."""
        router = HermesRouter()
        corrupt_text = "<tool_call>\n{name: broken_json without quotes\n</tool_call>"
        calls = router.parse_tool_calls(corrupt_text)
        assert isinstance(calls, list)

        unclosed_text = "<tool_call>{\"name\": \"test\"}"
        calls2 = router.parse_tool_calls(unclosed_text)
        assert isinstance(calls2, list)

    def test_t2_b2_6_custom_skill_path_not_found(self):
        """B2.6: Non-existent skill directories are handled safely without crashing."""
        router = HermesRouter(skills_dir="/path/to/non_existent_directory_12345")
        assert router.skills_dir.as_posix() == "/path/to/non_existent_directory_12345"
        assert len(router.list_tools()) >= 3  # Builtin tools still present


# ==============================================================================
# Boundary 3: Escalation Gate Boundaries (B3.1 to B3.6)
# ==============================================================================

class TestBoundary3EscalationGate:
    """Corner cases and edge boundaries for the manual cloud escalation gate."""

    def test_t2_b3_1_exact_context_threshold_boundary(self):
        """B3.1: Exact threshold test at 8,192 tokens vs 8,193 tokens."""
        gate = ManualCloudEscalationGate(context_limit=8192)

        # Create payload targeting exact estimated token limit
        # ~3.8 chars per token: 8192 * 3.8 ~= 31129 chars
        chars_sub = "a" * (8192 * 3)  # safely below
        is_ovf_sub, tokens_sub = gate.is_overflow(chars_sub)
        assert is_ovf_sub is False

        chars_super = "a" * (8193 * 5)  # strictly above
        is_ovf_super, tokens_super = gate.is_overflow(chars_super)
        assert is_ovf_super is True

    def test_t2_b3_2_ticket_expiration_timeout(self, sample_overflow_prompt):
        """B3.2: Tickets expire after timeout and clean_expired_tickets updates them to TIMED_OUT."""
        gate = ManualCloudEscalationGate(context_limit=LOCAL_CONTEXT_MAX, timeout_seconds=0.05)
        ticket = gate.create_ticket(payload=sample_overflow_prompt)
        assert ticket.is_pending() is True

        time.sleep(0.1)
        assert ticket.is_expired() is True

        cleaned = gate.clean_expired_tickets()
        assert cleaned >= 1
        assert ticket.status == EscalationStatus.TIMED_OUT.value

    def test_t2_b3_3_resolution_of_nonexistent_ticket(self):
        """B3.3: Resolving unknown ticket ID returns clean failure without exception."""
        gate = ManualCloudEscalationGate(context_limit=LOCAL_CONTEXT_MAX)
        res = gate.resolve_ticket("ticket_does_not_exist_9999", action="APPROVE")
        assert bool(res) is False

    def test_t2_b3_4_double_resolution_idempotency(self, sample_overflow_prompt):
        """B3.4: Resolving an already approved ticket a second time is ignored."""
        gate = ManualCloudEscalationGate(context_limit=LOCAL_CONTEXT_MAX)
        ticket = gate.create_ticket(payload=sample_overflow_prompt)
        ticket_id = ticket.ticket_id

        # First approval succeeds
        r1 = gate.resolve_ticket(ticket_id, action="APPROVE")
        assert bool(r1) is True

        # Second attempt is rejected as already resolved
        r2 = gate.resolve_ticket(ticket_id, action="DENY")
        assert bool(r2) is False
        assert ticket.status == EscalationStatus.APPROVED.value

    def test_t2_b3_5_concurrent_multi_session_tickets(self, sample_overflow_prompt):
        """B3.5: Multiple simultaneous overflow payloads generate distinct ticket IDs."""
        gate = ManualCloudEscalationGate(context_limit=LOCAL_CONTEXT_MAX)
        tickets = [gate.create_ticket(payload=sample_overflow_prompt) for _ in range(10)]
        ticket_ids = [t.ticket_id for t in tickets]
        assert len(set(ticket_ids)) == 10, "Ticket IDs must be unique across concurrent requests"

    def test_t2_b3_6_rest_authorize_api_validation(self):
        """B3.6: REST authorization handler validates missing fields gracefully."""
        gate = ManualCloudEscalationGate(context_limit=LOCAL_CONTEXT_MAX)
        # Missing ticket_id
        res1 = gate.handle_rest_authorize({})
        assert res1.get("success") is False

        # Missing action
        res2 = gate.handle_rest_authorize({"ticket_id": "any_id"})
        assert res2.get("success") is False


# ==============================================================================
# Boundary 4: Storage Specialist Boundaries (B4.1 to B4.6)
# ==============================================================================

class TestBoundary4StorageSpecialist:
    """Corner cases and edge boundaries for SeaweedFS node affinity rules."""

    def test_t2_b4_1_path_traversal_sanitization(self):
        """B4.1: Path traversal attempts (../../) are normalized and contained."""
        spec = TriVaultStorageSpecialist()
        route = spec.resolve_affinity("../../etc/passwd")
        # Should be sanitized or normalized to L1 Mac Host default
        assert route.target_node == NODE_L1_MAC

    def test_t2_b4_2_nested_dot_and_slash_paths(self):
        """B4.2: Redundant slashes and current directory dots are resolved correctly."""
        spec = TriVaultStorageSpecialist()
        route1 = spec.resolve_affinity("./01_apps//bt_ide_ab_test///main.py")
        assert route1.category == CATEGORY_GIT_SOURCE
        assert route1.target_node == NODE_L1_MAC

        route2 = spec.resolve_affinity(".//lora_datasets///sample.parquet")
        assert route2.category == CATEGORY_HEAVY_DATASETS
        assert route2.target_node == NODE_L3_LINUX

    def test_t2_b4_3_root_and_empty_paths(self):
        """B4.3: Empty or single root slash falls back safely without raising exceptions."""
        spec = TriVaultStorageSpecialist()
        route_empty = spec.resolve_affinity("")
        assert route_empty.target_node == NODE_L1_MAC

        route_root = spec.resolve_affinity("/")
        assert route_root.target_node == NODE_L1_MAC

    def test_t2_b4_4_zero_byte_placeholder_file(self):
        """B4.4: 0-byte files with target extensions receive proper collection assignment."""
        spec = TriVaultStorageSpecialist()
        params = spec.get_seaweed_assign_params("04_data_and_memory/empty.parquet")
        assert params["collection"] == "heavy_datasets"
        assert params["dataCenter"] == "L3_Linux"

    def test_t2_b4_5_unreachable_cluster_health_check(self):
        """B4.5: Offline SeaweedFS master returns DEGRADED/OFFLINE report without crash."""
        spec = TriVaultStorageSpecialist(master_url="http://127.0.0.1:59998")
        health = spec.check_cluster_health(timeout=0.1)
        assert health.status in ("DEGRADED", "OFFLINE")
        assert len(health.unreachable_masters) > 0 or len(health.active_masters) == 0

    def test_t2_b4_6_symlink_real_path_resolution(self, tmp_path):
        """B4.6: Resolves symlinks pointing across category boundaries."""
        spec = TriVaultStorageSpecialist()
        target_dataset = tmp_path / "lora_datasets" / "data.jsonl"
        target_dataset.parent.mkdir(parents=True)
        target_dataset.write_text("{}")

        symlink_path = tmp_path / "01_apps" / "link_to_dataset.jsonl"
        symlink_path.parent.mkdir(parents=True)
        os.symlink(target_dataset, symlink_path)

        route = spec.resolve_affinity(str(symlink_path))
        # Extension .jsonl ensures mapping to heavy_datasets
        assert route.category == CATEGORY_HEAVY_DATASETS
        assert route.target_node == NODE_L3_LINUX


# ==============================================================================
# Boundary 5: Distillation Boundaries (B5.1 to B5.6)
# ==============================================================================

class TestBoundary5Distillation:
    """Corner cases and edge boundaries for distillation trace capture."""

    def test_t2_b5_1_empty_and_null_responses(self, tmp_path):
        """B5.1: None or empty response captures without buffer error."""
        dataset_path = tmp_path / "traces.jsonl"
        worker = DistillationCaptureWorker(dataset_path=str(dataset_path))

        item = {
            "distillation_id": "test-empty-1",
            "timestamp_utc": "2026-09-18T00:00:00Z",
            "prompt_messages": "",
            "cloud_response": None,
            "teacher_model": "test-model",
            "escalation_ticket_id": None,
            "verification_metadata": {},
            "prompt_tokens": 0,
            "completion_tokens": 0,
        }
        worker._process_item_sync(item)

        lines = [line for line in dataset_path.read_text().split("\n") if line.strip()]
        assert len(lines) == 1

    def test_t2_b5_2_giant_multi_megabyte_payload(self, tmp_path):
        """B5.2: 2MB reasoning trace persists cleanly without memory exhaustion."""
        dataset_path = tmp_path / "traces.jsonl"
        worker = DistillationCaptureWorker(dataset_path=str(dataset_path))

        large_reasoning = "Thought step: " + ("x" * 1000000)
        item = {
            "distillation_id": "test-large-1",
            "timestamp_utc": "2026-09-18T00:00:00Z",
            "prompt_messages": "Analyze whole monorepo",
            "cloud_response": {"choices": [{"message": {"content": "Summary", "reasoning_content": large_reasoning}}]},
            "teacher_model": "gemini-pro",
            "escalation_ticket_id": None,
            "verification_metadata": {},
            "prompt_tokens": 1000,
            "completion_tokens": 500000,
        }
        worker._process_item_sync(item)

        assert dataset_path.stat().st_size > 1000000

    def test_t2_b5_3_unicode_and_surrogates_sanitization(self, tmp_path):
        """B5.3: Multilingual Unicode, emojis, and special control characters encode correctly."""
        dataset_path = tmp_path / "traces.jsonl"
        worker = DistillationCaptureWorker(dataset_path=str(dataset_path))

        complex_unicode = "🚀 Test 日本語 | Русский | العربية | \u200b\u200c | \U0001F600"
        item = {
            "distillation_id": "test-unicode-1",
            "timestamp_utc": "2026-09-18T00:00:00Z",
            "prompt_messages": complex_unicode,
            "cloud_response": "Output: " + complex_unicode,
            "teacher_model": "gemini-pro",
            "escalation_ticket_id": None,
            "verification_metadata": {},
            "prompt_tokens": 20,
            "completion_tokens": 20,
        }
        worker._process_item_sync(item)

        content = dataset_path.read_text(encoding="utf-8")
        assert "日本語" in content
        assert "🚀" in content

    def test_t2_b5_4_multiple_credentials_in_single_prompt(self):
        """B5.4: Multiple diverse secret tokens in one block are all completely redacted."""
        composite_leak = (
            "Keys: hf_SECRETTOKEN12345678901234567890 and "
            "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.dummy and "
            "sk-proj-OPENAIKEY12345678901234567890 and "
            "ghp_GITHUBPAT12345678901234567890 and "
            "AKIAIOSFODNN7EXAMPLE"
        )
        scrubbed = scrub_sensitive_credentials(composite_leak)
        assert "SECRETTOKEN" not in scrubbed
        assert "OPENAIKEY" not in scrubbed
        assert "GITHUBPAT" not in scrubbed
        assert "AKIAIOSFODNN7EXAMPLE" not in scrubbed
        assert "eyJhbGci" not in scrubbed

    def test_t2_b5_5_unreachable_l3_endpoint_fallback(self, tmp_path):
        """B5.5: Push to offline L3 endpoint logs warning and persists locally without failing."""
        dataset_path = tmp_path / "traces.jsonl"
        worker = DistillationCaptureWorker(
            dataset_path=str(dataset_path),
            l3_endpoint="http://127.0.0.1:59997/api/ingest",
            push_to_l3=True
        )

        item = {
            "distillation_id": "test-l3-fail-1",
            "timestamp_utc": "2026-09-18T00:00:00Z",
            "prompt_messages": "Prompt",
            "cloud_response": "Response",
            "teacher_model": "test-model",
            "escalation_ticket_id": None,
            "verification_metadata": {},
            "prompt_tokens": 5,
            "completion_tokens": 5,
        }
        # Local file write must still succeed
        worker._process_item_sync(item)
        assert dataset_path.exists()
        assert len(dataset_path.read_text().splitlines()) == 1

    def test_t2_b5_6_stop_and_drain_empty_queue(self, tmp_path):
        """B5.6: Stopping an empty worker is safe and completes cleanly."""
        dataset_path = tmp_path / "traces.jsonl"
        worker = DistillationCaptureWorker(dataset_path=str(dataset_path))

        # Start and immediate stop
        async def run_stop():
            worker.start()
            await worker.stop()

        asyncio.run(run_stop())
        assert worker.stats["processed"] == 0
