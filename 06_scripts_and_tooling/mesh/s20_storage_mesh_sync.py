#!/data/data/com.termux/files/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Lauburu Mesh: S20+ On-Device Storage Mesh Synchronization Agent
Runs locally in Termux on Samsung Galaxy S20+ (L7).
Synchronizes /sdcard/DFS_UNIFIED with SeaweedFS WebDAV / Filer cluster.
"""

import os
import sys
import time
import hashlib
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

STORAGE_DIR = Path("/sdcard/DFS_UNIFIED")
WEBDAV_URL = "http://192.168.8.230:7333/edge_mounts/samsung_s20"

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def test_webdav_sync():
    print("=== S20+ Termux Storage Mesh Sync Test ===")
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. Create canary file on S20
    now_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    canary_name = f"canary_termux_s20_{now_str}.txt"
    canary_path = STORAGE_DIR / canary_name
    canary_data = f"TERMUX_ORIGIN=Samsung_S20|TIME={now_str}|STORAGE_CLUSTER=SeaweedFS_WebDAV\n".encode("utf-8")
    
    with open(canary_path, "wb") as f:
        f.write(canary_data)
    local_sha = sha256_file(canary_path)
    print(f"[*] Created local canary: {canary_path}")
    print(f"    Local SHA256: {local_sha}")
    
    # 2. Upload to SeaweedFS WebDAV
    target_url = f"{WEBDAV_URL}/{canary_name}"
    print(f"[*] Uploading to WebDAV: {target_url}")
    try:
        req = urllib.request.Request(target_url, data=canary_data, method='PUT')
        with urllib.request.urlopen(req, timeout=5) as resp:
            print(f"    HTTP Status: {resp.status}")
    except Exception as e:
        print(f"    Upload failed: {e}")
        return False
        
    # 3. Read back and verify
    print(f"[*] Reading back from WebDAV: {target_url}")
    try:
        with urllib.request.urlopen(target_url, timeout=5) as resp:
            remote_bytes = resp.read()
            remote_sha = sha256_bytes(remote_bytes)
            print(f"    Remote SHA256: {remote_sha}")
            if remote_sha == local_sha:
                print("    [✓] SHA256 VERIFIED: End-to-end data integrity confirmed!")
                return True
            else:
                print("    [!] Checksum mismatch!")
                return False
    except Exception as e:
        print(f"    Readback failed: {e}")
        return False

if __name__ == '__main__':
    ok = test_webdav_sync()
    sys.exit(0 if ok else 1)
