import marimo

__generated_with = "0.24.0"
app = marimo.App()

@app.cell
def __():
    import sys, os
    # Auto-Path Resolution in Cell 1 per notebook-specialist skill
    for path in ["/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo", "/Users/aaronmaher/teamwork_projects"]:
        if os.path.isdir(path) and path not in sys.path:
            sys.path.insert(0, path)
    return os, sys


@app.cell
def __():
    import marimo as mo
    import zmq
    import json
    import threading
    import time
    import matplotlib.pyplot as plt
    # Render Clean High-DPI Charts
    plt.style.use('dark_background')
    return json, mo, plt, threading, time, zmq


@app.cell
def __(json, mo, threading, time, zmq):
    # Setup ZMQ subscriber to ingest TUI live mesh state
    get_state, set_state = mo.state({"L1_VRAM_Usage": 0.0, "L2_VRAM_Usage": 0.0, "active_nodes": 0, "tb4_rtt_ms": 0.0, "active_models": []})
    
    def listen_to_ipc_bridge():
        context = zmq.Context.instance()
        socket = context.socket(zmq.SUB)
        socket.connect("tcp://127.0.0.1:5555")
        socket.setsockopt(zmq.SUBSCRIBE, b"")
        
        while True:
            try:
                msg = socket.recv_multipart()
                data_str = msg[1].decode("utf-8")
                data = json.loads(data_str)
                set_state(data)
            except Exception:
                time.sleep(1)
                
    # Run in background to avoid blocking notebook rendering
    # Marimo threading automatically syncs state setter back to main loop
    thread = threading.Thread(target=listen_to_ipc_bridge, daemon=True)
    thread.start()
    return get_state, listen_to_ipc_bridge, set_state, thread


@app.cell
def __(get_state, mo, plt):
    # Visualize the live mesh state
    data = get_state()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    
    # Chart 1: VRAM Usage
    ax1.bar(["L1 (Mac Mini)", "L2 (MBP)"], [data.get("L1_VRAM_Usage", 0), data.get("L2_VRAM_Usage", 0)], color=['#4CAF50', '#2196F3'])
    ax1.set_ylabel("VRAM (GB)")
    ax1.set_title("Live Mesh VRAM Utilization")
    ax1.set_ylim(0, 24)
    
    # Chart 2: Network Latency
    ax2.bar(["TB4 DMA Bridge"], [data.get("tb4_rtt_ms", 0)], color='#FF9800')
    ax2.set_ylabel("RTT (ms)")
    ax2.set_title(f"Active Nodes: {data.get('active_nodes', 0)}")
    ax2.set_ylim(0, 1.0)
    
    fig.tight_layout()
    chart = fig
    return ax1, ax2, chart, data, fig


@app.cell
def __(data, mo):
    # Display the active models as text
    models_html = "<br>".join([f"<li>{m}</li>" for m in data.get("active_models", [])])
    display = mo.md(f"""
    # 🌐 Mesh Analytics Plane
    
    **Live Active Models:**
    <ul>
      {models_html}
    </ul>
    
    **Thunderbolt 4 RTT:** {data.get("tb4_rtt_ms", 0)} ms
    """)
    return display, models_html


if __name__ == "__main__":
    app.run()

