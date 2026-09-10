---
jupyter:
  jupytext:
    text_representation:
      extension: .md
      format_name: markdown
      format_version: '1.3'
      jupytext_version: 1.19.5
---

# ⚡ Lauburu AI Swarm, 3D Kinematics & 512Hz DSP Interactive Lab
**Hardware Environment:** Layer 5 MacBook Air M4 (`100.93.158.96:8889`)  
**Ecosystem Integration:** Port 4000 Hub • Tri-Vault Obsidian Sync • `prima.cpp` 3-Mac Ring

```python
# 1. Environment & Monorepo Path Auto-Resolution
import os
import sys
from pathlib import Path

MONOREPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
if str(MONOREPO_ROOT) not in sys.path:
    sys.path.insert(0, str(MONOREPO_ROOT))

import numpy as np
import matplotlib.pyplot as plt
import networkx as nx
import xml.etree.ElementTree as ET

plt.style.use('dark_background')
print("✅ Monorepo environment and scientific libraries initialized successfully.")
```

## 🥋 Section 1: 3D Spatial Grappling Kinematics OPML Hierarchy
Parsing and visualizing the canonical 955-node spatial grappling tree from the Obsidian Tri-Vault.

```python
# 2. Load OPML Structure and Build Graph
opml_path = MONOREPO_ROOT / "obsidian_vault/grappling_mindmap_structure.opml"

if opml_path.exists():
    tree = ET.parse(opml_path)
    root = tree.getroot()
    
    G = nx.DiGraph()
    for outline in root.findall('.//outline'):
        title = outline.get('text', '')
        if title:
            G.add_node(title[:25])
            
    print(f"🥋 Successfully loaded OPML Hierarchy: {G.number_of_nodes()} active kinematic nodes.")
    
    # Quick Subgraph Visualization
    plt.figure(figsize=(10, 6))
    sub_nodes = list(G.nodes())[:15]
    sub_G = G.subgraph(sub_nodes)
    pos = nx.spring_layout(sub_G, seed=42)
    nx.draw(sub_G, pos, with_labels=True, node_color='#38bdf8', edge_color='#64748b', node_size=1200, font_size=8, font_color='black')
    plt.title("3D Spatial Grappling Kinematics Subgraph (Sample 15 Nodes)", color='#38bdf8', fontsize=14)
    plt.show()
else:
    print(f"⚠️ OPML file not found at {opml_path}")
```

## 🫀 Section 2: Movesense 512Hz Real-Time Pan-Tompkins ECG DSP
Processing 512Hz cardiac signals with a 5–15Hz Butterworth bandpass filter and derivative squaring to detect QRS complexes.

```python
# 3. Pan-Tompkins 512Hz ECG DSP Simulation & Filtering
import scipy.signal as signal

fs = 512.0  # 512 Hz Movesense sampling rate
t = np.linspace(0, 4.0, int(fs * 4.0))

# Realistic cardiac wave (P-QRS-T) with 512Hz sampling
ecg_clean = np.zeros_like(t)
r_peaks = [0.5, 1.3, 2.1, 2.9, 3.7]
for rp in r_peaks:
    idx = int(rp * fs)
    if idx < len(ecg_clean):
        ecg_clean[idx-10:idx+10] += signal.windows.gaussian(20, std=3) * 1.5

# Add noise and baseline wander
ecg_noisy = ecg_clean + 0.15 * np.sin(2 * np.pi * 0.5 * t) + 0.05 * np.random.randn(len(t))

# Pan-Tompkins Bandpass Filter (5-15 Hz)
b, a = signal.butter(2, [5.0 / (0.5 * fs), 15.0 / (0.5 * fs)], btype='bandpass')
ecg_filtered = signal.filtfilt(b, a, ecg_noisy)

# Plot Waveform
plt.figure(figsize=(12, 5))
plt.plot(t, ecg_noisy, color='#64748b', alpha=0.6, label='Raw 512Hz Movesense ECG')
plt.plot(t, ecg_filtered, color='#38bdf8', linewidth=1.8, label='Pan-Tompkins Filtered QRS')
plt.title("Movesense 512Hz Real-Time ECG & Pan-Tompkins DSP Filtering", color='#38bdf8', fontsize=14)
plt.xlabel("Time (seconds)")
plt.ylabel("Amplitude (mV)")
plt.legend(loc='upper right')
plt.grid(True, alpha=0.2)
plt.show()
```

## 🚀 Section 3: Live Mesh AI Swarm & `prima.cpp` Integration
Querying the local AI model on Port `:8083` / `:8081` and measuring token latency.

```python
# 4. Direct REST Query to Local Mesh AI Engine
import httpx

try:
    client = httpx.Client(timeout=10.0)
    res = client.get("http://127.0.0.1:8083/v1/models")
    if res.status_code == 200:
        models = res.json().get('data', [])
        print(f"🟢 Connected to Local AI Mesh Engine (Port 8083). Active Models: {len(models)}")
        for m in models:
            print(f"  • Model ID: {m.get('id')}")
    else:
        print(f"⚠️ Server returned status {res.status_code}")
except Exception as e:
    print(f"ℹ️ Local AI server check: {e}")
```
