---
title: "Jupyter, Marimo, & Voila: Lens Dashboard Integration"
tags: [voila, jupyter, marimo, dashboards, screen_lens]
date: "2026-09-15"
---

# 📊 Notebook Ecosystem Analysis & Voila Integration

## 1. The Current State of Notebooks in the Lauburu Mesh
Rule 10 (Linux Mini First-Offload) and the Notebook Specialist skill mandate that JupyterLab and Marimo instances be offloaded to the L3 Linux Head Node (`100.101.39.98`). Currently, notebooks are used internally for prototyping DSP filters (Pan-Tompkins) and visualizing LoRA dataset loss curves.

## 2. Voila Deep Dive & Mechanism
**Voila** takes a standard `.ipynb` file, executes the kernel in the background (headless), and renders *only* the outputs (Plots, Markdown, IPyWidgets) via a Tornado web server. 
*   **Security:** Prevents arbitrary code execution by hiding the input cells.
*   **Reactivity:** IPyWidgets (like sliders for DSP thresholds) remain fully interactive because Voila maintains a live WebSocket connection to the Jupyter kernel.

## 3. Screen Lens Integration Plan
Screen Lens currently lacks a unified visual GUI for its storage audits, swarm token costs, and mesh topology ping results. Rather than building a React/Next.js dashboard from scratch (which is overkill), Lens will use Voila.

### The "Lens Sovereign Dashboard"
1. **Authoring:** The local Orchestrator will write an automated `lens_telemetry.ipynb` notebook using `nbformat`. This notebook will pull data from `screen_lens_storage_audit_v2.json` and the OpenRouter cost logs.
2. **Serving (Voila Daemon):** Lens will launch a background daemon on the Linux Node:
   `voila /mnt/dfs_unified/Lauburu-Monorepo/04_data_and_memory/lens_telemetry.ipynb --no-browser --port 4005`
3. **Integration:** The Voila dashboard will be iframe-embedded into the `01_apps/` Port 4000 Hub, giving Aaron a live, read-only, interactive dashboard of the mesh's health, AI token spend, and SeaweedFS volume capacity.

## 4. Why Marimo? (The Modern Alternative)
While Voila is standard for Jupyter, **Marimo** is a reactive Python notebook built for the modern AI stack. Marimo executes as a DAG (Directed Acyclic Graph), meaning when one widget changes, only dependent cells re-run.
*   **Recommendation:** Lens should default to Marimo (`marimo run lens_dashboard.py`) for the L3 Linux Hub, as it consumes significantly less RAM than a standard Jupyter + Voila Tornado stack, perfectly aligning with Rule 10 VRAM sparing.
