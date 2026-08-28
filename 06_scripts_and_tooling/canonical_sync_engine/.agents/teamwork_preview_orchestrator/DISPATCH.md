## 2026-08-27T07:11:24+10:00

You are the Project Orchestrator for the canonical_sync_engine project.

Your Working Directory: /Users/aaron/teamwork_projects/canonical_sync_engine/.agents/teamwork_preview_orchestrator
Project Root Directory: /Users/aaron/teamwork_projects/canonical_sync_engine
Original Request Path: /Users/aaron/teamwork_projects/canonical_sync_engine/ORIGINAL_REQUEST.md

USER REQUEST & ACCEPTANCE CRITERIA:
Build a distributed storage verification and synchronization pipeline that asserts the health of all mesh devices and synchronizes artifacts across PySpark, Obsidian, GitHub, and Google Drive to maintain a unified Canonical Source of Truth.

Working directory: `~/teamwork_projects/canonical_sync_engine`
Integrity mode: benchmark

Requirements:
1. R1. Mesh Storage Verification: Implement a verification mechanism that scans the active mesh nodes to confirm their storage is accurate and healthy. (e.g., schema checks, hashing, or AI audits per canonical rules).
2. R2. Quad-Vault Synchronization: Build a multi-target synchronization engine that actively mirrors verified data across the four canonical sources of truth: PySpark (Data Lake), Obsidian (Knowledge Graph), GitHub (Source Code), and Google Drive (Cloud Backup).
3. R3. Infrastructure Controls: Leverage existing local infrastructure for cloud syncing (e.g., native Google Drive mount at `/Volumes/Google Drive/My Drive` or `gdrive_handler.py`, and the local `gh` CLI for GitHub) to prevent raw API credential leakage.

Acceptance Criteria:
- Automated test script (`test_sync_pipeline.py` or similar).
- Test script injects a dummy "truth artifact" into a local node.
- Test script executes the synchronization pipeline.
- Test script programmatically asserts (returns exit code 0) that the dummy artifact successfully propagated to the PySpark dataset directory, the Obsidian vault, the Git working tree, and the Google Drive mount.

Remember to maintain your BRIEFING.md, plan.md, and progress.md in your working directory. Coordinate your team and report back when completed.
