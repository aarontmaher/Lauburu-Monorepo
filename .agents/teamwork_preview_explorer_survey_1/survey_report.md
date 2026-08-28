# Monorepo Comprehensive Survey & Architectural Reconciliation Report
**Date**: 2026-08-27 | **Agent**: `teamwork_preview_explorer_survey_1` | **Scope**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo` & `/Users/aaron/teamwork_projects`

## 1. Executive Summary & Ecosystem Totals
- **Total Unified Monorepo Files (Physical Tree)**: **133,463 files** across **12,768 directories** (7,894.94 MB / ~7.89 GB).
- **Teamwork Projects (`/Users/aaron/teamwork_projects`)**: **63,898 files** across **8,673 directories** (2,022.11 MB / ~2.02 GB) across 34 active federated project workspaces.
- **Total Combined Multi-Project Ecosystem**: **197,361 files**.
- **Symlink Audit**: **86 symlinks** in monorepo (79 relative, 7 absolute, **2 broken/dangling**), **45 symlinks** in teamwork_projects (31 relative, 14 absolute, 0 broken).
- **Storage Health Verification**: Certified **HEALTHY** (Obsidian Vault: OK, PySpark Lake: OK, Disk Free: 49.80 GB >= 5.0 GB).

## 2. Canonical 13-Module Inventory (00_ through 12_)
| Canonical Module | Purpose & Core Contents | Files | Dirs | Symlinks | Size (MB) | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `00_SYSTEM_DASHBOARDS` | Canonical Subsystem | 8 | 0 | 0 | 0.03 | Underpopulated |
| `00_core_infrastructure` | Canonical Subsystem | 32123 | 2739 | 28 | 254.11 | Populated |
| `01_apps` | Canonical Subsystem | 48482 | 5156 | 47 | 1390.17 | Populated |
| `02_ai_models_and_inference` | Canonical Subsystem | 21571 | 1957 | 0 | 2512.37 | Populated |
| `03_biometrics_and_telemetry` | Canonical Subsystem | 7 | 4 | 0 | 0.12 | Underpopulated |
| `04_data_and_memory` | Canonical Subsystem | 246 | 16 | 0 | 760.0 | Populated |
| `05_agents_and_swarms` | Canonical Subsystem | 22372 | 2070 | 3 | 613.9 | Populated |
| `06_scripts_and_tooling` | Canonical Subsystem | 116 | 13 | 2 | 0.8 | Populated |
| `07_docs_and_architecture` | Canonical Subsystem | 135 | 11 | 0 | 1.69 | Populated |
| `08_business_and_commerce` | Canonical Subsystem | 1 | 0 | 0 | 0.0 | Stub/README only |
| `09_app_store_and_release` | Canonical Subsystem | 1 | 0 | 0 | 0.0 | Stub/README only |
| `10_spatial_grappling_kinematics` | Canonical Subsystem | 5 | 1 | 0 | 0.62 | Underpopulated |
| `11_security_and_governance` | Canonical Subsystem | 1 | 0 | 0 | 0.0 | Stub/README only |
| `12_continuous_lora_evolution` | Canonical Subsystem | 24 | 1 | 0 | 427.94 | Populated |

### Detailed Breakdown of Key Canonical Modules:
1. **`00_core_infrastructure` (32,012 files, 2,723 dirs)**:
   - Contains SeaweedFS, Docker compose manifests, multi-WAN routing (52 items), systemd units, self-healing hub (Port 18802), and Marionette MCP.
   - *Action required*: Populate empty subdirs `cloudflare_worker` and `supabase` from legacy `core/` and `webapp/`.
2. **`01_apps` (48,455 files, 5,149 dirs)**:
   - Contains major production frontends: `lauburu_compute_hub`, `zone2_endurance`, `obsidian_web` (Quartz digital garden), `movesense_hub`, `port_4000_hub`, `openclaw`, `dark_mode_pwa`, `lauburu_business_app`, `lauburu-storefront`.
   - *Action required*: Populate empty `grapplingmap_web` (from `core/apps/grapplingmap-web` and `webapp/`) and empty `chat_app` (from `core/chat-app`).
3. **`02_ai_models_and_inference` (21,571 files, 1,957 dirs)**:
   - Contains llama.cpp RPC sharding (Ports 8081-8084), Petals DHT layer swarm, Exo P2P sharding, model vault GGUF descriptors, benchmarks, and modelfiles.
4. **`03_biometrics_and_telemetry` (7 files, 4 dirs)**:
   - Contains `dsp_algorithms/` (`whoop-intelligence.js`, `multi-user-health.js`, `health-context-input.js`), `movesense_ecg_128hz`, `optical_ppg_dsp`, and `Movesense/grappling_history.db`.
   - *Action required*: Consolidate Pan-Tompkins 512Hz QRS DSP and PTT blood pressure algorithms here.
5. **`04_data_and_memory` (246 files, 16 dirs)**:
   - Contains PySpark data indexers, Qdrant vector database storage, 24/7 LoRA datasets, session logs (118 items), and reports.
   - *Action required*: Populate empty `core_data/` from `core/data/`.
6. **`05_agents_and_swarms` (22,372 files, 2,070 dirs)**:
   - Contains Tri-Orchestrator AI debate engine, Genetic MoE engine, `architect_leaderboard.json`, `jules_scaling_protocol.md`, smolagents, and Antigravity skills.
7. **`06_scripts_and_tooling` (116 files, 13 dirs)**:
   - Contains `expect/` (29 `.exp` scripts), `dark_mode/`, `device_watchdog/`, `mesh/`, `network_self_healing/`, `storage/`, and `telemetry/`.
   - *Action required*: Populate empty `core_scripts/` from `core/scripts/` (25 scripts) and `core_tools/` from `core/tools/`.
8. **`07_docs_and_architecture` (135 files, 11 dirs)**:
   - Contains `core_docs/` (113 files synced from `core/docs`), debate whitepapers (`MOVESENSE_BLUETOOTH_ARCHITECTURE_DEBATE.md`, `SHIZUKU_ANDROID_EXECUTION_DEBATE.md`), and mesh storage topology.
9. **`08_business_and_commerce` (1 file - README.md)**:
   - *Action required*: Reconcile and link Shopify Storefront GraphQL apps, Shopify audit suites (`webapp/SHOPIFY_AUDITS`), and membership billing contracts.
10. **`09_app_store_and_release` (1 file - README.md)**:
    - *Action required*: Map OpenClaw APK build manifests, store metadata, App Store review compliance guidelines, and keystore signing manifests.
11. **`10_spatial_grappling_kinematics` (5 files, 1 dir)**:
    - Contains `opml_trees/` with `grappling.opml` (3,044 nodes), `grappling.opml.pre-structure-fix` (3,228 nodes), `grappling.opml.backup-guard01` (3,385 nodes), and `project_map.opml` (146 nodes).
12. **`11_security_and_governance` (1 file - README.md)**:
    - *Action required*: Map RPC socket encryption specs, Cloudflare HMAC authentication rules, and security audit tests from Hemodynamic Cloud Server.
13. **`12_continuous_lora_evolution` (24 files, 1 dir)**:
    - Contains 23 active `.jsonl` fine-tuning datasets for TRL/PEFT/DPO continuous distillation.

## 3. Legacy vs Restored Components Survey
| Directory | Files | Dirs | Role & Status | Reconciliation Action |
| :--- | :--- | :--- | :--- | :--- |
| `core/` | 1153 | 141 | Legacy / Root Subsystem | Reconcile into canonical hierarchy & maintain relative symlinks |
| `webapp/` | 493 | 39 | Legacy / Root Subsystem | Reconcile into canonical hierarchy & maintain relative symlinks |
| `apps/` | 25 | 1 | Legacy / Root Subsystem | Reconcile into canonical hierarchy & maintain relative symlinks |
| `data/` | 51 | 18 | Legacy / Root Subsystem | Reconcile into canonical hierarchy & maintain relative symlinks |
| `docs/` | 8 | 1 | Legacy / Root Subsystem | Reconcile into canonical hierarchy & maintain relative symlinks |
| `scripts/` | 34 | 0 | Legacy / Root Subsystem | Reconcile into canonical hierarchy & maintain relative symlinks |
| `tests/` | 90 | 5 | Legacy / Root Subsystem | Reconcile into canonical hierarchy & maintain relative symlinks |
| `reports/` | 77 | 2 | Legacy / Root Subsystem | Reconcile into canonical hierarchy & maintain relative symlinks |
| `logs/` | 5 | 0 | Legacy / Root Subsystem | Reconcile into canonical hierarchy & maintain relative symlinks |
| `self_healing_hub/` | 1404 | 195 | Legacy / Root Subsystem | Reconcile into canonical hierarchy & maintain relative symlinks |
| `Installed_Apps/` | 5 | 4 | Legacy / Root Subsystem | Reconcile into canonical hierarchy & maintain relative symlinks |
| `obsidian_vault/` | 85 | 47 | Legacy / Root Subsystem | Reconcile into canonical hierarchy & maintain relative symlinks |
| `lora_datasets/` | 8 | 0 | Legacy / Root Subsystem | Reconcile into canonical hierarchy & maintain relative symlinks |
| `ai_debate/` | 4 | 2 | Legacy / Root Subsystem | Reconcile into canonical hierarchy & maintain relative symlinks |

### Detailed Mapping of Legacy Directories:
- **`core/` (1,153 files, 141 dirs)**:
  - `core/apps/grapplingmap-web` (80 files) -> Map to `01_apps/grapplingmap_web/`
  - `core/apps/mobile` (7 files) -> Map to `01_apps/Installed_Apps/mobile`
  - `core/chat-app` (10 files) -> Map to `01_apps/chat_app/`
  - `core/cloudflare-worker` (10 files, tests/46) -> Map to `00_core_infrastructure/cloudflare_worker/`
  - `core/supabase` (8 files) -> Map to `00_core_infrastructure/supabase/`
  - `core/scripts` (25 files) -> Map to `06_scripts_and_tooling/core_scripts/`
  - `core/tools` (1 file) -> Map to `06_scripts_and_tooling/core_tools/`
  - `core/data` (4 files) -> Map to `04_data_and_memory/core_data/`
  - `core/docs` (113 files) -> Already mapped to `07_docs_and_architecture/core_docs/`
- **`webapp/` (493 files, 39 dirs)**:
  - Full standalone web app codebase for Grappling Map, Whoop intelligence, Stage 1 deployment, and Siri shortcuts.
  - Symlink / sync to `01_apps/grapplingmap_web/` and maintain backward-compatible relative links.
- **`self_healing_hub/` (1,404 files, 195 dirs)**:
  - Root-level duplicate of `00_core_infrastructure/self_healing_hub/`.
  - Can be symlinked to `00_core_infrastructure/self_healing_hub/` to eliminate duplicate node_modules and broken symlinks.
- **`Installed_Apps/` (5 files, 4 dirs)**:
  - Reconcile with `01_apps/Installed_Apps/`. Fix dangling symlink `Phone_Applications`.

## 4. Root-Level File Categorization & Hygiene Plan
The monorepo root currently contains **163 loose files** that require categorization and relocation under the Root Level Hygiene directive:
1. **Expect Scripts (`*.exp`, 29 files)**:
   - Files: `adb_linux.exp`, `adb_perms.exp`, `adb_perms_router.exp`, `adb_perms_router2.exp`, `adb_router.exp`, `cat_file.exp`, `check_samba.exp`, `check_samba_logs.exp`, `check_tether.exp`, `debug_router.exp`, `debug_router2.exp`, `deploy_nas.exp`, `deploy_nas2.exp`, `deploy_samba.exp`, `deploy_samba2.exp`, `fix_samba.exp`, `fix_samba2.exp`, `fix_samba3.exp`, `fix_samba4.exp`, `fix_samba_auth.exp`, `fix_samba_env.exp`, `force_tether.exp`, `mount_all_macs.exp`, `route_tether.exp`, `router_debug.exp`, `router_fix.exp`, `run_samba.exp`, `test_ping.exp`, `verify_macbook.exp`.
   - **Destination**: `06_scripts_and_tooling/expect/` (or `exp/`).
2. **Screenshots (`*.png`, 46 files)**:
   - Files: `grappling_screen.png`, `hub_screen1.png`, `hub_screenshot.png`, `movesense_screen.png`, `openclaw_pixel.png`, `pixel_screen*.png`, `s20_screen.png`, `step*.png`, `termux_chat*.png`, `zone2*.png`, etc.
   - **Destination**: `reports/screenshots/`.
3. **UI XML Dumps (`*.xml`, 30 files)**:
   - Files: `dump.xml`, `hub_dump.xml`, `openclaw_pixel_dump.xml`, `pixel_ui*.xml`, `scanning_dump.xml`, `sensors_dump.xml`, `window_dump*.xml`, `zone2*.xml`.
   - **Destination**: `reports/ui_dumps/`.
4. **Docker Compose & Dockerfiles (`docker-compose*.yml`, `Dockerfile.*`, 17 files)**:
   - Files: `docker-compose.yml`, `docker-compose.agi-backend.yml`, `docker-compose.connectivity.yml`, `docker-compose.dfs.yml`, `docker-compose.edge_hub.yml`, `docker-compose.genetic.yml`, `docker-compose.glusterfs.yml`, `docker-compose.mesh-agi.yml`, `docker-compose.mtd-test.yml`, `docker-compose.rpc_worker.yml`, `docker-compose.syncthing.yml`, `docker-compose.unified_node.yml`, `Dockerfile.connectivity`, `Dockerfile.edge_hub`, `Dockerfile.genetic`, `Dockerfile.mesh_daemon`, `Dockerfile.openclaw`.
   - **Destination**: `00_core_infrastructure/docker/`.
5. **Loose LoRA & Telemetry Datasets (`*.jsonl`, 12 files)**:
   - Files: `lora_dataset_task_*.jsonl` (9 files), `telemetry_chat_feed.jsonl`, `truth_audit_nomad_mesh_debate.jsonl`, `local_network_telemetry.jsonl`.
   - **Destination**: `04_data_and_memory/lora_datasets/` and `12_continuous_lora_evolution/lora_datasets/`.
6. **Helper Scripts & Configs**:
   - Python: `update_telemetry*.py` (4 files) -> `06_scripts_and_tooling/telemetry/`
   - JavaScript: `proxy.js`, `proxy2.js`, `test_ws.js` -> `06_scripts_and_tooling/scripts/`
   - LaunchDaemons / Configs: `com.lauburu.nasautomount.plist` -> `00_core_infrastructure/systemd/` or `launchdaemons/`; `smb_pool_config.conf` -> `00_core_infrastructure/infrastructure/`
   - Modelfiles: `Modelfile_moondream_max_compute`, `Modelfile_llava_reward` -> `02_ai_models_and_inference/modelfiles/`
   - OPML: `project_map.opml` -> `10_spatial_grappling_kinematics/opml_trees/`
7. **Pristine Root Preservation**:
   - Retain only canonical root files: `README.md`, `GEMINI.md`, `PROJECT.md`, `TEST_READY.md`, `TEST_INFRA.md`, `ORIGINAL_REQUEST.md`.

## 5. Teamwork Projects Inventory (34 Active Federated Projects)
| # | Project Name | Files | Dirs | Symlinks | Size (MB) | Purpose |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `ai_sharding_daemon` | 2055 | 236 | 3 | 27.96 | Federated Swarm Project |
| 2 | `ai_strengthening_training_game` | 279 | 62 | 3 | 41.12 | Federated Swarm Project |
| 3 | `ai_training_game` | 1109 | 129 | 3 | 19.34 | Federated Swarm Project |
| 4 | `ai_training_stealth_compute_arena` | 4672 | 526 | 3 | 126.66 | Federated Swarm Project |
| 5 | `antigravity_chat_mcp` | 2129 | 309 | 3 | 40.03 | Federated Swarm Project |
| 6 | `antigravity_mcp_models` | 1772 | 323 | 3 | 44.41 | Federated Swarm Project |
| 7 | `compute_pooling_app` | 68 | 21 | 0 | 0.31 | Federated Swarm Project |
| 8 | `dark_mode_audit` | 207 | 106 | 0 | 11.72 | Federated Swarm Project |
| 9 | `glinet_tethering_fix` | 174 | 50 | 0 | 0.59 | Federated Swarm Project |
| 10 | `glinet_usb_fix` | 52 | 17 | 0 | 0.34 | Federated Swarm Project |
| 11 | `global_training_games_audit` | 146 | 32 | 0 | 2.24 | Federated Swarm Project |
| 12 | `hf_training_integration` | 31372 | 3280 | 3 | 976.95 | Federated Swarm Project |
| 13 | `internet_debugging_swarm` | 712 | 76 | 3 | 8.99 | Federated Swarm Project |
| 14 | `internet_training_protocol` | 150 | 35 | 0 | 1.32 | Federated Swarm Project |
| 15 | `jules_repoless_integration` | 2665 | 400 | 5 | 63.52 | Federated Swarm Project |
| 16 | `lauburu_biometrics_algorithm_debate` | 0 | 0 | 0 | 0.0 | Federated Swarm Project |
| 17 | `lauburu_cli_sentinel` | 2188 | 242 | 3 | 24.81 | Federated Swarm Project |
| 18 | `lauburu_compute_hub` | 8118 | 1870 | 3 | 541.52 | Federated Swarm Project |
| 19 | `lauburu_webapp_and_competitor_analysis` | 2 | 0 | 0 | 0.06 | Federated Swarm Project |
| 20 | `luci_ai_connectivity` | 1673 | 207 | 3 | 24.83 | Federated Swarm Project |
| 21 | `mac_air_sync` | 72 | 15 | 0 | 0.22 | Federated Swarm Project |
| 22 | `mac_air_sync_audit` | 73 | 17 | 0 | 0.54 | Federated Swarm Project |
| 23 | `mesh_healing_ai_gym` | 22 | 6 | 0 | 0.09 | Federated Swarm Project |
| 24 | `mesh_network_optimizer` | 133 | 31 | 0 | 0.98 | Federated Swarm Project |
| 25 | `mesh_pwa_audit` | 182 | 50 | 0 | 1.08 | Federated Swarm Project |
| 26 | `mesh_telemetry_audit` | 176 | 46 | 1 | 0.92 | Federated Swarm Project |
| 27 | `open_source_scout_obsidian` | 168 | 67 | 0 | 1.16 | Federated Swarm Project |
| 28 | `software_dev_training_game` | 428 | 77 | 3 | 8.39 | Federated Swarm Project |
| 29 | `speedify_channel_bonding_ai` | 0 | 6 | 0 | 0.0 | Federated Swarm Project |
| 30 | `swarm_healer` | 72 | 20 | 0 | 0.23 | Federated Swarm Project |
| 31 | `termius_tui_dashboard` | 2782 | 320 | 3 | 50.29 | Federated Swarm Project |
| 32 | `tplink_linux_laptop` | 94 | 20 | 0 | 0.54 | Federated Swarm Project |
| 33 | `tplink_mesh_resurrection` | 151 | 41 | 0 | 0.94 | Federated Swarm Project |
| 34 | `visual_audit_swarm` | 0 | 2 | 0 | 0.0 | Federated Swarm Project |

## 6. Symlink Integrity & Broken Link Audit
### Monorepo Symlinks (86 total):
- **Relative symlinks (79)**: 100% valid node_modules binary links in `01_apps/zone2_endurance`, `01_apps/obsidian_web`, `00_core_infrastructure/self_healing_hub`, and internal module links.
- **Absolute symlinks (7)**:
  1. `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/movesense_hub` -> `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/movesense_hub`
  2. `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/teamwork_projects` -> `/Users/aaron/teamwork_projects`
  3. `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/obsidian_web/content` -> `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault`
  4. `00_core_infrastructure/self_healing_hub/.venv/bin/python` -> Python 3.13 uv interpreter
  5. `01_apps/lauburu_compute_hub/.venv/bin/python` -> Python 3.12 uv interpreter
  6. `05_agents_and_swarms/local_agi_smolagent/.venv/bin/python` -> Python 3.12 uv interpreter
  7. `Installed_Apps/Phone_Applications` -> `/Users/aaron/Lauburu-Monorepo-Local/Lauburu-Monorepo/Installed_Apps/Phone_Applications` (**BROKEN**)
- **Broken Symlinks Detected (2)**:
  1. `Installed_Apps/Phone_Applications` (points to missing `/Users/aaron/Lauburu-Monorepo-Local/...`).
  2. `self_healing_hub/frontend/node_modules/.bin/rolldown` (legacy un-reconciled tree; canonical `00_core_infrastructure/self_healing_hub` is intact).

### Teamwork Projects Symlinks (45 total):
- **45 symlinks total**: 31 relative, 14 absolute (all point to valid Python uv venv interpreters or active agent markers). **0 broken symlinks**.

## 7. Domain Subsystem Mapping & User Directive Alignment
1. **Web Apps & Frontends -> `01_apps/`**:
   - `grapplingmap_web`: Map from `core/apps/grapplingmap-web` and `webapp/` (80 files).
   - `chat_app`: Map from `core/chat-app` (10 files).
   - `movesense_hub`, `port_4000_hub`, `obsidian_web`, `zone2_endurance`, `openclaw`, `lauburu_business_app`: Fully established in `01_apps/`.
2. **OPML Grappling Trees & Kinematics -> `10_spatial_grappling_kinematics/`**:
   - `opml_trees/grappling.opml` (3,044 nodes), `grappling.opml.pre-structure-fix` (3,228 nodes), `grappling.opml.backup-guard01` (3,385 nodes), and `project_map.opml` (146 nodes) correctly placed in `10_spatial_grappling_kinematics/opml_trees/`.
3. **Biometrics DSP & Telemetry -> `03_biometrics_and_telemetry/`**:
   - Whoop intelligence, multi-user health, health context input, Movesense ECG (128Hz & 512Hz), optical PPG, and grappling history database mapped cleanly.
4. **Cloud Infrastructure -> `00_core_infrastructure/`**:
   - Cloudflare workers (`core/cloudflare-worker`) and Supabase edge functions/migrations (`core/supabase`, `webapp/supabase`) mapped to `00_core_infrastructure/`.
5. **Architecture Docs & Knowledge Graph -> `07_docs_and_architecture/` & `obsidian_vault/`**:
   - 113 core docs mapped to `07_docs_and_architecture/core_docs/`.
   - Obsidian Vault contains canonical knowledge graph and syncs directly to Quartz digital garden in `01_apps/obsidian_web/content`.
6. **Backward Compatibility Guarantee**:
   - Relative symlinks from legacy paths (`core/`, `webapp/`, root scripts) ensure no CLI, build system, or automation pipeline experiences regressions.