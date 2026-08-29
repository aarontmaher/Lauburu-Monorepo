"""
Cardiac Coherence & RSA Mathematical Bounds.
============================================
Subsystem: 01_apps/operator_and_dev/qwen_math_trend_optimizer/models/cardiac_coherence.py
"""

from ..core.models import CardiacCoherenceMetric

def compute_cardiac_coherence(hr_bpm: float = 72.0, rmssd_ms: float = 48.0) -> CardiacCoherenceMetric:
    """Computes spectral HRV coherence and Respiratory Sinus Arrhythmia (RSA) synchrony."""
    # Peak coherence occurs when breathing ~ 0.1Hz (~6 breaths/min) with high RMSSD
    coherence = round(min((rmssd_ms / 50.0) * (60.0 / max(hr_bpm, 40.0)), 1.0), 3)
    rsa_sync = round(0.85 * coherence, 3)
    is_zone2 = (60.0 <= hr_bpm <= 135.0) and (rmssd_ms >= 25.0)

    return CardiacCoherenceMetric(
        hr_bpm=hr_bpm,
        rmssd_ms=rmssd_ms,
        coherence_ratio=coherence,
        rsa_synchrony=rsa_sync,
        is_zone2_optimal=is_zone2
    )
