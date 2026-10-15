#!/usr/bin/env python3
"""
Samsung S20 Voice Coding & Ambient Mic Daemon
Records audio chunks and streams them to the Mac Mini for Voice-to-Code transcription.
"""
import os
import time
import subprocess
import requests

DEVICE_ID = "L7_Samsung_S20_Edge"
HUB_URL = "http://192.168.8.230:18899/api/audio/transcribe"
SAMPLE_FILE = os.path.expanduser("~/ambient_voice.m4a")
RECORD_DURATION = 5

def record_and_send():
    print(f"🎙️ [Samsung S20] Recording {RECORD_DURATION}s voice chunk...")
    subprocess.run(f"termux-microphone-record -l {RECORD_DURATION} -f {SAMPLE_FILE}", shell=True, check=True)
    time.sleep(RECORD_DURATION + 0.1)
    
    if os.path.exists(SAMPLE_FILE):
        print(f"📤 Sending audio to Mac Mini Hub...")
        try:
            with open(SAMPLE_FILE, 'rb') as f:
                files = {'audio_file': f}
                data = {'device_id': DEVICE_ID}
                resp = requests.post(HUB_URL, files=files, data=data, timeout=5.0)
                print(f"✅ Hub Response: {resp.json()}")
        except Exception as e:
            print(f"❌ Failed to send audio: {e}")

def main():
    print(f"🚀 Starting {DEVICE_ID} Voice Coding Daemon...")
    subprocess.run("termux-wake-lock", shell=True)
    while True:
        try:
            record_and_send()
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()
