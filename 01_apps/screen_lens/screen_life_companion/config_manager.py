import json
import os
from pathlib import Path

CONFIG_PATH = os.path.expanduser("~/.lauburu/config.json")

DEFAULT_CONFIG = {
    "user_profile": "developer", # 'developer', 'creator', 'student', 'general'
    "automation_threshold_roi": 90,
    "privacy": {
        "ignore_apps": ["1Password", "Bitwarden", "Bank"],
        "blur_faces": False
    },
    "custom_tracking_goals": [
        "Find highly repetitive file management tasks",
        "Monitor for unoptimized terminal workflows"
    ],
    "theme": "cyberpunk"
}

def load_config():
    if not os.path.exists(CONFIG_PATH):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG
    try:
        with open(CONFIG_PATH, 'r') as f:
            conf = json.load(f)
            # Merge defaults for missing keys
            for k, v in DEFAULT_CONFIG.items():
                if k not in conf:
                    conf[k] = v
            return conf
    except Exception:
        return DEFAULT_CONFIG

def save_config(config):
    Path(CONFIG_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=4)
