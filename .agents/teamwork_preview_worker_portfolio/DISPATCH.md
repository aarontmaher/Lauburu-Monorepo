## 2026-08-29T09:57:08Z
You are a Worker agent for Milestones M2, M3, M4: Monorepo Portfolio Separation & Universal Web-TUI Portal.
Your working directory is /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/teamwork_preview_worker_portfolio/
Path to ORIGINAL_REQUEST.md: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/ORIGINAL_REQUEST.md
Path to PROJECT.md: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/PROJECT.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Scope & Tasks:
1. User & Scaling Apps (01_apps/user_facing_and_scaling/):
   - movesense_readiness_hub/: Standardized modular package (core/, dsp/, transport/, presentation/) with 512Hz ECG, PTT BP, sleep staging, Zone 2 coaching, multi-platform clients.
   - spatial_grappling_3d/: Modular package with core/, kinematics/ (3,044 OPML tree & MediaPipe 33-landmark 3D skeleton on 10m x 10m tatami grid), presentation/.
   - combat_arena/: Modular package with core/, modes/ (4 game modes: Tug-of-War, Battle, Proximity, Defense), presentation/ (120 FPS power bar, live Movesense pulse gauge, RAG voice).
   - shopify_storefront/: Modular package with core/, graphql/ (headless Storefront GraphQL client), presentation/ (///mo tiers, hardware sensor bundles).
2. Operator & Dev Cockpits (01_apps/operator_and_dev/):
   - canonical_port/: Modular package with 9-screen stability hierarchy (7 physical nodes, 108GB RAM pool, AI debate).
   - smolagents_duel_sandbox/: Modular package with core/, tools/ (code-as-action tool registry), presentation/ (sandboxed Python execution duel arena).
   - qwen_math_trend_optimizer/: Modular package with core/, models/ (latency proofs, BQL depths, cardiac coherence), presentation/ (24/7 LoRA SFT/DPO dataset logging).
3. Universal Web-TUI Portal (01_apps/web_tui_portal/):
   - Implement serve_portal.py (and ensure 01_apps/canonical_port/tui/serve_web_tui.py compatibility): FastAPI + WebSocket async PTY engine on Port 8088 rendering all 7 applications (/readiness, /grappling, /arena, /store, /canonical, /smolagents, /math) via xterm.js WebGL at 120 FPS with automatic port reclamation.
4. Verification:
   - Ensure all modules compile cleanly with python3 -m py_compile.
   - Verify importability of all 7 applications.
   - Run tests: python3 tests/e2e/run_all_e2e_tests.py --all
   - Write full report to /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/teamwork_preview_worker_portfolio/handoff.md.
Send a completion message when finished.
