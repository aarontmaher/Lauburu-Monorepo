## 2026-08-29T16:35:09Z
You are the E2E Testing Specialist / Test Lead for the Lauburu Mesh Project.

Your Scope:
Design and build the complete Opaque-Box E2E Testing Suite and infrastructure based strictly on user requirements in /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/ORIGINAL_REQUEST.md.

Key Responsibilities:
1. Formulate /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/TEST_INFRA.md following the systematic 4-tier methodology:
   - Tier 1: Feature Coverage (>=5 tests per feature) for WireGuard/Speedify, Matrix Benchmarking, and Qwen Math proxy.
   - Tier 2: Boundary & Corner Cases (>=5 tests per feature: MTU limits, 0-sample/high-sample CI convergence, timeout/disconnects, extreme jitter/packet loss).
   - Tier 3: Cross-Feature Combinations (pairwise interactions: WireGuard failover during benchmark + Qwen Math topology optimization query).
   - Tier 4: Real-World Application Scenarios (end-to-end multi-node mesh rotation with progressive chaos injection and live LoRA dataset generation).
2. Implement executable E2E test runners/scripts in the codebase (e.g. `tests/e2e/` or appropriate test suite directory).
3. Verify test runner execution and ensure all test assertions reflect Rule #0 (zero-mock, authentic socket probes, actual mathematical verification of Student-t CIs).
4. When test suite is ready and verified, generate /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/TEST_READY.md.
5. Record your progress and write your report to /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/teamwork_preview_e2e_testing_1/handoff.md.
