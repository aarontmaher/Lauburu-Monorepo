#!/usr/bin/env python3
"""
Empirical Adversarial Stress-Test Suite for LAUBURU_APP_ECOSYSTEM.md
Auditor/Challenger: challenger_gen2_2c
"""

import sys
import math
import numpy as np

def section_header(title):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def test_kamath_filter():
    section_header("TEST 1: KAMATH 2004 20% RR ARTIFACT FILTER STRESS TEST")
    
    def kamath_filter(rr_series):
        valid = []
        rejected = []
        for i, rr in enumerate(rr_series):
            if i == 0:
                if rr > 0:
                    valid.append(rr)
                else:
                    rejected.append((i, rr, "Non-positive RR interval (<= 0)"))
                continue
            prev = valid[-1] if valid else None
            if prev is None or prev <= 0:
                rejected.append((i, rr, "No valid preceding RR interval"))
                continue
            dev = abs(rr - prev) / prev
            if dev <= 0.20:
                valid.append(rr)
            else:
                rejected.append((i, rr, f"Deviation {dev*100:.2f}% > 20% threshold"))
        return valid, rejected

    # 1.1 Ectopic beat test
    ectopic_series = [800, 810, 790, 450, 800, 815] # 450ms is ectopic
    v_ec, r_ec = kamath_filter(ectopic_series)
    print(f"[*] 1.1 Isolated Ectopic Beat (450ms):")
    print(f"    Input: {ectopic_series}")
    print(f"    Valid Beats ({len(v_ec)}): {v_ec}")
    print(f"    Rejected Beats ({len(r_ec)}): {r_ec}")
    assert len(r_ec) == 1 and r_ec[0][1] == 450, "Failed to isolate single ectopic beat"

    # 1.2 Physiological Sprint Acceleration Step Test (120 bpm -> 180 bpm)
    # RR drops from 500ms to 333ms (33.4% reduction).
    sprint_series = [500, 333, 332, 330, 335, 334]
    v_sp, r_sp = kamath_filter(sprint_series)
    print(f"\n[*] 1.2 Sudden Sprint Step (500ms -> 333ms, 33.4% drop):")
    print(f"    Input: {sprint_series}")
    print(f"    Valid Beats ({len(v_sp)}): {v_sp}")
    print(f"    Rejected Beats ({len(r_sp)}): {r_sp}")
    print(f"    [FINDING] Cascade Failure: When 333ms is rejected, preceding valid beat remains 500ms.")
    print(f"    Subsequent authentic beats (332ms, 330ms) are compared to 500ms and also rejected!")
    print(f"    Rejection count: {len(r_sp)} of {len(sprint_series)-1} post-acceleration beats rejected (100% cascade lockout).")

    # 1.3 Boundary deviations: exactly 20.00% vs 20.01%
    v_b1, r_b1 = kamath_filter([1000, 800]) # 20.00%
    v_b2, r_b2 = kamath_filter([1000, 799]) # 20.10%
    print(f"\n[*] 1.3 Boundary Threshold Sensitivity:")
    print(f"    1000ms -> 800ms (20.00% drop): Valid = {v_b1}, Rejected = {r_b1}")
    print(f"    1000ms -> 799ms (20.10% drop): Valid = {v_b2}, Rejected = {r_b2}")

    # 1.4 Zero / Sensor Disconnect
    v_z, r_z = kamath_filter([800, 0, -10, 810])
    print(f"\n[*] 1.4 Zero and Negative RR Handling:")
    print(f"    Valid = {v_z}, Rejected = {r_z}")

def test_dfa_and_luds():
    section_header("TEST 2: DFA-ALPHA1 & LUDS READINESS SCORE DISCONTINUITY")
    
    def compute_s_dfa(alpha1):
        if alpha1 >= 0.75:
            return 100.0
        elif 0.50 <= alpha1 < 0.75:
            return 70.0
        else:
            return 30.0

    def compute_luds(rmssd, rmssd_base, alpha1, map_val, p_drift=0, p_kinetic=0):
        w_hrv = 0.40
        w_dfa = 0.35
        w_bp = 0.25
        s_rmssd = min(100.0, (rmssd / rmssd_base) * 100.0) if rmssd_base > 0 else 0.0
        s_dfa = compute_s_dfa(alpha1)
        s_map = max(0.0, 100.0 - abs(map_val - 93.3) * 2.0)
        return w_hrv * s_rmssd + w_dfa * s_dfa + w_bp * s_map - p_drift - p_kinetic

    # 2.1 Boundary step jump at LT1 (0.75)
    a1_high = 0.750001
    a1_low = 0.749999
    s_high = compute_s_dfa(a1_high)
    s_low = compute_s_dfa(a1_low)
    luds_high = compute_luds(40, 50, a1_high, 93.3)
    luds_low = compute_luds(40, 50, a1_low, 93.3)
    print(f"[*] 2.1 LT1 Threshold Discontinuity at alpha_1 = 0.75:")
    print(f"    alpha_1 = {a1_high:.6f} -> S_dfa = {s_high:.1f}, LUDS = {luds_high:.2f}")
    print(f"    alpha_1 = {a1_low:.6f}  -> S_dfa = {s_low:.1f}, LUDS = {luds_low:.2f}")
    print(f"    Delta S_dfa: {s_high - s_low:.1f} pts | Delta LUDS: {luds_high - luds_low:.2f} pts (Discontinuous step jump)")

    # 2.2 Boundary step jump at LT2 (0.50)
    a2_high = 0.500001
    a2_low = 0.499999
    s2_high = compute_s_dfa(a2_high)
    s2_low = compute_s_dfa(a2_low)
    luds2_high = compute_luds(40, 50, a2_high, 93.3)
    luds2_low = compute_luds(40, 50, a2_low, 93.3)
    print(f"\n[*] 2.2 LT2 Threshold Discontinuity at alpha_1 = 0.50:")
    print(f"    alpha_1 = {a2_high:.6f} -> S_dfa = {s2_high:.1f}, LUDS = {luds2_high:.2f}")
    print(f"    alpha_1 = {a2_low:.6f}  -> S_dfa = {s2_low:.1f}, LUDS = {luds2_low:.2f}")
    print(f"    Delta S_dfa: {s2_high - s2_low:.1f} pts | Delta LUDS: {luds2_high - luds2_low:.2f} pts (Discontinuous step jump)")

    # 2.3 Unbounded Negative LUDS Score under severe fatigue
    luds_fatigued = compute_luds(rmssd=5, rmssd_base=60, alpha1=0.35, map_val=150.0, p_drift=15.0, p_kinetic=40.0)
    print(f"\n[*] 2.3 Severe Fatigue / Impact LUDS Lower Bound:")
    print(f"    Params: RMSSD=5/60, alpha1=0.35, MAP=150, P_drift=15, P_kinetic=40")
    print(f"    Raw LUDS Score: {luds_fatigued:.2f} (Breaches 0-100 nominal range without clamping)")

    # 2.4 DFA Singularity on Perfectly Periodic Rhythm (constant RR)
    def calculate_dfa_alpha1(rr_series, scales=range(4, 17)):
        N = len(rr_series)
        y = np.cumsum(rr_series - np.mean(rr_series))
        F_n = []
        scales_used = []
        for n in scales:
            if n > N:
                continue
            k_segs = N // n
            if k_segs == 0:
                continue
            flucs = []
            for k in range(k_segs):
                seg = y[k*n:(k+1)*n]
                x = np.arange(n)
                p = np.polyfit(x, seg, 1)
                fit = np.polyval(p, x)
                flucs.append(np.mean((seg - fit)**2))
            mean_fluc = np.sqrt(np.mean(flucs))
            F_n.append(mean_fluc)
            scales_used.append(n)
        if len(F_n) < 2 or all(f < 1e-12 for f in F_n):
            return None, "Singularity: All F(n) == 0 (ln(0) = -inf)"
        log_n = np.log(scales_used)
        log_F = np.log(np.maximum(F_n, 1e-15))
        slope, _ = np.polyfit(log_n, log_F, 1)
        return slope, "OK"

    const_rr = np.ones(120) * 800.0
    slope_c, stat_c = calculate_dfa_alpha1(const_rr)
    print(f"\n[*] 2.4 Constant RR DFA Singularity:")
    print(f"    120 beats of 800ms: slope = {slope_c}, status = {stat_c}")

def test_hemodynamics_and_windkessel():
    section_header("TEST 3: HEMODYNAMICS, PTT BP & 2-ELEMENT WINDKESSEL SVR")
    
    # 3.1 PTT approaching zero and negative values
    gamma = 0.017 # mmHg^-1
    a_sbp = -2.0 / gamma # -117.647
    a_dbp = -1.2 / gamma # -70.588
    c_sbp = 120.0
    c_dbp = 80.0
    
    print("[*] 3.1 Pulse Transit Time (PTT) Asymptotic & Singularity Analysis:")
    for ptt in [0.250, 0.200, 0.150, 0.100, 0.050, 0.010, 0.001, 0.0, -0.05]:
        if ptt <= 0:
            print(f"    PTT = {ptt:+.3f}s -> ln(PTT) is UNDEFINED (Math Domain Error / NaN)")
        else:
            sbp = a_sbp * math.log(ptt) + c_sbp
            dbp = a_dbp * math.log(ptt) + c_dbp
            pp = sbp - dbp
            print(f"    PTT = {ptt:.3f}s -> ln(PTT)={math.log(ptt):.3f} | SBP={sbp:6.1f} mmHg | DBP={dbp:5.1f} mmHg | PP={pp:5.1f} mmHg")

    # 3.2 2-Element Windkessel SVR Singularity & Negative Resistance
    V0 = 0.0010
    rho = 1055.0
    pwv = 6.0
    c_art = (V0 / (rho * (pwv**2))) * 133.322 * 1e6 # mL/mmHg (~3.51)
    delta_t = 0.50
    alpha_notch = 0.85
    
    print(f"\n[*] 3.2 2-Element Windkessel SVR (WK2) Singularities (C_art = {c_art:.3f} mL/mmHg):")
    print(f"    Formula: R_p = Delta_T_dia / (C_art * ln(alpha_notch * SBP / DBP)), alpha_notch = {alpha_notch}")
    
    test_cases = [
        (140, 80, "Exercise Normal (140/80)"),
        (120, 80, "Resting Normal (120/80)"),
        (117.65, 100.0, "Critical Singularity: SBP/DBP = 1/0.85 = 1.17647 -> ratio = 1.0"),
        (110, 95, "Narrow Pulse Pressure: 110/95 (ratio = 0.85*110/95 = 0.9842 < 1.0)"),
        (100, 90, "Hypotensive Tachycardia: 100/90 (ratio = 0.85*100/90 = 0.9444 < 1.0)")
    ]
    for sbp, dbp, label in test_cases:
        ratio = alpha_notch * (sbp / dbp)
        if ratio <= 0:
            res_str = "UNDEFINED (ratio <= 0)"
        else:
            denom = math.log(ratio)
            if abs(denom) < 1e-6:
                res_str = f"SINGULARITY: ln(1.0) = 0 -> R_p = +inf"
            else:
                rp = delta_t / (c_art * denom)
                if rp < 0:
                    res_str = f"FATAL NON-PHYSIOLOGICAL: R_p = {rp:.3f} mmHg*s/mL (Negative Resistance!)"
                else:
                    res_str = f"Valid: R_p = {rp:.3f} mmHg*s/mL"
        print(f"    Case '{label}': ratio = {ratio:.5f} -> {res_str}")

def test_elo_tournament():
    section_header("TEST 4: FFA MULTI-PLAYER ELO TOURNAMENT DYNAMICS (K=32, N=8)")
    
    def simulate_match(ratings, winner_idx, K=32):
        n = len(ratings)
        r_w = ratings[winner_idx]
        e_w = 0.0
        deltas = [0.0] * n
        for i in range(n):
            if i != winner_idx:
                r_l = ratings[i]
                e_wl = 1.0 / (1.0 + 10.0 ** ((r_l - r_w) / 400.0))
                e_lw = 1.0 - e_wl
                e_w += e_wl
                deltas[i] = -K * (1.0 - e_lw) # = -K * e_wl
        deltas[winner_idx] = K * ((n - 1) - e_w)
        new_ratings = [ratings[i] + deltas[i] for i in range(n)]
        net_change = sum(deltas)
        return new_ratings, deltas, net_change

    # 4.1 Balanced Field (all 1200)
    r_bal = [1200.0] * 8
    _, d_bal, net_bal = simulate_match(r_bal, 0)
    print(f"[*] 4.1 Balanced Field (All 8 Gladiators = 1200 ELO):")
    print(f"    Winner (Idx 0): Delta = {d_bal[0]:+.2f} ELO")
    print(f"    Each Loser:     Delta = {d_bal[1]:+.2f} ELO")
    print(f"    Net Pool Delta: {net_bal:+.2f} ELO (Conserved Zero-Sum when all ratings equal)")

    # 4.2 Dominant Champion (1600) vs Underdogs (1000x7)
    r_dom = [1600.0] + [1000.0] * 7
    _, d_dom, net_dom = simulate_match(r_dom, 0)
    print(f"\n[*] 4.2 Dominant Champion (1600) Wins against Underdogs (1000x7):")
    print(f"    Champion Winner: Delta = {d_dom[0]:+.2f} ELO")
    print(f"    Each Underdog:   Delta = {d_dom[1]:+.2f} ELO (Total Loser Delta = {sum(d_dom[1:]):+.2f})")
    print(f"    Net Pool Delta:  {net_dom:+.2f} ELO (Massive ELO Deflation!)")

    # 4.3 Underdog (1000) Wins against Champion (1600) + 6 Others
    _, d_und, net_und = simulate_match(r_dom, 1)
    print(f"\n[*] 4.3 Underdog (1000) Wins against Champion (1600) + Field:")
    print(f"    Underdog Winner: Delta = {d_und[1]:+.2f} ELO")
    print(f"    Champion Loser:  Delta = {d_und[0]:+.2f} ELO")
    print(f"    Other Losers:    Delta = {d_und[2]:+.2f} ELO (Total Loser Delta = {sum(d_und) - d_und[1]:+.2f})")
    print(f"    Net Pool Delta:  {net_und:+.2f} ELO (Massive ELO Inflation!)")

    # 4.4 Section 1.2 claim "+15 ELO per win" vs K=32 formula
    print(f"\n[*] 4.4 Discrepancy Analysis: Fixed '+15 ELO' (Sec 1.2) vs 'FFA K=32 Formula' (Sec 2.1):")
    print(f"    Section 1.2 claims: 'The winning agent earns +15 ELO in ai_elo_leaderboard.json'.")
    print(f"    Section 2.1 gives formula: Delta R_W = K * (|L| - E_W). For N=8, K=32, if equal, Delta R_W = +112 ELO!")
    print(f"    Ratio: +112 / +15 = 7.46x discrepancy. The two sections describe contradictory ELO adjustment magnitudes.")

def test_hardware_topology():
    section_header("TEST 5: MULTI-LAYER HARDWARE TOPOLOGY & VRAM ALLOCATION AUDIT")
    
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
    
    print(f"[*] 5.1 Aggregate Sums:")
    print(f"    Physical RAM Sum:               {total_physical_ram:.2f} GB (Document claims: 106.5 GB -> MATCH)")
    print(f"    Sum of Usable VRAM Caps:        {sum_individual_vram_caps:.2f} GB")
    print(f"    Claimed Cluster Usable VRAM:    {claimed_pooled_vram:.2f} GB")
    print(f"    Discrepancy (Sum - Claimed):    {sum_individual_vram_caps - claimed_pooled_vram:+.2f} GB")
    print(f"    Claimed Active (53.41) + Headroom (29.39) = {claimed_active_vram + claimed_headroom:.2f} GB (Matches 82.80 GB)")

    print(f"\n[*] 5.2 Per-Node Allocation vs 75% Host RAM Safety Ceiling:")
    for n in nodes:
        pct = (n["vram_cap"] / n["ram"]) * 100.0
        remaining_ram = n["ram"] - n["vram_cap"]
        safe_75_cap = n["ram"] * 0.75
        exceeds_75 = n["vram_cap"] > safe_75_cap
        status = "BREACH (>75%)" if exceeds_75 else "COMPLIANT (<=75%)"
        print(f"    Layer {n['layer']} ({n['name']:28s}): RAM={n['ram']:4.1f}GB, Cap={n['vram_cap']:4.1f}GB ({pct:5.2f}%) | OS Headroom={remaining_ram:4.1f}GB | 75% Cap={safe_75_cap:4.1f}GB -> {status}")

    print(f"\n[*] 5.3 Cluster-Wide RAM Safety Margins:")
    print(f"    Total Physical RAM: 106.5 GB")
    print(f"    75% Cluster Safety Margin: {106.5 * 0.75:.2f} GB")
    print(f"    Claimed VRAM Pool (82.8 GB): {82.8 / 106.5 * 100:.2f}% of RAM (Exceeds 75% cluster threshold by {82.8 - 106.5*0.75:.2f} GB)")
    print(f"    Sum of Node Caps (90.9 GB):  {90.9 / 106.5 * 100:.2f}% of RAM (Exceeds 75% cluster threshold by {90.9 - 106.5*0.75:.2f} GB)")

def test_slerp_and_merging():
    section_header("TEST 6: SLERP & DARE-TIES WEIGHT MERGING MATHEMATICS")
    
    def slerp(w0, w1, t=0.5):
        norm0 = np.linalg.norm(w0)
        norm1 = np.linalg.norm(w1)
        if norm0 == 0 or norm1 == 0:
            return None, "Zero norm vector"
        cos_theta = np.dot(w0, w1) / (norm0 * norm1)
        cos_theta_clamped = np.clip(cos_theta, -1.0, 1.0)
        theta = np.arccos(cos_theta_clamped)
        if abs(theta) < 1e-7:
            return (1 - t) * w0 + t * w1, "Collinear / Identical (LERP Fallback)"
        if abs(theta - np.pi) < 1e-7:
            return None, "Antipodal Vectors (theta = pi, sin(pi)=0, undefined geodesic)"
        sin_theta = np.sin(theta)
        res = (np.sin((1 - t) * theta) / sin_theta) * w0 + (np.sin(t * theta) / sin_theta) * w1
        return res, "Valid SLERP"

    # 6.1 Identical weights
    w_same = np.array([0.5, 0.5, 0.5, 0.5])
    r_same, stat_same = slerp(w_same, w_same)
    print(f"[*] 6.1 Identical Weights (theta = 0): {stat_same} -> Result: {r_same}")

    # 6.2 Orthogonal weights
    w_ortho0 = np.array([1.0, 0.0, 0.0])
    w_ortho1 = np.array([0.0, 1.0, 0.0])
    r_ortho, stat_ortho = slerp(w_ortho0, w_ortho1, t=0.5)
    print(f"[*] 6.2 Orthogonal Weights (theta = 90 deg): {stat_ortho} -> Result: {r_ortho}")

    # 6.3 Antipodal weights
    w_anti0 = np.array([1.0, 0.0, 0.0])
    w_anti1 = np.array([-1.0, 0.0, 0.0])
    r_anti, stat_anti = slerp(w_anti0, w_anti1, t=0.5)
    print(f"[*] 6.3 Antipodal Weights (theta = 180 deg): {stat_anti}")

    # 6.4 DARE-TIES Sparsity and Rescaling
    p_drop = 0.90
    scale = 1.0 / (1.0 - p_drop)
    print(f"\n[*] 6.4 DARE-TIES Rescaling Factor:")
    print(f"    Drop Rate p = {p_drop} -> Rescaling Multiplier = 1/(1-p) = {scale:.1f}x")
    print(f"    Surviving 10% of parameter deltas are magnified 10-fold to preserve total weight energy.")

def test_port_conflicts():
    section_header("TEST 7: CANONICAL PORT ALLOCATION MATRIX AUDIT")
    
    ports = [
        (22, "OpenSSH Server", "macOS & Linux Hosts", "Tailscale / LAN"),
        (445, "Samba SMB3 Gateway", "Linux Head Node", "LAN"),
        (3000, "Swarm Dashboard & Canvas", "All Nodes", "0.0.0.0"),
        (4000, "Canonical Web & Compute Hub", "All Nodes", "0.0.0.0"),
        (5001, "3D Spatial Kinematics Lab", "Mac/Linux", "0.0.0.0"),
        (5050, "Shadow Benchmarker API", "Host Node", "0.0.0.0"),
        (5555, "Android Debug Bridge (ADB)", "Termux / USB", "127.0.0.1"),
        (6333, "Qdrant Vector Database", "Linux Head Node", "127.0.0.1 / Tailscale"),
        (6379, "Apache Ray / Redis Cluster", "Linux Head Node", "100.101.39.98"),
        (8022, "Termux OpenSSH Server", "Android Edge Nodes", "Tailscale"),
        (8080, "llama.cpp OpenAI API Gateway", "Mac Mini Host", "127.0.0.1"),
        (8081, "Crucible Gladiator 1 (Qwen)", "Edge Nodes", "127.0.0.1"),
        (8082, "Crucible Gladiator 2 (Llama)", "Edge Nodes", "127.0.0.1"),
        (8083, "Crucible Gladiator 3 (Gemma)", "Edge Nodes", "127.0.0.1"),
        (8084, "Crucible Gladiator 4 (DeepSeek)", "Edge Nodes", "127.0.0.1"),
        (8085, "Crucible Gladiator 5 (SmolLM2)", "Linux Head Node", "127.0.0.1"),
        (8085, "Petals DHT Layer Swarm", "P2P Mesh", "0.0.0.0"),
        (8086, "Crucible Gladiator 6 (Phi-3)", "Bedside Linux Tablet", "127.0.0.1"),
        (8086, "Edge Sensor Daemon", "Edge Nodes", "0.0.0.0"),
        (8087, "Crucible Gladiator 7 (Granite)", "Headless MacBook Air", "127.0.0.1"),
        (8087, "LoRA Harvest Cron Service", "Linux Head Node", "127.0.0.1"),
        (8088, "Crucible Gladiator 8 (Danube)", "Local Edge Co-Processor", "127.0.0.1"),
        (8088, "Termux Edge Daemon", "Android Edge Nodes", "8088"),
        (8088, "SeaweedFS Filer / Quartz SSG", "Linux Head Node", "100.101.39.98 / 127.0.0.1"),
        (8265, "Apache Ray Web Dashboard", "Linux Head Node", "100.101.39.98"),
        (8384, "Syncthing Web Management", "All Nodes", "127.0.0.1 / Tailscale"),
        (8888, "Obsidian Commander (Quartz)", "Host Node", "Port 8888 (Sec 2.3)"),
        (9333, "SeaweedFS Master", "Linux Head Node", "100.101.39.98"),
        (18802, "Nomad Courier WoL API", "All Nodes", "0.0.0.0"),
        (22000, "Syncthing BEP Sync", "P2P Cluster", "0.0.0.0"),
        (50052, "llama.cpp RPC Server", "6 Mesh Endpoints", "0.0.0.0"),
        (52415, "Exo Distributed Ring", "All Nodes", "0.0.0.0")
    ]
    
    port_counts = {}
    for port, name, host, bind in ports:
        port_counts.setdefault(port, []).append((name, host, bind))
    
    print("[*] 7.1 Port Multi-Tenancy & Collision Detection:")
    for port, assignments in sorted(port_counts.items()):
        if len(assignments) > 1:
            print(f"    [MULTI-TENANCY / OVERLAP] Port {port}:")
            for name, host, bind in assignments:
                print(f"      - {name:32s} on {host:24s} (bind: {bind})")

def main():
    test_kamath_filter()
    test_dfa_and_luds()
    test_hemodynamics_and_windkessel()
    test_elo_tournament()
    test_hardware_topology()
    test_slerp_and_merging()
    test_port_conflicts()
    print("\n" + "=" * 80)
    print("  EMPIRICAL STRESS TESTS COMPLETE")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    main()
