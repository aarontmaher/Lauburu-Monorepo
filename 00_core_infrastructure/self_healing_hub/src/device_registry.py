import json
import os
import logging

logger = logging.getLogger(__name__)

class DeviceRegistry:
    def __init__(self, db_path="devices.json"):
        # Resolve path relative to this script just to be safe
        dir_path = os.path.dirname(os.path.realpath(__file__))
        self.db_path = os.path.join(dir_path, db_path)
        self.devices = self.load()

    def load(self):
        """Load devices from the JSON registry."""
        if not os.path.exists(self.db_path):
            logger.warning(f"Device registry {self.db_path} not found. Returning empty dict.")
            self.devices = {}
            return {}
        try:
            with open(self.db_path, "r") as f:
                self.devices = json.load(f)
                return self.devices
        except Exception as e:
            logger.error(f"Error loading device registry: {e}")
            return getattr(self, "devices", {})

    def save(self):
        """Save current devices to the JSON registry."""
        try:
            with open(self.db_path, "w") as f:
                json.dump(self.devices, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving device registry: {e}")
            return False

    def add_or_update_device(self, name, use_ssh=False, device_id=None, ssh_host=None, ssh_port=22, ssh_user="root", ssh_key=None, relay_host=None, relay_cmd=None, current_tier=1):
        """Add a new device or update an existing one."""
        self.devices[name] = {
            "use_ssh": use_ssh,
            "device_id": device_id,
            "ssh_host": ssh_host,
            "ssh_port": ssh_port,
            "ssh_user": ssh_user,
            "ssh_key": ssh_key,
            "relay_host": relay_host,
            "relay_cmd": relay_cmd,
            "current_tier": current_tier
        }
        self.save()
        logger.info(f"Updated registry for device: {name}")

    def rename_device(self, old_name, new_name):
        """Rename a device in the registry."""
        if old_name not in self.devices:
            logger.error(f"Cannot rename: Device {old_name} not found in registry.")
            return False
            
        if new_name in self.devices:
            logger.error(f"Cannot rename: Device {new_name} already exists.")
            return False
            
        # Copy config to new name and delete old
        self.devices[new_name] = self.devices.pop(old_name)
        self.save()
        logger.info(f"Renamed device from {old_name} to {new_name}")
        return True

    def get_all_devices(self):
        return self.devices
