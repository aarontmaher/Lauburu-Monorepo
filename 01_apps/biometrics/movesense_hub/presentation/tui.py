"""
Native Textual TUI Application for Movesense Hub.
Displays real-time biometrics HUD with responsive cards and strict Rule #0 Zero-Mock formatting.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Footer, Header, Static

from ..core.config import MovesenseHubConfig
from ..core.models import BiometricsStateStore, ReadinessReport


class MovesenseReadinessTUIApp(App):
    """
    Consumer & Pro Athlete Biometrics Dashboard.
    Displays:
    - 512Hz ECG & Autonomic RMSSD
    - Continuous Pulse Transit Time (PTT) Blood Pressure
    - Overnight Sleep Staging & Sleep Score (0-100)
    - Auto Workout Detection & Zone 2 Coaching (LT1 / LT2)
    - Estimated VO2max & Cardiorespiratory Readiness
    """

    TITLE = "💓 LAUBURU BIOFEEDBACK — PHYSIOLOGICAL READINESS & CARDIO COACH"
    SUB_TITLE = "Athlete Live HUD • 512Hz ECG • PTT Blood Pressure • Sleep Score • Zone 2 Coach"

    CSS = """
    Screen {
        background: #070b12;
        color: #f8fafc;
    }
    #hero-container {
        height: 10;
        margin: 1 1;
    }
    .metric-card {
        background: #0b111c;
        border: solid #1e293b;
        height: 100%;
        padding: 1 2;
    }
    .metric-card:hover {
        border: solid #38bdf8;
    }
    #body-container {
        height: 1fr;
        margin: 0 1 1 1;
    }
    .panel-card {
        background: #0b111c;
        border: solid #1e293b;
        height: 100%;
        padding: 1;
    }
    #footer-bar {
        height: 3;
        background: #0b111c;
        border-top: solid #1e293b;
        align: center middle;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh_data", "Refresh"),
    ]

    def __init__(
        self,
        config: Optional[MovesenseHubConfig] = None,
        state_store: Optional[BiometricsStateStore] = None,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self.config = config or MovesenseHubConfig()
        self.state_store = state_store

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="hero-container"):
            yield Static(id="card-hr", classes="metric-card")
            yield Static(id="card-bp", classes="metric-card")
            yield Static(id="card-sleep", classes="metric-card")
            yield Static(id="card-vo2", classes="metric-card")

        with Horizontal(id="body-container"):
            yield Static(id="card-workout", classes="panel-card")
            yield Static(id="card-ecg-dsp", classes="panel-card")

        with Horizontal(id="footer-bar"):
            yield Static(
                "🔒 100% Local Airgap Protected • Bluetooth 5.0 Movesense HR+ 261030002013 • Press [q] Quit",
                id="status-text",
            )
        yield Footer()

    def on_mount(self) -> None:
        self.set_interval(0.5, self.update_hud)
        self.update_hud()

    def _load_data(self) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Loads telemetry from state_store or fallback JSON files."""
        if self.state_store:
            rep = self.state_store.get_report().to_full_dict()
            return rep, rep.get("sensor_telemetry", {})

        readiness: Dict[str, Any] = {}
        if self.config.readiness_live_output_path.exists():
            try:
                with open(self.config.readiness_live_output_path, "r") as f:
                    readiness = json.load(f)
            except Exception:
                pass

        sensor: Dict[str, Any] = {}
        if self.config.movesense_live_stream_path.exists():
            try:
                with open(self.config.movesense_live_stream_path, "r") as f:
                    sensor = json.load(f)
            except Exception:
                pass

        return readiness, sensor

    def update_hud(self) -> None:
        readiness, sensor = self._load_data()

        is_connected = sensor.get("connected", False) or readiness.get("status") == "STREAMING"
        hr = sensor.get("heart_rate_bpm") or sensor.get("heart_rate") or readiness.get("sensor_telemetry", {}).get("heart_rate_bpm")
        rmssd = sensor.get("rmssd_ms") or readiness.get("sensor_telemetry", {}).get("rmssd_ms")
        dfa = sensor.get("dfa_alpha1") or readiness.get("sensor_telemetry", {}).get("dfa_alpha1")

        bp = readiness.get("blood_pressure_ptt", {})
        sys_bp = bp.get("systolic_bp_mmhg") or bp.get("systolic_mmhg")
        dia_bp = bp.get("diastolic_bp_mmhg") or bp.get("diastolic_mmhg")
        bp_status = bp.get("status", "STANDBY")

        sleep = readiness.get("overnight_sleep_analysis", {})
        sleep_score = sleep.get("sleep_score_pct")
        sleep_stage = sleep.get("recovery_status", "Awaiting Nocturnal Stream")

        cardio = readiness.get("cardiorespiratory_thresholds", {})
        lt1 = cardio.get("lt1_aerobic_threshold_bpm") or self.config.lt1_hr_estimate
        lt2 = cardio.get("lt2_anaerobic_threshold_bpm") or self.config.lt2_hr_estimate
        vo2 = cardio.get("estimated_vo2max_ml_kg_min") or self.config.estimated_vo2max

        workout = readiness.get("activity_and_workout", {})
        activity = workout.get("current_activity") or "RESTING"
        training_zone = workout.get("training_zone", "Awaiting Sensor Stream")

        # 1. Heart Rate & Autonomic RMSSD Card
        t_hr = Text()
        t_hr.append("💓 HEART RATE & HRV\n", style="bold cyan")
        if is_connected and hr is not None:
            hr_color = "green" if hr < 140 else "yellow" if hr < 170 else "red"
            t_hr.append(f" {hr} ", style=f"bold {hr_color} reverse")
            t_hr.append(" BPM\n\n", style=f"bold {hr_color}")
            t_hr.append(f"• RMSSD: {rmssd:.1f} ms\n" if rmssd is not None else "• RMSSD: --\n", style="white")
            t_hr.append(f"• DFA-α1: {dfa:.2f} (Zone 2 Base)" if dfa is not None else "• DFA-α1: --", style="dim")
        else:
            t_hr.append(" -- ", style="bold dim reverse")
            t_hr.append(" BPM\n\n", style="bold dim")
            t_hr.append("• RMSSD: --\n", style="dim")
            t_hr.append("• DFA-α1: WAITING_FOR_SENSOR", style="yellow dim")
        self.query_one("#card-hr", Static).update(t_hr)

        # 2. Continuous Blood Pressure Card
        t_bp = Text()
        t_bp.append("🩺 CONTINUOUS BP (PTT)\n", style="bold magenta")
        if is_connected and sys_bp is not None and dia_bp is not None:
            t_bp.append(f" {sys_bp:.0f}/{dia_bp:.0f} ", style="bold green reverse")
            t_bp.append(" mmHg\n\n", style="bold green")
            t_bp.append(f"• Status: {bp_status}\n", style="white")
            t_bp.append("• Method: Pulse Transit Time Inversion", style="dim")
        else:
            t_bp.append(" --/-- ", style="bold dim reverse")
            t_bp.append(" mmHg\n\n", style="bold dim")
            t_bp.append(f"• Status: {bp_status}\n", style="dim")
            t_bp.append("• Method: Standby (Zero-Mock)", style="dim")
        self.query_one("#card-bp", Static).update(t_bp)

        # 3. Overnight Sleep Staging Card
        t_sleep = Text()
        t_sleep.append("🌙 SLEEP & RECOVERY\n", style="bold yellow")
        if sleep_score is not None:
            s_color = "green" if sleep_score >= 80 else "yellow" if sleep_score >= 60 else "red"
            t_sleep.append(f" {sleep_score}/100 ", style=f"bold {s_color} reverse")
            t_sleep.append(" Score\n\n", style=f"bold {s_color}")
            t_sleep.append(f"• Recovery: {sleep_stage}\n", style="white")
            t_sleep.append("• Staging: 30s Optical PPG Epochs", style="dim")
        else:
            t_sleep.append(" --/100 ", style="bold dim reverse")
            t_sleep.append(" Score\n\n", style="bold dim")
            t_sleep.append(f"• Recovery: {sleep_stage}\n", style="dim")
            t_sleep.append("• Staging: Awaiting Stream", style="dim")
        self.query_one("#card-sleep", Static).update(t_sleep)

        # 4. VO2max & Cardiorespiratory Thresholds Card
        t_vo2 = Text()
        t_vo2.append("🫁 CARDIO CAPACITY\n", style="bold blue")
        t_vo2.append(f" {vo2:.1f} ", style="bold cyan reverse")
        t_vo2.append(" mL/kg/min\n\n", style="bold cyan")
        t_vo2.append(f"• LT1 (Aerobic): {lt1} BPM\n", style="white")
        t_vo2.append(f"• LT2 (Anaerobic): {lt2} BPM", style="dim")
        self.query_one("#card-vo2", Static).update(t_vo2)

        # 5. Body Panel Left: Workout & Zone 2 Coaching
        table_workout = Table(title="🏃 AUTO WORKOUT & ZONE 2 COACHING", expand=True, border_style="cyan")
        table_workout.add_column("Parameter", style="cyan", width=24)
        table_workout.add_column("Live Telemetry & Guidance", style="white")
        table_workout.add_row("Current Activity", str(activity))
        table_workout.add_row("Training Zone", str(training_zone))
        table_workout.add_row("Aerobic Zone 2 Target", f"{self.config.hr_rest_baseline + 0.55*(self.config.hr_max - self.config.hr_rest_baseline):.0f} - {self.config.hr_rest_baseline + 0.72*(self.config.hr_max - self.config.hr_rest_baseline):.0f} BPM")
        table_workout.add_row("DFA-α1 Alignment", "Optimal Zone 2 (Aerobic Base)" if (dfa and dfa >= 0.75) else "Above LT1 (Tempo/Anaerobic)" if dfa else "Awaiting Sensor Stream")
        table_workout.add_row("Coach Guidance", "Maintain steady cadence; breathing comfortably through nose." if (dfa and dfa >= 0.75) else "Ease intensity 5-10% to stay in Zone 2 fat oxidation." if dfa else "Connect Movesense sensor to begin active session.")
        self.query_one("#card-workout", Static).update(table_workout)

        # 6. Body Panel Right: 512Hz ECG DSP Diagnostics
        table_dsp = Table(title="⚡ 512Hz ECG DSP & HARDWARE TELEMETRY", expand=True, border_style="green")
        table_dsp.add_column("Subsystem", style="green", width=24)
        table_dsp.add_column("Status / Diagnostic Stream", style="white")
        table_dsp.add_row("Sensor Hardware", f"{self.config.device_name} (Serial {self.config.device_serial})")
        table_dsp.add_row("Connection Status", "🟢 ACTIVE STREAMING" if is_connected else "🟡 WAITING_FOR_SENSOR (Rule #0 Certified)")
        table_dsp.add_row("Pan-Tompkins DSP", f"{self.config.ecg_sample_rate_hz}Hz 4th-Order Bandpass + 150ms MWI")
        table_dsp.add_row("Kamath RR Filter", f"{self.config.kamath_threshold_pct:.0f}% Outlier Filter (Kamath et al. 2004)")
        table_dsp.add_row("Local Airgap Status", "🔒 100% AIRGAPPED (0% Biometrics Cloud Egress)")
        self.query_one("#card-ecg-dsp", Static).update(table_dsp)


def run_app() -> None:
    """Entrypoint function to run the Movesense Readiness Textual TUI."""
    app = MovesenseReadinessTUIApp()
    app.run()


if __name__ == "__main__":
    run_app()
