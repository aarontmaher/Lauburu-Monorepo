#!/usr/bin/env python3
import sys
import json
import subprocess
import os
import requests

ROUTER_IP = "192.168.8.1"
SSH_USER = "root"

def query_shadow_consensus(proposed_action):
    """
    Queries the tri-model shadow consensus (Local + Cloud) to get approval
    before executing potentially destructive router commands.
    """
    print(f"[*] Lens Intelligence: Seeking Shadow Consensus for action: {proposed_action}")
    
    # 1. Ask Qwen 3.8 Max (Port 8082 - Sovereign Master)
    local_consensus = False
    try:
        res_local = requests.post("http://127.0.0.1:8082/v1/chat/completions", json={
            "model": "qwen_38_max",
            "messages": [
                {"role": "system", "content": "You are the Mesh Guardian. You must approve or reject router configuration changes. Output strictly 'AGREE' or 'REJECT'."},
                {"role": "user", "content": f"Proposed action on router {ROUTER_IP}: {proposed_action}"}
            ]
        }, timeout=30)
        if res_local.status_code == 200 and "AGREE" in res_local.json()["choices"][0]["message"]["content"]:
            local_consensus = True
    except Exception as e:
        print(f"[!] Local consensus failed: {e}")

    # 2. If Local agrees, ask Cloud (Gemini)
    cloud_consensus = False
    if local_consensus:
        try:
            # Invoking agy CLI for Gemini Cloud consensus
            import shutil
            agy_bin = shutil.which("agy") or "/Users/aaron/.local/bin/agy"
            cmd = [agy_bin, '--model', 'gemini-3.1-pro-high', '-p', f"You are the Mesh Cloud Auditor. Approve or reject this router action: '{proposed_action}'. Respond strictly with 'AGREE' or 'REJECT'."]
            res_cloud = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if "AGREE" in res_cloud.stdout:
                cloud_consensus = True
        except Exception as e:
            print(f"[!] Cloud consensus failed: {e}")

    if local_consensus and cloud_consensus:
        print("[+] Tri-Model Shadow Consensus ACHIEVED. Execution Authorized.")
        return True
    else:
        print("[-] Consensus FAILED (Local: {}, Cloud: {}). Execution Rejected.".format(local_consensus, cloud_consensus))
        return False

def execute_router_ssh(command):
    """Executes a command on the GL.iNet router via SSH if consensus passes."""
    if not query_shadow_consensus(command):
        return {"error": "Rejected by Shadow Consensus Gate"}
    
    ssh_cmd = f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 {SSH_USER}@{ROUTER_IP} '{command}'"
    print(f"[*] Executing over SSH: {ssh_cmd}")
    try:
        res = subprocess.run(ssh_cmd, shell=True, capture_output=True, text=True, timeout=30)
        return {"stdout": res.stdout, "stderr": res.stderr, "code": res.returncode}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Missing arguments"}))
        sys.exit(1)
        
    action = sys.argv[1]
    
    if action == "router_remediate":
        # python3 lens_intelligence_router.py router_remediate "/etc/init.d/mwan3 restart"
        command = sys.argv[2]
        print(json.dumps(execute_router_ssh(command)))
    elif action == "listen":
        print("[*] Lens AI Listener started on canonical Mesh folder...")
        print("    -> Ready to intercept AI protocols.")
        while True:
            import time
            time.sleep(10)
    else:
        print(json.dumps({"error": "Unknown action"}))
