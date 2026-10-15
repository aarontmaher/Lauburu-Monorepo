import socket
import struct
import json
import urllib.request
import os

HOST = '0.0.0.0'
PORT = 19003
LOG_PATH = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/03_biometrics_and_telemetry/movesense_pull/live_movesense_mds_stream.log"
HUB_URL = "http://127.0.0.1:4000/api/biometrics/sample"

def handle_data(data):
    if len(data) < 2: return
    pkt_type = data[0]
    req_id = data[1]
    
    if pkt_type == 0x02 and req_id == 99 and len(data) >= 10:
        # req_id 0x99 is the ECG stream requested by Flutter app
        try:
            samples = []
            offset = 6 # skip timestamp and header
            while offset + 4 <= len(data):
                val_uv = struct.unpack('<i', data[offset:offset+4])[0]
                samples.append(val_uv / 1000.0)
                offset += 4
                
            if samples:
                # 1. Write to Log
                with open(LOG_PATH, "a") as f:
                    f.write(json.dumps({"Body": {"Samples": samples}}) + "\n")
                    
                # 2. POST to Hub
                try:
                    req = urllib.request.Request(
                        HUB_URL,
                        data=json.dumps({"samples": samples, "device_id": "Movesense via Flutter"}).encode("utf-8"),
                        headers={"Content-Type": "application/json"}
                    )
                    urllib.request.urlopen(req, timeout=0.2)
                except Exception:
                    pass
        except Exception as e:
            print(f"Parse error: {e}")

print(f"Starting Movesense TCP Receiver on {HOST}:{PORT}...")
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen(1)
    while True:
        conn, addr = s.accept()
        print(f"Connected by {addr}")
        with conn:
            buffer = bytearray()
            while True:
                data = conn.recv(1024)
                if not data: break
                buffer.extend(data)
                # Parse frames (this is simplified; in reality frames might be chunked, but let's try direct handling for now)
                # Movesense payload size is typically determined by MTU. Let's just process whatever we get if it starts with 0x02 0x99
                if len(buffer) > 2 and buffer[0] == 0x02:
                    handle_data(buffer)
                    buffer.clear()
