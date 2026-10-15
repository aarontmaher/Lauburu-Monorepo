# Test Infrastructure & Test Philosophy: Frontier Swarm Consensus Engine
## Omni-Lens Sovereign Mesh

**Subsystem:** `frontier_swarm_consensus` (`/Users/aaron/teamwork_projects/frontier_swarm_consensus`)  
**Governing Documents:** `PROJECT.md` & `ORIGINAL_REQUEST.md`  
**Author:** E2E Testing Specialist (`teamwork_preview_test_writer_e2e_1`)  
**Standard:** Python Standard Library `unittest`, `asyncio`, `pytest`

---

## 1. 4-Tier Requirement-Driven Test Architecture

The Frontier Swarm Consensus Engine is a continuous, autonomous multi-model deliberation framework integrating cloud frontier models (`agy` CLI, OpenRouter) and local sovereign mesh endpoints (Port 8082 Hermes-3 & Port 8083 Qwen 3.8 Max), 4-layer AI sharding across hardware nodes (L1, L8, L1b, L3), LoRA dataset distillation into `continuous_lora_dataset.jsonl` with SHA256 integrity hashes, and the Mandatory Tri-Proof Verification Gate (Proof 1 Exit Code 0, Proof 2 SHA256 Checksums, Proof 3 Screen Lens Sovereign Visual Capture).

To guarantee 100% production reliability, zero-mock fidelity, and fault-tolerant continuous execution, testing is structured into a 4-Tier Test Architecture:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       4-TIER TEST ARCHITECTURE                              │
├─────────────────────────────────────────────────────────────────────────────┤
│ TIER 1: FEATURE COVERAGE (R1, R2, R3)                                       │
│ • R1: Continuous state persistence, process locking, signal handling, 4-node│
│   mesh sharding & latency routing logic (>=5 tests per feature).            │
│ • R2: Cloud (`agy`/OpenRouter) + Local (8082/8083) model debate, consensus │
│   accord synthesis, LoRA reasoning trace distillation & SHA256 verification.│
│ • R3: Tri-Proof Verification Gate (Exit code 0, SHA256 hashes, Screen Lens  │
│   visual capture trigger) (>=5 tests per feature).                          │
├─────────────────────────────────────────────────────────────────────────────┤
│ TIER 2: BOUNDARY & CORNER CASES                                             │
│ • Missing / invalid OPENROUTER_API_KEY resolution and fallback handling.    │
│ • Unreachable local mesh ports (Port 8082/8083 connection timeouts).         │
│ • Malformed / corrupted JSON lines in dataset files.                        │
│ • Empty / zero-byte dataset files and disk space pressure assertions.       │
│ • Process signal interruptions (SIGINT/SIGTERM) and lockfile release.       │
│ • Extreme prompt payloads, empty prompt handling, and token limits.         │
├─────────────────────────────────────────────────────────────────────────────┤
│ TIER 3: CROSS-FEATURE INTERACTIONS                                          │
│ • Continuous execution loop + mesh sharding + LoRA dataset distillation.    │
│ • Multi-model debate consensus + SHA256 checksumming + Tri-Proof gate.      │
│ • State recovery across process restarts during active dataset writing.     │
│ • Concurrent lock prevention + multi-node routing fallback.                 │
├─────────────────────────────────────────────────────────────────────────────┤
│ TIER 4: REAL-WORLD APPLICATION SCENARIOS                                    │
│ • End-to-end single debate iteration (`--once`) with real/mocked model pool,│
│   dataset crystallization, SHA256 verification, and HUD screenshot proof.  │
│ • End-to-end continuous loop iteration (`--continuous`) verifying lock,      │
│   state updates, signal handling, and clean shutdown.                       │
│ • End-to-end verification gate (`--verify`) validating bit-for-bit mirrors. │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Test Tier Inventory & Coverage Matrix

### Tier 1: Feature Coverage (Requirement Driven)
- **R1. Continuous Execution & AI Sharding**:
  - `test_continuous_loop_state_init`: Asserts state initialization in `frontier_swarm_state.json`.
  - `test_process_file_locking`: Verifies single-instance lock file (`frontier_swarm.lock`) creation and release.
  - `test_signal_handling`: Verifies SIGINT / SIGTERM graceful loop shutdown.
  - `test_mesh_4_layer_node_registration`: Verifies 4 hardware nodes (L1 Mac Mini M4, L8 Linux Mini Hub, L1b Mac Mini M2 Pro, L3 Linux Head Node) registration.
  - `test_sharding_routing_latency`: Verifies sharding decision based on node availability and latency.
- **R2. Unified Model Integration & LoRA Distillation**:
  - `test_cloud_model_openrouter_query`: Verifies OpenRouter API request structure and response extraction.
  - `test_cloud_model_agy_cli`: Verifies `agy` CLI dispatch and stdout parsing.
  - `test_local_sovereign_duo_query`: Verifies HTTP query to Port 8082 (Hermes-3) and Port 8083 (Qwen 3.8 Max).
  - `test_consensus_synthesis`: Verifies multi-turn reasoning trace synthesis into unanimous accord.
  - `test_lora_dataset_distillation`: Verifies jsonl writing with line-by-line SHA256 checksums to `continuous_lora_dataset.jsonl`.
- **R3. Mandatory Tri-Proof Verification Gate**:
  - `test_tri_proof_1_exit_code`: Asserts exit code 0 on successful debate and verification.
  - `test_tri_proof_2_sha256_checksum`: Asserts cryptographic SHA256 calculation for string and file payloads.
  - `test_tri_proof_3_screen_lens_capture`: Verifies Screen Lens Sovereign visual capture trigger (Port 4003 / screencapture / ADB).
  - `test_tri_proof_gate_full_pass`: Verifies `verify_consensus_artifacts()` returns true when all artifacts match.
  - `test_tri_proof_gate_failure_detect`: Asserts `verify_consensus_artifacts()` returns false on checksum mismatch or missing files.

### Tier 2: Boundary & Corner Cases
- `test_missing_openrouter_api_key_fallback`: Verifies graceful fallback to architectural reasoning when API key is missing or invalid.
- `test_unreachable_mesh_ports_timeout`: Verifies timeout and fallback when Port 8082 or 8083 is offline.
- `test_corrupted_jsonl_dataset_recovery`: Tests handling of malformed JSON lines in dataset during verification.
- `test_empty_dataset_handling`: Verifies handling when dataset file exists but has zero lines.
- `test_signal_interruption_cleanup`: Tests signal interruption during active debate loop and verifies lock release.
- `test_empty_prompt_error_exit`: Verifies exit code 1 when prompt is empty or invalid.

### Tier 3: Cross-Feature Interactions
- `test_continuous_loop_sharding_distillation_integration`: Verifies continuous loop executes sharded queries and writes distilled entries.
- `test_debate_consensus_sha256_tri_proof_pipeline`: Verifies full pipeline from multi-model debate to dataset writing, SHA256 calculation, and Tri-Proof gate pass.
- `test_state_persistence_across_restarts`: Verifies state file is updated and reloaded on process restart.
- `test_concurrent_execution_lock_rejection`: Verifies a second process attempt is rejected while lockfile is held.

### Tier 4: Real-World Application Scenarios
- `test_e2e_single_debate_iteration`: Executes full `--once` debate iteration producing dataset output and visual proof.
- `test_e2e_continuous_loop_lifecycle`: Runs continuous loop for multiple cycles, validates state file updates, and triggers clean exit.
- `test_e2e_verification_gate_command`: Executes `--verify` command and asserts zero exit code.

---

## 3. Test File Layout

```
/Users/aaron/teamwork_projects/frontier_swarm_consensus/tests/
├── test_tier1_feature_coverage.py      # Tier 1: Requirements R1, R2, R3 feature test cases
├── test_tier2_boundary_corner_cases.py  # Tier 2: Boundary, error handling & corner cases
├── test_tier3_cross_feature.py          # Tier 3: Multi-component integration scenarios
├── test_tier4_e2e_real_world.py        # Tier 4: Real-world E2E debate & verification scenarios
└── run_e2e_tests.py                    # Master test runner script (exits 0 on pass)
```

---

## 4. Test Execution Command

To execute the full test suite:
```bash
python3 /Users/aaron/teamwork_projects/frontier_swarm_consensus/tests/run_e2e_tests.py
```

Expected Output:
```
======================================================================
FRONTIER SWARM CONSENSUS ENGINE — 4-TIER E2E TEST SUITE
======================================================================
[TIER 1] Running Feature Coverage Tests (R1, R2, R3)... [PASS]
[TIER 2] Running Boundary & Corner Case Tests...        [PASS]
[TIER 3] Running Cross-Feature Interaction Tests...     [PASS]
[TIER 4] Running Real-World E2E Application Tests...    [PASS]
----------------------------------------------------------------------
Ran 30 tests in X.XXXs — ALL PASSED (Exit Code 0)
======================================================================
```
