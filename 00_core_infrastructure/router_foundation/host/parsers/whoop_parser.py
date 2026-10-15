"""Whoop Biometrics Normalizer and Parser (Mac Mini Host).

Normalizes Whoop 4.0 telemetry (recovery, strain, HRV, heart rate, sleep, SpO2)
from both OpenWearables API payloads and live BLE GATT broadcasts.
Strictly compliant with Project Rule #0 (Zero-Mock) and Rule #3 (Host Sanctuary).
"""

from __future__ import annotations

import dataclasses
from datetime import datetime, timezone
import hashlib
import struct
from typing import Any, Dict, Optional, Union


@dataclasses.dataclass
class WhoopBiometricTelemetry:
    """Canonical Whoop Biometric Telemetry Record."""
    timestamp: str
    epoch: float
    source: str
    device_mac: Optional[str]
    device_name: Optional[str]
    recovery_score: Optional[float]
    resting_hr_bpm: Optional[float]
    hrv_rmssd_ms: Optional[float]
    spo2_pct: Optional[float]
    sleep_score: Optional[float]
    sleep_minutes: Optional[int]
    strain_score: Optional[float]
    calories: Optional[int]
    steps: Optional[int]
    heart_rate_bpm: Optional[int]
    battery_pct: Optional[int]
    skin_temp_celsius: Optional[float]
    raw_hex: str
    sha256_checksum: str = ""

    def compute_hash(self) -> str:
        content = (
            f"whoop:{self.epoch:.4f}:{self.device_mac}:{self.recovery_score}:"
            f"{self.strain_score}:{self.hrv_rmssd_ms}:{self.heart_rate_bpm}:{self.raw_hex}"
        )
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        d = dataclasses.asdict(self)
        if not d["sha256_checksum"]:
            d["sha256_checksum"] = self.compute_hash()
        return d


class WhoopParser:
    """Canonical Whoop normalizer supporting BLE manufacturer advertisements and OpenWearables API."""

    WHOOP_COMPANY_IDS = {0x02D7, 0x09EC}
    DEFAULT_NAME = "Whoop 4.0"

    def __init__(self, default_mac: Optional[str] = None):
        self.default_mac = default_mac

    def normalize_api(self, raw: Dict[str, Any], timestamp_epoch: Optional[float] = None) -> WhoopBiometricTelemetry:
        """Normalize raw Whoop cloud or OpenWearables API dictionary."""
        now_epoch = timestamp_epoch if timestamp_epoch is not None else datetime.now(timezone.utc).timestamp()
        ts_iso = datetime.fromtimestamp(now_epoch, tz=timezone.utc).isoformat()

        recovery = raw.get("recovery") or raw.get("score") or raw
        sleep = raw.get("sleep") or raw
        strain = raw.get("strain") or raw

        rec_score = recovery.get("recovery_score") if isinstance(recovery, dict) else None
        if rec_score is None and isinstance(recovery, dict):
            rec_score = recovery.get("score")
        r_hr = recovery.get("resting_heart_rate") if isinstance(recovery, dict) else None
        if r_hr is None and isinstance(recovery, dict):
            r_hr = recovery.get("resting_hr")
        hrv = recovery.get("hrv_rmssd_milli") if isinstance(recovery, dict) else None
        if hrv is None and isinstance(recovery, dict):
            hrv = recovery.get("hrv_rmssd")
        spo2 = recovery.get("spo2_percentage") if isinstance(recovery, dict) else None
        if spo2 is None and isinstance(recovery, dict):
            spo2 = recovery.get("spo2")

        sleep_score = sleep.get("sleep_score") if isinstance(sleep, dict) else None
        if sleep_score is None and isinstance(sleep, dict):
            sleep_score = sleep.get("score")
        total_sleep_ms = sleep.get("total_sleep_time_milli") if isinstance(sleep, dict) else None
        if total_sleep_ms is None and isinstance(sleep, dict):
            total_sleep_ms = sleep.get("duration_ms")
        total_sleep_min = round(float(total_sleep_ms) / 60000.0) if total_sleep_ms is not None else None

        strain_score = strain.get("strain_score") if isinstance(strain, dict) else None
        if strain_score is None and isinstance(strain, dict):
            strain_score = strain.get("score")
        active_kj = strain.get("kilojoules") if isinstance(strain, dict) else None
        if active_kj is not None:
            cals = round(float(active_kj) / 4.184)
        else:
            cals = int(raw.get("calories", 0)) if raw.get("calories") is not None else None

        live_hr = raw.get("heart_rate_bpm") or raw.get("current_hr")
        battery = raw.get("battery_pct") or raw.get("battery_percentage")
        skin_temp = raw.get("skin_temp_celsius") or raw.get("skin_temperature")
        steps_val = raw.get("steps")

        telemetry = WhoopBiometricTelemetry(
            timestamp=ts_iso,
            epoch=now_epoch,
            source="whoop",
            device_mac=raw.get("mac") or self.default_mac,
            device_name=raw.get("name") or self.DEFAULT_NAME,
            recovery_score=float(rec_score) if rec_score is not None else None,
            resting_hr_bpm=float(r_hr) if r_hr is not None else None,
            hrv_rmssd_ms=float(hrv) if hrv is not None else None,
            spo2_pct=float(spo2) if spo2 is not None else None,
            sleep_score=float(sleep_score) if sleep_score is not None else None,
            sleep_minutes=int(total_sleep_min) if total_sleep_min is not None else None,
            strain_score=float(strain_score) if strain_score is not None else None,
            calories=int(cals) if cals is not None else None,
            steps=int(steps_val) if steps_val is not None else None,
            heart_rate_bpm=int(live_hr) if live_hr is not None else None,
            battery_pct=int(battery) if battery is not None else None,
            skin_temp_celsius=float(skin_temp) if skin_temp is not None else None,
            raw_hex=raw.get("raw_hex", ""),
        )
        telemetry.sha256_checksum = telemetry.compute_hash()
        return telemetry

    def parse_ble_advertisement(
        self,
        raw_bytes: bytes,
        mac: Optional[str] = None,
        name: Optional[str] = None,
        timestamp_epoch: Optional[float] = None,
    ) -> WhoopBiometricTelemetry:
        """Parse raw Whoop BLE advertisement packet (Company ID 0x02D7 or 0x09EC)."""
        now_epoch = timestamp_epoch if timestamp_epoch is not None else datetime.now(timezone.utc).timestamp()
        ts_iso = datetime.fromtimestamp(now_epoch, tz=timezone.utc).isoformat()

        battery_pct: Optional[int] = None
        heart_rate: Optional[int] = None

        # Look for Company ID 0x02D7 (0xD7, 0x02) or 0x09EC (0xEC, 0x09)
        if len(raw_bytes) >= 2:
            company_id = struct.unpack("<H", raw_bytes[0:2])[0]
            if company_id in self.WHOOP_COMPANY_IDS:
                # Payload following company ID:
                # Byte 2: Battery percentage (0-100)
                # Byte 3: Live heart rate (if streaming enabled)
                if len(raw_bytes) >= 3:
                    batt_byte = raw_bytes[2]
                    if 0 <= batt_byte <= 100:
                        battery_pct = batt_byte
                if len(raw_bytes) >= 4:
                    hr_byte = raw_bytes[3]
                    if 30 <= hr_byte <= 220:
                        heart_rate = hr_byte

        telemetry = WhoopBiometricTelemetry(
            timestamp=ts_iso,
            epoch=now_epoch,
            source="whoop",
            device_mac=mac or self.default_mac,
            device_name=name or self.DEFAULT_NAME,
            recovery_score=None,
            resting_hr_bpm=None,
            hrv_rmssd_ms=None,
            spo2_pct=None,
            sleep_score=None,
            sleep_minutes=None,
            strain_score=None,
            calories=None,
            steps=None,
            heart_rate_bpm=heart_rate,
            battery_pct=battery_pct,
            skin_temp_celsius=None,
            raw_hex=raw_bytes.hex(),
        )
        telemetry.sha256_checksum = telemetry.compute_hash()
        return telemetry

    def parse_payload(
        self,
        payload: Union[bytes, str, Dict[str, Any]],
        device_mac: Optional[str] = None,
        timestamp_epoch: Optional[float] = None,
    ) -> WhoopBiometricTelemetry:
        """High-level dispatcher for API dict, hex string, or raw bytes."""
        if isinstance(payload, dict):
            # Check if it's raw BLE hex inside dict
            if "raw" in payload or "payload_hex" in payload:
                raw_hex = payload.get("raw") or payload.get("payload_hex", "")
                raw_bytes = bytes.fromhex(raw_hex) if isinstance(raw_hex, str) else bytes(raw_hex)
                mac = payload.get("mac") or device_mac or self.default_mac
                name = payload.get("name") or self.DEFAULT_NAME
                epoch = payload.get("timestamp") or payload.get("epoch") or timestamp_epoch
                return self.parse_ble_advertisement(raw_bytes, mac=mac, name=name, timestamp_epoch=epoch)
            return self.normalize_api(payload, timestamp_epoch=timestamp_epoch)

        if isinstance(payload, str):
            raw_bytes = bytes.fromhex(payload.strip())
            return self.parse_ble_advertisement(raw_bytes, mac=device_mac, timestamp_epoch=timestamp_epoch)

        return self.parse_ble_advertisement(payload, mac=device_mac, timestamp_epoch=timestamp_epoch)
