with open("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/03_biometrics_and_telemetry/movesense_to_4000_bridge.py", "r") as f:
    content = f.read()
content = content.replace("http://127.0.0.1:4000/api/sensors/ingest", "http://127.0.0.1:4000/api/v1/network/ingest")
with open("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/03_biometrics_and_telemetry/movesense_to_4000_bridge.py", "w") as f:
    f.write(content)
