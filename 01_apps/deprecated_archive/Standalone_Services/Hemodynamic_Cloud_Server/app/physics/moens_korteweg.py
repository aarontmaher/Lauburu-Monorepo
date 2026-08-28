"""
Moens-Korteweg hydrodynamic wave speed and Hughes non-linear strain-stiffening formulations.
"""

import math
from typing import Tuple
import numpy as np


def moens_korteweg_wave_speed(
    young_modulus_pa: float,
    wall_thickness_m: float,
    inner_diameter_m: float,
    blood_density_kg_m3: float = 1055.0
) -> float:
    """
    Calculate baseline pulse wave velocity (PWV_0) using the classical Moens-Korteweg equation:
    PWV_0 = sqrt( (E * h) / (rho * d) )

    Parameters:
        young_modulus_pa: Arterial wall Young's modulus E in Pascals (N/m^2)
        wall_thickness_m: Wall thickness h in meters
        inner_diameter_m: Internal vessel diameter d in meters
        blood_density_kg_m3: Blood density rho in kg/m^3 (default 1055.0)

    Returns:
        Pulse wave propagation speed in meters/second (m/s)
    """
    if young_modulus_pa <= 0.0 or wall_thickness_m <= 0.0 or inner_diameter_m <= 0.0 or blood_density_kg_m3 <= 0.0:
        raise ValueError("All physical parameters must be strictly positive.")
    
    numerator = young_modulus_pa * wall_thickness_m
    denominator = blood_density_kg_m3 * inner_diameter_m
    return math.sqrt(numerator / denominator)


def hughes_strain_stiffening(
    e0_pa: float,
    pressure_mmhg: float,
    gamma: float = 0.017
) -> float:
    """
    Calculate pressure-dependent Young's modulus using the Hughes exponential strain-stiffening relation:
    E(P) = E_0 * exp(gamma * P)

    Parameters:
        e0_pa: Baseline zero-pressure elastic modulus in Pascals
        pressure_mmhg: Transmural arterial pressure in mmHg
        gamma: Vessel-specific non-linear stiffness coefficient in mmHg^-1 (nominal 0.017)

    Returns:
        Pressure-coupled elastic modulus E(P) in Pascals
    """
    if e0_pa <= 0.0:
        raise ValueError("Baseline elasticity E0 must be strictly positive.")
    return e0_pa * math.exp(gamma * pressure_mmhg)


def pressure_dependent_pwv(
    pwv0: float,
    pressure_mmhg: float,
    gamma: float = 0.017
) -> float:
    """
    Calculate continuous pulse wave velocity at transmural pressure P:
    PWV(P) = PWV_0 * exp( (gamma / 2) * P )

    Parameters:
        pwv0: Baseline zero-pressure wave speed in m/s
        pressure_mmhg: Arterial pressure in mmHg
        gamma: Stiffness coefficient in mmHg^-1

    Returns:
        PWV(P) in m/s
    """
    if pwv0 <= 0.0:
        raise ValueError("PWV0 must be strictly positive.")
    return pwv0 * math.exp(0.5 * gamma * pressure_mmhg)


def moens_korteweg_pressure_inversion(
    ptt_sec: float,
    path_length_m: float,
    pwv0: float,
    gamma: float = 0.017
) -> float:
    """
    Analytically invert Pulse Transit Time (PTT) into blood pressure P:
    P = - (2 / gamma) * ln(PTT) + (2 / gamma) * ln(L / PWV_0)

    Parameters:
        ptt_sec: Pulse transit time in seconds
        path_length_m: Arterial propagation path length in meters
        pwv0: Baseline pulse wave velocity in m/s
        gamma: Stiffness coefficient in mmHg^-1

    Returns:
        Calculated blood pressure P in mmHg
    """
    if ptt_sec <= 0.0 or path_length_m <= 0.0 or pwv0 <= 0.0 or gamma <= 0.0:
        raise ValueError("PTT, path length, PWV0, and gamma must be strictly positive.")
    
    coeff_a = -2.0 / gamma
    coeff_b = (2.0 / gamma) * math.log(path_length_m / pwv0)
    return coeff_a * math.log(ptt_sec) + coeff_b


def logarithmic_moens_korteweg_bp(
    ptt_sec: float,
    e_ratio: float,
    hr_bpm: float,
    a_sbp: float = -50.0,
    b_sbp: float = 22.0,
    c_sbp: float = 45.0,
    k_hr_sbp: float = 0.18,
    a_dbp: float = -30.0,
    b_dbp: float = 14.0,
    c_dbp: float = 35.0,
    k_hr_dbp: float = 0.08
) -> Tuple[float, float]:
    """
    Execute calibrated logarithmic Moens-Korteweg inversion for SBP and DBP.
    
    Formula:
    SBP = a_sbp * ln(PTT_sec) + b_sbp * e_ratio + c_sbp + k_hr_sbp * (HR - 70)
    DBP = a_dbp * ln(PTT_sec) + b_dbp * e_ratio + c_dbp + k_hr_dbp * (HR - 70)

    Returns:
        Tuple of (sbp_mmhg, dbp_mmhg)
    """
    if ptt_sec <= 0.0:
        raise ValueError("PTT must be strictly positive.")
    
    hr_delta = hr_bpm - 70.0 if hr_bpm > 0.0 else 0.0
    ln_ptt = math.log(ptt_sec)
    
    sbp = (a_sbp * ln_ptt) + (b_sbp * e_ratio) + c_sbp + (k_hr_sbp * hr_delta)
    dbp = (a_dbp * ln_ptt) + (b_dbp * e_ratio) + c_dbp + (k_hr_dbp * hr_delta)
    
    return float(sbp), float(dbp)
