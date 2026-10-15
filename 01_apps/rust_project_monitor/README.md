# 🦀 Lauburu Simple Project Monitor TUI (`lauburu-monitor`)

A lightweight, zero-latency immediate-mode terminal user interface (TUI) written in Rust using [Ratatui](https://github.com/ratatui-org/ratatui) and [Crossterm](https://github.com/crossterm-rs/crossterm).

---

## ⚡ Key Features

1. **7-Layer Physical Mesh Radar**:
   - Real-time TCP connect probes across all 7 hardware layers (`L1` Mac Mini Host, `L2` MacBook Pro TB4, `L3` Linux Head Node, `L4` Linux Tablet, `L5` MacBook Air, `L6` Pixel 10 Pro XL, `L7` Samsung S20+, `GW` GL.iNet Router).
   - Real millisecond RTT latency tracking and 82.8 GB Pooled VRAM headroom monitor.

2. **Sovereign 14-Port Gateway Matrix**:
   - Live socket status for all 14 monorepo ports (`:3000`, `:4000`, `:8081`, `:8082`, `:8083`, `:8084`, `:8088`, `:8888`, `:8889`, `:8890`, `:9000`, `:9333`, `:18802`, `:18805`).

3. **10-Subsystem Monorepo AST Metrics**:
   - Fast file and line-of-code (LOC) metrics across `00_core_infrastructure`, `01_apps`, `02_ai_models_and_inference`, `03_biometrics_and_telemetry`, `04_data_and_memory`, `05_agents_and_swarms`, `06_scripts_and_tooling`, `07_docs_and_architecture`, `obsidian_vault`, and `teamwork_projects`.

4. **Tri-Vault Storage & 24/7 LoRA Tracker**:
   - Live verification of Obsidian knowledge graph, PySpark data lake, and GitHub tree integrity.
   - 1-click self-healing trigger (`h`) to repair missing directories or stale `.git/index.lock` files.

---

## 🚀 Building & Running

```bash
# Build release binary
cargo build --release

# Run interactive TUI
./target/release/lauburu-monitor

# Run headless self-test (instant single probe)
./target/release/lauburu-monitor --once
```

---

## ⌨️ Keyboard Navigation

| Key | Action |
| :--- | :--- |
| `Tab` / `BackTab` | Cycle through tabs (Overview, 14-Port Matrix, 7-Layer Mesh, Monorepo AST, Tri-Vault) |
| `1` - `5` | Jump directly to specific tab view |
| `r` | Trigger immediate re-probe of all network sockets and subsystems |
| `h` | Execute Tri-Vault pre-flight self-healing protocol |
| `q` / `Esc` | Quit the monitor gracefully |


## Canonical Architecture
This application adheres to [[CANONICAL_APP_UI_AND_STRUCTURE_RULE]] and uses the Astra Multimodal Live API via Screen Lens for UI evolution.
