import time
import json
import re
import urllib.request

LOG_FILE = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/03_biometrics_and_telemetry/movesense_pull/live_movesense_mds_stream.log"
TARGET_URL = "http://100.101.39.98:4007/biometrics/ingest"

def follow(thefile):
    thefile.seek(0, 2)
    while True:
        line = thefile.readline()
        if not line:
            time.sleep(0.1)
            continue
        yield line

print(f"Starting Movesense Telemetry Forwarder to {TARGET_URL}...")

try:
    with open(LOG_FILE, "r") as logfile:
        loglines = follow(logfile)
        for line in loglines:
            if "MdsOperationHandler" in line and "{" in line:
                try:
                    json_str = line[line.find("{"):]
                    payload = json.loads(json_str)
                    
                    data = json.dumps({"raw_logcat": payload}).encode('utf-8')
                    req = urllib.request.Request(TARGET_URL, data=data, headers={'Content-Type': 'application/json'}, method='POST')
                    with urllib.request.urlopen(req, timeout=1.0) as f:
                        pass
                except Exception as e:
                    pass
except FileNotFoundError:
    print(f"Log file not found: {LOG_FILE}")
