import os
import shutil
import time
import subprocess
import json

class StorageMeshGovernor:
    def __init__(self):
        self.nodes = {
            "L1_Mac_Node": "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo",
            "L3_Linux_Head": "/Volumes/nas", # Assuming NAS or Linux mount
            "GW_Router": "/Volumes/GL_Router_Storage",
            "SeaweedFS_Joint_Capacity": "/Users/aaron/DFS_UNIFIED"
        }
        self.min_headroom_gb = 25.0 # Safety threshold to prevent silent crash

    def check_headroom(self, path):
        if not os.path.exists(path):
            return -1.0
        try:
            free_bytes = shutil.disk_usage(path).free
            return free_bytes / (1024**3)
        except Exception:
            return -1.0

    def trigger_critical_alert(self, message):
        """Broadcasts via macOS Notification and logs it loudly."""
        print(f"[CRITICAL ALERT] {message}")
        try:
            # macOS native notification
            apple_script = f'display notification "{message}" with title "⚠️ Tri-Vault Storage Governor"'
            subprocess.run(["osascript", "-e", apple_script])
            
            # Optional: Broadcast via KDE connect if available to reach S20/Pixel
            # subprocess.run(["kdeconnect-cli", "-a", "--ping-msg", message])
        except Exception:
            pass

    def evaluate_and_route(self):
        routing_table = {}
        mac_free = self.check_headroom(self.nodes["L1_Mac_Node"])
        
        # 1. Evaluate Primary Data Lake (Mac Mini)
        if mac_free != -1.0 and mac_free < self.min_headroom_gb:
            alert_msg = f"Mac Mini Local Node CRITICAL ({mac_free:.1f} GB). Triggering SeaweedFS Volume Rebalance to Joint Mesh Capacity."
            self.trigger_critical_alert(alert_msg)
            routing_table["primary_write"] = "SeaweedFS_Joint_Capacity"  # Failover
            routing_table["mac_status"] = "FULL_LOCKED"
        else:
            routing_table["primary_write"] = "L1_Mac_Node"
            routing_table["mac_status"] = "HEALTHY"
            
        # 2. Evaluate Trigger Layer (Router)
        router_free = self.check_headroom(self.nodes["GW_Router"])
        if router_free == -1.0:
            routing_table["router_status"] = "OFFLINE_OR_UNMOUNTED"
        else:
            routing_table["router_status"] = f"HEALTHY ({router_free:.1f} GB)"

        # Save routing state for Canonical TUI to ingest
        state_file = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/storage_routing_state.json"
        os.makedirs(os.path.dirname(state_file), exist_ok=True)
        try:
            with open(state_file, "w") as f:
                json.dump(routing_table, f)
        except Exception:
            pass

        return routing_table

if __name__ == "__main__":
    governor = StorageMeshGovernor()
    state = governor.evaluate_and_route()
    print(json.dumps(state, indent=2))
