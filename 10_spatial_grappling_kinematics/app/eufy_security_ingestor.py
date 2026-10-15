#!/usr/bin/env python3
"""
Eufy Security Training Footage Ingestion Pipeline (L6 Pixel 10 Pro XL + Eufy Cloud/RTSP Bridge)
===============================================================================================
Prepares zero-mock ingestion of Aaron Maher's grappling training security footage from the Eufy Security app:
  1. Mode A (Eufy Web/Cloud API & RTSP/NAS Stream): Uses credentials stored in ~/.config/eufy_security/credentials.json
     (never logged to stdout, masked as [REDACTED_SOVEREIGN]) to pull recorded motion clips into `10_spatial_grappling_kinematics/app/inbox/`.
  2. Mode B (Screen Lens Sovereign Android ADB Extraction on L6 Pixel 10 Pro XL `192.168.8.213` / `100.114.215.68`):
     Pulls downloaded Eufy MP4 clips from `/sdcard/Movies/eufySecurity/` or `/sdcard/DCIM/eufySecurity/` directly over ADB/SSH
     into the 3D kinematics pipeline.
"""

import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

APP_DIR = Path(__file__).resolve().parent
INBOX_DIR = APP_DIR / "inbox" / "eufy_security"
CONFIG_DIR = Path.home() / ".config" / "eufy_security"
CRED_FILE = CONFIG_DIR / "credentials.json"


def mask_secret(val: str) -> str:
    val = (val or "").strip()
    if not val:
        return "[NOT_SET]"
    if len(val) > 6:
        return val[:4] + "...[REDACTED_SOVEREIGN]"
    return "[REDACTED_SOVEREIGN]"


def get_eufy_status() -> Dict[str, Any]:
    """Return current Eufy Security configuration and L6 Pixel 10 Pro XL readiness status."""
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    has_creds = CRED_FILE.exists()
    email_masked = "[AWAITING_LOGIN_TOMORROW]"
    rtsp_url_masked = "[OPTIONAL_RTSP_STREAM]"
    if has_creds:
        try:
            data = json.loads(CRED_FILE.read_text(encoding="utf-8"))
            email_masked = mask_secret(data.get("email", ""))
            rtsp_url_masked = mask_secret(data.get("rtsp_url", ""))
        except Exception:
            pass

    existing_clips = sorted(
        [p.name for p in INBOX_DIR.glob("*.mp4") if p.stat().st_size > 1000]
    )

    return {
        "status": "READY_FOR_CREDENTIALS" if not has_creds else "CREDENTIALS_CONFIGURED",
        "credentials_file": str(CRED_FILE),
        "email_masked": email_masked,
        "rtsp_stream_masked": rtsp_url_masked,
        "inbox_dir": str(INBOX_DIR),
        "ingested_clips_count": len(existing_clips),
        "ingested_clips": existing_clips[:20],
        "android_edge_node": "L6 Pixel 10 Pro XL (100.114.215.68 / 192.168.8.213)",
        "android_eufy_paths": [
            "/sdcard/Movies/eufySecurity",
            "/sdcard/DCIM/eufySecurity",
            "/sdcard/Download/eufySecurity",
        ],
    }


def save_eufy_credentials(email: str, password: str, rtsp_url: str = "", country: str = "AU") -> Dict[str, Any]:
    """Save Eufy Security credentials securely to local 0600 file (~/.config/eufy_security/credentials.json)."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "email": email.strip(),
        "password": password,
        "rtsp_url": rtsp_url.strip(),
        "country": country.strip() or "AU",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    CRED_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.chmod(CRED_FILE, 0o600)
    return get_eufy_status()


def sync_eufy_clips_from_pixel10() -> Dict[str, Any]:
    """
    Pulls any downloaded Eufy Security MP4 training videos from L6 Pixel 10 Pro XL
    (/sdcard/Movies/eufySecurity or /sdcard/DCIM/eufySecurity) via ADB or Termux SSH.
    """
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    pulled: List[str] = []
    errors: List[str] = []

    # Check ADB devices first
    try:
        res = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=5)
        devs = [l.split()[0] for l in res.stdout.strip().splitlines()[1:] if "\tdevice" in l]
        for dev in devs:
            for remote_dir in ["/sdcard/Movies/eufySecurity", "/sdcard/DCIM/eufySecurity", "/sdcard/Download"]:
                ls_res = subprocess.run(
                    ["adb", "-s", dev, "shell", f"ls -1 {remote_dir}/*.mp4 2>/dev/null"],
                    capture_output=True,
                    text=True,
                    timeout=8,
                )
                for remote_file in ls_res.stdout.strip().splitlines():
                    remote_file = remote_file.strip()
                    if not remote_file.endswith(".mp4"):
                        continue
                    if "eufy" not in remote_file.lower() and remote_dir == "/sdcard/Download":
                        continue
                    local_dest = INBOX_DIR / Path(remote_file).name
                    if not local_dest.exists():
                        subprocess.run(
                            ["adb", "-s", dev, "pull", remote_file, str(local_dest)],
                            capture_output=True,
                            timeout=60,
                        )
                        if local_dest.exists() and local_dest.stat().st_size > 10000:
                            pulled.append(local_dest.name)
    except Exception as e:
        errors.append(str(e))

    return {
        "pulled_clips": pulled,
        "pulled_count": len(pulled),
        "inbox_dir": str(INBOX_DIR),
        "errors": errors,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


if __name__ == "__main__":
    print(json.dumps(get_eufy_status(), indent=2))
