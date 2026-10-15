#!/usr/bin/env python3
"""
Lauburu Swarm - Sovereign Screen Lens Context & Multimodal Client
Provides all swarm agents, orchestrators, and subagents with zero-latency
access to real-time macOS desktop and Android mobile screen OCR context.
"""

import json
import os
import sqlite3
import subprocess
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

MAC_LENS_URL = "http://127.0.0.1:3035"
PIXEL_LENS_URLS = [
    "http://127.0.0.1:3036",       # ADB Port Forward
    "http://100.73.38.87:3035",    # Direct Tailscale WireGuard
    "http://192.168.8.145:3035",   # Direct Local LAN
]
MAC_DB_PATH = os.path.expanduser("~/.lauburu/screen_lens.sqlite")


class ScreenLensSwarmClient:
    """Client for Swarm agents to perceive cross-device screen activity."""

    def __init__(self, mac_url: str = MAC_LENS_URL):
        self.mac_url = mac_url

    def get_latest_mac_frame(self) -> Dict[str, Any]:
        """Fetches the latest screen OCR capture from the Mac Mini host."""
        try:
            req = urllib.request.urlopen(f"{self.mac_url}/api/latest", timeout=2.0)
            if req.status == 200:
                data = json.loads(req.read().decode("utf-8"))
                return {
                    "id": data.get("id", 0),
                    "timestamp": data.get("timestamp", ""),
                    "active_app_name": data.get("app") or data.get("active_app_name", ""),
                    "active_window_title": data.get("window_title") or data.get("active_window_title", ""),
                    "raw_text_summary": data.get("raw_text_summary") or data.get("raw_text", ""),
                    "source": "rest_api"
                }
        except Exception:
            # Fallback to direct SQLite read
            if os.path.exists(MAC_DB_PATH):
                try:
                    conn = sqlite3.connect(MAC_DB_PATH)
                    c = conn.cursor()
                    c.execute("""
                        SELECT id, timestamp, active_app_name, active_window_title, raw_text_summary, ocr_duration_ms
                        FROM captures ORDER BY id DESC LIMIT 1
                    """)
                    row = c.fetchone()
                    conn.close()
                    if row:
                        return {
                            "id": row[0],
                            "timestamp": row[1],
                            "active_app_name": row[2],
                            "active_window_title": row[3],
                            "raw_text_summary": row[4],
                            "ocr_duration_ms": row[5],
                            "source": "sqlite_direct"
                        }
                except Exception:
                    pass
        return {"status": "unavailable", "message": "Mac Screen Lens not responding"}

    def get_latest_pixel_frame(self) -> Dict[str, Any]:
        """Fetches the latest screen OCR capture from the Pixel 10 Pro XL."""
        for endpoint in PIXEL_LENS_URLS:
            try:
                req = urllib.request.urlopen(f"{endpoint}/v1/frames/latest", timeout=2.0)
                if req.status == 200:
                    data = json.loads(req.read().decode("utf-8"))
                    data["endpoint_used"] = endpoint
                    return data
            except Exception:
                continue
        return {"status": "unavailable", "message": "Pixel Screen Lens offline / sleeping"}

    def query_history(self, query: str, app: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Searches historical screen OCR records using FTS5 full-text search."""
        params = {"q": query, "limit": str(limit)}
        if app:
            params["app"] = app
        url = f"{self.mac_url}/api/query?{urllib.parse.urlencode(params)}"
        try:
            req = urllib.request.urlopen(url, timeout=3.0)
            if req.status == 200:
                data = json.loads(req.read().decode("utf-8"))
                return data.get("results", [])
        except Exception:
            if os.path.exists(MAC_DB_PATH):
                try:
                    conn = sqlite3.connect(MAC_DB_PATH)
                    c = conn.cursor()
                    sql = """
                        SELECT c.id, c.timestamp, c.active_app_name, c.active_window_title, c.raw_text_summary
                        FROM captures_fts(?) fts
                        JOIN captures c ON fts.rowid = c.id
                        ORDER BY c.id DESC LIMIT ?
                    """
                    c.execute(sql, (query, limit))
                    rows = c.fetchall()
                    conn.close()
                    return [{
                        "id": r[0],
                        "timestamp": r[1],
                        "app": r[2],
                        "window": r[3],
                        "text": r[4]
                    } for r in rows]
                except Exception:
                    pass
        return []

    def get_active_screen_summary(self) -> str:
        """Returns a concise text summary of active on-screen context across devices."""
        mac_frame = self.get_latest_mac_frame()
        pixel_frame = self.get_latest_pixel_frame()

        summary_lines = ["### 👁️ Live Screen Lens Context (Swarm Feed)"]
        if mac_frame.get("active_app_name"):
            summary_lines.append(
                f"- **Mac Mini (L1)**: Active in `{mac_frame.get('active_app_name')}` "
                f"(\"{mac_frame.get('active_window_title', '')}\")\n"
                f"  Text Snippet: {mac_frame.get('raw_text_summary', '')[:200]}..."
            )
        else:
            summary_lines.append("- **Mac Mini (L1)**: Standby / No recent frame")

        if pixel_frame.get("app_name"):
            summary_lines.append(
                f"- **Pixel 10 Pro (L6)**: Active in `{pixel_frame.get('app_name')}` "
                f"(`{pixel_frame.get('app_package', '')}`)\n"
                f"  Text Snippet: {pixel_frame.get('ocr_text', '')[:200]}..."
            )
        else:
            summary_lines.append("- **Pixel 10 Pro (L6)**: Away / Standby")

        return "\n".join(summary_lines)


if __name__ == "__main__":
    client = ScreenLensSwarmClient()
    print(client.get_active_screen_summary())
