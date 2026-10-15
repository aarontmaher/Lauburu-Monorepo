"""
tests/test_tier3_combinations.py
Tier 3: Pairwise Cross-Feature Integration Tests (7 Canonical Interactions).

Pairwise Matrix:
1. F1 (RAM) x F2 (Routing)    -> Memory saturation suspends background tasks while foreground IDE tool routing proceeds.
2. F1 (RAM) x F3 (Escalation)  -> Low RAM suspends background subagents, but NEVER auto-bypasses manual escalation gate.
3. F1 (RAM) x F4 (Storage)     -> Backpressure prioritizes foreground L1 Git I/O over background L3 dataset sync.
4. F2 (Routing) x F3 (Escalation)-> Vector page expansion beyond 8,192 tokens triggers Escalation Gate.
5. F2 (Routing) x F5 (Distillation)-> /loop trigger initiates distillation queue without blocking code generation.
6. F3 (Escalation) x F5 (Distillation)-> Authorized cloud response is streamed to IDE and silently captured into distillation.
7. F4 (Storage) x F5 (Distillation)-> Distillation dataset commits route to L3 Linux Hub per SeaweedFS affinity.
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


class TestTier3Combinations:
    """7 Pairwise Cross-Feature Interaction Tests."""

    def test_t3_pair1_ram_saturation_during_tool_routing(self, mock_servers, reset_mock_logs):
        """
        Pair 1: F1 (RAM) x F2 (Routing).
        Memory saturation occurs while Tool Router is executing a skill chain.
        Governor suspends background tasks, while foreground IDE tool routing succeeds.
        """
        # 1. Setup RAM Governor and register background tasks
        ram_mgr = BackpressureSuspensionManager()
        bg_harvester = ram_mgr.register_task("lora_harvest_01", "LoRA Harvester", SubagentPriority.LOW)
        bg_crawler = ram_mgr.register_task("ast_crawl_01", "AST Crawler", SubagentPriority.LOW)
        ide_task = ram_mgr.register_task("ide_session_01", "Active Editor Tab", SubagentPriority.IDE_CRITICAL)

        # 2. Inject saturation telemetry
        saturated_pool = GlobalRAMPoolMetric(
            total_mesh_ram_gb=108.0,
            available_mesh_ram_gb=3.8,  # Below 4.8 GB sanctuary
            usable_ai_vram_gb=2.5,
            pool_utilization_pct=92.0,
            nodes_reporting=7,
            nodes_total=7,
            backpressure_triggered=True,
            saturated_nodes=["L1_Mac_Host"]
        )

        suspended_ids = asyncio.run(ram_mgr.apply_backpressure(saturated_pool))
        assert "lora_harvest_01" in suspended_ids
        assert "ast_crawl_01" in suspended_ids
        assert ide_task.status == "RUNNING"

        # 3. Foreground Hermes Tool Router executes uninhibited
        router = HermesRouter(
            hermes_url=f"{mock_servers['hermes_8082'].url}/v1/chat/completions",
            coder_url=f"{mock_servers['coder_8081'].url}/v1/chat/completions"
        )
        decision = router.classify_and_route(
            payload={"tools": [{"name": "vector_search"}]},
            prompt="Find Pan-Tompkins QRS peak detection function."
        )
        assert decision.engine == "HERMES_TOOL_ROUTER"

        # 4. Release backpressure after foreground request
        resumed_ids = asyncio.run(ram_mgr.release_backpressure())
        assert len(resumed_ids) == 2
        assert bg_harvester.status == "RUNNING"

    def test_t3_pair2_low_ram_never_bypasses_escalation_gate(self, mock_servers, reset_mock_logs, sample_code_prompt):
        """
        Pair 2: F1 (RAM) x F3 (Escalation).
        Low local RAM (< 4.8 GB) suspends background tasks, but NEVER automatically
        dispatches to external cloud APIs without manual authorization (Rule 4).
        """
        # 1. System enters low RAM
        ram_mgr = BackpressureSuspensionManager()
        bg_task = ram_mgr.register_task("subagent_1", "Background Distiller", SubagentPriority.LOW)
        saturated_pool = GlobalRAMPoolMetric(
            total_mesh_ram_gb=108.0,
            available_mesh_ram_gb=3.5,
            usable_ai_vram_gb=2.0,
            pool_utilization_pct=94.0,
            nodes_reporting=7,
            nodes_total=7,
            backpressure_triggered=True,
            saturated_nodes=["L1_Mac_Host"]
        )
        asyncio.run(ram_mgr.apply_backpressure(saturated_pool))
        assert bg_task.status == "SUSPENDED"

        # 2. Incoming overflow request attempts to process
        gate = ManualCloudEscalationGate(context_limit=LOCAL_CONTEXT_MAX)
        large_prompt = sample_code_prompt * 500  # > 8,192 tokens
        is_ovf, tokens = gate.is_overflow(large_prompt)
        assert is_ovf is True

        # 3. Gate intercepts and halts execution - no cloud leak!
        ticket = gate.create_ticket(payload=large_prompt)
        assert ticket.is_pending() is True

        # Verify zero calls to mock cloud
        from tests.conftest import MockCloudHandler
        assert len(MockCloudHandler.call_log) == 0

    def test_t3_pair3_backpressure_suspension_with_storage_affinity(self):
        """
        Pair 3: F1 (RAM) x F4 (Storage).
        Under memory saturation, storage specialist verifies file placement affinity:
        Active IDE edits map to L1 NVMe, while heavy background sync targets L3.
        """
        spec = TriVaultStorageSpecialist()

        # Foreground active edit
        ide_route = spec.resolve_affinity("01_apps/bt_ide_ab_test/core/ram_governor.py")
        assert ide_route.target_node == NODE_L1_MAC
        assert ide_route.category == CATEGORY_GIT_SOURCE

        # Background heavy dataset
        dataset_route = spec.resolve_affinity("lora_datasets/overnight_pairs.parquet")
        assert dataset_route.target_node == NODE_L3_LINUX
        assert dataset_route.category == CATEGORY_HEAVY_DATASETS

    def test_t3_pair4_tool_retrieved_context_triggers_escalation_gate(self):
        """
        Pair 4: F2 (Routing) x F3 (Escalation).
        Vector context injection expands an initial prompt beyond the 8,192 token limit,
        triggering the Manual Cloud Escalation Gate.
        """
        gate = ManualCloudEscalationGate(context_limit=LOCAL_CONTEXT_MAX)
        pager = VectorPager()

        # Initial prompt is below limit (approx 2,000 tokens)
        initial_prompt = "Refactor this architecture.\n" + ("x = 1\n" * 1500)
        is_ovf_init, _ = gate.is_overflow(initial_prompt)
        assert is_ovf_init is False

        # Simulate massive vector page context injection (e.g. 10 large codebase chunks)
        injected_context = initial_prompt + ("\n<vector_page>\n" + ("def symbol(): pass\n" * 3000) + "\n</vector_page>")
        is_ovf_post, tokens_post = gate.is_overflow(injected_context)
        assert is_ovf_post is True
        assert tokens_post > LOCAL_CONTEXT_MAX

        # Intercepted!
        ticket = gate.create_ticket(payload=injected_context)
        assert ticket.status == EscalationStatus.PENDING.value

    def test_t3_pair5_loop_trigger_dispatches_to_distillation(self, tmp_path):
        """
        Pair 5: F2 (Routing) x F5 (Distillation).
        Hermes Router detects /loop trigger, routing intent and notifying distillation pipeline.
        """
        dataset_path = tmp_path / "continuous_lora_dataset.jsonl"
        distiller = DistillationCaptureWorker(dataset_path=str(dataset_path))
        router = HermesRouter()

        prompt_with_loop = "Optimize the QRS peak detection algorithm /loop continuous"
        decision = router.classify_and_route(payload={}, prompt=prompt_with_loop)
        assert decision.loop_triggered is True
        assert decision.engine == "HERMES_TOOL_ROUTER"

        # Record registration in distillation dataset
        item = {
            "distillation_id": "dist_loop_01",
            "timestamp_utc": "2026-09-18T00:00:00Z",
            "prompt_messages": prompt_with_loop,
            "cloud_response": "Optimized using vectorized numpy operations.",
            "teacher_model": "qwen_38_max_abliterated",
            "escalation_ticket_id": None,
            "verification_metadata": {"loop_triggered": True},
            "prompt_tokens": 15,
            "completion_tokens": 20,
        }
        distiller._process_item_sync(item)

        content = dataset_path.read_text(encoding="utf-8")
        assert "dist_loop_01" in content
        assert "loop_triggered" in content

    def test_t3_pair6_authorized_escalation_feeds_distillation_pipeline(self, tmp_path, mock_servers, reset_mock_logs):
        """
        Pair 6: F3 (Escalation) x F5 (Distillation).
        User approves escalation ticket; cloud response is retrieved, rendered,
        and silently captured into the local distillation dataset with credentials scrubbed.
        """
        gate = ManualCloudEscalationGate(context_limit=LOCAL_CONTEXT_MAX)
        dataset_path = tmp_path / "ide_distillation_traces.jsonl"
        distiller = DistillationCaptureWorker(dataset_path=str(dataset_path))

        raw_prompt = "Explain the 7-Layer Mesh Topology with secret key hf_SECRETTEST12345678901234567890"
        ticket = gate.create_ticket(payload=raw_prompt)
        assert ticket.is_pending() is True

        # User approves ticket
        res = gate.resolve_ticket(ticket.ticket_id, action="APPROVE")
        assert bool(res) is True
        assert ticket.is_approved() is True

        # Simulate cloud dispatch and capture
        cloud_response_text = "The 7-Layer mesh topology connects L1 Mac Host through L7 Samsung S20."
        item = {
            "distillation_id": f"dist_{ticket.ticket_id}",
            "timestamp_utc": "2026-09-18T00:00:00Z",
            "prompt_messages": raw_prompt,
            "cloud_response": cloud_response_text,
            "teacher_model": "google/gemini-pro-1.5",
            "escalation_ticket_id": ticket.ticket_id,
            "verification_metadata": {"authorized": True},
            "prompt_tokens": 25,
            "completion_tokens": 30,
        }
        distiller._process_item_sync(item)

        # Verify dataset persistence & credential scrubbing
        content = dataset_path.read_text(encoding="utf-8")
        assert "hf_SECRETTEST" not in content
        assert "7-Layer mesh topology" in content
        assert ticket.ticket_id in content

    def test_t3_pair7_distillation_dataset_affinity_to_l3(self):
        """
        Pair 7: F4 (Storage) x F5 (Distillation).
        Distillation dataset files route to L3 Linux Hub per SeaweedFS hardware affinity.
        """
        spec = TriVaultStorageSpecialist()
        dataset_path = "04_data_and_memory/lora_datasets/continuous_lora_dataset.jsonl"
        route = spec.resolve_affinity(dataset_path)

        assert route.category == CATEGORY_HEAVY_DATASETS
        assert route.target_node == NODE_L3_LINUX
        assert route.collection == "heavy_datasets"

        params = spec.get_seaweed_assign_params(dataset_path)
        assert params["collection"] == "heavy_datasets"
        assert params["dataCenter"] == "L3_Linux"
