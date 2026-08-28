"""
Master Hemodynamic Inversion Engine.
Transforms 6D telemetry vector u into continuous arterial pressure, compliance,
vascular resistance, and pulse wave velocity metrics with physiological clamping.
"""

import math
from typing import NamedTuple
import numpy as np
from app.core.config import settings
from app.physics.bramwell_hill import total_arterial_compliance_ml_per_mmhg
from app.physics.windkessel import calculate_peripheral_resistance_analytical


class InversionParameters(NamedTuple):
    blood_density: float = 1055.0
    nominal_path_length: float = 0.85
    nominal_blood_volume: float = 0.0010
    e_ref: float = 400.0
    a_sbp: float = -50.0
    b_sbp: float = 22.0
    c_sbp: float = 45.0
    k_hr_sbp: float = 0.18
    a_dbp: float = -30.0
    b_dbp: float = 14.0
    c_dbp: float = 35.0
    k_hr_dbp: float = 0.08
    k_motion: float = 0.05


DEFAULT_PARAMS = InversionParameters(
    blood_density=settings.NOMINAL_BLOOD_DENSITY_KG_M3,
    nominal_path_length=settings.NOMINAL_PATH_LENGTH_M,
    nominal_blood_volume=settings.NOMINAL_BLOOD_VOLUME_M3,
    e_ref=settings.E_REF_KPA,
    a_sbp=settings.A_SBP,
    b_sbp=settings.B_SBP,
    c_sbp=settings.C_SBP,
    k_hr_sbp=settings.K_HR_SBP,
    a_dbp=settings.A_DBP,
    b_dbp=settings.B_DBP,
    c_dbp=settings.C_DBP,
    k_hr_dbp=settings.K_HR_DBP,
    k_motion=settings.K_MOTION,
)


class InversionOutput(NamedTuple):
    systolic_bp_mmhg: float
    diastolic_bp_mmhg: float
    mean_arterial_pressure_mmhg: float
    pulse_pressure_mmhg: float
    arterial_compliance_ml_per_mmhg: float
    vascular_resistance_mmhg_s_per_ml: float
    pwv_m_s: float
    confidence_score: float


def calculate_signal_confidence(
    ptt_ms: float,
    hr_bpm: float,
    imu_acc_g: float
) -> float:
    """Calculate physiological signal confidence score in [0.0, 1.0]."""
    score = 1.0
    
    # PTT boundary penalties
    if ptt_ms < 100.0 or ptt_ms > 500.0:
        score *= 0.50
    elif ptt_ms < 140.0 or ptt_ms > 400.0:
        score *= 0.85
        
    # HR boundary penalties
    if hr_bpm < 35.0 or hr_bpm > 220.0:
        score *= 0.50
    elif hr_bpm < 45.0 or hr_bpm > 195.0:
        score *= 0.85
        
    # IMU excessive motion penalty
    if imu_acc_g > 3.0:
        score *= 0.60
    elif imu_acc_g > 1.8:
        score *= 0.85
        
    return max(0.05, min(1.0, float(score)))


def invert_hemodynamic_vector(
    ptt_ms: float,
    hr_bpm: float,
    rr_ms: float = 800.0,
    delta_t_dia_ms: float = 280.0,
    imu_acc_g: float = 1.0,
    e0_elasticity: float = 400.0,
    params: InversionParameters = DEFAULT_PARAMS
) -> InversionOutput:
    """
    Execute 6D telemetry vector inversion:
    u = [PTT, HR, RR, Delta_T_dia, ||a_IMU||, E_0] -> [SBP, DBP, MAP, PP, SVR, TAC, PWV]
    """
    # 1. Motion & Hydrostatic Artifact Correction
    motion_factor = 1.0 + params.k_motion * max(0.0, imu_acc_g - 1.0)
    ptt_sec = max(0.050, (ptt_ms / 1000.0) * motion_factor)
    
    # 2. Elasticity Ratio
    e_ratio = max(0.2, e0_elasticity / params.e_ref)
    
    # 3. Heart Rate Dynamic Shift
    hr_delta = max(-40.0, min(150.0, hr_bpm - 70.0)) if hr_bpm > 0.0 else 0.0
    
    # 4. Moens-Korteweg Logarithmic Inversion
    ln_ptt = math.log(ptt_sec)
    sbp_raw = (params.a_sbp * ln_ptt) + (params.b_sbp * e_ratio) + params.c_sbp + (params.k_hr_sbp * hr_delta)
    dbp_raw = (params.a_dbp * ln_ptt) + (params.b_dbp * e_ratio) + params.c_dbp + (params.k_hr_dbp * hr_delta)
    
    # 5. Physiological Invariant Enforcing & Clamping
    sbp = float(np.clip(sbp_raw, 70.0, 240.0))
    dbp = float(np.clip(dbp_raw, 40.0, 150.0))
    if sbp < dbp + 15.0:
        sbp = dbp + 15.0
        
    map_val = (1.0 / 3.0) * sbp + (2.0 / 3.0) * dbp
    pulse_pressure = sbp - dbp
    
    # 6. Bramwell-Hill PWV and Total Arterial Compliance
    pwv_est = (params.nominal_path_length / ptt_sec) * math.sqrt(e_ratio)
    pwv_clamped = max(3.0, min(25.0, pwv_est))
    c_art = total_arterial_compliance_ml_per_mmhg(
        pwv_clamped,
        params.nominal_blood_volume,
        params.blood_density
    )
    
    # 7. Windkessel Peripheral Resistance (SVR)
    delta_t_dia_s = max(0.05, delta_t_dia_ms / 1000.0)
    r_vasc = calculate_peripheral_resistance_analytical(
        delta_t_dia_s=delta_t_dia_s,
        c_art_ml_per_mmhg=c_art,
        sbp_mmhg=sbp,
        dbp_mmhg=dbp
    )
    
    # 8. Confidence Score
    confidence = calculate_signal_confidence(ptt_ms, hr_bpm, imu_acc_g)
    
    sbp_final = round(sbp, 1)
    dbp_final = round(dbp, 1)
    map_final = round((1.0 / 3.0) * sbp_final + (2.0 / 3.0) * dbp_final, 1)
    pp_final = round(sbp_final - dbp_final, 1)

    return InversionOutput(
        systolic_bp_mmhg=sbp_final,
        diastolic_bp_mmhg=dbp_final,
        mean_arterial_pressure_mmhg=map_final,
        pulse_pressure_mmhg=pp_final,
        arterial_compliance_ml_per_mmhg=round(c_art, 5),
        vascular_resistance_mmhg_s_per_ml=round(r_vasc, 3),
        pwv_m_s=round(pwv_clamped, 2),
        confidence_score=round(confidence, 2)
    )
