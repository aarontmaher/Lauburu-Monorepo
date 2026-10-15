import json
import random
import os

OUTPUT_FILE = "/Volumes/Lauburu-Monorepo/04_data_and_memory/data/router_network_healing_dataset.jsonl"

SYSTEM_PROMPT = "You are the Autonomous Mesh Governor running on an OpenWrt GL.iNet router. Analyze the system diagnostics and output a strictly formatted JSON object with 'action' and 'command' to heal the network. If healthy, action is 'none'."

scenarios = [
    {
        "diag": "tailscale status\n# Health check:\n#     - state: NeedsLogin",
        "action": "restart_tailscale",
        "command": "tailscale up --authkey=tskey-auth-XYZ"
    },
    {
        "diag": "hciconfig hci0\nhci0: Type: Primary  Bus: USB\n\tDOWN\n\tRX bytes:310 acl:0 sco:0 events:18 errors:0",
        "action": "reset_bluetooth_rf",
        "command": "hciconfig hci0 up"
    },
    {
        "diag": "ping -c 1 8.8.8.8\nping: sendto: Network is unreachable",
        "action": "restart_wan",
        "command": "/etc/init.d/network restart"
    },
    {
        "diag": "tailscale status\n100.119.199.76  Mac-Host  offline",
        "action": "ping_fallback_pan",
        "command": "ping -c 3 192.168.2.2" # Ping Mac Host PAN IP
    },
    {
        "diag": "tailscale status\n100.119.199.76  Mac-Host  active; direct",
        "action": "none",
        "command": "echo 'Network Healthy'"
    },
    {
        "diag": "hciconfig hci0\nhci0: Type: Primary  Bus: USB\n\tUP RUNNING\n\tRX bytes:9042 acl:120 sco:0 events:431 errors:0",
        "action": "none",
        "command": "echo 'RF Healthy'"
    }
]

# Generate permutations to build a robust LoRA dataset
dataset = []
for i in range(500):
    scenario = random.choice(scenarios)
    # Add some noise to the diagnostics to make the model robust
    noise = f"uptime: {random.randint(1000, 9999)}s\n"
    user_input = noise + scenario["diag"]
    
    conversation = {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Diagnostics:\n{user_input}"},
            {"role": "assistant", "content": json.dumps({"action": scenario["action"], "command": scenario["command"]})}
        ]
    }
    dataset.append(conversation)

os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
with open(OUTPUT_FILE, 'w') as f:
    for item in dataset:
        f.write(json.dumps(item) + '\n')

print(f"Generated {len(dataset)} training samples at {OUTPUT_FILE}")
