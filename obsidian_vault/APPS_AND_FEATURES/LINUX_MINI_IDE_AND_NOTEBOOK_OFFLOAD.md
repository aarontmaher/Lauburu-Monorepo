# 🐧 Linux Mini IDE & Notebook Compute Offload Architecture

> **Canonically Governed By:**
> - [[00_canonical_hardware_matrix|Rule 0: Canonical Hardware & Port Truth]]
> - [[01_zero_mock_truth_rule|Rule 1: Zero-Mock & Empirical Truth Verification]]
> - [[02_tri_vault_storage_rule|Rule 2: Tri-Vault Storage Architecture]]
> - [[03_host_sanctuary_and_ram_governance|Rule 3: Host Sanctuary & Dynamic RAM Governance]]
> - [[10_linux_mini_first_offload_rule|Rule 10: Linux Mini First-Offload Invariant]]

---

## 1. Executive Summary & Problem Solved

Modern IDEs (JetBrains PyCharm, GoLand, VS Code) and interactive scientific compute environments (JupyterLab, Marimo, PySpark) place massive demands on memory and CPU:
- Continuous indexing, AST tree building, and type-checking saturate CPU cores and consume 2–6 GB RAM per IDE window.
- Heavy Python data science dependencies (`numpy`, `pandas`, `scipy`, `matplotlib`, LLM inference) risk triggering macOS ACIO2 kernel panics on the Mac Mini M4 Pro host (L1) by threatening its mandatory $\ge 4.8\text{ GB}$ host memory sanctuary.

To permanently eliminate this burden, **100% of IDE compilation, language servers (`gopls`, `pyright`, `basedpyright`), background indexers, and notebook executions have been migrated to the Linux Mini (`lauburu` Node L8)**.

### Target Hardware Profile (Node L8)
| Metric | Specification | Empirical Status |
|:--|:--|:--|
| **Device** | Intel x86_64, Ubuntu 24.04 LTS (Linux 6.8) | Verified via `uname -a` |
| **CPU** | 12 Cores / 12 Threads | Fully utilized during parallel builds |
| **RAM** | 32 GB DDR4 (16+ GB free headroom) | Preserves L1 M4 host RAM sanctuary |
| **Storage** | 129 GB free NVMe SSD on `/` | High-speed cache for indexing |
| **Primary Link** | **40 Gb/s Thunderbolt 4 Bridge (`10.0.0.8`)** | **~0.38 ms RTT** round-trip latency |
| **Secondary Link** | Tailscale Overlay (`100.121.247.8`) | ~2.95 ms RTT mesh fallback |
| **Tertiary Link** | LAN Ethernet (`192.168.8.230`) | Sub-1 ms LAN fallback |

---

## 2. Multi-Tier Access Modalities

Development can be accessed seamlessly across three zero-friction modalities:

```
+-----------------------------------------------------------------------------------------+
|                                    CLIENT PLATFORMS                                     |
|  Mac Mini M4 (L1)  |  MacBook Pro Intel (L2)  |  MacBook Air M4 (L1a)  |  Android (L6/L7)|
+-----------------------------------------------------------------------------------------+
       |                                      |                                  |
   [Browser]                              [Browser]                      [JetBrains Gateway]
       |                                      |                                  |
       v                                      v                                  v
+------------------+                  +------------------+             +------------------+
|   Code-Server    |                  |    JupyterLab    |             | JetBrains Engine |
|    (Port 8443)   |                  |   (Port 8888)    |             |   (SSH Port 22)  |
|  Go/Python IDE   |                  |  Python 3.12/Go  |             |  GoLand & PyCharm|
+------------------+                  +------------------+             +------------------+
       \                                      |                                 /
        \                                     |                                /
         +------------------------------------+-------------------------------+
                                              |
                                              v
                              +-------------------------------+
                              |    LINUX MINI (lauburu L8)    |
                              | 12 Cores | 32GB RAM | 40Gb/s  |
                              +-------------------------------+
```

### Modality A: Web IDE (Code-Server) — Zero Client Install
A full VS Code IDE operating entirely in the browser. Zero RAM or CPU used on client machines.
- **Thunderbolt Link (Fastest, ~0.38ms):** [http://10.0.0.8:8443](http://10.0.0.8:8443)
- **Tailscale Mesh Link:** [http://100.121.247.8:8443](http://100.121.247.8:8443)
- **Pre-installed Extensions:**
  - `golang.go` (Go language server `gopls` + Delve debugger `dlv`)
  - `ms-python.python` (Python language server, linter, formatting)
  - `ms-toolsai.jupyter` (Interactive Notebooks within the Web IDE)
- **Authentication:** Direct LAN/Thunderbolt access (zero login friction within private mesh).

### Modality B: JupyterLab & Notebook Compute Backend
Interactive multi-kernel scientific computing backend.
- **Thunderbolt Link:** [http://10.0.0.8:8888/lab](http://10.0.0.8:8888/lab)
- **Tailscale Mesh Link:** [http://100.121.247.8:8888/lab](http://100.121.247.8:8888/lab)
- **Available Kernels:**
  1. `Python 3 (Linux Mini 32GB)`: Python 3.12.3 with NumPy, Pandas, SciPy, Matplotlib, IPyWidgets, IPyKernel.
  2. `Go (gophernotes)`: Native Go 1.27.2 interactive notebook kernel executing compiled Go cells.

### Modality C: JetBrains Remote Development (GoLand & PyCharm)
Connect from JetBrains Gateway or JetBrains Client on Mac/laptop:
- **Host:** `10.0.0.8` (Thunderbolt) or `100.121.247.8` (Tailscale)
- **User:** `linuxmini`
- **Pre-registered Backends:**
  - GoLand: `/opt/goland`
  - PyCharm Pro: `/opt/pycharm-pro`
  - PyCharm Community: `/opt/pycharm`
- **Gateway Cache Registry:** Pre-linked into `/home/linuxmini/.cache/JetBrains/RemoteDev/userProvidedDist/` so JetBrains Gateway immediately detects the local binaries without waiting to download gigabytes of tarballs.

---

## 3. Toolchain & Runtime Catalog

| Component | Path on Linux Mini | Version / Build | Verified Capabilities |
|:--|:--|:--|:--|
| **Go Compiler** | `/usr/local/go/bin/go` | `go1.27.2 linux/amd64` | Native compilation, 12-core parallel builds |
| **Go Language Server** | `/usr/local/bin/gopls` | `v0.23.0` | Autocomplete, AST diagnostics, references |
| **Go Debugger** | `/usr/local/bin/dlv` | `v1.27.2` | Headless & DAP debugging |
| **Gophernotes** | `/home/linuxmini/go/bin/gophernotes` | `v0.7.6` | Go Jupyter notebook kernel |
| **Python Compute Venv** | `/home/linuxmini/ide_venv` | Python 3.12.3 | Isolated scientific stack |
| **JupyterLab** | `/home/linuxmini/ide_venv/bin/jupyter-lab` | `v4.6.4` | Systemd service on port 8888 |
| **Notebook Server** | `/home/linuxmini/ide_venv/bin/jupyter-notebook` | `v7.6.3` | Notebook UI support |
| **Marimo** | `/home/linuxmini/ide_venv/bin/marimo` | `v0.25.1` | Reactive Python notebook server |
| **GoLand** | `/opt/goland` | `Build #GO-243.25659.52` | JetBrains remote-dev-server enabled |
| **PyCharm Pro** | `/opt/pycharm-pro` | `Build #PY-243.25659.43` | JetBrains remote-dev-server enabled |
| **PyCharm Community** | `/opt/pycharm` | `Build #PC-243.25659.43` | Standalone Linux IDE |
| **Code-Server** | `/usr/bin/code-server` | `v4.141.0` | Systemd service on port 8443 |

---

## 4. Systemd Background Daemons

All compute servers run as persistent systemd services that auto-start on boot:

### 1. JupyterLab Daemon (`jupyterlab.service`)
```ini
[Unit]
Description=JupyterLab 32GB Compute Server on Linux Mini
After=network.target

[Service]
Type=simple
User=linuxmini
WorkingDirectory=/home/linuxmini
ExecStart=/home/linuxmini/ide_venv/bin/jupyter-lab --config=/home/linuxmini/.jupyter/jupyter_lab_config.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 2. Code-Server Daemon (`code-server@linuxmini.service`)
```bash
sudo systemctl enable --now code-server@linuxmini
```
Configuration file: `/home/linuxmini/.config/code-server/config.yaml`
```yaml
bind-addr: 0.0.0.0:8443
auth: none
cert: false
```

---

## 5. CLI Management & Helper Tooling

A unified CLI helper is installed on Linux Mini at `/usr/local/bin/launch-remote-dev`:

```bash
# Check service status and active compute ports
launch-remote-dev status

# Launch headless GoLand backend for a project
launch-remote-dev goland /home/linuxmini/projects/my_project

# Launch headless PyCharm Pro backend for a project
launch-remote-dev pycharm /home/linuxmini/projects/my_project

# Launch PyCharm Community Edition
launch-remote-dev pycharm-ce /home/linuxmini/projects/my_project
```

---

## 6. Zero-Mock Empirical Tri-Proof Gate (Rule 1)

### Proof 1 (Actuation & Execution)
- Go compilation executed natively: 12-core concurrent build output confirmed.
- Jupyter Notebook execution verified: Both `python_executed.ipynb` and `go_executed.ipynb` generated and executed via headless `NotebookClient` with exit code 0.
- Systemd services verified active (`Active: active (running)`).

### Proof 2 (Sockets & Memory Inspection)
```
tcp   LISTEN 0.0.0.0:8888 (jupyter-lab PID 2513984)
tcp   LISTEN 0.0.0.0:8443 (code-server PID 2522536)
tcp   LISTEN 0.0.0.0:22   (sshd)
```
- Linux Mini Memory: 16+ GB free headroom available for heavy workloads.
- Mac Mini M4 Memory: Preserved $> 5\text{ GB}$ free physical RAM.

### Proof 3 (Visual & HTTP Response)
- HTTP probe from L1 over Thunderbolt:
  - `GET http://10.0.0.8:8888/lab` $\to$ `HTTP/1.1 200 OK`
  - `GET http://10.0.0.8:8443/` $\to$ `HTTP/1.1 200 OK`
- HTTP probe from L1 over Tailscale:
  - `GET http://100.121.247.8:8888/lab` $\to$ `HTTP/1.1 200 OK`
  - `GET http://100.121.247.8:8443/` $\to$ `HTTP/1.1 200 OK`
