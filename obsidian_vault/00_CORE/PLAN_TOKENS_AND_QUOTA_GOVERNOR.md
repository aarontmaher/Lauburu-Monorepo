---
title: "Google AI Ultra Plan & Multi-Tier Quota Governor"
date: 2026-09-04
tags: [plan_tokens, google_ultra, gemini_3_1_pro, free_tier_triage, quota_governor]
status: ACTIVE_GUARDED
---

# ⚡ Google AI Ultra Plan & Multi-Tier Quota Governor

> **Aaron's Directive:** "Monitor my plan's tokens as well and use Gemini 3.1 Pro very sparingly. Use Gemini API free tier to figure out when to use plan token usage on Gemini 3.1 Pro."

---

## 📊 1. Google AI Ultra Plan Allocation Status

| Quota Dimension | Allocation Remaining | Refresh ETA | Operating Status |
| :--- | :--- | :--- | :--- |
| **Gemini Models (Weekly Limit)** | **95.0%** | 6 days, 18 hours | 🟢 ABUNDANT HEADROOM |
| **Gemini Models (5-Hour Limit)** | **99.0%** | 4 hours, 52 minutes | 🟢 MAX HEADROOM (99%) |
| **Claude & GPT Models (Weekly)** | **0.0%** | 20 hours, 7 minutes | 🔴 EXHAUSTED COOLDOWN |
| **AI Credit Overages** | **DISABLED** | Managed Zero-Billing | 🛡️ OVERAGE COST PROTECTED |

---

## 🎯 2. Sparing Gemini 3.1 Pro Escalation Protocol

```
┌────────────────────────────────────────────────────────────────────────────────┐
│                    FREE-TIER TRIAGE & ESCALATION LADDER                        │
├────────────────────────────────────────────────────────────────────────────────┤
│ 1. TIER 0: Local Edge Model (SmolLM2-135M / Qwen 0.5B)                         │
│    • Cost: $0 | Latency: <10 ms | AST parsing, micro-triage, and formatting.   │
├────────────────────────────────────────────────────────────────────────────────┤
│ 2. TIER 1: Local Sharded Mesh (Qwen 3.8 Max 27B / TB4 Bridge)                  │
│    • Cost: $0 | Latency: <15 ms | Multi-file diffs, local code synthesis.     │
├────────────────────────────────────────────────────────────────────────────────┤
│ 3. TIER 2: Cloud Free API Triage (Gemini 2.0 / 2.5 Flash - 1,500 RPD)          │
│    • Cost: $0 | Latency: ~850 ms | Deep CoT analysis, whole-file AST review.   │
│    • AUTONOMOUS DECISION: Computes Confidence Score C in [0.0, 1.0].          │
│    • IF C >= 0.85 -> Execute directly on Free Tier / Local Mesh.               │
│    • IF C < 0.85 AND 2 prior attempts failed -> ESCALATE TO TIER 3.            │
├────────────────────────────────────────────────────────────────────────────────┤
│ 4. TIER 3: Google AI Ultra Plan Token Usage (Gemini 3.1 Pro High)              │
│    • SPARINg USE ONLY: Maximum 4,096 tokens per call.                          │
│    • Reserved for Apex Stagnation Breaking & Whole-Monorepo Architectural Deadlock│
└────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📈 3. Active Session Token Consumption
- **Active Transcript Size:** 1,553,276 bytes
- **Estimated Session Tokens:** 388,319 tokens
- **Total Conversation Turns:** 1105 steps
- **Next Global Reset:** 2026-09-04 10:00:00 AEST (Midnight UTC)
