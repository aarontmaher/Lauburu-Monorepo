import urllib.request
from pathlib import Path
import hashlib

def capture_and_hash(url, save_path):
    print(f"Fetching {url}...")
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as res:
            data = res.read()
            Path(save_path).write_bytes(data)
            sha256 = hashlib.sha256(data).hexdigest()
            print(f"Saved: {save_path} (Size: {len(data)} bytes, SHA256: {sha256})")
    except Exception as e:
        print(f"Failed to fetch {url}: {e}")

capture_and_hash("http://127.0.0.1:4003/api/node/l1_mac_host/frame", "/Users/aaron/.gemini/antigravity/brain/7b3e82a1-19b0-4226-9058-a888fd5aea67/l1_mac_host_proof.jpg")
capture_and_hash("http://127.0.0.1:4003/api/node/l7_samsung/frame", "/Users/aaron/.gemini/antigravity/brain/7b3e82a1-19b0-4226-9058-a888fd5aea67/l7_samsung_tui_proof.jpg")
capture_and_hash("http://127.0.0.1:4003/api/node/l2_macbook_pro/frame", "/Users/aaron/.gemini/antigravity/brain/7b3e82a1-19b0-4226-9058-a888fd5aea67/l2_macbook_pro_proof.jpg")
