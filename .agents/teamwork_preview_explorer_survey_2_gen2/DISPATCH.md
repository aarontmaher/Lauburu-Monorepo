## 2026-08-24T12:19:18Z

<USER_REQUEST>
You are Explorer 2 (Generation 2 replacement) for the Lauburu Monorepo Compute Hub Pruning & Pixel Ingestion project.
Your working directory is: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/teamwork_preview_explorer_survey_2_gen2
Repository root: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo

MANDATORY FIRST STEP: Read the authoritative user request at:
/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/ORIGINAL_REQUEST.md

Your Survey Objective (R2 & R3 Focus: Compute Hub Bloat Pruning & Pixel Movesense Ingestion/Local Storage):
1. Investigate `lauburu_compute_hub` (Android / Flutter / Kotlin / Gradle project located in the monorepo, e.g. in `01_apps/` or Android directories).
2. Codebase Bloat Audit (R3): Find all usages of `fl_chart`, any other charting/plotting libraries, legacy UI tabs/dashboards, and non-Movesense/Polar deprecated sensor drivers. Document every file and line that must be stripped.
3. Gradle Build Assessment: Inspect `build.gradle`, `build.gradle.kts`, `pubspec.yaml` (if Flutter), dependencies, SDK versions, and determine what is needed for `./gradlew assembleDebug` to compile cleanly and rapidly.
4. Movesense & Polar H10 Ingestion (R2): Audit current 128Hz BLE ingestion logic (MDS / Movesense .aar / Polar BLE SDK / BluetoothGatt).
5. Pixel Local Persistence (R2): Audit local storage implementation on Pixel (SQLite database or structured JSONL ledgers in app private storage `/data/data/...` or external files directory). Detail how raw and processed timestamped data payloads should be persisted locally with zero-loss for offline/sync.
6. WebRTC / WebSocket Forwarding (R3): Audit how the lean compute hub forwards the live BLE stream to Port 4000 hub.

Write a complete, structured report to /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/teamwork_preview_explorer_survey_2_gen2/handoff.md covering:
- Executive Summary
- Inventory of Bloat to Prune (files, dependencies like `fl_chart`, UI tabs, legacy sensors)
- Current & Proposed Android / Compute Hub Architecture
- Movesense 128Hz & Polar H10 BLE Pipeline Architecture
- Pixel Local Storage Design (SQLite/JSONL schema, storage paths, sync protocol)
- Port 4000 Forwarding Pipeline (WebRTC/WebSocket client)
- Gradle Build Verification Strategy (`./gradlew assembleDebug`)
- Concrete Implementation Steps for Milestone Workers

When finished, write handoff.md and send a completion message with the path.
</USER_REQUEST>
