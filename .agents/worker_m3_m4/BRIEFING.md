# BRIEFING — 2026-08-23T12:31:00Z

## Mission
Execute Milestone 3 & Milestone 4: Complete data migration and cryptographic SHA-256 parity verification across all 60,000+ files (~19.5GB), safely decommission Linux storage stack (Samba, NFS, MinIO, SeaweedFS, MergerFS), and verify Linux Head Node RAM reclaim (~3.5GB).

## 🔒 My Identity
- Archetype: worker
- Roles: implementer, qa, specialist
- Working directory: /Volumes/nas-1/Lauburu-Monorepo/.agents/worker_m3_m4
- Original parent: fc0b04f8-9f6c-4471-87b6-15c8d4f61eb7
- Milestone: Milestone 3 (Data Migration & Parity) & Milestone 4 (Linux Decommissioning & RAM Reclaim)

## 🔒 Key Constraints
- Zero tolerance for simulated/fake data or hardcoded test results. Real empirical verification only.
- Strict 100% SHA-256 cryptographic parity across all 60,000+ files (~19.5GB logical data) before decommissioning.
- Safe step-by-step teardown of Linux storage services: samba_nas_gateway, lauburu_nfs_core, nas-minio, weed mount, weed filer, weed volume, weed master, and mergerfs unmount.
- Empirical verification of Linux Head Node RAM reclaim (~3.5GB) using free -m, vmstat, ps aux before/after teardown.
- Output handoff report with exact command logs, memory tables, and parity reports to /Volumes/nas-1/Lauburu-Monorepo/.agents/worker_m3_m4/handoff.md.

## Current Parent
- Conversation ID: fc0b04f8-9f6c-4471-87b6-15c8d4f61eb7
- Updated: 2026-08-23T12:31:00Z

## Task Summary
- **What to build**: Full dataset sync to native macOS SeaweedFS cluster, programmatic SHA-256 parity verification script & execution, safe Linux storage decommission, RAM reclaim audit.
- **Success criteria**: 100% data parity verified across all files, legacy containers stopped and disabled, legacy weed/mergerfs daemons stopped, ~3.5GB RAM reclaimed on Linux node.

## Change Tracker
- **Files modified**: [TBD]
- **Build status**: [TBD]
- **Pending issues**: None

## Quality Status
- **Build/test result**: [TBD]
- **Lint status**: [TBD]
- **Tests added/modified**: [TBD]

## Loaded Skills
- None
