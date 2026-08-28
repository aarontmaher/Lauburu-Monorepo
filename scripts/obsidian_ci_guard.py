#!/usr/bin/env python3
import os
import json
import hashlib
import urllib.request
import urllib.parse
from datetime import datetime

VAULT_DIR = os.path.expanduser("~/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault")
CACHE_FILE = os.path.expanduser("~/DFS_UNIFIED/Lauburu-Monorepo/logs/obsidian_hash_cache.json")
LOG_FILE = os.path.expanduser("~/DFS_UNIFIED/Lauburu-Monorepo/logs/system_crons.log")
FRONTEND_URL = "http://127.0.0.1:4000/api/telemetry"

# Strict Global Rules against hardware hallucinations
BANNED_METRICS = {
    "62.8 GB": "82.8 GB",
    "62.8": "82.8",
    "M4 Mac Max": "M4 Mac Mini",
    "Mac Max": "Mac Mini"
}

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] [OBSIDIAN_GUARD] {msg}\n")
    print(f"[{timestamp}] [OBSIDIAN_GUARD] {msg}")

def get_md5(filepath):
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def main():
    if not os.path.exists(VAULT_DIR):
        log("Vault directory not found. Exiting.")
        return

    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            cache = json.load(f)
    else:
        cache = {}

    scanned = 0
    modified = 0
    hallucinations_fixed = 0

    log("Initiating Obsidian integrity sweep (Architecture: MD5 + JSON Cache)...")

    for root, _, files in os.walk(VAULT_DIR):
        for file in files:
            if file.endswith(".md"):
                scanned += 1
                filepath = os.path.join(root, file)
                file_hash = get_md5(filepath)
                
                # Compare MD5 Fingerprint to Cache
                if cache.get(filepath) != file_hash:
                    modified += 1
                    
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    needs_fix = False
                    for bad, good in BANNED_METRICS.items():
                        if bad in content:
                            content = content.replace(bad, good)
                            needs_fix = True
                            hallucinations_fixed += 1
                            log(f"HALLUCINATION ERADICATED in {file}: Replaced '{bad}' with '{good}'")
                    
                    if needs_fix:
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(content)
                        # Re-hash after automated remediation
                        file_hash = get_md5(filepath)

                    # Update cache state
                    cache[filepath] = file_hash

    # Save Cache
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f)

    log(f"Sweep Complete: {scanned} tracked | {modified} changed | {hallucinations_fixed} fixed.")

    # Push to Frontend Dashboard
    payload = json.dumps({
        "agent": "Obsidian_CI_Guard",
        "status": "pass",
        "metrics": {
            "files_scanned": scanned,
            "files_modified": modified,
            "hallucinations_fixed": hallucinations_fixed,
            "architecture": "MD5_JSON_Cache"
        }
    }).encode('utf-8')
    
    try:
        req = urllib.request.Request(FRONTEND_URL, data=payload, headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass # Silently fail if dashboard is offline

if __name__ == "__main__":
    main()
