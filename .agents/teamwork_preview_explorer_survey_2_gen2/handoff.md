# Handoff Report: Multi-View UI Engine, Iframe Routing & Port Matrix Technical Survey

**Agent**: `teamwork_preview_explorer_survey_2_gen2`  
**Milestone**: Multi-View UI Engine, Iframe Routing, and Port Matrix Technical Investigation  
**Date**: 2026-09-02T05:57:00+10:00 (UTC: 2026-09-01T19:57:00Z)  
**Parent Conversation ID**: `e9421748-42ff-4cf4-b121-3c19a4436405`

---

## 1. Observation

### 1.1 Target Notebook Analysis (`01_apps/notebooks/00_lauburu_global_master_project.ipynb`)
- **Cell 1 & 2**: Header and navigation section (`<div id="sec-ports"></div>`).
- **Cell 3**: Master 10-Port Matrix & Single Viewport Switcher.
  - Hardcoded `PORT_DIRECTORY` with 10 ports:
    - `:4000` -> `http://127.0.0.1:4000`
    - `:8088` -> `http://100.119.199.76:8088`
    - `:18805` -> `http://100.119.199.76:18805`
    - `:8889` -> `http://100.93.158.96:8889/lab`
    - `:8890` -> `http://100.93.158.96:8890`
    - `:8082` -> `http://100.119.199.76:8082/health`
    - `:8083` -> `http://100.119.199.76:8083/health`
    - `:8888` -> `http://100.101.39.98:8888`
    - `:9000` -> `http://100.119.199.76:9000/status`
    - `:18802` -> `http://100.119.199.76:18802/health`
  - **Single Viewport UI**: Only contains a single `widgets.Dropdown` and a single `widgets.Output` rendering one `<iframe>`. Does not allow concurrent multi-port monitoring.
  - **Missing Port 3000**: Port 3000 (Next.js Zone 2 Web UI / Universal Portal) is entirely absent from `PORT_DIRECTORY`.

### 1.2 Target Notebook Analysis (`obsidian_vault/notebooks/00_lauburu_global_master_project.ipynb`)
- **Cell 1**: Mandates headless backend `matplotlib.use('Agg')` and initializes glassmorphic CSS styling rules.
- **Cell 3**: Hardware Mesh Topology & Zero-Mock Live Mesh Prober table with 7 physical layers (L1 Mac Mini M4 Pro through L7 Samsung S20).

### 1.3 Empirical Port Probing & HTTP Header Verification
Direct socket and HTTP probing of local ports on the host revealed:
```
[Port 3000 (Zone 2/Frontend)] http://127.0.0.1:3000 -> STANDBY / Connection Refused (Dormant)
[Port 4000 (Movesense Hub)]   http://127.0.0.1:4000 -> ONLINE (HTTP 200, uvicorn, NO_X_FRAME_OPTIONS, NO_CSP)
[Port 8083 (Devils Advocate)] http://127.0.0.1:8083 -> ONLINE (HTTP 200 on /health)
[Port 8888 (SeaweedFS Filer)] http://127.0.0.1:8888 -> ONLINE (HTTP 200, SeaweedFS 30GB 4.44, NO_X_FRAME_OPTIONS)
[Port 8889 (JupyterLab Air)]  http://100.93.158.96:8889 -> ONLINE (HTTP 200 on Layer 5 MacBook Air)
[Port 8890 (Voila Dashboard)] http://127.0.0.1:8890 -> ONLINE (HTTP 200, TornadoServer/6.5.8)
[Port 9333 (SeaweedFS Master)]http://127.0.0.1:9333 -> ONLINE (HTTP 200)
```

When querying `http://100.119.199.76:8890` (Mac Mini Tailscale IP):
`urllib.error.URLError: <urlopen error [Errno 61] Connection refused>`
**Cause**: The Voila server and local services are bound exclusively to `127.0.0.1` / `localhost` and do not listen on the Tailscale network interface `100.119.199.76`.

### 1.4 Runtime Execution Environment
- Voila binary: `/Users/aaron/.local/share/uv/tools/jupyterlab/bin/voila` (running PID 63891 on `:8866`).
- Active ipykernel environment: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/self_healing_hub/.venv/bin/python3` (verified `ipywidgets: 8.1.9`, `matplotlib`, `psutil`).

---

## 2. Logic Chain

### 2.1 Root Causes of "Refused to Connect" Iframe Errors & Solutions
1. **Binding Address Mismatch (Tailscale IP vs Loopback)**:
   - *Observation*: Services running locally on Layer 1 Mac Mini (Ports 4000, 8088, 18805, 8082, 8083, 9000, 18802) were assigned URLs pointing to `http://100.119.199.76:<port>`.
   - *Logic*: When local microservices bind to `127.0.0.1`, the kernel drops or rejects SYN packets directed at `100.119.199.76`. When a browser on localhost renders `<iframe src="http://100.119.199.76:...">`, the connection fails with `ERR_CONNECTION_REFUSED`.
   - *Solution*: All local services on the host machine MUST use `http://127.0.0.1:<port>` or `http://localhost:<port>`. Remote services (such as L5 MacBook Air `:8889` or L3 Linux Head Node `:8888`) correctly use their respective Tailscale IPs (`100.93.158.96`, `100.101.39.98`).

2. **HTTP Framing Security Headers (`X-Frame-Options` & CSP)**:
   - *Observation*: Voila includes `Content-Security-Policy: frame-ancestors 'self'`.
   - *Logic*: If target services emit restrictive `X-Frame-Options: SAMEORIGIN` or `DENY`, browsers block iframe rendering across different port origins.
   - *Solution*: 
     - Provide standard permissive iframe sandbox attributes: `allow="camera; microphone; display-capture; autoplay; clipboard-write; encrypted-media"`, `sandbox="allow-forms allow-modals allow-popups allow-popups-to-escape-sandbox allow-same-origin allow-scripts allow-downloads"`.
     - Ensure internal microservices (FastAPI/Uvicorn, Next.js) configure CORS/CSP to allow local framing (`frame-ancestors 'self' http://localhost:* http://127.0.0.1:*`).

3. **Zero-Mock Standby Handling (Rule #0 Compliance)**:
   - *Observation*: If a target port is dormant/stopped, rendering the iframe causes the browser to show an unstyled grey connection error box.
   - *Logic*: Showing broken browser error pages degrades UX and violates clear system telemetry principles.
   - *Solution*: The widget conducts quick non-blocking socket probes (`socket.connect_ex` with 20ms timeout). If a port is offline, it renders an elegant cyber glassmorphic "Standby Mode" card displaying service role, startup commands, and a live retry button.

---

## 3. Caveats

1. **Hardware Isolation Mandate**:
   - Strictly forbidden from executing Playwright, Chromium, or GUI browser automation directly on Layer 1 Mac Mini (host).
   - Any end-to-end visual tests or screenshot validations must be offloaded remotely via SSH to Layer 5 MacBook Air (`100.93.158.96`) or Layer 7 Samsung S20 (`100.84.40.95`).
2. **Headless Execution Safety**:
   - In automated non-interactive runs (e.g. `papermill` or `nbconvert`), `ipywidgets` dynamic JavaScript observers do not execute. The code must gracefully render static HTML matrices and fallback cards when `widgets` is absent or running headlessly.
3. **Cross-Origin Storage / Cookies**:
   - Different ports on `127.0.0.1` have isolated `localStorage` and cookies under browser Same-Origin Policy (SOP). This does not impede iframe rendering or WebSocket streams.

---

## 4. Conclusion & Design Recommendations

### 4.1 Upgraded 14-Endpoint Canonical Port Matrix
Include Port 3000 alongside all existing mesh services with correct host addressing:

| Port | Service Name | Host Binding / URL | Protocol | Role & Subsystem |
|:---|:---|:---|:---|:---|
| **3000** | Zone 2 Endurance & Web Portal Hub | `http://127.0.0.1:3000` | HTTP/Next.js | Zone 2 Frontend & Real-Time Biometrics Dashboard |
| **4000** | Movesense 512Hz ECG & Zone 2 Hub | `http://127.0.0.1:4000` | HTTP/GATT BLE | 512Hz R-Peak DSP & In-App Edge Chat |
| **8081** | prima.cpp Master Instance (Qwen 32B) | `http://127.0.0.1:8081/health` | REST/TCP RPC | Primary Local AI Engine |
| **8082** | prima.cpp PRP Ring (Qwen 80B/72B) | `http://127.0.0.1:8082/health` | REST/TCP RPC | 3-Mac PRP Ring Sharding Coordinator |
| **8083** | Devil's Advocate & Edge AI Gateway | `http://127.0.0.1:8083/health` | OpenAI REST | Abliterated AI & SmolLM2 Chat |
| **8084** | llama.cpp Distributed RPC Worker 4 | `http://127.0.0.1:8084/health` | GGML RPC | Edge Tensor Sharding Worker |
| **8088** | Universal Web-TUI Portal & Leaderboard | `http://127.0.0.1:8088` | HTTP/WebSocket PTY | 120 FPS Terminal Streamer & Mesh Visualizer |
| **8888** | SeaweedFS Distributed Storage Hub | `http://127.0.0.1:8888` | HTTP/Filer | S3-Compatible Big Data & GGUF Storage |
| **8889** | JupyterLab Master IDE & Data Lab | `http://100.93.158.96:8889/lab` | HTTP/WebSocket | Primary Interactive Code Workbench (Layer 5 Air) |
| **8890** | Voilà Standalone Production Dashboard | `http://127.0.0.1:8890` | HTTP/WebSocket | Zero-Click Production Web App |
| **9000** | AI Budget Proxy & Killswitch Guard | `http://127.0.0.1:9000/status` | HTTP REST | $0.00 Hard-Locked Cloud Budget Sentinel |
| **9333** | SeaweedFS Master Raft Consensus | `http://127.0.0.1:9333` | HTTP/Raft | Storage Volume Topology & Raft Leader |
| **18802**| Self-Healing Hub & WoL Resurrection | `http://127.0.0.1:18802/health` | HTTP REST | Out-of-Band Power Recovery & ADB Keepalive |
| **18805**| Real-Time Live Command Cockpit | `http://127.0.0.1:18805` | HTTP/JS Polling | Live Genetic Radar & Model Download Gauges |

---

### 4.2 Dynamic Multi-View 2x2 Grid Architecture
The Multi-View Engine consists of:
1. **Global Control Header**:
   - **Layout Mode Selector**: `🔲 2x2 Quad Grid`, `🔳 1x2 Dual Split`, `⏹️ 1x1 Solo Focus`.
   - **Preset Quick-Loader**:
     - `🚀 Full Stack Quad`: [Port 3000, Port 4000, Port 8888, Port 8889]
     - `🧠 AI Cluster Quad`: [Port 8081, Port 8082, Port 8083, Port 9000]
     - `🖥️ Ops & Monitoring Quad`: [Port 4000, Port 18802, Port 18805, Port 8088]
     - `💾 Storage & Core Quad`: [Port 8888, Port 9333, Port 8890, Port 3000]
   - **Height Selector**: Compact (380px), Standard (520px), Expansive (720px).
   - **Refresh All Probes Button**: Re-checks socket status across all slots.
2. **4 Independent Viewport Slots**:
   - Each slot features:
     - Dropdown endpoint selector.
     - Real-time socket status pill (🟢 ONLINE / ⚪ STANDBY).
     - Direct "Open ↗" link.
     - Sandboxed iframe with lazy loading and error fallback.
3. **Dynamic CSS Grid Container**:
   - CSS `display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px;` for 2x2 layout, dynamically collapsing to 1 column on mobile or in 1x1 mode.

---

### 4.3 Drop-In Python Template for Master Notebook (Cell 3)

```python
# Master 14-Port Glassmorphic Matrix & Multi-View 2x2 Grid Engine
import socket, time, html
from IPython.display import display, HTML, clear_output
try:
    import ipywidgets as widgets
except ImportError:
    widgets = None

PORT_DIRECTORY = [
    {"port": 3000, "name": "Zone 2 Endurance & Web Portal Hub", "url": "http://127.0.0.1:3000", "protocol": "HTTP/Next.js", "role": "Zone 2 Frontend & Real-Time Biometrics Dashboard", "host": "127.0.0.1", "category": "web"},
    {"port": 4000, "name": "Movesense 512Hz ECG & Zone 2 Hub", "url": "http://127.0.0.1:4000", "protocol": "HTTP/GATT BLE", "role": "512Hz R-Peak DSP & In-App Edge Chat", "host": "127.0.0.1", "category": "biometrics"},
    {"port": 8088, "name": "Universal Web-TUI Portal & Leaderboard", "url": "http://127.0.0.1:8088", "protocol": "HTTP/WebSocket PTY", "role": "120 FPS Terminal Streamer & Mesh Visualizer", "host": "127.0.0.1", "category": "tui"},
    {"port": 18805, "name": "Real-Time Live Command Cockpit", "url": "http://127.0.0.1:18805", "protocol": "HTTP/JS Polling", "role": "Live Genetic Radar & Model Download Gauges", "host": "127.0.0.1", "category": "ops"},
    {"port": 8889, "name": "JupyterLab Master IDE & Data Lab", "url": "http://100.93.158.96:8889/lab", "protocol": "HTTP/WebSocket", "role": "Primary Interactive Code Workbench (Layer 5 Air)", "host": "100.93.158.96", "category": "ide"},
    {"port": 8890, "name": "Voilà Auto-Running Standalone Dashboard", "url": "http://127.0.0.1:8890", "protocol": "HTTP/WebSocket", "role": "Zero-Click Production Web App", "host": "127.0.0.1", "category": "dashboard"},
    {"port": 8081, "name": "prima.cpp Master Instance (Qwen 32B)", "url": "http://127.0.0.1:8081/health", "protocol": "REST/TCP RPC", "role": "Primary Local AI Engine", "host": "127.0.0.1", "category": "ai"},
    {"port": 8082, "name": "prima.cpp PRP Ring (Qwen 80B/72B)", "url": "http://127.0.0.1:8082/health", "protocol": "REST/TCP RPC", "role": "3-Mac PRP Ring Sharding Coordinator", "host": "127.0.0.1", "category": "ai"},
    {"port": 8083, "name": "Devil's Advocate & Edge AI Gateway", "url": "http://127.0.0.1:8083/health", "protocol": "OpenAI REST", "role": "Abliterated AI & SmolLM2 Chat", "host": "127.0.0.1", "category": "ai"},
    {"port": 8084, "name": "llama.cpp Distributed RPC Worker 4", "url": "http://127.0.0.1:8084/health", "protocol": "GGML RPC", "role": "Edge Tensor Sharding Worker", "host": "127.0.0.1", "category": "ai"},
    {"port": 8888, "name": "SeaweedFS Distributed Storage Hub", "url": "http://127.0.0.1:8888", "protocol": "HTTP/Filer", "role": "S3-Compatible Big Data & GGUF Storage", "host": "127.0.0.1", "category": "storage"},
    {"port": 9333, "name": "SeaweedFS Master Raft Consensus", "url": "http://127.0.0.1:9333", "protocol": "HTTP/Raft", "role": "Storage Volume Topology & Raft Leader", "host": "127.0.0.1", "category": "storage"},
    {"port": 9000, "name": "AI Budget Proxy & Killswitch Guard", "url": "http://127.0.0.1:9000/status", "protocol": "HTTP REST", "role": "$0.00 Hard-Locked Cloud Budget Sentinel", "host": "127.0.0.1", "category": "ops"},
    {"port": 18802, "name": "Self-Healing Hub & WoL Resurrection", "url": "http://127.0.0.1:18802/health", "protocol": "HTTP REST", "role": "Out-of-Band Power Recovery & ADB Keepalive", "host": "127.0.0.1", "category": "ops"}
]

PRESET_CONFIGS = {
    "🚀 Full Stack Quad": [
        "http://127.0.0.1:3000",
        "http://127.0.0.1:4000",
        "http://127.0.0.1:8888",
        "http://100.93.158.96:8889/lab"
    ],
    "🧠 AI Cluster Quad": [
        "http://127.0.0.1:8081/health",
        "http://127.0.0.1:8082/health",
        "http://127.0.0.1:8083/health",
        "http://127.0.0.1:9000/status"
    ],
    "🖥️ Ops & Monitoring Quad": [
        "http://127.0.0.1:4000",
        "http://127.0.0.1:18802/health",
        "http://127.0.0.1:18805",
        "http://127.0.0.1:8088"
    ],
    "💾 Storage & Core Quad": [
        "http://127.0.0.1:8888",
        "http://127.0.0.1:9333",
        "http://127.0.0.1:8890",
        "http://127.0.0.1:3000"
    ]
}

def probe_port_quick(host, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.025)
    try:
        return s.connect_ex((host, port)) == 0
    except Exception:
        return False
    finally:
        s.close()

# 1. Render Top Summary Status Cards
matrix_html = """<div class="glass-card" style="margin-bottom: 14px;"><div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 10px;">"""
for p in PORT_DIRECTORY:
    is_live = probe_port_quick(p["host"], p["port"])
    status_badge = '<span style="color: #10b981; font-size: 11px; font-weight: 600;">🟢 ONLINE</span>' if is_live else '<span style="color: #94a3b8; font-size: 11px; font-weight: 600;">⚪ STANDBY</span>'
    card_border = "#0284c7" if is_live else "#1e293b"
    matrix_html += f"""<div style="background: #020617; border: 1px solid {card_border}; border-radius: 8px; padding: 8px 10px; display: flex; flex-direction: column; justify-content: space-between;"><div style="display: flex; justify-content: space-between; align-items: center;"><span style="color: #38bdf8; font-weight: 700; font-family: monospace; font-size: 13px;">:{p['port']}</span>{status_badge}</div><div style="color: #cbd5e1; font-size: 11.5px; font-weight: 600; margin-top: 4px; line-height: 1.25; min-height: 28px;">{p['name']}</div><div style="color: #64748b; font-size: 10px; margin-top: 2px;">{p['protocol']} • {p['role'][:32]}</div></div>"""
matrix_html += "</div></div>"
display(HTML(matrix_html))

# 2. Render Interactive Multi-View 2x2 Engine
if widgets:
    port_lookup = {p["url"]: p for p in PORT_DIRECTORY}
    dropdown_options = {f":{p['port']} - {p['name']}": p["url"] for p in PORT_DIRECTORY}

    layout_mode_dropdown = widgets.Dropdown(
        options=[("🔲 2x2 Quad Grid (4 Views)", "2x2"), ("🔳 1x2 Dual Split (2 Views)", "1x2"), ("⏹️ 1x1 Solo Focus (1 View)", "1x1")],
        value="2x2",
        description="Layout:",
        style={'description_width': '60px'},
        layout=widgets.Layout(width="240px")
    )

    preset_dropdown = widgets.Dropdown(
        options=list(PRESET_CONFIGS.keys()),
        value="🚀 Full Stack Quad",
        description="Preset:",
        style={'description_width': '60px'},
        layout=widgets.Layout(width="240px")
    )

    height_dropdown = widgets.Dropdown(
        options=[("Compact (380px)", "380"), ("Standard (520px)", "520"), ("Expansive (750px)", "750")],
        value="520",
        description="Height:",
        style={'description_width': '60px'},
        layout=widgets.Layout(width="200px")
    )

    refresh_btn = widgets.Button(description="🔄 Re-Probe", button_style="info", icon="sync", layout=widgets.Layout(width="110px"))

    # Construct 4 Viewport Slots
    slots = []
    default_urls = PRESET_CONFIGS["🚀 Full Stack Quad"]

    for i in range(4):
        slot_url = default_urls[i] if i < len(default_urls) else PORT_DIRECTORY[i]["url"]
        dd = widgets.Dropdown(
            options=dropdown_options,
            value=slot_url,
            description=f"Pane {i+1}:",
            style={'description_width': '60px'},
            layout=widgets.Layout(width="100%", max_width="380px")
        )
        link_html = widgets.HTML(value=f'<a href="{slot_url}" target="_blank" class="nav-pill" style="padding: 4px 8px; font-size: 11px; color: #38bdf8;">↗ Open</a>')
        status_html = widgets.HTML()
        out = widgets.Output(layout=widgets.Layout(width="100%"))
        slot_box = widgets.VBox([
            widgets.HBox([dd, link_html, status_html], layout=widgets.Layout(align_items='center', justify_content='space-between', padding='4px 8px', background='#0f172a', border='1px solid #1e293b', border_radius='8px 8px 0 0')),
            out
        ], layout=widgets.Layout(border='1px solid #1e293b', border_radius='8px', overflow='hidden', background='#020617'))
        slots.append({"dropdown": dd, "link": link_html, "status": status_html, "out": out, "box": slot_box})

    grid_container = widgets.GridBox(
        children=[s["box"] for s in slots],
        layout=widgets.Layout(
            grid_template_columns="repeat(2, minmax(0, 1fr))",
            gap="14px",
            width="100%",
            margin="12px 0 0 0"
        )
    )

    def render_slot(index):
        s = slots[index]
        url = s["dropdown"].value
        p_info = port_lookup.get(url, {"port": "??", "name": "Custom", "host": "127.0.0.1", "role": ""})
        h = height_dropdown.value
        s["link"].value = f'<a href="{url}" target="_blank" class="nav-pill" style="padding: 4px 8px; font-size: 11px; color: #38bdf8;">↗ Open</a>'
        
        is_live = probe_port_quick(p_info.get("host", "127.0.0.1"), p_info.get("port", 0))
        s["status"].value = '<span style="color: #10b981; font-size: 11px; font-weight: 700;">🟢 LIVE</span>' if is_live else '<span style="color: #94a3b8; font-size: 11px; font-weight: 600;">⚪ STANDBY</span>'

        with s["out"]:
            clear_output(wait=True)
            if is_live:
                display(HTML(f"""<iframe src="{url}" width="100%" height="{h}" style="border: none; background: #020617;" allow="camera; microphone; autoplay; clipboard-write;" sandbox="allow-forms allow-modals allow-popups allow-popups-to-escape-sandbox allow-same-origin allow-scripts allow-downloads"></iframe>"""))
            else:
                display(HTML(f"""<div style="height: {h}px; display: flex; flex-direction: column; align-items: center; justify-content: center; background: #0b1329; border: 1px dashed #334155; padding: 20px; text-align: center;"><div style="font-size: 28px; margin-bottom: 8px;">📡</div><div style="font-weight: 700; color: #38bdf8; font-size: 14px; font-family: monospace;">:{p_info['port']} • {p_info['name']}</div><div style="color: #94a3b8; font-size: 12px; margin-top: 4px; max-width: 400px;">{p_info['role']}</div><div style="margin-top: 14px; padding: 4px 10px; background: rgba(148, 163, 184, 0.1); border-radius: 6px; font-size: 11px; color: #cbd5e1; font-family: monospace;">STATUS: STANDBY (Zero-Mock Verified)</div><a href="{url}" target="_blank" style="margin-top: 10px; color: #38bdf8; font-size: 11.5px; text-decoration: underline;">Attempt Direct Browser Connect ↗</a></div>"""))

    def on_layout_change(change=None):
        mode = layout_mode_dropdown.value
        if mode == "2x2":
            grid_container.layout.grid_template_columns = "repeat(2, minmax(0, 1fr))"
            for i in range(4):
                slots[i]["box"].layout.display = "flex"
                render_slot(i)
        elif mode == "1x2":
            grid_container.layout.grid_template_columns = "repeat(2, minmax(0, 1fr))"
            slots[0]["box"].layout.display = "flex"
            slots[1]["box"].layout.display = "flex"
            slots[2]["box"].layout.display = "none"
            slots[3]["box"].layout.display = "none"
            render_slot(0)
            render_slot(1)
        elif mode == "1x1":
            grid_container.layout.grid_template_columns = "1fr"
            slots[0]["box"].layout.display = "flex"
            slots[1]["box"].layout.display = "none"
            slots[2]["box"].layout.display = "none"
            slots[3]["box"].layout.display = "none"
            render_slot(0)

    def on_preset_change(change=None):
        cfg = PRESET_CONFIGS.get(preset_dropdown.value, [])
        for i, url in enumerate(cfg):
            if i < len(slots) and url in dropdown_options.values():
                slots[i]["dropdown"].value = url
        on_layout_change()

    def on_slot_change(i):
        def handler(change):
            render_slot(i)
        return handler

    for i in range(4):
        slots[i]["dropdown"].observe(on_slot_change(i), names='value')

    layout_mode_dropdown.observe(on_layout_change, names='value')
    preset_dropdown.observe(on_preset_change, names='value')
    height_dropdown.observe(lambda c: [render_slot(k) for k in range(4)], names='value')
    refresh_btn.on_click(lambda b: [render_slot(k) for k in range(4)])

    controls_bar = widgets.HBox(
        [layout_mode_dropdown, preset_dropdown, height_dropdown, refresh_btn],
        layout=widgets.Layout(align_items='center', flex_wrap='wrap', gap='10px', margin='0 0 10px 0')
    )

    display(widgets.VBox([controls_bar, grid_container]))
    on_layout_change()
```

---

## 5. Verification Method

To independently verify the Multi-View UI Engine, Iframe Routing, and Port Matrix:

1. **Matrix Probing & Syntax Verification Command**:
   ```bash
   /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/self_healing_hub/.venv/bin/python3 -c "
   import socket
   ports = [3000, 4000, 8081, 8082, 8083, 8084, 8088, 8888, 8889, 8890, 9000, 9333, 18802, 18805]
   for p in ports:
       s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
       s.settimeout(0.02)
       res = s.connect_ex(('127.0.0.1', p))
       s.close()
       print(f'Port {p}: {\"ONLINE\" if res == 0 else \"STANDBY\"}')
   "
   ```

2. **Headless Notebook Execution Verification**:
   ```bash
   /Users/aaron/.local/share/uv/tools/jupyterlab/bin/python -m jupyter nbconvert \
     --to notebook --execute \
     --ExecutePreprocessor.timeout=120 \
     /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/notebooks/00_lauburu_global_master_project.ipynb \
     --output /tmp/test_verified_master.ipynb
   ```

3. **Hardware Isolation Mandate Check**:
   Confirm that zero Playwright or Chrome processes are spawned on Mac Mini host:
   ```bash
   pgrep -fl "playwright|chromium|chrome"
   ```
   All UI automation is strictly delegated via SSH to Layer 5 MacBook Air (`100.93.158.96`) or Layer 7 Samsung S20 (`100.84.40.95`).

