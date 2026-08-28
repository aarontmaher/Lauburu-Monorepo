"""
Adversarial Biophysical Stress Testing Suite for Hemodynamic Cloud Server.

Challenger 1: Biophysical Stress Tester
Validates:
1. Extreme Edge Cases (PTT 10ms - 2000ms, HR 20 - 300 bpm, Motion up to 10g, E0 10 kPa - 50 MPa).
2. Conservation of Mass across varying HR, SV, Rp, C.
3. Conservation of Energy in periodic steady states.
4. Strict Monotonicity: d(SBP)/d(PTT) <= 0 and d(SBP)/d(E0) >= 0 (and strict < 0 / > 0 unclamped).
5. Numerical Stability & Floating-Point Integrity: zero NaNs, zero Infs, invariant adherence.
6. Empirical ODE Convergence Orders: Trapezoidal O(dt^2) and RK4 analysis.
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
    calculate_signal_confidence,
    InversionParameters,
    DEFAULT_PARAMS
)


class TestExtremeEdgeCases:
    """Test extreme and boundary conditions on biophysical solvers."""

    @pytest.mark.parametrize("ptt_ms", [10.0, 25.0, 50.0, 100.0, 250.0, 500.0, 1000.0, 1500.0, 2000.0])
    def test_ptt_extremes_10ms_to_2000ms(self, ptt_ms: float):
        """PTT ranging from 10 ms (hyper-rigid/artifact) to 2000 ms (extreme dilation/slow wave)."""
        res = invert_hemodynamic_vector(
            ptt_ms=ptt_ms,
            hr_bpm=72.0,
            rr_ms=833.0,
            delta_t_dia_ms=280.0,
            imu_acc_g=1.0,
            e0_elasticity=400.0
        )
        assert not math.isnan(res.systolic_bp_mmhg)
        assert not math.isnan(res.diastolic_bp_mmhg)
        assert not math.isinf(res.systolic_bp_mmhg)
        assert not math.isinf(res.diastolic_bp_mmhg)
        assert 70.0 <= res.systolic_bp_mmhg <= 240.0
        assert 40.0 <= res.diastolic_bp_mmhg <= 150.0
        assert res.systolic_bp_mmhg >= res.diastolic_bp_mmhg + 15.0 - 1e-5
        assert 0.0 <= res.confidence_score <= 1.0

    @pytest.mark.parametrize("hr_bpm", [20.0, 30.0, 45.0, 70.0, 120.0, 180.0, 220.0, 260.0, 300.0])
    def test_hr_extremes_20_to_300_bpm(self, hr_bpm: float):
        """Heart rate ranging from 20 bpm (severe bradycardia) to 300 bpm (ventricular tachycardia)."""
        res = invert_hemodynamic_vector(
            ptt_ms=220.0,
            hr_bpm=hr_bpm,
            rr_ms=60000.0 / hr_bpm,
            delta_t_dia_ms=max(50.0, (60000.0 / hr_bpm) * 0.4),
            imu_acc_g=1.0,
            e0_elasticity=400.0
        )
        assert not math.isnan(res.systolic_bp_mmhg)
        assert not math.isnan(res.diastolic_bp_mmhg)
        assert 70.0 <= res.systolic_bp_mmhg <= 240.0
        assert 40.0 <= res.diastolic_bp_mmhg <= 150.0
        assert res.systolic_bp_mmhg >= res.diastolic_bp_mmhg + 15.0 - 1e-5
        # For extreme HR (20 or 300 bpm), confidence should be degraded
        if hr_bpm <= 35.0 or hr_bpm >= 220.0:
            assert res.confidence_score <= 0.85

    @pytest.mark.parametrize("imu_acc_g", [0.0, 0.5, 1.0, 2.0, 3.5, 5.0, 8.0, 10.0, 25.0])
    def test_severe_motion_noise_up_to_10g(self, imu_acc_g: float):
        """IMU acceleration noise from 0g (free-fall) up to 10g+ (violent motion artifact)."""
        res = invert_hemodynamic_vector(
            ptt_ms=200.0,
            hr_bpm=140.0,
            rr_ms=428.0,
            delta_t_dia_ms=180.0,
            imu_acc_g=imu_acc_g,
            e0_elasticity=450.0
        )
        assert not math.isnan(res.systolic_bp_mmhg)
        assert not math.isnan(res.diastolic_bp_mmhg)
        assert 70.0 <= res.systolic_bp_mmhg <= 240.0
        assert 40.0 <= res.diastolic_bp_mmhg <= 150.0
        assert res.systolic_bp_mmhg >= res.diastolic_bp_mmhg + 15.0 - 1e-5
        if imu_acc_g >= 3.5:
            assert res.confidence_score <= 0.60

    @pytest.mark.parametrize("e0_kpa", [10.0, 50.0, 100.0, 400.0, 1000.0, 5000.0, 10000.0, 50000.0])
    def test_extreme_arterial_elasticity_10kpa_to_50mpa(self, e0_kpa: float):
        """Elasticity E0 from 10 kPa (extremely floppy/compliant) to 50,000 kPa = 50 MPa (calcified pipe)."""
        res = invert_hemodynamic_vector(
            ptt_ms=220.0,
            hr_bpm=72.0,
            rr_ms=833.0,
            delta_t_dia_ms=280.0,
            imu_acc_g=1.0,
            e0_elasticity=e0_kpa
        )
        assert not math.isnan(res.systolic_bp_mmhg)
        assert not math.isnan(res.diastolic_bp_mmhg)
        assert 70.0 <= res.systolic_bp_mmhg <= 240.0
        assert 40.0 <= res.diastolic_bp_mmhg <= 150.0
        assert res.arterial_compliance_ml_per_mmhg > 0.0
        assert 3.0 <= res.pwv_m_s <= 25.0

    def test_combinatorial_boundary_extremes(self):
        """Test extreme simultaneous multi-variable boundary combinations."""
        # Extreme 1: Min PTT, Max HR, Max Motion, Max Elasticity (Hyper-hypertensive stress)
        res_high = invert_hemodynamic_vector(
            ptt_ms=10.0,
            hr_bpm=300.0,
            rr_ms=200.0,
            delta_t_dia_ms=60.0,
            imu_acc_g=10.0,
            e0_elasticity=50000.0
        )
        assert res_high.systolic_bp_mmhg == 240.0
        assert res_high.diastolic_bp_mmhg <= 150.0
        assert res_high.systolic_bp_mmhg >= res_high.diastolic_bp_mmhg + 15.0

        # Extreme 2: Max PTT, Min HR, 0g Motion, Min Elasticity (Hyper-hypotensive stress)
        res_low = invert_hemodynamic_vector(
            ptt_ms=2000.0,
            hr_bpm=20.0,
            rr_ms=3000.0,
            delta_t_dia_ms=1200.0,
            imu_acc_g=0.0,
            e0_elasticity=10.0
        )
        assert res_low.systolic_bp_mmhg >= 70.0
        assert res_low.diastolic_bp_mmhg == 40.0
        assert res_low.systolic_bp_mmhg >= res_low.diastolic_bp_mmhg + 15.0


class TestConservationOfMass:
    """Rigorous verification of mass conservation over steady periodic cardiac cycles."""

    @pytest.mark.parametrize("hr_bpm", [30.0, 60.0, 75.0, 100.0, 120.0, 150.0, 200.0, 300.0])
    @pytest.mark.parametrize("stroke_volume_ml", [25.0, 70.0, 120.0, 200.0])
    def test_mass_conservation_across_hr_and_sv(self, hr_bpm: float, stroke_volume_ml: float):
        """Verify int(Q dt) == int(Pc / Rp dt) across varying HR and SV on integer-discretized cycles."""
        period = 60.0 / hr_bpm
        n_points_per_cycle = 2000
        dt = period / n_points_per_cycle
        t = np.arange(0.0, 10.0 * period + dt/2, dt)
        
        q_inflow = generate_cardiac_inflow(t, hr_bpm=hr_bpm, stroke_volume_ml=stroke_volume_ml)
        rp = 1.10
        c = 1.20
        zc = 0.05
        
        _, pc = solve_wk3_trapezoidal(q_inflow, dt=dt, rp=rp, c=c, zc=zc, num_warmup_cycles=10)
        
        q_cycle = q_inflow[-(n_points_per_cycle + 1):]
        pc_cycle = pc[-(n_points_per_cycle + 1):]
        
        mass_diff = verify_mass_conservation(q_cycle, pc_cycle, rp, dt)
        inflow_stroke_vol = float(np.trapezoid(q_cycle, dx=dt) if hasattr(np, 'trapezoid') else np.trapz(q_cycle, dx=dt))
        
        rel_mass_error = mass_diff / max(1e-3, inflow_stroke_vol)
        assert rel_mass_error < 1e-4, f"Mass conservation failed: rel_error={rel_mass_error}, diff={mass_diff} mL"

    @pytest.mark.parametrize("rp", [0.4, 0.8, 1.2, 2.0, 3.5])
    @pytest.mark.parametrize("c", [0.4, 0.9, 1.5, 3.0])
    def test_mass_conservation_across_rp_and_c(self, rp: float, c: float):
        """Verify mass conservation across systemic resistance Rp and arterial compliance C."""
        hr_bpm = 75.0
        period = 60.0 / hr_bpm
        n_points_per_cycle = 2000
        dt = period / n_points_per_cycle
        t = np.arange(0.0, 10.0 * period + dt/2, dt)
        
        q_inflow = generate_cardiac_inflow(t, hr_bpm=hr_bpm, stroke_volume_ml=75.0)
        zc = 0.05 * rp
        
        _, pc = solve_wk3_trapezoidal(q_inflow, dt=dt, rp=rp, c=c, zc=zc, num_warmup_cycles=10)
        
        q_cycle = q_inflow[-(n_points_per_cycle + 1):]
        pc_cycle = pc[-(n_points_per_cycle + 1):]
        
        mass_diff = verify_mass_conservation(q_cycle, pc_cycle, rp, dt)
        inflow_stroke_vol = float(np.trapezoid(q_cycle, dx=dt) if hasattr(np, 'trapezoid') else np.trapz(q_cycle, dx=dt))
        rel_mass_error = mass_diff / inflow_stroke_vol
        assert rel_mass_error < 1e-4, f"Mass conservation failed for Rp={rp}, C={c}: diff={mass_diff} mL"

    def test_mass_conservation_rk4_solver(self):
        """Verify mass conservation specifically with WK3 RK4 solver."""
        hr = 80.0
        period = 60.0 / hr
        n_points_per_cycle = 2000
        dt = period / n_points_per_cycle
        t = np.arange(0.0, 10.0 * period + dt/2, dt)
        
        q_inflow = generate_cardiac_inflow(t, hr_bpm=hr, stroke_volume_ml=85.0)
        rp = 1.15
        c = 1.30
        zc = 0.06
        
        _, pc = solve_wk3_rk4(q_inflow, dt=dt, rp=rp, c=c, zc=zc, num_warmup_cycles=10)
        
        q_cycle = q_inflow[-(n_points_per_cycle + 1):]
        pc_cycle = pc[-(n_points_per_cycle + 1):]
        
        mass_diff = verify_mass_conservation(q_cycle, pc_cycle, rp, dt)
        assert mass_diff < 1e-4


class TestConservationOfEnergy:
    """Rigorous verification of energy conservation in periodic steady states."""

    @pytest.mark.parametrize("hr_bpm,sv_ml,rp,c,zc", [
        (60.0, 80.0, 1.0, 1.4, 0.05),     # Normotensive rest
        (150.0, 110.0, 0.6, 1.2, 0.04),   # Heavy exercise
        (50.0, 95.0, 1.8, 0.8, 0.09),     # Hypertensive bradycardia / high resistance
        (100.0, 50.0, 0.7, 2.0, 0.03),    # High compliance / vasodilation
        (85.0, 75.0, 2.5, 0.5, 0.12),     # Severe arterial stiffness
    ])
    def test_energy_conservation_across_regimes(
        self, hr_bpm: float, sv_ml: float, rp: float, c: float, zc: float
    ):
        """Verify int(P*Q dt) == int(Pc^2/Rp + Zc*Q^2 dt) across multiple cardiovascular regimes."""
        period = 60.0 / hr_bpm
        dt = 0.0002
        t = np.arange(0.0, 8.0 * period + dt, dt)
        
        q_inflow = generate_cardiac_inflow(t, hr_bpm=hr_bpm, stroke_volume_ml=sv_ml)
        p_total, pc = solve_wk3_trapezoidal(q_inflow, dt=dt, rp=rp, c=c, zc=zc, num_warmup_cycles=8)
        
        n_cycle = int(round(period / dt))
        p_cycle = p_total[-(n_cycle + 1):]
        pc_cycle = pc[-(n_cycle + 1):]
        q_cycle = q_inflow[-(n_cycle + 1):]
        
        energy_diff = verify_energy_dissipation(p_cycle, pc_cycle, q_cycle, rp, zc, dt)
        total_work = float(np.trapezoid(p_cycle * q_cycle, dx=dt) if hasattr(np, 'trapezoid') else np.trapz(p_cycle * q_cycle, dx=dt))
        
        rel_energy_error = energy_diff / total_work
        assert rel_energy_error < 1e-3, f"Energy conservation error {rel_energy_error:.6e} exceeds 0.1% threshold"


class TestMonotonicityAndDerivatives:
    """Verify strict mathematical monotonicity and derivative signs."""

    def test_strict_negative_ptt_derivative_continuous(self):
        """Verify continuous analytical Moens-Korteweg equation has strictly negative derivative d(SBP)/d(PTT) < 0."""
        ptt_values = np.linspace(0.08, 0.60, 200)
        e_ratio = 1.0
        hr_bpm = 75.0
        
        sbp_vals = []
        dbp_vals = []
        for ptt in ptt_values:
            sbp, dbp = logarithmic_moens_korteweg_bp(ptt_sec=ptt, e_ratio=e_ratio, hr_bpm=hr_bpm)
            sbp_vals.append(sbp)
            dbp_vals.append(dbp)
            
        sbp_vals = np.array(sbp_vals)
        dbp_vals = np.array(dbp_vals)
        
        # Strict negativity on continuous derivative
        assert np.all(np.diff(sbp_vals) < 0.0)
        assert np.all(np.diff(dbp_vals) < 0.0)

    def test_strict_positive_elasticity_derivative_continuous(self):
        """Verify continuous analytical Moens-Korteweg equation has strictly positive derivative d(SBP)/d(E0) > 0."""
        e_ratios = np.linspace(0.2, 5.0, 200)
        ptt_sec = 0.220
        hr_bpm = 75.0
        
        sbp_vals = []
        dbp_vals = []
        for e_rat in e_ratios:
            sbp, dbp = logarithmic_moens_korteweg_bp(ptt_sec=ptt_sec, e_ratio=e_rat, hr_bpm=hr_bpm)
            sbp_vals.append(sbp)
            dbp_vals.append(dbp)
            
        sbp_vals = np.array(sbp_vals)
        dbp_vals = np.array(dbp_vals)
        
        # Strict positivity on continuous derivative
        assert np.all(np.diff(sbp_vals) > 0.0)
        assert np.all(np.diff(dbp_vals) > 0.0)

    def test_monotonicity_clamped_inversion_engine(self):
        """Verify the full 6D Inversion Engine output is monotonically non-increasing for PTT and non-decreasing for E0."""
        # PTT monotonic non-increasing
        ptt_dense = np.linspace(100.0, 500.0, 100)
        sbp_ptt = [invert_hemodynamic_vector(ptt_ms=p, hr_bpm=75.0).systolic_bp_mmhg for p in ptt_dense]
        assert np.all(np.diff(sbp_ptt) <= 0.0)

        # E0 monotonic non-decreasing
        e0_dense = np.linspace(100.0, 1500.0, 100)
        sbp_e0 = [invert_hemodynamic_vector(ptt_ms=220.0, hr_bpm=75.0, e0_elasticity=e).systolic_bp_mmhg for e in e0_dense]
        assert np.all(np.diff(sbp_e0) >= 0.0)

    def test_2d_grid_monotonicity(self):
        """2D Grid monotonicity: SBP(PTT_1, E0) >= SBP(PTT_2, E0) for PTT_1 < PTT_2, and SBP(PTT, E0_1) <= SBP(PTT, E0_2) for E0_1 < E0_2."""
        ptt_grid = np.linspace(50.0, 800.0, 40)
        e0_grid = np.linspace(50.0, 2000.0, 40)
        
        sbp_grid = np.zeros((len(ptt_grid), len(e0_grid)))
        
        for i, ptt in enumerate(ptt_grid):
            for j, e0 in enumerate(e0_grid):
                res = invert_hemodynamic_vector(ptt_ms=ptt, hr_bpm=70.0, e0_elasticity=e0)
                sbp_grid[i, j] = res.systolic_bp_mmhg
                
        # Check monotonic down columns (PTT increasing -> SBP non-increasing)
        for j in range(len(e0_grid)):
            assert np.all(np.diff(sbp_grid[:, j]) <= 1e-5)
            
        # Check monotonic across rows (E0 increasing -> SBP non-decreasing)
        for i in range(len(ptt_grid)):
            assert np.all(np.diff(sbp_grid[i, :]) >= -1e-5)


class TestNumericalStabilityAndInvariants:
    """Verify zero NaNs, zero Infs, and invariant compliance across extensive parameter spaces."""

    def test_high_coverage_grid_stability(self):
        """Test exhaustive parameter grid with zero exceptions or NaNs."""
        ptt_vals = [5.0, 10.0, 20.0, 50.0, 100.0, 200.0, 500.0, 1000.0, 2000.0, 5000.0]
        hr_vals = [10.0, 20.0, 30.0, 60.0, 120.0, 180.0, 240.0, 300.0, 400.0]
        imu_vals = [0.0, 0.5, 1.0, 2.5, 5.0, 10.0, 50.0, 100.0]
        e0_vals = [5.0, 10.0, 50.0, 100.0, 400.0, 2000.0, 10000.0, 50000.0]
        
        count = 0
        for ptt in ptt_vals:
            for hr in hr_vals:
                for imu in imu_vals:
                    for e0 in e0_vals:
                        res = invert_hemodynamic_vector(
                            ptt_ms=ptt,
                            hr_bpm=hr,
                            rr_ms=800.0,
                            delta_t_dia_ms=280.0,
                            imu_acc_g=imu,
                            e0_elasticity=e0
                        )
                        count += 1
                        assert not math.isnan(res.systolic_bp_mmhg)
                        assert not math.isnan(res.diastolic_bp_mmhg)
                        assert not math.isnan(res.mean_arterial_pressure_mmhg)
                        assert not math.isnan(res.pulse_pressure_mmhg)
                        assert not math.isnan(res.arterial_compliance_ml_per_mmhg)
                        assert not math.isnan(res.vascular_resistance_mmhg_s_per_ml)
                        assert not math.isnan(res.pwv_m_s)
                        assert not math.isnan(res.confidence_score)
                        
                        assert 70.0 <= res.systolic_bp_mmhg <= 240.0
                        assert 40.0 <= res.diastolic_bp_mmhg <= 150.0
                        assert res.systolic_bp_mmhg >= res.diastolic_bp_mmhg + 15.0 - 1e-4
                        assert pytest.approx(res.mean_arterial_pressure_mmhg, abs=0.2) == (1.0/3.0)*res.systolic_bp_mmhg + (2.0/3.0)*res.diastolic_bp_mmhg
                        assert pytest.approx(res.pulse_pressure_mmhg, abs=0.2) == res.systolic_bp_mmhg - res.diastolic_bp_mmhg
                        assert 0.0 <= res.confidence_score <= 1.0
        assert count == 10 * 9 * 8 * 8

    def test_50k_log_uniform_monte_carlo_stress(self):
        """Stress test with 50,000 log-uniform random samples spanning extreme scales."""
        np.random.seed(1337)
        n_samples = 50000
        
        ptt_samples = 10.0 ** np.random.uniform(np.log10(10.0), np.log10(3000.0), n_samples)
        hr_samples = 10.0 ** np.random.uniform(np.log10(15.0), np.log10(350.0), n_samples)
        rr_samples = 10.0 ** np.random.uniform(np.log10(100.0), np.log10(4000.0), n_samples)
        delta_dia_samples = 10.0 ** np.random.uniform(np.log10(20.0), np.log10(2000.0), n_samples)
        imu_samples = np.random.uniform(0.0, 20.0, n_samples)
        e0_samples = 10.0 ** np.random.uniform(np.log10(5.0), np.log10(60000.0), n_samples)
        
        for i in range(n_samples):
            res = invert_hemodynamic_vector(
                ptt_ms=float(ptt_samples[i]),
                hr_bpm=float(hr_samples[i]),
                rr_ms=float(rr_samples[i]),
                delta_t_dia_ms=float(delta_dia_samples[i]),
                imu_acc_g=float(imu_samples[i]),
                e0_elasticity=float(e0_samples[i])
            )
            assert not math.isnan(res.systolic_bp_mmhg)
            assert not math.isnan(res.diastolic_bp_mmhg)
            assert 70.0 <= res.systolic_bp_mmhg <= 240.0
            assert 40.0 <= res.diastolic_bp_mmhg <= 150.0
            assert res.systolic_bp_mmhg >= res.diastolic_bp_mmhg + 15.0 - 1e-4

    def test_low_level_physics_error_handling(self):
        """Ensure invalid/non-physical inputs raise descriptive ValueErrors rather than returning NaN."""
        with pytest.raises(ValueError):
            moens_korteweg_wave_speed(-100.0, 0.0015, 0.024)
        with pytest.raises(ValueError):
            moens_korteweg_wave_speed(400000.0, -0.0015, 0.024)
        with pytest.raises(ValueError):
            hughes_strain_stiffening(-100.0, 100.0)
        with pytest.raises(ValueError):
            pressure_dependent_pwv(-5.0, 100.0)
        with pytest.raises(ValueError):
            moens_korteweg_pressure_inversion(-0.2, 0.85, 5.0)
        with pytest.raises(ValueError):
            logarithmic_moens_korteweg_bp(-0.2, 1.0, 75.0)
        with pytest.raises(ValueError):
            bramwell_hill_wave_speed(-0.001)
        with pytest.raises(ValueError):
            volumetric_distensibility(-5.0)
        with pytest.raises(ValueError):
            cross_sectional_compliance(5.0, diameter_m=-0.02)
        with pytest.raises(ValueError):
            total_arterial_compliance(5.0, arterial_volume_m3=-0.001)
        with pytest.raises(ValueError):
            diastolic_decay_time_constant(-0.2, 80.0, 70.0)


class TestOdeConvergenceOrders:
    """Rigorous empirical verification of ODE solver convergence rates."""

    def test_trapezoidal_convergence_rate(self):
        """
        Trapezoidal Crank-Nicolson method is empirically O(dt^2) with convergence order ~ 2.0.
        """
        rp = 1.10
        c = 1.25
        tau = rp * c
        omega = 2.0 * np.pi / 0.8  # 75 bpm
        q0 = 85.0
        
        inv_tau = 1.0 / tau
        denom = (inv_tau ** 2) + (omega ** 2)
        coeff_a = (q0 / c) * inv_tau / denom
        coeff_b = -(q0 / c) * omega / denom
        
        def p_exact(t: float) -> float:
            return coeff_a * math.sin(omega * t) + coeff_b * math.cos(omega * t)
        
        p0 = p_exact(0.0)
        dt_list = [0.08, 0.04, 0.02, 0.01, 0.005]
        t_final = 0.8
        
        trap_errors = []
        for dt in dt_list:
            t_arr = np.arange(0.0, t_final + dt, dt)
            q_arr = q0 * np.sin(omega * t_arr)
            p_sim = solve_wk2_trapezoidal(q_arr, dt=dt, rp=rp, c=c, p0=p0)
            exact_arr = np.array([p_exact(ti) for ti in t_arr])
            l2_error = float(np.sqrt(np.mean((p_sim - exact_arr) ** 2)))
            trap_errors.append(l2_error)
            
        trap_orders = [
            math.log2(trap_errors[i] / trap_errors[i + 1])
            for i in range(len(trap_errors) - 1)
        ]
        # Verify Trapezoidal empirical order is ~2.0 (1.90 - 2.10)
        for order in trap_orders:
            assert 1.90 <= order <= 2.10, f"Trapezoidal order {order} deviated from 2.0"

    def test_euler_convergence_rates(self):
        """Explicit and Implicit Euler solvers are empirically O(dt) with convergence order ~ 1.0."""
        rp = 1.10
        c = 1.25
        tau = rp * c
        omega = 2.0 * np.pi / 0.8
        q0 = 85.0
        
        inv_tau = 1.0 / tau
        denom = (inv_tau ** 2) + (omega ** 2)
        coeff_a = (q0 / c) * inv_tau / denom
        coeff_b = -(q0 / c) * omega / denom
        
        def p_exact(t: float) -> float:
            return coeff_a * math.sin(omega * t) + coeff_b * math.cos(omega * t)
        
        p0 = p_exact(0.0)
        dt_list = [0.08, 0.04, 0.02, 0.01, 0.005]
        t_final = 0.8
        
        euler_errors = []
        for dt in dt_list:
            t_arr = np.arange(0.0, t_final + dt, dt)
            q_arr = q0 * np.sin(omega * t_arr)
            p_sim = solve_wk2_explicit_euler(q_arr, dt=dt, rp=rp, c=c, p0=p0)
            exact_arr = np.array([p_exact(ti) for ti in t_arr])
            l2_error = float(np.sqrt(np.mean((p_sim - exact_arr) ** 2)))
            euler_errors.append(l2_error)
            
        euler_orders = [
            math.log2(euler_errors[i] / euler_errors[i + 1])
            for i in range(len(euler_errors) - 1)
        ]
        for order in euler_orders:
            assert 0.90 <= order <= 1.15, f"Euler order {order} deviated from 1.0"

    def test_rk4_exact_continuous_fourth_order(self):
        """
        Demonstrate that the classical 4th-order Runge-Kutta integration scheme achieves
        O(dt^4) convergence when evaluated against exact continuous source inflow.
        """
        rp = 1.10
        c = 1.25
        tau = rp * c
        omega = 2.0 * np.pi / 0.8
        q0 = 85.0

        inv_tau = 1.0 / tau
        denom = (inv_tau ** 2) + (omega ** 2)
        coeff_a = (q0 / c) * inv_tau / denom
        coeff_b = -(q0 / c) * omega / denom

        def p_exact(t: float) -> float:
            return coeff_a * math.sin(omega * t) + coeff_b * math.cos(omega * t)

        def rk4_step_continuous(p_val: float, t_val: float, dt_val: float) -> float:
            def f(time_pt: float, val: float) -> float:
                q_val = q0 * math.sin(omega * time_pt)
                return (q_val / c) - (val / tau)

            k1 = f(t_val, p_val)
            k2 = f(t_val + 0.5 * dt_val, p_val + 0.5 * dt_val * k1)
            k3 = f(t_val + 0.5 * dt_val, p_val + 0.5 * dt_val * k2)
            k4 = f(t_val + dt_val, p_val + dt_val * k3)
            return p_val + (dt_val / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)

        dt_list = [0.08, 0.04, 0.02, 0.01, 0.005]
        t_final = 0.8
        errors = []
        for dt in dt_list:
            p_val = p_exact(0.0)
            for t_step in np.arange(0.0, t_final, dt):
                p_val = rk4_step_continuous(p_val, float(t_step), dt)
            err = abs(p_val - p_exact(t_final))
            errors.append(err)

        orders = [
            math.log2(errors[i] / max(1e-15, errors[i + 1]))
            for i in range(len(errors) - 1)
        ]
        for order in orders:
            assert 3.80 <= order <= 4.20, f"RK4 order {order} deviated from 4.0"

    def test_rk4_discrete_linear_midpoint_interpolation_bottleneck(self):
        """
        Adversarial Challenge Finding:
        Empirically demonstrate that solve_wk2_rk4 with discrete linear interpolation
        q_mid = 0.5*(qk + qk1) is limited to O(dt^2) convergence instead of O(dt^4).
        """
        rp = 1.10
        c = 1.25
        tau = rp * c
        omega = 2.0 * np.pi / 0.8
        q0 = 85.0
        
        inv_tau = 1.0 / tau
        denom = (inv_tau ** 2) + (omega ** 2)
        coeff_a = (q0 / c) * inv_tau / denom
        coeff_b = -(q0 / c) * omega / denom
        
        def p_exact(t: float) -> float:
            return coeff_a * math.sin(omega * t) + coeff_b * math.cos(omega * t)
        
        p0 = p_exact(0.0)
        dt_list = [0.04, 0.02, 0.01, 0.005]
        t_final = 0.8
        
        rk4_discrete_errors = []
        for dt in dt_list:
            t_arr = np.arange(0.0, t_final + dt/2, dt)
            q_arr = q0 * np.sin(omega * t_arr)
            p_sim = solve_wk2_rk4(q_arr, dt=dt, rp=rp, c=c, p0=p0)
            err = abs(p_sim[-1] - p_exact(t_final))
            rk4_discrete_errors.append(err)
            
        discrete_orders = [
            math.log2(rk4_discrete_errors[i] / rk4_discrete_errors[i + 1])
            for i in range(len(rk4_discrete_errors) - 1)
        ]
        # Empirically confirms the discrete linear interpolation forces ~2.0 order
        for order in discrete_orders:
            assert 1.95 <= order <= 2.05, f"Discrete RK4 order {order} unexpectedly differed from 2.0"
