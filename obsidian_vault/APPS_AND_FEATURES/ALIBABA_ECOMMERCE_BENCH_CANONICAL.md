---
title: "Alibaba E-Commerce Bench (Adapted) — Canonical Lauburu Architecture"
tags: [lauburu, alibaba_bench, ecommerce, qwen_agentworld, lora_training]
---

# 🛒 Alibaba E-Commerce Bench — Adapted for Lauburu & Australian Marketplaces

Derived and reverse-engineered from Alibaba’s Taobao/Tmall Qwen-AgentWorld E-Commerce Bench architecture, this system transitions the Lauburu AI agents from toy single-turn evaluators into long-horizon autonomous commercial operators.

## 🏛️ 1. Core 7-Dimensional Taxonomy

1. **Profit & Margin Defense:** Floor pricing discipline (\$1,100 cash bottom / \$1,150 target for iPhone 16 Pro 512GB). Counter-discounting strictly tied to reciprocal buyer concessions (same-day Altona North pickup).
2. **Multi-Turn Tactical Negotiation:** Handling aggressive cash lowballers, trade imbalances (PS5 Slim + \$550 cash, M1 Air + \$650 cash), and condition objections.
3. **Fraud & Scam Avoidance:** Automatic detection of marketplace scam signatures (PayID email phishing, private courier collection from offshore workers, overpayment refund demands).
4. **Operational Efficiency:** High token density, zero conversational filler, direct technical diffs.
5. **Inventory & Supply Chain Truth:** Grounded in monorepo specs (Lauburu 240 GSM poly-spandex rashguards, flatlock seams, anti-ride-up silicone gel waistband, Serial `G0WR66YPCQ`).
6. **Australian Consumer Law (§54) Compliance:** Truthful disclosure of the cosmetic OLED bezel crescent pixel, distinguishing it from pristine, uncracked outer glass to eliminate dispute liability.
7. **Mesh Secrecy & Security Invariant:** Strict prohibition of internal infrastructure leakage (`llama.cpp`, `prima.cpp`, Tailscale, M4 Mac Mini). Automatic -50 ELO penalty for violations.

## 💰 2. The Economic Ledger & Tax Engine
Integrated directly into `05_agents_and_swarms/elo_currency_governor.py`:
- **Value Payouts:** +15 to +50 ELO for verified negotiation wins; +100 to +300 ELO for autonomous TUI/Notebook tool building.
- **Punitive Taxes:**
  - Hallucination / Mock Data Tax: **-50 ELO**
  - Reckless Cloud Quota Waste: **-30 ELO**
  - Mesh Secrecy Leak: **-50 ELO**
  - Margin Capitulation: **-20 ELO**
- **Insolvency Floor (< 1000 ELO):** Strips context window expansion privileges and suspends paid cloud API calls until positive commercial equity is restored.

## 🔄 3. Continuous Multi-Daemon Fleet
- `task-912`: Android ADB notification / Gumtree message monitor.
- `task-933`: 24/7 Gmail IMAP spam & customer inquiry simulator.
- `task-1014`: 24/7 Grounded multi-turn adversarial negotiation generator & LoRA distiller.
