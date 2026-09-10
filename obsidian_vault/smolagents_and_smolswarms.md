---
title: "SmolAgents & SmolSwarms (Local AI Training Games)"
updated: "2026-08-26T12:00:00Z"
tags: [smolagents, smolswarms, rl, trl, training, elo, huggingface]
---

# 🤖 SmolAgents & SmolSwarms

This registry defines the specialist `smolagents` and the composite `smolswarms` that compete on the `localhost:3000` training module.

## The HuggingFace Reward System
All agents and swarms are evaluated using a continuous Reinforcement Learning from Human Feedback (RLHF) and Direct Preference Optimization (DPO) loop via **HuggingFace TRL**. 
The `localhost:3000` game engine tracks an **ELO rating** for every model and swarm configuration.
- **Reward Function:** +10 points for zero-mock truth audits, +5 for latency < 100ms, -50 for hallucinations or false positives.
- **Continuous Update (DPO Pipeline):** Instead of just running overnight, the DPO pipeline executes on a **dynamic high-frequency loop**. Initially, it runs extremely frequently (e.g., every hour or after every X completed games) to rapidly adapt the base models. As the models stabilize and the ELO plateaus, the pipeline auto-scales into a continuous 24/7 background loop. The top-performing base models (e.g., Qwen 2.5 0.5B, DeepSeek 1.5B) are continuously fine-tuned (PEFT/LoRA) using the highest ELO outputs against the rejected hallucinations.

## 1. Specialist SmolAgents
Hyper-focused, small-parameter local models (< 3B) competing for specific roles:
- **`SyntaxFixer`**: (Qwen 2.5 Coder 0.5B, DeepSeek-R1 1.5B) - Resolves formatting and syntax.
- **`UIDetector`**: (Llama-3.2-11B-Vision, Qwen3-VL) - Detects pixel overflows, mock data.
- **`LogParser`**: (Gemma 4 Nano, Qwen 2.5 1.5B) - Parses Android ADB stack traces.
- **`CodeReviewer`**: (DeepSeek-R1 1.5B, Llama 4 Smol) - Fast logic-gate checks.

## 2. SmolSwarms (Composite Swarms)
A `smolswarm` is a dynamic group of 2-5 specialist `smolagents`. The training games actively mutate the size, model combinations, and voting weights to find the highest ELO combination.

### Examples:
- **"Speed-First" Swarm:** 3x `SyntaxFixer` + 1x `LogParser` (Majority vote). Best for linting.
- **"Zero-Hallucination Visual" Swarm:** 2x `UIDetector` + 1x `CodeReviewer` (Strict unanimous vote). Best for Swarm Truth Audits.
- **"Dynamic Mutation" Swarm:** Random sizes/models assigned by the Genetic Orchestrator to discover emergent consensus behaviors.

## 🔗 Related Notes
- [[ai-debate]] — Source of architectural consensus for this protocol.
- [[teamwork-preview]] — Translates multi-model architectures into build prompts.
