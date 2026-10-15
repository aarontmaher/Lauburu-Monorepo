import marimo

__generated_with = "0.1.43"
app = marimo.App()

@app.cell
def __():
    import marimo as mo
    import json
    import time
    import zmq
    from pathlib import Path
    return json, mo, time, zmq, Path

@app.cell
def __(mo):
    mo.md("# 👁️ Omni-Lens Real-Time Mesh Dashboard")

@app.cell
def __(zmq):
    # Setup ZMQ Socket (Runs once)
    context = zmq.Context()
    zmq_sock = context.socket(zmq.SUB)
    zmq_sock.connect("tcp://127.0.0.1:5555")
    zmq_sock.setsockopt_string(zmq.SUBSCRIBE, "LENS.")
    return context, zmq_sock

@app.cell
def __(mo):
    refresh_timer = mo.ui.refresh(options=["1s", "5s", "10s"], default_interval="1s")
    mo.md(f"**Live Polling Active:** {refresh_timer}")
    return refresh_timer,

@app.cell
def __(json, mo, refresh_timer, zmq, zmq_sock):
    # This cell re-evaluates every time the refresh_timer ticks
    refresh_timer
    
    new_msgs = []
    try:
        while True:
            # Drain the socket of all available messages non-blocking
            msg = zmq_sock.recv_multipart(flags=zmq.NOBLOCK)
            topic = msg[0].decode('utf-8')
            payload = json.loads(msg[1].decode('utf-8'))
            new_msgs.append({"topic": topic, "data": payload})
    except zmq.Again:
        pass
        
    mo.ui.table(new_msgs if new_msgs else [{"status": "Listening for LENS payloads...", "topic": "-", "data": "-"}])
    return new_msgs,

if __name__ == "__main__":
    app.run()
