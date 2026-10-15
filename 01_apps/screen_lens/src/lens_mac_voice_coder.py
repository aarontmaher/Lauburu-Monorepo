#!/usr/bin/env python3
"""
01_apps/screen_lens/src/lens_mac_voice_coder.py
===============================================
Native macOS Voice Coder integrated with Screen Lens.

- Listens for continuous voice input using faster-whisper.
- Detects phrases automatically using simple Voice Activity Detection (RMS threshold).
- Routes commands to:
  1. Screen Lens Orchestrator (Port 3037) if addressed ("Hey Lens", "Lens")
  2. Canonical Port Voice Directive (Port 4000) for general coding/git commands.
- Speaks responses back using macOS native `say` command for fluid conversation.
"""

import os
import sys

# Ensure SSL_CERT_FILE points to a valid, permanent file to avoid huggingface_hub FileNotFoundError
if "SSL_CERT_FILE" in os.environ and ("proxy_cert_" in os.environ["SSL_CERT_FILE"] or not os.path.exists(os.environ["SSL_CERT_FILE"])):
    try:
        import certifi
        os.environ["SSL_CERT_FILE"] = certifi.where()
    except ImportError:
        del os.environ["SSL_CERT_FILE"]

import time
import numpy as np
import sounddevice as sd
import urllib.request
import json
import queue
import threading
from faster_whisper import WhisperModel

PORT_4000 = "http://127.0.0.1:4000/api/voice_coder/directive"
PORT_3037 = "http://127.0.0.1:3037/api/orchestrator/plan"

# Audio Settings
SAMPLE_RATE = 16000
CHANNELS = 1
BLOCK_SIZE = 4000  # 0.25 seconds
SILENCE_THRESHOLD = 0.015  # Tune this RMS value based on mic sensitivity
SILENCE_CHUNKS_LIMIT = 4   # 1 second of silence to trigger transcribe

print("🎙️ Starting Lauburu Mac Mini Voice Coder...")
print("📦 Loading faster-whisper model (tiny.en)...")
model = WhisperModel("tiny.en", device="cpu", compute_type="int8")

audio_queue = queue.Queue()

def audio_callback(indata, frames, time_info, status):
    if status:
        print(status, file=sys.stderr)
    audio_queue.put(indata.copy())

def speak(text):
    safe_text = text.replace('"', '\\"').replace("'", "")
    os.system(f'say "{safe_text}"')

def send_to_lens(transcript):
    print(f"👁️ Sending to Lens: {transcript}")
    try:
        req = urllib.request.Request(PORT_3037, data=json.dumps({"goal": transcript}).encode('utf-8'), headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                resp_json = json.loads(response.read().decode('utf-8'))
                plan = resp_json.get("plan", {})
                summary = plan.get("spoken_summary") or "Lens has processed the visual context."
                speak(summary)
            else:
                speak("Lens encountered an error.")
    except Exception as e:
        print("Lens Error:", e)
        speak("I couldn't reach the Lens orchestrator.")

def send_to_coder(transcript):
    print(f"💻 Sending to Coder: {transcript}")
    try:
        req = urllib.request.Request(PORT_4000, data=json.dumps({"raw_transcript": transcript}).encode('utf-8'), headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                resp_json = json.loads(response.read().decode('utf-8'))
                summary = resp_json.get("spoken_summary", "Command executed.")
                speak(summary)
            else:
                speak("Voice coder encountered an error.")
    except Exception as e:
        print("Coder Error:", e)
        speak("I couldn't reach the Port 4000 Unified Hub.")

def get_input_device():
    try:
        devices = sd.query_devices()
        default_in = sd.default.device[0]
        if default_in is not None and default_in >= 0:
            dev_info = sd.query_devices(default_in)
            if dev_info.get("max_input_channels", 0) > 0:
                return default_in
        if isinstance(devices, list):
            for i, dev in enumerate(devices):
                if dev.get("max_input_channels", 0) > 0:
                    return i
        elif isinstance(devices, dict) and devices.get("max_input_channels", 0) > 0:
            return 0
    except Exception:
        pass
    return None

def main():
    speak("Voice coding initialized.")
    buffer = []
    silence_chunks = 0
    recording = False

    while True:
        input_dev = get_input_device()
        if input_dev is None:
            print("⚠️ No audio input device (mic) detected. Standing by until audio input is available...")
            while get_input_device() is None:
                time.sleep(5)
            input_dev = get_input_device()

        print(f"🟢 Listening on device {input_dev}... (Say 'Lens' to ask about the screen, or just speak coding commands)")
        try:
            with sd.InputStream(device=input_dev, samplerate=SAMPLE_RATE, channels=CHANNELS, dtype='float32', callback=audio_callback, blocksize=BLOCK_SIZE):
                while True:
                    chunk = audio_queue.get()
                    rms = np.sqrt(np.mean(chunk**2))
                    
                    if rms > SILENCE_THRESHOLD:
                        if not recording:
                            print("🎤 Voice detected...")
                            recording = True
                        buffer.append(chunk)
                        silence_chunks = 0
                    else:
                        if recording:
                            silence_chunks += 1
                            buffer.append(chunk)
                            if silence_chunks > SILENCE_CHUNKS_LIMIT:
                                print("⏳ Silence detected, transcribing...")
                                recording = False
                                
                                audio_data = np.concatenate(buffer).flatten()
                                buffer = []
                                silence_chunks = 0
                                
                                if len(audio_data) > SAMPLE_RATE * 0.5: # At least 0.5s of audio
                                    segments, info = model.transcribe(audio_data, beam_size=1)
                                    text = " ".join([seg.text for seg in segments]).strip()
                                    if text:
                                        print(f"📝 Transcript: {text}")
                                        lower_text = text.lower()
                                        
                                        # Ignore hallucinations
                                        if "thank you" in lower_text and len(lower_text) < 15:
                                            continue
                                            
                                        if "lens" in lower_text:
                                            send_to_lens(text)
                                        else:
                                            send_to_coder(text)
                                            
                                print("🟢 Listening...")
        except Exception as e:
            print(f"⚠️ Audio input error or disconnection: {e}. Reconnecting...")
            time.sleep(2)

if __name__ == "__main__":
    main()
