#!/usr/bin/env python3
import time
import glob
import os
import sys
sys.path.append(os.path.expanduser('~/.local/lib/python3.14/site-packages'))
sys.path.append(os.path.expanduser('~/Library/Python/3.14/lib/python/site-packages'))

import requests
from google import genai
from dotenv import load_dotenv

load_dotenv(os.path.expanduser("~/.env"))

# Fallback: if GEMINI_API_KEY is not in env, we just grab it directly from os.getenv
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Use Port 8081 for the tiny local AI as 8082 was unavailable
TINY_AI_URL = "http://127.0.0.1:8081/v1/chat/completions"

def get_gemini_client():
    # If GEMINI_API_KEY is missing, we still instantiate it and let the SDK handle auth via default ways.
    return genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else genai.Client()

def compress_logs_local_ai(logs):
    if not logs:
        return f"**System Alert:** Gemini API Request failed. Raw logs appended:\n\n{compressed_text}"
    # If it's too big, truncate to avoid overflowing the local context window (max ~32k).
    # Let's say last 200 lines.
    recent_logs = logs[-200:]
    prompt = "Compress and summarize the following AI terminal transcripts. Focus on key system events, AI thought processes, errors, and task progress. Output a dense, concise summary.\n\n" + "\n".join(recent_logs)
    if len(prompt) > 8000:
        prompt = prompt[-8000:]
    
    payload = {
        "model": "qwen2.5-coder-7b-instruct-q4_k_m.gguf",
        "messages": [
            {"role": "system", "content": "You are a highly efficient local telemetry compression engine. Deliver compact, bulleted summaries of system logs."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3
    }
    try:
        resp = requests.post(TINY_AI_URL, json=payload, timeout=1.0)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except requests.exceptions.Timeout:
        print("[Warning] Local AI (Port 8081) timed out. Falling back to uncompressed snippet.")
        return prompt
    except Exception as e:
        print(f"[Error] Local AI Request failed: {e}")
        return prompt

def overview_gemini(compressed_text, client):
    prompt = (
        "Based on the following compressed terminal logs from the local swarm, "
        "provide a high-level continuous overview of the system's state, ongoing tasks, "
        "and any critical issues. Format as a markdown report.\n\n"
        f"{compressed_text}"
    )
    try:
        response = client.models.generate_content(
            model='gemini-3.8-flash',
            contents=prompt
        )
        return response.text
    except Exception as e:
        print(f"[Error] Gemini API Request failed: {e}")
        return f"**System Alert:** Gemini API Request failed. Raw logs appended:\n\n{compressed_text}"

def tail_files(file_pattern, file_positions):
    files = glob.glob(file_pattern)
    new_logs = []
    
    for f in files:
        if f not in file_positions:
            # Initialize with current size to not read ancient history on startup, 
            # or 0 to read from start. Given "continuous overview", starting from current size is safer.
            file_positions[f] = os.path.getsize(f)
            
        try:
            size = os.path.getsize(f)
            if size < file_positions[f]:
                # File was truncated or rotated
                file_positions[f] = 0
                
            if size > file_positions[f]:
                with open(f, 'r', encoding='utf-8', errors='ignore') as fd:
                    fd.seek(file_positions[f])
                    lines = fd.readlines()
                    file_positions[f] = fd.tell()
                    for line in lines:
                        if line.strip():
                            new_logs.append(line.strip())
        except Exception as e:
            print(f"[Error] Could not read {f}: {e}")
            
    return new_logs

def main():
    pattern = "/Users/aaron/.gemini/antigravity/brain/*/.system_generated/logs/transcript.jsonl"
    out_file = "/Volumes/Lauburu-Monorepo/obsidian_vault/04_ANALYTICS/GEMINI_CONTINUOUS_OVERVIEW.md"
    
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    
    print("Initializing Gemini Client...")
    client = get_gemini_client()
    file_positions = {}
    
    print(f"Tracking logs matching: {pattern}")
    print(f"Outputting overview to: {out_file}")
    print("Starting Terminal Stream Sentinel daemon loop...")
    
    while True:
        try:
            new_logs = tail_files(pattern, file_positions)
            if new_logs:
                print(f"[{time.strftime('%H:%M:%S')}] Found {len(new_logs)} new log lines. Compressing via Local AI...")
                compressed = compress_logs_local_ai(new_logs)
                
                if compressed:
                    print(f"[{time.strftime('%H:%M:%S')}] Local compression complete. Generating overview via Gemini...")
                    overview = overview_gemini(compressed, client)
                    
                    if overview:
                        with open(out_file, 'w', encoding='utf-8') as f:
                            f.write(f"# 🧠 Gemini Continuous Swarm Overview\n\n")
                            f.write(f"**Last Updated:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                            f.write("---\n\n")
                            f.write(overview)
                        print(f"[{time.strftime('%H:%M:%S')}] Successfully updated {out_file}")
            
        except Exception as e:
            print(f"[Fatal Error in Main Loop] {e}")
            
        time.sleep(15)

if __name__ == "__main__":
    main()
