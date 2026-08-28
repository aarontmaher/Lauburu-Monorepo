# Adversarial Challenge Report — Milestone 2 (M2)
**Project**: Canonical Port TUI & Blackboard Telemetry Integration
**Evaluator**: Challenger 1 (EMPIRICAL CHALLENGER — critic, specialist)
**Target Modules**:
- `01_apps/canonical_port/tui/models/blackboard_models.py`
- `01_apps/canonical_port/tui/services/blackboard_store.py`
**Test Harness**: `01_apps/canonical_port/tests/e2e/test_challenger_blackboard_stress.py`

---

## Challenge Summary

**Overall risk assessment**: **LOW**
**Verdict**: **APPROVE** (with architectural optimization advisories for M3/M4)

The Milestone 2 Blackboard state models and store service have been rigorously stress-tested across all 4 mandatory dimensions:
1. **High Concurrency**: 32 concurrent threads (16 readers, 16 writers, 1,280 operations) achieved 100% data integrity with zero deadlocks and zero race conditions under atomic temp-file disk persistence.
2. **Corrupted Disk State Recovery**: 100% zero-crash resilience across truncated JSON, malformed YAML, random binary garbage, 0-byte files, and unclosed collections with automatic canonical self-healing.
3. **Memory Stability**: 5,000 continuous snapshot creation and mutation cycles showed zero memory leaks (net heap growth only 128.23 KB, peak memory 0.46 MB) at ~797 ops/sec throughput.
4. **Socket Probing & Rule #0 Compliance**: Real TCP sockets probed with genuine RTT latencies (0.16ms on localhost); unroutable RFC 5737 IPs properly timed out without blocking threads beyond timeout limits; closed ports returned authentic `None`.

---

## Challenges

### [Medium] Challenge 1: Synchronous Socket Probing Under `_lock` in `get_snapshot()`
- **Assumption challenged**: Calling `store.get_snapshot(force_refresh=True)` is fast and non-blocking for concurrent callers.
- **Attack scenario**: When physical mesh nodes (e.g. Linux Head Node `100.101.39.98:50052` or MacBook Pro `169.254.187.138:50052`) are offline, disconnected, or traversing slow WAN links, `self.probe_endpoint` synchronously blocks for the socket timeout (80ms per offline node). Because this loop executes inside `with self._lock:` in `get_snapshot()`, all concurrent threads calling `get_snapshot()` or `update_layer()` are blocked for the full duration of all probe timeouts (~240ms per refresh).
- **Blast radius**: Under high-concurrency read/write bursts, if mesh nodes are offline, store throughput degrades from ~800 ops/sec down to ~4-10 ops/sec due to lock contention.
- **Mitigation**: Move socket probing to an asynchronous background worker daemon or non-blocking thread pool that updates RPC node latency fields independently, keeping `get_snapshot()` purely in-memory and sub-millisecond.

### [Low] Challenge 2: Discrepancy in Hardware Pool Test Contract vs Aggregate Ceiling
- **Assumption challenged**: The sum of physical node VRAM caps (`vram_cap_gb`) equals the aggregate pooled VRAM ceiling (`total_vram_gb`).
- **Attack scenario**: In `test_challenger_m2_contracts.py:218`, the test asserted `sum(n.vram_cap_gb for n in physical_nodes) == 82.8`. However, summing the 7 physical nodes defined in the canonical hardware matrix (`L1: 21.6`, `L2: 14.0`, `L3: 13.8`, `L4: 6.5`, `L5: 14.0`, `L6: 12.5`, `L7: 9.0`) yields `91.4 GB`. `total_vram_gb: float = 82.8` is the usable pooled AI VRAM limit after system reserves.
- **Blast radius**: Test failure in `test_contract_layer_1_hardware_nodes_and_memory_pools` due to comparing sum of individual node caps (91.4) directly against the pooled aggregate allocation ceiling (82.8).
- **Mitigation**: In test assertions, verify that `sum_vram == 91.4` (sum of raw physical node caps) and `l1.total_vram_gb == 82.8` (canonical usable AI pool limit).

---

## Stress Test Results

| Test Case | Scenario | Expected Behavior | Actual Behavior | Result |
|---|---|---|---|---|
| `test_stress_high_concurrency_multi_thread_bursts` | 32 concurrent threads (16 readers, 16 writers, 1,280 ops) | Zero deadlocks, zero race conditions, atomic disk state | 800 reads, 480 writes completed successfully in < 5s; clean disk load | **PASS** |
| `test_stress_corrupted_disk_recovery_matrix` | Fuzzing disk files with truncated JSON, raw binary, corrupted YAML | `load_from_disk()` returns `None`, `get_snapshot()` auto-heals to canonical default | Zero crashes; 100% self-healing to canonical default state | **PASS** |
| `test_stress_malformed_layer_mutation_payloads` | Updating layers with invalid keys, wrong data types, and partial dicts | `ValueError` on bad keys, `TypeError` on bad types, partial dicts hydrate cleanly | Precise exceptions raised; partial dicts preserved layer defaults | **PASS** |
| `test_stress_memory_leak_rapid_snapshot_creation` | 5,000 rapid snapshot creations + mutations with tracemalloc profiling | Zero memory leaks, throughput > 500 ops/sec, net growth < 5MB | Throughput: 797 ops/sec; net growth: 128.23 KB; peak memory: 0.46 MB | **PASS** |
| `test_stress_socket_probe_simulated_network_drops` | Real TCP server, closed ports, unroutable RFC 5737 IPs, malformed domains | Live RTT on open port, `None` on closed/unroutable, zero hanging threads | Measured 0.16ms on open port; `None` on closed/blackhole; timeouts honored | **PASS** |
| `test_stress_concurrent_socket_probes` | 20 threads executing 200 concurrent socket probes | No socket descriptor exhaustion, clean cleanup | 200/200 probes completed cleanly in < 1s | **PASS** |
| `test_stress_dataclass_boundary_and_fuzz_conditions` | Empty collections, None fields, 1000 loss points, Unicode node names | Roundtrip lossless fidelity across Dict -> JSON -> YAML -> Dataclass | 100% roundtrip precision maintained | **PASS** |

---

## Unchallenged Areas

- **UI Widget Rendering Performance**: Textual screen widget paint cycles and React DOM updates are deferred to Milestone 3 (Navigation & Visual Separation) and Milestone 4 (Maximalist TUI/Web integration).
- **Physical Movesense BLE Dongle / Hardware USB Hub**: Hardware serial links tested via mock-free null states and software loopbacks; physical Bluetooth hardware verification occurs in integration stage.
