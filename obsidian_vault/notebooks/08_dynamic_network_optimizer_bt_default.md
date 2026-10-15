---
title: "08_dynamic_network_optimizer_bt_default"
tags: [lauburu, notebook, dual-vault, zero-mock]
---

# 📓 08_dynamic_network_optimizer_bt_default
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

# 🌐 Lauburu Mesh: Dynamic Network Optimizer & BT-Default Telemetry

This notebook provides live visualization of the Tri-Band MLO network latency, Thunderbolt 4 AI Tensor sharding, and Bluetooth PAN fallback states.

```python
import sys, os
for path in ["/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo", "/Users/aaronmaher/teamwork_projects"]:
    if os.path.isdir(path) and path not in sys.path:
        sys.path.insert(0, path)

import json
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
try:
    import seaborn as sns
except ImportError:
    sns = None
from pathlib import Path

plt.style.use('dark_background')
sns.set_palette("coolwarm")
```

## 1. Load Live LoRA Dataset (Network RTT Heartbeats)

```python
LORA_DATASET = Path("/Users/aaron/DFS_UNIFIED/lora_datasets/continuous_lora_dataset.jsonl")

data = []
if LORA_DATASET.exists():
    with open(LORA_DATASET, 'r') as f:
        for line in f:
            try:
                entry = json.loads(line)
                if "ip_telemetry" in entry or "telemetry" in entry:
                    telemetry = entry.get("ip_telemetry", entry.get("telemetry", {}))
                    row = {"timestamp": pd.to_datetime(entry.get("timestamp", 0), unit='s')}
                    row.update(telemetry)
                    data.append(row)
            except: pass

df = pd.DataFrame(data)
if not df.empty:
    df.set_index('timestamp', inplace=True)
    print(f"Loaded {len(df)} telemetry snapshots.")
else:
    print("No telemetry data found yet.")
```

## 2. Visualize RTT Latency Across the 7-Layer Mesh

```python
if not df.empty:
    plt.figure(figsize=(12, 6))
    for col in df.columns:
        plt.plot(df.index, df[col], marker='o', linestyle='-', label=col)
    
    plt.title("Live Mesh RTT Latency (TB4 vs Wi-Fi 7 vs BT Fallback)", fontsize=14, fontweight='bold')
    plt.xlabel("Time", fontsize=12)
    plt.ylabel("Round Trip Time (ms)", fontsize=12)
    plt.legend(loc='upper right')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()
```
