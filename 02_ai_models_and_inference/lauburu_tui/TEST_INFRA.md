# Test Infrastructure & Specification Guide — `lauburu-tui`

## 1. Test Philosophy & Architecture

The `lauburu-tui` test architecture enforces an **opaque-box, requirement-driven, zero-mock** standard across all terminal widgets, async background tasks, sharding decision trees, cloud API optimization models, continuous training oversight, and dual-path data persistence.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    LAUBURU-TUI TEST HARNESS ARCHITECTURE                    │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. Opaque-Box Behavioral Validation                                         │
│    • Tests evaluate user-observable behavior (Ratatui TestBackend buffer,   │
│      keyboard event dispatch, state transitions, mathematical outputs).     │
│    • Zero coupling to transient private implementation details.             │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. Requirement & Physical Truth Derivation                                  │
│    • Expected outputs derive directly from PROJECT.md, ORIGINAL_REQUEST.md, │
│      and the 7-Layer Lauburu Physical Mesh Hardware Matrix (108.0 GB RAM /  │
│      82.8 GB Usable VRAM Pool).                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. Rule #0 Zero-Mock Truth Invariant                                        │
│    • Zero synthetic placeholders, fake tokens, or dummy data arrays.        │
│    • All telemetry, formulas, and sums are computed dynamically.            │
│    • Automated static analysis audits prevent mock keyword regressions.     │
├─────────────────────────────────────────────────────────────────────────────┤
│ 4. Adversarial Fault Injection & Resilience                                 │
│    • Micro-viewports (<50x12, 0x0), corrupted JSON payloads, unmounted      │
│      Google Drive volumes, rapid event spam, and SIGWINCH resize stress.    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 4-Tier Feature Inventory Mapping

| # | Feature Code | Feature Description | Tier 1 (Coverage ≥5) | Tier 2 (Boundary ≥5) | Tier 3 (Cross-Feature) | Tier 4 (Real-World Scenarios) |
|---|---|---|---|---|---|---|
| **F1** | `TAB-NAV` | 5-Tab Navigation & Shell UI | • 5 Tab variants mapping<br>• Title string contract<br>• Next tab forward cycle<br>• Prev tab reverse cycle<br>• Index 0-4 bijective map | • Numeric keys 1-5 direct jump<br>• Out-of-bounds index clamp<br>• Rapid 10k tab spam<br>• Textarea typing isolation<br>• Micro-viewport fallback | • Tab switch during SSE stream<br>• Tab switch with active table selection<br>• Tab state persistence | • Full user browsing journey across all 5 tabs with key verification |
| **F2** | `SHARD-TREE` | Unified AI Sharding Decision Tree | • TB4 DMA lowest latency path<br>• Apple Silicon Exo MLX path<br>• Linux/Android Petals path<br>• Local Solo fallback path<br>• Interconnect latency scoring | • Ping threshold boundary (<2ms)<br>• Disconnected TB4 failover<br>• Single node Apple cluster<br>• Offline Petals anchor<br>• Zero-VRAM CPU node fit | • Decision tree update on node health event<br>• Dynamic re-routing under load | • Multi-node failover simulation from TB4 to Exo Ring to Petals DHT |
| **F3** | `SHARD-ROUT` | 7-Layer Node & Model Routing Matrix | • 82.8 GB pooled VRAM sum<br>• 7-node L1-L7 layer allocation<br>• ≤8B local routing<br>• ≤70B 3-Mac RPC routing<br>• >120B Petals swarm routing | • 70B FP16 OOM detection (>82.8GB)<br>• Dynamic cap enforcement (75-90%)<br>• Single node 32B IQ2_XXS fit<br>• 0 GB VRAM allocation clamp<br>• Extreme 1000-node cluster scaling | • Model selection updates node shard table<br>• Multi-table focus navigation (h/l) | • Sharded model launch verification against canonical mesh hardware |
| **F4** | `API-VELOCITY` | $0 Cloud Spend Velocity Dashboard | • Spend velocity % formula<br>• Cumulative savings calculation<br>• Endpoint monthly cost math<br>• Input/Output token pricing<br>• Local request ratio % | • 100% velocity ($0 cloud spend)<br>• 0% velocity (spend >= baseline)<br>• Negative savings clamp<br>• Zero input/output tokens<br>• Huge token overflow test | • Spend update recalculates all dashboard gauges<br>• Background poller event emission | • Cloud-to-local migration scenario saving $146.50/month across 5 APIs |
| **F5** | `API-SWAP` | Local Model Swap Recommender | • gpt-4o -> DeepSeek-R1-32B<br>• claude-3.5 -> Llama-3.3-70B<br>• gemini-1.5-pro -> Qwen-32B<br>• gemini-flash -> Qwen-7B<br>• embedding -> bge-large | • Hardware pool fit check (<=82.8GB)<br>• Unrecognized cloud model fallback<br>• Zero-dollar endpoint handling<br>• Table wrap-around selection<br>• Duplicate endpoint deduplication | • Swap activation updates endpoint status<br>• Swap triggers persistence save | • Automated key scan recommending immediate $0 local replacements |
| **F6** | `TRAIN-LORA` | 24/7 LoRA Distillation Oversight | • Active/Teacher model tracking<br>• Step progress & epoch calc<br>• Loss history vector tracking<br>• Throughput (samples/s, t/s)<br>• Decreasing loss validation | • Step 0 / Step Max boundaries<br>• Zero throughput handling<br>• Single-step loss spike resilience<br>• Empty loss history clamp<br>• Million-step overflow test | • Loss update triggers sparkline refresh<br>• Training update event dispatch | • Multi-epoch LoRA distillation run from step 0 to 5,000 with loss tracking |
| **F7** | `TRAIN-GOV` | Dynamic RAM Governor State Machine | • Full Tier (>85% Free)<br>• Medium Tier (70-85% Free)<br>• Minimal Tier (50-70% Free)<br>• Emergency Pause (<50% Free)<br>• Directive text matching | • Exact boundary: 85.0%<br>• Exact boundary: 70.0%<br>• Exact boundary: 50.0%<br>• 0.0% critical memory exhaustion<br>• 100.0% completely idle host | • Governor tier transition dynamically pauses/resumes LoRA job<br>• RAM gauge update | • Memory pressure simulation: Full -> Medium -> Minimal -> Emergency -> Full |
| **F8** | `TRAIN-LEDGER`| Shadow Swarm ELO & NPU Ledger | • ELO score ranking order<br>• Win/Loss/Draw record format<br>• Promotion gate rule (Local>=Cloud)<br>• Tensor G5 TPU grant credits<br>• Apple Neural Engine (ANE) grant | • 0 ELO / Max ELO clamp<br>• Tied ELO score sorting<br>• Zero token credit grant<br>• Empty tournament table<br>• Multi-million credit arithmetic | • Promotion verdict triggers model status update<br>• Ledger table focus toggle | • Shadow tournament where local LoRA surpasses cloud teacher ELO |
| **F9** | `PERSIST-DUAL`| Dual-Path Persistence & Fallback | • Primary GDrive path detection<br>• Fallback `config/memory_fallback.json`<br>• Atomic temporary write + rename<br>• Directory auto-creation<br>• JSON serialization roundtrip | • Unmounted GDrive (/Volumes/...)<br>• Corrupted JSON recovery (None)<br>• Read-only filesystem error handling<br>• Missing parent directory creation<br>• 0-byte file resilience | • Persistence worker debounced save<br>• Load precedence: Primary over Fallback | • Offline node operation: saves to fallback, recovers cleanly on restart |
| **F10** | `UI-RENDER` | Ratatui 5-Tab Render & Viewport Guard | • Tab 1: Topology & Matrix<br>• Tab 2: Chat Stream & Textarea<br>• Tab 3: Sharding Flowchart<br>• Tab 4: API Scanner Gauges<br>• Tab 5: Training Dashboard | • Micro-viewport 40x10 fallback<br>• Micro-viewport 0x0 no-panic<br>• Extreme viewport 300x100<br>• Tall narrow viewport 40x80<br>• Wide short viewport 200x10 | • Rapid tab switching draw loop (1000 frames)<br>• Zero heap allocations in draw | • Complete continuous UI session exercising all 5 tabs at 60 FPS |

---

## 3. Test Suite Organization & Target Manifest

The test suite is partitioned into dedicated test binaries under `tests/`:

```
tests/
├── tab_navigation_tests.rs       # R1: 5-Tab navigation, 1-5 keys, cycling, viewport guards
├── sharding_protocol_tests.rs    # R2: Unified AI Sharding decision tree, 82.8GB pool, model routing
├── api_scanner_tests.rs          # R3: $0 Cloud Spend Velocity, endpoint cost math, model swaps
├── training_view_tests.rs        # R4: 24/7 LoRA metrics, RAM Governor state machine, ELO & NPU ledger
├── persistence_fallback_tests.rs # R5: Dual-path persistence, atomic writes, unmounted GDrive fallback
├── ui_rendering_tests.rs         # R1-R5: Ratatui TestBackend rendering across all 5 tabs
├── topology_tests.rs             # Baseline: 7-layer physical mesh representation
├── chat_stream_tests.rs          # Baseline: SSE streaming, token buffering, UTF-8 fragmentation
├── config_tests.rs               # Baseline: mesh.toml parsing, validation, error handling
├── zero_mock_tests.rs            # Baseline: Rule #0 Truth audit & static mock keyword scans
├── m2_challenger_stress_tests.rs # Baseline: Stress testing, FPS benchmarks, viewport boundaries
├── e2e_integration_tests.rs      # Baseline: Cross-module async workflows
└── e2e_test_runner.rs            # Master Test Runner & threshold verification
```

---

## 4. Test Execution Commands

```bash
# 1. Execute full comprehensive test suite across all targets
cargo test

# 2. Execute individual feature test suites
cargo test --test tab_navigation_tests
cargo test --test sharding_protocol_tests
cargo test --test api_scanner_tests
cargo test --test training_view_tests
cargo test --test persistence_fallback_tests
cargo test --test ui_rendering_tests

# 3. Execute baseline & stress verification suites
cargo test --test zero_mock_tests
cargo test --test topology_tests
cargo test --test chat_stream_tests
cargo test --test config_tests
cargo test --test m2_challenger_stress_tests
cargo test --test e2e_integration_tests
cargo test --test e2e_test_runner

# 4. Run tests with full uncaptured stdout output
cargo test -- --nocapture
```
