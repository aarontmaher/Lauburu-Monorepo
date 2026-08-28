import re

with open("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/self_healing_hub/src/api_server.py", "r") as f:
    content = f.read()

new_func = """@app.route("/api/telemetry", methods=["GET"])
def get_telemetry():
    \"\"\"Serves the latest telemetry state, prioritizing Port 4000 canonical hub, falling back to real local state.\"\"\"
    import urllib.request
    import json
    import os
    
    # 1. Try pulling LIVE data from canonical Port 4000 Hub
    try:
        req = urllib.request.urlopen("http://localhost:4000/api/biometrics", timeout=1.0)
        if req.getcode() == 200:
            data = json.loads(req.read().decode('utf-8'))
            
            # Use data from /api/biometrics endpoint
            biometrics = data.get("biometrics", {})
            sensor = data.get("sensor", {})
            
            # If Movesense is actively connected and has HR, use it as live!
            if sensor.get("device_name") and biometrics.get("heart_rate_bpm"):
                legacy_format = {
                    "heart_rate": biometrics.get("heart_rate_bpm"),
                    "heart_rate_variability": biometrics.get("rr_interval_ms", 0),
                    "respiratory_rate": biometrics.get("dfa_alpha1", 0) * 20 if biometrics.get("dfa_alpha1") else 0, # Approximate
                    "timestamp": data.get("timestamp")
                }
                ecg = data.get("raw_samples", {}).get("ecg_uv")
                if ecg:
                    legacy_format["ecg_microvolts"] = ecg[0] if isinstance(ecg, list) else ecg
                return jsonify(legacy_format)
    except Exception as e:
        pass # Fallback to local files

    # 2. Fallback to old real movesense data (telemetry_state.json)
    src_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(src_dir)
    candidates = [
        os.path.join(src_dir, "telemetry_state.json"),
        os.path.join(base_dir, "telemetry_state.json"),
        "telemetry_state.json"
    ]
    state_file = None
    for p in candidates:
        if os.path.exists(p):
            state_file = p
            break
            
    if not state_file:
        return jsonify({"error": "Telemetry state not yet available"}), 404
        
    try:
        with open(state_file, "r") as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
"""

content = re.sub(r'@app\.route\("/api/telemetry", methods=\["GET"\]\)\ndef get_telemetry\(\):\n(?:    .*\n)*?(?=\n@app\.route)', new_func, content, flags=re.MULTILINE)

with open("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/self_healing_hub/src/api_server.py", "w") as f:
    f.write(content)
