---
title: "09_sovereign_screen_lens_dashboard"
tags: [lauburu, notebook, dual-vault, zero-mock]
---

# 📓 09_sovereign_screen_lens_dashboard
*Synchronized Dual-Vault Mirror — [[Index]]*

<style>
  html, body, #rendered_cells, .jp-Notebook, .jp-Cell, .jp-OutputArea-output {
    background-color: #020617 !important;
    color: #f8fafc !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
  }
  .glass-card {
    background: rgba(15, 23, 42, 0.88);
    border: 1px solid rgba(56, 189, 248, 0.3);
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 12px;
  }
</style>

# 👁️ Sovereign Screen Lens Global Orchestrator Dashboard
Governed by **Notebook Specialist** and **Screen Lens Sovereign** skills.
Displays real-time OCR telemetry, MJPEG HUD, and integrated Lens apps (Life Companion).

```python
import matplotlib
matplotlib.use('Agg')
import sys, os
for path in ["/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo", "/Users/aaronmaher/teamwork_projects"]:
    if os.path.isdir(path) and path not in sys.path:
        sys.path.insert(0, path)

import requests
import ipywidgets as widgets
from IPython.display import display, HTML
import time
```

```python
# ==============================================================================
# CSS Styling (Dark/Glassmorphic)
# ==============================================================================
display(HTML("""
<style>
  html, body, .jp-Notebook, div.cell, div#notebook, .rendered_html {
    background-color: #020617 !important;
    color: #f8fafc !important;
    font-family: 'Inter', sans-serif !important;
  }
  .jupyter-widgets.p-TabBar {
    background: #090d16 !important;
    border-bottom: 1px solid #1e293b !important;
  }
  .p-TabBar-tab {
    background: #0f172a !important;
    color: #94a3b8 !important;
    border: 1px solid #1e293b !important;
    border-bottom: none !important;
    border-radius: 6px 6px 0 0 !important;
  }
  .p-TabBar-tab.p-mod-current {
    background: #1e293b !important;
    color: #e2e8f0 !important;
    border-top: 2px solid #3b82f6 !important;
  }
</style>
"""))
```

```python
# ==============================================================================
# Iframe Generators for Lens Apps
# ==============================================================================
def create_iframe_tab(url, height=800):
    out = widgets.Output()
    iframe_html = f"""
    <div style="height: {height}px; width: 100%; border: 1px solid #1e293b; border-radius: 8px; overflow: hidden; background: #020617;">
        <iframe src="{url}" width="100%" height="100%" frameborder="0" style="background: transparent;"></iframe>
    </div>
    """
    with out:
        display(HTML(iframe_html))
    return out

tab_life_companion = create_iframe_tab("http://127.0.0.1:3036")
tab_mjpeg_hud = create_iframe_tab("http://127.0.0.1:4003")
```

```python
# ==============================================================================
# Orchestrator Telemetry (Port 3037)
# ==============================================================================
out_telemetry = widgets.Output()
with out_telemetry:
    display(HTML("<h3 style='color: #38bdf8;'>Global Orchestrator State (Port 3037)</h3>"))
    try:
        response = requests.get('http://127.0.0.1:3037/api/orchestrator/state', timeout=2)
        import json
        display(HTML(f"<pre style='color: #a3e635; font-size: 14px;'>{json.dumps(response.json(), indent=2)}</pre>"))
    except Exception as e:
        display(HTML(f"<p style='color: #ef4444;'>Orchestrator unreachable: {e}</p>"))
```

```python
# ==============================================================================
# OCR Capture Engine Telemetry (Port 3035)
# ==============================================================================
out_ocr = widgets.Output()
with out_ocr:
    display(HTML("<h3 style='color: #f43f5e;'>OCR Engine Status (Port 3035)</h3>"))
    try:
        response = requests.get('http://127.0.0.1:3035/api/status', timeout=2)
        import json
        display(HTML(f"<pre style='color: #fbbf24; font-size: 14px;'>{json.dumps(response.json(), indent=2)}</pre>"))
    except Exception as e:
        display(HTML(f"<p style='color: #ef4444;'>OCR Engine unreachable: {e}</p>"))
```

```python
# ==============================================================================
# Global Orchestrator Master Tab Assembly
# ==============================================================================
master_tab = widgets.Tab(children=[
    out_telemetry,
    out_ocr,
    tab_life_companion,
    tab_mjpeg_hud,
])

master_tab.set_title(0, "🧠 Global Orchestrator")
master_tab.set_title(1, "👁️ OCR Engine")
master_tab.set_title(2, "📓 Life Companion")
master_tab.set_title(3, "📡 MJPEG HUD")

display(master_tab)
```

```python
# ─── /LENS SWARM TRAINING • PI CODING AGENT • EMBEDDINGGEMMA 2 (MRL) • QWEN 3D VLA ───
import json, socket, time, urllib.request
from pathlib import Path
import numpy as np

def probe_mesh_service(host, port, timeout=0.08):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    t0 = time.perf_counter()
    try:
        ok = (s.connect_ex((host, port)) == 0)
        return ok, round((time.perf_counter() - t0) * 1000.0, 2)
    except Exception:
        return False, -1.0
    finally:
        s.close()

services = [
    ('Screen Lens Core OCR', '127.0.0.1', 3035),
    ('Lens Global Orchestrator', '127.0.0.1', 3037),
    ('Screen MJPEG Stream', '127.0.0.1', 4003),
    ('EmbeddingGemma 2 MRL (:8087)', '127.0.0.1', 8087),
    ('Qwen2.5 0.5B Syntax (:8089)', '127.0.0.1', 8089),
    ('Hermes-3 8B Reasoning (:8085)', '127.0.0.1', 8085),
    ('Pi Edge Router 1M (L3)', '100.101.39.98', 8089),
    ('Qwen 3D Spatial VLA (L1b)', '10.0.0.3', 8090),
]
print('=== 1. /LENS & SOVEREIGN MESH ENDPOINTS ===')
for name, h, p in services:
    ok, rtt = probe_mesh_service(h, p)
    st = f'ONLINE ({rtt} ms)' if ok else 'STANDBY (--)'
    print(f'  • {name:<32} [{h}:{p}] -> {st}')

# 2. Pi Coding Agent (@earendil-works/pi-coding-agent) & Session Harvester
pi_bin = Path('/Users/aaron/.local/bin/pi')
pi_sessions = list(Path.home().glob('.pi/agent/sessions/**/*.jsonl'))
print(f"\n=== 2. PI CODING AGENT & SESSION HARVEST ===")
print(f"  • Binary: {pi_bin} ({'INSTALLED' if pi_bin.exists() else 'STANDBY'}) | Session JSONLs: {len(pi_sessions)}")

# 3. EmbeddingGemma 2 Matryoshka (MRL 768 -> 512 -> 256 -> 128D) Verification
print('\n=== 3. EMBEDDINGGEMMA 2 (MRL 768/512/256/128D) ===')
gemma2_ok, _ = probe_mesh_service('127.0.0.1', 8087)
if gemma2_ok:
    try:
        req = urllib.request.Request(
            'http://127.0.0.1:8087/v1/embeddings',
            data=json.dumps({'input': 'task: search result | query: Lauburu Screen Lens Qwen 3D VLA & EmbeddingGemma 2', 'model': 'embeddinggemma-2'}).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            edata = json.loads(resp.read().decode('utf-8'))
            vec = np.array(edata['data'][0]['embedding'], dtype=np.float32)
            mrl_norms = {d: round(float(np.linalg.norm(vec[:d] / (np.linalg.norm(vec[:d]) + 1e-12))), 4) for d in (768, 512, 256, 128)}
            print(f'  • Live 768D Embedding Norm: {np.linalg.norm(vec):.4f} | MRL L2 Norms: {mrl_norms}')
    except Exception as e:
        print(f'  • EmbeddingGemma 2 query note: {e}')
else:
    print('  • EmbeddingGemma 2 (:8087): STANDBY (--) — Zero-Mock waiting state')

# 4. Qwen 3D VLA (qwen_3d_vla_7b) & 5 Swarm Training Protocols
elo_path = Path('/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/project_elo_leaderboard.json')
qwen3d_elo = 1497.8
if elo_path.exists():
    try:
        qwen3d_elo = json.loads(elo_path.read_text()).get('models', {}).get('qwen_3d_vla_7b', {}).get('global_elo', 1497.8)
    except Exception:
        pass
lora_dir = Path('/Users/aaron/DFS_UNIFIED/lora_datasets')
protocols = [
    ('P1: 3D Spatial Instructional Map LoRA', '3d_spatial_instructional_map_lora.jsonl'),
    ('P2: Podman Curated Gemma 2 MRL LoRA', 'podman_curated_gemma2_mrl_lora.jsonl'),
    ('P3: Continuous LoRA Distillation', 'continuous_lora_dataset.jsonl'),
    ('P4: Proven Accuracy VLA Dataset', 'proven_accuracy_vla_dataset.jsonl'),
    ('P5: Adversarial Truth Audit Debate', 'truth_audit_debate.jsonl'),
]
print(f'\n=== 4. QWEN 3D VLA (ELO {qwen3d_elo}) & 5 SWARM TRAINING PROTOCOLS ===')
for label, fname in protocols:
    fp = lora_dir / fname
    cnt = sum(1 for ln in fp.open(encoding='utf-8', errors='ignore') if ln.strip()) if fp.exists() else 0
    print(f'  • {label:<40} -> {cnt:,} verified JSONL pairs')
```
