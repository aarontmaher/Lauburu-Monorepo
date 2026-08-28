#!/usr/bin/env python3
import os
import sys
import json
import time
from datetime import datetime

CHANNEL_FILE = "/Volumes/NAS/projects/ai_shared_channel.json"
LOCAL_LOG = os.getenv("AI_LISTENER_LOG", "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/data/ai_channel_listener.log")
CHECK_INTERVAL = 5  # seconds

def log_local(message):
    try:
        with open(LOCAL_LOG, "a") as f:
            f.write(message + "\n")
    except Exception as e:
        print(f"Error writing to local log: {e}", file=sys.stderr)

def get_messages():
    if not os.path.exists(CHANNEL_FILE):
        return []
    try:
        with open(CHANNEL_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []

def main():
    log_local(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Shared AI Channel Listener started.")
    last_idx = 0
    
    # Initialize index with current messages
    try:
        last_idx = len(get_messages())
    except Exception:
        pass

    while True:
        try:
            messages = get_messages()
            if len(messages) > last_idx:
                for i in range(last_idx, len(messages)):
                    msg = messages[i]
                    formatted = f"[{msg['timestamp']}] {msg['device']}: {msg['message']}"
                    log_local(formatted)
                last_idx = len(messages)
        except Exception as e:
            log_local(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error in listener loop: {e}")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
