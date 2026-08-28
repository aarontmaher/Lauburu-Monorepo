---
title: "Sub-Project: /teamwork-preview (Multi-Agent Teamwork Orchestration)"
updated: "2026-08-24T10:44:04Z"
tags: [sub_project, teamwork_preview, multi_agent, verification, prompt_draft]
---

# 👥 Sub-Project: `/teamwork-preview`

The **Teamwork Preview System** crafts robust, objectively verifiable multi-agent prompts and coordinates specialized subagent teams (full teams, proof pipelines, small focused units) across the monorepo.

## 🎯 Core Principles
1. **Specify What, Not How:** Focus on requirements and acceptance criteria; let agent teams discover optimal architectures.
2. **Objective Verification:** Require independent programmatic tests or agent-as-judge rubrics before self-certification.
3. **Acceptance Criteria as Guardrails:** Prevent premature completion and enforce iterative build $\rightarrow$ test $\rightarrow$ debug loops.

## 🔗 Related Notes
- [[ai-debate]] — Supplies strategic priorities into teamwork prompts.
- [[swarm]] — Physical and containerized execution substrate running teamwork subagents.
- [[device-hardware-governor]] — Allocates dynamic hardware resources to prevent system lag during multi-agent team runs.
