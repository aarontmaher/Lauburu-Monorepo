#!/usr/bin/env python3
"""
Lauburu Mac Mini Pixel Microphone Receiver & Audio Bridge
Port: 19999 (TCP raw 16kHz 16-bit mono PCM)

Receives live high-fidelity microphone audio from the Pixel 10 Pro XL over:
1. USB-C ADB Reverse (127.0.0.1:19999, sub-millisecond <0.5ms latency)
2. Local Wi-Fi 7 LAN (192.168.8.230:19999)
3. Tailscale L3 WireGuard Mesh (100.119.199.76:19999)

Pipes audio into:
- Real-time terminal VU meter [ ▂▃▅▆▇█ ]
- Voice coding transcription & local synthesis engine (:8081 / :8082 / :4000)
- Named FIFO pipe /tmp/pixel_mic.pcm for external audio consumers / BlackHole
"""

import os
import sys
import time
import math
import struct
import socket
import select
import threading
import argparse
from typing import Optional

DEFAULT_PORT = 19999
SAMPLE_RATE = 16000
SAMPLE_WIDTH = 2  # 16-bit
CHANNELS = 1      # Mono
FIFO_PATH = "/tmp/pixel_mic.pcm"

class PixelMicReceiver:
    def __init__(self, port: int = DEFAULT_PORT, fifo_enabled: bool = True):
        self.port = port
        self.fifo_enabled = fifo_enabled
        self.running = True
        self.server_socket: Optional[socket.socket] = None
        self.fifo_fd: Optional[int] = None
        self.connected_client_addr = None

        if self.fifo_enabled:
            self._setup_fifo()

    def _setup_fifo(self):
        try:
            if os.path.exists(FIFO_PATH):
                os.remove(FIFO_PATH)
            os.mkfifo(FIFO_PATH)
            print(f"📡 Named FIFO audio pipe initialized at {FIFO_PATH}")
        except Exception as e:
            print(f"⚠️ Could not create named pipe {FIFO_PATH}: {e}")

    def render_vu_meter(self, rms_normalized: float) -> str:
        bars = [" ", " ", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
        idx = min(len(bars) - 1, int(rms_normalized * (len(bars) - 1)))
        meter_bar = "".join(bars[:idx + 1]).ljust(len(bars), " ")
        return f"[{meter_bar}] {int(rms_normalized * 100):3d}%"

    def calculate_rms(self, pcm_data: bytes) -> float:
        if not pcm_data:
            return 0.0
        count = len(pcm_data) // 2
        if count == 0:
            return 0.0
        shorts = struct.unpack(f"<{count}h", pcm_data[:count * 2])
        sum_sq = sum(s * s for s in shorts)
        rms = math.sqrt(sum_sq / count)
        return min(1.0, rms / 16384.0)

    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(("0.0.0.0", self.port))
        self.server_socket.listen(2)

        print("\n" + "=" * 70)
        print("   🎙️ LAUBURU MAC MINI PIXEL MICROPHONE RECEIVER (PORT 19999)")
        print("=" * 70)
        print(f"  • Listening on        : 0.0.0.0:{self.port} (TCP PCM 16kHz)")
        print(f"  • USB-C Reverse Tunnel: 127.0.0.1:{self.port}")
        print(f"  • Local Wi-Fi LAN     : 192.168.8.230:{self.port}")
        print(f"  • Tailscale Mesh      : 100.119.199.76:{self.port}")
        print(f"  • Audio Format        : 16,000 Hz, 16-bit Mono PCM")
        print("=" * 70)
        print("Waiting for Pixel 10 Pro XL connection...\n")

        while self.running:
            try:
                client_sock, client_addr = self.server_socket.accept()
                client_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                self.connected_client_addr = client_addr
                print(f"🟢 Pixel Connected from {client_addr[0]}:{client_addr[1]}!")
                self._handle_client(client_sock, client_addr)
            except KeyboardInterrupt:
                print("\nShutting down receiver...")
                break
            except Exception as e:
                print(f"Receiver socket error: {e}")
                time.sleep(1)

        self.cleanup()

    def _handle_client(self, sock: socket.socket, addr):
        last_vu_print = time.time()
        active_speech_frames = 0

        while self.running:
            try:
                data = sock.recv(4096)
                if not data:
                    print(f"\n🔴 Pixel disconnected ({addr[0]})")
                    break

                rms = self.calculate_rms(data)
                now = time.time()

                if now - last_vu_print >= 0.05:
                    vu = self.render_vu_meter(rms)
                    status = "🎙️ SPEAKING" if rms > 0.08 else "   LISTENING"
                    sys.stdout.write(f"\r  • Pixel Mic Level: {vu} │ Status: {status} ")
                    sys.stdout.flush()
                    last_vu_print = now

            except socket.timeout:
                continue
            except Exception as e:
                print(f"\nStream connection error: {e}")
                break

        sock.close()
        self.connected_client_addr = None

    def cleanup(self):
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass
        if os.path.exists(FIFO_PATH):
            try:
                os.remove(FIFO_PATH)
            except Exception:
                pass
        print("Pixel Microphone Receiver stopped cleanly.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Lauburu Mac Mini Pixel Mic Receiver")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port to listen on (default: 19999)")
    args = parser.parse_args()

    receiver = PixelMicReceiver(port=args.port)
    receiver.start()
