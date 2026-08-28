with open("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/self_healing_hub/src/api_server.py", "r") as f:
    content = f.read()

import re
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
            
            biometrics = data.get("biometrics", {})
            sensor = data.get("sensor", {})
            
            if sensor.get("device_name") and biometrics.get("heart_rate_bpm"):
                legacy_format = {
                    "heart_rate_bpm": biometrics.get("heart_rate_bpm"),
                    "hrv_rmssd_ms": biometrics.get("rr_interval_ms", 0) or 0,
                    "dfa_alpha1": biometrics.get("dfa_alpha1", 1.0) or 1.0,
                    "timestamp": data.get("timestamp"),
                    "connected": True,
                    "battery_pct": sensor.get("battery_pct", 100)
                }
                ecg = data.get("raw_samples", {}).get("ecg_uv")
                if ecg:
                    legacy_format["ecg_hz"] = 500
                return jsonify(legacy_format)
    except Exception as e:
        print("Error pulling from port 4000:", e)

    # 2. Fallback to old real movesense data (telemetry_state.json)"""

# Instead of regex, just split string and replace
parts = content.split('@app.route("/api/telemetry", methods=["GET"])')
if len(parts) > 1:
    after = parts[1].split('# 2. Fallback to old real movesense data (telemetry_state.json)', 1)[1]
    new_content = parts[0] + new_func + after
    with open("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/self_healing_hub/src/api_server.py", "w") as f:
        f.write(new_content)
