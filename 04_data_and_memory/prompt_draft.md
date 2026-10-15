# Teamwork Project Prompt — Draft

> Status: Step 2 — Ready for Launch & Awaiting Aaron's Approval
> Goal: Multi-agent execution of Lauburu Storage Pooling & ELO Verification
> Requested team: Full multi-agent team across 7 physical mesh layers

The Lauburu Mesh Ecosystem requires autonomous synchronization, continuous ELO auditing, and native C11 storage pooling across its 7 physical layers, pooling 1,085 GB of storage and 82.8 GB usable AI VRAM under strict Zero-Mock enforcement.

Working directory: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo
Integrity mode: development

## Requirements

### R1. Sovereign Storage Pooling & Consistent Hash Ring
Implement and verify native C11 consistent hash storage pooling (`lauburu_pooled_storage.c`) across the 7 mesh layers, enforcing 64KB chunk slicing, Fletcher32 checksums, and sub-millisecond reassembly.

### R2. Canonical Read-Only Storage Context Map Governance
Maintain `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/07_docs_and_architecture/STORAGE_ARCHITECTURE_CONTEXT_MAP.md` in strict read-only mode until formal consensus from Cloud Shadow Orchestrators (Gemini 3.8 Flash High) is reached.

### R3. Project-Specific ELO & Confidence Evaluation Engine
Continuously update mathematical Bradley-Terry ELO ratings (1000–3000) and empirical confidence intervals ($C \in [0.0, 1.0]$) across frontend surfaces, backend C11 systems, and AI models.

## Acceptance Criteria

### Storage Integrity & Performance
- [ ] 1.0 MB payload dispersed and reassembled with 100% bit-for-bit SHA256 match.
- [ ] Dispersal latency $\le 2.0\text{ ms}$ and reassembly latency $\le 0.5\text{ ms}$ in native C11.
- [ ] Fletcher32 bitrot detection verifies zero corrupted blocks.

### ELO Engine Precision
- [ ] ELO scorecard evaluates across 3 categories (Frontend, Backend, AI Models) in $\le 50\ \mu\text{s}$.
- [ ] Confidence intervals mathematically calculated for all qualitative components without raw physical sensors.

---
*Next: when approved → delegate via invoke_subagent(TypeName='teamwork_preview')*
