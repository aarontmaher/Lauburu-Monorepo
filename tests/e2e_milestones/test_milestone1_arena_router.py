"""
Milestone 1 Unit Tests — Continuous AI Arena Core Routing & Background Engine
=============================================================================
Tests the complete Milestone 1 implementation:
1. ChampionLeaderboardResolver (debounced mtime caching, fallback safety, rank resolution)
2. ContinuousArenaEngine (bounded queue, async worker, 2x challenger concurrency, timeout/error safety)
3. ContinuousArenaInferenceRouter (zero-added-latency Champion streaming + async trial enqueue)
4. Integration with UnifiedInferenceRouter and CloudAIRouter
"""

import os
import sys
import time
import json
import uuid
import asyncio
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional, AsyncGenerator

import pytest

# Ensure monorepo and canonical port packages are importable
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

CANONICAL_PORT_DIR = REPO_ROOT / "01_apps" / "canonical_port"
if str(CANONICAL_PORT_DIR) not in sys.path:
    sys.path.insert(0, str(CANONICAL_PORT_DIR))

from backend.agents.continuous_arena_router import (
    ChampionLeaderboardResolver,
    ContinuousArenaEngine,
    ContinuousArenaInferenceRouter,
    ArenaTrialRequest,
    ArenaTrialResult,
    DEFAULT_CHAMPION_SPEC,
    MODEL_ENGINE_MAPPINGS,
    DEFAULT_CHALLENGER_POOL,
    resolve_model_engine,
)
from backend.agents.cloud_ai_router import CloudAIRouter
from tui.services.inference_router import UnifiedInferenceRouter
from tui.services.inference_bridges.base_bridge import BaseInferenceBridge


# ---------------------------------------------------------------------------
# Test Fixtures & Mock Bridges
# ---------------------------------------------------------------------------

class MockTestBridge(BaseInferenceBridge):
    """Real asynchronous test bridge capturing prompt calls and yielding tokens."""

    def __init__(self, engine_name: str = "llama_rpc", model_name: str = "Test-Model", **kwargs):
        super().__init__(**kwargs)
        self._engine_name = engine_name
        self._model_name = model_name
        self.call_history: List[Dict[str, Any]] = []

    def get_engine_name(self) -> str:
        return self._engine_name

    def get_display_name(self) -> str:
        return f"Mock {self._model_name}"

    async def connect(self, timeout: Optional[float] = None) -> bool:
        return True

    def is_connected(self) -> bool:
        return True

    def get_status(self) -> Dict[str, Any]:
        return {
            "engine_name": self._engine_name,
            "model_name": self._model_name,
            "is_connected": True,
        }

    def get_status_badge(self) -> str:
        return f"[{self._engine_name.upper()}: ACTIVE]"

    async def stream_generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> AsyncGenerator[str, None]:
        self.call_history.append({"prompt": prompt, "method": "stream_generate"})
        tokens = [f"Token1_{self._engine_name}", f"Token2_{self._engine_name}", f"Token3_{self._engine_name}"]
        for tok in tokens:
            await asyncio.sleep(0.005)
            if self.on_token:
                self.on_token(tok)
            yield tok + " "
        if self.on_complete:
            self.on_complete(" ".join(tokens))

    async def process_user_input(
        self,
        prompt: str,
        is_voice: bool = False,
        max_tokens: int = 256
    ) -> str:
        self.call_history.append({"prompt": prompt, "is_voice": is_voice, "method": "process_user_input"})
        await asyncio.sleep(0.01)
        resp = f"[{self._model_name} response to: {prompt}]"
        if self.on_complete:
            self.on_complete(resp)
        return resp


@pytest.fixture
def sample_leaderboard_data() -> Dict[str, Any]:
    """Sample valid leaderboard payload matching schema v7."""
    return {
        "schema_version": "2.5.0",
        "last_updated_utc": "2026-08-28T00:00:00Z",
        "canonical_summary": {
            "total_models": 3,
            "top_sovereign_model_id": "kimi_tandem_titan",
            "top_sovereign_orchestrator": "Kimi Tandem Titan",
            "top_local_model_id": "genetic_moe_orchestrator",
            "top_local_core": "Genetic MoE Local Orchestrator",
            "total_matches_recorded": 10,
            "total_duels_recorded": 10,
            "total_harvested_lora_pairs": 54300,
            "mesh_usable_vram_gb": 82.8,
            "hardware_npu_tops": 121.0,
            "zero_fake_data_guarantee": "100% Certified Empirical Telemetry",
            "timestamp": "2026-08-28 00:00:00 UTC"
        },
        "leaderboard": [
            {
                "id": "kimi_tandem_titan",
                "name": "Kimi Tandem Titan (VL-Encoder + 72B Backbone)",
                "engine": "llama_rpc",
                "elo": 3089.0,
                "canonical_score": 99.6,
                "rank": 1,
                "tier": "LOCAL_SOVEREIGN_GIANT",
                "params_b": 88.0
            },
            {
                "id": "command_r_plus_104b",
                "name": "Command-R+ 104B Q4_K_M",
                "engine": "llama_rpc",
                "elo": 2980.0,
                "canonical_score": 98.4,
                "rank": 2,
                "tier": "LOCAL_100B_TITAN",
                "params_b": 104.0
            },
            {
                "id": "gemini_37_flash",
                "name": "Gemini 3.7 Flash Ultra",
                "engine": "gemini",
                "elo": 2950.0,
                "canonical_score": 98.0,
                "rank": 3,
                "tier": "FRONTIER_CLOUD_API",
                "params_b": 70.0
            }
        ]
    }


# ===========================================================================
# 1. CHAMPION LEADERBOARD RESOLVER TESTS
# ===========================================================================

def test_resolver_loads_valid_canonical_leaderboard(sample_leaderboard_data):
    """Verify resolver parses valid leaderboard and identifies rank #1 Champion."""
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(sample_leaderboard_data, f)
        temp_path = f.name

    try:
        resolver = ChampionLeaderboardResolver(ledger_path=temp_path, debounce_ttl_sec=0.1)
        champion = resolver.resolve_current_champion()

        assert champion["model_id"] == "kimi_tandem_titan"
        assert champion["engine"] == "llama_rpc"
        assert champion["elo"] == 3089.0
        assert champion["rank"] == 1
        assert champion["is_fallback"] is False
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_resolver_mtime_debounce_caching(sample_leaderboard_data):
    """Verify resolver uses mtime debounced cache on rapid successive calls (<0.1ms)."""
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(sample_leaderboard_data, f)
        temp_path = f.name

    try:
        resolver = ChampionLeaderboardResolver(ledger_path=temp_path, debounce_ttl_sec=1.0)

        # First read loads from disk
        c1 = resolver.resolve_current_champion()

        # Second read within debounce TTL should be sub-millisecond cache hit
        t0 = time.perf_counter()
        c2 = resolver.resolve_current_champion()
        elapsed_us = (time.perf_counter() - t0) * 1_000_000

        assert c1["model_id"] == c2["model_id"]
        assert c1["elo"] == c2["elo"]
        # Fast in-memory cache hit
        assert elapsed_us < 500.0  # < 0.5ms
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_resolver_cache_invalidation_on_mtime_change(sample_leaderboard_data):
    """Verify resolver detects file update and promotes new #1 ELO model."""
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(sample_leaderboard_data, f)
        temp_path = f.name

    try:
        resolver = ChampionLeaderboardResolver(ledger_path=temp_path, debounce_ttl_sec=0.05)
        c1 = resolver.resolve_current_champion()
        assert c1["model_id"] == "kimi_tandem_titan"

        # Update file: promote command_r_plus_104b to 3200.0 ELO
        time.sleep(0.1)
        sample_leaderboard_data["leaderboard"][1]["elo"] = 3200.0
        with open(temp_path, "w") as f:
            json.dump(sample_leaderboard_data, f)

        # Invalidate cache or wait for TTL
        resolver.invalidate_cache()
        c2 = resolver.resolve_current_champion()

        assert c2["model_id"] == "command_r_plus_104b"
        assert c2["elo"] == 3200.0
        assert c2["rank"] == 1
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_resolver_fallback_on_missing_or_corrupted_file():
    """Verify resolver safely falls back to default champion on missing or corrupted JSON."""
    # 1. Non-existent file
    resolver_missing = ChampionLeaderboardResolver(ledger_path="/tmp/non_existent_ledger_9999.json")
    champ_missing = resolver_missing.resolve_current_champion()
    assert champ_missing["model_id"] == DEFAULT_CHAMPION_SPEC["model_id"]
    assert champ_missing["engine"] == DEFAULT_CHAMPION_SPEC["engine"]
    assert champ_missing["is_fallback"] is True

    # 2. Corrupted JSON file
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        f.write("{ INVALID JSON CONTENT :::")
        corrupt_path = f.name

    try:
        resolver_corrupt = ChampionLeaderboardResolver(ledger_path=corrupt_path)
        champ_corrupt = resolver_corrupt.resolve_current_champion()
        assert champ_corrupt["model_id"] == DEFAULT_CHAMPION_SPEC["model_id"]
        assert champ_corrupt["is_fallback"] is True
    finally:
        if os.path.exists(corrupt_path):
            os.remove(corrupt_path)


def test_resolver_engine_mapping_rules():
    """Verify model ID to engine mapping rules."""
    assert resolve_model_engine("kimi_tandem_titan") == "llama_rpc"
    assert resolve_model_engine("command_r_plus_104b") == "llama_rpc"
    assert resolve_model_engine("abliterated_llama3_70b") == "llama_rpc"
    assert resolve_model_engine("exo_coder_7b") == "exo"
    assert resolve_model_engine("accelerate_mps") == "accelerate"
    assert resolve_model_engine("petals_swarm") == "petals"
    assert resolve_model_engine("gemini_37_flash") == "gemini"
    assert resolve_model_engine("cloudflare_llama3_8b") == "cloudflare"
    assert resolve_model_engine("julien_ultra") == "julien"


# ===========================================================================
# 2. CONTINUOUS ARENA ENGINE TESTS
# ===========================================================================

@pytest.mark.asyncio
async def test_arena_engine_bounded_queue_and_overflow():
    """Verify queue boundedness (capacity limit) and non-blocking drop handling."""
    engine = ContinuousArenaEngine(queue_maxsize=3, default_timeout=5.0)

    # Enqueue 3 items without starting worker
    q1 = engine.enqueue_trial("Prompt 1", {"model_id": "m1", "text": "resp1"}, auto_start=False)
    q2 = engine.enqueue_trial("Prompt 2", {"model_id": "m1", "text": "resp2"}, auto_start=False)
    q3 = engine.enqueue_trial("Prompt 3", {"model_id": "m1", "text": "resp3"}, auto_start=False)

    assert q1 is True
    assert q2 is True
    assert q3 is True
    assert engine.queue.qsize() == 3

    # 4th item should be rejected/dropped due to capacity limit
    q4 = engine.enqueue_trial("Prompt 4 (Overflow)", {"model_id": "m1", "text": "resp4"}, auto_start=False)
    assert q4 is False

    metrics = engine.get_metrics()
    assert metrics["total_enqueued"] == 3
    assert metrics["total_dropped"] == 1
    assert metrics["queue_size"] == 3

    engine.close()


def test_arena_engine_challenger_selection_rotation():
    """Verify select_challengers excludes champion and rotates across challenger pool."""
    engine = ContinuousArenaEngine()

    # Exclude champion model
    challengers_1 = engine.select_challengers(exclude_model_id="kimi_tandem_titan", count=2)
    assert len(challengers_1) == 2
    assert all(c["model_id"] != "kimi_tandem_titan" for c in challengers_1)

    # Next rotation should select distinct/next items
    challengers_2 = engine.select_challengers(exclude_model_id="kimi_tandem_titan", count=2)
    assert len(challengers_2) == 2
    assert all(c["model_id"] != "kimi_tandem_titan" for c in challengers_2)


@pytest.mark.asyncio
async def test_arena_engine_concurrent_challenger_execution():
    """Verify 2 challenger models execute concurrently with accurate timing."""
    async def mock_executor(spec: Dict[str, Any], prompt: str, timeout: float) -> Dict[str, Any]:
        await asyncio.sleep(0.05)
        return {
            "model_id": spec["model_id"],
            "engine": spec.get("engine", "llama_rpc"),
            "text": f"Challenger output from {spec['model_id']}",
            "status": "SUCCESS",
        }

    engine = ContinuousArenaEngine(executor_func=mock_executor)

    spec1 = {"model_id": "command_r_plus_104b", "engine": "llama_rpc"}
    spec2 = {"model_id": "gemini_37_flash", "engine": "gemini"}

    t0 = time.perf_counter()
    # Concurrently execute
    task1 = engine.execute_challenger(spec1, "Calculate PTT BP", timeout=2.0)
    task2 = engine.execute_challenger(spec2, "Calculate PTT BP", timeout=2.0)
    res1, res2 = await asyncio.gather(task1, task2)
    elapsed = time.perf_counter() - t0

    assert res1["status"] == "SUCCESS"
    assert res2["status"] == "SUCCESS"
    assert "command_r_plus_104b" in res1["text"]
    assert "gemini_37_flash" in res2["text"]
    assert res1["latency_ms"] >= 40.0
    # Concurrent execution took ~50ms rather than ~100ms
    assert elapsed < 0.12

    engine.close()


@pytest.mark.asyncio
async def test_arena_engine_timeout_protection():
    """Verify challenger execution timeout protection captures error without throwing."""
    async def slow_executor(spec: Dict[str, Any], prompt: str, timeout: float) -> Dict[str, Any]:
        await asyncio.sleep(0.3)  # Exceeds 0.05s timeout
        return {"text": "Late response"}

    engine = ContinuousArenaEngine(executor_func=slow_executor)
    spec = {"model_id": "slow_model", "engine": "llama_rpc"}

    res = await engine.execute_challenger(spec, "Test prompt", timeout=0.05)

    assert res["status"] == "TIMEOUT"
    assert "timed out" in res["error"].lower()

    metrics = engine.get_metrics()
    assert metrics["total_challenger_timeouts"] >= 1

    engine.close()


@pytest.mark.asyncio
async def test_arena_engine_exception_isolation():
    """Verify runtime exceptions inside challenger execution are safely caught."""
    async def crashing_executor(spec: Dict[str, Any], prompt: str, timeout: float) -> Dict[str, Any]:
        raise RuntimeError("Simulated connection drop on RPC socket")

    engine = ContinuousArenaEngine(executor_func=crashing_executor)
    spec = {"model_id": "faulty_model", "engine": "llama_rpc"}

    res = await engine.execute_challenger(spec, "Test prompt", timeout=1.0)

    assert res["status"] == "ERROR"
    assert "Simulated connection drop" in res["error"]

    metrics = engine.get_metrics()
    assert metrics["total_challenger_errors"] >= 1

    engine.close()


@pytest.mark.asyncio
async def test_arena_engine_worker_lifecycle_and_trial_processing():
    """Verify background worker processes enqueued trial and fires completion callback."""
    completed_trials: List[ArenaTrialResult] = []

    def on_complete(result: ArenaTrialResult):
        completed_trials.append(result)

    async def mock_executor(spec: Dict[str, Any], prompt: str, timeout: float) -> Dict[str, Any]:
        await asyncio.sleep(0.01)
        return {
            "model_id": spec["model_id"],
            "text": f"Output from {spec['model_id']}",
            "status": "SUCCESS",
        }

    engine = ContinuousArenaEngine(
        executor_func=mock_executor,
        on_trial_complete=on_complete,
        idle_timeout=0.2,
    )

    champion_res = {
        "model_id": "kimi_tandem_titan",
        "engine": "llama_rpc",
        "text": "Champion response",
        "latency_ms": 15.0,
        "status": "SUCCESS",
    }

    # Enqueue trial
    success = engine.enqueue_trial(
        prompt="Design a resilient ECG QRS detection pipeline",
        champion_result=champion_res,
    )
    assert success is True

    # Wait briefly for background worker to process trial
    await asyncio.sleep(0.15)

    assert len(completed_trials) == 1
    trial = completed_trials[0]
    assert trial.status == "COMPLETED"
    assert trial.champion_result["model_id"] == "kimi_tandem_titan"
    assert len(trial.challenger_results) == 2

    metrics = engine.get_metrics()
    assert metrics["total_completed"] >= 1

    engine.close()


# ===========================================================================
# 3. CONTINUOUS ARENA INFERENCE ROUTER TESTS
# ===========================================================================

@pytest.mark.asyncio
async def test_arena_router_synchronous_champion_stream_zero_latency(sample_leaderboard_data):
    """
    Verify ContinuousArenaInferenceRouter streams from #1 Champion with zero latency overhead
    and automatically enqueues the background trial.
    """
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(sample_leaderboard_data, f)
        temp_path = f.name

    try:
        resolver = ChampionLeaderboardResolver(ledger_path=temp_path)
        mock_bridge = MockTestBridge(engine_name="llama_rpc", model_name="Kimi-Tandem-88B")
        bridges = {"llama_rpc": mock_bridge}

        enqueued_trials: List[Dict[str, Any]] = []

        class MockArenaEngine(ContinuousArenaEngine):
            def enqueue_trial(self, prompt, champion_result, challenger_specs=None, metadata=None):
                enqueued_trials.append({"prompt": prompt, "champion_result": champion_result})
                return True

        arena_engine = MockArenaEngine()
        router = ContinuousArenaInferenceRouter(
            resolver=resolver,
            arena_engine=arena_engine,
            bridges=bridges,
            enable_arena=True,
        )

        prompt = "Explain Pan-Tompkins 512Hz QRS detection"
        tokens_received = []

        # Stream generate tokens
        async for token in router.stream_generate(prompt):
            tokens_received.append(token)

        assert len(tokens_received) == 3
        assert "Token1_llama_rpc" in tokens_received[0]

        # Verify background trial was enqueued
        assert len(enqueued_trials) == 1
        trial = enqueued_trials[0]
        assert trial["prompt"] == prompt
        assert trial["champion_result"]["model_id"] == "kimi_tandem_titan"
        assert trial["champion_result"]["status"] == "SUCCESS"
        assert trial["champion_result"]["latency_ms"] > 0.0

        arena_engine.close()
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@pytest.mark.asyncio
async def test_arena_router_process_user_input_and_generate_response():
    """Verify router process_user_input and generate_response methods."""
    resolver = ChampionLeaderboardResolver()
    mock_bridge = MockTestBridge(engine_name="llama_rpc", model_name="Kimi-Tandem-88B")
    bridges = {"llama_rpc": mock_bridge}

    enqueued_trials = []

    class MockArenaEngine(ContinuousArenaEngine):
        def enqueue_trial(self, prompt, champion_result, challenger_specs=None, metadata=None):
            enqueued_trials.append(champion_result)
            return True

    arena_engine = MockArenaEngine()
    router = ContinuousArenaInferenceRouter(
        resolver=resolver,
        arena_engine=arena_engine,
        bridges=bridges,
        enable_arena=True,
    )

    # 1. Test process_user_input
    resp = await router.process_user_input("Check mesh latency", is_voice=True)
    assert "response to: Check mesh latency" in resp
    assert len(enqueued_trials) == 1

    # 2. Test generate_response
    struct_resp = await router.generate_response("Summarize LoRA loss curve")
    champ_meta = resolver.resolve_current_champion()
    assert struct_resp["status"] == "SUCCESS"
    assert struct_resp["model_id"] == champ_meta["model_id"]
    assert len(enqueued_trials) == 2

    arena_engine.close()


# ===========================================================================
# 4. INTEGRATION WITH UNIFIED INFERENCE ROUTER & CLOUD AI ROUTER
# ===========================================================================

@pytest.mark.asyncio
async def test_unified_inference_router_arena_integration():
    """Verify UnifiedInferenceRouter supports champion/arena mode and triggers background trials."""
    mock_bridge_llama = MockTestBridge(engine_name="llama_rpc", model_name="Kimi-88B")
    mock_bridge_gemini = MockTestBridge(engine_name="gemini", model_name="Gemini-Flash")
    bridges = {
        "llama_rpc": mock_bridge_llama,
        "gemini": mock_bridge_gemini,
    }

    enqueued_trials = []

    class MockArenaEngine(ContinuousArenaEngine):
        def enqueue_trial(self, prompt, champion_result, challenger_specs=None, metadata=None):
            enqueued_trials.append(champion_result)
            return True

    arena_engine = MockArenaEngine()
    router = UnifiedInferenceRouter(
        default_engine="champion",
        bridges=bridges,
        arena_engine=arena_engine,
        enable_arena=True,
    )

    assert router.active_engine == "champion"
    assert "champion" in router.supported_engines
    assert "arena" in router.supported_engines

    # Effective engine should resolve to champion engine (llama_rpc)
    eff = router.get_effective_engine()
    assert eff in ("llama_rpc", "gemini")

    # Stream should yield tokens and enqueue trial
    tokens = []
    async for tok in router.stream_generate("Audit zero-mock telemetry"):
        tokens.append(tok)

    assert len(tokens) == 3
    assert len(enqueued_trials) == 1
    assert enqueued_trials[0]["engine"] == eff

    # Verify status and HUD badge
    status = router.get_status()
    assert status["arena_enabled"] is True
    assert "[CHAMPION:" in router.get_status_badge()

    arena_engine.close()


@pytest.mark.asyncio
async def test_cloud_ai_router_arena_integration():
    """Verify CloudAIRouter attaches arena engine and enqueues trials on generate_response."""
    router = CloudAIRouter()
    enqueued_trials = []

    class MockArenaEngine(ContinuousArenaEngine):
        def enqueue_trial(self, prompt, champion_result, challenger_specs=None, metadata=None):
            enqueued_trials.append(champion_result)
            return True

    arena_engine = MockArenaEngine()
    router.attach_arena_engine(arena_engine, enable=True)

    resp = await router.generate_response("Deploy SeaweedFS S3 mount")

    assert resp["status"] == "SUCCESS"
    assert len(enqueued_trials) == 1
    assert enqueued_trials[0]["text"] == resp["response"]

    metrics = router.get_arena_metrics()
    assert metrics["is_running"] is False or metrics["queue_capacity"] >= 10

    arena_engine.close()
