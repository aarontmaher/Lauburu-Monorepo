# E2E Test Infra: Voice Bridge Daemon & Frontend Audio Pipeline

## Test Philosophy
- Opaque-box, requirement-driven. No dependency on implementation design.
- Methodology: Category-Partition + Boundary Value Analysis (BVA) + Pairwise Combinatorial + Real-World Workload Testing.

## Feature Inventory
| # | Feature | Source (requirement) | Tier 1 | Tier 2 | Tier 3 | Tier 4 |
|---|---------|---------------------|:------:|:------:|:------:|:------:|
| 1 | Bi-Directional Binary Audio Streaming | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ | ✓ |
| 2 | Pure Asyncio & WebSockets Backend | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ | ✓ |
| 3 | JSON Control Plane & Lifecycle | Survey 1 & 3 | 5 | 5 | ✓ | ✓ |
| 4 | HTTP Diagnostic Interceptors | Survey 1 | 3 | 3 | ✓ | ✓ |
| 5 | Non-Blocking Inference Queue Hooks | Survey 1 | 3 | 3 | ✓ | ✓ |
| 6 | Frontend Live WebSocket Audio Capture | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ | ✓ |
| 7 | Frontend Web Audio Playback & Demux | Survey 2 | 4 | 4 | ✓ | ✓ |
| 8 | Frontend Lifecycle & Hardware Disposal | Survey 2 | 3 | 3 | ✓ | ✓ |
| 9 | Standalone Latency Test Harness (<500ms) | ORIGINAL_REQUEST §Acceptance | 5 | 5 | ✓ | ✓ |
| 10 | Multi-Tier Automated Test Suite | Survey 3 | 5 | 5 | ✓ | ✓ |

## Test Architecture
- **Standalone Benchmark**: `test_voice_bridge.py`
  - Ephemeral daemon launcher with random port allocation
  - 100KB binary payload generation (`os.urandom(102400)`)
  - Sub-millisecond timing with `time.perf_counter()`
  - Assertions: `rtt_ms < 500.0`, byte match, SHA-256 validation
- **Pytest Suite**: `tests/test_voice_bridge_suite.py`
  - Tier 1: Core SLA, session management, telemetry
  - Tier 2: Boundary (0B to 10MB), malformed JSON, protocol fuzzing
  - Tier 3: Multi-client concurrency (10-25 clients), packet flood
  - Tier 4: RecordRTC 150ms emulation, CLI `--json` output, Pytest runner
- **Adversarial Stress Harnesses**:
  - `tests/stress_adversarial_voice_bridge.py`: 100 iterations, 500 pkts/s flood, 10MB frames
  - `tests/test_adversarial_challenger2_voice_bridge.py`: 25 concurrent clients, 40-client churn, abrupt TCP socket termination

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Complexity |
|---|----------|--------------------|------------|
| 1 | RecordRTC 150ms Streaming Session | F1, F2, F3, F6, F7, F8 | Medium |
| 2 | High-Concurrency Voice IDE Multi-Session | F1, F2, F3, F5, F9, F10 | High |
| 3 | Burst Audio Packet Flood with Interleaved Control | F1, F2, F3, F4, F10 | High |
| 4 | Abrupt Disconnect Recovery & Zero Leaks | F1, F2, F3, F5, F8 | High |
| 5 | Full CLI Benchmark with Machine-Readable JSON | F1, F2, F9, F10 | Medium |

## Coverage Thresholds
- Tier 1: ≥5 per major feature
- Tier 2: ≥5 boundary conditions (0B, 1B, 100KB, 5MB, 10MB, >10MB)
- Tier 3: Pairwise coverage of multi-client concurrency and packet bursts
- Tier 4: 5 realistic application scenarios
