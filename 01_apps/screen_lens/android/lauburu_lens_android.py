#!/usr/bin/env python3
"""
Lauburu Screen Lens - Android Sovereign Activity-Driven Capture & OCR Daemon
Target: Pixel 10 Pro XL (Tensor G5 / Android 15 / Termux)
Port: 3035 | SQLite: ~/.lauburu/screen_lens.sqlite
Rule #0 Compliant: Zero-Mock, Live Hardware Capture, Ephemeral Frame Purge, Adaptive Polling
"""

import argparse
import datetime
import hashlib
import http.server
import json
import os
import re
import socketserver
import sqlite3
import subprocess
import sys
import threading
import time
import urllib.parse
from typing import Dict, Any, Tuple, Optional

PORT = 3035
DB_DIR = os.path.expanduser("~/.lauburu")
DB_PATH = os.path.join(DB_DIR, "screen_lens.sqlite")
FRAMES_DIR = os.path.join(DB_DIR, "frames")
PID_FILE = os.path.join(DB_DIR, "lauburu_lens.pid")

os.makedirs(DB_DIR, exist_ok=True)
os.makedirs(FRAMES_DIR, exist_ok=True)

class ScreenLensState:
    last_hash: Optional[str] = None
    last_app: str = "SystemUI"
    active_streak: int = 0
    idle_streak: int = 0
    total_frames_processed: int = 0
    total_bytes_saved: int = 0



def search_frames(query: str, limit: int = 5):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM screen_lens_fts WHERE screen_lens_fts MATCH ? ORDER BY rank LIMIT ?", (query, limit))
        res = cur.fetchall()
    except sqlite3.OperationalError:
        try:
            cur.execute("SELECT * FROM frames_fts WHERE frames_fts MATCH ? ORDER BY rank LIMIT ?", (query, limit))
            res = cur.fetchall()
        except Exception:
            res = []
    conn.close()
    return res

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS frames (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            epoch_ms INTEGER NOT NULL,
            app_package TEXT NOT NULL,
            app_name TEXT NOT NULL,
            ocr_text TEXT NOT NULL,
            frame_path TEXT DEFAULT 'EPHEMERAL_DELETED',
            width INTEGER DEFAULT 1344,
            height INTEGER DEFAULT 2992,
            ocr_latency_ms REAL DEFAULT 0.0,
            change_hash TEXT DEFAULT ''
        )
    """)
    cursor.execute("PRAGMA table_info(frames)")
    cols = [r[1] for r in cursor.fetchall()]
    if "change_hash" not in cols:
        cursor.execute("ALTER TABLE frames ADD COLUMN change_hash TEXT DEFAULT ''")
    cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS frames_fts USING fts5(
            app_name,
            ocr_text,
            content='frames',
            content_rowid='id'
        )
    """)
    cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS screen_lens_fts USING fts5(
            app_name,
            ocr_text,
            content='frames',
            content_rowid='id'
        )
    """)
    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS frames_ai AFTER INSERT ON frames BEGIN
            INSERT INTO frames_fts(rowid, app_name, ocr_text)
            VALUES (new.id, new.app_name, new.ocr_text);
            INSERT INTO screen_lens_fts(rowid, app_name, ocr_text)
            VALUES (new.id, new.app_name, new.ocr_text);
        END;
    """)
    conn.commit()
    conn.close()


def is_shizuku_local() -> bool:
    """Check if Shizuku rish is present directly on this Android device (e.g. inside Termux)."""
    return os.path.exists("/data/local/tmp/rish") and os.access("/data/local/tmp/rish", os.X_OK)


def find_adb_device() -> Optional[str]:
    """Finds active local or USB ADB device."""
    try:
        res = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=2.0)
        lines = [l.split()[0] for l in res.stdout.splitlines() if "\tdevice" in l]
        if lines:
            return lines[0]
    except Exception:
        pass
    return None


def get_active_app() -> Tuple[str, str]:
    if is_shizuku_local():
        cmd = ["/data/local/tmp/rish", "-c", "dumpsys window displays"]
    else:
        target = find_adb_device()
        cmd = ["adb"]
        if target:
            cmd.extend(["-s", target])
        cmd.extend(["shell", "/data/local/tmp/rish -c 'dumpsys window displays' 2>/dev/null || dumpsys window displays"])

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=2.0)
        for line in res.stdout.splitlines():
            if "mCurrentFocus=" in line or "mFocusedApp=" in line:
                m = re.search(r"([a-zA-Z0-9_.]+)/([a-zA-Z0-9_.]+)", line)
                if m:
                    pkg = m.group(1)
                    cls = m.group(2)
                    app_name = pkg.split(".")[-1].capitalize()
                    return pkg, app_name
    except Exception:
        pass
    return "com.android.systemui", "SystemUI"


def capture_and_ocr(force: bool = False) -> Dict[str, Any]:
    """
    Activity-Driven Capture:
    1. Grabs live screen buffer into a temporary file.
    2. Computes SHA-256 hash of visual buffer.
    3. If unchanged and not forced, immediately deletes file and skips OCR (0 compute waste).
    4. If changed, executes Tesseract OCR, writes text to SQLite, and IMMEDIATELY deletes raw frame (0 disk waste).
    """
    t0 = time.time()
    now = datetime.datetime.now(datetime.timezone.utc)
    timestamp_str = now.isoformat()
    epoch_ms = int(now.timestamp() * 1000)
    temp_frame = os.path.join(FRAMES_DIR, f"temp_{epoch_ms}.png")

    if is_shizuku_local():
        screencap_cmd = ["/data/local/tmp/rish", "-c", "screencap -p"]
    else:
        target = find_adb_device()
        screencap_cmd = ["adb"]
        if target:
            screencap_cmd.extend(["-s", target])
        screencap_cmd.extend(["exec-out", "screencap", "-p"])

    try:
        with open(temp_frame, "wb") as f:
            subprocess.run(screencap_cmd, stdout=f, timeout=3.0, check=True)
    except Exception as e:
        if os.path.exists(temp_frame):
            try:
                os.remove(temp_frame)
            except Exception:
                pass
        return {"error": f"Screencap failed: {str(e)}"}

    if not os.path.exists(temp_frame) or os.path.getsize(temp_frame) == 0:
        if os.path.exists(temp_frame):
            os.remove(temp_frame)
        return {"error": "Captured frame is empty"}

    frame_size_bytes = os.path.getsize(temp_frame)

    # 2. Compute Fast Visual Hash
    hasher = hashlib.sha256()
    with open(temp_frame, "rb") as f:
        # Sample first 64KB and middle 64KB for sub-millisecond hashing
        hasher.update(f.read(65536))
        f.seek(max(0, frame_size_bytes // 2))
        hasher.update(f.read(65536))
    current_hash = hasher.hexdigest()

    pkg, app_name = get_active_app()
    is_same = (ScreenLensState.last_hash == current_hash and ScreenLensState.last_app == app_name and not force)

    if is_same:
        # Screen is completely static. Immediately delete frame and skip heavy OCR.
        try:
            os.remove(temp_frame)
        except Exception:
            pass
        ScreenLensState.idle_streak += 1
        ScreenLensState.active_streak = 0
        return {
            "status": "SKIPPED_STATIC_NO_CHANGE",
            "app_package": pkg,
            "app_name": app_name,
            "hash": current_hash,
            "duration_ms": round((time.time() - t0) * 1000, 2)
        }

    # 3. Active Change Detected: Run Tesseract OCR
    ScreenLensState.active_streak += 1
    ScreenLensState.idle_streak = 0
    ScreenLensState.last_hash = current_hash
    ScreenLensState.last_app = app_name

    ocr_out_base = os.path.join(FRAMES_DIR, f"temp_ocr_{epoch_ms}")
    ocr_text = ""
    try:
        subprocess.run(
            ["tesseract", temp_frame, ocr_out_base, "--oem", "1", "-l", "eng"],
            capture_output=True,
            timeout=5.0
        )
        txt_path = ocr_out_base + ".txt"
        if os.path.exists(txt_path):
            with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
                ocr_text = f.read().strip()
            os.remove(txt_path)
    except Exception as e:
        ocr_text = f"[OCR Error: {str(e)}]"

    # 4. CRITICAL EPHEMERAL PURGE: Immediately delete raw PNG from disk
    try:
        os.remove(temp_frame)
        ScreenLensState.total_bytes_saved += frame_size_bytes
    except Exception:
        pass

    t_end = time.time()
    ocr_latency_ms = round((t_end - t0) * 1000, 2)

    # 5. Insert Extracted Text into SQLite
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO frames (timestamp, epoch_ms, app_package, app_name, ocr_text, frame_path, ocr_latency_ms, change_hash)
        VALUES (?, ?, ?, ?, ?, 'EPHEMERAL_DELETED', ?, ?)
    """, (timestamp_str, epoch_ms, pkg, app_name, ocr_text, ocr_latency_ms, current_hash))
    frame_id = cursor.lastrowid
    conn.commit()
    conn.close()

    ScreenLensState.total_frames_processed += 1

    return {
        "id": frame_id,
        "timestamp": timestamp_str,
        "epoch_ms": epoch_ms,
        "app_package": pkg,
        "app_name": app_name,
        "ocr_text": ocr_text,
        "frame_retained": False,
        "ocr_latency_ms": ocr_latency_ms,
        "hash": current_hash
    }


def get_status() -> Dict[str, Any]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*), COALESCE(MAX(id), 0) FROM frames")
    total_frames, latest_id = cursor.fetchone()
    conn.close()

    pkg, app_name = get_active_app()
    db_size = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0
    frames_count = len([f for f in os.listdir(FRAMES_DIR) if os.path.isfile(os.path.join(FRAMES_DIR, f))])

    return {
        "status": "healthy",
        "node_layer": "L6",
        "node_name": "Pixel_10_Pro_XL",
        "service": "lauburu-lens-android-activity-driven",
        "port": PORT,
        "total_frames_indexed": total_frames,
        "latest_frame_id": latest_id,
        "active_app_package": pkg,
        "active_app_name": app_name,
        "ephemeral_mode": "ZERO_DISK_RETENTION",
        "disk_frames_stored": frames_count,
        "db_size_mb": round(db_size / (1024 * 1024), 2),
        "total_bytes_purged_mb": round(ScreenLensState.total_bytes_saved / (1024 * 1024), 2),
        "active_streak": ScreenLensState.active_streak,
        "idle_streak": ScreenLensState.idle_streak,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }


class LensHttpHandler(http.server.BaseHTTPRequestHandler):
    def _send_json(self, data, status=200):
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path in ["/", "/v1/status", "/status"]:
            self._send_json(get_status())
        elif path == "/v1/capture":
            res = capture_and_ocr(force=True)
            self._send_json(res)
        elif path == "/v1/frames/latest":
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT id, timestamp, app_package, app_name, ocr_text, ocr_latency_ms FROM frames ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            conn.close()
            if row:
                self._send_json({
                    "id": row[0],
                    "timestamp": row[1],
                    "app_package": row[2],
                    "app_name": row[3],
                    "ocr_text": row[4],
                    "ocr_latency_ms": row[5]
                })
            else:
                self._send_json({"message": "No frames captured yet"}, 404)
        else:
            self._send_json({"error": f"Endpoint not found: {path}"}, 404)

    def do_POST(self):
        if self.path in ["/v1/capture", "/capture"]:
            res = capture_and_ocr(force=True)
            self._send_json(res)
        else:
            self._send_json({"error": f"Endpoint not found: {self.path}"}, 404)

    def log_message(self, format, *args):
        pass


def run_daemon():
    """
    Adaptive Continuous Loop:
    - Active changes: 0.5s–1.0s interval for rapid capture during typing/scrolling.
    - Static screens: Backs off exponentially to 3.0s to save CPU and battery.
    """
    init_db()
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    # Acquire Termux Wake Lock
    subprocess.run(["termux-wake-lock"], capture_output=True)

    server = socketserver.ThreadingTCPServer(("0.0.0.0", PORT), LensHttpHandler)
    server.allow_reuse_address = True
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    print(f"🚀 Lauburu Screen Lens (Activity-Driven) running on http://0.0.0.0:{PORT}")
    print("⚡ Ephemeral mode: ACTIVE (Raw frames immediately purged after OCR)")

    try:
        while True:
            res = capture_and_ocr(force=False)
            
            # Dynamic Adaptive Sleep
            if res.get("status") == "SKIPPED_STATIC_NO_CHANGE":
                sleep_time = min(3.0, 1.0 + (ScreenLensState.idle_streak * 0.5))
            else:
                sleep_time = 0.5  # Rapid responsive capture while active
                
            time.sleep(sleep_time)
    except KeyboardInterrupt:
        print("\nStopping Screen Lens...")
    finally:
        server.shutdown()
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)


def main():
    parser = argparse.ArgumentParser(description="Lauburu Screen Lens Activity-Driven Daemon")
    parser.add_argument("command", choices=["start", "stop", "status", "capture"], nargs="?", default="status")
    args = parser.parse_args()

    init_db()

    if args.command == "start":
        run_daemon()
    elif args.command == "stop":
        if os.path.exists(PID_FILE):
            with open(PID_FILE, "r") as f:
                pid = int(f.read().strip())
            try:
                os.kill(pid, 15)
                print(f"Stopped Screen Lens daemon (PID {pid})")
            except ProcessLookupError:
                print("Daemon not running")
            if os.path.exists(PID_FILE):
                os.remove(PID_FILE)
    elif args.command == "status":
        print(json.dumps(get_status(), indent=2))
    elif args.command == "capture":
        res = capture_and_ocr(force=True)
        print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
