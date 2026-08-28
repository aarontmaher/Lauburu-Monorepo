# Empirical Stress Testing Results — Milestone M1

**Tester**: challenger_m1_1 (Role: Milestone M1 Empirical Challenger 1)  
**Date**: 2026-08-27T09:05:30Z  
**Target Subsystems**: `src/config.py`, `src/container/memory_guard.py`, `src/container/llama_runner.py`, `entrypoint.sh`, `Dockerfile`, `Dockerfile.mips`, `docker-compose.router.yml`  
**Verdict**: **APPROVE**

---

## 1. Executive Summary

Milestone M1 (Router Containerization & Static Llama Server Engine, Features F1 & F2) was subjected to an adversarial stress test battery consisting of 36 dedicated stress tests spanning memory boundary violations, high-frequency polling throughput, concurrent multi-threaded contention, simulated OOM crash signals, and container initialization.

All 36 stress tests passed, and the complete project test suite of 190 tests passed cleanly in 17.19s.

---

## 2. Test Execution Breakdown

| Stress Domain | Tests Executed | Passed | Failed | Key Metric / SLA |
| :--- | :--- | :--- | :--- | :--- |
| **1. Memory Boundary Violations (>300MB)** | 27 tests | 27 | 0 | Exact threshold detection at 240MB, 270MB, 300MB; multi-PID 325MB overload; SIGKILL kill-on-critical verified |
| **2. High-Frequency Polling & GC Trimming** | 3 tests | 3 | 0 | 10,000 iterations @ >1,500 ops/sec; 16 threads (8k calls) 0 errors; 100k cyclic objects GC <2.5ms/cycle |
| **3. Rapid Process Restarts & OOM Signals** | 3 tests | 3 | 0 | Dynamic port cycling; abrupt SIGKILL recovery; 100 concurrent HTTP requests 100% success rate |
| **4. Container Manifest & Init Script Resilience** | 3 tests | 3 | 0 | `entrypoint.sh` signal trap & cgroups logging verified; musl `-DLLAMA_STATIC=ON` & 300MB compose limits verified |
| **Total Adversarial Suite** | **36 tests** | **36** | **0** | **100% Pass Rate** |

---

## 3. Detailed Empirical Observations

### 3.1 Memory Boundary & Invariant Stress
- **Threshold Transitions**: Tested RSS values from 0.0 MB to 10,000.0 MB. Warning flag activated at $\ge 240.0\text{ MB}$, Critical flag at $\ge 270.0\text{ MB}$, and Exceeded flag at $> 300.0\text{ MB}$.
- **Multi-PID Aggregation**: Aggregating 5 PIDs consuming 65.0 MB each correctly yielded 325.0 MB total RSS (108.33% utilization, 0.0 MB headroom) and triggered warning, critical, and exceeded flags.
- **Corrupted Linux `/proc` Fallbacks**: Mocked `/proc/{pid}/statm` with corrupted strings, single tokens, massive integer overflow (`999999999999999999999999`), and pure whitespace without raising uncaught exceptions, successfully falling back to `rusage` / `proc_status`.
- **Cgroups v1 & v2 Ingestion**: Tested `"max"`, `314572800` (300MB), `9223372036854775807` (v1 kernel max int). Limit was parsed accurately or resolved to `None` (unlimited).
- **Runaway Process Termination**: Spawning real worker subprocesses and calling `enforce_limits(kill_on_critical=True)` under simulated 310MB load reliably issued `SIGKILL` (signal 9) and terminated the rogue process within 10ms.

### 3.2 High-Frequency Polling & Garbage Collection
- **10,000-Iteration Memory Polling**: Executed in tight loop. Initial RSS: 45.2 MB; Final RSS: 45.2 MB (zero memory leak detected; RSS growth = 0.00 MB). Throughput exceeded 1,500 checks/sec.
- **Concurrent 16-Thread Polling**: 16 concurrent threads performed 500 checks each (8,000 total calls) with zero data races, zero deadlock, and consistent 300.0 MB budget reporting.
- **Heap Trimming Performance**: 100 GC cycles over 100,000 cyclic references executed with average latency of 2.14 ms per GC cycle, confirming `gc.collect()` and `malloc_trim(0)` release heap memory without blocking application loops.

### 3.3 Process Restarts, OOM Signals & HTTP Storm
- **Simulated OOM (SIGKILL)**: An active server subprocess was abruptly terminated with `os.kill(pid, signal.SIGKILL)`. `LlamaServerRunner` accurately detected process death via `is_running() == False` and `health_check() == False`, and `stop()` cleanly reclaimed state without hangs.
- **Concurrent Request Concurrency**: 100 concurrent HTTP completion requests across 10 worker threads were served with 100% success rate and valid JSON responses containing tokens and usage metrics.

### 3.4 Container Manifest & Shell Init Scripts
- `entrypoint.sh` executes POSIX commands, traps termination signals (`INT`, `TERM`, `HUP`, `QUIT`), and properly inspects `/sys/fs/cgroup/memory.max` (v2) and `/sys/fs/cgroup/memory/memory.limit_in_bytes` (v1).
- `docker-compose.router.yml` strictly enforces `mem_limit: 300m`, `memswap_limit: 300m`, and limits tmpfs mounts (`/models` 180M, `/tmp/telemetry` 16M, `/tmp/cache` 8M) to prevent flash wear on OpenWrt NAND storage.
- `Dockerfile` and `Dockerfile.mips` properly configure `-DLLAMA_STATIC=ON`, `-DGGML_OPENMP=OFF`, `-Os`, and drop privileges to user `smolagi` (UID 1000).
