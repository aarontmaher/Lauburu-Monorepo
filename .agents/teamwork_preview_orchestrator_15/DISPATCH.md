# Dispatch Log

## 2026-08-27T12:45:53Z
You are the Project Orchestrator for the following request.

Your metadata working directory is: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/teamwork_preview_orchestrator_15`
The user's original request is recorded in: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/ORIGINAL_REQUEST.md`
The target project working directory is: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_tui_prototypes`
Integrity mode: benchmark

# Teamwork Project Prompt

Deep research and prototyping of Terminal User Interfaces (TUIs) to determine the best framework for a canonical Lauburu Monorepo backend, prioritizing integration with the free token API cron.

Working directory: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_tui_prototypes
Integrity mode: benchmark

## Requirements

### R1. Tri-Framework Prototyping
Develop three distinct TUI prototypes that interface with the newly integrated `cloud_api_quota_manager.py` (located in `06_scripts_and_tooling/automation/cloud_api_quota_manager.py` and reading `04_data_and_memory/data/cloud_api_quota_state.json`) to display system telemetry and active API token usage:
1. Python (Textual)
2. Go (Charm/Bubble Tea)
3. Rust (Ratatui)

### R2. Termux Wireless Deployment
Use wireless debugging (ADB over TCP) and the universal SSH mesh transports to deploy these prototypes directly into the Termux environment on the mobile edge nodes (e.g., Pixel 10 Pro XL or Samsung S20+).

### R3. Automated Dependency Provisioning
The deployment process must automatically install all required toolchains and dependencies (Python, Go, Rust/Cargo) within the Termux environment via `pkg install` to ensure the TUIs compile and run natively on the edge hardware.

## Acceptance Criteria

### Execution & Verification
- [ ] Three separate, runnable TUI prototypes exist in the working directory (`01_apps/canonical_tui_prototypes/`).
- [ ] An automated deployment script successfully establishes an ADB/SSH connection to a Termux node.
- [ ] The deployment script successfully installs Python, Go, and Rust within the Termux environment without manual intervention.
- [ ] A verification script runs each TUI remotely inside Termux and confirms they launch without crashing and successfully read the `cloud_api_quota_state.json` lockfile.

Maintain your `plan.md`, `progress.md`, and `context.md` inside your working directory.
Dispatch specialists for exploration, implementation, review, and verification.
When all acceptance criteria are met, deliver your completion handoff.md report to the sentinel.

## 2026-08-27T13:01:40Z
[NEW REQUIREMENT FROM USER]
The user has provided an additional requirement for the TUI research and prototyping phase:
"Please also analyze existing advanced Textual-based apps and libraries to see how they structure their UIs and handle data. Examples provided by the user include: Posting (HTTP client), Memray (memory profiler), Toolong (log viewer), Dolphie (MySQL analytics), Harlequin (DB client), Elia (LLM interface), Trogon (CLI auto-generator), TFTUI (Terraform), RecoverPy, Frogmouth (Markdown viewer), oterm, and logmerger. Have the swarm explicitly incorporate the design patterns, widgets, and architectures of these advanced Textual apps into the Textual prototype's evaluation."

Please ensure the swarm analyzes these apps/libraries, extracts their architectural design patterns, widgets, and reactive data handling mechanisms, and incorporates this deep analysis directly into the Textual prototype evaluation and project documentation.
