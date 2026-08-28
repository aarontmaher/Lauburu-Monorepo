# Milestone 1 Adversarial Challenger 2 Report

**Agent**: `challenger_m1_2` (EMPIRICAL CHALLENGER — critic, specialist)  
**Milestone**: Milestone 1 — Canonical Port Bootstrapper & Mesh Integration  
**Target Repository**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port`  
**Date**: 2026-08-28T01:42:00Z  
**Verdict**: **REQUEST_CHANGES**

---

## 1. Observation

Direct inspections, runtime probing in live Tmux sessions, and execution of a 15-test adversarial test suite (`tests/unit/test_challenger_2_m1_mesh_and_router.py`) revealed the following:

### 1.1 Bootstrapper Script (`boot_canonical_mesh.sh`)
- **Syntax & Execution**: Passes `bash -n boot_canonical_mesh.sh` with exit code 0.
- **Port Conflict Cleanup**: `lsof -ti :4000` cleanup correctly terminates stale processes before launching.
- **Readiness Polling**: `until curl -s -f http://127.0.0.1:4000/ >/dev/null 2>&1; do sleep 0.5; done` correctly synchronizes all child panes to FastAPI startup.
- **Live Tmux Validation**:
  - Window 0 (Command Center): Launches `tui/canonical_tui.py` full-screen after port 4000 is ready.
  - Window 1 (Services):
    - Pane 1.0 (`uvicorn backend.app:app --port 4000`): Runs successfully.
    - Pane 1.1 (`movesense_to_4000_bridge.py`): Starts in standby mode without Bleak and pushes telemetry.
    - Pane 1.2 (`ai_debate_tui_sync.py`): **CRASHES AT RUNTIME** on first cycle.

### 1.2 Declarative Multiplexer (`canonical_mesh.kdl`)
- **Syntax & Structure**: Valid KDL with balanced braces (12 open, 12 close).
- **Paths & Panes**: Tab structure separates "Command Center" and "Background Services".
- **Path Resolution**: Relative paths (`../../03_biometrics_and_telemetry/movesense_to_4000_bridge.py`, `tui/services/ai_debate_tui_sync.py`, `tui/canonical_tui.py`) exist and resolve correctly from `01_apps/canonical_port`.

### 1.3 UnifiedInferenceRouter & `get_effective_engine()` Resilience
- **Missing API Keys**: When `GEMINI_API_KEY`, `CLOUDFLARE_API_TOKEN`, and `JULIEN_API_KEY` are unset, `get_effective_engine()` in `auto` mode strictly filters out all 3 cloud engines and routes exclusively to healthy local backends (`llama_rpc`, `exo`, `accelerate`, `petals`).
- **Dynamic TTFT Auto-Routing**: Dynamically selects the minimum latency engine among candidate bridges.
- **Total External Outage**: When all external backends are offline (`ttft_ms = inf`, `is_available = False`), `get_effective_engine()` safely defaults to `llama_rpc`.
- **Forced Engine Swaps**: `set_active_engine()` successfully overrides `auto` mode across all 8 supported engines and all known aliases (`gemini_pro`, `workers_ai`, `cf`, `julien_ultra`, `llamacpp`, `ring`, `mps`, `dynamic`).
- **Stream Cancellation**: 50 consecutive mid-generation engine swaps execute in <1ms without leaking asyncio tasks or raising unhandled exceptions.
- **Candidate Protection**: Poller metrics with unknown/rogue engine names are strictly ignored by candidate allowlists in `get_effective_engine()`.

### 1.4 Confirmed Defect: `ai_debate_tui_sync.py` Telemetry Attribute Mismatch
- **File**: `tui/services/ai_debate_tui_sync.py:149`
- **Line Content**:
  ```python
  tb4 = net.tb4_interconnect
  ```
- **Error Stack Trace** (Captured directly from Tmux Pane 1.2 and verified in unit tests):
  ```
  Traceback (most recent call last):
    File "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/tui/services/ai_debate_tui_sync.py", line 105, in execute_sync_cycle
      topic = self._identify_top_priority_topic(snapshot)
    File "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/tui/services/ai_debate_tui_sync.py", line 149, in _identify_top_priority_topic
      tb4 = net.tb4_interconnect
            ^^^^^^^^^^^^^^^^^^^^
  AttributeError: 'Layer0NetworkingState' object has no attribute 'tb4_interconnect'
  ```
- **Root Cause**: `Layer0NetworkingState` in `tui/models/blackboard_models.py:195` defines `tb4_dma: Tb4DmaInterconnect`. Accessing `.tb4_interconnect` raises `AttributeError` and crashes the synchronization daemon spawned by the bootstrapper.

---

## 2. Logic Chain

1. **Premise 1**: The bootstrapper (`boot_canonical_mesh.sh` Pane 1.2) and Zellij layout (`canonical_mesh.kdl`) spawn `ai_debate_tui_sync.py` as a core background service for continuous AI debate synchronization.
2. **Premise 2**: Upon execution, `AIDebateTUISyncEngine.execute_sync_cycle()` ingests a telemetry snapshot and calls `_identify_top_priority_topic(snapshot)`.
3. **Premise 3**: Line 149 in `ai_debate_tui_sync.py` accesses `snapshot.layer_0_networking.tb4_interconnect`.
4. **Premise 4**: In `tui/models/blackboard_models.py:195`, `Layer0NetworkingState` defines `tb4_dma`, not `tb4_interconnect`.
5. **Conclusion**: When booted via `boot_canonical_mesh.sh` or `canonical_mesh.kdl`, Pane 1.2 immediately terminates with `AttributeError`, leaving the AI Debate synchronization pipeline dead on launch.

---

## 3. Caveats

- **Physical BLE Hardware**: BLE testing operated in tether standby mode because physical Movesense sensor hardware is external; Rule #0 invariants (clean `--` waiting states) were properly upheld.
- **Pre-existing Voice Stress Test**: `test_voice_challenger_stress.py::test_stress_simultaneous_audio_stream_and_ui_commands` failed on a strict timing assertion (27.6ms vs 15.0ms SLA); this is part of Milestone 5 voice stress suite and unrelated to Milestone 1 infrastructure.

---

## 4. Conclusion

**Verdict: REQUEST_CHANGES**

The core infrastructure repairs in Milestone 1 (inference bridge syntax, cloud bridge filtering in TTFT poller, DaemonSupervisor circuit breaking, REPL slash command security, and HTTP readiness polling) are well-architected and robust.

However, the bootstrapper directly launches `ai_debate_tui_sync.py` in Pane 1.2, which consistently crashes on launch due to the attribute mismatch on line 149.

### Required Action for Worker:
In `tui/services/ai_debate_tui_sync.py:149`, update:
```python
# Before
tb4 = net.tb4_interconnect

# After
tb4 = getattr(net, "tb4_dma", None) or getattr(net, "tb4_interconnect", None)
```

---

## 5. Verification Method

To independently verify the adversarial test suite and reproduce the findings:

```bash
# 1. Run Challenger 2 Adversarial Test Suite (15 tests)
uv run pytest tests/unit/test_challenger_2_m1_mesh_and_router.py -v

# 2. Empirically reproduce ai_debate_tui_sync.py runtime crash
uv run python -c "from tui.services.ai_debate_tui_sync import AIDebateTUISyncEngine; AIDebateTUISyncEngine().execute_sync_cycle()"

# 3. Verify Tmux Detached Boot and Inspect Pane 1.2
./boot_canonical_mesh.sh --detached
sleep 3
tmux capture-pane -p -t lauburu-canonical:1.2
./boot_canonical_mesh.sh --kill
```

### Invalidation Conditions
- If `AIDebateTUISyncEngine().execute_sync_cycle()` runs without raising `AttributeError`, the bug has been fixed.
- If `test_challenger_2_m1_mesh_and_router.py` passes all 15 tests including telemetry attribute resolution, the change request can be resolved to APPROVE.
