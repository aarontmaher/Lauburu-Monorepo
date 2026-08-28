"""
2-Element (WK2) and 3-Element (WK3) Windkessel arterial hemodynamics models,
analytical diastolic decay solvers, numerical ODE integrators, and SciPy parameter estimators.
"""

import math
from typing import Dict, Optional, Tuple, Any
import numpy as np
from scipy.optimize import least_squares


def diastolic_decay_time_constant(
    delta_t_dia_s: float,
    p_notch_mmhg: float,
    dbp_mmhg: float
) -> float:
    """
    Calculate Windkessel systemic hemodynamic time constant tau = R_p * C
    from diastolic pressure decay duration:
    tau = Delta_T_dia / ln( P_notch / DBP )
    """
    if delta_t_dia_s <= 0.0 or p_notch_mmhg <= 0.0 or dbp_mmhg <= 0.0:
        raise ValueError("Inputs must be strictly positive.")
    
    ratio = max(1.02, p_notch_mmhg / dbp_mmhg)
    return delta_t_dia_s / math.log(ratio)


def calculate_peripheral_resistance_analytical(
    delta_t_dia_s: float,
    c_art_ml_per_mmhg: float,
    sbp_mmhg: float,
    dbp_mmhg: float,
    alpha_notch: float = 0.85
) -> float:
    """
    Calculate Systemic Vascular Resistance (SVR / R_p) analytically from diastolic decay:
    R_p = Delta_T_dia / (C_art * ln(alpha_notch * SBP / DBP))
    
    Returns:
        R_p in mmHg*s/mL (nominal 0.8 - 1.4 mmHg*s/mL)
    """
    if c_art_ml_per_mmhg <= 0.0 or delta_t_dia_s <= 0.0:
        return 1.10
    
    ratio = max(1.05, (sbp_mmhg * alpha_notch) / max(30.0, dbp_mmhg))
    tau = delta_t_dia_s / math.log(ratio)
    return tau / c_art_ml_per_mmhg


def generate_cardiac_inflow(
    t_samples: np.ndarray,
    hr_bpm: float,
    stroke_volume_ml: float = 75.0,
    ejection_time_sec: Optional[float] = None
) -> np.ndarray:
    """
    Generate physiological aortic inflow waveform Q(t) using half-sine ejection model.
    
    Q(t) = (pi * SV / (2 * Te)) * sin(pi * t / Te) for 0 <= t <= Te, else 0
    """
    period = 60.0 / hr_bpm
    te = ejection_time_sec if ejection_time_sec is not None else 0.30 * math.sqrt(period)
    
    t_cycle = t_samples % period
    q = np.where(
        t_cycle <= te,
        (math.pi * stroke_volume_ml / (2.0 * te)) * np.sin(math.pi * t_cycle / te),
        0.0
    )
    return q


def solve_wk2_explicit_euler(
    q_inflow: np.ndarray,
    dt: float,
    rp: float,
    c: float,
    p0: Optional[float] = None
) -> np.ndarray:
    """
    Solve 2-Element Windkessel ODE using Explicit Euler (O(dt)):
    P_{k+1} = P_k * (1 - dt / (rp * c)) + (dt / c) * Q_k
    """
    n = len(q_inflow)
    p = np.zeros(n, dtype=np.float64)
    tau = rp * c
    p[0] = p0 if p0 is not None else np.mean(q_inflow) * rp
    
    decay = 1.0 - (dt / tau)
    step_input = dt / c
    
    for k in range(n - 1):
        p[k + 1] = p[k] * decay + step_input * q_inflow[k]
        
    return p


def solve_wk2_implicit_euler(
    q_inflow: np.ndarray,
    dt: float,
    rp: float,
    c: float,
    p0: Optional[float] = None
) -> np.ndarray:
    """
    Solve 2-Element Windkessel ODE using Implicit Backward Euler (O(dt), A-stable):
    P_{k+1} = (P_k + (dt / c) * Q_{k+1}) / (1 + dt / (rp * c))
    """
    n = len(q_inflow)
    p = np.zeros(n, dtype=np.float64)
    tau = rp * c
    p[0] = p0 if p0 is not None else np.mean(q_inflow) * rp
    
    denom = 1.0 + (dt / tau)
    step_input = dt / c
    
    for k in range(n - 1):
        p[k + 1] = (p[k] + step_input * q_inflow[k + 1]) / denom
        
    return p


def solve_wk2_trapezoidal(
    q_inflow: np.ndarray,
    dt: float,
    rp: float,
    c: float,
    p0: Optional[float] = None
) -> np.ndarray:
    """
    Solve 2-Element Windkessel ODE using Crank-Nicolson / Trapezoidal (O(dt^2), A-stable):
    P_{k+1} = [ P_k * (1 - dt / (2*tau)) + (dt / (2*c)) * (Q_k + Q_{k+1}) ] / (1 + dt / (2*tau))
    """
    n = len(q_inflow)
    p = np.zeros(n, dtype=np.float64)
    tau = rp * c
    alpha = dt / (2.0 * tau)
    beta = dt / (2.0 * c)
    
    c1 = (1.0 - alpha) / (1.0 + alpha)
    c2 = beta / (1.0 + alpha)
    
    p[0] = p0 if p0 is not None else np.mean(q_inflow) * rp
    for k in range(n - 1):
        p[k + 1] = c1 * p[k] + c2 * (q_inflow[k] + q_inflow[k + 1])
        
    return p


def solve_wk2_rk4(
    q_inflow: np.ndarray,
    dt: float,
    rp: float,
    c: float,
    p0: Optional[float] = None
) -> np.ndarray:
    """
    Solve 2-Element Windkessel ODE using Classical 4th-Order Runge-Kutta (O(dt^4)).
    """
    n = len(q_inflow)
    p = np.zeros(n, dtype=np.float64)
    tau = rp * c
    p[0] = p0 if p0 is not None else np.mean(q_inflow) * rp
    
    inv_c = 1.0 / c
    inv_tau = 1.0 / tau
    
    for k in range(n - 1):
        qk = q_inflow[k]
        qk1 = q_inflow[k + 1]
        q_mid = 0.5 * (qk + qk1)
        
        k1 = inv_c * qk - inv_tau * p[k]
        k2 = inv_c * q_mid - inv_tau * (p[k] + 0.5 * dt * k1)
        k3 = inv_c * q_mid - inv_tau * (p[k] + 0.5 * dt * k2)
        k4 = inv_c * qk1 - inv_tau * (p[k] + dt * k3)
        
        p[k + 1] = p[k] + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)
        
    return p


def solve_wk3_trapezoidal(
    q_inflow: np.ndarray,
    dt: float,
    rp: float,
    c: float,
    zc: float,
    num_warmup_cycles: int = 3
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Solve 3-Element Westerhof Windkessel (WK3: Zc, Rp, C) using Trapezoidal Crank-Nicolson method.
    
    State equations:
    dPc/dt = -Pc / (Rp * C) + Q(t) / C
    P(t) = Pc(t) + Zc * Q(t)
    
    Returns:
        Tuple of (p_total, pc_compliance_pressure)
    """
    n_points = len(q_inflow)
    tau = rp * c
    alpha = dt / (2.0 * tau)
    beta = dt / (2.0 * c)
    
    c1 = (1.0 - alpha) / (1.0 + alpha)
    c2 = beta / (1.0 + alpha)
    
    pc = float(np.mean(q_inflow) * rp)
    
    # Warmup cycles to reach steady-state periodic limit cycle
    for _ in range(num_warmup_cycles):
        for k in range(n_points - 1):
            pc = c1 * pc + c2 * (q_inflow[k] + q_inflow[k + 1])
            
    pc_arr = np.zeros(n_points, dtype=np.float64)
    pc_arr[0] = pc
    for k in range(n_points - 1):
        pc_arr[k + 1] = c1 * pc_arr[k] + c2 * (q_inflow[k] + q_inflow[k + 1])
        
    p_total = pc_arr + zc * q_inflow
    return p_total, pc_arr


def solve_wk3_rk4(
    q_inflow: np.ndarray,
    dt: float,
    rp: float,
    c: float,
    zc: float,
    num_warmup_cycles: int = 3
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Solve 3-Element Westerhof Windkessel using 4th-Order Runge-Kutta integration.
    
    Returns:
        Tuple of (p_total, pc_compliance_pressure)
    """
    n_points = len(q_inflow)
    tau = rp * c
    inv_c = 1.0 / c
    inv_tau = 1.0 / tau
    
    pc = float(np.mean(q_inflow) * rp)
    
    # Warmup cycles
    for _ in range(num_warmup_cycles):
        for k in range(n_points - 1):
            qk = q_inflow[k]
            qk1 = q_inflow[k + 1]
            q_mid = 0.5 * (qk + qk1)
            
            k1 = inv_c * qk - inv_tau * pc
            k2 = inv_c * q_mid - inv_tau * (pc + 0.5 * dt * k1)
            k3 = inv_c * q_mid - inv_tau * (pc + 0.5 * dt * k2)
            k4 = inv_c * qk1 - inv_tau * (pc + dt * k3)
            pc = pc + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)
            
    pc_arr = np.zeros(n_points, dtype=np.float64)
    pc_arr[0] = pc
    for k in range(n_points - 1):
        qk = q_inflow[k]
        qk1 = q_inflow[k + 1]
        q_mid = 0.5 * (qk + qk1)
        
        k1 = inv_c * qk - inv_tau * pc_arr[k]
        k2 = inv_c * q_mid - inv_tau * (pc_arr[k] + 0.5 * dt * k1)
        k3 = inv_c * q_mid - inv_tau * (pc_arr[k] + 0.5 * dt * k2)
        k4 = inv_c * qk1 - inv_tau * (pc_arr[k] + dt * k3)
        pc_arr[k + 1] = pc_arr[k] + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)
        
    p_total = pc_arr + zc * q_inflow
    return p_total, pc_arr


def fit_windkessel_parameters(
    t_samples: np.ndarray,
    p_measured: np.ndarray,
    hr_bpm: float,
    prior_guess: Optional[np.ndarray] = None
) -> Dict[str, Any]:
    """
    Fit Windkessel parameters theta = [Rp, C, Zc, SV, Te] using non-linear least squares
    with Trust Region Reflective (TRF) algorithm and Soft L1 robust loss.
    """
    period = 60.0 / hr_bpm
    dt = float(t_samples[1] - t_samples[0])
    
    if prior_guess is None:
        p_mean = float(np.mean(p_measured))
        pp = float(np.max(p_measured) - np.min(p_measured))
        c_init = float(np.clip(70.0 / max(20.0, pp), 0.5, 2.5))
        rp_init = float(np.clip((p_mean * period) / 70.0, 0.6, 2.0))
        zc_init = 0.06 * rp_init
        sv_init = (p_mean * period) / rp_init
        te_init = 0.30 * math.sqrt(period)
        theta_0 = np.array([rp_init, c_init, zc_init, sv_init, te_init], dtype=np.float64)
    else:
        theta_0 = np.asarray(prior_guess, dtype=np.float64)

    lower_bounds = np.array([0.40, 0.35, 0.02, 35.0, 0.18], dtype=np.float64)
    upper_bounds = np.array([2.80, 3.50, 0.25, 180.0, 0.45], dtype=np.float64)

    def residual_fn(theta: np.ndarray) -> np.ndarray:
        rp, c, zc, sv, te = theta
        t_cycle = t_samples % period
        q = np.where(
            t_cycle <= te,
            (math.pi * sv / (2.0 * te)) * np.sin(math.pi * t_cycle / te),
            0.0
        )
        p_sim, _ = solve_wk3_trapezoidal(q, dt, rp, c, zc)
        return p_sim - p_measured

    try:
        res = least_squares(
            residual_fn,
            x0=theta_0,
            bounds=(lower_bounds, upper_bounds),
            method='trf',
            loss='soft_l1',
            f_scale=2.5,
            max_nfev=60,
            ftol=1e-4,
            xtol=1e-4
        )
        if res.success:
            return {
                "rp": float(res.x[0]),
                "c": float(res.x[1]),
                "zc": float(res.x[2]),
                "sv": float(res.x[3]),
                "te": float(res.x[4]),
                "cost": float(res.cost),
                "converged": True
            }
    except Exception:
        pass

    return {
        "rp": float(theta_0[0]),
        "c": float(theta_0[1]),
        "zc": float(theta_0[2]),
        "sv": float(theta_0[3]),
        "te": float(theta_0[4]),
        "cost": 0.0,
        "converged": False
    }


def verify_mass_conservation(
    q_inflow: np.ndarray,
    pc: np.ndarray,
    rp: float,
    dt: float
) -> float:
    """
    Verify conservation of fluid mass over complete cardiac cycles:
    Total Inflow Stroke Volume = Total Peripheral Outflow Volume
    int( Q(t) dt ) == int( Pc(t) / Rp dt )
    
    Returns:
        Absolute volumetric difference in mL
    """
    inflow_vol = float(np.trapezoid(q_inflow, dx=dt) if hasattr(np, 'trapezoid') else np.trapz(q_inflow, dx=dt))
    outflow_vol = float(np.trapezoid(pc / rp, dx=dt) if hasattr(np, 'trapezoid') else np.trapz(pc / rp, dx=dt))
    return abs(inflow_vol - outflow_vol)


def verify_energy_dissipation(
    p_total: np.ndarray,
    pc: np.ndarray,
    q_inflow: np.ndarray,
    rp: float,
    zc: float,
    dt: float
) -> float:
    """
    Verify periodic energy balance:
    Total Left Ventricular Work W_LV = Dissipated Viscous Energy E_diss
    int( P(t) * Q(t) dt ) == int( Pc^2 / Rp + Zc * Q^2 dt )
    
    Returns:
        Absolute energy difference in Joules (or mmHg*mL equivalent)
    """
    w_lv = float(np.trapezoid(p_total * q_inflow, dx=dt) if hasattr(np, 'trapezoid') else np.trapz(p_total * q_inflow, dx=dt))
    e_diss = float(np.trapezoid((pc ** 2) / rp + zc * (q_inflow ** 2), dx=dt) if hasattr(np, 'trapezoid') else np.trapz((pc ** 2) / rp + zc * (q_inflow ** 2), dx=dt))
    return abs(w_lv - e_diss)
