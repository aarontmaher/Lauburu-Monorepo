# Plan: Shizuku Capability Research, Tri-Orchestrator AI Debate, Pixel Diagnostics & LoRA Memory Logging

## Step 1: Pre-Flight & Survey Phase
- Spawn 3 Explorers in parallel:
  - Explorer 1 (Shizuku Internals & API Architecture): Deep dive into Shizuku AIDL/Binder IPC, UserService, hidden APIs, AppOpsManager, PackageManager, privileged shell execution (`shizuku-api`, `rikka.shizuku`), and differences vs classic `adb shell` / root (Magisk/KernelSU).
  - Explorer 2 (Lauburu Subsystem Integration Points): Analyze where Shizuku fits in Lauburu (`01_apps/OpenClaw` automated UI test audits, Termux background daemon lifecycle, battery optimization whitelisting, Movesense BLE foreground persistence, network routing).
  - Explorer 3 (Pixel Diagnostics & Network Probe Architecture): Inspect current mesh ADB transport setup (`06_scripts_and_tooling/`), Tailscale routing to Pixel 10 Pro XL (`100.73.38.87`), ADB wireless debugging ephemeral port vs standard port 5555, and diagnostic command harness.

## Step 2: Tri-Orchestrator AI Debate Execution (M2) & Pixel Network Diagnostics (M3)
- Dispatch Worker(s) / Debate Specialists:
  - Worker 1: Execute Tri-Orchestrator Live Agent Debate Protocol (Gemini 3.1 Pro, Gemini 3.7 Flash, Kimi Tandem, Qwen 3.8max perspectives) on Shizuku integration strategies. Produce complete multi-round transcript with at least 3 concrete capabilities and integration pathways.
  - Worker 2: Execute live zero-mock network diagnostics against Pixel 10 Pro XL (`100.73.38.87`) - ping, port scans (5555, wireless debugging range 30000-45000), ADB connect attempts, diagnose connection refusal root cause, verify wireless vs USB override requirement.

## Step 3: Swarm Memory Logging & LoRA Dataset Serialization (M4)
- Worker: Serialize debate transcript, architectural decisions, and diagnostic telemetry into structured JSONL fine-tuning pairs in `/Users/aaron/DFS_UNIFIED/lora_datasets/` (e.g. `truth_audit_shizuku_debate_2026.jsonl`).

## Step 4: Verification & Gating (Reviewers, Challengers, Forensic Auditor)
- Dispatch Reviewers to evaluate debate completeness, technical accuracy of Shizuku Binder/UserService APIs, and integration proposals.
- Dispatch Challengers to stress-test the diagnostic findings and integration assumptions.
- Dispatch Forensic Auditor (`teamwork_preview_auditor`) to verify zero-mock integrity, real terminal command execution, and authentic LoRA dataset entries.

## Step 5: Final Synthesis & Parent Reporting
- Aggregate all reports into unified deliverables.
- Send completion message to parent orchestrator (`79f0e5f0-876d-4cd6-9531-7d89b97a54f0`).
