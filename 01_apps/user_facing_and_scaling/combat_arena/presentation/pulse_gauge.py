"""
Live Movesense Pulse Gauge & Telemetry View.
============================================
Subsystem: 01_apps/user_facing_and_scaling/combat_arena/presentation/pulse_gauge.py
"""

from rich.text import Text
from ..core.models import PulseTelemetry

def render_pulse_gauge(telemetry: PulseTelemetry) -> Text:
    """Renders live biometric pulse gauge adhering strictly to Rule #0."""
    t = Text()
    t.append("💓 MOVESENSE BIOFEEDBACK\n", style="bold red")
    
    if telemetry.is_connected and telemetry.heart_rate_bpm is not None:
        hr = round(telemetry.heart_rate_bpm, 1)
        rmssd = round(telemetry.rmssd_ms, 1) if telemetry.rmssd_ms is not None else "--"
        t.append(f"• Heart Rate: {hr} BPM\n", style="bold green")
        t.append(f"• HRV RMSSD: {rmssd} ms\n", style="white")
        zone_style = "bold green" if telemetry.zone2_aligned else "bold yellow"
        t.append(f"• Zone 2 Coached: {'YES' if telemetry.zone2_aligned else 'NO'}\n", style=zone_style)
        t.append("• Stream: 512Hz Pan-Tompkins DSP (Airgapped)", style="dim")
    else:
        t.append("• Status: [WAITING_FOR_SENSOR]\n", style="bold yellow")
        t.append("• Live HR: -- BPM\n", style="dim")
        t.append("• HRV RMSSD: -- ms\n", style="dim")
        t.append("• Zero-Mock Rule #0 Enforced", style="bold cyan")
    return t
