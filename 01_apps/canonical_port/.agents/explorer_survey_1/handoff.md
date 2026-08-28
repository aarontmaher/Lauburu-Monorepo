# Canonical Port Competitive TUI Swarm Survey & Architectural Recommendation Report

**Date**: 2026-08-28  
**Author**: Explorer 1 (Competitive TUI Swarm Survey Specialist)  
**Target Monorepo**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port`  
**Working Directory**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/.agents/explorer_survey_1`  

---

## 1. Observation

A comprehensive inspection of `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/` and its `tui/`, `backend/`, and `tests/` subsystems was conducted. Below are the verified architectural facts, file paths, line numbers, and implementation mechanisms:

### 1.1 Application Entrypoint, Navigation & Stability Hierarchy
- **Entrypoint**: `tui/canonical_tui.py` (267 LOC) defines `CanonicalPortApp(App)` implementing the **9-Screen Stability Hierarchy** alongside `AllTabsGridScreen` (`0`/`a`) and `ArchitectureExplorerScreen` (`e`/`x`).
- **Screen Registry (`canonical_tui.py:80-92`)**:
  ```python
  SCREENS: Dict[str, Type[Screen]] = {
      "agi_terminal": AgiCodingTerminalScreen,      # Screen 1 / Hotkey 'c' or '1'
      "network": NetworkScreen,                     # Screen 2 / Hotkey 'n' or '2'
      "hardware": HardwareScreen,                   # Screen 3 / Hotkey 'h' or '3'
      "biometrics": BiometricsScreen,               # Screen 4 / Hotkey 'b' or '4'
      "ai_inference": AiInferenceScreen,            # Screen 5 / Hotkey 'i' or '5'
      "training": TrainingScreen,                   # Screen 6 / Hotkey 't' or '6'
      "governance": GovernanceScreen,               # Screen 7 / Hotkey 'g' or '7'
      "tooling": ToolingScreen,                     # Screen 8 / Hotkey 's' or '8'
      "optimization": OptimizationScreen,           # Screen 9 / Hotkey 'o' or '9'
      "all_tabs": AllTabsGridScreen,                # All Tabs / Hotkey '0' or 'a'
      "explorer": ArchitectureExplorerScreen,       # Architecture / Hotkey 'e' or 'x'
  }
  ```
- **Navigation Controls**:
  - `cycle_screen(delta, force)` (`canonical_tui.py:166-185`) enforces a 0.20s debounce throttle (`scroll_debounce_sec = 0.20`) to prevent mouse-wheel event flooding.
  - Number keys `1`–`9` and letter hotkeys `c`,`n`,`h`,`b`,`i`,`t`,`g`,`s`,`o`,`e`,`x`,`0`,`a` provide instant direct switching.
  - Pinned navigation bar widget `PinnedTabNavBar` (`tui/widgets/pinned_tab_nav_bar.py`, 380 LOC) is permanently docked across all screens, featuring dynamic responsive width adaptation (Full $\ge$138 cols, Compact 78–137 cols, Tiny 53–77 cols, Micro <53 cols).
  - Docked shortcuts legend widget `DockedShortcutsLegend` (`tui/widgets/docked_shortcuts_legend.py`, 266 LOC) is permanently docked at the bottom with 4 responsive tiers.
  - Visual Inference Engine Selector `EngineSelectorWidget` (`tui/widgets/engine_selector.py`, 173 LOC) is docked in top bars, bound to `[Ctrl+E]` / `[F2]` hotkeys for cycling inference engines (`auto`, `llama_rpc`, `exo`, `accelerate`, `petals`).

### 1.2 Textual CSS / TCSS Layout Structure & Responsiveness
- **Styling Separation**: Global CSS in `tui/canonical_tui.css` (46 LOC) and component-level `DEFAULT_CSS` in each view/widget maintain strict styling-logic separation (`#070b12`, `#0b111c`, `#1e293b`, `#00ffcc`, `#38bdf8`, `#e879f9`, `#4ade80`, `#facc15`, `#f43f5e`, `#a78bfa`).
- **Screen & View Decoupling**: Screens in `tui/screens/` wrap composable `Container`/`Vertical` views from `tui/views/` (`AgiCodingTerminalView`, `NetworkView`, `HardwareView`, `BiometricsView`, `AiInferenceView`, `TrainingView`, `GovernanceView`, `ToolingView`, `OptimizationView`, `OverviewView`, `ArchitectureExplorerView`).
- **Grid Layouts**: `tui/grid_screen.py` and `tui/screens/all_tabs_screen.py` implement a 3x3 `Grid` (`#all-tabs-grid` with `grid-size: 3 3; grid-columns: 1fr 1fr 1fr; grid-rows: 1fr 1fr 1fr; grid-gutter: 1`).
- **Split Containers**: `ArchitectureExplorerView` implements a dual-pane horizontal split (`#explorer-left-pane` at 48% width with Tree + Search + Chips + Markdown Detail; `#explorer-right-pane` at 52% width with Metrics HUD + ASCII Canvas).

### 1.3 Obsidian Architecture Explorer & Dual-Layout Graph Engine
- **Vault Parser (`tui/services/obsidian_vault_parser.py`, 408 LOC)**:
  - Crawls `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault` (over 320 markdown files).
  - Extracts YAML frontmatter with a robust regex fallback for malformed headers (`extract_frontmatter`, lines 233–260).
  - Resolves standard Obsidian Wikilinks `[[target|alias#anchor]]` into directed bidirectional dependencies (`in_links`, `out_links`, `in_degree`, `out_degree`).
  - Classifies nodes deterministically into 9 canonical categories (`Canonical Module`, `Infrastructure`, `AI & Inference`, `Biometrics & DSP`, `Data & Memory`, `Swarm & Governance`, `Tooling & Scripts`, `Architecture & Docs`, `Audit & Telemetry`).
  - Extracts architectural features and markdown section headings.
- **Graph Topology & Algorithms (`tui/models/architecture_graph.py`, 366 LOC)**:
  - In-memory directed graph `ArchitectureGraph` supporting node filtering, neighbor lookups, and graph density metrics.
  - Tarjan's Strongly Connected Components (SCC) algorithm (`find_sccs`, lines 233–281) for cycle isolation.
  - Sugiyama topological stratification with barycentric crossing reduction (`get_stratified_layers`, lines 297–357).
- **ASCII/ANSI Renderer (`tui/services/ascii_graph_renderer.py`, 257 LOC)**:
  - Renders stratified layers with Unicode box-drawing connectors (`╭─╮`, `──▶`, `├──┴──▶`, `╰──▶`), category color badges, in/out degrees, and `★ SELECTED` highlight tags.
  - Annotates strongly connected cycles (`↺ STRONGLY CONNECTED CYCLES`).
- **Interactive Dual View (`tui/views/architecture_explorer_view.py`, 450 LOC)**:
  - Left Pane: Real-time search `Input` (`/` to focus), 10 category chip toggle `Button`s (`[All]`, `[Modules]`, `[Infra]`, `[AI]`, `[Biometrics]`, `[Data]`, `[Governance]`, `[Tooling]`, `[Docs]`, `[Audit]`), interactive `Tree[str]` widget with link sub-branches, and scrollable `Markdown` feature detail pane.
  - Right Pane: Top Metrics HUD Table and scrollable `Static` ASCII canvas.
  - Real-time synchronization: Node selection in Tree updates Markdown detail and highlights node in ASCII canvas; filtering query or category chip updates Tree, ASCII canvas, and HUD simultaneously.

### 1.4 Inference Router & Infrastructure Integration
- **Inference Router (`tui/services/inference_router.py`, 507 LOC)**:
  - Central coordinator managing `auto`, `llama_rpc` (:50052 & :8081–:8085), `exo` (:52415), `accelerate` (MPS/DDP), `petals` (:31330/:31337), `gemini`, `cloudflare`, and `julien` bridges.
  - Dynamic latency auto-routing (`DynamicLatencyPoller`) with sub-1ms stream cancellation on engine swap or speech barge-in.
- **Daemon Supervisor & Bootstrapper**:
  - `backend/agents/crons/daemon_supervisor.py` (136 LOC) monitors OS daemons (`openclaw`, `docker`, `llama.cpp`, `exo`, `accelerate`, `petals`, `cloudflared`, `tailscale`, `seaweedfs`, `movesense`) and automatically heals exited/unhealthy Docker containers.
  - `boot_canonical_mesh.sh` (45 LOC) orchestrates a 3-pane Tmux session (Backend Port 4000, Movesense BLE bridge, and Textual TUI).

---

## 2. Logic Chain

From the observations above, the following analytical conclusions and design implications emerge:

```
[Observation 1: Comprehensive Backend & Services]
(Blackboard Store, Multi-Engine Inference Router, S2S Voice IO, Obsidian Parser, Daemon Supervisor)
                              │
                              ▼
[Inference 1: Core Functionality is Decoupled & Highly Modular]
(All business logic, data models, and network adapters exist as standalone Python services)
                              │
                              ▼
[Observation 2: Existing TUI is General-Purpose & Tab-Heavy]
(Screen 1 bundles Shell+Voice+Tree+Trace; Screens 2-9 are siloed in individual views; AllTabs is 3x3)
                              │
                              ▼
[Inference 2: Opportunity for 3 Purpose-Built Competitive TUI Paradigms]
(Different user personas require distinct information densities, interaction models, and screen allocations)
                              │
                              ▼
┌─────────────────────────────┼─────────────────────────────┐
▼                             ▼                             ▼
[Track 1: TUI-Alpha]          [Track 2: TUI-Beta]           [Track 3: TUI-Gamma]
"NOC & Telemetry Dashboard"   "Swarm IDE & Chat Shell"      "Architecture & Graph Explorer"
High-density multi-node       Interactive REPL + Chat,      Expansive ASCII canvas +
telemetry cockpit, alerts,    multi-engine token streams,   Tree + 320-note Obsidian
live 512Hz ECG, Docker NOC.   debate arena, voice coding.   graph + AST dependency trees.
```

---

## 3. Comprehensive Evaluation of Existing Layout

### 3.1 Strengths
1. **Rule #0 Zero-Mock Integrity**: Direct binding to authentic hardware probes, blackboard snapshots, and network sockets; no synthetic random arrays.
2. **Thread Safety & Non-Blocking Event Loop**: Background worker threads (`@work(thread=True)`) and asynchronous periodic refreshes (`set_interval(1.5, ...)`) guarantee zero UI lockups during network latency or heavy computation.
3. **High Architectural Extensibility**: View/Screen decoupling allows any view (`views/`) to be mounted either as a dedicated full screen or as a component inside multi-view grids.
4. **Resilient Graph Algorithms**: Tarjan's SCC cycle isolation and Sugiyama layering prevent infinite loops and layout corruption when rendering cyclic Obsidian note dependencies.
5. **Multi-Engine Inference Routing**: Seamless hotkey-driven engine switching (`[Ctrl+E]` / `[F2]`) and dynamic auto-routing across local RPC, decentralized DHT, and cloud gateway backends.

### 3.2 Weaknesses & Bottlenecks
1. **Screen 1 Information Fragmentation**: `AgiCodingTerminalScreen` attempts to house the code editor, REPL output, voice telemetry, AST file tree, and execution traces within 4 tab panes, forcing operators to switch tabs rather than seeing correlated telemetry in parallel.
2. **All-Tabs 3x3 Viewport Constraints**: The 3x3 grid in `AllTabsGridScreen` divides standard 80–120 column terminals into narrow 25–38 column cells, causing text clipping and metric truncation across the 9 mounted views.
3. **Architecture Explorer Pane Ratio Constraints**: The 48%/52% horizontal split in `ArchitectureExplorerView` restricts the ASCII topology canvas width, requiring horizontal scrolling on large graphs with $>10$ nodes per layer.

---

## 4. Competitive TUI Swarm Specifications (3 Distinct Tracks)

To fulfill Requirement R2 of `ORIGINAL_REQUEST.md`, we specify three distinct, runnable competitive TUI paradigms:

### Track 1: TUI-Alpha — "Telemetry & Mesh NOC Dashboard" (Dashboard-Heavy)
- **Target Persona**: Systems Reliability Engineers, Mesh Network Operators, Biometrics Monitors.
- **Layout Architecture**:
  - **Top Bar (3 lines)**: Master 7-Node Hardware Health Pill Matrix (L1–L7 + GW), Pooled RAM/VRAM Meter (`108.0 GB / 82.8 GB`), Active Ingress WAN Interface, and System Uptime.
  - **Main Grid (Bento Box Layout / 3 Columns)**:
    - **Col 1 (30% width)**: 7-Layer Node Telemetry Cards (CPU load, thermals, VRAM caps, TB4 DMA 0.277ms RTT link status).
    - **Col 2 (45% width - Center)**: Live Biometrics & DSP Center (512Hz ECG waveform simulation/stream, Kamath 20% RR filter status, DFA-alpha1 Zone 2 gauge, PTT Blood Pressure, IMU kinematics).
    - **Col 3 (25% width - Right)**: Docker & Daemon Supervisor HUD (Container health states, auto-restart counters, Port 18802 Self-Healing status, Tailscale DERP relays).
  - **Bottom Dock (4 lines)**: Live Alarm & Telemetry Event Ticker + 1-Click Action Buttons (`[Restart Daemons]`, `[Probe TB4]`, `[Calibrate ECG]`, `[Purge RAM]`).
- **Key Differentiator**: Maximum situational awareness with zero tab-switching required to monitor all 7 physical mesh layers simultaneously.

### Track 2: TUI-Beta — "Multi-Engine Swarm IDE & Chat Shell" (Chat/Inference-Heavy)
- **Target Persona**: Autonomous AI Engineers, Prompt Architects, Multi-Model Debate Judges.
- **Layout Architecture**:
  - **Top Bar (2 lines)**: Dynamic Engine Selector (`auto`, `llama_rpc`, `exo`, `accelerate`, `petals`, `gemini`, `cloudflare`, `julien`) with real-time TTFT and tok/s metrics.
  - **Split Workspace (65% / 35%)**:
    - **Left Main Pane (65% width)**:
      - Upper (60%): Interactive Multi-Agent Chat & REPL Stream with color-coded agent badges (`[Kimi 88B]`, `[Qwen 38B]`, `[Llama 70B]`, `[Gemini Flash]`) and markdown syntax rendering.
      - Lower (40%): Active Code Buffer & Diff Inspector with line numbers and 1-click execution.
    - **Right Sidebar (35% width)**:
      - Panel 1: Live Tri-Orchestrator Debate Consensus Gauge (Cosine accord meter, current turn, tie-breaker code-off status).
      - Panel 2: S2S Voice Coding & Transcription HUD (16kHz VAD status, live transcription buffer, TTS playback pill).
      - Panel 3: Multi-Engine Latency Matrix (TTFT comparison table across all 7 backends).
  - **Bottom Bar**: Interactive Prompt / Command Input Bar (`/audit`, `/duel`, `/split`, `/engine`, `/model`) with command history.
- **Key Differentiator**: Streamlines agent code generation, multi-model debate deliberation, and voice-assisted programming.

### Track 3: TUI-Gamma — "Obsidian Topology & Knowledge Explorer" (Graph/Architecture-Heavy)
- **Target Persona**: Enterprise System Architects, Security Auditors, Monorepo Code Reviewers.
- **Layout Architecture**:
  - **Collapsible Left Sidebar (25% width)**:
    - Search input (`/` to focus) with live fuzzy substring matching.
    - 10 Quick-Filter Category Chips (`[All]`, `[Modules]`, `[Infra]`, `[AI]`, `[Biometrics]`, `[Data]`, `[Governance]`, `[Tooling]`, `[Docs]`, `[Audit]`).
    - Hierarchical Obsidian Knowledge Tree with expand/collapse and dependency link counts.
  - **Center Canvas (55% width - Primary Focus)**:
    - Expansive ASCII/ANSI Directed Topology Canvas rendered via Sugiyama layered layout.
    - Tarjan SCC cycle component badges (`↺ SCC`) and bidirectional dependency flow vectors.
    - Zoom / Depth selector (`Depth: 1 / 2 / 3 / All`) and Layer isolation toggles.
  - **Right Inspector Pane (20% width)**:
    - Markdown Architecture Document Inspector (Frontmatter, tags, backlinks, features, subsystem specifications).
    - Code AST Metrics Card (PySpark LOC count, AST file counts, language breakdowns).
  - **Bottom Dock**: Graph Metrics HUD (Total nodes, total edges, graph density, dangling link count, average degree).
- **Key Differentiator**: Unlocks expansive visual real estate for deep monorepo dependency analysis and architectural auditing.

---

## 5. Caveats

1. **Terminal Viewport Constraints**: Terminal windows narrower than 80 columns will experience severe text wrapping on 3-column dashboard layouts (TUI-Alpha); responsive degradation rules must collapse columns on small viewports.
2. **Real vs. Standby Hardware Probes**: When physical mesh nodes (e.g. Linux Tablet L4 or Samsung S20 L7) or Movesense BLE sensors are powered off or disconnected, the TUIs must display clean standby/waiting indicators (`--` or `[dim]STANDBY[/dim]`) in compliance with Rule #0.
3. **No Source Code Modifications**: As an Explorer agent, this survey report is strictly read-only and introduces zero direct code modifications into the source tree.

---

## 6. Conclusion & Recommendation

1. **Existing Base Quality**: The existing Canonical Port TUI has a world-class foundation with strong architecture models (`architecture_graph.py`), robust parsers (`obsidian_vault_parser.py`), multi-engine routing (`inference_router.py`), and decoupled views (`views/`).
2. **Tri-Track Competitive Strategy**: The swarm should proceed to implement prototype variations for **TUI-Alpha (Dashboard-Heavy)**, **TUI-Beta (Chat/Inference-Heavy)**, and **TUI-Gamma (Graph/Architecture-Heavy)** as distinct screen configurations or standalone runnable profiles under `tui/prototypes/` or `tui/screens/`.
3. **Evaluation Protocol**: The `ai-debate` Tri-Orchestrator council can rigorously evaluate and benchmark each variation across:
   - **Throughput & Responsiveness** (frame rate, render latency under 100+ telemetry events/sec).
   - **Information Density & UX Ergonomics** (clarity of data presentation, minimal keystrokes).
   - **Fault Tolerance & Resilience** (graceful degradation when daemons/engines drop).

---

## 7. Verification Method

To independently verify all findings and test suites mentioned in this report:

```bash
# 1. Run Obsidian Parser Unit Tests
uv run pytest tests/unit/test_obsidian_parser.py -v

# 2. Run ASCII Graph Renderer Unit Tests
uv run pytest tests/unit/test_ascii_graph_renderer.py -v

# 3. Run E2E Architecture Explorer Textual Pilot Tests
uv run pytest tests/e2e/test_explorer_view.py -v

# 4. Run Pinned Tab Navigation & Engine Selector Pilot Tests
uv run pytest tests/e2e/test_pinned_tab_navigation.py tests/e2e/test_engine_selector.py -v

# 5. Run Full 4-Tier Test Suite
uv run pytest tests/e2e/test_explorer_4tier_suite.py -v

# 6. Launch Canonical TUI App directly
uv run textual run tui/canonical_tui.py
```

### Invalidation Conditions
- If `tests/e2e/test_explorer_view.py` or `tests/unit/test_obsidian_parser.py` fail, frontmatter extraction or pilot layout mounting has broken.
- If `canonical_tui.py` fails to switch screens on hotkeys `1`..`9` or `e`/`x`, the screen binding table in `canonical_tui.py:106-140` has been corrupted.
