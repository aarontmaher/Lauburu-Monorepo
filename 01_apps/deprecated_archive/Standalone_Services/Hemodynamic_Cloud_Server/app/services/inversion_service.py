"""
Hemodynamic Inversion Service orchestrating physics solver, trend hunting, and SQLite WAL logging.
"""

import time
from typing import List, Optional, Tuple
from app.models.schemas import (
    BatchInversionRequest,
    BatchInversionResponse,
    HemodynamicEdgeState,
    InversionRequest,
    ZeroPiiEdgeResponse,
)
from app.physics.hemodynamic_inversion import invert_hemodynamic_vector
from app.services.trend_hunting_service import TrendHuntingService, get_trend_hunting_service
from app.storage.sqlite_manager import SqliteManager, get_sqlite_manager


def _extract_6d_vector(req: InversionRequest) -> Tuple[float, float, float, float, float, float, float, float]:
    """
    Extract (ptt_ms, hr_bpm, rr_ms, delta_t_dia_ms, imu_acc_g, e0_elasticity, dfa_a1, power)
    from request regardless of whether VectorU or ZeroPiiTelemetryVector was passed.
    """
    if req.vector_u is not None:
        u = req.vector_u
        return (
            u.ptt_ms,
            u.hr_bpm,
            u.rr_ms,
            u.delta_t_dia_ms,
            u.imu_acc_g,
            u.e0_elasticity,
            1.0,
            0.0
        )
    elif req.telemetry_vector is not None:
        vec = req.telemetry_vector
        ptt = vec.transit_hemodynamics.ptt_ms
        hr = vec.cardiac_autonomic.hr_bpm
        rr = (60000.0 / hr) if hr > 0 else 800.0
        # Calculate delta_t_dia from RR and estimated systolic duration
        te = 0.30 * ((rr / 1000.0) ** 0.5) * 1000.0
        delta_t_dia = max(100.0, rr - te)
        imu_acc = 1.0 + (vec.biomechanical_context.imu_acc_variance_g2 ** 0.5)
        e0 = vec.vascular_morphology.elasticity_baseline_e0 * 400.0
        dfa_a1 = vec.cardiac_autonomic.dfa_alpha1
        power = vec.biomechanical_context.pedal_power_watts
        return (ptt, hr, rr, delta_t_dia, imu_acc, e0, dfa_a1, power)
    else:
        # Defaults
        return (220.0, 72.0, 833.0, 280.0, 1.0, 400.0, 1.0, 0.0)


class InversionService:
    """Service coordinating hemodynamic mathematical inversion, database persistence, and trends."""

    def __init__(
        self,
        sqlite_manager: Optional[SqliteManager] = None,
        trend_service: Optional[TrendHuntingService] = None
    ):
        self.sqlite = sqlite_manager or get_sqlite_manager()
        self.trends = trend_service or get_trend_hunting_service()

    async def process_inversion(self, request: InversionRequest) -> ZeroPiiEdgeResponse:
        """Process a single real-time telemetry tick."""
        now_epoch_ms = int(time.time() * 1000)
        (
            ptt_ms,
            hr_bpm,
            rr_ms,
            delta_t_dia_ms,
            imu_acc_g,
            e0_elasticity,
            dfa_a1,
            power
        ) = _extract_6d_vector(request)

        # Execute genuine physics inversion
        inv = invert_hemodynamic_vector(
            ptt_ms=ptt_ms,
            hr_bpm=hr_bpm,
            rr_ms=rr_ms,
            delta_t_dia_ms=delta_t_dia_ms,
            imu_acc_g=imu_acc_g,
            e0_elasticity=e0_elasticity
        )

        # Evaluate trend insights
        insights = self.trends.evaluate_trends(
            session_hash=request.session_token,
            pwv_m_s=inv.pwv_m_s,
            hr_bpm=hr_bpm,
            vascular_resistance=inv.vascular_resistance_mmhg_s_per_ml,
            arterial_compliance=inv.arterial_compliance_ml_per_mmhg,
            dfa_alpha1=dfa_a1,
            pedal_power_watts=power
        )

        # Log tick asynchronously
        await self.sqlite.log_telemetry_tick(
            session_hash=request.session_token,
            tick_epoch_ms=now_epoch_ms,
            delta_time_ms=request.delta_time_ms,
            ptt_ms=ptt_ms,
            hr_bpm=hr_bpm,
            rr_ms=rr_ms,
            delta_t_dia_ms=delta_t_dia_ms,
            imu_acc_g=imu_acc_g,
            e0_elasticity=e0_elasticity,
            sbp_calc=inv.systolic_bp_mmhg,
            dbp_calc=inv.diastolic_bp_mmhg,
            map_calc=inv.mean_arterial_pressure_mmhg,
            pulse_pressure_calc=inv.pulse_pressure_mmhg,
            vascular_resistance=inv.vascular_resistance_mmhg_s_per_ml,
            confidence_score=inv.confidence_score
        )

        state = HemodynamicEdgeState(
            systolic_bp_mmHg=inv.systolic_bp_mmhg,
            diastolic_bp_mmHg=inv.diastolic_bp_mmhg,
            mean_arterial_pressure_mmHg=inv.mean_arterial_pressure_mmhg,
            pulse_pressure_mmHg=inv.pulse_pressure_mmhg,
            arterial_compliance=inv.arterial_compliance_ml_per_mmhg,
            vascular_resistance=inv.vascular_resistance_mmhg_s_per_ml,
            pwv_m_s=inv.pwv_m_s,
            confidence_score=inv.confidence_score
        )

        return ZeroPiiEdgeResponse(
            protocol_version=request.protocol_version,
            session_token=request.session_token,
            delta_time_ms=request.delta_time_ms,
            hemodynamic_state=state,
            trend_hunting_insights=insights
        )

    async def process_batch(self, request: BatchInversionRequest) -> BatchInversionResponse:
        """Process batch buffered ticks for session replay or synchronization."""
        results: List[ZeroPiiEdgeResponse] = []
        for tick in request.ticks:
            sub_req = InversionRequest(
                protocol_version=request.protocol_version,
                session_token=request.session_token,
                delta_time_ms=tick.delta_time_ms,
                telemetry_vector=tick.telemetry_vector,
                vector_u=tick.vector_u
            )
            res = await self.process_inversion(sub_req)
            results.append(res)

        return BatchInversionResponse(
            protocol_version=request.protocol_version,
            session_token=request.session_token,
            total_processed=len(results),
            results=results
        )


_global_inversion_service: Optional[InversionService] = None


def get_inversion_service() -> InversionService:
    global _global_inversion_service
    if _global_inversion_service is None:
        _global_inversion_service = InversionService()
    return _global_inversion_service
