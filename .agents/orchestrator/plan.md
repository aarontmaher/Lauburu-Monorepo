# Master Project Plan: 24/7 Offline & Free-Tier AI Utilization Cron Pipeline

## Overview
This project deploys a continuous 24/7 offline and free-tier AI utilization cron pipeline across the 7-node physical mesh to maximize zero-cost AI model distillation, AST code optimization, and autonomic self-healing.

## Phases
1. **Phase 0: Comprehensive Survey & Codebase Exploration**
   - Survey Existing Daemons, Ports (8080-8086, 18802, 50052, 8088), Services, and Cron Hooks across monorepo.
   - Survey LoRA dataset harvesting pipelines, TRL/PEFT scripts, and PySpark Lake.
   - Survey Tri-Vault storage state (Obsidian, PySpark, Git) and router/airgapping telemetry.
   - Output: Consolidated Feature Inventory and Architecture Map in `PROJECT.md`.

2. **Phase 1: Architecture & Milestone Decomposition**
   - Milestone 1 (M1): Free-Tier AI Scheduling, Quota Governance & Airgapped Rate Limiter (Gemini 2.5 Flash, Cloudflare Workers AI, Local Mesh Ports 8081-8086, zero 429 errors).
   - Milestone 2 (M2): Continuous Multi-Model LoRA Dataset Harvesting & Nightly Metal GPU Training Pipeline (DPO/RLHF, >=500 pairs/day, Obsidian loss curve logging).
   - Milestone 3 (M3): Tri-Vault Storage Auto-Healing, Daemon Supervision & Mesh Hardware Health (Obsidian, PySpark, Git, Ports resurrection, GL-MT3600BE RAM <=35MB).
   - Parallel Track: Opaque-Box E2E Testing Track (Tiers 1-4).

3. **Phase 2: Milestone Execution via Sub-Orchestration / Iteration Loops**
   - Execute M1, M2, M3 in parallel/dependency order with Explorer -> Worker -> Reviewer -> Challenger -> Auditor gates.
   - Execute E2E Testing Track to publish `TEST_READY.md`.

4. **Phase 3: E2E Verification & Adversarial Hardening**
   - Final Milestone: Pass 100% E2E tests (Tiers 1-4).
   - Adversarial Hardening (Tier 5): Challenger-driven gap analysis & adversarial tests.

5. **Phase 4: Synthesis & Victory Reporting**
   - Final audit verification and notification to Sentinel.
