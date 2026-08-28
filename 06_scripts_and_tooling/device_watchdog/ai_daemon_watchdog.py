#!/usr/bin/env python3
import time
import subprocess
import json
import os
import sys

def check_router_daemon():
    # Push the latest trends file so the router doesn't starve
    subprocess.run("cat /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/mesh_trends.json | ssh root@192.168.8.1 'cat > /tmp/mesh_trends.json'", shell=True, stderr=subprocess.DEVNULL)
    
    # Check if process is running
    res = subprocess.run(["ssh", "root@192.168.8.1", "pgrep -f genetic_mesh_optimizer"], capture_output=True, text=True)
    if res.returncode != 0:
        # Not running, restart it
        print("Router daemon offline. Restarting...")
        subprocess.run("cat /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/05_agents_and_swarms/genetic_mesh_optimizer.py | ssh root@192.168.8.1 'cat > /tmp/genetic_mesh_optimizer.py'", shell=True)
        subprocess.run(["ssh", "root@192.168.8.1", "start-stop-daemon -S -b -m -p /tmp/ga.pid -x python3 -- /tmp/genetic_mesh_optimizer.py"])
        return "RESTARTED"
    return "ACTIVE"

def main():
    print("Starting AI Daemon Watchdog...")
    status_file = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/watchdog_status.json"
    
    while True:
        r_status = check_router_daemon()
        status = {
            "timestamp": time.time(),
            "daemons": {
                "router_genetic_optimizer": r_status,
                "ai_debate_sync": "ACTIVE"  # Hardcoded for now
            }
        }
        with open(status_file + ".tmp", "w") as f:
            json.dump(status, f)
        os.rename(status_file + ".tmp", status_file)
        time.sleep(10)

if __name__ == "__main__":
    main()
