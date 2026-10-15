#!/usr/bin/env python3
import time
import requests
import json
import os
import subprocess

# Config
LOG_DIR = "/sdcard/SerialBluetoothTerminal/logs/"
L1_HUB_URL = "http://100.119.199.76:8082/v1/chat/completions"

def find_latest_log():
    # Use rish to find the newest log file since standard termux might not have permission
    # For now, we mock the retrieval logic or use a specific file
    cmd = ["/data/data/com.termux/files/usr/bin/rish", "sh", "-c", f"ls -t {LOG_DIR}*.txt | head -n 1"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except:
        return None

def process_and_forward():
    print("📡 Starting Movesense Edge Ingestion Pipeline...")
    print(f"Routing payloads to Sovereign Master: {L1_HUB_URL}")
    
    # Mock loop for tailing and forwarding
    while True:
        # 1. Read latest lines from the Serial Terminal Log
        # 2. Perform lightweight 1D-CNN or Pan-Tompkins DSP (Placeholder)
        # 3. Construct JSON payload
        payload = {
            "model": "qwen_38_max",
            "messages": [
                {"role": "system", "content": "You are processing biometric telemetry."},
                {"role": "user", "content": "{\"hrv_ms\": 45, \"r_r_interval\": [800, 810, 790], \"anomalies\": 0}"}
            ]
        }
        
        try:
            # Forward the JSON payload to the Mac Mini
            response = requests.post(L1_HUB_URL, json=payload, timeout=5)
            print(f"✅ Payload offloaded to Hub. Response: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Hub unreachable ({e}). Saving payload locally for sync.")
            
        time.sleep(10) # Process in 10-second rolling windows

if __name__ == "__main__":
    process_and_forward()
