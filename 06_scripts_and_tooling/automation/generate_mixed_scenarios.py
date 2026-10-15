import json
import random
import os

OUTPUT_FILE = "/Volumes/Lauburu-Monorepo/04_data_and_memory/data/mixed_network_healing_dataset.jsonl"
OUT_DIR = "/Volumes/Lauburu-Monorepo/04_data_and_memory/data/mixed_mlx_data"
os.makedirs(OUT_DIR, exist_ok=True)

SYSTEM_PROMPT = "You are the Autonomous Mesh Governor running on an OpenWrt GL.iNet router. When a node connection fails, output a strict JSON object with 'diagnosis' and 'healing_chain'. The healing_chain must escalate starting from the lowest required physical layer."

nodes = [{"name": "Linux_Hub", "mac": "30:E0:44:6D:18:EC", "ip": "192.168.8.2"},
         {"name": "MacBook_Air", "mac": "CA:6B:75:9D:8E:92", "ip": "192.168.8.3"},
         {"name": "Samsung_S20", "mac": "5C:CB:99:05:81:41", "ip": "192.168.8.4"}]

dataset = []
for i in range(500):
    node = random.choice(nodes)
    scenario_type = random.choice(["FULL_FAILURE", "TAILSCALE_ONLY", "WIFI_DOWN"])
    
    if scenario_type == "FULL_FAILURE":
        user_input = f"Diagnostics:\ntarget: {node['name']}\ntailscale status: offline\nping {node['ip']}: Network is unreachable\nbluetooth pan: missing"
        response_json = {
            "diagnosis": f"Total node failure detected on {node['name']}. Escaping to absolute lowest layer.",
            "healing_chain": [
                {"step": 1, "protocol": "ip-less_bluetooth_rf", "command": f"python3 /root/rf_plugin_proxy.py --wake --target {node['mac']}"},
                {"step": 2, "protocol": "bluetooth_pan", "command": f"blueutil --connect {node['mac']}"},
                {"step": 3, "protocol": "ssh", "command": f"ssh -i /root/.ssh/id_rsa aaron@{node['ip']}"},
                {"step": 4, "protocol": "wifi", "command": f"ssh aaron@{node['ip']} 'nmcli radio wifi off && nmcli radio wifi on'"},
                {"step": 5, "protocol": "tailscale", "command": f"ssh aaron@{node['ip']} 'tailscale up'"}
            ]
        }
    elif scenario_type == "TAILSCALE_ONLY":
        user_input = f"Diagnostics:\ntarget: {node['name']}\ntailscale status: NeedsLogin\nping {node['ip']}: 64 bytes from {node['ip']} time=1.2ms\nbluetooth pan: active"
        response_json = {
            "diagnosis": f"Wi-Fi and PAN are healthy on {node['name']}. Tailscale overlay auth dropped.",
            "healing_chain": [
                {"step": 1, "protocol": "ssh", "command": f"ssh -i /root/.ssh/id_rsa aaron@{node['ip']}"},
                {"step": 2, "protocol": "tailscale", "command": f"ssh aaron@{node['ip']} 'tailscale up --authkey=tskey-auth-XYZ'"}
            ]
        }
    else: # WIFI_DOWN
        user_input = f"Diagnostics:\ntarget: {node['name']}\ntailscale status: offline\nping {node['ip']}: Network is unreachable\nbluetooth pan: active"
        response_json = {
            "diagnosis": f"Wi-Fi is down on {node['name']}. Bluetooth PAN is active. Using PAN to restore Wi-Fi.",
            "healing_chain": [
                {"step": 1, "protocol": "ssh", "command": f"ssh -i /root/.ssh/id_rsa aaron@{node['ip']}"},
                {"step": 2, "protocol": "wifi", "command": f"ssh aaron@{node['ip']} 'nmcli radio wifi on'"},
                {"step": 3, "protocol": "tailscale", "command": f"ssh aaron@{node['ip']} 'tailscale up'"}
            ]
        }
        
    conversation = {
        "text": f"<|im_start|>system\n{SYSTEM_PROMPT}<|im_end|>\n<|im_start|>user\n{user_input}<|im_end|>\n<|im_start|>assistant\n{json.dumps(response_json)}<|im_end|>\n"
    }
    dataset.append(conversation)

random.shuffle(dataset)
train_data, valid_data = dataset[:450], dataset[450:]

with open(os.path.join(OUT_DIR, "train.jsonl"), "w") as f:
    for item in train_data: f.write(json.dumps(item) + '\n')
with open(os.path.join(OUT_DIR, "valid.jsonl"), "w") as f:
    for item in valid_data: f.write(json.dumps(item) + '\n')

print(f"Generated {len(dataset)} mixed scenarios.")
