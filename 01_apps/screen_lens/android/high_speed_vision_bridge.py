#!/usr/bin/env python3
"""
Android High-Speed Vision Bridge (Zero-Screencap)
Replaces the slow (~1 FPS) `adb screencap` pipeline with a native, high-speed
socket connection to an F-Droid MJPEG Screen Streamer app or scrcpy server.

Usage:
  This script binds to the MJPEG HTTP stream exposed by the F-Droid app on the Android device
  (e.g., http://192.168.8.x:8080/mjpeg) and feeds raw frames directly into the Screen Lens VLA
  at 30-60 FPS.
"""

import cv2
import requests
import numpy as np
import threading
import time
import argparse
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("AndroidVisionBridge")

class MJPEGVisionBridge:
    def __init__(self, stream_url: str):
        self.stream_url = stream_url
        self.latest_frame = None
        self.running = False
        self.lock = threading.Lock()

    def _stream_worker(self):
        log.info(f"Connecting to Android MJPEG stream at {self.stream_url}...")
        try:
            # Connect to the F-Droid MJPEG Server stream
            with requests.get(self.stream_url, stream=True, timeout=5.0) as r:
                r.raise_for_status()
                bytes_buffer = bytes()
                log.info("Connected to MJPEG stream. Receiving frames...")
                for chunk in r.iter_content(chunk_size=4096):
                    if not self.running:
                        break
                    bytes_buffer += chunk
                    # MJPEG boundaries: 0xff 0xd8 (start) to 0xff 0xd9 (end)
                    a = bytes_buffer.find(b'\xff\xd8')
                    b = bytes_buffer.find(b'\xff\xd9')
                    if a != -1 and b != -1:
                        jpg = bytes_buffer[a:b+2]
                        bytes_buffer = bytes_buffer[b+2:]
                        
                        # Decode directly to numpy array for VLA processing
                        frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                        with self.lock:
                            self.latest_frame = frame
        except Exception as e:
            log.error(f"Stream connection failed: {e}")
            self.running = False

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._stream_worker, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if hasattr(self, 'thread'):
            self.thread.join(timeout=2.0)

    def get_latest_frame(self):
        with self.lock:
            return self.latest_frame.copy() if self.latest_frame is not None else None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Android High-Speed Vision Bridge")
    parser.add_argument("--url", type=str, default="http://100.84.40.95:8080/screen.mjpeg", help="F-Droid MJPEG Server URL")
    args = parser.parse_args()

    bridge = MJPEGVisionBridge(args.url)
    bridge.start()

    try:
        log.info("Starting VLA ingestion loop. Press Ctrl+C to exit.")
        while bridge.running:
            frame = bridge.get_latest_frame()
            if frame is not None:
                # In a real pipeline, this frame is passed to the VLA processor (e.g., Qwen-VL or Gemini)
                # For testing, we just print the resolution.
                h, w, c = frame.shape
                sys.stdout.write(f"\rIngested frame: {w}x{h} ({c} channels) at {time.time():.2f}")
                sys.stdout.flush()
            time.sleep(0.033) # Simulate ~30 FPS polling
    except KeyboardInterrupt:
        log.info("\nShutting down vision bridge.")
    finally:
        bridge.stop()
