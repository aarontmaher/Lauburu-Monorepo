# Project: Canonical Port TUI — Screen 6 (TrainingScreen & 5 AI Gyms)

## Architecture
The Canonical Port TUI is built on Python 3.10+ (running Python 3.13) with Textual (v0.85+) and Rich, following a 9-Screen Stability Hierarchy with matching embedded Views.

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                CANONICAL PORT TUI: SCREEN 6 (TRAINING)                                  │
├────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 1. AI TRAINING PIPELINE DASHBOARD                                                                      │
│    • Ingestion Loop Panel: Live continuous_lora_dataset.jsonl size (MB/bytes), lines, growth rate      │
│    • Gatekeeper Intercept Panel: Active packet intercepts, security logs, Devil's Lock governor state   │
│    • Staged HF Epoch Panel: Dynamic VRAM availability gate (Kimi 88B load detection, Blocked/Ready)    │
├────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 2. THE 5 LAUBURU AI GYMS INTERACTIVE WIDGETS                                                           │
│    • [1] Red/Blue Arena: Attack/Defense logs, resistance buffs, token heists, vulnerability discovery  │
│    • [2] Mesh Healing AI Gym: Route chaos injection, recovery latency, 5-tier failover status          │
│    • [3] AI Stealth Compute Arena: Tensor routing paths, silent thermal limits, Android Doze-bypass    │
│    • [4] Software Dev Training Game: Live architect_leaderboard.json ELO tracking, tournament ledgers  │
│    • [5] Spatial Grappling 3D: Kinematic torque (tau = 120*r*sin(theta)), 955-node OPML tree metrics  │
├────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 3. ARCHITECTURAL PARADIGMS & RULE #0 TRUTH ENGINE                                                      │
│    • MPSCRingBuffer: Bounded lock-free ring buffers for multi-producer asynchronous stream ingestion   │
│    • Braille Matrices: Unicode sub-pixel sparklines (U+2800..U+28FF) for high-density telemetry        │
│    • Zero-Mock Engine: psutil, os.stat, live JSON/JSONL reads, non-blocking socket probes, 0 fake data │
└────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| F1 | Ingestion Loop Telemetry | Real-time file stat and growth tracking of `continuous_lora_dataset.jsonl` without hardcoding | M1, M2 | ORIGINAL_REQUEST R1 |
| F2 | Gatekeeper Intercepts | Active packet intercepts, Devil's Lock governor, security audit logs | M1, M2 | ORIGINAL_REQUEST R1 |
| F3 | Staged HF Epoch VRAM Gate | Dynamic VRAM headroom check and Kimi 88B resident memory lock state (Blocked/Ready) | M1, M2 | ORIGINAL_REQUEST R1 |
| F4 | Red/Blue Arena Widget | Attack/defense logs, vulnerability discovery rate, resistance buffs, token heists | M1, M2 | ORIGINAL_REQUEST R2.1 |
| F5 | Mesh Healing AI Gym Widget | Route chaos injection, recovery latency, 5-tier failover status, WoL resurrection | M1, M2 | ORIGINAL_REQUEST R2.2 |
| F6 | AI Stealth Compute Widget | Sub-5ms foreground yield, silent thermals, tensor routes, Android Doze whitelist | M1, M2 | ORIGINAL_REQUEST R2.3 |
| F7 | Software Dev Game Widget | Live `architect_leaderboard.json` ELO tracking, 13 subsystem architects, shadow ledgers | M1, M2 | ORIGINAL_REQUEST R2.4 |
| F8 | Spatial Grappling 3D Widget | Kinematic torque calculation, 955-node OPML tree parser metrics, Movesense sync | M1, M2 | ORIGINAL_REQUEST R2.5 |
| F9 | Screen 6 & TrainingView Integration | Register in `canonical_tui.py:SCREENS`, hotkeys 't'/'6', tabs, Braille rendering | M3 | ORIGINAL_REQUEST R3 |
| F10 | Comprehensive Test Suite | Multi-tier unit, integration, and E2E test verification with zero mocks | M4 | ORIGINAL_REQUEST Acceptance |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Training Telemetry & Gyms Data Bridge | Build zero-mock asynchronous collectors in `backend/training_telemetry_collector.py` with MPSC ring buffers | none | PLANNED |
| M2 | Screen 6 Widgets & Braille Visualizers | Implement Textual widgets with Unicode Braille matrices in `tui/widgets/training_pipeline_widget.py` & `tui/widgets/lauburu_gyms_widget.py` | M1 | PLANNED |
| M3 | TrainingScreen & TrainingView Assembly | Assemble `tui/screens/training_screen.py`, `tui/views/training_view.py`, and register in `tui/canonical_tui.py` | M2 | PLANNED |
| M4 | E2E Testing Suite & TEST_READY | Full 4-Tier test suite covering all features with verified exit code 0 | M3 | PLANNED |
| M5 | Final Verification & Swarm Truth Audit | Complete visual/runtime verification and forensic audit compliance check | M4 | PLANNED |

## Interface Contracts
### `backend/training_telemetry_collector.py` ↔ `tui/widgets/training_pipeline_widget.py`
- `get_ingestion_loop_telemetry() -> Dict[str, Any]`: Returns `file_size_bytes`, `file_size_mb`, `record_count`, `growth_rate_bps`, `aux_datasets`.
- `get_gatekeeper_telemetry() -> Dict[str, Any]`: Returns `active_intercepts_count`, `lock_state`, `recent_intercepts_log`, `threat_level`.
- `get_hf_epoch_vram_gate() -> Dict[str, Any]`: Returns `vram_free_gb`, `vram_total_gb`, `vram_headroom_pct`, `kimi_88b_active`, `is_blocked`, `status_message`.

### `backend/training_telemetry_collector.py` ↔ `tui/widgets/lauburu_gyms_widget.py`
- `get_red_blue_arena_telemetry() -> Dict[str, Any]`: Returns `team_local_score`, `team_cloud_score`, `vuln_discovery_rate`, `recent_attacks`, `resistances`.
- `get_mesh_healing_telemetry() -> Dict[str, Any]`: Returns `last_recovery_latency_ms`, `active_tier`, `fault_count`, `recent_healing_events`.
- `get_stealth_compute_telemetry() -> Dict[str, Any]`: Returns `yield_latency_ms`, `max_temperature_c`, `tensor_route`, `doze_whitelisted_apps`.
- `get_software_dev_game_telemetry() -> Dict[str, Any]`: Returns `leaderboard_entries` (rank, architect, ELO, compliance), `recent_matches`.
- `get_spatial_grappling_telemetry() -> Dict[str, Any]`: Returns `opml_node_count`, `active_positions`, `current_torque_nm`, `movesense_sync_hz`.

## Code Layout
```
01_apps/canonical_port/
├── backend/
│   ├── training_telemetry_collector.py    # Zero-mock data collectors & MPSC bridges
│   ├── blackboard_store.py               # Shared thread-safe telemetry cache
│   └── devils_lock_governor.py           # VRAM gate & process lock governor
├── tui/
│   ├── canonical_tui.py                  # Main TUI app & screen switcher registration
│   ├── screens/
│   │   ├── training_screen.py            # Screen 6: TrainingScreen
│   │   └── ...
│   ├── views/
│   │   ├── training_view.py              # Embedded TrainingView for grid
│   │   └── ...
│   └── widgets/
│       ├── training_pipeline_widget.py   # Ingestion Loop, Gatekeeper, HF Epoch widget
│       ├── lauburu_gyms_widget.py        # 5 AI Gyms interactive tabbed widget
│       └── live_implementation_stream_widget.py # MPSC & Braille sparkline utilities
└── tests/
    ├── unit/
    │   ├── test_training_telemetry_collector.py
    │   ├── test_training_pipeline_widget.py
    │   └── test_lauburu_gyms_widget.py
    └── e2e/
        └── test_training_screen_e2e.py
```
