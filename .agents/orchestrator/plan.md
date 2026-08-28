# Execution Plan — SeaweedFS High Availability & Stabilization

## Objective
Re-architect and stabilize the SeaweedFS distributed network storage layer across the 7-node Tailscale mesh to ensure zero downtime during network drops, specifically addressing FUSE mount lockups and single-point-of-failure master nodes.

## Orchestration Strategy: Project Pattern (Dual-Track)

### Step 0: Comprehensive Survey & Specification Mining
- Spawn 3 parallel survey explorers / spec miners:
  - `survey_explorer_1`: Deep inspection of existing `00_core_infrastructure/seaweedfs` or related configs, compose files, current SeaweedFS mount scripts, ports, volumes, and architecture.
  - `survey_spec_miner_2`: Formal SeaweedFS Raft consensus specifications (3-master peers topology, master ports 9333, gRPC 19333, volume servers, filer clusters, failover behavior, S3/FUSE HA routing).
  - `survey_explorer_3`: FUSE mount failure modes on macOS/Linux (timeout, hang, transport endpoint not connected, `umount -l`, zombie process recovery, smolagents `@tool` signature requirements).
- Synthesize findings into global `PROJECT.md` with full Feature Inventory and Interface Contracts.

### Step 1: E2E Testing Track
- Spawn E2E Testing Orchestrator / Test Writer to design comprehensive 4-Tier test suite:
  - Tier 1: Feature Coverage (Raft peer discovery, watchdog health check, tool schemas)
  - Tier 2: Boundary & Corner Cases (network drop simulation, unmount timeout, leader election during partition)
  - Tier 3: Cross-Feature Combinations (watchdog trigger while smolagent tool executing, failover under active I/O)
  - Tier 4: Real-World Application Workloads (7-node Tailscale mesh multi-client I/O, chaos network resilience)
- Publish `TEST_INFRA.md` and `TEST_READY.md`.

### Step 2: Implementation Track — Milestones & Gate Verification
- **Milestone 1**: SeaweedFS 3-Node Raft Cluster Deployment
  - Update `docker-compose.yml` / deployment scripts with 3-master Raft consensus across Tailscale mesh.
  - Verification Gate: Explorers -> Worker -> 2 Reviewers -> 2 Challengers -> Forensic Auditor.
- **Milestone 2**: FUSE Mount Zombie Watchdog Daemon
  - Create `fuse_watchdog.sh` / daemon with aggressive I/O timeout detection, `umount -l`, and auto-remounting.
  - Verification Gate: Explorers -> Worker -> 2 Reviewers -> 2 Challengers -> Forensic Auditor.
- **Milestone 3**: Mesh Healer Agent Smolagents Integration
  - Author `seaweed_tools.py` with fully typed `@tool` functions (`heal_fuse_mount()`, `check_raft_consensus()`).
  - Verification Gate: Explorers -> Worker -> 2 Reviewers -> 2 Challengers -> Forensic Auditor.
- **Milestone 4**: Full E2E Live Mesh Verification & Victory Audit
  - Execute full E2E test suite against all 3 milestones.
  - Forensic Victory Audit for zero-mock compliance, real execution, and acceptance criteria.
  - Delivery to Sentinel.
