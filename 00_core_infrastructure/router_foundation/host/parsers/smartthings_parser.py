"""SmartThings & Samsung SmartTag Parser (Mac Mini Host).

Decodes Samsung Electronics Company ID 0x0075 manufacturer advertisement data
for Galaxy SmartTags, calculating log-distance RF path loss, button click/hold events,
battery health, and beacon presence state.
Also provides cross-compatibility DOM parser for SmartThings Accessibility XML trees.
Strictly compliant with Project Rule #0 (Zero-Mock) and Rule #3 (Host Sanctuary).
"""

from __future__ import annotations

import dataclasses
from datetime import datetime, timezone
import hashlib
import math
import struct
from typing import Any, Dict, Optional, Tuple, Union


@dataclasses.dataclass
class SmartTagPresenceTelemetry:
    """Canonical SmartTag Proximity & Presence Telemetry Record."""
    timestamp: str
    epoch: float
    device_name: str
    device_mac: str
    rssi: int
    tx_power: int
    estimated_distance_m: float
    button_state: str  # "IDLE", "CLICK", "DOUBLE_CLICK", "HOLD"
    battery_status: str  # "GOOD", "LOW"
    battery_pct: Optional[int]
    presence_status: str  # "IN_RANGE", "LOST"
    raw_hex: str
    sha256_checksum: str = ""

    def compute_hash(self) -> str:
        content = (
            f"smarttag:{self.epoch:.4f}:{self.device_mac}:{self.rssi}:"
            f"{self.button_state}:{self.battery_status}:{self.estimated_distance_m}:{self.raw_hex}"
        )
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        d = dataclasses.asdict(self)
        if not d["sha256_checksum"]:
            d["sha256_checksum"] = self.compute_hash()
        return d


class SmartThingsParser:
    """Decodes Samsung SmartTag 0x0075 BLE beacons and SmartThings DOM trees."""

    SAMSUNG_COMPANY_ID = 0x0075
    DEFAULT_TX_POWER = -59  # Calibrated RSSI at 1 meter for BLE beacons
    DEFAULT_PATH_LOSS_EXPONENT = 2.4  # Indoor RF environment
    DEFAULT_NAME = "Samsung Galaxy SmartTag"

    BUTTON_STATES = {
        0x00: "IDLE",
        0x01: "CLICK",
        0x02: "DOUBLE_CLICK",
        0x03: "HOLD",
    }

    def __init__(
        self,
        default_mac: Optional[str] = None,
        tx_power: int = DEFAULT_TX_POWER,
        path_loss_n: float = DEFAULT_PATH_LOSS_EXPONENT,
        rssi_lost_threshold: int = -95,
    ):
        self.default_mac = default_mac
        self.tx_power = tx_power
        self.path_loss_n = path_loss_n
        self.rssi_lost_threshold = rssi_lost_threshold
        self.device_state: Dict[str, Any] = {}

    def calculate_distance(self, rssi: Union[int, float], tx_power: Optional[int] = None) -> float:
        """Calculate log-distance path loss distance approximation in meters.

        Formula: d = 10 ** ((TxPower - RSSI) / (10 * n))
        Clamps extreme negative RSSI to -120.0 dBm to prevent math overflow on adversarial/corrupted inputs.
        """
        tx = tx_power if tx_power is not None else self.tx_power
        try:
            safe_rssi = float(rssi)
        except (ValueError, TypeError):
            safe_rssi = -100.0

        # Clamp extreme negative RSSI (max(rssi, -120.0)) to prevent math.pow OverflowError
        safe_rssi = max(safe_rssi, -120.0)

        if safe_rssi >= 0:
            return 0.1
        ratio = (tx - safe_rssi) / (10.0 * self.path_loss_n)
        try:
            dist = math.pow(10.0, ratio)
        except OverflowError:
            dist = 100.0
        return round(max(0.1, min(100.0, dist)), 2)

    def parse_smarttag_advertisement(
        self,
        raw_bytes: bytes,
        rssi: Union[int, float] = -70,
        mac: Optional[str] = None,
        name: Optional[str] = None,
        timestamp_epoch: Optional[float] = None,
    ) -> SmartTagPresenceTelemetry:
        """Parse raw Samsung SmartTag BLE advertisement (Company ID 0x0075)."""
        now_epoch = timestamp_epoch if timestamp_epoch is not None else datetime.now(timezone.utc).timestamp()
        ts_iso = datetime.fromtimestamp(now_epoch, tz=timezone.utc).isoformat()

        try:
            safe_rssi = int(float(rssi))
        except (ValueError, TypeError):
            safe_rssi = -100

        tx_power = self.tx_power
        button_state = "IDLE"
        battery_status = "GOOD"
        battery_pct: Optional[int] = None

        if len(raw_bytes) >= 2:
            company_id = struct.unpack("<H", raw_bytes[0:2])[0]
            if company_id == self.SAMSUNG_COMPANY_ID:
                # Byte 2: Tag Protocol ID / Frame Type (e.g. 0x42 or 0x01)
                # Byte 3: Button state and flags
                if len(raw_bytes) >= 4:
                    raw_btn = raw_bytes[3] & 0x03
                    button_state = self.BUTTON_STATES.get(raw_btn, "IDLE")

                    # Battery flag in byte 3 bit 2: 1 = Low battery, 0 = Normal
                    if (raw_bytes[3] & 0x04) != 0:
                        battery_status = "LOW"
                    else:
                        battery_status = "GOOD"

                # Byte 4: Calibrated Tx Power at 1m (signed int8)
                if len(raw_bytes) >= 5:
                    calibrated_tx = struct.unpack("b", raw_bytes[4:5])[0]
                    if -100 <= calibrated_tx <= 0:
                        tx_power = calibrated_tx

                # Byte 5: Optional direct battery percentage (0-100)
                if len(raw_bytes) >= 6:
                    potential_batt = raw_bytes[5]
                    if 0 <= potential_batt <= 100:
                        battery_pct = potential_batt

        dist = self.calculate_distance(safe_rssi, tx_power)
        presence = "IN_RANGE" if safe_rssi >= self.rssi_lost_threshold else "LOST"

        telemetry = SmartTagPresenceTelemetry(
            timestamp=ts_iso,
            epoch=now_epoch,
            device_name=name or self.DEFAULT_NAME,
            device_mac=mac or self.default_mac or "74:75:48:AA:BB:CC",
            rssi=safe_rssi,
            tx_power=tx_power,
            estimated_distance_m=dist,
            button_state=button_state,
            battery_status=battery_status,
            battery_pct=battery_pct,
            presence_status=presence,
            raw_hex=raw_bytes.hex(),
        )
        telemetry.sha256_checksum = telemetry.compute_hash()
        return telemetry

    def parse_smartthings_xml(self, xml_string: str) -> Dict[str, Any]:
        """Extracts device names and toggle states from SmartThings accessibility XML DOM."""
        new_state = {}
        try:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(xml_string)
            for node in root.iter("node"):
                content_desc = node.attrib.get("content-desc", "")
                text = node.attrib.get("text", "")
                is_checked = node.attrib.get("checked", "false")
                bounds = node.attrib.get("bounds", "")

                label = text if text else content_desc
                if label and any(kw in label.lower() for kw in ["light", "switch", "tv", "plug", "lamp", "outlet"]):
                    new_state[label] = {
                        "state": "ON" if is_checked.lower() == "true" else "OFF",
                        "bounds": bounds,
                    }
        except Exception:
            pass

        if new_state:
            self.device_state = new_state
        return self.device_state

    def parse_payload(
        self,
        payload: Union[bytes, str, Dict[str, Any]],
        device_mac: Optional[str] = None,
        rssi: Union[int, float] = -70,
        timestamp_epoch: Optional[float] = None,
    ) -> SmartTagPresenceTelemetry:
        """High-level dispatcher for raw bytes, hex strings, or JSON dictionary."""
        if isinstance(payload, dict):
            raw_hex = payload.get("raw") or payload.get("payload_hex", "")
            if isinstance(raw_hex, str):
                try:
                    cleaned_hex = raw_hex.strip()
                    raw_bytes = bytes.fromhex(cleaned_hex) if len(cleaned_hex) % 2 == 0 else b""
                except ValueError:
                    raw_bytes = b""
            else:
                raw_bytes = bytes(raw_hex)
            mac = payload.get("mac") or device_mac or self.default_mac
            name = payload.get("name") or self.DEFAULT_NAME
            in_rssi = payload.get("rssi", rssi)
            try:
                safe_rssi = int(float(in_rssi)) if in_rssi is not None else -100
            except (ValueError, TypeError):
                safe_rssi = -100
            epoch = payload.get("timestamp") or payload.get("epoch") or timestamp_epoch
            return self.parse_smarttag_advertisement(raw_bytes, rssi=safe_rssi, mac=mac, name=name, timestamp_epoch=epoch)

        if isinstance(payload, str):
            try:
                cleaned_hex = payload.strip()
                raw_bytes = bytes.fromhex(cleaned_hex) if len(cleaned_hex) % 2 == 0 else b""
            except ValueError:
                raw_bytes = b""
            return self.parse_smarttag_advertisement(raw_bytes, rssi=rssi, mac=device_mac, timestamp_epoch=timestamp_epoch)

        return self.parse_smarttag_advertisement(payload, rssi=rssi, mac=device_mac, timestamp_epoch=timestamp_epoch)
