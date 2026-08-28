# Lauburu Swarm Dashboard (localhost:3000): End-to-End Functional & UI/UX Requirements Specification & 14-Point Rubric Matrix

**Author:** `spec_miner_2` (Specification Mining Agent)  
**Date:** 2026-08-25T14:00:00Z  
**Target Application:** `http://localhost:3000` (Lauburu Swarm Mesh Dashboard)  
**Monorepo Root:** `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo`  
**Frontend Source:** `00_core_infrastructure/self_healing_hub/frontend/src/`  
**Backend API Gateway:** `http://localhost:5001` (`00_core_infrastructure/self_healing_hub/src/api_server.py`)  

---

## 1. Executive Summary & Specification Scope

The **Lauburu Swarm Dashboard** on `http://localhost:3000` serves as the centralized mission-control interface for the 7-Device Physical Mesh, 82.8 GB Pooled VRAM distributed cluster, real-time biometrics DSP pipeline, and autonomous multi-agent governance system.

This specification document establishes the authoritative requirements, architectural data flows, component hierarchies, backend API contracts, and the **Strict 14-Point Assessment Rubric** governing the comprehensive end-to-end evaluation of the dashboard. In accordance with the user's explicit directives:
1. **Dynamic Human Interaction:** Every feature requirement mandates dynamic human-perspective interaction testing (clicking, menu navigation, widget interactions, form inputs, user journey flow) in addition to static visual and code-level inspection.
2. **Empirical Data Authenticity (Rule #0):** Every feature must be audited against empirical ground-truth telemetry from physical hardware, real BLE biometrics sensors, and live daemons, strictly prohibiting hallucinated or hardcoded simulated mock data.

---

## 2. Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | Developer Workspace | Custom Voice IDE & Multi-Device Workspace | 3-column IDE integrating voice STT/TTS coding, multi-device app simulator (Android, iPhone, Laptop), and multi-daemon live logs | Mic audio stream, voice commands, device selection, zoom level | Synthesized voice TTS, AST code updates, simulated UI viewport, daemon logs | Web Speech API fallback, terminal disconnect notices | `CustomVoiceIDEView.jsx`, `IDENativeVoiceChannel.jsx`, `AppSimulatorWorkspace.jsx` |
| 2 | AI Governance | Meta-Training Game & AI Debate State Machine | 4-turn deliberative consensus state machine (Theses -> Cross-Exam -> Concessions -> Accord), FIDE ELO ledger, and AST task dispatcher | Topic string, domain, model selections (Cloud Titan, Local Sovereign, Genetic MoE) | 4-turn structured debate transcripts, CoT reasoning, ELO delta updates, `truth_audit_debate.jsonl` | Graceful fallback banner, automatic retry with exponential backoff | `MetaTrainingGameDashboardView.jsx`, `api_server.py:4447` |
| 3 | Distributed Hardware | Global 11-Config Hardware & Model Profiler | Visualizer for 11 hardware topologies across 7 physical nodes (82.8GB VRAM), dual AI benchmarks, and NVIDIA linear speedups | Filter criteria (`all`, `home_2_device`, `cross_platform`, `mobile`, `full_mesh`) | VRAM distribution bars, latency (0.277ms TB4), TTFT speedup, memory bandwidth | Loading spinner, cached fallback topology | `GlobalMeshShardingProfiler.jsx`, `/api/network/global_sharding_profiler` |
| 4 | Benchmarking & Gaming | Public AI Benchmarks & CTF Faction Arena | Multi-suite benchmark evaluation (SWE-bench, TerminalBench), 1v1 Fighter duels, and Blue Mesh vs Red Cloud CTF simulation | Benchmark suite selection, fighter choices, CTF action triggers (`ast_exploit`, `firewall_probe`) | Match scores, extracted flags (`FLAG{...}`), ELO adjustments, LCT token rewards | Inline failure message, fallback leaderboard cache | `PublicBenchmarkArenaView.jsx`, `/api/benchmarks/public_suite` |
| 5 | 3D World Models | AI Training Game (Genie 2 Tatami Arena) | DeepMind Genie 2 3D spatial world with WebGPU 120 FPS WGSL tensor compute, 1v1 martial grappling duels, and autonomous tick engine | Grappling technique choice, challenge type, WebGPU matrix size | 3D canvas rendering, WGSL GEMM GFLOPs benchmark, LoRA dataset pairs, LCT tokens | Canvas WebGL fallback, WebGPU unsupported notice | `UnifiedGenieTatamiArenaView.jsx`, `WebGPUComputeEngine.js` |
| 6 | Distributed Inference | EXO Distributed P2P Inference Cluster | P2P inference cluster manager on port 52415, embedding native Exo UI, OpenAI-compatible chat, and Multi-WAN telemetry | Model key, prompt string, temperature, max_tokens | Streaming tokens, cluster node topology, multi-WAN throughput/latency | Port 52415 offline banner, error role message | `ExoClusterView.jsx`, `http://localhost:52415/models` |
| 7 | Multi-Agent Consensus | Specialist Skills & Consensus Dashboard | Consensus governance for 13 subsystem skills, dynamic ROI moves execution, and full-parameter visual AI leaderboard | Dynamic ROI action keys (`SHARD_KIMI_TITAN`, `WEBGPU_120FPS`, `LORA_PROMOTE`) | Executed move confirmation, Metal/WebGPU latency profiler report | Action execution retry, terminal log fallback | `ConsensusSpecialistSkillsDashboard.jsx`, `WebGPUVisualizer.jsx` |
| 8 | Spatial Biomechanics | 3D Instructional Map & Kinematic Editor | Interactive 3D spatial node and transition editor mapping 955-node OPML grappling taxonomy with joint torque (Nm) calculations | Node coordinates (X, Y, Z), risk level, transition difficulty, torque | Rendered kinematic graph, animated flow simulation, exported LoRA pairs | Form validation alerts, API error catch | `SpatialGrapplingMapEditorView.jsx`, `/api/spatial/grappling_map` |
| 9 | Dataset Harvesting | Live Real-Data Training Streams (Harvester) | Real-time monitoring and manual ingestion across 4 live data streams (128Hz Movesense, Shopify Storefront, Git AST, Mesh Telemetry) | Stream category filter (`all`, `biometrics`, `commerce`, `ast`, `mesh`), manual harvest trigger | Ingested record counters, size (MB), ShareGPT JSON sample preview | Stream ingestion warning, cached telemetry fallback | `LiveTrainingDataHarvesterView.jsx`, `/api/lora/live_harvesting_metrics` |
| 10 | Low-Power Edge Vision | Grappling Vision, NPU (1.2W) & Token Gating | 1.2W NPU-accelerated MediaPipe 3D pose + 128Hz IMU EKF fusion with safety radar and token-gated Shopify membership check | Customer access token / email, live stream toggle | Hyperextension risk gauge, Kimura rotational torque, membership tier unlock | Safe risk default, validation error message | `GrapplingVisionBiometricsView.jsx`, `/api/shopify/validate_membership` |
| 11 | Distributed Compute | PySpark Mesh Control Center & Canonical Crons (:8750) | Control center for PySpark distributed engine, 7-device node status, 10-route Multi-WAN accelerator, and 18 ROI-ranked crons | Cron search query, view mode toggle (`native`, `iframe`), sub-service switch | Live RDD partitions, RPC latency, cron execution status, storage pool health | Tri-level fallback (:5001 -> :8750 -> :8088) | `PySparkMeshControlCenterView.jsx`, `/api/spark-metrics` |
| 12 | Conversational Hub | Tri-Orchestrator Live Chat & Action Room | Multi-agent live discussion room (Cloud Titan, Local Sovereign, Genetic MoE) with executable embedded action buttons | Prompt string, chat mode (`multi_beam`, `consensus`, `debate`), filter chip | Optimistic message bubbles, streaming agent replies, action toast feedback | Offline indicator, dispatch error toast | `TriOrchestratorLiveChatView.jsx`, `/api/chat/messages` |
| 13 | Spatial Computing | 3D Spatial Radar & DeepMind Genie 2 Hologram | UWB spatial anchor positioning, 60 FPS Genie 2 generative world, and SVG 3D isometric laser mesh projection | View mode (`genie_world`, `3d_hologram`, `vlm_raycast`, `entities_list`) | SVG optical beam links, 3D room coordinates, active entity cards | Polling fallback banner, zero-node default | `Spatial3DMapView.jsx`, `Genie3DSpatialWorldView.jsx` |
| 14 | Training & Distillation | 24/7 NPU Acceleration & Multi-Stream LoRA Training Hub | Continuous harvesting of OS metrics, chat transcripts, and biometrics accelerated by Apple ANE, Tensor TPU, Snapdragon NPU | Sample index navigation, distillation trigger | 121 TOPS cluster status, live loss metrics, sample inspector | Client-side feedback banner, API catch | `AITrainingHub.jsx`, `ShardedRPCClusterSafetyView.jsx` |
| 15 | System Governor (Global) | 7-Layer Live Device Sentinel HUD | Real-time device monitor, battery/thermal telemetry, disconnected channel alerts, and 1-click auto-recovery | Alert dismiss click, auto-recover device ID, force ranking trigger | High-priority alert banner, OS desktop notifications, top-7 rank badges | Auto-heal dispatched badge, manual heal fallback | `LiveDeviceSentinelHUD.jsx`, `/api/devices/live_monitor` |
| 16 | System Governor (Global) | Persistent Local AI Model Stream Sidebar | Collapsible floating bottom dock tracking active GGUF model downloads, speeds (MB/s), ETA, and 10G TB4 link latency | Header click to toggle collapse/expand | Real-time progress bar, downloaded GB counter, ETA minutes | Hides cleanly if no download data available | `ModelDownloadSidebar.jsx`, `/api/models/download_status` |

---

## 3. Edge Cases & Observed System Behaviors

| # | Feature | Input / Condition | Observed / Documented Behavior | Error Handling & Recovery |
|---|---------|-------------------|--------------------------------|---------------------------|
| 1 | Custom Voice IDE | Initial application load with default state `useState('custom_voice_ide')` | Blank viewport rendered below navigation bar because `App.jsx` lacks a conditional render check for `'custom_voice_ide'` | **Critical Bug:** User must manually click another tab and click back. Fix required in `App.jsx`. |
| 2 | Live Device Sentinel | Multiple network/AI channels disconnect simultaneously on a node (e.g. Pixel 10 drops Wi-Fi & ADB) | High-priority red alert banner triggers, OS desktop notification is dispatched via Web Notification API, disconnected channel icons are replaced by `❌` | Auto-heal daemon is triggered via `/api/devices/auto_recover` with 1-click manual override fallback. |
| 3 | PySpark Control Center | Port 5001 API server is slow or unreachable | Component executes cascading serial fallback: first attempts `:5001/api/spark-metrics`, then `:8750/api/spark-metrics`, then `:8088/status` | If all fail, renders default static fallback telemetry state with offline warning. |
| 4 | EXO Cluster | Port 52415 Exo daemon is stopped or uninitialized | Embedded iframe shows native browser connection refused screen; chat input returns `❌ Connection Error to Exo (:52415)` | Status dock displays `Exo Cluster Offline (Port 52415)` with red border. |
| 5 | WebGPU Tatami Shaders | Browser lacks WebGPU support or `navigator.gpu` is undefined (e.g., standard Firefox or older Chrome) | `WebGPUComputeEngine.js` fails gracefully, `webGpuState.supported` is set to `false`, visualizer shows `⚡ Initializing 120 FPS WebGPU Hardware Pipeline & Shaders...` | Fallback Canvas2D / WebGL2 rendering path activates automatically. |
| 6 | Grappling Vision & Token Gating | User submits email verification in Shopify token-gating form | Component executes `handleVerifyShopify`, but code currently sends hardcoded `'sample_token_or_email'` instead of `shopifyEmail` state | **Code Flaw:** Form input is ignored. Must update payload to `{ customerAccessToken: shopifyEmail }`. |
| 7 | Meta-Training Debate | Auto-debate toggle enabled while API server is under heavy load | 15-second countdown timer fires `/api/debate/execute_ui_debate`; if response takes >15s, timer resets cleanly using `useRef` | Prevents overlapping concurrent debate executions. |
| 8 | 3D Spatial Radar | Room coordinates exceed standard 6m x 4m bounds (e.g. Node X = 8.5m) | SVG isometric projection formula (`400 + x * 110`) calculates coordinates outside viewBox `800x450`, causing SVG clipping | Nodes render off-screen. Formula must be updated to use normalized dynamic scaling. |

---

## 4. Strict 14-Point Assessment Rubric Schema

Every modular feature tab on `localhost:3000` must be evaluated against this standardized 9-pillar rubric.

```
================================================================================
RUBRIC PILLAR                         EVALUATION CRITERIA
================================================================================
1. Feature ID & Classification        Exact tab ID, display label, and architectural category
2. Visual Layout & UI Hierarchy       Component layout, card styling, visual density, responsive grid
3. Code-Level Data Flow & State       React hooks, state management, props drilling, memoization
4. Real API Contracts & Endpoints     HTTP/WS endpoints, request methods, payload structures, polling rates
5. Dynamic Human Interaction Protocol Step-by-step interactive testing (clicks, inputs, toggles, journeys)
6. Rule #0 Data Authenticity Audit    Empirical hardware telemetry source validation (Zero fake/mock data)
7. Error Handling & Edge Behaviors    Fallback states, loading skeletons, disconnect recovery, timeouts
8. Change / Removal Justification     At least one concrete architectural or UI improvement/removal justification
9. Rubric Compliance Verdict          PASS / REMEDIATE / REMOVE with quantitative score (0-100%)
================================================================================
```

---

## 5. Detailed 14-Feature Requirements & Evaluation Matrix

### Point 1: Custom Voice IDE & Multi-Device Workspace (`custom_voice_ide`)
- **Component Path:** `00_core_infrastructure/self_healing_hub/frontend/src/CustomVoiceIDEView.jsx`
- **Visual Layout:** 3-column split view (`1fr 2fr 1fr`):
  - Left: AI Fabric Chat (`TriOrchestratorLiveChatView`)
  - Center: App Simulator Workspace with voice coding banner, device frame previewer (Android 412x890, iPhone 393x852, Laptop 1180x740), orientation toggle, and zoom control.
  - Right: Live daemon log terminals (`/api/logs/exo`, `/api/logs/llamacpp`, `/api/logs/petals`).
- **Data Flow & State:**
  - Speech Recognition: Web Speech API via `IDENativeVoiceChannel.jsx` (`isListening`, `transcript`, `voiceActive`).
  - Simulator State: `device` ('android'|'iphone'|'laptop'), `orientation` ('portrait'|'landscape'), `zoomLevel` (0.5 to 1.5).
  - Terminal Logs: Periodic text stream polling via `BackendTerminal.jsx`.
- **Backend Endpoints:**
  - `GET /api/logs/exo` (Exo MLX Native daemon logs)
  - `GET /api/logs/llamacpp` (llama.cpp RPC sharding daemon logs)
  - `GET /api/logs/petals` (Petals DHT background logs)
  - `POST /api/chat/voice_transcribe` (Audio token ingestion)
- **Dynamic Human Interaction Protocol:**
  1. Click target simulator buttons: Switch from Android (default) to iPhone, then Laptop/PC; observe frame dimension and bezel radius transformations.
  2. Toggle Orientation button: Rotate Android viewport from Portrait (412x890) to Landscape (890x412).
  3. Drag Zoom Level slider: Scale simulator frame from 50% to 120% and verify viewport scaling.
  4. Click "🎙️ Start Voice Coding Session" in `IDENativeVoiceChannel`: Verify microphone permissions prompt, speak test command, and verify transcript displays in real-time.
  5. Type message in AI Fabric Chat left column and verify reply appears without breaking simulator center layout.
- **Rule #0 Data Authenticity Verification:**
  - Verify that daemon logs in right column reflect genuine process streams from local process daemons (`ps aux | grep llama-server` / `exo`), not simulated filler strings.
- **Architectural / UI Change Justification:**
  - **Critical Fix:** Add `{mainNavTab === 'custom_voice_ide' && <CustomVoiceIDEView />}` to the conditional render block in `App.jsx` to eliminate initial blank-screen bug.
  - **Responsive UI:** Convert rigid 3-column layout to collapsible accordion / drawer columns on screens under 1440px.

---

### Point 2: Meta-Training Game & AI Debate Arena (`meta_training_debate`)
- **Component Path:** `00_core_infrastructure/self_healing_hub/frontend/src/MetaTrainingGameDashboardView.jsx`
- **Visual Layout:**
  - Top ELO leaderboard metrics card with real-time FIDE ratings, win rates, and active debate countdown.
  - Model selection matrix for Cloud Titans, Local Sovereigns, and Genetic MoE.
  - 4-turn interactive debate transcript view with collapsible CoT reasoning traces.
  - Real Task Dispatcher with Subsystem selector (00 to 12), code editor, and AST compliance slider.
- **Data Flow & State:**
  - `activeSubTab` ('arena'|'consensus_telemetry'|'elo_dispatcher'|'lora_harvest').
  - `debateRecord` (stores 4-turn output: Opening Theses, Cross-Examination, Technical Concessions, Unanimous Accord).
  - `isDebating`, `autoDebateActive`, `autoDebateCountdown` (15s timer).
- **Backend Endpoints:**
  - `GET /api/canonical_ai_leaderboard` (FIDE ELO scores & records)
  - `GET /api/dispatch/subsystems` (13 subsystems taxonomy)
  - `GET /api/live_agent_debate/history` (Debate transcripts & LoRA dataset)
  - `POST /api/debate/execute_ui_debate` (Execute 4-turn debate state machine)
  - `POST /api/dispatch/task` (Dispatch AST-verified task to winning model)
- **Dynamic Human Interaction Protocol:**
  1. Select preset debate topic from dropdown (e.g. "WebGPU 120 FPS Tatami Shaders") or type custom topic in input box.
  2. Select Cloud Model (Gemini 3.7 Flash) and Local Model (Kimi Tandem Titan 88B) chips.
  3. Click "⚡ Execute Live 4-Turn Debate" button; verify loading spinner, live turn rendering, and final Unanimous Accord generation.
  4. Click "🔍 Expand Full CoT Reasoning" on individual turns to verify structured reasoning chains.
  5. Toggle Auto-Debate loop switch (`ON`/`OFF`), observe 15s countdown timer, and verify automatic turn advancement.
  6. Switch to "Real Task Dispatcher" sub-tab, select subsystem `01_apps`, paste code snippet, click "🚀 Dispatch Verified Task to ELO Winner", and inspect AST verification confirmation.
- **Rule #0 Data Authenticity Verification:**
  - Verify that debate transcripts are saved to real disk ledger `truth_audit_nomad_mesh_debate.jsonl` and that model ELO ratings update in `canonical_ai_leaderboard.py`.
- **Architectural / UI Change Justification:**
  - **Modularization:** Refactor the 1,550-line file into dedicated sub-tab modules (`DebateArenaTab.jsx`, `EloDispatcherTab.jsx`, `LoraHarvestTab.jsx`).
  - **Streaming:** Migrate from blocking HTTP POST to Server-Sent Events (SSE) `/api/debate/stream` for character-by-character token rendering.

---

### Point 3: Global 11-Config Hardware & Model Profiler (`global_profiler`)
- **Component Path:** `00_core_infrastructure/self_healing_hub/frontend/src/GlobalMeshShardingProfiler.jsx`
- **Visual Layout:**
  - Top stats dock: 7 Physical Nodes, 82.8 GB Pooled VRAM, +18.8GB to +30.8GB MoE headroom, 25.1x NVIDIA linear speedup.
  - Sub-tabs bar: `'configs'`, `'tasks'`, `'nvidia_linear'`, `'models'`, `'transports'`.
  - Filter chips: `All`, `Home 2-Device`, `Cross-Platform`, `Mobile`, `Full Mesh`.
  - 11 Topology Cards displaying nodes, VRAM split, Thunderbolt 4 / Ethernet latency, and ROI score.
- **Data Flow & State:**
  - `selectedFilter` ('all'|'home_2_device'|'cross_platform'|'mobile'|'full_mesh').
  - `selectedConfig` (detailed view object).
  - `activeTab` ('configs'|'tasks'|'nvidia_linear'|'models'|'transports').
- **Backend Endpoints:**
  - `GET /api/network/global_sharding_profiler` (Polled every 10s).
- **Dynamic Human Interaction Protocol:**
  1. Click filter chips (`home_2_device`, `cross_platform`, `mobile`, `full_mesh`) and verify topology list filters instantly.
  2. Click on a specific configuration card (e.g. Config 1: 7-Device Full Mesh) to view detailed VRAM sharding allocation breakdown.
  3. Switch sub-tabs to `'tasks'`, `'nvidia_linear'`, `'models'`, and `'transports'` to verify dual-benchmark charts and speedup tables.
  4. Hover over node memory bars to verify exact MB allocations and `-ts` layer split.
- **Rule #0 Data Authenticity Verification:**
  - Verify that the 7 physical nodes and 82.8 GB VRAM capacity correspond to genuine device specs in `device_registry.py` and actual ping latencies over `169.254.187.138` (TB4 DMA 0.277ms).
- **Architectural / UI Change Justification:**
  - **Actionable Execution:** Add a 1-click "Apply & Restart RPC Mesh" button linking directly to `/api/rpc_sharding/tune` to dynamically apply the selected tensor split to live daemons.
  - **Mobile Layout:** Wrap cards in responsive CSS grid `minmax(320px, 1fr)` to prevent card compression on tablet screens.

---

### Point 4: Public AI Benchmarks & CTF Faction Arena (`public_benchmarks`)
- **Component Path:** `00_core_infrastructure/self_healing_hub/frontend/src/PublicBenchmarkArenaView.jsx`
- **Visual Layout:**
  - Multi-tab navigation: `'arena'`, `'project_context_accuracy'`, `'ctf_faction_battle'`, `'playable_game'`, `'leaderboard'`, `'harvest_feed'`.
  - Benchmark Suite Card (SWE-bench, TerminalBench 2.1, Arena-Hard, BigCode-Bench, Biometrics-DSP-Bench).
  - CTF Faction Battle Arena: Blue Mesh vs Red Cloud battle console, action command triggers, and capture-the-flag reward terminal.
  - Project Context Accuracy evaluation arena with query input and ground-truth comparison against specs 00-12.
- **Data Flow & State:**
  - `activeTab`, `selectedFighter1`, `selectedFighter2`, `isBattling`, `ctfBattleState`, `contextAccuracyState`.
  - `ctfLogs` (in-memory terminal combat history).
- **Backend Endpoints:**
  - `GET /api/benchmarks/public_suite`
  - `GET /api/canonical_ai_leaderboard`
  - `POST /api/benchmarks/ctf_faction_battle` (Actions: `brute_force`, `firewall_probe`, `ast_exploit`, `flag_capture`)
  - `POST /api/benchmarks/context_accuracy_eval` (Query accuracy testing)
  - `POST /api/benchmarks/vote` (Cast user vote)
- **Dynamic Human Interaction Protocol:**
  1. Switch to `'ctf_faction_battle'` sub-tab, click action button (e.g. "Firewall Probe" or "AST Exploit"), observe streaming combat logs, winner resolution, and extracted flag `FLAG{...}`.
  2. Switch to `'project_context_accuracy'` sub-tab, select preset query (e.g. "Kamath Artifact Correction in Spec 03") or type custom query, click "Run Context Accuracy Test", and compare Local vs Cloud response precision.
  3. Switch to `'arena'`, select Fighter 1 and Fighter 2, click "Run Benchmark Battle", vote for the winning model, and verify ELO rating update.
- **Rule #0 Data Authenticity Verification:**
  - Verify that context accuracy test answers are evaluated against genuine markdown files in `00_core_infrastructure` through `12_continuous_lora_evolution` rather than synthetic responses.
- **Architectural / UI Change Justification:**
  - **File Decomposition:** Split 1,581-line monolithic component into dedicated sub-views (`CtfFactionArena.jsx`, `ContextAccuracyView.jsx`, `BenchmarkLeaderboard.jsx`).
  - **Persistence:** Save CTF match history to `04_data_and_memory/ctf_tournament_ledger.jsonl` to survive page reloads.

---

### Point 5: AI Training Game (Genie 2 Tatami Arena & 3D Spatial Canvas) (`ai_training_game`)
- **Component Path:** `00_core_infrastructure/self_healing_hub/frontend/src/UnifiedGenieTatamiArenaView.jsx`
- **Visual Layout:**
  - 3D Tatami Arena canvas with WebGPU 120 FPS particle shader visualization.
  - 1v1 Fighter duel panel with grapple technique dropdown (Berimbolo, Flying Armbar, Heel Hook, Kimura Sweep) and challenge domain.
  - Autonomous AI Consensus Engine status dock with live 4s tick countdown, phase badge, and session statistics.
  - WebGPU Hardware Acceleration & WGSL Compute Shader benchmark panel.
- **Data Flow & State:**
  - `subTab` ('duels'|'edge_fleet'|'factions_shop'|'pyspark_lora'|'multi_wan'|'webgpu_compute').
  - `isAutonomousActive`, `tickCountdown`, `webGpuState`, `sessionStats`.
- **Backend Endpoints:**
  - `GET /api/game_arena/state`
  - `GET /api/canonical_ai_leaderboard`
  - `GET /api/game/shop_items`
  - `POST /api/game_arena/duel`
  - `POST /api/game/buy_product`
  - `POST /api/game_arena/tick`
- **Dynamic Human Interaction Protocol:**
  1. Toggle Autonomous Mode (`ON`/`OFF`), observe 4s tick countdown, and verify automatic 1v1 duel execution and action log streaming.
  2. In `'duels'` sub-tab, manually select Fighter 1, Fighter 2, Challenge Type, and Grapple Technique, click "🥋 Fight 1v1 Arena Duel", and inspect output ELO delta and synthesized LoRA pair.
  3. In `'webgpu_compute'` sub-tab, click "⚡ Run WebGPU Hardware Benchmark" (256x256 / 512x512 matrix multiply) and verify Metal/WGSL GFLOPs throughput.
  4. In `'factions_shop'` sub-tab, select an available upgrade item, click "Buy Upgrade", and verify LCT token balance deduction.
- **Rule #0 Data Authenticity Verification:**
  - Verify that WebGPU matrix benchmarks execute genuine WGSL shaders on the client GPU (`navigator.gpu.requestAdapter()`) and return real nanosecond timestamps.
- **Architectural / UI Change Justification:**
  - **WebGL/WebGPU Cleanup:** Add explicit context loss and resource disposal handlers on unmount in `Genie3DSpatialWorldView` to prevent browser tab GPU memory leaks.
  - **Fallback Canvas:** Provide graceful Canvas2D fallback for browsers with WebGPU disabled.

---

### Point 6: EXO Distributed P2P Inference Cluster (`exo_cluster`)
- **Component Path:** `00_core_infrastructure/self_healing_hub/frontend/src/ExoClusterView.jsx`
- **Visual Layout:**
  - Top cluster status dock showing port 52415 online status, connected nodes, and loaded models.
  - Sub-tabs bar: `'embedded_ui'`, `'direct_chat'`, `'multiwan_matrix'`.
  - Embedded Exo native cluster visualization iframe (`http://localhost:52415`).
  - Direct Chat interface with model selector (`mlx-community/Qwen3.5-122B-A10B-8bit`), chat transcript, and prompt input.
  - Multi-WAN transport matrix breakdown table.
- **Data Flow & State:**
  - `exoStatus` ({ online, port, nodeCount, modelCount }).
  - `models`, `selectedModel`, `prompt`, `chatLog`, `isInferencing`, `multiWanData`.
- **Backend Endpoints:**
  - `GET http://localhost:52415/models`
  - `POST http://localhost:52415/v1/chat/completions`
  - `GET /api/network/multi_wan_accelerator`
- **Dynamic Human Interaction Protocol:**
  1. Switch between sub-tabs (`embedded_ui`, `direct_chat`, `multiwan_matrix`).
  2. In `'direct_chat'`, select model from dropdown, type prompt, click Send, and verify response from port 52415.
  3. In `'multiwan_matrix'`, inspect live throughput and latency stats across Thunderbolt 4, 10GbE, and WiFi 7 links.
  4. In `'embedded_ui'`, click and drag to orbit Exo's native ring memory / P2P device topology graph.
- **Rule #0 Data Authenticity Verification:**
  - Verify live HTTP socket connectivity to Exo MLX daemon on port 52415 and empirical token throughput from real model inference.
- **Architectural / UI Change Justification:**
  - **Self-Healing Launch Trigger:** Add 1-click "🚀 Start Exo Daemon" button when port 52415 is unreachable to trigger background launch via `/api/daemons/start_exo`.
  - **Timeout Protection:** Implement 8s request timeout on chat completions with user-friendly error recovery.

---

### Point 7: Specialist Skills & Consensus Dashboard (`specialist_skills`)
- **Component Path:** `00_core_infrastructure/self_healing_hub/frontend/src/ConsensusSpecialistSkillsDashboard.jsx`
- **Visual Layout:**
  - WebGPU 120 FPS Hardware Pipeline & Shader canvas visualizer (lazy-loaded).
  - Dynamic Live ROI Moves cards with status badges, confidence ratings, and 1-click execution triggers.
  - Strongest Frontier Vision-Language Models Leaderboard (Ranks 1 to 8).
  - GPU hardware profiling report generator.
- **Data Flow & State:**
  - `dynamicRoiMoves`, `executingMove`, `profilerReport`, `isProfiling`, `roiCycle`.
- **Backend Endpoints:**
  - `GET /api/mesh/dynamic_roi_moves` (Polled every 6s)
  - `POST /api/mesh/execute_roi_move` (Action key execution)
  - `POST /api/consensus/force_evaluate`
- **Dynamic Human Interaction Protocol:**
  1. Click "Execute Optimization" button on any active ROI move card (e.g. "Shard Kimi Tandem Titan over TB4 DMA"); verify button state switches to "⚡ Executing..." and refreshes the move list.
  2. Click "⚡ Trigger Full Consensus Loop" button to initiate consensus evaluation across all 13 subsystem specialists.
  3. Click "📊 Profile Metal/WebGPU Hardware" button to run GPU benchmark and inspect latency/GFLOPs report.
  4. Sort or filter the Visual AI Leaderboard by ELO, win rate, or aesthetic quality score.
- **Rule #0 Data Authenticity Verification:**
  - Verify that ROI actions dispatch real system commands via `06_scripts_and_tooling` and update actual state in `00_SYSTEM_DASHBOARDS/CRON_ROI_GOVERNANCE_DASHBOARD.md`.
- **Architectural / UI Change Justification:**
  - **Skill Deep-Links:** Add direct clickable links to each specialist skill's `SKILL.md` in the monorepo.
  - **Canvas Fallback:** Provide Canvas2D fallback when WebGPU hardware visualizer is compiling shaders.

---

### Point 8: 3D Instructional Map & Kinematic Editor (`spatial_map_editor`)
- **Component Path:** `00_core_infrastructure/self_healing_hub/frontend/src/SpatialGrapplingMapEditorView.jsx`
- **Visual Layout:**
  - Sub-tabs: `'canvas'`, `'node_editor'`, `'transition_linker'`, `'flow_sim'`.
  - 2D/3D interactive spatial node canvas.
  - Node Inspector & Editor form with coordinate inputs (X, Y, Z meters), category, risk level, and description.
  - Transition Linker form with Origin, Destination, difficulty, torque (Nm), and min execution time.
  - Biomechanical Flow Simulator panel with path visualizer.
- **Data Flow & State:**
  - `mapData`, `selectedNode`, `selectedTransition`, `nodeForm`, `transForm`, `simulatedChain`.
- **Backend Endpoints:**
  - `GET /api/spatial/grappling_map`
  - `POST /api/spatial/grappling_map/node`
  - `POST /api/spatial/grappling_map/transition`
  - `POST /api/spatial/grappling_map/simulate_flow`
- **Dynamic Human Interaction Protocol:**
  1. Click on any spatial node in the canvas or list to inspect coordinates and risk parameters.
  2. Switch to `'node_editor'`, edit coordinates (e.g. X: 0.5, Y: 1.8, Z: 0.2), click "Save Node", and verify update confirmation.
  3. Switch to `'transition_linker'`, select Origin "Closed Guard" and Destination "Armbar", set Torque (180 Nm), click "Link Transition".
  4. Switch to `'flow_sim'`, select Start Node and End Node, click "Simulate Biomechanical Path", and observe animated transition sequence.
- **Rule #0 Data Authenticity Verification:**
  - Verify that spatial node taxonomy matches real 955-node OPML tree in `project_map.opml` and joint torques adhere to physical biomechanical constraints in Spec 10.
- **Architectural / UI Change Justification:**
  - **Canvas Zoom/Pan:** Add mousewheel zoom and drag-pan controls to the spatial canvas.
  - **Validation:** Add client-side floating-point validation to prevent malformed coordinate submissions.

---

### Point 9: Live Real-Data Training Streams (Harvester) (`live_data_harvesters`)
- **Component Path:** `00_core_infrastructure/self_healing_hub/frontend/src/LiveTrainingDataHarvesterView.jsx`
- **Visual Layout:**
  - Top stream metrics banner: Total Records Count, Total Size MB, Active Harvesting Rate, and 100% Empirical Truth Badge.
  - 4 Stream Overview Cards (Movesense ECG/IMU, Shopify Storefront, Git AST, 5-Layer Mesh Telemetry).
  - Filter tabs: `'all'`, `'biometrics'`, `'commerce'`, `'ast'`, `'mesh'`.
  - Ingested ShareGPT JSON sample preview card with syntax highlighting.
  - "Trigger Live Harvest" action button.
- **Data Flow & State:**
  - `metrics` ({ datasets, total_records, active_rate }), `isRefreshing`, `triggerStatus`, `activeDatasetTab`.
- **Backend Endpoints:**
  - `GET /api/lora/live_harvesting_metrics` (Polled every 3s).
- **Dynamic Human Interaction Protocol:**
  1. Click dataset filter tabs (`all`, `biometrics`, `commerce`, `ast`, `mesh`) to isolate specific data pipelines.
  2. Click "📡 Ingest & Harvest Live Streams Now" button, observe spinner and success confirmation.
  3. Click on individual sample records to expand formatted JSON payload and inspect Chain-of-Thought reasoning traces.
  4. Verify byte counters and record numbers increment dynamically as background daemons produce data.
- **Rule #0 Data Authenticity Verification:**
  - Inspect on-disk dataset files `lora_datasets/` and `session_logs/` to prove records originate from real Movesense Bluetooth GATT notifications and Git commit trees.
- **Architectural / UI Change Justification:**
  - **Search Bar:** Add real-time text search filter across ingested training samples.
  - **Export Action:** Add 1-click "Download Verified JSONL Slice" button for offline model training.

---

### Point 10: Grappling Vision, NPU (1.2W) & Token Gating (`grappling_vision`)
- **Component Path:** `00_core_infrastructure/self_healing_hub/frontend/src/GrapplingVisionBiometricsView.jsx`
- **Visual Layout:**
  - Header with NPU-First badge (1.2W consumption vs 85W Cloud GPU) and live power telemetry.
  - Sub-tabs: `'radar'`, `'hardware'`, `'shopify'`.
  - Safety Radar card (Armbar hyperextension, Kimura rotational risk, Joint Torque Nm, EKF occlusion state).
  - Hardware NPU/VRAM utilization metrics.
  - Shopify Token-Gated Membership verification form ($0 Free, $19/mo Pro, Lifetime Crowdsourced Compute).
- **Data Flow & State:**
  - `hardwareStatus`, `fusionData`, `isLiveActive`, `shopifyEmail`, `membershipStatus`, `isCheckingMembership`.
- **Backend Endpoints:**
  - `GET /api/hardware/npu_vram_status` (Polled every 2.5s)
  - `GET /api/grappling/fusion_stream` (Polled every 2.5s)
  - `POST /api/shopify/validate_membership`
- **Dynamic Human Interaction Protocol:**
  1. Toggle live telemetry stream (`Live Active` / `Paused`).
  2. Switch between `'radar'`, `'hardware'`, `'shopify'` sub-tabs.
  3. In `'shopify'` tab, enter customer token / email, click "Verify Subscription Status", and observe membership tier unlock.
  4. In `'hardware'` tab, compare wattage, TOPS/Watt, and latency metrics across local NPU vs cloud GPU.
- **Rule #0 Data Authenticity Verification:**
  - Validate that NPU wattage (1.2W) and TOPS ratings originate from real Apple Silicon / Tensor G5 power rails and not simulated constants.
- **Architectural / UI Change Justification:**
  - **Bug Fix:** Fix `handleVerifyShopify` to send the controlled `shopifyEmail` state variable in request body instead of hardcoded `'sample_token_or_email'`.
  - **Kinematic Overlay:** Add visual 2D joint skeleton overlay over the 3D pose detection radar.

---

### Point 11: PySpark Mesh Control Center & Canonical Crons (:8750) (`pyspark_mesh_crons`)
- **Component Path:** `00_core_infrastructure/self_healing_hub/frontend/src/PySparkMeshControlCenterView.jsx`
- **Visual Layout:**
  - Top PySpark Engine Stats: Calculation duration (0.35ms), Pooled RAM (82.8 GB), Active VRAM (57.96 GB), Memory Ceiling Governor (75.0% inviolable safety cap), System ROI score (9.88), RDD Partitions synced (8).
  - 7-Device Physical Mesh Nodes grid with IP, hardware, AI RAM cap, power status, and RPC latency.
  - 10-Route Multi-WAN Accelerator breakdown table.
  - 18 ROI-Ranked Cron Automations table with search filter and domain badges.
  - Storage pools breakdown (Mac NVMe Vault, APFS Root, Linux 1TB NVMe).
- **Data Flow & State:**
  - `telemetry`, `isLoading`, `viewMode` ('native'|'iframe'), `selectedSubService` ('multiwan'|'ainet'|'training'), `cronFilter`.
- **Backend Endpoints:**
  - `GET /api/spark-metrics` with fallbacks to `:8750/api/spark-metrics` and `:8088/status`.
- **Dynamic Human Interaction Protocol:**
  1. Toggle View Mode between `'native'` (integrated dashboard) and `'iframe'` (direct connection to external ports).
  2. When in iframe mode, switch sub-service between `multiwan` (:5050), `ainet` (:8087), `training` (:8900).
  3. Filter the Cron Automations table by typing in the search bar (e.g. "LoRA", "Mesh", "Healer").
  4. Hover over Multi-WAN transport cards to verify live RTT latency and sharding roles.
- **Rule #0 Data Authenticity Verification:**
  - Verify that the 18 cron automations correspond to active systemd / launchd timer jobs and real disk pools mapped via SeaweedFS FUSE.
- **Architectural / UI Change Justification:**
  - **Parallel Fallback:** Replace serial 3-step HTTP fallback with `Promise.any` to eliminate loading freezes if port 8750 is down.
  - **Manual Cron Triggers:** Add 1-click "Run Now" buttons in the cron table rows to trigger individual crons on demand.

---

### Point 12: Tri-Orchestrator Live Chat & Swarm Action Room (`live_chat`)
- **Component Path:** `00_core_infrastructure/self_healing_hub/frontend/src/TriOrchestratorLiveChatView.jsx`
- **Visual Layout:**
  - Mode selector bar with interactive mode chips (`multi_beam`, `consensus`, `auto_moe`, `debate`, `cloud`, `local`, `edge`, `genetic`).
  - Multi-agent live message stream with avatar icons, role badges, timestamps, and syntax-highlighted code blocks.
  - Interactive Action Cards with 1-click "Execute Action" buttons embedded in agent replies.
  - Message input dock with auto-scroll lock toggle, character counter, and prompt dispatch button.
- **Data Flow & State:**
  - `messages`, `inputText`, `isSending`, `activeFilter`, `chatMode`, `autoScroll`, `toastMessage`.
- **Backend Endpoints:**
  - `GET /api/chat/messages` (Polled every 3s)
  - `POST /api/chat/send` (Send message to swarm)
  - `POST /api/chat/execute_action` (Execute embedded action)
- **Dynamic Human Interaction Protocol:**
  1. Switch chat mode (e.g. from `multi_beam` to `consensus` or `debate`).
  2. Filter messages by sender (`cloud`, `local`, `genetic`, `user`).
  3. Type message in input bar, click Send (or press Enter), observe optimistic UI bubble and multi-agent streaming replies.
  4. Click an embedded Action button (e.g. "Run Truth Audit") within an agent message and observe toast notification and status update.
  5. Toggle Auto-Scroll lock switch.
- **Rule #0 Data Authenticity Verification:**
  - Verify that chat messages are logged to `telemetry_chat_feed.jsonl` and actions dispatched to real system services.
- **Architectural / UI Change Justification:**
  - **Markdown Rendering:** Integrate markdown code syntax highlighter for agent code snippets.
  - **WebSocket Feed:** Replace 3s polling with WebSocket / SSE stream at `/api/chat/stream` to eliminate scroll jitter.

---

### Point 13: 3D Spatial Radar & DeepMind Genie 2 Hologram (`spatial_3d`)
- **Component Path:** `00_core_infrastructure/self_healing_hub/frontend/src/Spatial3DMapView.jsx`
- **Visual Layout:**
  - View mode switcher: Google Genie 2 (60FPS), 3D Mesh View, VLM Raycast Angle, Tracked Entities list.
  - In `'genie_world'`: 3D interactive physics and holographic environment with tatami mats, avatar entities, and camera controls (`Genie3DSpatialWorldView`).
  - In `'3d_hologram'`: SVG 3D Isometric projection displaying room bounds (6m x 4m), optical mesh laser beams, UWB spatial anchors, and physical node positions.
  - In `'entities_list'`: Breakdown of all tracked physical devices with 3D pose vectors `[x, y, z]`, velocity, and tracking confidence.
- **Data Flow & State:**
  - `spatialViewMode` ('genie_world'|'3d_hologram'|'vlm_raycast'|'entities_list'), `hoveredNode`, `selectedNode`, `hoveredBeam`.
  - Props: `spatialMap` (from `/api/spatial_3d_map`).
- **Backend Endpoints:**
  - `GET /api/spatial_3d_map`
  - `GET /api/spatial_dashboard_projection`
- **Dynamic Human Interaction Protocol:**
  1. Switch between view modes (`genie_world`, `3d_hologram`, `vlm_raycast`, `entities_list`).
  2. In `'3d_hologram'`, hover over optical laser beams to highlight sender/receiver nodes and beam latency.
  3. Click on device nodes in the spatial SVG to view coordinates and hardware status popup.
  4. In `'genie_world'`, use keyboard/mouse controls to orbit camera and inspect tatami arena.
- **Rule #0 Data Authenticity Verification:**
  - Verify that physical node coordinates correspond to actual UWB anchor readings and device IP topology on the local subnet (`192.168.8.x`).
- **Architectural / UI Change Justification:**
  - **Dynamic Projection Bounds:** Replace hardcoded multiplier projection (`x * 110`, `y * 70`) with normalized bounding-box projection based on dynamic `room_dimensions_meters`.
  - **Orbit Controls:** Add Three.js OrbitControls for full 360-degree rotation.

---

### Point 14: 24/7 NPU Acceleration & Multi-Stream LoRA Training Hub (`ai_training`)
- **Component Path:** `00_core_infrastructure/self_healing_hub/frontend/src/AITrainingHub.jsx`
- **Visual Layout:**
  - Header Hero with NPU Cluster status (121.0 TOPS active) and "Trigger Live Distillation Step" button.
  - 4 Summary stat cards (Total Training Samples, Active Rate, Current LoRA Loss, Model Checkpoint Version).
  - 5 Nested Sub-Modules:
    1. AI Benchmark Leaderboard (`AIBenchmarkLeaderboard.jsx`)
    2. Swarm Arena Competitions (`SwarmArenaCompetitionView.jsx`)
    3. Sharded RPC Cluster Safety & VRAM Ceiling (`ShardedRPCClusterSafetyView.jsx`)
    4. Genetic PySpark Optimization Pipeline (`GeneticPySparkPipelineView.jsx`)
    5. MergeKit & Optuna Genetic Weight Merger (`MergeKitOptunaGeneticView.jsx`)
  - Live sample stream inspector with next/prev navigation buttons.
- **Data Flow & State:**
  - `trainingStatus`, `geneticMoeMetrics`, `npuStatus`, `dataStreams`, `sampleStream`, `activeSampleIndex`, `isSyncing`, `syncFeedback`.
- **Backend Endpoints:**
  - `GET /api/ai_training/status`
  - `GET /api/genetic_moe/live_metrics`
  - `GET /api/ai_training/npu_status`
  - `GET /api/ai_training/data_streams`
  - `GET /api/ai_training/sample_stream`
- **Dynamic Human Interaction Protocol:**
  1. Click "Trigger Live Distillation Step" button, verify status message updates and clears after 5s.
  2. Navigate sample streams using "Previous Sample" and "Next Sample" buttons to inspect harvested instruction-reasoning pairs.
  3. In `ShardedRPCClusterSafetyView`, adjust target capacity slider (60% to 90%) and verify dynamic RPC re-tuning.
  4. In `MergeKitOptunaGeneticView`, click "Run Trial" to simulate genetic MoE weight merging.
- **Rule #0 Data Authenticity Verification:**
  - Inspect `lora_dataset_task_*.jsonl` files in monorepo root to verify that sample pairs are harvested from real execution traces with genuine timestamps.
- **Architectural / UI Change Justification:**
  - **Real Backend Distillation:** Connect distillation trigger button to real backend endpoint `/api/pyspark/harvest_training_data` instead of simulated `setTimeout`.
  - **Loss Curve Visualization:** Add real-time SVG / Chart.js loss curve rendering training convergence.

---

## 6. Global UX & UI Requirements Matrix

### 6.1 Global UX Requirements (Mandatory >= 3)
1. **UX-1: Deep-Linked URL Routing & Tab State Persistence**
   - *Current Flaw:* Navigation in `App.jsx` is purely in-memory React state (`mainNavTab`). Reloading the browser resets the view to default, breaking multi-tasking and shareable links.
   - *Requirement:* Implement `window.location.hash` synchronization (e.g. `http://localhost:3000/#custom_voice_ide`), browser forward/back history support, and category-grouped navigation docks (Compute, Biometrics, Spatial, Tools).
2. **UX-2: Centralized WebSocket Event Fabric (TelemetryProvider)**
   - *Current Flaw:* 14 modular components poll port 5001 independently every 2-5 seconds via `fetch()`, flooding the local HTTP server with 20-30 requests/sec.
   - *Requirement:* Establish a single WebSocket connection (`/ws/telemetry_stream`) wrapped in a root `TelemetryProvider` context, distributing real-time device, ELO, and training telemetry via reactive pub/sub.
3. **UX-3: Unified Toast Notification & Error Boundary Architecture**
   - *Current Flaw:* Feedback across tabs uses inconsistent browser `alert()`, inline text banners, or unhandled errors. A single WebGPU shader crash can unmount the entire application.
   - *Requirement:* Implement a global Toast Notification manager (`react-hot-toast` or custom queue) and wrap each of the 14 modular tab views in a dedicated React `ErrorBoundary` with 1-click component recovery.

### 6.2 Global UI Requirements (Mandatory >= 3)
1. **UI-1: WCAG AAA Color Contrast & Semantic Design Token System**
   - *Current Flaw:* Dark background `#090d16` with low-contrast muted text `#64748b` and `#8b949e` in subheadings and table headers, failing 4.5:1 contrast ratios on standard monitors.
   - *Requirement:* Implement high-contrast design tokens (`#f8fafc` primary, `#cbd5e1` secondary, `#94a3b8` tertiary), ensure all interactive text meets minimum 4.5:1 contrast, and use standardized status colors (Emerald `#10b981`, Sky `#38bdf8`, Amber `#f59e0b`, Rose `#ef4444`).
2. **UI-2: Responsive Fluid Grid & Standardized Container Layouts**
   - *Current Flaw:* Hardcoded pixel heights (`height: calc(100vh - 100px)`) and fixed 3-column layouts cause overflow clipping and dual scrollbars on screens under 1440px width.
   - *Requirement:* Standardize card padding (`1.2rem`), glassmorphic backdrop blur (`backdrop-filter: blur(12px)`), and fluid CSS grid layouts (`grid-template-columns: repeat(auto-fit, minmax(320px, 1fr))`) across all 14 feature tabs.
3. **UI-3: Typographic Hierarchy & Tabular Number Formatting**
   - *Current Flaw:* Inconsistent font sizes ranging from unreadable 0.44rem (Sentinel HUD) to 2.2rem without clear typographic hierarchy, causing visual clutter.
   - *Requirement:* Enforce a strict 6-tier typographic scale (Micro 10px / 0.625rem, Small 12px / 0.75rem, Body 14px / 0.875rem, Subhead 16px / 1rem, Title 20px / 1.25rem, Display 28px / 1.75rem), eliminate sub-10px text, and apply `font-variant-numeric: tabular-nums` to all live numeric metrics.

---

## 7. Zero-Mock Telemetry & Verification Matrix

In strict compliance with Monorepo Rule #0 (Zero Mock Data):
- All hardware metrics (VRAM, CPU, RAM, TOPS, power, temperatures) must originate from real physical device queries via `00_core_infrastructure/self_healing_hub/src/api_server.py` and `device_registry.py`.
- Biometrics telemetry must originate from real Movesense GATT sensor broadcasts or empirical session logs in `session_logs/movesense_live.json`.
- ELO ratings and debate records must originate from genuine 4-turn state machine runs saved to `truth_audit_nomad_mesh_debate.jsonl`.
