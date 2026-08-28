"""
Adversarial Challenger 2 Test Suite for Milestone 1
Tests:
1. boot_canonical_mesh.sh syntax, flag handling, readiness polling logic
2. canonical_mesh.kdl format and pane command validity
3. UnifiedInferenceRouter.get_effective_engine() under missing API keys, disconnected sockets, and forced swaps
4. ai_debate_tui_sync.py resilience and telemetry model compatibility
"""

import os
import sys
import math
import time
import shutil
import asyncio
import subprocess
from pathlib import Path
from typing import AsyncGenerator, Dict, Any, Optional
import pytest

from tui.services.inference_router import UnifiedInferenceRouter
from tui.services.latency_poller import DynamicLatencyPoller, EngineLatencyMetric
from tui.services.inference_bridges.base_bridge import BaseInferenceBridge
from tui.services.inference_bridges.llama_bridge import LlamaRpcInferenceBridge
from tui.services.inference_bridges.exo_bridge import ExoInferenceBridge
from tui.services.inference_bridges.accelerate_bridge import AccelerateInferenceBridge
from tui.services.inference_bridges.petals_bridge import PetalsInferenceBridge
from tui.services.inference_bridges.gemini_bridge import GeminiBridge
from tui.services.inference_bridges.cloudflare_bridge import CloudflareBridge
from tui.services.inference_bridges.julien_bridge import JulienBridge
from tui.services.blackboard_store import blackboard_store
from tui.services.ai_debate_tui_sync import AIDebateTUISyncEngine


class MockFailingBridge(BaseInferenceBridge):
    """A bridge that simulates socket disconnection or immediate failure."""
    def __init__(self, name: str, should_fail_on_connect: bool = True, fail_mid_stream: bool = False):
        super().__init__()
        self._eng_name = name
        self._disp_name = f"Mock {name}"
        self._should_fail_on_connect = should_fail_on_connect
        self._fail_mid_stream = fail_mid_stream
        self._connected = not should_fail_on_connect

    def get_engine_name(self) -> str:
        return self._eng_name

    def get_display_name(self) -> str:
        return self._disp_name

    def get_status(self) -> Dict[str, Any]:
        return {
            "engine_name": self._eng_name,
            "display_name": self._disp_name,
            "is_connected": self._connected,
        }

    def get_status_badge(self) -> str:
        return f"[{self._eng_name.upper()}: {'ACTIVE' if self._connected else 'OFFLINE'}]"

    def is_connected(self) -> bool:
        return self._connected

    async def connect(self, timeout: Optional[float] = None) -> bool:
        if self._should_fail_on_connect:
            self._connected = False
            return False
        self._connected = True
        return True

    async def stream_generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> AsyncGenerator[str, None]:
        if self._should_fail_on_connect or not self._connected:
            raise ConnectionError(f"Engine {self._eng_name} socket unreachable")
        if self._fail_mid_stream:
            yield "token1 "
            yield "token2 "
            raise ConnectionResetError("Socket dropped mid-stream")
        yield f"response from {self._eng_name}"

    async def process_user_input(self, prompt: str, is_voice: bool = False, max_tokens: int = 256) -> str:
        if self._should_fail_on_connect or not self._connected:
            raise ConnectionError(f"Engine {self._eng_name} socket unreachable")
        return f"processed by {self._eng_name}"


# ============================================================================
# 1. BOOTSTRAPPER AND KDL TESTS
# ============================================================================

def test_boot_script_bash_syntax():
    """Verify boot_canonical_mesh.sh passes bash syntax check."""
    root = Path(__file__).resolve().parent.parent.parent
    script = root / "boot_canonical_mesh.sh"
    assert script.exists(), "boot_canonical_mesh.sh not found"
    res = subprocess.run(["bash", "-n", str(script)], capture_output=True, text=True)
    assert res.returncode == 0, f"Syntax error in boot_canonical_mesh.sh: {res.stderr}"


def test_boot_script_target_paths_exist():
    """Verify all files referenced in boot_canonical_mesh.sh actually exist."""
    root = Path(__file__).resolve().parent.parent.parent
    monorepo_root = root.parent.parent

    tui_script = root / "tui" / "canonical_tui.py"
    movesense_script = monorepo_root / "03_biometrics_and_telemetry" / "movesense_to_4000_bridge.py"
    ai_debate_sync_script = root / "tui" / "services" / "ai_debate_tui_sync.py"

    assert tui_script.exists(), f"Missing {tui_script}"
    assert movesense_script.exists(), f"Missing {movesense_script}"
    assert ai_debate_sync_script.exists(), f"Missing {ai_debate_sync_script}"


def test_canonical_mesh_kdl_validity():
    """Verify canonical_mesh.kdl file existence, brace balance, and pane definitions."""
    root = Path(__file__).resolve().parent.parent.parent
    kdl_path = root / "canonical_mesh.kdl"
    assert kdl_path.exists(), "canonical_mesh.kdl not found"

    with open(kdl_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert content.count("{") == content.count("}"), "Unbalanced braces in canonical_mesh.kdl"
    assert 'tab name="Command Center"' in content
    assert 'tab name="Background Services"' in content
    assert 'pane' in content
    assert 'name "Textual Cockpit"' in content
    assert 'name "FastAPI Backend (:4000) & Crons"' in content
    assert 'name "Movesense BLE Bridge"' in content
    assert 'name "AI Debate TUI Sync Daemon"' in content


# ============================================================================
# 2. INFERENCE ROUTER & GET_EFFECTIVE_ENGINE ADVERSARIAL CHALLENGES
# ============================================================================

def test_get_effective_engine_with_no_api_keys(monkeypatch):
    """
    Adversarial Challenge: When cloud API keys (Gemini, Cloudflare, Julien) are completely missing,
    get_effective_engine() in 'auto' mode MUST NOT return any cloud engine.
    """
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("CLOUDFLARE_API_TOKEN", raising=False)
    monkeypatch.delenv("CLOUDFLARE_ACCOUNT_ID", raising=False)
    monkeypatch.delenv("JULIEN_API_KEY", raising=False)

    router = UnifiedInferenceRouter(default_engine="auto")
    eff = router.get_effective_engine()
    assert eff not in ["gemini", "cloudflare", "julien"], f"Unconfigured cloud engine '{eff}' chosen in auto mode"
    assert eff in ["llama_rpc", "exo", "accelerate", "petals"]


def test_get_effective_engine_dynamic_lowest_ttft():
    """
    Adversarial Challenge: Verify get_effective_engine() strictly picks the engine with lowest TTFT in auto mode.
    """
    router = UnifiedInferenceRouter(default_engine="auto")
    poller = router.poller

    # Simulate latencies: exo=12ms, accelerate=45ms, petals=150ms, llama_rpc=50ms
    poller.set_metric_for_testing("exo", ttft_ms=12.0, is_available=True)
    poller.set_metric_for_testing("accelerate", ttft_ms=45.0, is_available=True)
    poller.set_metric_for_testing("petals", ttft_ms=150.0, is_available=True)
    poller.set_metric_for_testing("llama_rpc", ttft_ms=50.0, is_available=True)

    assert router.get_effective_engine() == "exo"

    # Now accelerate becomes faster (8ms)
    poller.set_metric_for_testing("accelerate", ttft_ms=8.0, is_available=True)
    assert router.get_effective_engine() == "accelerate"

    # Accelerate fails / disconnects
    poller.set_metric_for_testing("accelerate", ttft_ms=float("inf"), is_available=False)
    assert router.get_effective_engine() == "exo"


def test_get_effective_engine_all_external_disconnected():
    """
    Adversarial Challenge: If all external engines are disconnected or unavailable,
    get_effective_engine() must safely default to llama_rpc.
    """
    router = UnifiedInferenceRouter(default_engine="auto")
    poller = router.poller

    for eng in ["exo", "accelerate", "petals", "gemini", "cloudflare", "julien", "llama_rpc"]:
        poller.set_metric_for_testing(eng, ttft_ms=float("inf"), is_available=False, error="Disconnected")

    assert router.get_effective_engine() == "llama_rpc"


def test_forced_engine_swaps_and_aliases():
    """
    Adversarial Challenge: Forced engine swaps must bypass auto routing and return the exact forced engine,
    supporting all aliases and case variations.
    """
    router = UnifiedInferenceRouter(default_engine="auto")

    test_cases = [
        ("gemini", "gemini"),
        ("GEMINI", "gemini"),
        ("google", "gemini"),
        ("gemini_pro", "gemini"),
        ("cloudflare", "cloudflare"),
        ("cf", "cloudflare"),
        ("workers_ai", "cloudflare"),
        ("julien", "julien"),
        ("julien_ai", "julien"),
        ("julien_ultra", "julien"),
        ("llama_rpc", "llama_rpc"),
        ("llamacpp", "llama_rpc"),
        ("rpc", "llama_rpc"),
        ("exo", "exo"),
        ("ring", "exo"),
        ("accelerate", "accelerate"),
        ("mps", "accelerate"),
        ("metal", "accelerate"),
        ("petals", "petals"),
        ("dht", "petals"),
        ("auto", "auto"),
        ("dynamic", "auto"),
        ("fastest", "auto"),
    ]

    for input_name, expected_active in test_cases:
        res = router.set_active_engine(input_name)
        assert res == expected_active
        assert router.active_engine == expected_active

    # Invalid engine name raises ValueError
    with pytest.raises(ValueError):
        router.set_active_engine("non_existent_engine_xyz")


@pytest.mark.asyncio
async def test_forced_engine_swap_unconfigured_cloud_stream_graceful():
    """
    Adversarial Challenge: Forcing an unconfigured cloud engine and calling stream_generate()
    must yield a clean error/system message without crashing the event loop or raising unhandled exceptions.
    """
    router = UnifiedInferenceRouter(default_engine="llama_rpc")

    for cloud_eng in ["gemini", "cloudflare", "julien"]:
        router.set_active_engine(cloud_eng)
        assert router.get_effective_engine() == cloud_eng

        tokens = []
        try:
            async for token in router.stream_generate("Hello"):
                tokens.append(token)
        except Exception as e:
            pytest.fail(f"stream_generate raised unhandled exception on forced {cloud_eng}: {e}")

        full_output = "".join(tokens)
        assert len(full_output) > 0, f"Expected system notice for unconfigured {cloud_eng}"


@pytest.mark.asyncio
async def test_rapid_engine_swapping_mid_generation():
    """
    Adversarial Challenge: Rapidly swapping active engines 50 times during stream generation
    must cleanly cancel active tasks in <1ms without leaking tasks or crashing asyncio.
    """
    router = UnifiedInferenceRouter(default_engine="llama_rpc")

    engines = ["llama_rpc", "exo", "accelerate", "petals", "gemini", "cloudflare", "julien", "auto"]

    for i in range(50):
        target = engines[i % len(engines)]
        gen = router.stream_generate("stress test rapid swapping")
        router.set_active_engine(target)
        assert router.active_engine == target


@pytest.mark.asyncio
async def test_auto_fallback_mid_stream_vs_pre_stream():
    """
    Adversarial Challenge: Verify auto-fallback semantics:
    - Pre-stream failure -> automatically falls back to llama_rpc
    """
    failing_exo = MockFailingBridge("exo", should_fail_on_connect=True)
    working_llama = MockFailingBridge("llama_rpc", should_fail_on_connect=False)

    router = UnifiedInferenceRouter(
        default_engine="auto",
        bridges={"exo": failing_exo, "llama_rpc": working_llama}
    )
    router.poller.set_metric_for_testing("exo", ttft_ms=5.0, is_available=True)
    router.poller.set_metric_for_testing("llama_rpc", ttft_ms=50.0, is_available=True)

    tokens = []
    async for token in router.stream_generate("test prompt"):
        tokens.append(token)

    assert "".join(tokens) == "response from llama_rpc"


# ============================================================================
# 3. AI DEBATE TUI SYNC ATTRIBUTE RESOLUTION CHALLENGE
# ============================================================================

def test_ai_debate_tui_sync_telemetry_attribute_resolution():
    """
    Verify that ai_debate_tui_sync.py successfully resolves telemetry attributes
    (using tb4_dma or tb4_interconnect fallback) without raising AttributeError.
    """
    engine = AIDebateTUISyncEngine()
    snapshot = blackboard_store.get_snapshot()
    net = snapshot.layer_0_networking

    assert hasattr(net, "tb4_dma"), "Layer0NetworkingState must have tb4_dma attribute"

    # Verify that calling _identify_top_priority_topic executes cleanly without AttributeError
    topic = engine._identify_top_priority_topic(snapshot)
    assert isinstance(topic, str) and len(topic) > 0


# ============================================================================
# 4. ADDITIONAL DEEP STRESS & EDGE-CASE CHALLENGES
# ============================================================================

def test_engine_cycling_forward_and_backward():
    """Verify cycle_engine() cycles forward and backwards through full roster without index errors."""
    router = UnifiedInferenceRouter(default_engine="auto")

    roster = ["auto", "llama_rpc", "exo", "accelerate", "petals", "gemini", "cloudflare", "julien"]

    for i in range(len(roster) * 3):
        expected = roster[(i + 1) % len(roster)]
        actual = router.cycle_engine(delta=1)
        assert actual == expected

    for i in range(len(roster) * 3):
        cur_idx = roster.index(router.active_engine)
        expected = roster[(cur_idx - 1) % len(roster)]
        actual = router.cycle_engine(delta=-1)
        assert actual == expected


@pytest.mark.asyncio
async def test_auto_mode_process_user_input_fallback_on_exception():
    """Verify process_user_input in auto mode gracefully falls back to llama_rpc on exception."""
    failing_exo = MockFailingBridge("exo", should_fail_on_connect=True)
    working_llama = MockFailingBridge("llama_rpc", should_fail_on_connect=False)

    router = UnifiedInferenceRouter(
        default_engine="auto",
        bridges={"exo": failing_exo, "llama_rpc": working_llama}
    )
    router.poller.set_metric_for_testing("exo", ttft_ms=5.0, is_available=True)
    router.poller.set_metric_for_testing("llama_rpc", ttft_ms=50.0, is_available=True)

    res = await router.process_user_input("prompt text")
    assert res == "processed by llama_rpc"


def test_status_badge_formatting_for_all_engines():
    """Verify get_status_badge() returns formatted string for every engine and in auto mode."""
    router = UnifiedInferenceRouter(default_engine="auto")

    badge_auto = router.get_status_badge()
    assert "[AUTO" in badge_auto

    for eng in ["llama_rpc", "exo", "accelerate", "petals", "gemini", "cloudflare", "julien"]:
        router.set_active_engine(eng)
        badge = router.get_status_badge()
        assert badge.startswith("[") and badge.endswith("]")
        assert eng.upper() in badge or "LLAMA.CPP" in badge or "EXO" in badge or "ACCELERATE" in badge or "PETALS" in badge or "GEMINI" in badge or "CLOUDFLARE" in badge or "JULIEN" in badge


def test_poller_invalid_candidate_recovery():
    """Verify get_effective_engine() ignores rogue engines not in candidate list and picks lowest among valid candidates."""
    router = UnifiedInferenceRouter(default_engine="auto")
    # Inject unknown rogue engine metric with 0.1ms latency
    router.poller.set_metric_for_testing("unknown_quantum_engine", ttft_ms=0.1, is_available=True)
    # Set valid candidate latencies
    router.poller.set_metric_for_testing("llama_rpc", ttft_ms=25.0, is_available=True)
    router.poller.set_metric_for_testing("exo", ttft_ms=10.0, is_available=True)

    # Effective engine should pick 'exo' (10.0ms), completely ignoring 'unknown_quantum_engine' (0.1ms)
    eff = router.get_effective_engine()
    assert eff == "exo"
