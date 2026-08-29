# Handoff Report: Application Portfolio Separation & Web-TUI Portal Survey

**Agent**: `teamwork_preview_explorer_survey_2`  
**Timestamp**: 2026-08-29T19:36:35+10:00  
**Target Recipient**: Parent Orchestrator (`2a18102f-99e3-40e0-adec-7d45ce293833`)  
**Integrity Mode**: Development / Zero-Mock Rule #0 Verified  

---

## 1. Observation

Direct examination of the monorepo identified all 7 target applications, their existing file implementations, and the current Web-TUI engine on Port 8088:

1. **Movesense Physiological Readiness Suite**:
   - `01_apps/biometrics/movesense_readiness_tui.py` (lines 1-199): Native Textual TUI with responsive metric cards for 512Hz ECG, continuous PTT blood pressure, overnight sleep staging, and Zone 2 pacing.
   - `03_biometrics_and_telemetry/movesense_readiness_suite.py` (lines 1-100): `compute_ptt_blood_pressure` implementing Hughes-Bramwell arterial wave inversion equation, DFA-alpha1 thresholds (LT1 0.75, LT2 0.50), and 0-100 sleep score.
   - `03_biometrics_and_telemetry/pan_tompkins_dsp.py`: 512Hz QRS detection and bandpass filtering.
   - `01_apps/biometrics/zone2_endurance/` & `01_apps/biometrics/lauburu_zone2_endurance/`: Next.js 14 web client and Flutter cross-platform mobile client scaffolds.

2. **3D Spatial Grappling Kinematics**:
   - `01_apps/spatial_and_3d/grapplingmap_web/grappling.opml` & `10_spatial_grappling_kinematics/opml_trees/grappling.opml`: Canonical 3,044-node OPML mindmap tree across Wrestling, Guard, Pins, and Scrambles.
   - `00_core_infrastructure/self_healing_hub/src/spatial_grappling_map_engine.py` (lines 1-100): `SpatialGrapplingMapEngine` parsing 3,044 outline nodes into 3D spatial mat coordinates $(x, y, z)$ on a 10m x 10m tatami grid with MediaPipe 33-landmark 3D kinematic skeleton integration.

3. **Gamified Combat Arena**:
   - `01_apps/canonical_port/tui/tui_live_arena_dev.py` (lines 1-100): Hermes 3 + OpenClaw (Red Faction) vs LuCI OpenWrt + Sentinel (Blue Faction) with 4 game modes, animated 120 FPS compute power tug-of-war bar, live Movesense pulse gauge, dual graphical topology maps, 1-key battle abilities (`[c]`, `[h]`, `[b]`, `[s]`), and RAG voice TTS.

4. **Headless Shopify Storefront**:
   - `01_apps/commerce_and_business/storefront_membership_tui.py` (lines 1-100): Tiered membership architecture ($9 Athlete, $29 Pro, $99 Gym Team/mo), hardware sensor bundles (Movesense HR+ 512Hz chest/bicep straps), headless GraphQL checkout.

5. **Canonical Port 9-Screen NOC**:
   - `01_apps/canonical_port/tui/canonical_tui.py` (lines 1-100): 9-Screen stability hierarchy covering Swarm Chat IDE, Layer 0 Network, Layer 1 Hardware NOC (7 physical nodes, 108GB RAM pool), Layer 2 Biometrics, Layer 3 Model Mesh, Layer 4 Training/LoRA, Layer 5 Governance/Debate, Layer 6 Tooling/Daemons, Layer 7 Network Settings Optimizer, All Tabs Grid, and Obsidian Vault Explorer.

6. **SmolAgents Python Duel Sandbox**:
   - `05_agents_and_swarms/red_blue_arena/smolagents_arena_engine.py` (lines 1-100): `SmolagentsArenaEngine` and `SmolagentsToolRegistry` providing executable Python tools (`probe_socket`, `get_mesh_latency`, `inspect_vram_load`, `apply_kamath_filter`) with code-as-action sandboxed execution.

7. **Standalone Qwen Math Trend Optimizer**:
   - `02_ai_models_and_inference/quantum/autonomous_math_trend_optimizer.py` (lines 1-100): Decoupled background analytics computing inverse-variance latency striping weights, BQL buffer depths, cardiac coherence index, and 24/7 LoRA SFT/DPO JSONL serialization.

8. **Web-TUI Server**:
   - `01_apps/canonical_port/tui/serve_web_tui.py` (lines 1-399): WebSocket PTY engine on Port 8088 routing `/readiness`, `/grappling`, `/arena`, `/store`, `/canonical`, `/smolagents`, and `/math` using xterm.js WebGL rendering at 120 FPS.

---

## 2. Logic Chain

1. **Requirement Mapping**: R1 and R2 mandate a clean architectural separation of the monorepo application portfolio into two isolated tiers: `01_apps/user_facing_and_scaling/` and `01_apps/operator_and_dev/`.
2. **Current Scattering**: Existing files are currently distributed across `01_apps/biometrics/`, `01_apps/spatial_and_3d/`, `01_apps/canonical_port/`, `01_apps/commerce_and_business/`, `00_core_infrastructure/`, `03_biometrics_and_telemetry/`, and `05_agents_and_swarms/`.
3. **Decoupling Strategy**: By establishing standardized sub-packages (`core/`, `dsp/`, `presentation/`, `transport/`) in `movesense_readiness_hub` and creating dedicated top-level modules for the other 6 apps under their respective domain folders, we eliminate cyclic imports and developer tool clutter in consumer paths.
4. **Unified Access via Port 8088**: Centralizing `serve_web_tui.py` as `01_apps/web_tui_portal/serve_portal.py` enables all 7 applications to be launched independently or accessed simultaneously through a unified landing page and individual WebSocket PTY routes at 120 FPS.
5. **Airgap Integrity**: Separating mathematical DSP logic into local shared libraries preserves 100% airgap compliance (Rule #0), while free-tier AI APIs (Gemini Flash, Cloudflare Workers AI) are utilized exclusively for autonomous code generation, UI scaffolding, and unit test generation.

---

## 3. Caveats

- **Port Conflicts**: Port 8088 must be reclaimed automatically on startup using process termination (`lsof -ti :8088 | xargs kill -9`) to prevent stale daemon collision.
- **PTY Environment Variables**: PTY subprocess execution in `serve_web_tui.py` requires explicit `PYTHONPATH` injection pointing to the restructured directory hierarchy.
- **Zero-Mock Discipline**: In accordance with Rule #0, all visualizers must display clean waiting states (`--`) when physical sensors or hardware links are disconnected.

---

## 4. Conclusion

The application build-out plan is fully mapped, verified against monorepo code, and ready for structural separation into:
1. `01_apps/user_facing_and_scaling/`
   - `movesense_readiness_hub/` (`core/`, `dsp/`, `presentation/`, `transport/`, `web/`, `mobile/`)
   - `spatial_grappling_3d/` (`core/`, `kinematics/`, `opml_trees/`, `presentation/`)
   - `combat_arena/` (`core/`, `modes/`, `presentation/`)
   - `shopify_storefront/` (`core/`, `graphql/`, `presentation/`)
2. `01_apps/operator_and_dev/`
   - `canonical_port/` (`screens/`, `views/`, `widgets/`, `services/`, `backend/`)
   - `smolagents_duel_sandbox/` (`core/`, `tools/`, `presentation/`)
   - `qwen_math_trend_optimizer/` (`core/`, `models/`, `presentation/`)
3. `01_apps/web_tui_portal/`
   - Unified FastAPI + WebSocket PTY server on Port 8088 serving all 7 apps at 120 FPS.

---

## 5. Verification Method

1. **Verify Analysis Artifacts**:
   - Inspect `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/teamwork_preview_explorer_survey_2/analysis.md`
   - Inspect `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/teamwork_preview_explorer_survey_2/handoff.md`
2. **Verify Target Application Source Files**:
   - `python3 -m py_compile /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/biometrics/movesense_readiness_tui.py`
   - `python3 -m py_compile /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/self_healing_hub/src/spatial_grappling_map_engine.py`
   - `python3 -m py_compile /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/tui/tui_live_arena_dev.py`
   - `python3 -m py_compile /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/commerce_and_business/storefront_membership_tui.py`
   - `python3 -m py_compile /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/tui/canonical_tui.py`
   - `python3 -m py_compile /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/05_agents_and_swarms/red_blue_arena/smolagents_arena_engine.py`
   - `python3 -m py_compile /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/quantum/autonomous_math_trend_optimizer.py`
   - `python3 -m py_compile /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/tui/serve_web_tui.py`
3. **Verify Web-TUI Portal Execution**:
   - Launch `python3 /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/tui/serve_web_tui.py` and query `curl -I http://localhost:8088/` to verify HTTP 200 responses across all endpoints.
