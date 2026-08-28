# Dispatch for Worker M3 Deployer Gen 2 (Milestone 3 Deployment & Verification)

Working directory: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/worker_m3_deploy_gen2`
Project root: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo`
Authoritative request: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/ORIGINAL_REQUEST.md`
Scope document: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/PROJECT.md`
Deployment script: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/worker_m3/deploy_m3.py`
Test suite: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/tests/test_petals_mesh_e2e.py`

## Mission
1. Connect via SSH to `100.73.38.87 -p 8022` (probe port 8022 and retry with backoff).
2. Execute deployment via `python3 /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/worker_m3/deploy_m3.py`.
3. Verify on-device Runit service (`sv status petals`), `svlogd`, `01-mesh-boot.sh`, `petals_guardian.sh`, and `rpc-server` on `0.0.0.0:50052`.
4. Run Tier 1 Feature 5 & 6 tests (`TestTier1Feature5PersistentRunitService` and `TestTier1Feature6CoexistenceRPC`) in `tests/test_petals_mesh_e2e.py`.
5. Write your report to `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/worker_m3_deploy_gen2/handoff.md`.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
