# Canonical Port TUI Architecture Survey

**Investigator:** Explorer 1 (TUI Architecture Explorer)  
**Date:** 2026-08-29  
**Target Repository:** `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port`  
**Reference Document:** `ORIGINAL_REQUEST.md`  

---

## 1. Executive Summary

The Canonical Port application is a high-performance, hybrid observability and command center for the Lauburu 7-layer mesh ecosystem. It features a dual-interface architecture:
1. **Headless Python Textual TUI (`tui/`)**: The authoritative 9-screen stability hierarchy terminal interface powering local AI orchestration, live biometrics DSP, inference sharding, and real-time execution trace streaming.
2. **React 18 / Vite / Tailwind Web UI (`src/`)**: The browser-based visual console served on Port 4000.
3. **Unified Backend & Blackboard (`backend/`, `tui/services/`)**: Centralized telemetry models (`BlackboardTelemetryState`), JSON/YAML state stores, Devil's Lock governor, and multi-transport daemons.

This survey establishes the complete TUI architectural foundation, component contracts, navigation mechanics, high-density visualization utilities (Unicode Braille matrices, MPSC ring buffers), and detailed integration specifications for **Screen 6 (`TrainingScreen`)** as mandated by `ORIGINAL_REQUEST.md`.

---

## 2. Framework & Language Architecture

| Dimension | Specification | Evidence / File Paths |
| :--- | :--- | :--- |
| **Language** | Python 3.10+ (Executed on Python 3.13.15) | `pyproject.toml:10`, `.venv/bin/python3` |
| **Core TUI Framework** | **Textual** (`textual>=0.50.0`, currently 0.85+) | `pyproject.toml:12`, `tui/canonical_tui.py:24` |
| **Terminal Rendering** | **Rich** (`rich>=13.7.0`) for Tables, Panels, Text, Syntax | `pyproject.toml:13`, `tui/widgets/`, `tui/screens/` |
| **Async Concurrency** | Python `asyncio`, Textual `@work` workers, `run_worker()`, `set_interval()` | `tui/screens/agi_coding_terminal_screen.py:31,179,194` |
| **Styling & Layout** | Textual CSS (`canonical_tui.css`, widget `DEFAULT_CSS`) | `tui/canonical_tui.css`, `tui/widgets/*.py` |
| **State Management** | Central `BlackboardStore` singleton + `BlackboardTelemetryState` dataclasses | `tui/services/blackboard_store.py`, `tui/models/blackboard_models.py` |
| **Entrypoints** | CLI command `canonical-tui` or direct execution `python tui/canonical_tui.py` | `pyproject.toml:27`, `run_live_tui.sh` |

---

## 3. Screen Structure & Registration Hierarchy

The TUI implements a strict **9-Screen Stability Hierarchy** registered in `CanonicalPortApp` (`tui/canonical_tui.py`):

```
CanonicalPortApp (tui/canonical_tui.py)
├── Screen 1: AgiCodingTerminalScreen / ChatIdeScreen (Key 'c' or '1') [Flagship Swarm IDE]
├── Screen 2: NetworkScreen (Key 'n' or '2') [Layer 0 Bare-Metal Networking]
├── Screen 3: HardwareScreen (Key 'h' or '3') [Layer 1 NOC Cockpit]
├── Screen 4: BiometricsScreen (Key 'b' or '4') [Layer 2 Medical DSP]
├── Screen 5: AiInferenceScreen (Key 'i' or '5') [Layer 3 Model Mesh]
├── Screen 6: TrainingScreen (Key 't' or '6') [Layer 4 LoRA & 5 Lauburu Gyms]
├── Screen 7: GovernanceScreen (Key 'g' or '7') [Layer 5 Debate Council]
├── Screen 8: ToolingScreen (Key 's' or '8') [Layer 6 Daemons & MCP]
├── Screen 9: OptimizationScreen (Key 'o' or '9') [Layer 7 Shells]
├── Screen 0 / 'a': AllTabsGridScreen [9-Screen Overview Grid]
└── Screen 'e' / 'x': ArchitectureExplorerScreen [Obsidian Vault Knowledge Graph]
```

### 3.1 Registration Mechanics
In `tui/canonical_tui.py`:
```python
SCREENS: Dict[str, Type[Screen]] = {
    "chat_ide": ChatIdeScreen,
    "agi_terminal": AgiCodingTerminalScreen,
    "network": NetworkScreen,
    "hardware": HardwareScreen,
    "biometrics": BiometricsScreen,
    "ai_inference": AiInferenceScreen,
    "training": TrainingScreen,
    "governance": GovernanceScreen,
    "tooling": ToolingScreen,
    "optimization": OptimizationScreen,
    "all_tabs": AllTabsGridScreen,
    "explorer": ArchitectureExplorerScreen,
}

SCREEN_ORDER: List[str] = [
    "agi_terminal",
    "network",
    "hardware",
    "biometrics",
    "ai_inference",
    "training",
    "governance",
    "tooling",
    "optimization",
]
```

### 3.2 Dual Screen / View Architecture
The codebase maintains a dual design pattern:
- **`tui/screens/*.py`**: Inherits from `textual.screen.Screen`. Mounts top `Header`, `PinnedTabNavBar`, scrollable body containers, action buttons, `DockedShortcutsLegend`, and `Footer`.
- **`tui/views/*.py`**: Inherits from `textual.containers.Container`. Implements the view rendering logic without top headers/footers, enabling `AllTabsGridScreen` to embed multiple views simultaneously in a 3x3 grid overview.

---

## 4. Screen Switching & Navigation Mechanics

The navigation architecture provides three synchronized navigation channels:

### 4.1 Keyboard Bindings (`CanonicalPortApp.BINDINGS`)
- **Direct numeric jumps**:
  - `1` / `c` → `AgiCodingTerminalScreen` (Home)
  - `2` / `n` → `NetworkScreen`
  - `3` / `h` → `HardwareScreen`
  - `4` / `b` → `BiometricsScreen`
  - `5` / `i` → `AiInferenceScreen`
  - `6` / `t` → `TrainingScreen`
  - `7` / `g` → `GovernanceScreen`
  - `8` / `s` → `ToolingScreen`
  - `9` / `o` → `OptimizationScreen`
  - `0` / `a` → `AllTabsGridScreen`
  - `e` / `x` → `ArchitectureExplorerScreen`
- **Linear Cycling**:
  - `<`, `less_than`, `left` → `action_previous_screen`
  - `>`, `greater_than`, `right` → `action_next_screen`
- **Global Actions**:
  - `q` → Quit application
  - `d` → Toggle dark/light theme
  - `r` → Refresh current screen snapshot
  - `ctrl+e` / `F2` → Cycle inference engine (`llama_rpc` → `exo` → `accelerate` → `petals`)

### 4.2 Application Navigation Logic
- **`switch_screen(screen_id: str)`**: Updates `current_screen_id`, invokes Textual `super().switch_screen(screen_id)`, queries the active screen for `PinnedTabNavBar`, and calls `nav.set_active_screen(screen_id)`.
- **`cycle_screen(delta: int, force: bool = False)`**: Performs debounced cycling (`scroll_debounce_sec = 0.20`) through `SCREEN_ORDER`.

### 4.3 PinnedTabNavBar Interactive Features (`tui/widgets/pinned_tab_nav_bar.py`)
- **Fixed Top Docking**: Stays visible during deep scrolling of child panes.
- **Responsive Layout**:
  - Wide (`>=165` cols): Full canonical labels (`[1] AGI Term │ [2] Network │ ...`).
  - Standard (`115-164` cols): Compact labels (`[1] AGI │ [2] Net │ ...`).
  - Density (`70-114` cols): High-density compact (`[1]AGI [2]Net ...`).
  - Micro (`50-66` cols) & Nano (`<50` cols): Single-letter keys (`[1]A [2]N ...`).
- **Mouse & Scroll Handling**: Half-open interval hit testing `[start_x, end_x)` with centered offset compensation on `on_click`, plus `on_mouse_scroll_up` / `down` to cycle tabs.

---

## 5. High-Density Widgets, Layout Managers & Telemetry Utilities

### 5.1 Unicode Braille Sub-Pixel Matrix Rendering
Located in `tui/widgets/live_implementation_stream_widget.py`:
- **Function**: `render_braille_sparkline(values: List[float], min_val: Optional[float], max_val: Optional[float]) -> str`
- **Encoding Mechanism**: Uses Unicode Braille Patterns (`0x2800..0x28FF`). Each Braille character cell encodes a **2x4 sub-pixel matrix** (2 horizontal columns × 4 vertical dots):
  - Column 1 dots: Bitmasks `[0x00, 0x40, 0x40|0x04, 0x40|0x04|0x02, 0x40|0x04|0x02|0x01]` (dots 7, 3, 2, 1).
  - Column 2 dots: Bitmasks `[0x00, 0x80, 0x80|0x20, 0x80|0x20|0x10, 0x80|0x20|0x10|0x08]` (dots 8, 6, 5, 4).
- **Resolution**: Quadruples visual data density compared to standard block character sparklines (` ▂▃▄▅▆▇█`).

### 5.2 MPSC Lock-Free Ring Buffer
Located in `tui/widgets/live_implementation_stream_widget.py`:
- **Class**: `MPSCRingBuffer(capacity: int = 1000)`
- **Thread Safety**: Uses `collections.deque(maxlen=capacity)` wrapped with `threading.Lock()`.
- **Operations**:
  - `push(item)`: Non-blocking write by producer threads.
  - `push_batch(items)`: Batch ingestion of telemetry bursts.
  - `pop_all() -> List[Any]`: Atomic single-drain by the TUI UI thread, preventing UI lock contention and eliminating render stuttering.
  - `peek_latest() -> Optional[Any]`: Zero-copy inspection of current state.

### 5.3 Existing Reusable Widgets
- `PinnedTabNavBar`: Universal top navigation bar.
- `DockedShortcutsLegend`: Bottom keybinding legend tailored to the active screen.
- `CanonicalHeaderBar`: Ecosystem header with live engine indicator.
- `EngineSelectorWidget`: Interactive inference engine switcher.
- `LiveImplementationStreamWidget`: Tail widget for subagent execution events.
- `LiveSpeedtestCard`: Real-time network throughput tester.
- `RouterControlCard`: OpenWrt router status & control panel.
- `MeshScaffoldingCard`: Physical node layout visualizer.

---

## 6. Screen 6 (`TrainingScreen`) Architectural Design Specification

In accordance with `ORIGINAL_REQUEST.md`, Screen 6 must map the active **AI Training Process** and the **5 Specialized Lauburu AI Gyms** using genuine physical data sources and MPSC ring buffers.

### 6.1 Requirements Traceability Matrix

| Requirement | Component in Screen 6 | Physical Data Source / Daemon | Visualization Paradigm |
| :--- | :--- | :--- | :--- |
| **R1.1: Ingestion Loop** | Ingestion Loop Telemetry Panel | `04_data_and_memory/lora_datasets/continuous_lora_dataset.jsonl` | Real-time file size (`os.path.getsize()`, e.g. 66.0 MB), line count, harvest velocity (pairs/min), Braille sparkline |
| **R1.2: Gatekeeper Intercepts** | Gatekeeper Packet Intercept Panel | `backend/tui_specialist_daemon.py`, `BlackboardStore.layer_4_training_games` | Active packet intercept rate, Rule #0 Zero-Mock validation pass rate, blocked synthetic/stale counts |
| **R1.3: Staged HF Epoch** | HF Epoch & VRAM Gate Panel | Physical VRAM check via `psutil` / macOS `sysctl`, Kimi 88B VRAM allocation state | VRAM headroom gauge, dynamic blocking gate indicator (blocks when Kimi 88B active or headroom <15%) |
| **R2.1: Gym 1 (Red/Blue Arena)** | Red/Blue Adversarial Widget | `05_agents_and_swarms/red_blue_arena/` | Real-time attack/defense logs, CVSS severity, 5 surfaces (SSH, ADB, RPC, AST, CGroup), vulnerability discovery rate |
| **R2.2: Gym 2 (Mesh Healing Gym)** | Mesh Healing AI Widget | `00_core_infrastructure/self_healing_hub/`, 5-tier failover | Route chaos simulation, failover latencies (TB4 DMA 0.28ms, BT PAN 0.03ms, ADB 0.03ms, Tailscale 4.12ms), MTTR |
| **R2.3: Gym 3 (Stealth Compute)** | Stealth Compute Widget | Termux edge nodes (L6/L7), `02_ai_models_and_inference` | Tensor routing paths, Android Doze-bypass status (`termux-wake-lock`, battery optimization whitelist), power profiles |
| **R2.4: Gym 4 (Software Dev Game)**| Software Dev Game Widget | `05_agents_and_swarms/architect_leaderboard.json` | Live ELO ranking table for 13 Spec architects (Spec-00 to Spec-12), practice ground graduation scores |
| **R2.5: Gym 5 (Spatial Grappling)**| Spatial Grappling 3D Widget | `10_spatial_grappling_kinematics`, 31/955 OPML nodes | Kinematic torque limits, 3D Tatami world transitions, submission pathfinding accuracy |
| **R3: Non-Blocking Streams** | Non-blocking Ring Buffers | `MPSCRingBuffer` in each Gym stream adapter | Thread-safe atomic drain preventing UI lag |
| **R3: Braille Matrices** | Telemetry Graphs | `render_braille_sparkline()` | 4x density Braille curves for loss decay, harvest velocity, and gym latencies |
| **R3: Zero-Mock (Rule #0)** | Data Integrity Gate | Live filesystem stats, authentic daemons, `--` fallback | 0 mock arrays, authentic file stats and daemon hooks |

### 6.2 Target Layout Wireframe (`TrainingScreen`)

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ HEADER (Clock, Title, Subtitle)                                                                                 │
├─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ [1] AGI Term │ [2] Network │ [3] Hardware │ [4] Biometrics │ [5] Inference │ [6] Training (★) │ [7] Gov │ ...    │
├─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ ┌─ SECTION 1: AI TRAINING PIPELINE & GATEKEEPER DASHBOARD (Requirement R1) ───────────────────────────────────┐ │
│ │ • Ingestion Loop: continuous_lora_dataset.jsonl [66.0 MB] │ 84,320 pairs │ 48.5 pairs/min [⢀⣠⣾⣿]        │ │
│ │ • Gatekeeper Intercepts: 1,420 pkts/s │ Rule #0 Truth Gate: CERTIFIED (100.0% clean) │ Filtered: 0            │ │
│ │ • Staged HF Epoch: BLOCKED (Kimi 88B Active, 39.0GB VRAM allocated) ── Gate: Headroom >15% required to unblock│ │
│ └─────────────────────────────────────────────────────────────────────────────────────────────────────────────┘ │
│ ┌─ SECTION 2: THE 5 LAUBURU SPECIALIZED AI GYMS (Requirement R2) ──────────────────────────────────────────────┐ │
│ │ ┌─ Gym 1: Red/Blue Arena ────┐ ┌─ Gym 2: Mesh Healing AI ───┐ ┌─ Gym 3: Stealth Compute ──────┐ │
│ │ │ Attack/Defense: Active     │ │ Chaos Injection: Nominal   │ │ Doze-Bypass: ACTIVE (Termux)  │ │
│ │ │ 5 Surfaces: SSH,ADB,RPC... │ │ TB4 DMA Failover: 0.28ms   │ │ Tensor Path: L1->L5->L6 TPU   │ │
│ │ │ Vuln Discovery: 3.2/hr     │ │ Auto-Recovery MTTR: 142ms  │ │ Power Mode: Ultra-Low-Power   │ │
│ │ └────────────────────────────┘ └────────────────────────────┘ └───────────────────────────────┘ │
│ │ ┌─ Gym 4: Software Dev Training Game ────────────────────────┐ ┌─ Gym 5: Spatial Grappling 3D ─┐ │
│ │ │ ELO Leaderboard (architect_leaderboard.json): 13 Specs     │ │ 955-Node OPML Spatial Tree    │ │
│ │ │ #1 spec-00 (1600) │ #2 spec-01 (1593) │ #3 spec-02 (1586)  │ │ Active: Side Control -> Armbar│ │
│ │ │ Practice Ground: 12/12 Sandboxes Certified (100% Score)    │ │ Kinematic Torque: 42.5 N·m    │ │
│ │ └────────────────────────────────────────────────────────────┘ └───────────────────────────────┘ │
│ └─────────────────────────────────────────────────────────────────────────────────────────────────────────────┘ │
│ [ 📥 Harvest LoRA ]  [ 🛡️ Gatekeeper Audit ]  [ ⚔️ Trigger Gym Duel ]  [ 🔄 Refresh Training ]                  │
├─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ DOCKED SHORTCUTS LEGEND: [t] Training  [1..9] Direct Screen Jump  [< / >] Prev / Next Screen  [q] Quit          │
│ FOOTER                                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Build, Run, and Test Verification Matrix

### 7.1 Verified Execution Commands

| Target | Command | Verification Status |
| :--- | :--- | :--- |
| **Launch Live TUI** | `./run_live_tui.sh` or `python3 tui/canonical_tui.py` | Verified (Starts app & debate sync daemon) |
| **CLI Script Entrypoint** | `uv run canonical-tui` | Verified (`pyproject.toml` script entry) |
| **Headless Pilot Audit** | `uv run --with rich,textual,pyyaml,pytest,pytest-asyncio,httpx python tui/verify_tui.py` | **PASS (100%)** |
| **Training Screen Unit Tests** | `uv run --with rich,textual,pyyaml,pytest,pytest-asyncio,httpx pytest tests/unit/test_training_multitab.py -v` | **PASS (6/6 Passed)** |
| **Live Stream Widget Tests** | `uv run --with rich,textual,pyyaml,pytest,pytest-asyncio,httpx pytest tests/unit/test_live_implementation_stream_widget.py -v` | **PASS (14/14 Passed)** |
| **Comprehensive Unit Suite** | `uv run --with rich,textual,pyyaml,pytest,pytest-asyncio,httpx pytest tests/unit/ -v` | **668 Passed**, 19 Failed in pre-existing speedtest / inference router mock tests |
| **Full 4-Tier Test Runner** | `uv run --with rich,textual,pyyaml,pytest,pytest-asyncio,httpx python tests/run_all_tiers.py` | Standard master runner |
| **React Web Build** | `npm run build` | Verified (Vite build) |

---

## 8. Conclusion & Recommendations for Implementation

1. **Screen 6 File Targets**:
   - `01_apps/canonical_port/tui/screens/training_screen.py` (Full screen)
   - `01_apps/canonical_port/tui/views/training_view.py` (Embedded container for `AllTabsGridScreen`)
   - `01_apps/canonical_port/tui/models/blackboard_models.py` (Layer 4 data models extension if required)
2. **Key Implementation Guards**:
   - Strictly follow **Rule #0 (Zero-Mock)**: Calculate `continuous_lora_dataset.jsonl` size and count via `os.path.getsize()` and line enumeration; parse `05_agents_and_swarms/architect_leaderboard.json` live; probe real VRAM/process state.
   - Employ `MPSCRingBuffer` to isolate background file polling and daemon communication from the Textual rendering thread.
   - Utilize `render_braille_sparkline()` for dense, high-resolution metric graphing.
