"""
Comprehensive Empirical Stress-Testing Harness for LAUBURU_APP_ECOSYSTEM.md
"""

import math
import numpy as np

def run_tests():
    results = {}
    
    # =========================================================================
    # Test 1: Kamath et al. (2004) 20% RR Artifact Filter Stress Test
    # =========================================================================
    print("=== TEST 1: Kamath 20% RR Artifact Filter ===")
    def kamath_filter(rr_series):
        valid_rr = []
        rejected = []
        for i, rr in enumerate(rr_series):
            if i == 0:
                if rr > 0:
                    valid_rr.append(rr)
                else:
                    rejected.append((i, rr, "Zero/negative initial RR"))
                continue
            prev = valid_rr[-1] if valid_rr else None
            if prev is None or prev == 0:
                rejected.append((i, rr, "No valid previous RR / Prev is 0"))
                continue
            dev = abs(rr - prev) / prev
            if dev <= 0.20:
                valid_rr.append(rr)
            else:
                rejected.append((i, rr, f"Deviation {dev*100:.2f}% > 20%"))
        return valid_rr, rejected

    # Scenario 1A: Normal rhythm with ectopic beat
    rr_normal_ectopic = [800, 810, 790, 805, 450, 800, 810] # 450 is premature beat (dev = 44%)
    valid, rej = kamath_filter(rr_normal_ectopic)
    print(f"Normal + Ectopic: In={len(rr_normal_ectopic)}, Valid={len(valid)}, Rej={len(rej)}")
    
    # Scenario 1B: Sudden physiological sprint acceleration (e.g. Zone 2 to VO2 max: 120bpm -> 180bpm, RR: 500ms -> 333ms, dev = 33.4%)
    rr_sprint = [500, 333, 330, 332, 330]
    valid_sprint, rej_sprint = kamath_filter(rr_sprint)
    print(f"Sprint Step: In={len(rr_sprint)}, Valid={len(valid_sprint)}, Rej={len(rej_sprint)}")
    # If the second beat is rejected, the third beat (330) is compared against 500 again (dev 34%), also rejected!
    # This leads to cascade failure where authentic rapid rhythm is permanently locked out!
    print(f"Sprint Rejection Cascade: {rej_sprint}")
    
    # Scenario 1C: Zero RR interval
    valid_zero, rej_zero = kamath_filter([800, 0, 800])
    print(f"Zero RR handling: {rej_zero}")

    # =========================================================================
    # Test 2: DFA-alpha1 Rolling Window & LT1/LT2 Threshold Discontinuity
    # =========================================================================
    print("\n=== TEST 2: DFA-alpha1 & LUDS S_dfa Discontinuity ===")
    def compute_s_dfa(alpha1):
        if alpha1 >= 0.75:
            return 100.0
        elif 0.50 <= alpha1 < 0.75:
            return 70.0
        else:
            return 30.0

    # Test step discontinuity at boundary 0.75
    alpha_below = 0.749999
    alpha_above = 0.750000
    s_below = compute_s_dfa(alpha_below)
    s_above = compute_s_dfa(alpha_above)
    delta_s = s_above - s_below
    luds_impact = 0.35 * delta_s
    print(f"DFA LT1 Boundary (0.75): alpha={alpha_below:.6f} -> S_dfa={s_below}, alpha={alpha_above:.6f} -> S_dfa={s_above}")
    print(f"Discontinuous Jump in S_dfa: {delta_s} points -> LUDS Score Swing: {luds_impact:.2f} points")

    # Test step discontinuity at boundary 0.50
    alpha_below_lt2 = 0.499999
    alpha_above_lt2 = 0.500000
    s_below_lt2 = compute_s_dfa(alpha_below_lt2)
    s_above_lt2 = compute_s_dfa(alpha_above_lt2)
    delta_s_lt2 = s_above_lt2 - s_below_lt2
    luds_impact_lt2 = 0.35 * delta_s_lt2
    print(f"DFA LT2 Boundary (0.50): alpha={alpha_below_lt2:.6f} -> S_dfa={s_below_lt2}, alpha={alpha_above_lt2:.6f} -> S_dfa={s_above_lt2}")
    print(f"Discontinuous Jump in S_dfa: {delta_s_lt2} points -> LUDS Score Swing: {luds_impact_lt2:.2f} points")

    # DFA computation edge case: constant RR intervals (F(n) = 0)
    def dfa_alpha1_synthetic(rr_intervals, scales=range(4, 17)):
        y = np.cumsum(rr_intervals - np.mean(rr_intervals))
        N = len(rr_intervals)
        F_n = []
        valid_scales = []
        for n in scales:
            if n > N:
                continue
            k_segments = N // n
            if k_segments == 0:
                continue
            flucs = []
            for k in range(k_segments):
                seg = y[k*n : (k+1)*n]
                x = np.arange(n)
                poly = np.polyfit(x, seg, 1)
                trend = np.polyval(poly, x)
                flucs.append(np.mean((seg - trend)**2))
            mean_fluc = np.sqrt(np.mean(flucs))
            if mean_fluc > 1e-12:
                F_n.append(mean_fluc)
                valid_scales.append(n)
            else:
                F_n.append(0.0)
                valid_scales.append(n)
        if len([f for f in F_n if f > 0]) < 2:
            return None, "Singularity/Zero fluctuation (F(n)=0)"
        log_n = np.log(valid_scales)
        log_F = np.log(F_n)
        slope, _ = np.polyfit(log_n, log_F, 1)
        return slope, "OK"

    constant_rr = np.ones(120) * 800.0
    slope_c, msg_c = dfa_alpha1_synthetic(constant_rr)
    print(f"DFA on constant RR: slope={slope_c}, status={msg_c}")

    # =========================================================================
    # Test 3: Moens-Korteweg / PTT Blood Pressure Singularity & Asymptotes
    # =========================================================================
    print("\n=== TEST 3: Moens-Korteweg & PTT Blood Pressure Limits ===")
    gamma = 0.017 # mmHg^-1
    a_sbp = -2.0 / gamma # ~ -117.65
    a_dbp = -1.2 / gamma # ~ -70.59
    c_sbp = 120.0
    c_dbp = 80.0
    
    ptt_values = [0.250, 0.200, 0.150, 0.100, 0.050, 0.010, 0.001, 0.0, -0.05]
    for ptt in ptt_values:
        if ptt <= 0:
            print(f"PTT = {ptt}s -> ln(PTT) is UNDEFINED (Math Domain Error / NaN)")
        else:
            sbp = a_sbp * math.log(ptt) + c_sbp
            dbp = a_dbp * math.log(ptt) + c_dbp
            pp = sbp - dbp
            print(f"PTT = {ptt:.3f}s -> ln(PTT)={math.log(ptt):.3f} | SBP = {sbp:.1f} mmHg | DBP = {dbp:.1f} mmHg | Pulse Pressure = {pp:.1f} mmHg")

    # =========================================================================
    # Test 4: Bramwell-Hill Arterial Compliance & 2-Element Windkessel SVR Singularity
    # =========================================================================
    print("\n=== TEST 4: Bramwell-Hill & Windkessel SVR Singularity ===")
    V0 = 0.0010 # m^3
    rho = 1055.0 # kg/m^3
    
    def compute_cart(pwv):
        if pwv <= 0:
            return float('inf')
        return (V0 / (rho * (pwv**2))) * 133.322 * 1e6

    pwv_tests = [4.0, 6.0, 8.0, 12.0, 0.0]
    for pwv in pwv_tests:
        cart = compute_cart(pwv)
        print(f"PWV = {pwv:.1f} m/s -> C_art = {cart:.3f} mL/mmHg")

    def compute_wk2_rp(delta_t_dia, c_art, sbp, dbp, alpha_notch=0.85):
        ratio = alpha_notch * (sbp / dbp)
        if ratio <= 0:
            return None, "Math domain error: ratio <= 0"
        denominator_term = math.log(ratio)
        if abs(denominator_term) < 1e-12:
            return float('inf'), "Singularity: alpha_notch * SBP == DBP -> ln(1) = 0 -> Rp = inf"
        rp = delta_t_dia / (c_art * denominator_term)
        status = "OK" if rp > 0 else "FATAL: Negative Resistance (Rp < 0)"
        return rp, status

    c_art_norm = compute_cart(6.0) # ~ 3.51 mL/mmHg
    delta_t = 0.50 # 500ms diastolic decay
    
    wk2_scenarios = [
        (140, 80, "Normal Exercise: 140/80"),
        (120, 80, "Resting: 120/80"),
        (110, 80, "Low Pulse Pressure: 110/80"),
        (100, 85, "Hypotensive / Tachycardia: 100/85 (ratio = 0.85 * 100/85 = 1.0)"),
        (95, 85, "Narrow PP / Shock: 95/85 (ratio = 0.85 * 95/85 = 0.95 < 1.0)"),
    ]
    for sbp, dbp, label in wk2_scenarios:
        rp, stat = compute_wk2_rp(delta_t, c_art_norm, sbp, dbp)
        ratio = 0.85 * (sbp / dbp)
        print(f"Scenario: {label} -> ratio={ratio:.4f} | Rp = {rp} | {stat}")

    # =========================================================================
    # Test 5: LUDS Readiness Score Bounds & Clamping Test
    # =========================================================================
    print("\n=== TEST 5: LUDS Readiness Bounds ===")
    def compute_luds(rmssd, rmssd_base, alpha1, map_val, p_drift, p_kinetic):
        w_hrv = 0.40
        w_dfa = 0.35
        w_bp = 0.25
        
        s_rmssd = min(100.0, (rmssd / rmssd_base) * 100.0) if rmssd_base > 0 else 0.0
        s_dfa = 100.0 if alpha1 >= 0.75 else (70.0 if alpha1 >= 0.50 else 30.0)
        s_map = max(0.0, 100.0 - abs(map_val - 93.3) * 2.0)
        
        raw_luds = w_hrv * s_rmssd + w_dfa * s_dfa + w_bp * s_map - p_drift - p_kinetic
        return raw_luds

    luds_best = compute_luds(rmssd=100, rmssd_base=100, alpha1=0.85, map_val=93.3, p_drift=0, p_kinetic=0)
    luds_worst = compute_luds(rmssd=5, rmssd_base=100, alpha1=0.30, map_val=160.0, p_drift=15, p_kinetic=30)
    print(f"Optimal Case: LUDS = {luds_best:.2f}")
    print(f"Severe Stress Case: LUDS = {luds_worst:.2f} (Negative score when unbounded!)")

    # =========================================================================
    # Test 6: Multi-Player FFA ELO Rating Algorithm (K=32, N=8) Inflation/Deflation Simulation
    # =========================================================================
    print("\n=== TEST 6: FFA ELO Rating Conservation & Inflation/Deflation ===")
    def simulate_ffa_match(ratings, winner_idx, K=32):
        n = len(ratings)
        r_w = ratings[winner_idx]
        e_w = 0.0
        delta_r = [0.0] * n
        
        # Calculate expected score for winner against each loser
        for i in range(n):
            if i != winner_idx:
                r_l = ratings[i]
                e_wl = 1.0 / (1.0 + 10.0 ** ((r_l - r_w) / 400.0))
                e_lw = 1.0 - e_wl
                e_w += e_wl
                delta_r[i] = -K * (1.0 - e_lw) # = -K * e_wl
        
        num_losers = n - 1
        delta_r[winner_idx] = K * (num_losers - e_w)
        
        new_ratings = [ratings[i] + delta_r[i] for i in range(n)]
        net_elo_change = sum(delta_r)
        return new_ratings, delta_r, net_elo_change

    # Equal initial ratings of 1200
    ratings_equal = [1200.0] * 8
    new_r, deltas, net_change = simulate_ffa_match(ratings_equal, winner_idx=0)
    print(f"Equal Ratings (1200x8), Winner=0:")
    print(f"  Delta Winner: {deltas[0]:+.2f}, Delta Losers: {deltas[1]:+.2f}")
    print(f"  Net Pool ELO Change: {net_change:+.2f} (Pool ELO is preserved only when all ratings equal: E_W = 7 * 0.5 = 3.5 -> Net = 32*(7-7) = 0)")

    # Dominant Champion (1600) vs Underdogs (1000x7)
    ratings_unequal = [1600.0] + [1000.0]*7
    new_r2, deltas2, net_change2 = simulate_ffa_match(ratings_unequal, winner_idx=0)
    print(f"Dominant Champion (1600) Wins:")
    print(f"  Delta Winner: {deltas2[0]:+.2f}, Delta Loser: {deltas2[1]:+.2f}")
    print(f"  Net Pool ELO Change: {net_change2:+.2f} (Massive ELO Deflation!)")

    # Underdog (1000) beats Champion (1600) + Others
    new_r3, deltas3, net_change3 = simulate_ffa_match(ratings_unequal, winner_idx=1)
    print(f"Underdog (1000) Wins:")
    print(f"  Delta Winner: {deltas3[1]:+.2f}, Delta Champion: {deltas3[0]:+.2f}, Delta Other Loser: {deltas3[2]:+.2f}")
    print(f"  Net Pool ELO Change: {net_change3:+.2f} (Massive ELO Inflation!)")

    # =========================================================================
    # Test 7: Hardware VRAM / RAM Allocation & Headroom Audit
    # =========================================================================
    print("\n=== TEST 7: Hardware VRAM Pool & Physical RAM Headroom Audit ===")
    nodes = [
        {"layer": 1, "name": "Apple M4 Pro Mac Mini Host", "ram": 24.0, "vram_cap": 21.6, "rank": 4},
        {"layer": 2, "name": "MacBook Pro M1 Max", "ram": 16.0, "vram_cap": 14.0, "rank": 2},
        {"layer": 3, "name": "Linux Head Node (Ryzen 7)", "ram": 15.3, "vram_cap": 13.8, "rank": 1},
        {"layer": 4, "name": "Bedside Linux Tablet", "ram": 8.0, "vram_cap": 6.5, "rank": 1},
        {"layer": 5, "name": "MacBook Air (Apple M4)", "ram": 16.0, "vram_cap": 13.5, "rank": 3},
        {"layer": 6, "name": "Google Pixel 10 Pro XL", "ram": 15.2, "vram_cap": 12.5, "rank": 6},
        {"layer": 7, "name": "Samsung Galaxy S20+", "ram": 12.0, "vram_cap": 9.0, "rank": 5},
    ]
    
    total_physical_ram = sum(n["ram"] for n in nodes)
    sum_individual_vram_caps = sum(n["vram_cap"] for n in nodes)
    claimed_pooled_vram = 82.8
    claimed_active_vram = 53.41
    claimed_headroom = 29.39
    
    print(f"Sum of Physical RAM: {total_physical_ram:.2f} GB (Claimed: 106.5 GB)")
    print(f"Sum of Individual VRAM Caps: {sum_individual_vram_caps:.2f} GB (Claimed Pool: {claimed_pooled_vram:.2f} GB)")
    print(f"Discrepancy in VRAM Caps vs Pool: {sum_individual_vram_caps - claimed_pooled_vram:+.2f} GB")
    print(f"Claimed Active + Headroom: {claimed_active_vram + claimed_headroom:.2f} GB")
    
    # Check node by node allocation percentages
    for n in nodes:
        pct = (n["vram_cap"] / n["ram"]) * 100.0
        exceeds_75 = pct > 75.0
        print(f"  Layer {n['layer']} ({n['name']}): RAM={n['ram']}GB, VRAM={n['vram_cap']}GB ({pct:.2f}%) -> Exceeds 75% RAM limit: {exceeds_75}")

    # =========================================================================
    # Test 8: SLERP Singularity at Collinear Vectors (theta = 0)
    # =========================================================================
    print("\n=== TEST 8: SLERP Collinear & Out-of-Domain Boundaries ===")
    def slerp(w0, w1, t=0.5):
        norm_w0 = np.linalg.norm(w0)
        norm_w1 = np.linalg.norm(w1)
        if norm_w0 == 0 or norm_w1 == 0:
            return None, "Zero norm vector"
        cos_theta = np.dot(w0, w1) / (norm_w0 * norm_w1)
        # Check floating point precision exceeding 1.0
        if cos_theta > 1.0:
            cos_theta = 1.0 # Need clamp
        elif cos_theta < -1.0:
            cos_theta = -1.0
        theta = np.arccos(cos_theta)
        if abs(theta) < 1e-7:
            # Collinear vectors -> sin(theta) = 0 -> division by zero
            # Standard linear interpolation fallback required:
            return (1 - t) * w0 + t * w1, "Collinear Fallback to LERP"
        sin_theta = np.sin(theta)
        res = (np.sin((1 - t) * theta) / sin_theta) * w0 + (np.sin(t * theta) / sin_theta) * w1
        return res, "Standard SLERP"

    v0 = np.array([1.0, 2.0, 3.0])
    v1 = np.array([1.0, 2.0, 3.0]) # Identical weights
    res_ident, stat_ident = slerp(v0, v1)
    print(f"Identical Model Weights (theta=0): status={stat_ident}, result={res_ident}")

if __name__ == "__main__":
    run_tests()
