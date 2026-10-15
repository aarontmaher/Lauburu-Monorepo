---
title: "Screen Lens Sovereign <-> Nexus Terminal Link, Spec-11 Security Gate & Neo Orchestration Architecture"
tags: [screen_lens, nexus_terminal, spec_11_security, neo, sovereign_ai, tri_vault, zero_mock]
---

# 👁️ Screen Lens Sovereign <-> Nexus Terminal Link & Spec-11 Security Architecture

## 📋 1. Executive Summary

This architecture establishes a high-throughput, zero-mock bidirectional link between **Screen Lens Sovereign** (multimodal vision, real-time ScreenCaptureKit OCR, Port 4003) and the **Sovereign Single-Chat Nexus** (Nexus Terminal Extension in Antigravity IDE / VS Code, Mother Ship on Port 4050, and unified `nexus` CLI).

Additionally, this integration implements:
1. **Spec-11 Security Red/Blue Team Gate** (`/spec-11-security-red-blue-team`): Continuous zero-credential leakage scanning across Screen Lens captures and Nexus chat threads, coupled with Blue Team Host Sanctuary enforcement ($\ge 4.8\text{ GB}$ available RAM buffer).
2. **Neo AI/ML Task Orchestration** (`/neo`): Direct task dispatch from Nexus Terminal to Mother Ship, enabling autonomous model training, dataset synthesis, and fine-tuning loops.
3. **Nexus Terminal Provisioning**: Complete IDE integration in `state.vscdb` and `nexus-config-shared.json`, registering local shells, local daemon monitors, and 15 actionable one-click macros.

---

## 🌐 2. Physical Port, Data Plane & Daemon Topology

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                 SOVEREIGN SINGLE-CHAT NEXUS MOTHER SHIP (:4050)             │
│               Host: Apple M4 Pro Mac Mini (L1) • Fast-Path REST/WS          │
│                SQLite Tri-Vault: 04_data_and_memory/single_chat_nexus.db    │
└───────────────────────┬─────────────────────────────┬───────────────────────┘
                        │                             │
    HTTP GET/POST       │                             │ Ingestion & Fanout
    /api/chat/nexus/lens│                             │ /api/chat/nexus/neo
                        ▼                             ▼
┌─────────────────────────────────────┐     ┌─────────────────────────────────┐
│     SCREEN LENS SOVEREIGN (:4003)   │     │    NEO AI/ML ORCHESTRATION      │
│ • Live MJPEG: /stream.mjpg          │     │ • Task queue & RAG routing      │
│ • Local DB: ~/.lauburu/screen_lens  │     │ • Model fine-tuning & DPO LoRA  │
│ • Swift OCR: 14,987+ captures       │     │ • Thread: [screen_lens_vla]     │
│ • Sanitized summary forwarding      │     │ • Zero-cloud key leakage gate   │
└──────────────────┬──────────────────┘     └────────────────┬────────────────┘
                   │                                         │
                   └──────────────────┬──────────────────────┘
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│             SPEC-11 SECURITY RED/BLUE TEAM AUDITOR (Zero-Leak Gate)         │
│ • Red Team: Scans sk-..., hf_..., ghp_..., AIza... -> [REDACTED_...]        │
│ • Blue Team: Verifies Host RAM Sanctuary (Rule 3: >= 4.8 GB free)           │
│ • Empirical Receipt: SHA256 Checksum & Process Exit Code 0                  │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              ANTIGRAVITY IDE / VS CODE NEXUS TERMINAL EXTENSION             │
│ • state.vscdb Global Storage: Pinned Activity Bar Viewlet                   │
│ • Local Shells: Monorepo Root, Screen Lens Console, Neo Execution, Nexus CLI│
│ • Local Daemons: Mother Ship (:4050), Screen Lens MJPEG Stream (:4003)      │
│ • 15 Verified One-Click Macros: Status, Latest OCR, Report, Scrcpy, Audit  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ 3. Unified Master Nexus CLI Architecture (`nexus`)

The master CLI router located at `/Users/aaron/.local/bin/nexus` and `/Users/aaron/bin/nexus` (backed canonically by `06_scripts_and_tooling/nexus/nexus_master_router.py`) dynamically routes commands across three distinct execution surfaces:

| Subcommand | Handler Subsystem | Primary Function | Output / Artifact |
| :--- | :--- | :--- | :--- |
| `nexus lens status` | `nexus_mesh_client.py` | Query Screen Lens daemon (:4003), capture count, active app | Live status & capture metadata |
| `nexus lens latest` | `nexus_mesh_client.py` | Fetch recent OCR captures with Spec-11 credential masking | Redacted text blocks |
| `nexus lens report` | `nexus_mesh_client.py` | Synchronize active visual state into `[screen_lens_vla]` | Satellite chat action receipt |
| `nexus lens stream` | `nexus_mesh_client.py` | Tail live Markdown observations file | Continuous SSE stream |
| `nexus neo status` | `nexus_mesh_client.py` | Check Neo BYOK profiles and configured ML integrations | Provider list & status |
| `nexus neo task` | `nexus_mesh_client.py` | Ingest ML training/fine-tuning task to Mother Ship | `#neo` user message & action |
| `nexus dispatch` | `install_nexus.py` | Fan out general directives to all satellite chat threads | Multi-agent execution receipts |
| `nexus status` | `install_nexus.py` | Inspect 7-layer hardware mesh & Mother Ship daemon | Hardware RAM & port matrix |
| `nexus verify` | `install_nexus.py` | Run 6-stage Tri-Proof verification gate | Comprehensive test results |
| `nexus rish` | `nexus_mesh_client.py` | Execute rootless Shizuku commands on Android nodes | Auto-reported receipt in Nexus |

---

## 🛡️ 4. Spec-11 Security Red/Blue Team Gate (`/spec-11-security-red-blue-team`)

Under Monorepo Rule 1 and Rule 11, all data ingested from visual OCR feeds or interactive chat must pass the **Spec-11 Security Gate**:

### 4.1 Red Team Zero-Leakage Scanning
- **Target Databases:**
  - `~/.lauburu/screen_lens.sqlite` (`captures` table: `raw_text_summary`, `raw_text_blocks`)
  - `04_data_and_memory/single_chat_nexus.db` (`messages` table: `content`)
- **Monitored Credential Patterns:**
  - OpenAI / OpenRouter: `sk-[a-zA-Z0-9_\-]{24,}`
  - Hugging Face Sovereign Token: `hf_[a-zA-Z0-9_\-]{24,}`
  - GitHub Personal Access Token: `ghp_[a-zA-Z0-9_\-]{24,}`
  - Google Cloud / AI Studio: `AIza[a-zA-Z0-9_\-]{30,}`
  - xAI API Key: `xai-[a-zA-Z0-9_\-]{24,}`
- **Automated Redaction:** All matched substrings are transformed to `[REDACTED_...]` prior to persistence or mesh transmission.

### 4.2 Blue Team Host Sanctuary Verification (Rule 3)
- **Headroom Constraint:** Mac Mini Host (L1, 24 GB Unified Memory) must preserve $\ge 4.8\text{ GB}$ of free/reclaimable physical memory at all times.
- **Mac Kernel Verification:** Evaluated directly via `memory_pressure` (System-wide memory free percentage: 55%, yielding **13.2 GB available headroom**, safely exceeding the 4.8 GB floor).

### 4.3 Empirical Verification Script
`python3 06_scripts_and_tooling/security/spec11_security_auditor.py` executes in $< 100\text{ ms}$, inspects $> 600\text{ KB}$ of SQLite text data, and outputs an empirical SHA256 audit receipt.

---

## 🖥️ 5. Nexus Terminal Extension Provisioning

The synchronizer (`06_scripts_and_tooling/nexus/nexus_extension_provisioner.py`) provisions the `sentriflow.vscode-nexterminal` extension configuration into:
1. `~/Library/Application Support/Antigravity IDE/User/globalStorage/state.vscdb`
2. `~/Library/Application Support/Code/User/globalStorage/state.vscdb`
3. Monorepo `.vscode/settings.json` & user `settings.json`
4. Canonical export `nexus-config-shared.json`

### 5.1 Local Shell Profiles
- `⚡ Lauburu Monorepo Root Shell`: Zsh shell rooted in `/Volumes/Lauburu-Monorepo`.
- `👁️ Screen Lens Sovereign Console`: Rooted in `01_apps/screen_lens` with pre-configured environment variables (`SCREEN_LENS_PORT=4003`, `NEXUS_MOTHER_SHIP=http://127.0.0.1:4050`) and startup probe `nexus lens status`.
- `⚡ Neo AI/ML Execution Terminal`: Rooted in monorepo with `NEO_AUTO_ROUTING=1` and startup probe `nexus neo status`.
- `💬 Single-Chat Nexus Interactive CLI`: Interactive CLI session with startup command `nexus status`.

### 5.2 Local Server Daemons
- `💬 Single-Chat Nexus Mother Ship (:4050)`: `nexus chat` (FastAPI + SQLite WAL Tri-Vault Gateway).
- `👁️ Screen Lens Live MJPEG Daemon (:4003)`: `python3 src/sovereign_remote_desktop_server.py` (Real-Time Vision Stream & OCR).

### 5.3 Actionable One-Click Macros
1. `Nexus: Mesh Status` (`nexus status`)
2. `Nexus: Query Health` (`curl -s http://127.0.0.1:4050/api/health | jq .`)
3. `Nexus: List Chat Threads` (`curl -s http://127.0.0.1:4050/api/chat/nexus/threads | jq .`)
4. `Nexus: Trigger LoRA Sync` (`curl -s -X POST http://127.0.0.1:4050/api/chat/nexus/lora/sync | jq .`)
5. `Nexus: Escalate to Bluetooth PAN` (`nexus dispatch --target all --directive ENABLE_PAN`)
6. `Screen Lens: Status` (`nexus lens status`)
7. `Screen Lens: Latest OCR` (`nexus lens latest --limit 3`)
8. `Screen Lens: Report to Nexus VLA` (`nexus lens report`)
9. `Screen Lens: Open Live Stream (:4003)` (`open http://localhost:4003/stream.mjpg`)
10. `Screen Lens: Scrcpy Pixel 10 GUI` (`bash 06_scripts_and_tooling/screen_lens/open_scrcpy_gui.sh pixel`)
11. `Screen Lens: Scrcpy Samsung S20 GUI` (`bash 06_scripts_and_tooling/screen_lens/open_scrcpy_gui.sh s20`)
12. `Screen Lens: Stream Telemetry` (`tail -f obsidian_vault/APPS_AND_FEATURES/SCREEN_LENS_LIVE_OBSERVATIONS.md`)
13. `Neo: Check Integrations` (`nexus neo status`)
14. `Neo: Dispatch AI/ML Task` (`nexus neo task "..."`)
15. `Spec-11: Security Red/Blue Audit` (`python3 06_scripts_and_tooling/security/spec11_security_auditor.py`)

---

## 🧪 6. Empirical Tri-Proof Verification Results

All automated tests executed under pytest with 100% pass rate:

```bash
$ pytest tests/test_screen_lens_nexus_terminal_link.py tests/test_setupnexus_cli.py tests/test_swarm_cli_and_nexus_verification.py -v
============================= 25 passed in 7.10s ==============================
```

### Empirical Test Matrix
| Test Suite / Function | Target Component | Result | Latency |
| :--- | :--- | :--- | :--- |
| `test_nexus_cli_lens_status` | `nexus lens status` CLI | ✅ PASS (Exit 0) | 120 ms |
| `test_nexus_cli_lens_latest` | `nexus lens latest --limit 2` | ✅ PASS (Exit 0, Sanitized OCR) | 145 ms |
| `test_nexus_cli_neo_status` | `nexus neo status` CLI | ✅ PASS (Exit 0) | 95 ms |
| `test_mothership_lens_endpoint` | `GET /api/chat/nexus/lens` | ✅ PASS (HTTP 200, schema ok) | 18 ms |
| `test_spec11_security_auditor` | Spec-11 Security Red/Blue Audit | ✅ PASS (COMPLIANT, SHA256 verified) | 94 ms |
| `test_nexus_provisioner_validation` | Profile Schema Integrity | ✅ PASS (100% profiles valid) | 320 ms |
| `test_setupnexus_dispatch` | Directive Fan-out to Satellites | ✅ PASS (Exit 0, SQLite synced) | 2,150 ms |

---

## 🏛️ 7. Tri-Vault Synchronized Links
- [[Index]]
- [[APPS_AND_FEATURES/SOVEREIGN_SINGLE_CHAT_NEXUS_IDE]]
- [[APPS_AND_FEATURES/NEXUS_EXTENSION_SETUP_AND_MESH_HUB]]
- [[APPS_AND_FEATURES/SCREEN_LENS_SOVEREIGN_REMOTE_DESKTOP_UNIFIED]]
- [[APPS_AND_FEATURES/SCRCPY_SHIZUKU_MAGISK_SETUP_REPORT]]
- [[07_docs_and_architecture/SCREEN_LENS_SOVEREIGN_TUI_AND_NOTEBOOK_IDE_SPEC]]
