import json
import os
import time
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class LoraLogger:
    def __init__(self, log_path="/Volumes/Google Drive/My Drive/Lauburu_AI_Memory/lora_datasets/network_telemetry.jsonl"):
        self.log_path = log_path
        self._ensure_directory()

    def _ensure_directory(self):
        try:
            os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        except Exception as e:
            logger.warning(f"Could not create Google Drive directory (might not be mounted). Using local fallback. Error: {e}")
            self.log_path = "local_network_telemetry.jsonl"

    def log_telemetry_event(self, state, action, success):
        """
        Logs a telemetry event formatted for LoRA training.
        :param state: Dict representing the environment state (battery, network rates, current tier).
        :param action: String representing the action taken (e.g., 'switch_to_tailscale', 'none').
        :param success: Boolean or String representing if the action resolved the state.
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "unix_time": time.time(),
            "state": state,
            "action": action,
            "success": success
        }
        
        try:
            with open(self.log_path, 'a') as f:
                f.write(json.dumps(entry) + '\n')
        except Exception as e:
            logger.error(f"Failed to write to LoRA dataset log: {e}")
