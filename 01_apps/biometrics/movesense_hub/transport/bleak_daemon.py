"""
Movesense Bleak Bluetooth Low Energy GATT Ingestion Daemon.
Direct hardware communication with Movesense sensor serial 261030002013.
Implements:
- Movesense MDS 2.0 Whiteboard Protocol (34800001-7185-4d5d-b431-b30e393d9e05)
- Standard Bluetooth SIG Heart Rate Service (0x180D / 0x2A37)
- Standard Battery Service (0x180F / 0x2A19)
- Real-time DSP packet feeding & state synchronization
- Strict Rule #0 Zero-Mock validation (WAITING_FOR_SENSOR when disconnected).
"""

from __future__ import annotations

import asyncio
import logging
import struct
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..core.config import MovesenseHubConfig
from ..core.models import BiometricsStateStore, RawEcgFrame, ReadinessReport
from ..dsp.hemodynamics_bp import ContinuousPttBloodPressureModel
from ..dsp.pan_tompkins import (
    MovesenseECGPipeline,
    apply_kamath_artifact_filter,
    calculate_dfa_alpha1,
    calculate_rmssd,
)
from ..dsp.sleep_scoring import SleepStagingEngine
from ..dsp.zone2_coaching import (
    Zone2CoachingEngine,
    classify_workout_state,
    compute_cardiorespiratory_thresholds,
)

# Bleak conditional import
try:
    import bleak
    from bleak import BleakClient, BleakScanner
    BLEAK_AVAILABLE = True
except ImportError:
    bleak = None
    BleakClient = None
    BleakScanner = None
    BLEAK_AVAILABLE = False

logger = logging.getLogger("movesense_bleak_daemon")

# 128-bit Movesense MDS 2.0 & SIG UUIDs
MOVESENSE_MDS_SERVICE_UUID = "34800001-7185-4d5d-b431-b30e393d9e05"
MOVESENSE_COMMAND_CHAR_UUID = "34800001-7185-4d5d-b431-b30e393d9e05"
MOVESENSE_DATA_CHAR_UUID_1 = "34800002-7185-4d5d-b431-b30e393d9e05"
MOVESENSE_DATA_CHAR_UUID_2 = "34800003-7185-4d5d-b431-b30e393d9e05"

SIG_HRS_SERVICE_UUID = "0000180d-0000-1000-8000-00805f9b34fb"
SIG_HRS_MEASUREMENT_UUID = "00002a37-0000-1000-8000-00805f9b34fb"
SIG_BATTERY_LEVEL_UUID = "00002a19-0000-1000-8000-00805f9b34fb"


def decode_sig_heart_rate_measurement(data: bytes) -> Tuple[int, List[float]]:
    """
    Decodes standard Bluetooth SIG 0x2A37 Heart Rate Measurement payload.
    Returns (heart_rate_bpm, rr_intervals_ms).
    """
    if not data or len(data) < 2:
        return 0, []

    flags = data[0]
    hr_is_uint16 = bool(flags & 0x01)
    rr_present = bool(flags & 0x10)

    offset = 1
    if hr_is_uint16:
        if len(data) < 3:
            return 0, []
        hr_bpm = struct.unpack("<H", data[1:3])[0]
        offset = 3
    else:
        hr_bpm = int(data[1])
        offset = 2

    # Check Energy Expended field (flags & 0x08)
    if flags & 0x08:
        offset += 2

    rr_intervals: List[float] = []
    if rr_present:
        while offset + 1 < len(data):
            raw_rr = struct.unpack("<H", data[offset : offset + 2])[0]
            # Convert 1/1024 seconds to milliseconds
            rr_ms = round((raw_rr / 1024.0) * 1000.0, 1)
            if 250.0 <= rr_ms <= 2200.0:  # Physiological filter
                rr_intervals.append(rr_ms)
            offset += 2

    return hr_bpm, rr_intervals


def decode_movesense_ecg_packet(data: bytes) -> Optional[RawEcgFrame]:
    """
    Decodes Movesense MDS 2.0 /Meas/ECG data notification packet.
    Packet structure:
    - Byte 0: response type (0x02 for notification)
    - Byte 1: reference id
    - Bytes 2-5: uint32 timestamp (ms or us)
    - Remaining bytes: sequence of int32 or int16 ECG samples (microvolts / millivolts)
    """
    if not data or len(data) < 6:
        return None

    try:
        # Check notification header
        if data[0] == 0x02:
            ts = struct.unpack("<I", data[2:6])[0]
            samples_raw = data[6:]
            samples_mv: List[float] = []

            # Determine int32 vs int16 sample format
            if len(samples_raw) % 4 == 0:
                num_samples = len(samples_raw) // 4
                for i in range(num_samples):
                    val = struct.unpack("<i", samples_raw[i * 4 : (i + 1) * 4])[0]
                    samples_mv.append(val / 1000.0)  # uV to mV
            elif len(samples_raw) % 2 == 0:
                num_samples = len(samples_raw) // 2
                for i in range(num_samples):
                    val = struct.unpack("<h", samples_raw[i * 2 : (i + 1) * 2])[0]
                    samples_mv.append(val / 1000.0)

            return RawEcgFrame(
                timestamp_us=int(ts * 1000),
                sample_rate_hz=512 if len(samples_mv) > 16 else 128,
                samples_mv=samples_mv
            )
    except Exception as e:
        logger.debug("Failed to decode Movesense ECG packet: %s", e)

    return None


class MovesenseBleakDaemon:
    """
    Asynchronous Bleak GATT Ingestion Daemon for Movesense 261030002013.
    """

    def __init__(
        self,
        config: Optional[MovesenseHubConfig] = None,
        state_store: Optional[BiometricsStateStore] = None,
    ):
        self.config = config or MovesenseHubConfig()
        self.state_store = state_store or BiometricsStateStore(
            persistence_path=self.config.readiness_live_output_path,
            lora_dataset_path=self.config.lora_dataset_output_path,
        )
        self.pipeline = MovesenseECGPipeline(sample_rate_hz=self.config.ecg_sample_rate_hz)
        self.bp_model = ContinuousPttBloodPressureModel(hr_rest_baseline=self.config.hr_rest_baseline)
        self.sleep_engine = SleepStagingEngine(hr_rest_baseline=self.config.hr_rest_baseline)
        self.zone2_engine = Zone2CoachingEngine(
            user_age=self.config.user_age,
            hr_rest_baseline=self.config.hr_rest_baseline
        )

        self._running = False
        self._connected = False
        self._client: Optional[Any] = None
        self._rr_buffer: List[float] = []
        self._packet_count = 0
        self._battery_pct: Optional[int] = None

    @property
    def is_connected(self) -> bool:
        return self._connected

    def handle_hrs_notification(self, sender: Any, data: bytearray) -> None:
        """Processes incoming SIG 0x2A37 Heart Rate Measurement notification."""
        hr_bpm, rrs = decode_sig_heart_rate_measurement(bytes(data))
        if hr_bpm <= 0:
            return

        self._packet_count += 1
        if rrs:
            cleaned_rrs, _ = apply_kamath_artifact_filter(rrs, threshold_pct=self.config.kamath_threshold_pct)
            self._rr_buffer.extend(cleaned_rrs)
            if len(self._rr_buffer) > self.config.rr_history_max_len:
                self._rr_buffer = self._rr_buffer[-self.config.rr_history_max_len :]

        active_rrs = self._rr_buffer if self._rr_buffer else rrs
        rmssd = calculate_rmssd(active_rrs)
        dfa_a1 = calculate_dfa_alpha1(active_rrs, scale_min=self.config.dfa_scale_min, scale_max=self.config.dfa_scale_max)

        # Compute DSP models
        bp = self.bp_model.compute_ptt_blood_pressure(hr_bpm, rmssd)
        sleep = self.sleep_engine.compute_overnight_sleep_analysis(hr_bpm, rmssd)
        workout = classify_workout_state(hr_bpm, hr_max=self.config.hr_max)
        cardio = compute_cardiorespiratory_thresholds(
            hr_bpm, dfa_a1, hr_max=self.config.hr_max, hr_rest_baseline=self.config.hr_rest_baseline
        )

        report = ReadinessReport(
            status="STREAMING",
            device_name=self.config.device_name,
            connected=True,
            heart_rate_bpm=float(hr_bpm),
            rmssd_ms=rmssd,
            dfa_alpha1=dfa_a1,
            blood_pressure=bp,
            sleep_analysis=sleep,
            workout=workout,
            cardiorespiratory=cardio,
            rule_0_zero_mock=True,
        )

        self.state_store.update_report(report)

    def handle_battery_notification(self, sender: Any, data: bytearray) -> None:
        """Processes incoming SIG 0x2A19 Battery Level notification."""
        if data:
            self._battery_pct = int(data[0])

    def emit_disconnected_state(self) -> None:
        """Emits explicit Rule #0 WAITING_FOR_SENSOR state."""
        self._connected = False
        report = ReadinessReport(
            status="WAITING_FOR_SENSOR",
            device_name=self.config.device_name,
            connected=False,
            heart_rate_bpm=None,
            rmssd_ms=None,
            dfa_alpha1=None,
            rule_0_zero_mock=True,
        )
        self.state_store.update_report(report)

    async def run_daemon(self) -> None:
        """Main async loop attempting connection to physical Movesense sensor."""
        self._running = True
        self.emit_disconnected_state()

        if not BLEAK_AVAILABLE:
            logger.warning("Bleak is not available in environment. MovesenseBleakDaemon in standby.")
            while self._running:
                await asyncio.sleep(1.0)
            return

        address = self.config.device_mac_address
        while self._running:
            try:
                logger.info("Attempting BLE connection to Movesense %s...", address)
                async with BleakClient(address, timeout=self.config.ble_timeout_sec) as client:
                    self._client = client
                    self._connected = client.is_connected
                    if self._connected:
                        logger.info("Connected to Movesense %s. Subscribing to GATT services...", address)
                        await client.start_notify(SIG_HRS_MEASUREMENT_UUID, self.handle_hrs_notification)
                        try:
                            await client.start_notify(SIG_BATTERY_LEVEL_UUID, self.handle_battery_notification)
                        except Exception:
                            pass

                        while self._running and client.is_connected:
                            await asyncio.sleep(0.5)

            except Exception as e:
                logger.debug("Bleak connection error (%s). Reconnecting in %.1fs...", e, self.config.reconnect_interval_sec)
            finally:
                self._connected = False
                self.emit_disconnected_state()
                if self._running:
                    await asyncio.sleep(self.config.reconnect_interval_sec)

    def stop(self) -> None:
        self._running = False
        self.emit_disconnected_state()
