# Project: Canonical TUI Prototypes & Termux Deployment Engine

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       CLOUD API QUOTA DAEMON                                │
│       06_scripts_and_tooling/automation/cloud_api_quota_manager.py           │
│                                  │ (atomic replace with lock)               │
│                                  ▼                                          │
│        04_data_and_memory/data/cloud_api_quota_state.json                   │
│        04_data_and_memory/data/cloud_api_quota_state.lock                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                   │ (Shared Read / Sync)
         ┌─────────────────────────┼─────────────────────────┐
         ▼                         ▼                         ▼
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│ Python (Textual)│       │Go (Bubble Tea)  │       │ Rust (Ratatui)  │
│  - DataTable    │       │ - Elm Model     │       │ - Crossterm     │
│  - Progress/HUD │       │ - Lip Gloss     │       │ - Serde JSON    │
│  - Async Loop   │       │ - Goroutine Poll│       │ - Sub-10ms Init │
└─────────────────┘       └─────────────────┘       └─────────────────┘
         │                         │                         │
         └─────────────────────────┼─────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                 TERMUX AUTOMATED PROVISIONING & DEPLOYMENT                  │
│       - Wireless ADB (Port 5555) / Universal SSH (Port 8022)                │
│       - Auto Toolchain Bootstrap: pkg install python, golang, rust          │
│       - Edge Native Compilation & Remote Smoke Verification                 │
│       - Targets: Pixel 10 Pro XL (L6), Samsung Galaxy S20+ (L7)             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Feature Inventory

| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Python Textual Prototype | Interactive TUI with DataTable, progress meters, reactive polling, and `--verify` mode | M1 | R1 |
| 2 | Go Bubble Tea Prototype | Single-binary Elm-architecture TUI with Lip Gloss styling, `--verify` mode | M1 | R1 |
| 3 | Rust Ratatui Prototype | High-performance compiled TUI with Crossterm, immediate mode widgets, `--verify` mode | M1 | R1 |
| 4 | Atomic Concurrency & Locking | Safe concurrent reads with retry backoff against `cloud_api_quota_state.lock` | M1 | R1 |
| 5 | Automated Toolchain Provisioner | Zero-touch `pkg install -y python golang rust` on Termux via ADB/SSH | M2 | R3 |
| 6 | Wireless Deployment Engine | Synchronizes code, builds binaries, and syncs quota state over ADB/SSH | M2 | R2 |
| 7 | Remote Termux Smoke Verification | Non-interactive execution on mobile hardware confirming clean launch and state read | M3 | Acceptance |
| 8 | Comprehensive E2E Test Suite | 4-tier opaque-box test suite verifying all features, boundary cases, and edge runs | E2E | Acceptance |

## Milestones

| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Tri-Framework TUI Prototypes | Implement Python Textual, Go Bubble Tea, and Rust Ratatui TUIs with full CLI flags and verify modes | None | DONE |
| M2 | Termux Automated Provisioner & Deployer | Implement automated toolchain provisioning and source sync scripts over ADB / SSH | M1 | DONE |
| M3 | Remote Verification & Integration | Implement remote verification test harness running on host against Termux nodes | M1, M2 | DONE |
| E2E | E2E Testing Suite (Tiers 1-4) | Comprehensive test suite for local and remote verification | M1, M2, M3 | DONE |

## Interface Contracts

### 1. Quota State Schema (`cloud_api_quota_state.json`)
```json
{
  "version": "2.0.0",
  "last_reset": "ISO8601",
  "last_reset_date": "YYYY-MM-DD",
  "last_updated": "ISO8601",
  "providers": {
    "<provider_id>": {
      "name": "string",
      "limit": 1000,
      "used_today": 0,
      "remaining_pct": 1.0,
      "status": "healthy|degraded|exhausted",
      "total_requests": 0,
      "consecutive_failures": 0,
      "avg_latency_ms": 45.0,
      "last_latency_ms": 42.0,
      "last_score": 0.95,
      "is_local": false
    }
  },
  "metrics": {
    "total_tasks_routed": 0,
    "cloud_tasks_succeeded": 0,
    "local_mesh_fallback_count": 0,
    "total_lora_samples_harvested": 0
  }
}
```

### 2. Standard CLI Flags for all TUIs
- `--state-path <path>`: Path to `cloud_api_quota_state.json` (defaults to monorepo standard path or relative `data/cloud_api_quota_state.json`).
- `--poll-interval <seconds>`: Refresh polling interval (default: 2.0).
- `--verify`: Run in non-interactive validation mode. Read state file, validate schema, print summary, exit 0 on success, non-zero on failure.
- `--timeout <seconds>`: Automatically terminate after N seconds (useful for headless smoke tests).

### 3. Termux Deployment Contract
- Connect to edge node via SSH (`ssh -p 8022 u0_a*@<ip>`) with fallback to ADB (`adb -s <ip>:5555 shell`).
- Deploy directory: `$HOME/lauburu_tui_prototypes` (`/data/data/com.termux/files/home/lauburu_tui_prototypes`).
- Ensure toolchain: `pkg install -y python golang rust jq git build-essential clang` and `pip install --break-system-packages textual rich pydantic`.
- Remote build commands: `go build -o bin/tui_go main.go`, `cargo build --release`.

## Code Layout

```
01_apps/canonical_tui_prototypes/
├── python_textual/
│   ├── app.py
│   ├── pyproject.toml
│   └── requirements.txt
├── go_bubbletea/
│   ├── main.go
│   ├── go.mod
│   └── go.sum
├── rust_ratatui/
│   ├── Cargo.toml
│   └── src/
│       └── main.rs
├── deploy/
│   ├── deploy_termux.sh
│   └── deploy_termux_tui.py
├── verify/
│   ├── verify_local.py
│   └── verify_termux.sh
└── tests/
    ├── conftest.py
    ├── test_tui_e2e.py
    └── test_adversarial_concurrency_fuzzing.py
```
