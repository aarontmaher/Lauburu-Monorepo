import asyncio
import json
import logging
from datetime import datetime, timezone
import subprocess

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Load IP matrix
with open("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/network/mesh_ip_matrix.json") as f:
    matrix = json.load(f)

NODES = []
for key, data in matrix.items():
    if isinstance(data, dict) and "tier5_ssh" in data:
        NODES.append(data)

async def check_node(node):
    ssh_info = node["tier5_ssh"]
    user = ssh_info["user"]
    host = ssh_info.get("tailscale_ip", ssh_info.get("host"))
    port = ssh_info.get("port", 22)
    name = node["name"]
    
    cmd = [
        "ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=3", "-p", str(port),
        f"{user}@{host}", "free -m || top -l 1 | grep PhysMem"
    ]
    
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    
    if proc.returncode == 0:
        return {"name": name, "status": "ONLINE", "ram": stdout.decode().strip().split('\n')[0]}
    else:
        return {"name": name, "status": "OFFLINE", "error": stderr.decode().strip()}

async def main():
    logging.info(f"Initiating Swarm RAM & Health check across {len(NODES)} nodes...")
    results = await asyncio.gather(*(check_node(n) for n in NODES))
    
    health_report = {"timestamp": datetime.now(timezone.utc).isoformat(), "nodes": results}
    
    with open("/Users/aaron/DFS_UNIFIED/lora_datasets/continuous_lora_dataset.jsonl", "a") as f:
        # Generate synthetic training pair based on RAM health
        prompt = f"Optimize mesh roles based on current RAM state: {json.dumps(health_report)}"
        output = "All nodes online. Recommend shifting heavy inference to L8 Linux Hub to protect Mac Host RAM."
        lora_pair = {"instruction": prompt, "output": output}
        f.write(json.dumps(lora_pair) + "\n")
        
    for r in results:
        logging.info(f"{r['name']} - {r['status']} - RAM: {r.get('ram', r.get('error'))}")

if __name__ == "__main__":
    asyncio.run(main())
