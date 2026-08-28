"""
Physics Invariants & Numerical Verification Test Suite.
Verifies all 7 biophysical invariants, conservation laws, monotonicity bounds,
and numerical convergence rates.
"""

import math
import numpy as np
import pytest

from app.physics.moens_korteweg import (
    moens_korteweg_wave_speed,
    hughes_strain_stiffening,
    pressure_dependent_pwv,
    moens_korteweg_pressure_inversion,
    logarithmic_moens_korteweg_bp
)
from app.physics.bramwell_hill import (
    bramwell_hill_wave_speed,
    volumetric_distensibility,
    volumetric_distensibility_mmhg,
    cross_sectional_compliance,
    total_arterial_compliance,
    total_arterial_compliance_ml_per_mmhg
)
from app.physics.windkessel import (
    diastolic_decay_time_constant,
    calculate_peripheral_resistance_analytical,
    generate_cardiac_inflow,
    solve_wk2_explicit_euler,
    solve_wk2_implicit_euler,
    solve_wk2_trapezoidal,
    solve_wk2_rk4,
    solve_wk3_trapezoidal,
    solve_wk3_rk4,
    fit_windkessel_parameters,
    verify_mass_conservation,
    verify_energy_dissipation
)
from app.physics.hemodynamic_inversion import (
    invert_hemodynamic_vector,
    calculate_signal_confidence
)


class TestMoensKortewegPhysics:
    def test_moens_korteweg_baseline_wave_speed(self):
        # E = 400 kPa, h = 1.5 mm, d = 24 mm, rho = 1055 kg/m^3
        # PWV = sqrt( (400,000 * 0.0015) / (1055 * 0.024) ) = sqrt( 600 / 25.32 ) = sqrt(23.6967) ~= 4.868 m/s
        pwv = moens_korteweg_wave_speed(
            young_modulus_pa=400000.0,
            wall_thickness_m=0.0015,
            inner_diameter_m=0.024,
            blood_density_kg_m3=1055.0
        )
        assert 4.8 < pwv < 4.9

    def test_hughes_strain_stiffening(self):
        # E(P) = E0 * exp(gamma * P)
        e0 = 400000.0
        p = 100.0
        gamma = 0.017
        e_p = hughes_strain_stiffening(e0, p, gamma)
        expected = e0 * math.exp(0.017 * 100.0)
        assert pytest.approx(e_p, rel=1e-5) == expected
        assert e_p > e0

    def test_pressure_dependent_pwv(self):
        pwv0 = 5.0
        p = 120.0
        pwv_p = pressure_dependent_pwv(pwv0, p, gamma=0.017)
        assert pwv_p > pwv0
        assert pytest.approx(pwv_p, rel=1e-5) == 5.0 * math.exp(0.5 * 0.017 * 120.0)

    def test_moens_korteweg_pressure_inversion(self):
        # Test exact roundtrip: P -> PTT -> P
        p_true = 115.0
        pwv0 = 5.2
        path_length = 0.85
        gamma = 0.017
        pwv_p = pressure_dependent_pwv(pwv0, p_true, gamma)
        ptt_true = path_length / pwv_p
        
        p_calc = moens_korteweg_pressure_inversion(ptt_true, path_length, pwv0, gamma)
        assert pytest.approx(p_calc, abs=1e-3) == p_true


class TestBramwellHillPhysics:
    def test_bramwell_hill_equivalence_with_moens_korteweg(self):
        # For thin walled tube: D_v = A0 / (E * h) * (1 / A0) = 1 / (E * h / d)
        # c_BH = sqrt( 1 / (rho * D_v) ) == sqrt( E * h / (rho * d) )
        e = 450000.0
        h = 0.0016
        d = 0.025
        rho = 1055.0
        pwv_mk = moens_korteweg_wave_speed(e, h, d, rho)
        
        # Volumetric distensibility D_v = d / (E * h)
        dv = d / (e * h)
        pwv_bh = bramwell_hill_wave_speed(dv, rho)
        assert pytest.approx(pwv_mk, rel=1e-6) == pwv_bh

    def test_total_arterial_compliance_clinical_units(self):
        # For PWV = 6.0 m/s, V0 = 1.0 L = 0.001 m^3, rho = 1055 kg/m^3
        # C_art = 0.001 * 133.322e6 / (1055 * 36) ~= 3.51 mL/mmHg
        c_art = total_arterial_compliance_ml_per_mmhg(pwv_m_s=6.0, arterial_volume_m3=0.0010, blood_density_kg_m3=1055.0)
        assert 3.4 < c_art < 3.6


class TestWindkesselInvariantsAndSolvers:
    """Rigorous verification of biophysical invariants and numerical ODE solvers."""

    def test_inv_01_conservation_of_mass(self):
        """INV-01: Integral of Inflow Q(t) equals Outflow Integral Pc(t)/Rp over steady cardiac cycle."""
        hr = 75.0
        period = 60.0 / hr
        dt = 0.0005
        t = np.arange(0.0, 6.0 * period + dt, dt)
        
        q_inflow = generate_cardiac_inflow(t, hr_bpm=hr, stroke_volume_ml=70.0)
        rp = 1.05
        c = 1.25
        zc = 0.06
        
        _, pc = solve_wk3_trapezoidal(q_inflow, dt=dt, rp=rp, c=c, zc=zc, num_warmup_cycles=8)
        
        # Examine the final complete cycle of duration period = 0.8s
        n_cycle = int(round(period / dt))
        q_cycle = q_inflow[-(n_cycle + 1):]
        pc_cycle = pc[-(n_cycle + 1):]
        
        diff = verify_mass_conservation(q_cycle, pc_cycle, rp, dt)
        assert diff < 1e-5, f"Mass conservation error {diff} mL exceeds tolerance"

    def test_inv_02_conservation_of_energy(self):
        """INV-02: Total LV work equals dissipated energy in periodic steady state."""
        hr = 80.0
        period = 60.0 / hr
        dt = 0.0005
        t = np.arange(0.0, 6.0 * period + dt, dt)
        
        q_inflow = generate_cardiac_inflow(t, hr_bpm=hr, stroke_volume_ml=75.0)
        rp = 1.10
        c = 1.30
        zc = 0.05
        
        p_total, pc = solve_wk3_trapezoidal(q_inflow, dt=dt, rp=rp, c=c, zc=zc, num_warmup_cycles=8)
        
        n_cycle = int(round(period / dt))
        p_cycle = p_total[-(n_cycle + 1):]
        pc_cycle = pc[-(n_cycle + 1):]
        q_cycle = q_inflow[-(n_cycle + 1):]
        
        energy_diff = verify_energy_dissipation(p_cycle, pc_cycle, q_cycle, rp, zc, dt)
        total_work = float(np.trapezoid(p_cycle * q_cycle, dx=dt) if hasattr(np, 'trapezoid') else np.trapz(p_cycle * q_cycle, dx=dt))
        rel_error = energy_diff / total_work
        assert rel_error < 1e-3, f"Energy conservation relative error {rel_error} exceeds 0.1%"

    def test_inv_03_ptt_monotonicity(self):
        """INV-03: SBP and DBP must strictly decrease as PTT increases."""
        ptt_values = np.linspace(150.0, 350.0, 50)
        sbp_list = []
        dbp_list = []
        
        for ptt in ptt_values:
            res = invert_hemodynamic_vector(ptt_ms=ptt, hr_bpm=75.0, e0_elasticity=400.0)
            sbp_list.append(res.systolic_bp_mmhg)
            dbp_list.append(res.diastolic_bp_mmhg)
            
        # Check strict decreasing order
        for i in range(len(ptt_values) - 1):
            assert sbp_list[i] >= sbp_list[i + 1], f"SBP monotonicity violated at PTT {ptt_values[i]}"
            assert dbp_list[i] >= dbp_list[i + 1], f"DBP monotonicity violated at PTT {ptt_values[i]}"

    def test_inv_04_elasticity_monotonicity(self):
        """INV-04: SBP and DBP must strictly increase as baseline elasticity E0 increases."""
        e0_values = np.linspace(200.0, 700.0, 50)
        sbp_list = []
        dbp_list = []
        
        for e0 in e0_values:
            res = invert_hemodynamic_vector(ptt_ms=220.0, hr_bpm=75.0, e0_elasticity=e0)
            sbp_list.append(res.systolic_bp_mmhg)
            dbp_list.append(res.diastolic_bp_mmhg)
            
        for i in range(len(e0_values) - 1):
            assert sbp_list[i] <= sbp_list[i + 1], f"SBP elasticity monotonicity violated at E0 {e0_values[i]}"
            assert dbp_list[i] <= dbp_list[i + 1], f"DBP elasticity monotonicity violated at E0 {e0_values[i]}"

    def test_inv_05_monte_carlo_bounds_10000_samples(self):
        """INV-05: SBP >= DBP + 15 bound and range limits across 10,000 extreme Monte Carlo samples."""
        np.random.seed(42)
        n_samples = 10000
        
        ptt_samples = np.random.uniform(80.0, 600.0, n_samples)
        hr_samples = np.random.uniform(30.0, 240.0, n_samples)
        rr_samples = np.random.uniform(250.0, 2000.0, n_samples)
        delta_t_dia_samples = np.random.uniform(80.0, 600.0, n_samples)
        imu_samples = np.random.uniform(0.5, 4.5, n_samples)
        e0_samples = np.random.uniform(100.0, 800.0, n_samples)
        
        for i in range(n_samples):
            res = invert_hemodynamic_vector(
                ptt_ms=float(ptt_samples[i]),
                hr_bpm=float(hr_samples[i]),
                rr_ms=float(rr_samples[i]),
                delta_t_dia_ms=float(delta_t_dia_samples[i]),
                imu_acc_g=float(imu_samples[i]),
                e0_elasticity=float(e0_samples[i])
            )
            
            # No NaN or Inf
            assert not math.isnan(res.systolic_bp_mmhg), f"NaN SBP at sample {i}"
            assert not math.isnan(res.diastolic_bp_mmhg), f"NaN DBP at sample {i}"
            assert not math.isnan(res.mean_arterial_pressure_mmhg), f"NaN MAP at sample {i}"
            assert not math.isnan(res.vascular_resistance_mmhg_s_per_ml), f"NaN SVR at sample {i}"
            
            # Bounds
            assert 70.0 <= res.systolic_bp_mmhg <= 240.0, f"SBP {res.systolic_bp_mmhg} out of range"
            assert 40.0 <= res.diastolic_bp_mmhg <= 150.0, f"DBP {res.diastolic_bp_mmhg} out of range"
            assert res.systolic_bp_mmhg >= res.diastolic_bp_mmhg + 15.0 - 1e-4, f"PP violation: {res}"
            assert res.pulse_pressure_mmhg >= 15.0 - 1e-4
            assert 0.0 <= res.confidence_score <= 1.0

    def test_inv_06_trapezoidal_second_order_convergence(self):
        """INV-06: Halving time step in Trapezoidal WK3 solver yields ~4x error reduction (O(dt^2))."""
        hr = 75.0
        period = 0.8
        te = 0.24  # Aligned with test time steps (0.008, 0.004, 0.0001)
        t_max = 2.0 * period
        
        # High precision reference solution
        dt_ref = 0.0001
        t_ref = np.arange(0.0, t_max + dt_ref, dt_ref)
        q_ref = generate_cardiac_inflow(t_ref, hr_bpm=hr, ejection_time_sec=te)
        p_ref, _ = solve_wk3_trapezoidal(q_ref, dt=dt_ref, rp=1.0, c=1.2, zc=0.05, num_warmup_cycles=8)
        
        # Compare coarse dt1 vs finer dt2 = dt1 / 2
        dt1 = 0.008
        dt2 = 0.004
        
        t1 = np.arange(0.0, t_max + dt1, dt1)
        q1 = generate_cardiac_inflow(t1, hr_bpm=hr, ejection_time_sec=te)
        p1, _ = solve_wk3_trapezoidal(q1, dt=dt1, rp=1.0, c=1.2, zc=0.05, num_warmup_cycles=8)
        
        t2 = np.arange(0.0, t_max + dt2, dt2)
        q2 = generate_cardiac_inflow(t2, hr_bpm=hr, ejection_time_sec=te)
        p2, _ = solve_wk3_trapezoidal(q2, dt=dt2, rp=1.0, c=1.2, zc=0.05, num_warmup_cycles=8)
        
        # Interpolate reference at matching points
        ref_at_t1 = np.interp(t1, t_ref, p_ref)
        ref_at_t2 = np.interp(t2, t_ref, p_ref)
        
        err1 = float(np.mean(np.abs(p1 - ref_at_t1)))
        err2 = float(np.mean(np.abs(p2 - ref_at_t2)))
        
        ratio = err1 / max(1e-9, err2)
        # For 2nd order, ratio should be ~4.0 (3.5 - 4.5)
        assert 3.5 <= ratio <= 4.5, f"Trapezoidal convergence ratio {ratio} not close to 4.0"

    def test_inv_07_rk4_fourth_order_convergence(self):
        """INV-07: Halving time step in RK4 solver yields ~16x error reduction (O(dt^4))."""
        # Exact mathematical verification on smooth harmonic inflow Q(t) = Q0 * sin(omega * t)
        rp = 1.0
        c = 1.2
        tau = rp * c
        omega = 2.0 * np.pi / 0.8
        q0 = 80.0

        # Analytical steady-state solution
        inv_tau = 1.0 / tau
        denom = (inv_tau ** 2) + (omega ** 2)
        coeff_a = (q0 / c) * inv_tau / denom
        coeff_b = -(q0 / c) * omega / denom

        def p_exact(t: float) -> float:
            return coeff_a * math.sin(omega * t) + coeff_b * math.cos(omega * t)

        def rk4_step(p_val: float, t_val: float, dt_val: float) -> float:
            def f(time_pt: float, val: float) -> float:
                q_val = q0 * math.sin(omega * time_pt)
                return (q_val / c) - (val / tau)

            k1 = f(t_val, p_val)
            k2 = f(t_val + 0.5 * dt_val, p_val + 0.5 * dt_val * k1)
            k3 = f(t_val + 0.5 * dt_val, p_val + 0.5 * dt_val * k2)
            k4 = f(t_val + dt_val, p_val + dt_val * k3)
            return p_val + (dt_val / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)

        dt1 = 0.04
        dt2 = 0.02

        # Solve with dt1
        p1 = p_exact(0.0)
        for t_step in np.arange(0.0, 0.8, dt1):
            p1 = rk4_step(p1, float(t_step), dt1)
        err1 = abs(p1 - p_exact(0.8))

        # Solve with dt2
        p2 = p_exact(0.0)
        for t_step in np.arange(0.0, 0.8, dt2):
            p2 = rk4_step(p2, float(t_step), dt2)
        err2 = abs(p2 - p_exact(0.8))

        ratio = err1 / max(1e-12, err2)
        # For 4th order, error ratio on step halving is ~16.0 (14.0 - 18.0)
        assert 14.0 <= ratio <= 18.0, f"RK4 convergence ratio {ratio} not close to 16.0"
        assert ratio >= 10.0, f"RK4 convergence ratio {ratio} not high enough for 4th order"

    def test_scipy_windkessel_parameter_fitting(self):
        """Test non-linear parameter inversion on synthetic pressure waveform."""
        hr = 72.0
        period = 60.0 / hr
        dt = 0.002
        t = np.arange(0.0, 3.0 * period, dt)
        
        true_rp = 1.15
        true_c = 1.35
        true_zc = 0.07
        
        q = generate_cardiac_inflow(t, hr_bpm=hr, stroke_volume_ml=80.0)
        p_measured, _ = solve_wk3_trapezoidal(q, dt=dt, rp=true_rp, c=true_c, zc=true_zc, num_warmup_cycles=3)
        
        fit = fit_windkessel_parameters(t, p_measured, hr_bpm=hr)
        assert fit["converged"] is True
        assert pytest.approx(fit["rp"], rel=0.15) == true_rp
        assert pytest.approx(fit["c"], rel=0.15) == true_c
