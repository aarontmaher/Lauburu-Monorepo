import requests
import time
import json
import subprocess

MASTER_URL = "http://10.1.0.12:9333"
FILER_URL = "http://10.1.0.12:8888"
LENS_TRIGGER = "/Volumes/Lauburu-Monorepo/01_apps/screen_lens/src/trigger_lens.sh" # Assumed path

def get_topology():
    try:
        r = requests.get(f"{MASTER_URL}/dir/status", timeout=5)
        return r.json()
    except:
        return None

def check_balance(topology):
    if not topology: return False
    
    try:
        nodes = topology['Topology']['DataCenters'][0]['Racks'][0]['DataNodes']
        vols = [n['Volumes'] for n in nodes]
        if max(vols) - min(vols) > 5:
            return True # Imbalanced
    except:
        pass
    return False

def main():
    while True:
        topo = get_topology()
        if topo:
            imbalanced = check_balance(topo)
            if imbalanced:
                print("DFS Imbalance detected. Triggering Screen Lens Sovereign for structural reorganization.")
                # We log this for Screen Lens to observe
                with open("/Volumes/Lauburu-Monorepo/obsidian_vault/DFS_LENS_OBSERVATIONS.md", "a") as f:
                    f.write(f"\n- [IMBALANCE DETECTED]: Volume skew detected across {len(topo['Topology']['DataCenters'][0]['Racks'][0]['DataNodes'])} nodes. Needs rebalancing.\n")
                
                # In a real scenario, this would call Screen Lens MCP or API
                # subprocess.run(["bash", LENS_TRIGGER, "dfs_rebalance"])
        
        time.sleep(300) # Check every 5 minutes

if __name__ == "__main__":
    main()
