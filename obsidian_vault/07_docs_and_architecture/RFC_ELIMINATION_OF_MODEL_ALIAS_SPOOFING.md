---
title: 'RFC: Elimination of Model Alias Spoofing & Explicit Model Differentiation'
date: '2026-09-12'
tags: [zero_mock, rule_0, qwen, llama_server, prima_cpp]
---

# 🛡️ RFC: Elimination of Model Alias Spoofing & Explicit Model Differentiation

## 1. Issue Identified (Rule 0 & Truth Invariant Breach)
In previous configuration,  launched:
- Binary: 
- Target Model:  (7.6 Billion Parameters, 4.4 GB)
- **Breach**: Passed , deceptively masquerading a 7B model as the 27B  model.

## 2. Canonical Resolution
1. **Launchd Job Updated**:
   -  purged of fake alias.
   - Set true model alias: .
   - Constrained to  to eliminate multi-slot Metal GPU memory exhaustion.
2. **Prima Coordinator Catalog Updated**:
   -  now explicitly differentiates:
     -  (4.4 GB, Port 8083, local Metal)
     -  (16.0 GB, Port 8085 / TB4 sharded)
     -  (Sovereign PRP Ring Coordinator, Port 8082)
3. **TUI & Screen Lens Telemetry Updated**:
   -  explicitly lists Port 8083 as .
   - Deployed bit-for-bit to Linux Mini ().
