# Continuous AI Arena — 4-Tier Test Infrastructure Specification

**Document Version:** 1.0.0-CANONICAL  
**Date:** 2026-08-28T02:47:32Z  
**Author:** `sub_orch_e2e_tests` (E2E Testing Track Orchestrator)  
**Target System:** Continuous AI Arena (`PROJECT.md`)  
**Repository:** `Lauburu-Monorepo`  
**Test Suite:** `tests/e2e/test_continuous_ai_arena_4tier.py`  
**Master Runner:** `tests/e2e/run_all_e2e.py`

---

## 1. Executive Test Strategy & Opaque-Box Methodology

The **Continuous AI Arena** transforms every user-facing AI interaction into an automated, continuous tournament trial across the Lauburu mesh ecosystem. To guarantee 100% reliability, zero-latency user degradation, cryptographic state integrity, and zero-mock truth adherence, this test infrastructure enforces a strict **4-Tier Opaque-Box Validation Hierarchy**.

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              CONTINUOUS AI ARENA — 4-TIER TEST HIERARCHY                               │
├────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                        │
│   TIER 1: FEATURE COVERAGE (≥5 Tests per Feature F1–F9 = 52 Total Tests)                               │
│   • F1: Dynamic Champion Resolution (Leaderboard mtime debounce, fallback defaults, schema parsing)    │
│   • F2: Synchronous Champion Dispatch (0ms latency overhead, token streaming, engine routing)          │
│   • F3: Asynchronous Challenger Queue (Bounded queue, async background worker, lifecycle safety)       │
│   • F4: Challenger Pool Cycler (Local 100B+/70B & Cloud API rotation, timeout isolation)               │
│   • F5: Tri-Orchestrator Blind Grading (Alias anonymization, 3-judge panel, pairwise scoring)          │
│   • F6: Dynamic Multi-Factor ELO Engine (6-factor K-factor, atomic POSIX save, Schema v7 validation)   │
│   • F7: Dynamic Champion Promotion (Challenger victory ELO overtakes, subsequent prompt auto-swap)     │
│   • F8: Tri-Vault Logging (DPO/SFT JSONL dataset sinks, Obsidian Markdown debate transcripts)          │
│   • F9: Zero-Mock Validation & Truth Compliance (Rule #0 compliance, zero synthetic data arrays)       │
│                                                                                                        │
│   TIER 2: BOUNDARY VALUE & CORNER CASES (8 Tests)                                                      │
│   • 15.0s challenger timeout handling without champion degradation                                     │
│   • Offline local model / RPC socket drop detection                                                    │
│   • Cloud API HTTP 429 rate limit cooldown and retry suppression                                       │
│   • Empty, whitespace-only, and ultra-long prompt ingestion                                            │
│   • Corrupted / missing leaderboard JSON auto-healing and fallback                                     │
│   • Extreme ELO divergence (|R_A - R_B| ≥ 1000) logistic boundary clamping                             │
│                                                                                                        │
│   TIER 3: CROSS-FEATURE COMBINATIONS & INTEGRATION (6 Tests)                                           │
│   • Complete match outcomes: Champion Win, Challenger Win, and Draw                                    │
│   • Full ELO flip triggering dynamic champion swap on the immediate next prompt                        │
│   • Multi-factor K-factor dynamics under heavy concurrent load (varying size/token/consensus factors)  │
│   • Concurrent multi-trial queue processing with atomic disk write lock contention                     │
│                                                                                                        │
│   TIER 4: REAL-WORLD WORKLOAD SCENARIOS (4 Comprehensive Scenarios)                                    │
│   • 10-turn continuous conversational thread triggering 10 shadow arena background trials              │
│   • Bounded background worker concurrency with 0ms impact on user response stream                      │
│   • 24/7 LoRA DPO and Obsidian transcript persistence across continuous operations                     │
│   • Full End-to-End System Life-Cycle: Prompt → Stream → Async Challengers → Blind Grading →          │
│     Dynamic ELO Update → Tri-Vault Persistence → Dynamic Champion Handover                             │
│                                                                                                        │
└────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Test Tier Breakdown & Requirement Matrix

### Tier 1: Feature Coverage (Category-Partition Testing)
Every feature F1 through F9 is validated by at least 5 dedicated, isolated unit and functional tests:

| Feature ID | Feature Name | Minimum Tests | Implemented Tests | Primary Verification Objective |
| :--- | :--- | :--- | :--- | :--- |
| **F1** | Dynamic Champion Resolution | ≥5 | 6 | Reads #1 ranked model from ELO leaderboard; verifies mtime debounced caching; validates fallback on missing/corrupted file. |
| **F2** | Synchronous Champion Dispatch | ≥5 | 5 | Ensures immediate response to user with 0ms added delay; validates token streaming and metadata. |
| **F3** | Asynchronous Challenger Queue | ≥5 | 5 | Validates non-blocking background queue enqueue, bounded capacity, async worker lifecycle, and clean drain. |
| **F4** | Challenger Pool Cycler | ≥5 | 6 | Rotates local 100B+ GGUFs, 70Bs, and cloud APIs; excludes active champion; enforces 15.0s timeout and error capture. |
| **F5** | Tri-Orchestrator Blind Grading | ≥5 | 5 | Strips headers; generates randomized aliases ($\alpha, \beta, \gamma$); runs 3-judge judicial panel across 5 scoring pillars. |
| **F6** | Dynamic Multi-Factor ELO Engine | ≥5 | 6 | Calculates logistic expected outcomes, dynamic 6-factor K-factor ($K = K_0 \cdot \prod \eta$), atomic POSIX save, Schema v7. |
| **F7** | Dynamic Champion Promotion | ≥5 | 5 | Verifies ELO overtake automatically updates leaderboard rankings and promotes winner to #1 for next prompt. |
| **F8** | Tri-Vault Logging | ≥5 | 5 | Appends DPO/SFT JSONL pairs to `/lora_datasets/`; writes Markdown debate transcripts to `obsidian_vault/01_DEBATES/`. |
| **F9** | Zero-Mock Validation | ≥5 | 5 | Enforces Rule #0 (zero simulated data arrays); validates authentic token/latency telemetry; verifies $\eta_{\text{truth}}$. |
| **TOTAL** | **Tier 1 Feature Tests** | **≥45** | **52** | **Full Feature Coverage Across F1–F9** |

---

### Tier 2: Boundary Value Analysis & Corner Cases
Tests system behavior under edge conditions, faults, and boundary thresholds:

1. `test_t2_01_challenger_timeout_isolation`: When a challenger times out (>15.0s), the champion response is unaffected, and grader records a timed-out loss for the challenger.
2. `test_t2_02_offline_local_model_handling`: Sockets that fail to connect are flagged `offline` without throwing unhandled exceptions to the router.
3. `test_t2_03_api_rate_limit_429_cooldown`: When a cloud API provider returns HTTP 429, it enters cooldown mode for 60s and is excluded from subsequent challenger rounds.
4. `test_t2_04_empty_and_whitespace_prompt_handling`: Empty prompts or whitespace strings are safely validated with appropriate default responses.
5. `test_t2_05_extreme_token_length_context_clipping`: Prompts exceeding model context window are safely clipped or penalized via token efficiency multipliers.
6. `test_t2_06_corrupted_leaderboard_json_recovery`: Corrupted or truncated JSON file triggers fallback champion resolution and auto-heals file.
7. `test_t2_07_extreme_elo_difference_clamping`: ELO differences $\ge 1000$ points produce stable expected outcomes bounded in $(0.001, 0.999)$ without overflow.
8. `test_t2_08_all_challengers_failing_resilience`: If both challengers fail concurrently, champion retains rating and no corrupted match history is written.

---

### Tier 3: Pairwise & Combinatorial Integration
Validates cross-feature interactions and state transitions:

1. `test_t3_01_champion_win_outcome_flow`: Champion beats both challengers → Champion ELO increases, challengers decrease, rankings maintained.
2. `test_t3_02_challenger_win_and_dynamic_swap`: Challenger beats Champion with large score differential → ELO overtakes Champion → Subsequent prompt immediately resolves new Champion.
3. `test_t3_03_draw_outcome_elo_convergence`: Evenly matched models result in minimal ELO adjustment towards convergence.
4. `test_t3_04_multi_factor_k_factor_dynamics`: Evaluates composite K-factor across all 6 efficiency multipliers ($\eta_{\text{type}}, \eta_{\text{size}}, \eta_{\text{token}}, \eta_{\text{consensus}}, \eta_{\text{compute}}, \eta_{\text{truth}}$).
5. `test_t3_05_concurrent_queue_load_under_pressure`: 10 concurrent prompts dispatched rapidly into queue; all processed without race conditions or memory leaks.
6. `test_t3_06_atomic_file_lock_collision_resilience`: Concurrent writes to `canonical_ai_leaderboard.json` execute safely via POSIX `os.replace` and atomic temporary files.

---

### Tier 4: Real-World Workload Scenarios
Validates continuous production workloads:

1. `test_t4_01_continuous_multiturn_conversation_arena`: Simulates a 10-turn multi-turn conversation; verifies that each user turn triggers a background shadow arena trial and logs match records.
2. `test_t4_02_zero_latency_user_experience_simulation`: Measures synchronous user response time vs asynchronous challenger execution; confirms 0ms user impact.
3. `test_t4_03_continuous_24_7_lora_and_obsidian_persistence`: Executes multiple arena matches and verifies that DPO JSONL datasets and Obsidian Markdown transcripts are continuously generated and formatted.
4. `test_t4_04_full_lifecycle_continuous_arena_simulation`: Complete end-to-end tournament cycle: Prompt ingestion → Immediate Champion stream → Background Challenger execution → Tri-Orchestrator Blind Grading → Dynamic ELO update → Tri-Vault persistence → Dynamic Champion Handover.

---

## 3. Execution Commands & Verification

### Run Entire 4-Tier Test Suite
```bash
python3 tests/e2e/run_all_e2e.py --all
```

### Run Specific Tiers
```bash
python3 tests/e2e/run_all_e2e.py --tier 1
python3 tests/e2e/run_all_e2e.py --tier 2
python3 tests/e2e/run_all_e2e.py --tier 3
python3 tests/e2e/run_all_e2e.py --tier 4
```

### Run via Pytest
```bash
pytest tests/e2e/test_continuous_ai_arena_4tier.py -v
pytest tests/test_meta_training_tier1_features.py -v
```

### Export JSON Test Report
```bash
python3 tests/e2e/run_all_e2e.py --all --json-output reports/continuous_arena_e2e_report.json
```

---

## 4. Test Invariants & Zero-Mock Truth Protocol

1. **Rule #0 Compliance**: Tests MUST NOT use fabricated or mock data arrays. All telemetry, scores, token counts, and latency figures represent authentic execution or clean `--` empty states.
2. **Atomic Disk Safety**: All leaderboard modifications use POSIX atomic file replacement (`os.replace`) to guarantee data integrity across threads and processes.
3. **JSON Schema v7 Validation**: All leaderboard updates are validated against `CANONICAL_LEADERBOARD_SCHEMA_V7`.
4. **Deterministic Math**: Logistic ELO functions, expected outcomes, and multi-factor K-factors are mathematically exact and tested against reference values.
