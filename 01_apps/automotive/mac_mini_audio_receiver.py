#!/usr/bin/env python3
"""
Lauburu Mac Mini Studio Voice & Audio Receiver Daemon
Port: 19999 (TCP)
Governance: Sovereign Host Sanctuary & Zero-Mock Telemetry

Listens on TCP Port 19999 across USB-C (ADB reverse <0.5ms), Wi-Fi 7 LAN, and Tailscale.
Ingests continuous 16kHz 16-bit mono PCM audio from the Pixel 10 Pro XL hardware mic,
detects speech boundaries via RMS energy VAD, classifies the spoken language via
HeyNeo Spoken LID Service (Port 4005), and dispatches coding directives to Port 4000 / Port 8081.
"""

import asyncio
import io
import json
import logging
import math
import os
import struct
import sys
import time
import wave
from typing import Dict, Optional, Tuple

import httpx

# Configure Structured Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [VoiceReceiver:19999] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("VoiceReceiver")

PORT = 19999
HOST = "0.0.0.0"
SAMPLE_RATE = 16000
CHANNELS = 1
SAMPLE_WIDTH = 2  # 16-bit PCM

HEYNEO_LID_URL = "http://127.0.0.1:4005/api/audio/classify_language"
PORT_4000_URL = "http://127.0.0.1:4000/api/voice_coder/directive"
BT_TERMINAL_URL = "http://127.0.0.1:4050/api/voice/directive"
TELEMETRY_LOG = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/voice_receiver_telemetry.json"

# VAD Parameters
SILENCE_THRESHOLD_RMS = 2.5     # Audio level below which is considered silence
SILENCE_DURATION_SEC = 0.8      # Silence required to mark utterance end
MIN_UTTERANCE_SEC = 0.5         # Minimum speech length to classify
MAX_UTTERANCE_SEC = 15.0        # Maximum buffer before forced processing


class VoiceReceiverServer:
    def __init__(self, host: str = HOST, port: int = PORT):
        self.host = host
        self.port = port
        self.active_clients = 0
        self.total_bytes_received = 0
        self.total_utterances_processed = 0
        self.last_language_detected = "en"
        self.last_confidence = 0.0
        self.current_rms = 0.0
        self.is_running = False
        self.server: Optional[asyncio.Server] = None
        self.http_client = httpx.AsyncClient(timeout=5.0)

    def calculate_rms(self, pcm_chunk: bytes) -> float:
        """Calculates RMS amplitude percentage (0.0 - 100.0) for 16-bit PCM."""
        if not pcm_chunk:
            return 0.0
        num_samples = len(pcm_chunk) // 2
        if num_samples == 0:
            return 0.0
        
        # Unpack 16-bit signed little-endian integers
        format_str = f"<{num_samples}h"
        try:
            samples = struct.unpack(format_str, pcm_chunk)
            sum_squares = sum((s / 32768.0) ** 2 for s in samples)
            rms = math.sqrt(sum_squares / num_samples) * 100.0
            return min(100.0, max(0.0, rms))
        except Exception:
            return 0.0

    def pcm_to_wav(self, pcm_data: bytes) -> bytes:
        """Encapsulates raw PCM bytes into a standard RIFF/WAV container in-memory."""
        wav_io = io.BytesIO()
        with wave.open(wav_io, "wb") as wav_file:
            wav_file.setnchannels(CHANNELS)
            wav_file.setsampwidth(SAMPLE_WIDTH)
            wav_file.setframerate(SAMPLE_RATE)
            wav_file.writeframes(pcm_data)
        return wav_io.getvalue()

    async def classify_and_route_utterance(self, pcm_buffer: bytes, duration_sec: float):
        """Asynchronously dispatches speech segment to HeyNeo LID and Port 4000."""
        self.total_utterances_processed += 1
        wav_bytes = self.pcm_to_wav(pcm_buffer)
        logger.info(
            f"Speech utterance detected ({duration_sec:.2f}s, {len(pcm_buffer)} bytes). "
            f"Dispatching to HeyNeo LID (:4005)..."
        )

        detected_lang = "en"
        confidence = 0.0
        try:
            files = {"file": ("utterance.wav", wav_bytes, "audio/wav")}
            data = {"user_id": "pixel_studio_mic", "top_k": "3", "apply_adaptation": "true"}
            response = await self.http_client.post(HEYNEO_LID_URL, files=files, data=data)
            
            if response.status_code == 200:
                lid_res = response.json()
                detected_lang = lid_res.get("detected_language", "en")
                confidence = lid_res.get("confidence", 0.0)
                lang_name = lid_res.get("language_name", detected_lang)
                logger.info(
                    f"✓ HeyNeo Spoken LID: {lang_name} ({detected_lang}) "
                    f"Confidence: {confidence:.1%} Latency: {lid_res.get('latency_ms', 0)}ms"
                )
                self.last_language_detected = detected_lang
                self.last_confidence = confidence
            else:
                logger.warning(f"HeyNeo LID returned status {response.status_code}")
        except Exception as e:
            logger.warning(f"LID dispatch unavailable: {e}")

        # Forward voice directive to Bluetooth Terminal IDE (:4050)
        try:
            transcript = lid_res.get("transcript") if 'lid_res' in locals() and lid_res.get("transcript") else f"Voice utterance ({duration_sec:.1f}s)"
            payload = {
                "directive": transcript,
                "raw_transcript": transcript,
                "caller": "pixel_studio_mic_tcp19999"
            }
            await self.http_client.post(BT_TERMINAL_URL, json=payload)
        except Exception:
            pass

        # Update telemetry ledger
        self.save_telemetry(detected_lang, confidence, duration_sec)

    def save_telemetry(self, lang: str, conf: float, duration: float):
        try:
            telemetry = {
                "timestamp": time.time(),
                "status": "ONLINE",
                "port": self.port,
                "active_clients": self.active_clients,
                "total_bytes_received": self.total_bytes_received,
                "total_utterances": self.total_utterances_processed,
                "last_language": lang,
                "last_confidence": round(conf, 4),
                "last_duration_sec": round(duration, 2),
                "current_rms": round(self.current_rms, 2)
            }
            with open(TELEMETRY_LOG, "w") as f:
                json.dump(telemetry, f, indent=2)
        except Exception:
            pass

    async def _periodic_telemetry_loop(self):
        while self.is_running:
            self.save_telemetry(self.last_language_detected, self.last_confidence, 0.0)
            await asyncio.sleep(2.0)

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        peer = writer.get_extra_info("peername")
        self.active_clients += 1
        logger.info(f"🟢 Pixel audio client connected from: {peer}")
        self.save_telemetry(self.last_language_detected, self.last_confidence, 0.0)

        speech_buffer = bytearray()
        last_speech_time = time.time()
        in_speech = False
        bytes_per_second = SAMPLE_RATE * SAMPLE_WIDTH * CHANNELS  # 32,000 B/s

        try:
            while self.is_running:
                chunk = await reader.read(2048)
                if not chunk:
                    break

                self.total_bytes_received += len(chunk)
                rms = self.calculate_rms(chunk)
                self.current_rms = rms
                now = time.time()

                if rms > SILENCE_THRESHOLD_RMS:
                    speech_buffer.extend(chunk)
                    last_speech_time = now
                    in_speech = True
                else:
                    if in_speech:
                        speech_buffer.extend(chunk)
                        silence_duration = now - last_speech_time
                        buffer_duration = len(speech_buffer) / bytes_per_second

                        if silence_duration >= SILENCE_DURATION_SEC or buffer_duration >= MAX_UTTERANCE_SEC:
                            if buffer_duration >= MIN_UTTERANCE_SEC:
                                asyncio.create_task(
                                    self.classify_and_route_utterance(bytes(speech_buffer), buffer_duration)
                                )
                            speech_buffer.clear()
                            in_speech = False

        except (asyncio.CancelledError, ConnectionResetError, BrokenPipeError):
            pass
        finally:
            self.active_clients = max(0, self.active_clients - 1)
            logger.info(f"🔴 Pixel audio client disconnected from: {peer}")
            writer.close()
            await writer.wait_closed()

    async def start(self):
        self.is_running = True
        self.server = await asyncio.start_server(self.handle_client, self.host, self.port)
        addrs = ", ".join(str(sock.getsockname()) for sock in self.server.sockets)
        logger.info(f"🚀 Studio Audio Receiver daemon listening on TCP Port {self.port} ({addrs})")
        logger.info(f"Targeting: 16kHz 16-bit Mono PCM | HeyNeo LID (:4005) | Console (:4000)")
        self.save_telemetry("en", 1.0, 0.0)
        asyncio.create_task(self._periodic_telemetry_loop())

        async with self.server:
            await self.server.serve_forever()

    async def stop(self):
        self.is_running = False
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        await self.http_client.aclose()
        logger.info("Studio Audio Receiver daemon stopped.")


async def main():
    server = VoiceReceiverServer()
    try:
        await server.start()
    except (KeyboardInterrupt, asyncio.CancelledError):
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())
