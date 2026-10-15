#!/usr/bin/env python3
"""
Pixel 10 Pro XL 24/7 Ambient Mic & Mesh Election Daemon
Continuously samples ambient microphone volume and participates in the
Lauburu Mesh Acoustic Election for dynamic hands-free microphone handoff.
"""
import os
import sys
import time
import json
import re
import subprocess
import urllib.request

DEVICE_ID = "L6_Pixel_10_Edge"
HUB_URL = "http://10.1.0.10:18899/api/audio/mesh_election"
SAMPLE_FILE = os.path.expanduser("~/ambient_sample.m4a")

def measure_ambient_volume(duration_sec=1) -> float:
    try:
        # Record sample
        cmd_rec = f"termux-microphone-record -l {duration_sec} -f {SAMPLE_FILE}"
        subprocess.run(cmd_rec, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        time.sleep(duration_sec + 0.1)

        # Detect volume via ffmpeg
        cmd_vol = f"ffmpeg -i {SAMPLE_FILE} -af volumedetect -vn -sn -dn -f null /dev/null 2>&1"
        res = subprocess.run(cmd_vol, shell=True, capture_output=True, text=True)
        
        # Parse max_volume: -XX.X dB
        match = re.search(r"max_volume:\s+([-\d\.]+)\s+dB", res.stdout)
        if match:
            return float(match.group(1))
        
        # Fallback to mean_volume
        match_mean = re.search(r"mean_volume:\s+([-\d\.]+)\s+dB", res.stdout)
        if match_mean:
            return float(match_mean.group(1))
        
        return -90.0
    except Exception as e:
        return -90.0

def report_to_mesh(amplitude_db: float) -> dict:
    try:
        payload = json.dumps({
            "device_id": DEVICE_ID,
            "amplitude_db": amplitude_db,
            "timestamp": time.time()
        }).encode("utf-8")
        req = urllib.request.Request(
            HUB_URL,
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e)}

def main():
    print(f"🎙️ Starting {DEVICE_ID} Ambient Mic & Mesh Election Daemon...")
    # Ensure wakelock to prevent Android 15 Doze
    subprocess.run("termux-wake-lock", shell=True)

    while True:
        try:
            amp = measure_ambient_volume(duration_sec=1)
            result = report_to_mesh(amp)
            winner = result.get("winning_device")
            if winner == DEVICE_ID:
                print(f"[{DEVICE_ID}] 👑 ELECTION WON ({amp:.1f} dB) - Active Mesh Mic Streamer")
            else:
                print(f"[{DEVICE_ID}] Passive ({amp:.1f} dB) | Winner: {winner}")
            time.sleep(0.5)
        except KeyboardInterrupt:
            break
        except Exception as e:
            time.sleep(1.0)

if __name__ == "__main__":
    main()
