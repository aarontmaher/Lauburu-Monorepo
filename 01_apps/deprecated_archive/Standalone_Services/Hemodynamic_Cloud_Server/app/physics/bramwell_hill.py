"""
Bramwell-Hill arterial distensibility and compliance formulations.
"""

import math

MMHG_TO_PA = 133.322387415
PA_TO_MMHG = 1.0 / MMHG_TO_PA
M3_TO_ML = 1.0e6


def bramwell_hill_wave_speed(
    volumetric_distensibility_pa_inv: float,
    blood_density_kg_m3: float = 1055.0
) -> float:
    """
    Calculate pulse wave velocity from volumetric distensibility D_v:
    c = sqrt( 1 / (rho * D_v) )

    Parameters:
        volumetric_distensibility_pa_inv: Arterial volume distensibility in Pa^-1
        blood_density_kg_m3: Blood mass density in kg/m^3

    Returns:
        Pulse wave velocity in m/s
    """
    if volumetric_distensibility_pa_inv <= 0.0 or blood_density_kg_m3 <= 0.0:
        raise ValueError("Distensibility and blood density must be strictly positive.")
    return math.sqrt(1.0 / (blood_density_kg_m3 * volumetric_distensibility_pa_inv))


def volumetric_distensibility(
    pwv_m_s: float,
    blood_density_kg_m3: float = 1055.0
) -> float:
    """
    Calculate volumetric distensibility D_v in SI units (Pa^-1) from PWV:
    D_v = 1 / (rho * PWV^2)
    """
    if pwv_m_s <= 0.0 or blood_density_kg_m3 <= 0.0:
        raise ValueError("PWV and blood density must be strictly positive.")
    return 1.0 / (blood_density_kg_m3 * (pwv_m_s ** 2))


def volumetric_distensibility_mmhg(
    pwv_m_s: float,
    blood_density_kg_m3: float = 1055.0
) -> float:
    """
    Calculate volumetric distensibility in clinical units (mmHg^-1):
    D_v_mmhg = 133.322 / (rho * PWV^2)
    """
    d_v_pa = volumetric_distensibility(pwv_m_s, blood_density_kg_m3)
    return d_v_pa * MMHG_TO_PA


def cross_sectional_compliance(
    pwv_m_s: float,
    diameter_m: float = 0.024,
    blood_density_kg_m3: float = 1055.0
) -> float:
    """
    Calculate arterial cross-sectional compliance C_A in m^2/Pa:
    C_A = A_0 / (rho * PWV^2) = (pi * d^2 / 4) / (rho * PWV^2)
    """
    if diameter_m <= 0.0:
        raise ValueError("Arterial diameter must be strictly positive.")
    a0 = (math.pi * (diameter_m ** 2)) / 4.0
    return a0 * volumetric_distensibility(pwv_m_s, blood_density_kg_m3)


def total_arterial_compliance(
    pwv_m_s: float,
    arterial_volume_m3: float = 0.0010,
    blood_density_kg_m3: float = 1055.0
) -> float:
    """
    Calculate Total Arterial Compliance (TAC / C_art) in SI units (m^3/Pa):
    TAC = V_0 / (rho * PWV^2)
    """
    if arterial_volume_m3 <= 0.0:
        raise ValueError("Arterial volume must be strictly positive.")
    return arterial_volume_m3 * volumetric_distensibility(pwv_m_s, blood_density_kg_m3)


def total_arterial_compliance_ml_per_mmhg(
    pwv_m_s: float,
    arterial_volume_m3: float = 0.0010,
    blood_density_kg_m3: float = 1055.0
) -> float:
    """
    Calculate Total Arterial Compliance in clinical units (mL/mmHg):
    C_art = (V_0 * 133.322 * 10^6) / (rho * PWV^2)
    """
    tac_si = total_arterial_compliance(pwv_m_s, arterial_volume_m3, blood_density_kg_m3)
    return tac_si * MMHG_TO_PA * M3_TO_ML
