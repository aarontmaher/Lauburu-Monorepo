#!/usr/bin/env python3
"""
Cloud Peer-Review Auditor for Tri-Proof Verification Gate (Rule #5)
Queries Google AI Studio (Gemini 2.5 Flash / Flash-Lite) to adversarially review
the empirical proofs collected from the Lauburu Mesh cluster.
"""

import os
import json
import urllib.request
import urllib.error

GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")

prompt = """
You are an adversarial Cloud Security & Distributed Systems Auditor.
Review the following empirical tri-proofs provided for the Lauburu 7-Layer Mesh deployment:

1. Actuation Proofs:
   - Samsung S20+ Sovereign Router Control Center: HTTP 200 at http://192.168.8.131:9090/health (Shizuku bridge verified, uid=2000 shell execution).
   - Router Health: GL-BE14000 gateway running with 2.0GB RAM, 2.0GB active swap (/overlay/swapfile), 1.29GB free.
   - Neo AI Engine: Running on L8 Linux Mini (AMD Ryzen 7, 32GB RAM) at http://192.168.2.3:8080/health with HTTP 200 {"status":"ok"}, preserving Mac Mini host sanctuary.
   - SeaweedFS Mobile DFS Pool: Samsung S20+ and Pixel 10 Pro XL synchronized into SeaweedFS WebDAV at http://100.119.199.76:7333 via rclone (60GB S20+ and 181GB Pixel 10 pool verified).
   - WireGuard Public IPv6: Native endpoint [2401:d006:c100::181]:51820 active on router; utun5 (10.1.0.10) active on Mac Mini.

2. Line-by-Line Cryptographic Checksums:
   - nexus_extension_provisioner.py: 31983 bytes | SHA256: 986e4d67088ed27a4d78d3ca78f51f146d57423a880eddd9eeef68660c508d6f
   - mobile_dfs_sync.sh: 2127 bytes | SHA256: 1c03363ccccecf42952be5ed02293e291b9dcaa524320b1483ae9ffe723c9ade
   - s20_router_control_agent.py: 7466 bytes | SHA256: a4404f877a30ec5193f8d86b2a6b4d2cf370f4c5d2561b9a0dd14de63aadf24a
   - wireguard_manager.py: 3910 bytes | SHA256: 9a1b34030a33573ab1afdfcc4b81b185c9fc083eec9e6b38bbb2d886426e4c38
   - DEBATE_SCREEN_LENS_MCP.md: 12269 bytes | SHA256: 35583173669b5df3540da3c68418d34da400390ec4c6a26fa6175a74cb82f140

3. Visual Verification:
   - Samsung S20+ live screen capture (240KB PNG) verified showing Termux/Shizuku running with battery at 45% charging.

Task:
Provide a concise, adversarial peer-review:
- Verify empirical authenticity
- Highlight any architectural risks or edge cases
- Give 2-3 concrete optimizations or next-level methods for network resilience and local AI throughput.
"""

url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_KEY}"
headers = {"Content-Type": "application/json"}
body = {
    "contents": [{"parts": [{"text": prompt}]}],
    "generationConfig": {"temperature": 0.2, "maxOutputTokens": 800}
}

req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers)
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        review_text = data["candidates"][0]["content"]["parts"][0]["text"]
        print("=== 🌟 GOOGLE AI STUDIO GEMINI CLOUD AUDIT VERDICT ===")
        print(review_text)
        
        # Save audit to Obsidian vault
        audit_path = "/Volumes/Lauburu-Monorepo/obsidian_vault/APPS_AND_FEATURES/CLOUD_PROOF_AUDIT_VERDICT.md"
        with open(audit_path, "w", encoding="utf-8") as f:
            f.write(f"# 🌟 Cloud Peer-Review Audit Verdict (Rule #5)\n\n{review_text}\n")
        print(f"\n✓ Saved audit review to {audit_path}")
except Exception as e:
    print(f"Cloud Audit Error: {e}")
