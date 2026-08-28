## 2026-08-23T12:29:52Z

You are the Implementation Worker for Milestone 3 & Milestone 4: Data Migration, Cryptographic Parity Verification, Linux Decommissioning & RAM Reclaim.
Your Working Directory: /Volumes/nas-1/Lauburu-Monorepo/.agents/worker_m3_m4/
Authoritative Requirements: /Volumes/nas-1/Lauburu-Monorepo/.agents/ORIGINAL_REQUEST.md
Survey Reports:
- /Volumes/nas-1/Lauburu-Monorepo/.agents/explorer_survey_storage/handoff.md
- /Volumes/nas-1/Lauburu-Monorepo/.agents/explorer_survey_network/handoff.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Tasks:
1. Data Migration & Parity Verification:
   - Ensure all data from the Linux backend (/mnt/dfs_unified / /Volumes/nas) is fully synced to the native macOS SeaweedFS cluster (Filer at 169.254.80.69:8888) and the local NVMe monorepo.
   - Run a programmatic verification script comparing file paths, file sizes, and SHA-256 cryptographic hashes between the source dataset and destination.
   - Confirm 100% data parity across all 60,000+ files (~19.5 GB logical data).
2. Linux Storage Backend Decommissioning:
   - Once data parity is verified at 100%, connect to the Linux Head Node (192.168.8.224 / 100.101.39.98).
   - Safely stop and disable the legacy storage containers: `samba_nas_gateway`, `lauburu_nfs_core`, `nas-minio`.
   - Safely stop legacy Linux SeaweedFS daemons (`weed mount`, `weed filer`, `weed volume`, `weed master`) and unmount mergerfs.
3. Linux RAM Reclaim Verification:
   - Inspect Linux Head Node memory before and after teardown (`free -m`, `vmstat`, `ps aux --sort=-%mem`).
   - Confirm that ~3.5GB of RAM has been reclaimed and is now available for local AI inference.

Write your handoff report with exact command logs, memory tables, and parity reports to:
/Volumes/nas-1/Lauburu-Monorepo/.agents/worker_m3_m4/handoff.md
Send a completion message back to orchestrator when finished.
