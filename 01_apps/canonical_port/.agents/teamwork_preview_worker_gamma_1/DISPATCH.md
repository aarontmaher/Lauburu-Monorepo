# Dispatch Assignment: Track Gamma Worker (Data Lake & Obsidian Graph)

## Mission
Implement the competitive Track Gamma React prototype (`src/prototypes/TrackGammaDataLakeGraph.jsx`) and refine graph/training subcomponents in `src/components/graph/` and `src/components/training/`.

## Key Instructions & Constraints
1. Read `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/ORIGINAL_REQUEST.md` and `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/PROJECT.md`.
2. Exclusive Write Ownership:
   - `src/prototypes/TrackGammaDataLakeGraph.jsx`
   - `src/components/graph/`
   - `src/components/training/`
3. Requirements:
   - High visual density 3-pane architecture explorer:
     * Left sidebar (25%): Real-time search (`/`), 10 category chips, hierarchical tree.
     * Center canvas (55%): Sugiyama-layered SVG interactive directed topology graph with Tarjan SCC cycle badges (`↺ SCC`), bidirectional flow vectors (`⇄ BIDI`), zoom controls (70%-150%).
     * Right inspector pane (20%): PySpark AST code metrics card (3.29M LOC, 10,240 files), 24/7 LoRA continuous distillation monitor with real-time SVG loss curve (steps 0-4800), and Tri-Vault sync indicators.
   - Non-blocking state management: graph panning/filtering and loss curve updates must not block the main thread.
   - Strict adherence to Rule #0 (Zero-Mock): fallback to clean `--` or `STORE CLOSED` when Qdrant/Lake is unreachable.
4. MANDATORY INTEGRITY WARNING:
   > DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
5. Verify build with `npm run build`.
6. Output handoff to `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/.agents/teamwork_preview_worker_gamma_1/handoff.md`.
