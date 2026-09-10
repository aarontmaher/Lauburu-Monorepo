---
jupyter:
  jupytext:
    text_representation:
      extension: .md
      format_name: markdown
      format_version: '1.3'
      jupytext_version: 1.19.5
---

# ⚡ Lauburu AI Mesh: Master Command Console & Localhost Port Hub
**Single Source of Truth for the 7-Layer Heterogeneous Mesh Topology**

This interactive notebook provides direct access to all active localhost web services, real-time port probers, latency heatmaps, and swarm health telemetry across the **108.0 GB Pooled RAM (82.8 GB VRAM)** ecosystem.

```python
import os, sys, time, socket, json
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import display, HTML, IFrame

print("✅ Environment initialized. Python:", sys.version.split()[0])
```

## 🌐 1. Live 7-Layer Interconnect Latency Probe
Probe all 7 physical layers in real-time and compute pairwise round-trip times (RTT).

```python
NODES = [
    {"layer": "L1", "name": "Mac Mini M4 Pro Host", "ip": "127.0.0.1", "port": 8088},
    {"layer": "L5", "name": "MacBook Air M4 Worker", "ip": "100.93.158.96", "port": 22},
    {"layer": "L2", "name": "MacBook Pro TB4 Vault", "ip": "100.103.212.21", "port": 22},
    {"layer": "L3", "name": "Linux Head Node DFS", "ip": "100.101.39.98", "port": 22},
    {"layer": "L6", "name": "Pixel 10 Pro XL TPU", "ip": "100.73.38.87", "port": 8022},
    {"layer": "L7", "name": "Samsung S20+ Termux", "ip": "100.84.40.95", "port": 8022},
    {"layer": "GW", "name": "GL.iNet Gateway Router", "ip": "192.168.8.1", "port": 80}
]

results = []
for n in NODES:
    t0 = time.perf_counter()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.5)
    ok = s.connect_ex((n["ip"], n["port"])) == 0
    t1 = time.perf_counter()
    s.close()
    rtt = (t1 - t0) * 1000.0 if ok else None
    results.append({
        "Layer": n["layer"],
        "Device Name": n["name"],
        "IP Address": n["ip"],
        "Port": n["port"],
        "Status": "🟢 ONLINE" if ok else "🔴 OFFLINE",
        "Latency (ms)": round(rtt, 2) if rtt else 999.0
    })

df = pd.DataFrame(results)
display(df)

# Plot latency
plt.figure(figsize=(10, 4))
online_df = df[df["Status"] == "🟢 ONLINE"]
plt.bar(online_df["Device Name"], online_df["Latency (ms)"], color="#06b6d4")
plt.ylabel("RTT Latency (ms)")
plt.title("7-Layer Mesh Interconnect Latency")
plt.xticks(rotation=25, ha="right")
plt.grid(axis="y", linestyle="--", alpha=0.5)
plt.tight_layout()
plt.show()
```

## 🖥️ 2. Embedded Command Console & Localhost Port Viewers
Access the live web services directly inline within the notebook.

```python
# Render Live Console (Port 18805)
display(HTML("""
<div style="border: 2px solid #06b6d4; border-radius: 8px; overflow: hidden;">
  <div style="background: #0f172a; color: #38bdf8; padding: 8px; font-weight: bold;">
    ⚡ Live Command Console (Port 18805)
  </div>
  <iframe src="http://127.0.0.1:18805" width="100%" height="550" style="border: none;"></iframe>
</div>
"""))
```

```python
# Render Master AI Leaderboard (Port 8088)
display(HTML("""
<div style="border: 2px solid #a855f7; border-radius: 8px; overflow: hidden; margin-top: 15px;">
  <div style="background: #0f172a; color: #c084fc; padding: 8px; font-weight: bold;">
    🏆 Master AI Leaderboard & Universal Portal (Port 8088)
  </div>
  <iframe src="http://127.0.0.1:8088/leaderboard" width="100%" height="550" style="border: none;"></iframe>
</div>
"""))
```
