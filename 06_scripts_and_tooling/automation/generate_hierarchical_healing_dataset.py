import json
import random
import os

OUTPUT_FILE = "/Volumes/Lauburu-Monorepo/04_data_and_memory/data/router_network_healing_dataset.jsonl"

SYSTEM_PROMPT = "You are the Autonomous Mesh Governor running on an OpenWrt GL.iNet router. When a node connection fails, you must output a strictly formatted JSON object with 'diagnosis' and 'healing_chain'. The healing_chain MUST follow the exact hierarchical order: 1) ip-less_bluetooth_rf, 2) bluetooth_pan, 3) ssh, 4) wifi, 5) tailscale."

node_macs = ["30:E0:44:6D:18:EC", "CA:6B:75:9D:8E:92", "5C:CB:99:05:81:41"]
node_ips = ["192.168.8.2", "192.168.8.3", "192.168.8.4"]
node_names = ["Linux_Hub", "MacBook_Air", "Pixel_10"]

dataset = []
for i in range(500):
    idx = random.randint(0, 2)
    name = node_names[idx]
    mac = node_macs[idx]
    ip = node_ips[idx]
    
    user_input = f"Diagnostics:\ntarget: {name}\ntailscale status: offline\nping {ip}: Network is unreachable\nuptime: {random.randint(1000, 9999)}s"
    
    response_json = {
        "diagnosis": f"{name} is fully disconnected from high-level routing.",
        "healing_chain": [
            {"step": 1, "protocol": "ip-less_bluetooth_rf", "command": f"python3 /root/rf_plugin_proxy.py --wake --target {mac}"},
            {"step": 2, "protocol": "bluetooth_pan", "command": f"blueutil --connect {mac}"},
            {"step": 3, "protocol": "ssh", "command": f"ssh -i /root/.ssh/id_rsa aaron@{ip}"},
            {"step": 4, "protocol": "wifi", "command": f"ssh aaron@{ip} 'nmcli radio wifi off && nmcli radio wifi on'"},
            {"step": 5, "protocol": "tailscale", "command": f"ssh aaron@{ip} 'tailscale up'" }
        ]
    }
    
    conversation = {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_input},
            {"role": "assistant", "content": json.dumps(response_json)}
        ]
    }
    dataset.append(conversation)

os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
with open(OUTPUT_FILE, 'w') as f:
    for item in dataset:
        f.write(json.dumps(item) + '\n')

print(f"Generated {len(dataset)} hierarchical healing training samples.")
