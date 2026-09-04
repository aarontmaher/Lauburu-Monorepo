# Dispatch: Worker M2 (Canonical Read-Only Storage Context Map Governance)

## Identity
- Role: Worker for Milestone 2
- TypeName: teamwork_preview_worker
- Assigned Working Directory: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/teamwork_preview_worker_m2
- Orchestrator: teamwork_preview_orchestrator_23 (878c1253-0956-4401-91a5-0f3927d54244)

## Mandatory Rules & Warnings
MANDATORY FIRST STEP: Read the authoritative original request file:
/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/ORIGINAL_REQUEST.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Exclusive Write Ownership
You exclusively own:
- `tests/test_storage_architecture_governance.py` (create new test file)
- Applying `chmod 0444` and staging in git:
  * `07_docs_and_architecture/STORAGE_ARCHITECTURE_CONTEXT_MAP.md`
  * `obsidian_vault/07_STORAGE/CANONICAL_STORAGE_ARCHITECTURE_CONTEXT_MAP.md`

Do NOT modify the content of `STORAGE_ARCHITECTURE_CONTEXT_MAP.md` or its Obsidian mirror (they are strictly READ-ONLY awaiting cloud consensus).

## Explorer Survey Findings to Implement
Review findings in:
`/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/teamwork_preview_explorer_survey_governance/analysis.md`
`/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/teamwork_preview_explorer_survey_governance/handoff.md`

Tasks:
1. Stage both files in git:
   `git add 07_docs_and_architecture/STORAGE_ARCHITECTURE_CONTEXT_MAP.md obsidian_vault/07_STORAGE/CANONICAL_STORAGE_ARCHITECTURE_CONTEXT_MAP.md`
2. Set POSIX permissions to read-only (`0444`):
   `chmod 0444 07_docs_and_architecture/STORAGE_ARCHITECTURE_CONTEXT_MAP.md obsidian_vault/07_STORAGE/CANONICAL_STORAGE_ARCHITECTURE_CONTEXT_MAP.md`
3. Create the automated governance and health test file `tests/test_storage_architecture_governance.py` per the specifications in `analysis.md`:
   - Test 1: Assert both files exist and have non-zero size.
   - Test 2: Assert both files have POSIX mode `0444` (`stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH`, write bits cleared).
   - Test 3: Adversarial write rejection: attempt open(..., "a") and assert `PermissionError` is raised.
   - Test 4: Parity verification: assert SHA256 of primary file matches Obsidian mirror bit-for-bit (`80e96726403861ba55f8d9029442fb44e581bfb2da345adc0a27fce024ef0b02`).
   - Test 5: Tri-Vault storage health: assert Obsidian Vault exists with non-empty `Index.md`, PySpark Data Lake / lora_datasets directory exists, and host disk free headroom >= 5.0 GB.
4. Run pytest:
   `pytest tests/test_storage_architecture_governance.py -v`
   Verify all tests pass cleanly.

## Output Requirements
- Write your completion report to `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/teamwork_preview_worker_m2/handoff.md`
- Include test execution results in your report.
- Send a completion message to the parent orchestrator via send_message.

## 2026-09-03T23:08:00Z
Received user dispatch:
Implement:
1. Stage both context map files in git:
   git add 07_docs_and_architecture/STORAGE_ARCHITECTURE_CONTEXT_MAP.md obsidian_vault/07_STORAGE/CANONICAL_STORAGE_ARCHITECTURE_CONTEXT_MAP.md
2. Set POSIX mode to 0444 read-only:
   chmod 0444 07_docs_and_architecture/STORAGE_ARCHITECTURE_CONTEXT_MAP.md obsidian_vault/07_STORAGE/CANONICAL_STORAGE_ARCHITECTURE_CONTEXT_MAP.md
3. Create tests/test_storage_architecture_governance.py asserting:
   - Existence and non-zero size
   - Mode 0444 (write bits cleared)
   - Adversarial write attempt raises PermissionError
   - 100% bit-for-bit SHA256 match between primary file and Obsidian mirror (80e96726...0b02)
   - Tri-Vault health (Obsidian index.md exists, lora_datasets exists, disk headroom >= 5GB)
4. Run pytest tests/test_storage_architecture_governance.py -v and verify all pass.
