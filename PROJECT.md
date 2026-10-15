# PROJECT: Continuous Lens 1B-Context Loop, Pod Mesh & Frontier Swarm Consensus Engine

## Architecture
The Lauburu Monorepo Continuous Lens 1B-Context Pod Mesh and Swarm Consensus System integrates four primary pillars:
1. **Headless Pod Mesh Infrastructure (`00_core_infrastructure`)**: Podman-compose rootful pod stack (`podman-compose-headless-mesh.yml`) hosting `headless-chromium` (CDP port 9222), `sovereign-colab-jupyter` (port 8889), `headless-ide-intellij` (port 8443), `pyspark-data-lake` (port 8089), `neo-graphs-qdrant` (ports 6333/6334), `screen-lens-sovereign-daemon` (host network), and `pi-agent-worker` (`@earendil-works/pi-coding-agent`).
2. **1B Context Sharding Fabric & Lens Perception (`01_apps/screen_lens`, `02_ai_models_and_inference`, `06_scripts_and_tooling/automation`)**: Pipelined Ring Parallelism (PRP) context sharding over 40Gbps Thunderbolt 4 bridge (`10.0.0.2` <-> `10.0.0.8` / `10.0.0.4`, <0.4ms RTT) managed by `decentralized_prima_daemon.py` (Port 8082). Driven by `continuous_1b_lens_loop.py`, `continuous_lens_cdp_practice.py`, and `unified_screen_lens.py` to extract VLA perception artifacts (PNG screenshots and JSON DOM trees) into `obsidian_vault/04_ANALYTICS/VLA_PERCEPTION/`.
3. **Continuous Swarm Consensus Engine (`06_scripts_and_tooling/ai`, `05_agents_and_swarms`)**: Multi-pillar debate loop in `frontier_swarm_consensus.py` summoning cloud frontier models (Google DeepMind Gemini 2.5 Pro/Flash, Anthropic Claude 3.5 Sonnet / 3 Opus, OpenAI GPT-4o, DeepSeek Chat) and local endpoints (Ports 8082, 8083, 8081). Integrates `deep-research`, `closed-source-reverse-engineering`, and `hardware-market-scout`.
4. **Tri-Vault Storage & Tri-Proof Verification Gate (`obsidian_vault/`, `lora_datasets/`, `04_data_and_memory/`)**: Dual-plane document mirroring (`LOAD_BALANCING_CONSENSUS.md` in monorepo root and Obsidian Vault), SHA256-checksummed JSONL DPO stream to `continuous_lora_dataset.jsonl`, and Tri-Proof Gate (Exit Code 0, SHA256 verification, Screen Lens visual HUD capture).

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Podman Compose Headless Mesh | Container composition including JupyterLab, Chromium CDP, Code-Server, PySpark, Qdrant | Milestone 1 | Follow-up 2026-10-12 |
| 2 | Safe Tri-Vault Volume Mounts | Safe mounting of `obsidian_vault`, `lora_datasets`, `04_data_and_memory` without host pollution | Milestone 1 | Follow-up 2026-10-12 |
| 3 | Containerized 'pi' Agent Worker | Running `@earendil-works/pi-coding-agent` worker safely in pod alongside Lens and IDEs | Milestone 1 | Follow-up 2026-10-13 |
| 4 | Host Sanctuary Memory Telemetry | Active `vm_stat`/`sysctl` Mach watchdog preserving >= 4.8 GB free physical RAM on L1 host | Milestone 1 | Dispatch R4 / Rule 3 |
| 5 | Lens 1B Context Window Loop | 1-billion token context block processing sharded across 40Gbps TB4 bridge without OOM | Milestone 2 | Dispatch R1 |
| 6 | Chromium CDP VLA Perception | CDP practice automation extracting PNG screenshots and JSON DOM accessibility trees to Obsidian | Milestone 2 | Follow-up 2026-10-12 |
| 7 | Terminal AI 'pi' Trajectory Harvesting | Harvesting `pi` session logs into `continuous_lora_dataset.jsonl` with SHA256 checksums | Milestone 2 | Initial Request R2/R3 |
| 8 | Continuous Frontier Swarm Consensus | Multi-model debate between cloud frontier models and local endpoints (Ports 8082, 8083) | Milestone 3 | Initial Request R1/R2 |
| 9 | Specialized Skills Integration | Grounding consensus via `deep-research`, `closed-source-reverse-engineering`, `hardware-market-scout` | Milestone 3 | Dispatch R3 |
| 10 | Tri-Proof Verification Gate | Exit Code 0 (Proof 1), SHA256 checksums (Proof 2), Screen Lens visual HUD capture (Proof 3) | Milestone 3 | Initial Request R3 |
| 11 | Continuous LoRA Dataset Distillation | Streaming DPO/instruction pairs with SHA256 hashes to `continuous_lora_dataset.jsonl` | Milestone 3 | Initial Request R2 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Pod Manifests, 'pi' Container Worker & Host Sanctuary | Expand `podman-compose-headless-mesh.yml` with Jupyter, Chromium, Code-Server, 'pi' worker; enforce safe volume mounts and Host Sanctuary >=4.8GB free RAM cap | None | DONE |
| 2 | 1B Context Sharding Loop & Screen-Lens CDP Automation | Implement `continuous_1b_lens_loop.py` for 1B context sharding over 40Gbps TB4 bridge (Port 8082) + CDP VLA perception extraction & 'pi' trajectory harvester | M1 | DONE |
| 3 | Swarm Consensus Engine with Deep Research & Market Scouting | Enhance `frontier_swarm_consensus.py` with `deep-research`, `closed-source-reverse-engineering`, `hardware-market-scout`, Tri-Proof Gate, and SHA256 distillation | M1, M2 | DONE |
| 4 | Final E2E Test Suite Pass & Adversarial Hardening | Pass 100% of E2E test suite across Tiers 1-4, followed by Tier 5 adversarial coverage hardening | M1, M2, M3 | DONE |

## Interface Contracts
### Pod Mesh ↔ Host Sanctuary Interface
- Endpoint: `HostSanctuary.get_free_ram_gb()` / `HostSanctuary.is_sanctuary_safe(threshold_gb=4.8)`
- Signal: Returns `True` if L1 Mach kernel free RAM >= 4.8 GB; if `False`, pod orchestrator waterfills/offloads heavy container tasks to Node L8 (`10.0.0.8`).

### 1B Context Sharding ↔ TB4 Ring Interface
- Endpoint: `http://127.0.0.1:8082/v1/chat/completions` & `/v1/ring_status`
- Data Flow: Context chunks transmitted via 40Gbps Thunderbolt 4 DMA (`bridge0` IP `10.0.0.2` <-> `10.0.0.8` / `10.0.0.4`, <0.4ms RTT) using Pipelined Ring Parallelism (PRP).

### Swarm Consensus ↔ Tri-Vault Distillation Interface
- Output Sink: `/Users/aaron/DFS_UNIFIED/lora_datasets/continuous_lora_dataset.jsonl`
- Format: JSONL containing `instruction`, `input`, `output`, `metadata`, `timestamp`, and `sha256` (64-char hex hash). Thread-safe append via `fcntl.flock(f, fcntl.LOCK_EX)`.

## Code Layout
```
/Users/Shared/aaron/DFS_UNIFIED/Lauburu-Monorepo/
├── 00_core_infrastructure/
│   ├── podman-compose-headless-mesh.yml          # Headless Podman compose manifest
│   ├── bootstrap_podman_headless_mesh.sh         # Podman mesh deployment bootstrapper
│   └── mcp_servers/lens-mcp/                     # TypeScript Screen Lens MCP server
├── 01_apps/screen_lens/                          # Screen Lens application & orchestrator
├── 02_ai_models_and_inference/
│   ├── decentralized_prima_daemon.py             # Port 8082 Sovereign Master REST server
│   └── decentralized_prima_mesh_coordinator.py   # PRP ring topology & sharding coordinator
├── 05_agents_and_swarms/
│   └── screen_lens_mcp_evolution/
│       └── frontier_swarm_consensus.py           # Subsystem Quad-Council consensus engine
├── 06_scripts_and_tooling/
│   ├── ai/
│   │   └── frontier_swarm_consensus.py           # Primary production Swarm Consensus CLI
│   └── automation/
│       ├── continuous_1b_lens_loop.py            # Continuous 1B context sharding loop
│       ├── continuous_lens_cdp_practice.py       # CDP VLA perception practice automation
│       ├── unified_screen_lens.py                # Multi-node Screen Lens automation driver
│       └── multiplexed_ai_terminal_orchestrator.py # Terminal AI & 'pi' trajectory harvester
├── obsidian_vault/
│   ├── 04_ANALYTICS/VLA_PERCEPTION/             # VLA perception screenshots & DOM trees
│   └── APPS_AND_FEATURES/                       # Mirrored architectural consensus reports
└── lora_datasets/
    └── continuous_lora_dataset.jsonl             # Central Tri-Vault LoRA distillation sink
```
