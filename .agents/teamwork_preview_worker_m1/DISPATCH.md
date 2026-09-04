# Dispatch: Worker M1 (C11 Consistent Hash Ring & Pooled Storage)

## Identity
- Role: Worker for Milestone 1
- TypeName: teamwork_preview_worker
- Assigned Working Directory: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/teamwork_preview_worker_m1
- Orchestrator: teamwork_preview_orchestrator_23 (878c1253-0956-4401-91a5-0f3927d54244)

## Mandatory Rules & Warnings
MANDATORY FIRST STEP: Read the authoritative original request file:
/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/ORIGINAL_REQUEST.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Exclusive Write Ownership
You exclusively own and may modify ONLY these files:
- `01_apps/screen_lens/c_core/lauburu_pooled_storage.c`
- `01_apps/screen_lens/c_core/lauburu_pooled_storage.h`
- `01_apps/screen_lens/c_core/test_pooled_storage.c`

Do NOT modify any files outside this path.

## Explorer Survey Findings to Implement
Review findings in:
`/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/teamwork_preview_explorer_survey_storage/analysis.md`
`/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/teamwork_preview_explorer_survey_storage/handoff.md`

Tasks:
1. In `lauburu_pooled_storage.c`:
   - Implement `storage_pool_sort_ring()` using `qsort` on `g_ring` by token value.
   - Call `storage_pool_sort_ring()` whenever nodes/virtual slots are added, or after `storage_pool_add_node()`.
   - Update `find_node_on_ring()` to use binary search or sorted circular successor search so that chunks are evenly distributed across all 7 layers instead of 90.8% starving to Node 0.
   - Fix Fletcher32 odd-byte padding: handle odd `len` cleanly so that the trailing byte is never truncated and memory alignment is preserved.
2. In `test_pooled_storage.c`:
   - Register all 7 canonical mesh layers:
     * L1: `L1_Mac_Node` (host, 24.0 GB)
     * L2: `L2_MacBook_Pro` (TB4, 16.0 GB)
     * L3: `L3_Linux_Head_Node` (compute, 16.0 GB)
     * L4: `L4_Linux_Tablet` (touch DSP, 8.0 GB)
     * L5: `L5_MacBook_Air` (metal, 16.0 GB)
     * L6: `L6_Pixel_10_Pro_XL` (edge TPU, 16.0 GB)
     * L7: `L7_Samsung_S20` (UI tester, 12.0 GB)
   - Replace repeating 256-byte payload pattern with a non-repeating PRNG or hash-based pattern for the 1.0 MB payload.
   - Add explicit bitrot fault injection test (e.g. flipping a bit in a chunk and asserting reassembly fails).
   - Verify: 1.0 MB dispersal latency <= 2.0 ms, reassembly latency <= 0.5 ms, 100% bit-for-bit SHA256 match, Fletcher32 bitrot detection.
3. Build and test:
   - Compile with clang/gcc (e.g. `clang -O3 -std=c11 -Wall -Wextra lauburu_pooled_storage.c test_pooled_storage.c -o lauburu_storage_bench`).
   - Run `./lauburu_storage_bench` and verify all assertions pass.

## Output Requirements
- Write your completion report to `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/teamwork_preview_worker_m1/handoff.md`
- Include build and execution logs in your report.
- Send a completion message to the parent orchestrator via send_message.

## 2026-09-03T23:08:00Z
Received dispatch to implement C11 consistent hash ring & pooled storage in:
- 01_apps/screen_lens/c_core/lauburu_pooled_storage.c
- 01_apps/screen_lens/c_core/lauburu_pooled_storage.h
- 01_apps/screen_lens/c_core/test_pooled_storage.c

Requirements:
1. Virtual ring sorting via qsort by token value in lauburu_pooled_storage.c.
2. Clockwise binary search / circular successor routing in find_node_on_ring to ensure even distribution across the 7 mesh layers and eliminate Node 0 starvation.
3. Fletcher32 odd-byte padding and memory alignment safety.
4. Update test_pooled_storage.c to register all 7 canonical mesh layers (L1 Mac Host, L2 MacBook Pro TB4, L3 Linux Head Node, L4 Linux Tablet, L5 MacBook Air, L6 Pixel 10 Pro XL, L7 Samsung S20).
5. Add diverse 1.0 MB non-repeating payload, explicit bitrot corruption injection test, and verify:
   - Dispersal latency <= 2.0 ms
   - Reassembly latency <= 0.5 ms
   - 100% bit-for-bit SHA256 match
   - Fletcher32 bitrot detection (returns false on corruption)
6. Compile and run ./lauburu_storage_bench and report actual metrics.

