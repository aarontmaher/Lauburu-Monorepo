#!/usr/bin/env python3
"""
Lauburu Samsung Galaxy S20+ Hardware Audio & Voice Coding Agent
Coordinates Samsung microphone input, Bluetooth A2DP audio output,
and Mesh AI pair-programming (Ports :8081 / :8082 / :4000).

Usage:
  python3 samsung_voice_agent.py --info              # Check audio routes & hardware state
  python3 samsung_voice_agent.py --speak "Message"    # Test audio playback on Samsung/Bluetooth
  python3 samsung_voice_agent.py --listen             # Capture speech from Samsung microphone
  python3 samsung_voice_agent.py --query "Prompt"     # Query Mesh and speak response
  python3 samsung_voice_agent.py --stream             # Stream mic audio to Mac Mini Port 19999
  python3 samsung_voice_agent.py --loop               # Continuous voice pair-programming loop
"""

import sys
import os
import json
import time
import socket
import argparse
import subprocess
import urllib.request
import urllib.error

MAC_MINI_TAILSCALE = "100.119.199.76"
MAC_MINI_LAN = "192.168.8.230"
DEFAULT_MIC_PORT = 19999
MESH_HUB_URL = f"http://{MAC_MINI_TAILSCALE}:4000/api/voice-directive"
LLM_SHARD_URL = f"http://{MAC_MINI_TAILSCALE}:8081/v1/chat/completions"

def run_cmd(cmd_list, timeout=10):
    try:
        res = subprocess.run(cmd_list, capture_output=True, text=True, timeout=timeout)
        return res.returncode, res.stdout.strip(), res.stderr.strip()
    except Exception as e:
        return -1, "", str(e)

def get_audio_info():
    code, stdout, _ = run_cmd(["termux-audio-info"], timeout=5)
    if code == 0 and stdout:
        try:
            return json.loads(stdout)
        except Exception:
            pass
    return {}

def speak(text: str, pitch: float = 1.0, rate: float = 1.05):
    """Speaks text through the Samsung's active audio device (Bluetooth A2DP or Stereo Speakers)."""
    print(f"🔊 Speaking: \"{text}\"")
    cmd = ["termux-tts-speak", "-p", str(pitch), "-r", str(rate), text]
    code, _, err = run_cmd(cmd, timeout=15)
    if code != 0:
        print(f"⚠️ termux-tts-speak error: {err}")
    return code == 0

def listen(prompt: str = "Listening on Tensor G5 mic...") -> str:
    """Listens for speech using the Samsung's hardware microphone and returns transcript."""
    print(f"🎙️ {prompt}")
    code, stdout, err = run_cmd(["termux-speech-to-text"], timeout=20)
    if code == 0 and stdout:
        try:
            data = json.loads(stdout)
            if isinstance(data, dict) and "text" in data:
                return data["text"].strip()
            elif isinstance(data, list) and len(data) > 0 and "text" in data[0]:
                return data[0]["text"].strip()
        except Exception:
            return stdout.strip()
    if err:
        print(f"⚠️ Speech input notice: {err}")
    return ""

def query_mesh(transcript: str) -> dict:
    """Dispatches transcript to the Lauburu Mesh Hub or sharded local Qwen MoE."""
    print(f"🧠 Querying Lauburu Mesh with: \"{transcript}\"")
    lower = transcript.lower()
    if "diff" in lower or "changes" in lower:
        directive = "EXPLAIN_DIFF"
    elif "test" in lower:
        directive = "RUN_TESTS"
    elif "git" in lower or "status" in lower:
        directive = "GIT_STATUS"
    elif "refactor" in lower:
        directive = "REFACTOR"
    elif "commit" in lower:
        directive = "COMMIT"
    else:
        directive = "UNKNOWN"

    payload = json.dumps({
        "directive": directive,
        "action_intent": directive,
        "target": "",
        "raw_transcript": transcript,
        "caller": "samsung_10_pro_xl"
    }).encode("utf-8")

    # Try Port 4000 Hub first
    for endpoint in [f"http://{MAC_MINI_TAILSCALE}:4000/api/voice_coder/directive", f"http://{MAC_MINI_TAILSCALE}:4000/api/voice-directive"]:
        try:
            req = urllib.request.Request(
                endpoint,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=15) as response:
                res_body = response.read().decode("utf-8")
                data = json.loads(res_body)
                spoken = data.get("spoken_summary") or data.get("spokenSummary") or "Directive executed successfully."
                headline = data.get("hud_card", {}).get("headline") or data.get("hudCard", {}).get("headline") or "Success"
                return {
                    "spokenSummary": spoken,
                    "headline": headline,
                    "status": data.get("status", "SUCCESS")
                }
        except Exception:
            continue

    # Fallback to direct llama.cpp / prima.cpp shard (:8081)
    try:
        llm_payload = json.dumps({
            "model": "qwen-moe-80b",
            "messages": [
                {
                    "role": "system",
                    "content": "You are Lauburu Voice Coder. Output a 1-sentence concise spoken summary first, then compact code."
                },
                {"role": "user", "content": transcript}
            ],
            "max_tokens": 256,
            "temperature": 0.2
        }).encode("utf-8")

        req = urllib.request.Request(
            LLM_SHARD_URL,
            data=llm_payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=12) as response:
            res_body = response.read().decode("utf-8")
            data = json.loads(res_body)
            content = data["choices"][0]["message"]["content"]
            lines = [line for line in content.split("\n") if line.strip()]
            spoken = lines[0] if lines else "Task synthesized on local cluster."
            return {
                "spokenSummary": spoken,
                "headline": "Synthesized",
                "status": "SUCCESS",
                "code": content
            }
    except Exception as e2:
        error_msg = f"Mesh unreachable: {e2}"
        print(f"❌ {error_msg}")
        return {
            "spokenSummary": "Could not connect to mesh orchestrator.",
            "headline": "Network Error",
            "status": "ERROR"
        }

def stream_mic_to_mac(duration_sec: int = 15):
    """Records microphone audio and streams it to Mac Mini on Port 19999."""
    print(f"🎙️ Connecting to Mac Mini Port {DEFAULT_MIC_PORT}...")
    sock = None
    for host in [MAC_MINI_LAN, MAC_MINI_TAILSCALE]:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2.0)
            s.connect((host, DEFAULT_MIC_PORT))
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            sock = s
            print(f"🟢 Connected to Mac Mini at {host}:{DEFAULT_MIC_PORT}")
            break
        except Exception:
            continue

    if not sock:
        print("❌ Could not connect to Mac Mini receiver on Port 19999.")
        return False

    temp_audio = "/data/data/com.termux/files/home/temp_mic.raw"
    try:
        print(f"Recording from Samsung mic for {duration_sec}s...")
        run_cmd(["termux-microphone-record", "-f", temp_audio, "-l", str(duration_sec), "-r", "16000", "-c", "1", "-e", "amr_wb"], timeout=duration_sec + 3)
        if os.path.exists(temp_audio):
            with open(temp_audio, "rb") as f:
                data = f.read()
                sock.sendall(data)
            print(f"Sent {len(data)} bytes of audio to Mac Mini.")
            os.remove(temp_audio)
            return True
    finally:
        sock.close()
    return False

def print_status():
    print("=" * 60)
    print("   🎙️ LAUBURU PIXEL 10 PRO XL AUDIO & VOICE AGENT")
    print("=" * 60)
    audio = get_audio_info()
    if audio:
        bt_on = audio.get("BLUETOOTH_A2DP_IS_ON", False)
        sr = audio.get("PROPERTY_OUTPUT_SAMPLE_RATE", "Unknown")
        print(f"  • Bluetooth A2DP Audio  : {'🟢 Connected' if bt_on else '⚪ Disconnected (Stereo Speakers)'}")
        print(f"  • Native Sample Rate    : {sr} Hz")
    else:
        print("  • Audio Info            : Default Hardware Routes")
    print(f"  • Mac Mini Tailscale    : {MAC_MINI_TAILSCALE}")
    print(f"  • Mesh Hub Port 4000    : {MESH_HUB_URL}")
    print(f"  • LLM Shard Port 8081   : {LLM_SHARD_URL}")
    print("=" * 60)

def main():
    parser = argparse.ArgumentParser(description="Lauburu Samsung Voice Coding Agent")
    parser.add_argument("--info", action="store_true", help="Display audio status")
    parser.add_argument("--speak", type=str, help="Speak a text message")
    parser.add_argument("--listen", action="store_true", help="Listen for speech")
    parser.add_argument("--query", type=str, help="Send prompt to mesh and speak response")
    parser.add_argument("--stream", type=int, nargs="?", const=10, help="Stream mic to Mac Mini for N seconds")
    parser.add_argument("--loop", action="store_true", help="Start continuous voice coding loop")

    args = parser.parse_args()

    if args.info or len(sys.argv) == 1:
        print_status()

    if args.speak:
        speak(args.speak)

    if args.listen:
        text = listen()
        print(f"Recognized: \"{text}\"")

    if args.query:
        res = query_mesh(args.query)
        speak(res["spokenSummary"])

    if args.stream is not None:
        stream_mic_to_mac(args.stream)

    if args.loop:
        print_status()
        speak("Lauburu Voice Coding loop ready. Tap or speak your directive.")
        while True:
            try:
                transcript = listen("Say directive or 'exit':")
                if not transcript:
                    time.sleep(1)
                    continue
                if transcript.lower() in ["exit", "quit", "stop"]:
                    speak("Voice coding session terminated.")
                    break
                print(f"🗣️ Spoken: \"{transcript}\"")
                result = query_mesh(transcript)
                speak(result["spokenSummary"])
            except KeyboardInterrupt:
                speak("Goodbye.")
                break

if __name__ == "__main__":
    main()
