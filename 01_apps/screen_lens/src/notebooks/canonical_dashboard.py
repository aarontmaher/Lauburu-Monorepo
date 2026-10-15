import marimo

__generated_with = "0.1.43"
app = marimo.App()

@app.cell
def __():
    import marimo as mo
    import json
    import time
    from pathlib import Path
    return json, mo, time, Path

@app.cell
def __(json, mo, time, Path):
    mo.md("# 📊 Lauburu Canonical Observation Plane (Layer 2)")

@app.cell
def __(json, time, Path):
    telemetry_path = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/tui_telemetry/ble_serial_stream.jsonl")
    def read_stream():
        data = []
        if telemetry_path.exists():
            with open(telemetry_path, "r") as f:
                for line in f:
                    if line.strip():
                        data.append(json.loads(line))
        return data
    stream_data = read_stream()
    stream_data
    
@app.cell
def __(mo, stream_data):
    mo.ui.table(stream_data[-10:] if stream_data else [])
    
if __name__ == "__main__":
    app.run()
