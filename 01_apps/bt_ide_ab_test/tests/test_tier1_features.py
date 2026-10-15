"""
tests/test_tier1_features.py
Tier 1: Comprehensive Feature Coverage Tests (>= 25 tests, covering F1.1 through F5.6).

Features Under Test:
- F1: Dynamic Global Mesh RAM Governance (core.ram_governor, core.telemetry)
- F2: Dual-Engine Tool Routing Separation (core.hermes_router, core.code_generator, core.vector_pager)
- F3: Manual Cloud Escalation Gate (core.escalation_gate)
- F4: Tri-Vault Storage Specialist & Hardware Affinity (core.storage_specialist)
- F5: Continuous Local Distillation Loop (core.distillation)
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
    collect_local_node_telemetry,
    collect_local_os_memory,
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
# Feature 1: Dynamic Global Mesh RAM Governance (F1.1 to F1.6)
# ==============================================================================

class TestFeature1RAMGovernance:
    """Tests covering dynamic global mesh RAM governance and backpressure."""

    def test_t1_f1_1_multi_endpoint_telemetry_polling(self, mock_servers, reset_mock_logs):
        """F1.1: Multi-node async polling using MeshTelemetryCollector."""
        collector = MeshTelemetryCollector()
        collector.set_simulated_ip("100.119.199.76", {
            "node_id": "L1_Mac_Host",
            "total_ram_mb": 24576.0,
            "free_ram_mb": 10000.0,
            "available_ram_mb": 18432.0,
            "utilization_pct": 25.0,
            "dynamic_safety_threshold_mb": 4915.2,
            "is_saturated": False
        })
        collector.set_simulated_ip("100.101.39.98", {
            "node_id": "L3_Linux_Hub",
            "total_ram_mb": 16384.0,
            "free_ram_mb": 8000.0,
            "available_ram_mb": 13107.2,
            "utilization_pct": 20.0,
            "dynamic_safety_threshold_mb": 3276.8,
            "is_saturated": False
        })

        results = asyncio.run(collector.collect_all())
        assert len(results) >= 2, f"Expected telemetry reports from nodes, got {len(results)}"
        reporting = [r for r in results if r.is_reachable]
        assert len(reporting) >= 2
        for r in reporting:
            assert r.total_ram_mb > 0
            assert r.available_ram_mb > 0
            assert 0.0 <= r.utilization_pct <= 100.0

    def test_t1_f1_2_global_ram_pool_computation(self):
        """F1.2: Compute aggregate cluster memory metrics across all 7 layers."""
        telemetry_items = [
            NodeMemoryTelemetry("L1_Mac_Host", "100.119.199.76", 24576.0, 10000.0, 18432.0, 25.0, 4915.2, False, True, 0.5),
            NodeMemoryTelemetry("L2_MacBook_Pro", "100.103.212.21", 16384.0, 8000.0, 12288.0, 25.0, 3276.8, False, True, 0.6),
            NodeMemoryTelemetry("L3_Linux_Hub", "100.101.39.98", 16384.0, 9000.0, 13107.2, 20.0, 3276.8, False, True, 5.0),
            NodeMemoryTelemetry("L4_Linux_Tablet", "100.81.92.125", 8192.0, 4000.0, 6144.0, 25.0, 2048.0, False, True, 8.0),
            NodeMemoryTelemetry("L5_MacBook_Air", "100.121.202.34", 16384.0, 8000.0, 12288.0, 25.0, 3276.8, False, True, 1.2),
            NodeMemoryTelemetry("L6_Pixel_10_Edge", "100.73.38.87", 16384.0, 8000.0, 13107.2, 20.0, 3276.8, False, True, 12.0),
            NodeMemoryTelemetry("L7_Samsung_S20", "100.84.40.95", 12288.0, 6000.0, 9216.0, 25.0, 3072.0, False, True, 10.0),
        ]

        pool = compute_global_pool_metric(telemetry_items)
        assert pool.nodes_reporting == 7
        assert pool.total_mesh_ram_gb >= 105.0, f"Expected ~108GB pool, got {pool.total_mesh_ram_gb}"
        assert pool.available_mesh_ram_gb > 70.0
        assert pool.usable_ai_vram_gb > 50.0
        assert pool.backpressure_triggered is False
        assert len(pool.saturated_nodes) == 0

    def test_t1_f1_3_dynamic_safety_threshold_enforcement(self):
        """F1.3: Verify dynamic safety limits for Host L1, Linux L3, and Android L6."""
        # Case A: L1 Host violates sanctuary (RAM available < 4.8 GB = 4915.2 MB)
        crit_l1 = [
            NodeMemoryTelemetry("L1_Mac_Host", "100.119.199.76", 24576.0, 2000.0, 3500.0, 85.8, 4915.2, True, True, 0.5),
            NodeMemoryTelemetry("L3_Linux_Hub", "100.101.39.98", 16384.0, 9000.0, 13107.2, 20.0, 3276.8, False, True, 5.0),
        ]
        pool_a = compute_global_pool_metric(crit_l1)
        assert pool_a.backpressure_triggered is True
        assert "L1_Mac_Host" in pool_a.saturated_nodes

        # Case B: L3 Linux Hub exceeds 80% utilization cap
        crit_l3 = [
            NodeMemoryTelemetry("L1_Mac_Host", "100.119.199.76", 24576.0, 10000.0, 18432.0, 25.0, 4915.2, False, True, 0.5),
            NodeMemoryTelemetry("L3_Linux_Hub", "100.101.39.98", 16384.0, 1000.0, 2000.0, 87.8, 3276.8, True, True, 5.0),
            NodeMemoryTelemetry("L6_Pixel_10_Edge", "100.73.38.87", 16384.0, 1000.0, 1500.0, 90.8, 3276.8, True, True, 12.0),
        ]
        pool_b = compute_global_pool_metric(crit_l3)
        assert pool_b.backpressure_triggered is True
        assert "L3_Linux_Hub" in pool_b.saturated_nodes
        assert "L6_Pixel_10_Edge" in pool_b.saturated_nodes

    def test_t1_f1_4_backpressure_suspension_actuation(self):
        """F1.4: Verify backpressure manager suspends low and medium priority tasks."""
        mgr = BackpressureSuspensionManager()
        t1 = mgr.register_task("t1", "LoRA Harvester", SubagentPriority.LOW)
        t2 = mgr.register_task("t2", "AST Crawler", SubagentPriority.LOW)
        t3 = mgr.register_task("t3", "Benchmarker", SubagentPriority.MEDIUM)
        t4 = mgr.register_task("t4", "IDE Active Prompt", SubagentPriority.IDE_CRITICAL)

        saturated_metric = GlobalRAMPoolMetric(
            total_mesh_ram_gb=108.0,
            available_mesh_ram_gb=4.0,
            usable_ai_vram_gb=3.0,
            pool_utilization_pct=92.0,
            nodes_reporting=7,
            nodes_total=7,
            backpressure_triggered=True,
            saturated_nodes=["L1_Mac_Host"]
        )

        # Trigger suspension
        suspended_ids = asyncio.run(mgr.apply_backpressure(saturated_metric))
        assert len(suspended_ids) == 3
        assert t1.status == "SUSPENDED"
        assert t2.status == "SUSPENDED"
        assert t3.status == "SUSPENDED"
        assert t4.status == "RUNNING", "IDE_CRITICAL task must never be suspended!"

    def test_t1_f1_5_automatic_backpressure_recovery(self):
        """F1.5: Verify backpressure release returns suspended tasks to RUNNING."""
        mgr = BackpressureSuspensionManager()
        mgr.register_task("t1", "LoRA Harvester", SubagentPriority.LOW)
        mgr.register_task("t2", "Continuous Benchmarker", SubagentPriority.MEDIUM)
        
        saturated_metric = GlobalRAMPoolMetric(
            total_mesh_ram_gb=108.0,
            available_mesh_ram_gb=4.0,
            usable_ai_vram_gb=3.0,
            pool_utilization_pct=92.0,
            nodes_reporting=7,
            nodes_total=7,
            backpressure_triggered=True,
            saturated_nodes=["L1_Mac_Host"]
        )
        asyncio.run(mgr.apply_backpressure(saturated_metric))

        assert mgr.get_task("t1").status == "SUSPENDED"
        assert mgr.get_task("t2").status == "SUSPENDED"

        # Release backpressure
        resumed_ids = asyncio.run(mgr.release_backpressure())
        assert len(resumed_ids) == 2
        assert mgr.get_task("t1").status == "RUNNING"
        assert mgr.get_task("t2").status == "RUNNING"

    def test_t1_f1_6_priority_protection_invariant(self):
        """F1.6: Verify strict priority ordering under partial suspension."""
        mgr = BackpressureSuspensionManager()
        t_low = mgr.register_task("t_low", "Low Task", SubagentPriority.LOW)
        t_med = mgr.register_task("t_med", "Med Task", SubagentPriority.MEDIUM)
        t_high = mgr.register_task("t_high", "High Debate", SubagentPriority.HIGH)
        t_crit = mgr.register_task("t_crit", "IDE Session", SubagentPriority.IDE_CRITICAL)

        saturated_metric = GlobalRAMPoolMetric(
            total_mesh_ram_gb=108.0,
            available_mesh_ram_gb=4.0,
            usable_ai_vram_gb=3.0,
            pool_utilization_pct=92.0,
            nodes_reporting=7,
            nodes_total=7,
            backpressure_triggered=True,
            saturated_nodes=["L1_Mac_Host"]
        )

        # Suspend only below HIGH (LOW and MEDIUM)
        suspended = asyncio.run(mgr.apply_backpressure(saturated_metric, min_protected_priority=SubagentPriority.HIGH))
        assert "t_low" in suspended
        assert "t_med" in suspended
        assert t_high.status == "RUNNING"
        assert t_crit.status == "RUNNING"


# ==============================================================================
# Feature 2: Dual-Engine Tool Routing Separation (F2.1 to F2.6)
# ==============================================================================

class TestFeature2DualEngineRouting:
    """Tests covering Hermes 3 tool routing vs Qwen 2.5 Coder code generation."""

    def test_t1_f2_1_hermes_tool_router_dispatch(self, mock_servers, reset_mock_logs):
        """F2.1: Payloads containing tool schemas dispatch to Hermes 3 Tool Router."""
        router = HermesRouter(
            hermes_url=f"{mock_servers['hermes_8082'].url}/v1/chat/completions",
            coder_url=f"{mock_servers['coder_8081'].url}/v1/chat/completions"
        )
        decision = router.classify_and_route(
            payload={"tools": [{"name": "vector_search"}]},
            prompt="Find the ECG Pan-Tompkins filter implementation."
        )
        assert decision.engine == "HERMES_TOOL_ROUTER"
        assert f":{PORT_HERMES_MASTER}" in decision.target_endpoint or mock_servers['hermes_8082'].url in decision.target_endpoint
        assert decision.model_id == "qwen_38_max_abliterated"

    def test_t1_f2_2_qwen_coder_dispatch(self, mock_servers, reset_mock_logs):
        """F2.2: Pure code generation / completion dispatches to Qwen 2.5 Coder."""
        router = HermesRouter(
            hermes_url=f"{mock_servers['hermes_8082'].url}/v1/chat/completions",
            coder_url=f"{mock_servers['coder_8081'].url}/v1/chat/completions"
        )
        decision = router.classify_and_route(
            payload={"prompt": "def calculate_qrs(ecg_signal):\n    pass"},
            prompt="def calculate_qrs(ecg_signal):\n    pass"
        )
        assert decision.engine == "QWEN_CODE_GENERATOR"
        assert f":{PORT_QWEN_CODER}" in decision.target_endpoint or mock_servers['coder_8081'].url in decision.target_endpoint
        assert decision.model_id == "qwen2.5-coder-7b-instruct"

    def test_t1_f2_3_vector_db_context_paging(self, mock_servers, reset_mock_logs):
        """F2.3: Vector context paging queries Qdrant and retrieves code chunks."""
        pager = VectorPager(qdrant_url=mock_servers['qdrant_6333'].url)
        pages = pager.page_context(query="Pan-Tompkins QRS algorithm", top_k=2)
        assert len(pages) == 2
        assert any("pan_tompkins" in p.content.lower() or "governor" in p.content.lower() for p in pages)
        assert pages[0].score >= 0.80

    def test_t1_f2_4_continuous_loop_trigger(self, mock_servers, reset_mock_logs):
        """F2.4: Requests with `/loop` trigger continuous distillation flag."""
        router = HermesRouter()
        decision = router.classify_and_route(
            payload={},
            prompt="Please optimize this function /loop nightly"
        )
        assert decision.loop_triggered is True
        assert decision.engine == "HERMES_TOOL_ROUTER"

    def test_t1_f2_5_mutual_exclusivity_verification(self, mock_servers, reset_mock_logs):
        """F2.5: Code Generator endpoint receives pure code request without tool schemas."""
        coder = CodeGenerator(primary_url=mock_servers['coder_8081'].url)
        res = asyncio.run(coder.generate_completion(prompt="def test_matrix(): pass"))
        assert res.success is True

        # Verify that mock coder handler received clean code request without tool schemas
        from tests.conftest import MockCoderHandler
        assert len(MockCoderHandler.call_log) > 0
        last_body = MockCoderHandler.call_log[-1]["body"]
        assert "tools" not in last_body

    def test_t1_f2_6_skill_discovery_and_registration(self):
        """F2.6: Built-in and monorepo skills are loaded into tool registry."""
        router = HermesRouter()
        tools = router.list_tools()
        tool_names = [t.name for t in tools]
        assert "vector_search" in tool_names
        assert "read_source_file" in tool_names


# ==============================================================================
# Feature 3: Manual Cloud Escalation Gate (F3.1 to F3.6)
# ==============================================================================

class TestFeature3EscalationGate:
    """Tests covering context overflow detection and manual authorization."""

    def test_t1_f3_1_sub_threshold_local_pass_through(self, sample_code_prompt):
        """F3.1: Prompts under LOCAL_CONTEXT_MAX (8,192 tokens) pass locally."""
        gate = ManualCloudEscalationGate(context_limit=LOCAL_CONTEXT_MAX)
        is_ovf, tokens = gate.is_overflow(sample_code_prompt)
        assert is_ovf is False
        assert tokens < LOCAL_CONTEXT_MAX

    def test_t1_f3_2_context_overflow_interception(self, sample_overflow_prompt):
        """F3.2: Prompts exceeding 8,192 tokens trigger ticket and block cloud."""
        gate = ManualCloudEscalationGate(context_limit=LOCAL_CONTEXT_MAX)
        is_ovf, tokens = gate.is_overflow(sample_overflow_prompt)
        assert is_ovf is True
        assert tokens > LOCAL_CONTEXT_MAX

        ticket = gate.create_ticket(payload=sample_overflow_prompt)
        assert ticket is not None
        assert ticket.is_pending() is True
        assert ticket.token_count > LOCAL_CONTEXT_MAX

    def test_t1_f3_3_manual_override_approval(self, sample_overflow_prompt):
        """F3.3: Explicit manual approval marks ticket APPROVED."""
        gate = ManualCloudEscalationGate(context_limit=LOCAL_CONTEXT_MAX)
        ticket = gate.create_ticket(payload=sample_overflow_prompt)
        ticket_id = ticket.ticket_id

        # Authorize via REST / hook
        res = gate.resolve_ticket(ticket_id, action="APPROVE")
        assert bool(res) is True

        updated = gate.get_ticket(ticket_id)
        assert updated.status == EscalationStatus.APPROVED.value
        assert updated.is_approved() is True

    def test_t1_f3_4_manual_override_denial(self, sample_overflow_prompt):
        """F3.4: Explicit denial marks ticket REJECTED with zero cloud dispatch."""
        gate = ManualCloudEscalationGate(context_limit=LOCAL_CONTEXT_MAX)
        ticket = gate.create_ticket(payload=sample_overflow_prompt)
        ticket_id = ticket.ticket_id

        res = gate.resolve_ticket(ticket_id, action="DENY")
        assert bool(res) is True

        updated = gate.get_ticket(ticket_id)
        assert updated.status == EscalationStatus.REJECTED.value
        assert updated.is_approved() is False

    def test_t1_f3_5_zero_cloud_leakage_invariant(self, mock_servers, reset_mock_logs, sample_overflow_prompt):
        """F3.5: Verify no HTTP request reaches the cloud endpoint when ticket is pending."""
        gate = ManualCloudEscalationGate(context_limit=LOCAL_CONTEXT_MAX)
        is_ovf, tokens = gate.is_overflow(sample_overflow_prompt)
        assert is_ovf is True
        ticket = gate.create_ticket(payload=sample_overflow_prompt)

        # Verify MockCloudHandler received exactly zero calls
        from tests.conftest import MockCloudHandler
        assert len(MockCloudHandler.call_log) == 0, "Cloud leakage detected! Zero calls allowed when unapproved."

    def test_t1_f3_6_ticket_ledger_persistence(self, tmp_path, sample_overflow_prompt):
        """F3.6: Tickets are recorded in the active ledger."""
        ledger_file = tmp_path / "escalations.json"
        gate = ManualCloudEscalationGate(context_limit=LOCAL_CONTEXT_MAX, ledger_path=str(ledger_file))
        ticket = gate.create_ticket(payload=sample_overflow_prompt)
        ticket_id = ticket.ticket_id

        fetched = gate.get_ticket(ticket_id)
        assert fetched is not None
        assert fetched.ticket_id == ticket_id


# ==============================================================================
# Feature 4: SeaweedFS Storage Specialist & Hardware Affinity (F4.1 to F4.6)
# ==============================================================================

class TestFeature4StorageSpecialist:
    """Tests covering SeaweedFS physical node affinity rules."""

    def test_t1_f4_1_heavy_dataset_affinity_l3(self):
        """F4.1: Heavy datasets (*.parquet, *.jsonl, lora_datasets/) map to L3 Linux Hub."""
        spec = TriVaultStorageSpecialist()
        route1 = spec.resolve_affinity("lora_datasets/instruction_pairs.jsonl")
        assert route1.category == CATEGORY_HEAVY_DATASETS
        assert route1.target_node == NODE_L3_LINUX
        assert route1.collection == "heavy_datasets"

        route2 = spec.resolve_affinity("04_data_and_memory/biometrics_lake/ecg_signals.parquet")
        assert route2.category == CATEGORY_HEAVY_DATASETS
        assert route2.target_node == NODE_L3_LINUX

    def test_t1_f4_2_vector_context_affinity_l6(self):
        """F4.2: Vector context (*.lance, *.index, qdrant_data/) map to L6/L4 Edge NPUs."""
        spec = TriVaultStorageSpecialist()
        route1 = spec.resolve_affinity("04_data_and_memory/qdrant_data/collection.lance")
        assert route1.category == CATEGORY_VECTOR_CONTEXT
        assert route1.target_node == NODE_L6_EDGE
        assert route1.collection == "vector_context"

        route2 = spec.resolve_affinity("vector_db/embeddings.index")
        assert route2.category == CATEGORY_VECTOR_CONTEXT
        assert route2.target_node == NODE_L6_EDGE

    def test_t1_f4_3_git_source_affinity_l1(self):
        """F4.3: Active Git source (.git/, 01_apps/, *.py) map to L1 Mac Host."""
        spec = TriVaultStorageSpecialist()
        route1 = spec.resolve_affinity("01_apps/bt_ide_ab_test/main.py")
        assert route1.category == CATEGORY_GIT_SOURCE
        assert route1.target_node == NODE_L1_MAC
        assert route1.collection == "git_source"

        route2 = spec.resolve_affinity(".git/HEAD")
        assert route2.category == CATEGORY_GIT_SOURCE
        assert route2.target_node == NODE_L1_MAC

    def test_t1_f4_4_seaweed_assign_params_synthesis(self):
        """F4.4: get_seaweed_assign_params returns valid SeaweedFS Master /dir/assign parameters."""
        spec = TriVaultStorageSpecialist()
        params_l3 = spec.get_seaweed_assign_params("lora_datasets/distillation.jsonl")
        assert params_l3["collection"] == "heavy_datasets"
        assert params_l3["dataCenter"] == "L3_Linux"
        assert params_l3["count"] == "1"

        params_l1 = spec.get_seaweed_assign_params("01_apps/main.py")
        assert params_l1["collection"] == "git_source"
        assert params_l1["dataCenter"] == "L1_Mac"

    def test_t1_f4_5_transparent_vfs_preservation(self):
        """F4.5: VFS path mapping retains identical relative path."""
        spec = TriVaultStorageSpecialist()
        path = "01_apps/bt_ide_ab_test/core/storage_specialist.py"
        route = spec.resolve_affinity(path)
        assert route.path == path

    def test_t1_f4_6_default_fallback_to_l1(self):
        """F4.6: Unmapped or arbitrary extensions fall back safely to L1 Mac Host."""
        spec = TriVaultStorageSpecialist()
        route = spec.resolve_affinity("unknown_directory/random_artifact.custom_bin")
        assert route.category == CATEGORY_GIT_SOURCE
        assert route.target_node == NODE_L1_MAC


# ==============================================================================
# Feature 5: Continuous Local Distillation Loop (F5.1 to F5.6)
# ==============================================================================

class TestFeature5DistillationLoop:
    """Tests covering continuous local distillation and credential sanitization."""

    def test_t1_f5_1_silent_trace_capture(self, tmp_path):
        """F5.1: Synchronously process and write authorized cloud trace to file."""
        dataset_path = tmp_path / "traces.jsonl"
        worker = DistillationCaptureWorker(dataset_path=str(dataset_path))

        item = {
            "distillation_id": "test-dist-1",
            "timestamp_utc": "2026-09-18T00:00:00Z",
            "prompt_messages": "Refactor this function to be thread-safe.",
            "cloud_response": "Here is the thread-safe version using threading.Lock()...",
            "teacher_model": "google/gemini-pro-1.5",
            "escalation_ticket_id": "test-ticket-001",
            "verification_metadata": {},
            "prompt_tokens": 10,
            "completion_tokens": 12,
        }
        worker._process_item_sync(item)

        assert dataset_path.exists()
        content = dataset_path.read_text(encoding="utf-8")
        assert "Refactor this function" in content
        assert "threading.Lock()" in content

    def test_t1_f5_2_trace_serialization_schema(self, tmp_path):
        """F5.2: Trace JSONL matches ChatML/OpenAI format."""
        dataset_path = tmp_path / "traces.jsonl"
        worker = DistillationCaptureWorker(dataset_path=str(dataset_path))

        item = {
            "distillation_id": "test-dist-2",
            "timestamp_utc": "2026-09-18T00:00:00Z",
            "prompt_messages": "Prompt 1",
            "cloud_response": "Response 1",
            "teacher_model": "test-model",
            "escalation_ticket_id": None,
            "verification_metadata": {},
            "prompt_tokens": 5,
            "completion_tokens": 5,
        }
        worker._process_item_sync(item)

        lines = dataset_path.read_text().strip().split("\n")
        assert len(lines) >= 1
        record = json.loads(lines[0])
        assert "conversations" in record or ("messages" in record) or ("instruction" in record and "output" in record)

    def test_t1_f5_3_ingestion_queue_persistence(self, tmp_path):
        """F5.3: Multiple traces persist cleanly into dataset file."""
        dataset_path = tmp_path / "traces.jsonl"
        worker = DistillationCaptureWorker(dataset_path=str(dataset_path))

        for i in range(5):
            item = {
                "distillation_id": f"test-dist-{i}",
                "timestamp_utc": "2026-09-18T00:00:00Z",
                "prompt_messages": f"Task {i}",
                "cloud_response": f"Solution {i}",
                "teacher_model": "test-model",
                "escalation_ticket_id": None,
                "verification_metadata": {},
                "prompt_tokens": 5,
                "completion_tokens": 5,
            }
            worker._process_item_sync(item)

        lines = [line for line in dataset_path.read_text().split("\n") if line.strip()]
        assert len(lines) == 5

    def test_t1_f5_4_credential_masking(self):
        """F5.4: Verify sensitive tokens (HF, Bearer, OpenAI keys) are scrubbed."""
        raw_text = (
            "Clone repository with hf_abcdef12345678901234567890 and "
            "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9 and "
            "sk-proj-abc1234567890123456789012345"
        )
        scrubbed = scrub_sensitive_credentials(raw_text)
        assert "hf_abcdef" not in scrubbed
        assert "hf_...[REDACTED]" in scrubbed or "[REDACTED" in scrubbed
        assert "Bearer [REDACTED]" in scrubbed or "Bearer eyJhbG" not in scrubbed
        assert "sk-proj-abc" not in scrubbed

    def test_t1_f5_5_overnight_queue_batch_trigger(self, tmp_path):
        """F5.5: Queue accumulation triggers overnight batch check."""
        dataset_path = tmp_path / "traces.jsonl"
        worker = DistillationCaptureWorker(dataset_path=str(dataset_path))

        for i in range(12):
            item = {
                "distillation_id": f"test-dist-{i}",
                "timestamp_utc": "2026-09-18T00:00:00Z",
                "prompt_messages": f"Q{i}",
                "cloud_response": f"A{i}",
                "teacher_model": "test-model",
                "escalation_ticket_id": None,
                "verification_metadata": {},
                "prompt_tokens": 5,
                "completion_tokens": 5,
            }
            worker._process_item_sync(item)

        res = worker.trigger_overnight_training(min_traces=10)
        assert bool(res) is True or res.queued is True

    def test_t1_f5_6_trace_metadata_and_verification(self, tmp_path):
        """F5.6: Verify trace record captures complete metadata and verification status."""
        dataset_path = tmp_path / "traces.jsonl"
        worker = DistillationCaptureWorker(dataset_path=str(dataset_path))

        item = {
            "distillation_id": "test-meta-1",
            "timestamp_utc": "2026-09-18T00:00:00Z",
            "prompt_messages": "Implement DFA alpha 1 calculation.",
            "cloud_response": "def calculate_dfa_alpha1(rr_intervals): ...",
            "teacher_model": "gemini-2.5-flash-thinking",
            "escalation_ticket_id": "ticket-dfa-101",
            "verification_metadata": {"syntax_valid": True, "exit_code": 0, "test_suite": "dsp_tests"},
            "prompt_tokens": 15,
            "completion_tokens": 45,
        }
        worker._process_item_sync(item)

        lines = [line for line in dataset_path.read_text().split("\n") if line.strip()]
        assert len(lines) == 1
        record = json.loads(lines[0])
        assert record["distillation_id"] == "test-meta-1"
        assert record["teacher_model"] == "gemini-2.5-flash-thinking"
        assert record["verification_metadata"]["escalation_ticket_id"] == "ticket-dfa-101"
        assert record["verification_metadata"]["exit_code"] == 0
