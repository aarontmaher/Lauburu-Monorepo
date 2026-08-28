"""
Port 4000 Live Telemetry Forwarding Client.
Pushes real-time Movesense/Polar frames to Port 4000 Canonical Hub via:
1. HTTP REST endpoint (POST /api/sensors/ingest)
2. Low-latency WebSocket stream (ws://...:4000/ws/telemetry)
Includes offline queuing, batch retroactive synchronization, and retry resilience.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple, Union
import urllib.error
import urllib.request

try:
    import websockets
except ImportError:
    websockets = None

try:
    from .pixel_persistence_engine import PixelPersistenceEngine
except (ImportError, ValueError):
    from pixel_persistence_engine import PixelPersistenceEngine

logger = logging.getLogger("port4000_forwarder")


class Port4000Forwarder:
    """
    Live forwarding client that streams telemetry frames from Pixel to Port 4000 Hub.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 4000,
        session_token: Optional[str] = None,
        persistence_engine: Optional[PixelPersistenceEngine] = None,
        timeout_sec: float = 3.0
    ):
        self.host = host
        self.port = port
        self.session_token = session_token
        self.persistence_engine = persistence_engine
        self.timeout_sec = timeout_sec

        self.http_base_url = f"http://{host}:{port}"
        self.ws_url = f"ws://{host}:{port}/ws/telemetry"

    def set_session_token(self, session_token: str) -> None:
        """Sets or updates the session token for authenticated ingestion."""
        self.session_token = session_token

    def _prepare_http_payload(self, frame: Dict[str, Any]) -> Dict[str, Any]:
        """Maps internal frame dictionary to Port 4000 Ingest Request schema."""
        sensor_type = frame.get("sensor_type", "movesense")
        if "polar" in sensor_type.lower():
            sensor_type = "polar"
        elif "movesense" in sensor_type.lower():
            sensor_type = "movesense"

        return {
            "session_token": self.session_token or frame.get("session_token"),
            "sensor_type": sensor_type,
            "heart_rate": frame.get("heart_rate") or frame.get("hr_bpm"),
            "rr_intervals_ms": frame.get("rr_intervals_ms") or frame.get("rr_ms") or [],
            "rmssd": frame.get("rmssd"),
            "dfa_alpha1": frame.get("dfa_alpha1"),
            "ecg_mv": frame.get("ecg_mv") or frame.get("raw_samples") or frame.get("ecg_sample"),
            "acc_g": frame.get("acc_g") or frame.get("accel"),
            "skin_temp_c": frame.get("skin_temp_c"),
            "ptt_ms": frame.get("ptt_ms"),
            "delta_time_ms": frame.get("delta_time_ms", 0),
            "epoch_ms": frame.get("timestamp_epoch_ms") or frame.get("epoch_ms") or int(time.time() * 1000)
        }

    def _prepare_ws_payload(self, frame: Dict[str, Any]) -> Dict[str, Any]:
        """Maps internal frame to Port 4000 WebSocket push_tick action."""
        http_data = self._prepare_http_payload(frame)
        ecg_val = http_data.get("ecg_mv")
        if isinstance(ecg_val, list) and ecg_val:
            ecg_sample = ecg_val[0]
        elif isinstance(ecg_val, (int, float)):
            ecg_sample = float(ecg_val)
        else:
            ecg_sample = None

        return {
            "action": "push_tick",
            "session_token": http_data.get("session_token"),
            "tick": {
                "epoch_ms": http_data.get("epoch_ms"),
                "sensor_type": http_data.get("sensor_type"),
                "hr_bpm": http_data.get("heart_rate"),
                "rr_ms": http_data.get("rr_intervals_ms"),
                "rmssd": http_data.get("rmssd"),
                "dfa_alpha1": http_data.get("dfa_alpha1"),
                "ecg_sample": ecg_sample,
                "accel": http_data.get("acc_g"),
                "skin_temp_c": http_data.get("skin_temp_c"),
                "ptt_ms": http_data.get("ptt_ms"),
                "delta_time_ms": http_data.get("delta_time_ms", 0)
            }
        }

    def forward_http(self, frame: Dict[str, Any], frame_id: Optional[int] = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Synchronously forwards a telemetry frame via HTTP POST /api/sensors/ingest.
        Updates persistence sync state upon success.
        """
        url = f"{self.http_base_url}/api/sensors/ingest"
        payload = self._prepare_http_payload(frame)
        data = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json", "User-Agent": "LauburuPixelForwarder/2.0"}
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                success = (resp.status == 200)
                if success and self.persistence_engine and frame_id is not None:
                    self.persistence_engine.mark_frames_synced([frame_id])
                return success, resp_data
        except urllib.error.HTTPError as e:
            try:
                error_body = json.loads(e.read().decode("utf-8"))
            except Exception:
                error_body = {"error": str(e)}
            logger.warning(f"HTTP Error forwarding to {url}: {e.code} - {error_body}")
            return False, {"error": f"HTTP {e.code}", "detail": error_body}
        except Exception as e:
            logger.warning(f"Network error forwarding to {url}: {e}")
            return False, {"error": "Network connection error", "detail": str(e)}

    async def forward_http_async(self, frame: Dict[str, Any], frame_id: Optional[int] = None) -> Tuple[bool, Dict[str, Any]]:
        """Asynchronously forwards a frame via HTTP run in executor."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.forward_http, frame, frame_id)

    async def forward_ws_async(self, frame: Dict[str, Any], frame_id: Optional[int] = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Asynchronously sends a telemetry frame to the Port 4000 WebSocket endpoint.
        """
        if websockets is None:
            # Fallback to HTTP if websockets module not available
            return await self.forward_http_async(frame, frame_id)

        payload = self._prepare_ws_payload(frame)
        try:
            async with websockets.connect(self.ws_url) as ws:
                await ws.send(json.dumps(payload))
                if self.persistence_engine and frame_id is not None:
                    self.persistence_engine.mark_frames_synced([frame_id])
                return True, {"status": "success", "channel": "websocket", "payload": payload}
        except Exception as e:
            logger.warning(f"WebSocket forward error to {self.ws_url}: {e}")
            return False, {"error": "WebSocket error", "detail": str(e)}

    def sync_unsynced_frames(self, batch_size: int = 50) -> Dict[str, Any]:
        """
        Pulls pending unsynced records from the local SQLite engine and forwards them in order.
        Returns summary of synchronized frames.
        """
        if not self.persistence_engine:
            return {"synced": 0, "failed": 0, "remaining": 0}

        unsynced = self.persistence_engine.get_unsynced_frames(limit=batch_size)
        synced_count = 0
        failed_count = 0
        synced_ids = []

        for frame in unsynced:
            frame_id = frame.get("id")
            ok, _ = self.forward_http(frame)
            if ok:
                synced_count += 1
                if frame_id:
                    synced_ids.append(frame_id)
            else:
                failed_count += 1

        if synced_ids:
            self.persistence_engine.mark_frames_synced(synced_ids)

        remaining = len(self.persistence_engine.get_unsynced_frames(limit=1))
        return {
            "synced": synced_count,
            "failed": failed_count,
            "remaining": remaining,
            "synced_ids": synced_ids
        }
