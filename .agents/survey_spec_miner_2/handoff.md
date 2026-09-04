# 👑 Specification Mining Handoff Report: Confidence Gating, Quota Harvester & Dual-World MCTS Simulation

**Subsystem**: `05_agents_and_swarms`, `02_ai_models_and_inference/simulation`, `00_core_infrastructure/cloudflare`  
**Agent ID**: `survey_spec_miner_2`  
**Date**: `2026-09-01T09:41:00Z`  
**Target Milestone**: Dual-World Sovereign Mesh Swarm & Continuous Free Cloud Quota Automation

---

## 1. Observation

Direct inspection of the Lauburu Monorepo codebase and test execution yielded the following concrete, verbatim evidence:

### 1.1 Dynamic Confidence Gating & Swarm Runner (`05_agents_and_swarms/high_confidence_swarm_runner.py`)
- **Confidence Threshold**: Defined in `DualWorldConfidenceGate.CONFIDENCE_THRESHOLD = 0.85` (Line 35).
- **Scoring Function**: `evaluate_action_confidence(task_desc: str, target_domain: str, has_test_harness: bool = True) -> Tuple[float, str]` (Lines 38–56):
  - Base confidence = 0.70.
  - If `has_test_harness` is True: $+0.15$.
  - Domain modifier: $+0.10$ for `["commerce", "biometrics", "rust_tui", "tb4_dma", "mcp_bridge"]`; $-0.25$ for `["speculative_frontier_physics", "unverified_unquantized_kernel"]`.
  - Jitter range: $\text{Uniform}(-0.03, +0.04)$, clamped to $[0.40, 0.99]$.
- **Routing Decision**:
  - `score >= 0.85` $\rightarrow$ `DIRECT_EXECUTION` (executes via Free Cloud Oracle e.g. Gemini 3.7 Flash Free 15 RPM, Dual-World simulation pass).
  - `score < 0.85` $\rightarrow$ `LOCAL_TRAINING_FALLBACK` (generates adversarial counter-example via Huihui-27B Devil's Advocate, appends training pair to `continuous_lora_dataset.jsonl`).
- **Resource Constraints**:
  - Mac Mini M4 Pro RAM headroom: $\ge 4.5\text{ GB}$ (tracked at 4.7 GB in `high_confidence_runner_state.json`).
  - OpenWrt Router Sentinel RSS RAM: $\le 28.0\text{ MB}$ (tracked at 27.8 MB in `high_confidence_runner_state.json`).
  - Cloud spend: Strictly $\$0.00\text{ AUD}$.

### 1.2 Free Cloud AI API Quota Harvester & Zero-Dollar Spend Enforcement (`cloud_oracle_shadow.py`, `ai_gateway/free_tier_token_harvester.py`, `ai_gateway/budget_proxy.py`)
- **Rate Pacing Math**: `PacedTokenBucketRateLimiter` enforces $14.2\text{ RPM}$ ($\Delta t = \frac{60.0}{14.2} \approx 4.22535\text{ s}$ interval) against Google AI Studio Free Tier (`cloud_oracle_shadow.py` Lines 167–242).
- **Daily Quota Ceiling**: `DailyQuotaManager` enforces a 1,500 Requests Per Day (RPD) limit for Google AI Studio with UTC date rollover and exponential backoff circuit breaker on HTTP 429 (`cloud_oracle_shadow.py` Lines 249–358).
- **4-Tier Waterfall Hierarchy**:
  1. **Tier 1**: Google AI Studio Free Tier (`gemini-3.7-flash`, `gemini-3.7-flash-high`, `gemini-2.5-flash`, `gemini-2.0-flash`, `gemini-1.5-flash`, `gemini-1.5-pro-free`).
  2. **Tier 2**: Cloudflare Workers AI Free Tier ($10\text{k free daily Neurons}$, `@cf/meta/llama-3.1-8b-instruct`, `@cf/qwen/qwen2.5-coder-32b-instruct`, `@cf/deepseek-ai/deepseek-r1-distill-qwen-32b`).
  3. **Tier 3**: Local Hardware Mesh RPC (Ports 8081–8088 / `llama.cpp` / `Petals` / `Exo`).
  4. **Tier 4**: Deterministic Offline Heuristic Engine (100% Zero-Mock AST-valid generation).
- **Dual-Gate Zero-Dollar Spend Invariant**:
  - `_assert_zero_spend(provider, model, cost_usd)` verifies `is_free_tier` and `assert cost_usd == 0.00`.
  - Non-zero cost or paid models (`gpt-4`, `claude-3`, `o1-`, etc.) raise `ZeroDollarSpendViolationError`.
  - In `budget_proxy.py`, paid endpoint fallbacks are governed by a hard kill-switch returning HTTP 429 when budget is exhausted.

### 1.3 Dual-World MCTS Lookahead Simulation (`dual_world_mcts.py`, `agentworld_driver.py`, `webworld_driver.py`, `lookahead_interceptor.py`)
- **PUCT Search Formula**:
  $$\text{PUCT}(s, a) = Q(s, a) + c_{\text{puct}} \cdot P(s, a) \cdot \frac{\sqrt{\sum_b N(s, b)}}{1 + N(s, a)}$$
  where $c_{\text{puct}} = 1.414$, $P(s, a) \in (0, 1]$ is policy prior, $Q(s, a) = \frac{W(s, a)}{N(s, a)}$.
- **Composite Value Valuation Equation**:
  $$V(s) = \text{clamp}\left(0.25 \cdot V_{\text{oracle}} + 0.35 \cdot V_{\text{agent}} + 0.25 \cdot V_{\text{web}} - 0.15 \cdot P_{\text{devil}}, 0.0, 1.0\right)$$
  - $V_{\text{oracle}} \in [0, 1]$: Cloud Oracle alignment score.
  - $V_{\text{agent}} \in [0, 1]$: AgentWorld-35B OS/AST test outcome (Port 8086).
  - $V_{\text{web}} \in [0, 1]$: WebWorld-32B DOM/API contract conformance (Port 8088).
  - $P_{\text{devil}} \in [0, 1]$: Huihui-27B Devil's Advocate adversarial vulnerability penalty (Port 8085).
- **Admission Gate Quantitative Invariants (`LookaheadInterceptor`)**:
  - Safety Score: $S \ge 0.90$
  - Regression Probability: $P_{\text{reg}} \le 0.05$
  - Layout Overflows: $O_{\text{layout}} == 0$
  - Simulation Confidence: $C_{\text{sim}} \ge 0.85$
  - Composite Score: $S_{\text{composite}} = 0.40 \cdot S + 0.30 \cdot (1 - P_{\text{reg}}) + 0.20 \cdot C_{\text{sim}} + 0.10 \cdot L_{\text{factor}}$
  - Lookahead Steps: 30-step trajectory rollout in Copy-on-Write VFS / ShadowDOM.
- **Verification Rule for MCTS Terminal State**:
  $$\text{is\_verified} = \text{ast\_valid} \land (V_{\text{agent}} \ge 0.85) \land (P_{\text{devil}} \le 0.20)$$

### 1.4 Empirical Test Execution Results
- `python3 -m unittest 05_agents_and_swarms/test_high_confidence_runner.py`: 3 tests ran, **0 failures (OK)** in 0.001s.
- `pytest 05_agents_and_swarms/test_dual_world_mcts.py -v`: 29 tests ran, **29 PASSED** in 11.59s.
- `python3 -m unittest 02_ai_models_and_inference/tests/test_dual_world_simulation.py`: 22 tests ran, **0 failures (OK)** in 0.007s.
- `pytest 05_agents_and_swarms/test_cloud_oracle_shadow.py -v`: 23 tests ran, **23 PASSED** in 3.10s.

---

## 2. Logic Chain

1. **Confidence Routing Invariant**:
   From `high_confidence_swarm_runner.py` and `test_high_confidence_runner.py`, when a task exhibits clear domain semantics and an active test harness, `DualWorldConfidenceGate` outputs confidence $\ge 0.85$, selecting `DIRECT_EXECUTION`. If the task involves speculative/unverified domains or lacks test harnesses, confidence drops below $0.85$, triggering `LOCAL_TRAINING_FALLBACK`.
2. **Zero-Spend Free Quota Harvesting**:
   From `cloud_oracle_shadow.py` and `free_tier_token_harvester.py`, rate limits are paced strictly at $14.2\text{ RPM}$ with a 1,500 RPD daily quota. If Google AI Studio returns HTTP 429, the waterfall cascades to Tier 2 (Cloudflare 10k Neurons), Tier 3 (Local Mesh Ports 8081-8088), and Tier 4 (Deterministic Offline). Non-zero costs trigger `ZeroDollarSpendViolationError`, guaranteeing $\$0.00\text{ AUD}$ total spend.
3. **Dual-World MCTS Regression Prevention**:
   From `dual_world_mcts.py`, `agentworld_driver.py`, `webworld_driver.py`, and `lookahead_interceptor.py`, candidate code patches and actions undergo 30-step simulation in Copy-on-Write memory (`CopyOnWriteVFS` and `ShadowDOM`). The composite value function weights Oracle, AgentWorld OS execution, WebWorld DOM/WCAG audits, and subtracts Devil's Advocate penalties. Only trajectories satisfying all 4 admission thresholds ($S \ge 0.90, P_{\text{reg}} \le 0.05, O_{\text{layout}} == 0, C_{\text{sim}} \ge 0.85$) are certified.
4. **Continuous Learning Loop**:
   Both `high_confidence_swarm_runner.py`, `free_tier_token_harvester.py`, and `dual_world_mcts.py` serialize verified and adversarial failure trajectories into `/Users/aaron/DFS_UNIFIED/lora_datasets/continuous_lora_dataset.jsonl` for local LoRA fine-tuning.

---

## 3. Caveats

1. **Live Network vs Offline Deterministic Mode**:
   In test and offline environments, live ports (`:8085`, `:8086`, `:8088`, `:18802`) automatically fall back to the deterministic zero-mock offline engines (`DeterministicOfflineRolloutEngine`, `DeterministicOfflineOracle`). The interface signatures and return schemas are 100% identical between live and offline modes.
2. **Hardware Dynamic Limits**:
   Mac Mini M4 Pro RAM headroom must maintain $\ge 4.5\text{ GB}$ free headroom, and OpenWrt Router Sentinel RSS RAM must remain $\le 28.0\text{ MB}$.

---

## 4. Conclusion

The specification contracts for **Dynamic Confidence Gating ($\tau = 0.85$)**, **Free Cloud AI API Quota Harvesting ($\$0.00\text{ spend}$)**, and **Dual-World MCTS Lookahead Simulation** are completely defined, fully implemented, and validated by comprehensive unit and integration test suites in the monorepo.

---

## 5. Verification Method

To independently verify the discovered specifications and test suites:

```bash
# 1. Verify High Confidence Swarm Runner & Fallback Gating
python3 -m unittest 05_agents_and_swarms/test_high_confidence_runner.py

# 2. Verify Dual-World MCTS Engine, PUCT Math & Valuation
pytest 05_agents_and_swarms/test_dual_world_mcts.py -v

# 3. Verify Copy-on-Write AgentWorld, WebWorld & Lookahead Interceptor
python3 -m unittest 02_ai_models_and_inference/tests/test_dual_world_simulation.py

# 4. Verify Free Cloud Oracle Waterfall & Zero-Spend Assertions
pytest 05_agents_and_swarms/test_cloud_oracle_shadow.py -v
```

---

## Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | Confidence Gating | `DualWorldConfidenceGate.evaluate_action_confidence` | Evaluates prospective monorepo actions based on domain clarity, test harness availability, and AST validity | `task_desc: str, target_domain: str, has_test_harness: bool` | `Tuple[float, str]` (score $\in [0.40, 0.99]$, mode: `DIRECT_EXECUTION` or `LOCAL_TRAINING_FALLBACK`) | Clamped to $[0.40, 0.99]$, defaults to fallback on low score | `05_agents_and_swarms/high_confidence_swarm_runner.py:34` |
| 2 | Swarm Execution | `HighConfidenceSwarmRunner.execute_step` | Coordinates direct execution vs local training fallback and updates persistent state | `task_id: str, task_desc: str, domain: str, has_test_harness: bool` | `Dict[str, Any]` (state dictionary with `selected_mode`, `oracle`, `mcts_lookahead`, `action_status`) | Appends training pair to `continuous_lora_dataset.jsonl` on fallback | `05_agents_and_swarms/high_confidence_swarm_runner.py:58` |
| 3 | Rate Limiting | `PacedTokenBucketRateLimiter` | Enforces 14.2 RPM (~4.225s interval) rate-pacing for Google AI Studio Free Tier | `target_rpm: float = 14.2, capacity: float = 1.0` | `wait_time: float` (seconds waited) | Sleeps until token available in blocking mode | `05_agents_and_swarms/cloud_oracle_shadow.py:166` |
| 4 | Quota Management | `DailyQuotaManager` | Governs 1,500 RPD daily quota with UTC date rollover and circuit breaker on 429 | `quota_file: Path, daily_limit: int = 1500` | `can_request_google: bool`, records stats in JSON | Engages exponential backoff circuit breaker on 429 | `05_agents_and_swarms/cloud_oracle_shadow.py:248` |
| 5 | Zero-Spend Enforcement | `CloudOracleShadow._assert_zero_spend` | Dual-gate zero-spend assertion verifying free model whitelist and `cost_usd == 0.00` | `provider: str, model: str, cost_usd: float` | `None` (validates invariant) | Raises `ZeroDollarSpendViolationError` | `05_agents_and_swarms/cloud_oracle_shadow.py:546` |
| 6 | Cloud Waterfall | `CloudOracleShadow.query_oracle` | 4-tier waterfall: Google Free $\rightarrow$ Cloudflare Free $\rightarrow$ Local Mesh $\rightarrow$ Deterministic Offline | `prompt: str, task_context: dict, model: str, provider: str` | `Dict[str, Any]` (`thought`, `solution`, `provider`, `cost_usd: 0.00`, `is_free_tier: True`) | Cascades to next tier on network error / 429 | `05_agents_and_swarms/cloud_oracle_shadow.py:773` |
| 7 | Continuous Harvesting | `FreeTierTokenHarvester` | Harvests reasoning traces across domains and distills into LoRA datasets | Domain prompt pool (`rust_metal_dsp`, `sharding`, `security`, `ast`, `swe_bench`) | JSONL records in `continuous_lora_dataset.jsonl` | Logs errors, continues loop | `05_agents_and_swarms/ai_gateway/free_tier_token_harvester.py:64` |
| 8 | Budget Proxy | `FastAPI Budget Proxy` | Intercepts AI calls, routes free providers ($0.00), blocks paid calls with $1.00 kill switch | HTTP `/v1/chat/completions`, `/health`, `/status`, `/reset` | HTTP 200 response with `X-Lauburu-Tier: free-tier` | HTTP 429 `BudgetExceeded` when paid limit reached | `05_agents_and_swarms/ai_gateway/budget_proxy.py:339` |
| 9 | MCTS Node | `MCTSNode` | State node tracking patch AST diff, $N$, $W$, $Q$, prior $P$, depth, simulation scores | `patch: str, parent: MCTSNode, action: str, prior_p: float` | Object with `puct_score()`, `select_child()`, `update()` | Clamps prior $P \in [1e-4, 1.0]$ | `05_agents_and_swarms/dual_world_mcts.py:712` |
| 10 | MCTS Valuation | `CompositeValueCalculator.compute_value` | Calculates $V(s) = \text{clamp}(0.25 V_o + 0.35 V_a + 0.25 V_w - 0.15 P_d, 0.0, 1.0)$ | `v_oracle, v_agent, v_web, p_devil: float` | `float \in [0.0, 1.0]` | Clamps inputs and output to $[0.0, 1.0]$ | `05_agents_and_swarms/dual_world_mcts.py:687` |
| 11 | MCTS Engine | `DualWorldMCTSEngine.search` | PUCT tree search orchestrating AST mutations, multi-world simulations, and LoRA sink | `task_instance: dict, oracle_guidance: dict, iterations: int` | `MCTSResult` dict (`best_patch`, `value`, `is_verified`, `trajectories`) | Falls back to root if no children expand | `05_agents_and_swarms/dual_world_mcts.py:835` |
| 12 | OS World Simulator | `AgentWorldSimulator` / `AgentWorldDriver` | Simulates OS syscalls, terminal execution, and MCP tools in Copy-on-Write VFS | `patch_str: str, task_context: dict` or shell commands | `Dict[str, Any]` ($V_{\text{agent}}$, `ast_valid`, `simulated_exit_code`) | Returns $V_{\text{agent}} = 0.0$, exit code 1 on AST error | `05_agents_and_swarms/dual_world_mcts.py:378` & `02_ai_models_and_inference/simulation/agentworld_driver.py:214` |
| 13 | Web World Simulator | `WebWorldSimulator` / `WebWorldDriver` | Simulates React DOM, layout overflow, WCAG 2.1 AA contrast, and route 404s in ShadowDOM | `patch_str: str, task_context: dict` or DOM mutations | `Dict[str, Any]` ($V_{\text{web}}$, `contract_satisfied`, `layout_overflows`) | Returns $V_{\text{web}} = 0.0$, HTTP 500 on AST syntax error | `05_agents_and_swarms/dual_world_mcts.py:449` & `02_ai_models_and_inference/simulation/webworld_driver.py:258` |
| 14 | Devil's Advocate | `DevilsAdvocateClient` | Adversarial code auditor detecting regex bypasses, unhandled exceptions, and concurrency risks | `task_instance: dict, patch_str: str` | `Dict[str, Any]` (`penalty \in [0, 1]`, `critique: str`) | Returns maximum penalty $1.0$ on syntax violation | `05_agents_and_swarms/dual_world_mcts.py:519` |
| 15 | Router Sentinel | `RouterSentinelMonitor` | OpenWrt router monitor verifying embedded RAM $\le 28\text{ MB}$, $0\%$ packet loss, latency $< 50\text{ ms}$ | HTTP probe on Port 18802 `/api/health` | `Dict[str, Any]` (`status`, `healthy: bool`, `ram_footprint_mb`, `packet_loss_pct`) | Returns `healthy: False` if RAM $> 28.0\text{ MB}$ or loss $> 0\%$ | `05_agents_and_swarms/dual_world_mcts.py:623` |
| 16 | Lookahead Interceptor | `LookaheadInterceptor.simulate_trajectory` | Intercepts actions and executes 30-step trajectory rollout against quantitative admission gates | `action_type: str, action_payload: dict, lookahead_steps: int = 30` | `Tuple[bool, float, Dict[str, Any]]` (`admitted`, `composite_score`, `diagnostics`) | Rejects if $S < 0.90$, $P_{\text{reg}} > 0.05$, $O > 0$, or $C < 0.85$ | `02_ai_models_and_inference/simulation/lookahead_interceptor.py:56` |
| 17 | Router Dual-World Tester | `RouterDualWorldTester.evaluate_healing_trajectory` | Validates self-healing actions (e.g. Tailscale bounce, Wi-Fi channel rebalance) in dual-world lookahead | `action_name: str, parameters: dict, lookahead_steps: int = 30` | `DualWorldValidationResult` (`is_safe`, `overall_confidence`, `recommended_action`) | Recommends `REJECT_OR_FALLBACK` on invariant breach | `02_ai_models_and_inference/simulation/router_dual_world_tester.py:61` |
| 18 | Batch Proof Adjudicator | `FreeApiProofAdjudicator` | Stages locally debated claims (batch $N=3$) and dispatches batch review to Free Cloud AI | `claim_record: dict` | Updates pool, commits certified proofs to Obsidian & LoRA dataset | Re-probes or rejects if consensus $< 0.90$ | `05_agents_and_swarms/ai_debate/free_api_proof_adjudicator.py:33` |

---

## Edge Cases

| # | Feature | Input | Observed Behavior |
|---|---------|-------|-------------------|
| 1 | `DualWorldConfidenceGate` | Target domain `"speculative_frontier_physics"`, `has_test_harness=False` | Returns confidence score $< 0.85$ (e.g. 0.490), routes to `LOCAL_TRAINING_FALLBACK`. |
| 2 | `DualWorldConfidenceGate` | Target domain `"biometrics"`, `has_test_harness=True` | Returns confidence score $\ge 0.85$ (e.g. 0.959), routes to `DIRECT_EXECUTION`. |
| 3 | `PacedTokenBucketRateLimiter` | Immediate consecutive calls to `acquire(blocking=True)` | First call returns 0.0s wait; second call sleeps ~4.225s to enforce 14.2 RPM limit. |
| 4 | `DailyQuotaManager` | Daily requests count reaches 1,500 RPD | `can_request_google()` returns `False`, blocking further calls until UTC midnight rollover. |
| 5 | `DailyQuotaManager` | Upstream returns HTTP 429 | `record_429()` triggers exponential backoff circuit breaker ($5 \times 2^{k-1}$ seconds). |
| 6 | `CloudOracleShadow` | Query with `model="gpt-4o"` or `model="claude-3-5-sonnet"` | Raises `ZeroDollarSpendViolationError` immediately before network dispatch. |
| 7 | `CloudOracleShadow` | Upstream Google AI Studio returns HTTP 429 | Cascades to Tier 2 (Cloudflare Workers AI); if unavailable, cascades to Tier 3 (Local Mesh) and Tier 4 (Deterministic Offline). |
| 8 | `DeterministicOfflineOracle` | Regex trailing newline task (`django-11099`) | Generates unified diff with `\A` and `\Z` anchors; verified syntactically via AST diff parser. |
| 9 | `DeterministicOfflineOracle` | Fallible exception task (`pytest-7168`) | Generates defensive `try-except Exception` block; verified syntactically via AST diff parser. |
| 10 | `DeterministicOfflineRolloutEngine` | Patch with syntax error (`def broken(:`) | Returns $V_{\text{agent}} = 0.0$, `ast_valid: False`, exit code 1, test failed. |
| 11 | `WebWorldDriver` / `ShadowDOM` | Viewport 1280px, element width 1600px | Detects `VIEWPORT_HORIZONTAL_OVERFLOW`, increments `layout_overflows`, safety score penalised. |
| 12 | `WebWorldDriver` / `ShadowDOM` | Foreground `#444444` on Background `#333333` (contrast 1.34:1) | Flags `WCAG_CONTRAST_VIOLATION` (requires $\ge 4.5:1$). |
| 13 | `WebWorldDriver` / `ShadowDOM` | Link with `href="/non_existent_page"` | Detects `BROKEN_INTERNAL_ROUTE_404`, triggers regression penalty. |
| 14 | `DevilsAdvocateClient` | Patch using line anchor `$` instead of `\Z` in validator | Assigns penalty $\ge 0.70$ and critiques "Trailing newline bypass via line anchor '$'". |
| 15 | `DevilsAdvocateClient` | Patch using strict string anchors `\A` and `\Z` | Assigns penalty $\le 0.20$ and notes "string terminator '\Z' anchors verified". |
| 16 | `RouterSentinelMonitor` | Router RSS RAM at 21.8 MB ($< 28.0$ MB) and 0% packet loss | Reports `healthy: True`, `status: "HEALTHY"`, `is_ram_compliant: True`. |
| 17 | `RouterSentinelMonitor` | Router RSS RAM exceeds 28.0 MB | Reports `healthy: False`, `status: "DEGRADED"`. |
| 18 | `CompositeValueCalculator` | Rollout values $(V_o=1.0, V_a=1.0, V_w=1.0, P_d=0.0)$ | Value is $0.25(1) + 0.35(1) + 0.25(1) - 0.15(0) = 0.85$. |
| 19 | `CompositeValueCalculator` | Input values exceeding $[0, 1]$ bounds (e.g. 2.0, -1.0) | Clamped safely to $[0, 1]$ before calculation. |
| 20 | `LookaheadInterceptor` | Dangerous command `rm -rf /` | Blocked by safety policy; returns `admitted: False`, `verdict: "REJECTED_GATING_BREACH"`. |
| 21 | `LookaheadInterceptor` | Post-admission callback when action admitted | `intercept_and_execute` runs callback and records `execution_status: "EXECUTED_SUCCESS"`. |
| 22 | `LookaheadInterceptor` | Post-admission callback when action rejected | Callback is NOT executed; records `execution_status: "BLOCKED_BY_GATING"`. |
