#!/usr/bin/env python3
"""
Cross-Platform UI/UX Harvester Daemon
Continuously extracts screen topography (Pixels + XML) from connected Android Edge devices.
Evaluates them to generate human-level UI/UX DPO training pairs for the Screen Lens Sovereign.
"""

import os
import time
import subprocess
import json
import logging
from pathlib import Path
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(asctime)s [UI Harvester] %(levelname)s: %(message)s")
log = logging.getLogger("UI_Harvester")

CORPUS_DIR = Path("/Volumes/Lauburu-Monorepo/04_data_and_memory/data/ui_vision_corpus")
CORPUS_DIR.mkdir(parents=True, exist_ok=True)
DPO_SINK = CORPUS_DIR / "cross_platform_ui_dpo.jsonl"

def get_active_adb_devices():
    res = subprocess.run(["adb", "devices"], capture_output=True, text=True)
    devices = []
    for line in res.stdout.strip().split("\n")[1:]:
        parts = line.split()
        if len(parts) == 2 and parts[1] == "device":
            devices.append(parts[0])
    return devices

def harvest_device_ui(device_id: str):
    timestamp = int(time.time())
    img_path = CORPUS_DIR / f"{device_id}_{timestamp}.png"
    xml_path = CORPUS_DIR / f"{device_id}_{timestamp}.xml"
    
    try:
        # Capture Screenshot
        with open(img_path, "wb") as f:
            subprocess.run(["adb", "-s", device_id, "exec-out", "screencap", "-p"], stdout=f, timeout=10)
            
        # Capture UI Automator dump
        dump_cmd = ["adb", "-s", device_id, "shell", "uiautomator", "dump", "/sdcard/window_dump.xml"]
        subprocess.run(dump_cmd, capture_output=True, timeout=10)
        
        # Pull XML
        pull_cmd = ["adb", "-s", device_id, "pull", "/sdcard/window_dump.xml", str(xml_path)]
        subprocess.run(pull_cmd, capture_output=True, timeout=10)
        
        # Verify sizes
        if img_path.exists() and img_path.stat().st_size > 1000 and xml_path.exists() and xml_path.stat().st_size > 100:
            log.info(f"✅ Successfully harvested UI state from {device_id}")
            return img_path, xml_path
        else:
            log.warning(f"Harvest failed or empty for {device_id}")
            return None, None
    except Exception as e:
        log.error(f"Error harvesting {device_id}: {e}")
        return None, None

def synthesize_dpo_placeholder(img_path, xml_path, device_id):
    """
    In a full run, this invokes Gemini/Claude via MCP to analyze the screenshot.
    Here we build the rigorous DPO structure ready for the local Qwen model.
    """
    ts = datetime.now(timezone.utc).isoformat()
    entry = {
        "timestamp": ts,
        "device_id": device_id,
        "image_artifact": str(img_path),
        "xml_artifact": str(xml_path),
        "instruction": "Analyze this cross-platform UI state. Identify adherence to WCAG AAA contrast, 8pt modular grid alignment, and touch-target ergonomics. Provide a formal critique and specify visual refactoring steps.",
        "status": "pending_multimodal_evaluation"
    }
    with open(DPO_SINK, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
        
def run_harvester_loop():
    log.info("Starting Continuous UI/UX Harvester Daemon...")
    while True:
        devices = get_active_adb_devices()
        if not devices:
            log.warning("No active ADB devices found. Retrying in 60s...")
            time.sleep(60)
            continue
            
        for dev in devices:
            log.info(f"Harvesting {dev}...")
            img, xml = harvest_device_ui(dev)
            if img and xml:
                synthesize_dpo_placeholder(img, xml, dev)
                
        # Sleep for 15 minutes between systemic harvests to avoid saturating storage/battery
        time.sleep(900)

if __name__ == "__main__":
    run_harvester_loop()
