"""
Acute and longitudinal trend hunting service for cardiovascular drift,
vascular fatigue, endothelial reserve tracking, and Zone 2 aerobic boundary compliance.
"""

from typing import Dict, List, Optional
from app.models.schemas import TrendHuntingInsights


class SessionTrendState:
    """In-memory rolling buffer state for active sessions."""

    def __init__(self, session_hash: str):
        self.session_hash = session_hash
        self.initial_pwv: Optional[float] = None
        self.initial_hr: Optional[float] = None
        self.initial_power: Optional[float] = None
        self.history_pwv: List[float] = []
        self.history_hr: List[float] = []
        self.history_power: List[float] = []
        self.history_r_vasc: List[float] = []
        self.history_c_art: List[float] = []


class TrendHuntingService:
    """
    Evaluates acute and rolling-window hemodynamic changes to detect
    cardiovascular drift and autonomic/vascular strain without PII.
    """

    def __init__(self):
        self._sessions: Dict[str, SessionTrendState] = {}

    def get_or_create_state(self, session_hash: str) -> SessionTrendState:
        if session_hash not in self._sessions:
            self._sessions[session_hash] = SessionTrendState(session_hash)
        return self._sessions[session_hash]

    def evaluate_trends(
        self,
        session_hash: str,
        pwv_m_s: float,
        hr_bpm: float,
        vascular_resistance: float,
        arterial_compliance: float,
        dfa_alpha1: float = 1.0,
        pedal_power_watts: float = 0.0
    ) -> TrendHuntingInsights:
        state = self.get_or_create_state(session_hash)

        # Baseline capture
        if state.initial_pwv is None and pwv_m_s > 0.0:
            state.initial_pwv = pwv_m_s
        if state.initial_hr is None and hr_bpm > 0.0:
            state.initial_hr = hr_bpm
        if state.initial_power is None and pedal_power_watts > 0.0:
            state.initial_power = pedal_power_watts

        state.history_pwv.append(pwv_m_s)
        state.history_hr.append(hr_bpm)
        state.history_r_vasc.append(vascular_resistance)
        state.history_c_art.append(arterial_compliance)
        if pedal_power_watts > 0:
            state.history_power.append(pedal_power_watts)

        # 1. Arterial Stiffness Drift (%)
        stiffness_drift_pct = 0.0
        if state.initial_pwv and state.initial_pwv > 0:
            stiffness_drift_pct = ((pwv_m_s - state.initial_pwv) / state.initial_pwv) * 100.0

        # 2. Vascular Fatigue Index [0.0 - 1.0]
        # Evaluated as combination of elevated resistance and reduced compliance
        r_mean = sum(state.history_r_vasc[-10:]) / len(state.history_r_vasc[-10:])
        c_mean = sum(state.history_c_art[-10:]) / len(state.history_c_art[-10:])
        vfi_raw = (r_mean / 2.0) * (0.002 / max(1e-5, c_mean))
        vascular_fatigue = min(1.0, max(0.0, float(vfi_raw - 0.5)))

        # 3. Endothelial Reserve Status
        if abs(stiffness_drift_pct) < 5.0 and vascular_fatigue < 0.30:
            reserve_status = "optimal"
        elif abs(stiffness_drift_pct) < 12.0 or vascular_fatigue < 0.65:
            reserve_status = "strained"
        else:
            reserve_status = "exhausted"

        # 4. Cardiovascular Drift Detection
        # HR rising by > 6% over session while power is steady/declining (or in long aerobic state)
        cardiac_drift = False
        if state.initial_hr and state.initial_hr > 0 and len(state.history_hr) > 20:
            hr_rise_pct = ((hr_bpm - state.initial_hr) / state.initial_hr) * 100.0
            if hr_rise_pct > 6.0:
                cardiac_drift = True

        # 5. Zone 2 Compliance (DFA alpha-1 thresholding)
        # Zone 2 is typically DFA a1 between 0.75 and 1.00
        if dfa_alpha1 >= 0.75:
            zone2_comp = "in_zone2_aerobic"
        elif dfa_alpha1 >= 0.65:
            zone2_comp = "upper_zone2_threshold"
        else:
            zone2_comp = "aerobic_threshold_breach"

        return TrendHuntingInsights(
            arterial_stiffness_drift_pct=round(stiffness_drift_pct, 2),
            vascular_fatigue_index=round(vascular_fatigue, 2),
            endothelial_reserve_status=reserve_status,
            cardiac_drift_detected=cardiac_drift,
            zone2_compliance=zone2_comp
        )


_global_trend_hunting_service: Optional[TrendHuntingService] = None


def get_trend_hunting_service() -> TrendHuntingService:
    global _global_trend_hunting_service
    if _global_trend_hunting_service is None:
        _global_trend_hunting_service = TrendHuntingService()
    return _global_trend_hunting_service
