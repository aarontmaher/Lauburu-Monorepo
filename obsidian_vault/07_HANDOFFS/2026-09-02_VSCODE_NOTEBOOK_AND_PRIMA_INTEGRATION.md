---
title: "VS Code Notebook Optimization & prima.cpp Integration"
date: "2026-09-02"
truth_audited: true
audit_swarm_engine: "antigravity_local+prima_cpp"
canonical_source: true
tags: [vscode, jupyter, notebooks, prima_cpp, optimization, extensions, lora]
---

# 🚀 VS Code Notebook Optimization & prima.cpp Studio Guide

## 1. Registered Kernels
- `🧠 Lauburu Canonical Studio (Python 3.13 - Widgets & DSP)` (`lauburu-notebooks`):
  - Path: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/notebooks/.venv/bin/python3`
  - Stack: `ipywidgets 8.1.9`, `scipy 1.18.1`, `voila 0.5.12`, `plotly 7.0.0`, `matplotlib 3.11.1`, `numpy 2.5.2`, `pandas 3.0.5`, `marimo 0.24.0`, `ruff`, `black`
- `🧠 Lauburu UV Studio (Python 3.14)` (`lauburu-uv`):
  - Path: `/Users/aaron/.local/share/uv/tools/jupyterlab/bin/python`

## 2. VS Code Configuration Suite
- `.vscode/extensions.json`: 34 curated extensions spanning Jupyter, Marimo, Ruff, local AI (OAI Copilot, LLM Gateway, Opilot, Llama-VSCode), and multi-language toolchains.
- `.vscode/settings.json`: Zero-latency execution, cell toolbars, format-on-save/execution with Ruff, widget CDN scripts, and local AI proxy endpoints (`http://127.0.0.1:8083/v1`).
- `.vscode/launch.json`: Integrated debugging for `decentralized_prima_daemon.py`, `prima_ring_adapter.py`, `hybrid_sharding_engine.py`, `voila` master console (:8890), and Rust monitor TUI.
- `.vscode/tasks.json`: 30+ automated tasks including 1-click Voilà dashboard launch, 13-notebook headless test suite, prima ring status/healing, and TUI benchmark automators.

## 3. prima.cpp VS Code Integration
- **Daemon (`:8082`)**: Mesh coordinator monitoring 7 hardware nodes & 85.0 GB pooled VRAM.
- **Proxy (`:8083`)**: OpenAI-compatible endpoint serving `qwen2.5-coder-7b-instruct-q4_k_m.gguf` with zero recurring cloud spend.
