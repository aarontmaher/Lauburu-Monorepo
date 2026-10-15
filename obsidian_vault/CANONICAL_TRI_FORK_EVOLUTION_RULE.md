---
title: "Canonical Tri-Fork Evolution Rule & AI Competency Lifecycle"
tags: [canonical_rule, ai_evolution, tri_fork, model_competency, lifecycle]
date: "2026-09-11"
---

# 🔱 The Canonical Tri-Fork Evolution Rule

This document enshrines a core project-wide mandate regarding the lifecycle and evolution of competent AI models within the Lauburu Mesh Ecosystem.

## 1. The Core Mandate: Never Discard a Competent Model
**Never get rid of a model once it has proven competent in a specific task, unless it is replaced by an improved version of the EXACT SAME size.** 
If a model successfully completes its hyper-niche objective (e.g., controlling a router, parsing an AST, forecasting an ECG), it is locked into the architecture. It cannot be arbitrarily pruned just because a larger model exists. 

## 2. The Tri-Fork Development Protocol
Any time an AI model is proven competent at a task, its development MUST immediately fork into three parallel, continuous streams:

1. **Make it Smaller & Just as Competent (Distillation & Pruning):**
   - Goal: Reduce the parameter count (e.g., from 10M to 5M, or 1M to 500K).
   - Method: Knowledge Distillation, Genetic MoE parameter pruning, sparsity forcing.
   - Success Metric: Matches the baseline accuracy while consuming less RAM and computing faster.

2. **Keep it the Same Size & Make it More Competent (In-Place Optimization):**
   - Goal: Squeeze more reasoning density into the exact same parameter footprint.
   - Method: Continuous LoRA datasets, higher quality DPO (Direct Preference Optimization) pairs, hyperparameter mutation (learning rate, tau, K).
   - Success Metric: Higher pass@1 rate, better edge-case handling without increasing RAM footprint.

3. **Make it Slightly & Progressively Larger & More Competent (Scaling Up):**
   - Goal: Introduce a slightly larger sibling model to handle the task with vastly superior reasoning capabilities.
   - Method: Scale dimensions (e.g., $d\_{model}$, $n\_{layers}$).
   - Success Metric: Achieves near-perfect or AGI-like reliability for that specific task domain, establishing a new ceiling for what is possible.

## 3. Implementation in the Mesh
This Tri-Fork rule drives the 24/7 Genetic MoE engine. When a micro-model like the 1M Router Classifier proves its competence on the GL.iNet router, the Genetic Engine will automatically spawn three child containers:
- A 500K variant.
- A newly-seeded 1M variant with harder dataset examples.
- A 2.5M variant.

This philosophy guarantees that the ecosystem continuously optimizes for the absolute minimum footprint required per task, whilst simultaneously pushing the boundary of maximum competence.
