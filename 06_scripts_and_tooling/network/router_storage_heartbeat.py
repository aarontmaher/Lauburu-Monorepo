import os
import time

ROUTER_MOUNT_PATH = "/Volumes/GL_Router_Storage"
OBSIDIAN_VAULT_ROUTER_PATH = os.path.join(ROUTER_MOUNT_PATH, "obsidian_vault")
HEARTBEAT_LOCKFILE = os.path.join(ROUTER_MOUNT_PATH, ".heartbeat.lock")

def check_router_storage_health():
    """
    Validates the hybrid 'Trigger Layer' storage on the GL.iNet Router.
    If this fails, the Nomad Courier will trigger network healing to the Linux Head node.
    """
    if not os.path.exists(ROUTER_MOUNT_PATH):
        return False, "ROUTER_MOUNT_DROPPED"
    
    try:
        # Update heartbeat lockfile
        with open(HEARTBEAT_LOCKFILE, "w") as f:
            f.write(str(time.time()))
        return True, "HEALTHY"
    except Exception as e:
        return False, f"LOCKFILE_ERROR: {e}"

if __name__ == "__main__":
    health, status = check_router_storage_health()
    print(f"Router Storage Status: {status}")
