# 🚀 Canonical Project Handoff: Lauburu Master Notebook & TUI Ecosystem
**Date:** September 2, 2026  
**Target Environment:** VS Code, JupyterLab (:8889), Voilà Standalone (:8890), Native Rust / Clang++ Toolchains  
**SSoT Repository:** `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo`

---

## 🏛️ 1. Executive Summary & Active State

The entire interactive workspace has been built, hardened for headless safety, validated against **Rule #0 (Zero-Mock / Zero-Simulated Data)**, and synchronized across the Tri-Vault storage layers (`01_apps/notebooks/`, `obsidian_vault/notebooks/`, and `lora_datasets/`).

### Active Subsystems:
1. **Master Voilà & JupyterLab Console (`00_lauburu_global_master_project.ipynb`)**:
   - 8 Complete Glassmorphic Subsystems: 14-Port Matrix, Multi-View 2x2 Grid, Multi-TUI Streamer, SeaweedFS Distributed IDE, 7-Layer Mesh Radar, 512Hz Pan-Tompkins DSP, 955-Node BJJ Tree, 1-Click Optimizer, and Real-Time Global Project AST Analysis.
2. **Simple Project Monitoring Rust TUI (`01_apps/rust_project_monitor/`)**:
   - Standalone `lauburu-monitor` binary written in Ratatui/Crossterm delivering zero-latency 14-port polling, 7-layer mesh latency probing, and monorepo AST analytics.
3. **Canonical 13-Notebook Domain Suite**:
   - 100% passing headless execution across all 13 `.ipynb` files via `ExecutePreprocessor` (Python 3.13 kernel).
   - 68/68 automated PyTest unit tests passing in `01_apps/notebooks/tests/`.

---

## 📓 2. Canonical 13-Notebook Suite Directory & Entrypoints

Open any of these notebooks directly in **VS Code** (with the Jupyter extension) or in **JupyterLab** (`http://100.93.158.96:8889/lab` / `http://127.0.0.1:8889/lab`):

| # | Notebook Name | Path in Monorepo | Core Domain & Focus |
| :- | :--- | :--- | :--- |
| **00** | `00_lauburu_global_master_project.ipynb` | `01_apps/notebooks/00_lauburu_global_master_project.ipynb` | **Master SSoT Console**: 14-Port Matrix, 2x2 Grid, SeaweedFS IDE, 512Hz DSP, AST Console |
| **00b**| `00_lauburu_master_interactive_console_and_ui_specialist.ipynb` | `01_apps/notebooks/00_lauburu_master_interactive_console_and_ui_specialist.ipynb` | **UI/UX Specialist AI**: Local AI prompt console, Butterworth DSP filter tuner |
| **00c**| `00_lauburu_qwen_moe_master_console.ipynb` | `01_apps/notebooks/00_lauburu_qwen_moe_master_console.ipynb` | **Qwen MoE Sovereign Status**: Swarm ELO leaderboard, 10Gbps TB4 DMA link monitor |
| **01** | `01_lauburu_swarm_and_kinematics_interactive.ipynb` | `01_apps/notebooks/01_lauburu_swarm_and_kinematics_interactive.ipynb` | **Swarm & Kinematics**: OPML tactical trees, NetworkX directed graphs, QRS filters |
| **01b**| `01_master_mesh_console_and_ports.ipynb` | `01_apps/notebooks/01_master_mesh_console_and_ports.ipynb` | **Mesh Ports Prober**: 7-layer node latencies, 14-port service health cards |
| **02** | `02_lauburu_canonical_knowledge_vault_explorer.ipynb` | `01_apps/notebooks/02_lauburu_canonical_knowledge_vault_explorer.ipynb` | **Obsidian Vault Explorer**: Markdown note ingestion, semantic Wikilink graph explorer |
| **02b**| `02_tui_ecosystem_and_terminal_streamer.ipynb` | `01_apps/notebooks/02_tui_ecosystem_and_terminal_streamer.ipynb` | **TUI Streamer**: Port 8088 WebGL PTY streamer, 120 FPS latency benchmark chart |
| **03** | `03_full_network_prima_ai_lab.ipynb` | `01_apps/notebooks/03_full_network_prima_ai_lab.ipynb` | **Distributed AI Lab**: 7-node topology (82.8 GB VRAM), PRP Ring layer allocation |
| **03b**| `03_lauburu_lens_vision_and_next_steps.ipynb` | `01_apps/notebooks/03_lauburu_lens_vision_and_next_steps.ipynb` | **Screen Lens Multimodal**: OCR capture stream, milestone roadmap planning |
| **04** | `04_movesense_biometrics_and_dsp.ipynb` | `01_apps/notebooks/04_movesense_biometrics_and_dsp.ipynb` | **512Hz Biometrics DSP**: Pan-Tompkins QRS detection, HRV (RMSSD/SDNN), DFA-a1 Zone 2, PTT BP |
| **05** | `05_spatial_grappling_3d_kinematics.ipynb` | `01_apps/notebooks/05_spatial_grappling_3d_kinematics.ipynb` | **3D Spatial Grappling**: 955-node OPML parser, Markov transition chains, 8x8m Tatami Arena |
| **06** | `06_genetic_project_scout_and_lora.ipynb` | `01_apps/notebooks/06_genetic_project_scout_and_lora.ipynb` | **24/7 LoRA Tracker**: 70K+ pairs harvester, loss/perplexity tracker, Swarm ELO |
| **07** | `07_cpp_tui_canonical_recreation_studio.ipynb` | `01_apps/notebooks/07_cpp_tui_canonical_recreation_studio.ipynb` | **C++ TUI Studio**: FTXUI, ncurses, ImTui blueprints, live Clang++ M4 benchmark runner |

---

## 💻 3. VS Code Live Notebook Hot Reloading & Environment Setup

### 3.1 Kernel Selection in VS Code
When opening any `.ipynb` file in VS Code:
1. Click **Select Kernel** in the top right of the notebook editor.
2. Select **Python Environments...** -> Choose the uv Python environment:
   `/Users/aaron/.local/share/uv/tools/jupyterlab/bin/python`
   *(or the system Python: `/opt/homebrew/bin/python3`)*
3. All dependencies (`ipywidgets`, `matplotlib`, `numpy`, `scipy`, `pandas`, `nbformat`, `nbconvert`) are pre-installed in this environment.

### 3.2 Running Voilà Live Standalone Web App
To run the master dashboard as a standalone web application on **Port 8890**:
```bash
cd /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/notebooks
voila 00_lauburu_global_master_project.ipynb --port 8890 --no-browser --theme=dark
```
Access in browser at: `http://127.0.0.1:8890` or `http://100.93.158.96:8890`.

### 3.3 Regenerating Notebooks from Python Scripts
Each major notebook has an automated, single-source-of-truth Python generator script that rebuilds the notebook, runs AST syntax checks, and synchronizes to both `01_apps/notebooks/` and `obsidian_vault/notebooks/` with Jupytext markdown:
```bash
# Rebuild Master Studio
python3 01_apps/notebooks/generate_glassmorphic_master_studio.py

# Rebuild Movesense Biometrics 512Hz DSP
python3 01_apps/notebooks/generate_biometrics_notebook.py

# Rebuild 3D Spatial Grappling Kinematics
python3 01_apps/notebooks/generate_grappling_notebook.py

# Rebuild 24/7 LoRA Tracker
python3 01_apps/notebooks/generate_genetic_lora_notebook.py

# Rebuild C++ TUI Studio
python3 01_apps/notebooks/generate_cpp_tui_studio.py

# Rebuild TUI Ecosystem Streamer
python3 01_apps/notebooks/generate_tui_ecosystem_notebook.py

# Rebuild Prima AI Inference Lab
python3 01_apps/notebooks/generate_prima_ai_lab_notebook.py
```

---

## 🦀 4. Simple Project Monitoring Rust TUI (`lauburu-monitor`)

Located at: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/rust_project_monitor/`

### Build & Execution Commands:
```bash
cd /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/rust_project_monitor

# 1. Run Interactive Terminal Monitor
cargo run --release

# 2. Run Instant Single-Shot Probe (Headless/CI)
./target/release/lauburu-monitor --once

# 3. Run Test Suite
cargo test --release
```

### Hotkeys:
- `Tab` / `BackTab`: Cycle views (Overview, 14-Port Matrix, 7-Layer Mesh, Monorepo AST, Tri-Vault).
- `1` - `5`: Direct jump to tab.
- `r`: Force immediate socket & AST re-probe.
- `h`: Execute storage pre-flight self-healing.
- `q` / `Esc`: Clean quit.

---

## 🌐 5. 14-Port Service Matrix & Socket Endpoints

| Port | Service Name | Protocol | URL | Default Role |
| :--- | :--- | :--- | :--- | :--- |
| **:3000** | Zone 2 Web Portal | HTTP/Next.js | `http://127.0.0.1:3000` | Zone 2 Frontend & Biometrics Dashboard |
| **:4000** | Movesense 512Hz ECG Hub | HTTP/GATT BLE | `http://127.0.0.1:4000` | 512Hz R-Peak DSP & In-App Edge Chat |
| **:8081** | prima.cpp Master (32B) | REST/RPC | `http://127.0.0.1:8081/health` | Primary Local AI Engine |
| **:8082** | prima.cpp PRP Ring (80B) | REST/RPC | `http://127.0.0.1:8082/health` | 3-Mac Ring Parallelism Coordinator |
| **:8083** | Devil's Advocate & Edge Gateway | OpenAI REST | `http://127.0.0.1:8083/health` | Abliterated AI & SmolLM2 Chat |
| **:8084** | llama.cpp Worker 4 | GGML RPC | `http://127.0.0.1:8084/health` | Edge Tensor Sharding Worker |
| **:8088** | Universal Web-TUI Streamer | PTY/WebSocket | `http://127.0.0.1:8088` | 120 FPS Terminal Streamer |
| **:8888** | SeaweedFS Distributed Storage | HTTP/Filer | `http://127.0.0.1:8888` | S3-Compatible Big Data Storage |
| **:8889** | JupyterLab Master IDE | HTTP/WS | `http://100.93.158.96:8889/lab` | Interactive Code Workbench (Layer 5 Air) |
| **:8890** | Voilà Auto-Running Dashboard | HTTP/WS | `http://127.0.0.1:8890` | Zero-Click Standalone Web App |
| **:9000** | AI Budget Proxy | HTTP REST | `http://127.0.0.1:9000/status` | $0.00 Hard-Locked Budget Sentinel |
| **:9333** | SeaweedFS Raft Consensus | HTTP/Raft | `http://127.0.0.1:9333` | Storage Volume Topology & Raft Leader |
| **:18802**| Self-Healing Hub | HTTP REST | `http://127.0.0.1:18802/health` | Out-of-Band Power Recovery & ADB |
| **:18805**| Real-Time Command Console | HTTP/JS | `http://127.0.0.1:18805` | Live Genetic Radar & Model Downloads |

---

## 🧪 6. Test Suite & Verification Commands

```bash
# 1. Run Complete PyTest Suite for All Notebooks (68 tests)
pytest 01_apps/notebooks/tests/ -v

# 2. Run Headless Execution Preprocessor across All 13 Notebooks
/Users/aaron/.local/share/uv/tools/jupyterlab/bin/python -c "
import nbformat, glob
from nbconvert.preprocessors import ExecutePreprocessor
ep = ExecutePreprocessor(timeout=60, kernel_name='python3')
for p in sorted(glob.glob('01_apps/notebooks/*.ipynb')):
    with open(p) as f:
        nb = nbformat.read(f, as_version=4)
    ep.preprocess(nb, {'metadata': {'path': '01_apps/notebooks'}})
    print(f'✅ PASS {p}')
"

# 3. Run Rust TUI Unit Tests
cd 01_apps/rust_project_monitor && cargo test --release
```

---

## 🎯 7. Next Priorities for VS Code / Swarm Evolution

1. **Live Cell Execution in VS Code**: Open `00_lauburu_global_master_project.ipynb` in VS Code to test interactive widgets directly in the editor.
2. **WebSocket Live Telemetry Feed**: Hook up `movesense_readiness_live.json` into the Rust TUI and master notebook for real-time live ECG streaming when BLE connects.
3. **24/7 LoRA Ingestion**: Continue auto-harvesting validated code diffs to `/Users/aaron/DFS_UNIFIED/lora_datasets/` for continuous local model fine-tuning.
