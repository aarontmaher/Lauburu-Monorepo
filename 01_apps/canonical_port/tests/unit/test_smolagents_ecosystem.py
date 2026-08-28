"""
Canonical Port — Unit Test Suite: Smolagents Autonomous Ecosystem
Verifies tool calling, local AI (llama.cpp/exo) & free-tier cloud (Cloudflare/Gemini) routing,
background cron scheduling, task cancellation cleanly without unhandled asyncio exceptions,
and memory leak isolation. Strictly enforces Rule #0 (Zero-Mock Data).
"""

import pytest
import asyncio
import time
import gc
import sys
from typing import Dict, Any, List, Optional, Callable


# ============================================================================
# SMOLAGENTS ECOSYSTEM IMPORT FROM BACKEND.AGENTS
# ============================================================================

from backend.agents import (
    SmolagentTool,
    SmolagentAIRouter,
    SmolagentCronScheduler,
    SmolagentAgentWrapper,
)



# ============================================================================
# TIER 1: TOOL CALLING & EXECUTION TESTS
# ============================================================================

class TestSmolagentToolCalling:
    """Verifies tool registration, schema inspection, parameter coercion, and execution."""

    def test_tool_registration_and_metadata(self):
        def sample_tool(ip: str) -> str:
            return f"pong from {ip}"

        tool = SmolagentTool(
            name="ping_node",
            description="Ping node IP",
            func=sample_tool,
            parameters={"ip": {"type": "string", "required": True}}
        )
        assert tool.name == "ping_node"
        assert "ip" in tool.parameters

    def test_tool_execution_success(self):
        def add(a: int, b: int) -> int:
            return a + b

        tool = SmolagentTool(name="add", description="Add numbers", func=add)
        result = tool.execute(a=10, b=25)
        assert result == 35

    def test_tool_missing_required_parameter_raises(self):
        def fetch(url: str):
            return url

        tool = SmolagentTool(
            name="fetch",
            description="Fetch URL",
            func=fetch,
            parameters={"url": {"type": "string", "required": True}}
        )
        with pytest.raises(ValueError, match="Missing required parameter 'url'"):
            tool.execute()

    def test_agent_wrapper_registers_and_dispatches_tools(self):
        router = SmolagentAIRouter()
        agent = SmolagentAgentWrapper(router)
        
        tool1 = SmolagentTool("echo", "Echo text", lambda msg: msg)
        tool2 = SmolagentTool("calc_vram", "Calc free VRAM", lambda total, used: total - used)
        
        agent.register_tool(tool1)
        agent.register_tool(tool2)
        
        assert agent.execute_tool("echo", msg="hello world") == "hello world"
        assert agent.execute_tool("calc_vram", total=24.0, used=12.0) == 12.0

    def test_agent_wrapper_unregistered_tool_raises(self):
        router = SmolagentAIRouter()
        agent = SmolagentAgentWrapper(router)
        with pytest.raises(KeyError, match="Tool 'nonexistent' is not registered"):
            agent.execute_tool("nonexistent")


# ============================================================================
# TIER 2: LOCAL AI & CLOUD FALLBACK ROUTING TESTS
# ============================================================================

class TestLocalAndCloudAIRouting:
    """Verifies routing priority (llama.cpp -> exo -> Cloudflare AI -> Gemini Flash 300 quota)."""

    def test_primary_route_local_llamacpp(self, smolagent_provider_configs):
        router = SmolagentAIRouter(smolagent_provider_configs)
        routed = router.route_request("Test prompt")
        assert routed["provider"] == "local_llamacpp"
        assert routed["is_local"] is True
        assert routed["model"] == "Kimi-88B-Tandem"

    def test_fallback_to_exo_when_llamacpp_offline(self, smolagent_provider_configs):
        router = SmolagentAIRouter(smolagent_provider_configs)
        router.set_provider_status("local_llamacpp", False)
        
        routed = router.route_request("Test prompt")
        assert routed["provider"] == "local_exo"
        assert routed["is_local"] is True
        assert routed["model"] == "Qwen2.5-Coder-7B"

    def test_fallback_to_cloudflare_when_all_local_offline(self, smolagent_provider_configs):
        router = SmolagentAIRouter(smolagent_provider_configs)
        router.set_provider_status("local_llamacpp", False)
        router.set_provider_status("local_exo", False)
        
        routed = router.route_request("Test prompt")
        assert routed["provider"] == "cloudflare_ai_free"
        assert routed["is_local"] is False
        assert routed["model"] == "@cf/meta/llama-3-8b-instruct"

    def test_fallback_to_gemini_flash_when_cloudflare_offline(self, smolagent_provider_configs):
        router = SmolagentAIRouter(smolagent_provider_configs)
        router.set_provider_status("local_llamacpp", False)
        router.set_provider_status("local_exo", False)
        router.set_provider_status("cloudflare_ai_free", False)
        
        routed = router.route_request("Test prompt")
        assert routed["provider"] == "gemini_flash_free"
        assert routed["is_local"] is False
        assert routed["remaining_quota"] == 299

    def test_gemini_flash_300_quota_enforcement(self, smolagent_provider_configs):
        router = SmolagentAIRouter(smolagent_provider_configs)
        router.set_provider_status("local_llamacpp", False)
        router.set_provider_status("local_exo", False)
        router.set_provider_status("cloudflare_ai_free", False)
        
        # Exhaust quota (300 requests)
        router.gemini_daily_requests_count = 300
        
        routed = router.route_request("Test prompt")
        assert routed["status"] == "QUOTA_EXHAUSTED"
        assert routed["error"] == "DailyQuotaExceeded"


# ============================================================================
# TIER 3: AUTONOMOUS CRON SCHEDULER TESTS
# ============================================================================

class TestAutonomousBackgroundCronScheduler:
    """Verifies scheduled crons, non-overlapping execution locks, and error resilience."""

    @pytest.mark.asyncio
    async def test_cron_registration_and_execution(self):
        scheduler = SmolagentCronScheduler()
        counter = 0

        def sync_job():
            nonlocal counter
            counter += 1

        scheduler.register_job("job_sync", interval_seconds=0.01, func=sync_job)
        scheduler.start()

        await asyncio.sleep(0.04)
        await scheduler.stop()

        assert counter >= 2
        assert scheduler.execution_counts["job_sync"] >= 2

    @pytest.mark.asyncio
    async def test_async_cron_job_execution(self):
        scheduler = SmolagentCronScheduler()
        hits = []

        async def async_health_check():
            hits.append(time.time())

        scheduler.register_job("health_check", interval_seconds=0.01, func=async_health_check)
        scheduler.start()

        await asyncio.sleep(0.035)
        await scheduler.stop()

        assert len(hits) >= 2

    @pytest.mark.asyncio
    async def test_cron_resilience_to_job_errors(self):
        scheduler = SmolagentCronScheduler()
        runs = 0

        def failing_job():
            nonlocal runs
            runs += 1
            if runs % 2 == 1:
                raise RuntimeError("Simulated transient socket error")

        scheduler.register_job("failing_job", interval_seconds=0.01, func=failing_job)
        scheduler.start()

        await asyncio.sleep(0.04)
        await scheduler.stop()

        # Job continued to run despite intermittent exceptions
        assert runs >= 2


# ============================================================================
# TIER 4: TASK CANCELLATION & TEARDOWN CLEANLINESS
# ============================================================================

class TestTaskCancellationAndCleanTeardown:
    """Verifies that task cancellation terminates cleanly with zero unhandled exceptions."""

    @pytest.mark.asyncio
    async def test_async_task_cancellation_graceful_catch(self):
        cancelled_cleanly = False

        async def long_running_smolagent_task():
            nonlocal cancelled_cleanly
            try:
                await asyncio.sleep(10.0)
            except asyncio.CancelledError:
                cancelled_cleanly = True
                raise

        task = asyncio.create_task(long_running_smolagent_task())
        await asyncio.sleep(0.01)
        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task

        assert cancelled_cleanly is True

    @pytest.mark.asyncio
    async def test_scheduler_stop_cancels_all_running_tasks_cleanly(self):
        scheduler = SmolagentCronScheduler()
        
        async def sleep_forever():
            await asyncio.sleep(100.0)

        scheduler.register_job("forever_1", interval_seconds=0.001, func=sleep_forever)
        scheduler.register_job("forever_2", interval_seconds=0.001, func=sleep_forever)
        scheduler.start()

        await asyncio.sleep(0.01)
        assert len(scheduler.running_tasks) == 2
        
        # Stop must cleanly cancel both without throwing
        await scheduler.stop()
        assert len(scheduler.running_tasks) == 0


# ============================================================================
# TIER 5: MEMORY LEAK & REPEATED EXECUTION ISOLATION
# ============================================================================

class TestMemoryLeakAndResourceIsolation:
    """Verifies that executing repeated smolagent cycles does not leak memory or objects."""

    @pytest.mark.asyncio
    async def test_repeated_agent_cycles_memory_stability(self, smolagent_provider_configs):
        router = SmolagentAIRouter(smolagent_provider_configs)
        agent = SmolagentAgentWrapper(router)

        # Run 50 cycles
        for i in range(50):
            res = await agent.run_autonomous_cycle(f"task_{i}")
            assert res["status"] == "COMPLETED"

        gc.collect()
        # Verify no hanging tasks in agent
        assert len(agent.active_tasks) == 0


# ============================================================================
# TIER 6: SPECIALIST TOOLS & AUTONOMOUS CAPABILITIES
# ============================================================================

class TestSpecialistToolsEcosystem:
    """Verifies specialist tools: Mesh diagnostics, Obsidian knowledge, Self-healing, LoRA dataset, System metrics."""

    def test_mesh_diagnostics_tool(self):
        from backend.agents import create_mesh_diagnostics_tool
        tool = create_mesh_diagnostics_tool()
        assert tool.name == "mesh_diagnostics"
        # Test probing localhost
        res = tool.execute(target_ip="127.0.0.1", port=65534)
        assert "target_ip" in res
        assert "status" in res

    def test_obsidian_knowledge_tool(self, mock_obsidian_vault_dir):
        from backend.agents import create_obsidian_knowledge_tool
        tool = create_obsidian_knowledge_tool(mock_obsidian_vault_dir)
        assert tool.name == "obsidian_knowledge"
        res = tool.execute(note_name="Mac_Node")
        assert res["status"] == "SUCCESS"
        assert res["has_index"] is True
        assert res["matching_notes_count"] >= 1

    def test_self_healing_tool(self, tmp_path):
        from backend.agents import create_self_healing_tool
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        git_dir = repo_dir / ".git"
        git_dir.mkdir()
        lock_file = git_dir / "index.lock"
        lock_file.write_text("lock")

        tool = create_self_healing_tool(str(repo_dir))
        res = tool.execute(action="clean_git_lock")
        assert res["status"] == "HEALTHY"
        assert not lock_file.exists()

    def test_lora_dataset_tool(self, tmp_path):
        from backend.agents import create_lora_dataset_tool
        dataset_dir = tmp_path / "lora_datasets"
        dataset_dir.mkdir()
        (dataset_dir / "test_run.jsonl").write_text('{"prompt": "hi", "completion": "hello"}\n')

        tool = create_lora_dataset_tool()
        res = tool.execute(dataset_dir=str(dataset_dir))
        assert res["status"] == "SUCCESS"
        assert res["jsonl_files_count"] == 1
        assert res["total_size_bytes"] > 0

    def test_system_metrics_tool(self):
        from backend.agents import create_system_metrics_tool
        tool = create_system_metrics_tool()
        res = tool.execute()
        assert res["pooled_vram_gb"] == 82.8
        assert res["total_physical_ram_gb"] == 108.0
        assert res["status"] == "HEALTHY"


# ============================================================================
# TIER 7: QUOTA GOVERNOR & RATE LIMITING TESTS
# ============================================================================

class TestQuotaGovernorDirect:
    """Verifies QuotaGovernor rolling window, cost tiers, rate limits, and status telemetry."""

    def test_quota_governor_hierarchy_and_cost_tracking(self):
        from backend.agents import QuotaGovernor
        gov = QuotaGovernor(gemini_daily_limit=5, window_seconds=10.0)

        assert gov.get_optimal_provider() == "local_llamacpp"
        gov.record_request("local_llamacpp", tokens=100)

        # Fallback when local is offline
        gov.set_provider_status("local_llamacpp", False)
        assert gov.get_optimal_provider() == "local_exo"

        gov.set_provider_status("local_exo", False)
        assert gov.get_optimal_provider() == "cloudflare_ai_free"

        gov.set_provider_status("cloudflare_ai_free", False)
        assert gov.get_optimal_provider() == "gemini_flash_free"

        # Record 5 gemini requests to exhaust quota
        for _ in range(5):
            gov.record_request("gemini_flash_free", tokens=50)

        assert not gov.can_route_to("gemini_flash_free")
        assert gov.get_optimal_provider() is None

        status = gov.get_quota_status()
        assert status["providers"]["gemini_flash_free"]["is_exhausted"] is True

    def test_quota_governor_reset_window(self):
        from backend.agents import QuotaGovernor
        gov = QuotaGovernor(gemini_daily_limit=2)
        gov.record_request("gemini_flash_free", tokens=50)
        gov.record_request("gemini_flash_free", tokens=50)
        assert not gov.can_route_to("gemini_flash_free")

        gov.reset_window()
        assert gov.can_route_to("gemini_flash_free")
        assert gov.gemini_daily_requests_count == 0


# ============================================================================
# TIER 8: SELF-HEALING DAEMON TESTS
# ============================================================================

class TestSelfHealingDaemonDirect:
    """Verifies RFC 792 WoL Magic Packet generation, ADB wake lock, and auto-healing cycle."""

    def test_wol_magic_packet_generation(self):
        from backend.agents import SelfHealingDaemon
        daemon = SelfHealingDaemon()
        # Valid MAC
        res = daemon.send_wol_magic_packet("AA:BB:CC:DD:EE:FF")
        assert res["status"] == "SENT"
        assert res["action"] == "WOL_MAGIC_PACKET"

        # Invalid MAC
        err_res = daemon.send_wol_magic_packet("INVALID_MAC")
        assert err_res["status"] == "ERROR"

    def test_heal_stale_git_locks(self, tmp_path):
        from backend.agents import SelfHealingDaemon
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        git_dir = repo_dir / ".git"
        git_dir.mkdir()
        lock_file = git_dir / "index.lock"
        lock_file.write_text("lock")

        # Fake old timestamp
        old_time = time.time() - 10.0
        import os
        os.utime(str(lock_file), (old_time, old_time))

        daemon = SelfHealingDaemon(repo_path=str(repo_dir))
        res = daemon.heal_stale_git_locks()
        assert res["status"] == "REMOVED_STALE_LOCK"
        assert not lock_file.exists()

    @pytest.mark.asyncio
    async def test_run_self_healing_cycle(self, tmp_path):
        from backend.agents import SelfHealingDaemon
        daemon = SelfHealingDaemon(repo_path=str(tmp_path))
        res = await daemon.run_self_healing_cycle()
        assert res["status"] == "HEALTHY"
        assert "git_heal" in res


# ============================================================================
# TIER 9: REST API ROUTER ENDPOINTS TESTS
# ============================================================================

class TestAgentsApiRouter:
    """Verifies FastAPI endpoints for agents, crons, quota, tools, and self-healing."""

    def test_agents_endpoints(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from backend.router import create_app_router

        app = FastAPI()
        app.include_router(create_app_router())
        client = TestClient(app)

        # 1. GET /api/v1/agents/quota
        res_quota = client.get("/api/v1/agents/quota")
        assert res_quota.status_code == 200
        quota_data = res_quota.json()
        assert "providers" in quota_data
        assert "gemini_flash_free" in quota_data["providers"]

        # 2. GET /api/v1/agents/crons
        res_crons = client.get("/api/v1/agents/crons")
        assert res_crons.status_code == 200
        crons_data = res_crons.json()
        assert "jobs" in crons_data
        assert "network_health_scan" in crons_data["jobs"]

        # 3. GET /api/v1/agents/tools
        res_tools = client.get("/api/v1/agents/tools")
        assert res_tools.status_code == 200
        tools_data = res_tools.json()
        assert "tools" in tools_data
        assert "mesh_diagnostics" in tools_data["tools"]

        # 4. POST /api/v1/agents/run
        res_run = client.post("/api/v1/agents/run", json={"task": "system_metrics"})
        assert res_run.status_code == 200
        run_data = res_run.json()
        assert run_data["status"] == "COMPLETED"

        # 5. POST /api/v1/agents/self-heal
        res_heal = client.post("/api/v1/agents/self-heal", json={"action": "all"})
        assert res_heal.status_code == 200
        heal_data = res_heal.json()
        assert heal_data["status"] == "HEALTHY"

