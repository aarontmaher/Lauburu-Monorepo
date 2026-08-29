"""
Web Bluetooth & WebSocket Client Biometrics Ingestion Bridge.
Bridges browser-based Web Bluetooth API frames (movesenseBleService.ts) and Web-TUI clients
into the core Movesense DSP and state store.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from ..core.config import MovesenseHubConfig
from ..core.models import BiometricsStateStore, ReadinessReport
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

logger = logging.getLogger("web_ble_bridge")


class WebBleBridge:
    """
    Bridge connecting Web Bluetooth and WebSocket streams to the Movesense Hub.
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
            hr_rest_baseline=self.config.hr_rest_baseline,
        )
        self._rr_buffer: List[float] = []

    def ingest_sig_hrs_frame(
        self,
        hr_bpm: Optional[int],
        rr_intervals_ms: Optional[List[float]] = None,
        device_name: Optional[str] = None,
    ) -> ReadinessReport:
        """
        Ingests a decoded Heart Rate frame from Web Bluetooth (0x2A37).
        Strict Rule #0: if hr_bpm is None or <= 0, emits WAITING_FOR_SENSOR.
        """
        if hr_bpm is None or hr_bpm <= 0:
            report = ReadinessReport(
                status="WAITING_FOR_SENSOR",
                device_name=device_name or self.config.device_name,
                connected=False,
                heart_rate_bpm=None,
                rmssd_ms=None,
                dfa_alpha1=None,
                rule_0_zero_mock=True,
            )
            self.state_store.update_report(report)
            return report

        rrs = rr_intervals_ms or []
        if rrs:
            cleaned_rrs, _ = apply_kamath_artifact_filter(rrs, threshold_pct=self.config.kamath_threshold_pct)
            self._rr_buffer.extend(cleaned_rrs)
            if len(self._rr_buffer) > self.config.rr_history_max_len:
                self._rr_buffer = self._rr_buffer[-self.config.rr_history_max_len :]

        active_rrs = self._rr_buffer if self._rr_buffer else rrs
        rmssd = calculate_rmssd(active_rrs)
        dfa_a1 = calculate_dfa_alpha1(
            active_rrs, scale_min=self.config.dfa_scale_min, scale_max=self.config.dfa_scale_max
        )

        bp = self.bp_model.compute_ptt_blood_pressure(hr_bpm, rmssd)
        sleep = self.sleep_engine.compute_overnight_sleep_analysis(hr_bpm, rmssd)
        workout = classify_workout_state(hr_bpm, hr_max=self.config.hr_max)
        cardio = compute_cardiorespiratory_thresholds(
            hr_bpm, dfa_a1, hr_max=self.config.hr_max, hr_rest_baseline=self.config.hr_rest_baseline
        )

        report = ReadinessReport(
            status="STREAMING",
            device_name=device_name or self.config.device_name,
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
        return report

    def ingest_raw_ecg_samples(
        self,
        samples_mv: List[float],
        sample_rate_hz: Optional[int] = None,
        ptt_ms: Optional[float] = None,
        device_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Processes a raw ECG sample batch (e.g. from /Meas/ECG/128 or /Meas/ECG/512).
        """
        fs = sample_rate_hz or self.config.ecg_sample_rate_hz
        if self.pipeline.sample_rate_hz != fs:
            self.pipeline = MovesenseECGPipeline(sample_rate_hz=fs)

        result = self.pipeline.process_raw_ecg_window(
            ecg_samples=samples_mv,
            ptt_ms=ptt_ms,
            device_id=device_name or self.config.device_name,
        )

        # Update state store if connected
        if result.get("connected") and result.get("heart_rate_bpm") is not None:
            hr = float(result["heart_rate_bpm"])
            rmssd = result.get("rmssd_ms")
            dfa = result.get("dfa_alpha1")
            bp = self.bp_model.compute_ptt_blood_pressure(hr, rmssd, ptt_ms=ptt_ms)
            sleep = self.sleep_engine.compute_overnight_sleep_analysis(hr, rmssd)
            workout = classify_workout_state(hr, hr_max=self.config.hr_max)
            cardio = compute_cardiorespiratory_thresholds(
                hr, dfa, hr_max=self.config.hr_max, hr_rest_baseline=self.config.hr_rest_baseline
            )

            report = ReadinessReport(
                status="STREAMING",
                device_name=device_name or self.config.device_name,
                connected=True,
                heart_rate_bpm=hr,
                rmssd_ms=rmssd,
                dfa_alpha1=dfa,
                blood_pressure=bp,
                sleep_analysis=sleep,
                workout=workout,
                cardiorespiratory=cardio,
                rule_0_zero_mock=True,
            )
            self.state_store.update_report(report)

        return result

    def ingest_web_ble_packet(self, packet: Dict[str, Any]) -> ReadinessReport:
        """
        Generic dictionary packet ingestion handler from WebSocket JSON.
        """
        if not packet or not packet.get("connected", False):
            return self.ingest_sig_hrs_frame(None)

        hr = packet.get("heart_rate_bpm") or packet.get("heart_rate")
        rrs = packet.get("rr_intervals_ms") or packet.get("rr_intervals_recent") or []
        device = packet.get("device_name") or packet.get("device")
        return self.ingest_sig_hrs_frame(hr_bpm=hr, rr_intervals_ms=rrs, device_name=device)

    def reset_to_disconnected(self) -> ReadinessReport:
        """Emits clean Rule #0 WAITING_FOR_SENSOR state."""
        return self.ingest_sig_hrs_frame(None)
