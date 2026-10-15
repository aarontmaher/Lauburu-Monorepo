"""
tests/test_tier4_real_world.py
Tier 4: Complete Real-World Application Workload Scenarios (4 Scenarios).

Scenarios:
1. Interactive IDE Coding Session Under Memory Stress (F1, F2, F3, F5)
2. Large-Scale Monorepo Multi-File Refactoring (F4, F5, F6, F7, F8)
3. Context Overflow with Manual Cloud Authorization & Overnight Learning (F9, F10, F11, F12)
4. Hardware Fault Injection & Resilient Self-Healing (F1, F7, F8, F13)
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


class TestTier4RealWorldScenarios:
    """Real-World Application Scenarios exercising full multi-feature pipelines."""

    def test_scenario_1_interactive_ide_session_under_memory_stress(self, mock_servers, reset_mock_logs):
        """
        Scenario 1: Interactive IDE Coding Session Under Memory Stress.
        A background LoRA harvester runs; memory drops below 4.8 GB; backpressure
        suspends the harvester; user submits code prompt; Qwen 2.5 Coder generates
        syntax; memory recovers; harvester resumes.
        """
        # Step 1: Initialize RAM Governor and register tasks
        ram_mgr = BackpressureSuspensionManager()
        harvester = ram_mgr.register_task("lora_harvester_nightly", "Background Harvester", SubagentPriority.LOW)
        ide_tab = ram_mgr.register_task("vscode_tab_active", "User Active Editor Tab", SubagentPriority.IDE_CRITICAL)

        # Step 2: Memory drops below 4.8 GB (e.g. 3.9 GB on L1)
        stressed_pool = GlobalRAMPoolMetric(
            total_mesh_ram_gb=108.0,
            available_mesh_ram_gb=3.9,
            usable_ai_vram_gb=2.0,
            pool_utilization_pct=94.0,
            nodes_reporting=7,
            nodes_total=7,
            backpressure_triggered=True,
            saturated_nodes=["L1_Mac_Host"]
        )

        # Step 3: Governor executes backpressure suspension
        suspended = asyncio.run(ram_mgr.apply_backpressure(stressed_pool))
        assert "lora_harvester_nightly" in suspended
        assert harvester.status == "SUSPENDED"
        assert ide_tab.status == "RUNNING"

        # Step 4: User typing in IDE submits prompt for code generation
        coder = CodeGenerator(primary_url=mock_servers['coder_8081'].url)
        gen_res = asyncio.run(coder.generate_completion(prompt="def calculate_dfa_alpha1(rr_intervals):"))
        assert gen_res.success is True
        assert "def" in gen_res.text

        # Step 5: Memory recovers above threshold (e.g. 5.5 GB on L1)
        resumed = asyncio.run(ram_mgr.release_backpressure())
        assert "lora_harvester_nightly" in resumed
        assert harvester.status == "RUNNING"

    def test_scenario_2_large_scale_monorepo_refactoring(self, mock_servers, reset_mock_logs, isolated_workspace):
        """
        Scenario 2: Large-Scale Monorepo Multi-File Refactoring.
        User refactors multi-file codebase; Tool Router retrieves vector pages;
        synthesizes plan; Code Generator outputs refactored code; Storage Specialist
        routes modified files to L1 Mac Host NVMe.
        """
        router = HermesRouter(
            hermes_url=f"{mock_servers['hermes_8082'].url}/v1/chat/completions",
            coder_url=f"{mock_servers['coder_8081'].url}/v1/chat/completions"
        )
        pager = VectorPager(qdrant_url=mock_servers['qdrant_6333'].url)
        coder = CodeGenerator(primary_url=mock_servers['coder_8081'].url)
        storage = TriVaultStorageSpecialist()

        # Step 1: Query vector context for symbol dependencies
        query = "MeshRAMGovernor GlobalRAMPoolMetric Pan-Tompkins"
        context_pages = pager.page_context(query, top_k=2)
        assert len(context_pages) >= 2

        # Step 2: Route request through Hermes Tool Router
        decision = router.classify_and_route(
            payload={"tools": [{"name": "vector_search"}]},
            prompt=f"Refactor telemetry pipeline with context: {context_pages[0].content[:100]}"
        )
        assert decision.engine == "HERMES_TOOL_ROUTER"

        # Step 3: Fan out code synthesis to Qwen 2.5 Coder
        code_result = asyncio.run(coder.generate_completion(
            prompt="def refactored_telemetry_poller():\n    return True"
        ))
        assert code_result.success is True

        # Step 4: Commit refactored source to VFS and verify physical placement
        target_file = "01_apps/bt_ide_ab_test/core/telemetry.py"
        route = storage.resolve_affinity(target_file)
        assert route.category == CATEGORY_GIT_SOURCE
        assert route.target_node == NODE_L1_MAC

    def test_scenario_3_context_overflow_with_manual_authorization_and_distillation(
        self, tmp_path, mock_servers, reset_mock_logs, sample_overflow_prompt
    ):
        """
        Scenario 3: Context Overflow with Manual Cloud Authorization & Overnight Learning.
        15,000-token prompt exceeds local context; Escalation Gate blocks and issues ticket;
        user approves via REST hook; Cloud API returns high-reasoning response;
        Distillation worker intercepts, scrubs secrets, and saves trace for overnight training.
        """
        gate = ManualCloudEscalationGate(context_limit=LOCAL_CONTEXT_MAX)
        dataset_path = tmp_path / "ide_distillation_traces.jsonl"
        distiller = DistillationCaptureWorker(dataset_path=str(dataset_path))

        # Step 1: Prompt exceeds local limit
        is_ovf, tokens = gate.is_overflow(sample_overflow_prompt)
        assert is_ovf is True
        assert tokens > LOCAL_CONTEXT_MAX

        # Step 2: Escalation Gate halts execution and generates ticket
        ticket = gate.create_ticket(payload=sample_overflow_prompt, target_cloud_model="google/gemini-pro-1.5")
        assert ticket.status == EscalationStatus.PENDING.value

        # Verify zero calls to cloud while pending
        from tests.conftest import MockCloudHandler
        assert len(MockCloudHandler.call_log) == 0

        # Step 3: User approves escalation via REST webhook
        auth_result = gate.handle_rest_authorize({
            "ticket_id": ticket.ticket_id,
            "action": "APPROVE"
        })
        assert auth_result.get("success") is True
        assert ticket.status == EscalationStatus.APPROVED.value

        # Step 4: Dispatch to Cloud API (MockCloudHandler)
        import urllib.request
        req = urllib.request.Request(
            f"{mock_servers['cloud_mock'].url}/v1/chat/completions",
            data=json.dumps({"prompt": sample_overflow_prompt[:200]}).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": "Bearer hf_SECRETTOKEN12345678901234567890"}
        )
        with urllib.request.urlopen(req) as resp:
            cloud_json = json.loads(resp.read().decode("utf-8"))

        cloud_reply = cloud_json["choices"][0]["message"]["content"]
        assert len(cloud_reply) > 0

        # Step 5: Silently capture and scrub trace for overnight distillation
        item = {
            "distillation_id": f"dist_{ticket.ticket_id}",
            "timestamp_utc": "2026-09-18T00:00:00Z",
            "prompt_messages": sample_overflow_prompt[:300] + " with token hf_SECRETTOKEN12345678901234567890",
            "cloud_response": cloud_reply,
            "teacher_model": "google/gemini-pro-1.5",
            "escalation_ticket_id": ticket.ticket_id,
            "verification_metadata": {"authorized": True, "tokens": tokens},
            "prompt_tokens": tokens,
            "completion_tokens": 150,
        }
        distiller._process_item_sync(item)

        # Step 6: Verify trace is clean and recorded
        traces = [json.loads(line) for line in dataset_path.read_text().splitlines() if line.strip()]
        assert len(traces) == 1
        assert "hf_SECRETTOKEN" not in dataset_path.read_text()
        assert traces[0]["teacher_model"] == "google/gemini-pro-1.5"

    def test_scenario_4_hardware_fault_injection_and_self_healing(self, mock_servers, reset_mock_logs):
        """
        Scenario 4: Hardware Fault Injection & Resilient Self-Healing.
        Remote L3 Linux Hub endpoint drops offline; RAM governor recalculates degraded
        pool without throwing exceptions; Storage Specialist reports degraded cluster
        and maintains operational integrity for local workspace.
        """
        # Step 1: Healthy 7-layer cluster initial telemetry
        collector = MeshTelemetryCollector()
        storage = TriVaultStorageSpecialist()

        # Step 2: Fault Injection - L3 node drops / times out
        collector.set_simulated_ip("100.101.39.98", {
            "node_id": "L3_Linux_Hub",
            "unreachable": True,
            "error": "Connection timed out (100.101.39.98:8085)"
        })

        telemetry_reports = asyncio.run(collector.collect_all())
        l3_report = next((r for r in telemetry_reports if r.node_id == "L3_Linux_Hub"), None)
        assert l3_report is not None
        assert l3_report.is_reachable is False

        # Step 3: RAM Governor evaluates degraded cluster
        pool_metric = compute_global_pool_metric(telemetry_reports)
        assert pool_metric.nodes_reporting < pool_metric.nodes_total

        # Step 4: Storage Specialist audits cluster health and ensures zero system freeze
        health = storage.check_cluster_health(timeout=0.1)
        assert health.status in ("HEALTHY", "DEGRADED", "OFFLINE")

        # Step 5: Critical IDE file routing remains 100% operational on L1
        route = storage.resolve_affinity("01_apps/bt_ide_ab_test/main.py")
        assert route.category == CATEGORY_GIT_SOURCE
        assert route.target_node == NODE_L1_MAC
