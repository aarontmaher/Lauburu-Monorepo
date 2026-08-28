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
        req = urllib.request.urlopen("http://localhost:4000/api/sensors/status", timeout=1.0)
        if req.getcode() == 200:
            data = json.loads(req.read().decode('utf-8'))
            
            # Map canonical port 4000 format to port 5001 legacy format for the games
            # Port 4000 returns: {"sensors": {"movesense": {"heart_rate": 65, "ecg_mv": [1.2, ...], ...}}}
            movesense = data.get("sensors", {}).get("movesense", {})
            polar = data.get("sensors", {}).get("polar", {})
            
            # If Movesense is actively connected and has HR, use it as live!
            if movesense.get("connected") and movesense.get("heart_rate"):
                legacy_format = {
                    "heart_rate": movesense.get("heart_rate"),
                    "heart_rate_variability": movesense.get("rmssd", 0),
                    "respiratory_rate": movesense.get("dfa_alpha1", 0) * 20, # Approximate
                    "timestamp": data.get("timestamp")
                }
                if "ecg_mv" in movesense and movesense["ecg_mv"]:
                    legacy_format["ecg_microvolts"] = movesense["ecg_mv"][0] if isinstance(movesense["ecg_mv"], list) else movesense["ecg_mv"]
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
