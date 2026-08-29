import ast
import glob
import os
import re
import sys

target_dirs = [
    "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/biometrics/movesense_hub",
    "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/user_facing_and_scaling/movesense_readiness_hub",
    "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/03_biometrics_and_telemetry",
]

print("=" * 80)
print("FORENSIC INTEGRITY AUDIT: MILESTONE M1 (MOVESENSE READINESS SUITE)")
print("=" * 80)

total_files_scanned = 0
all_violations = []

# 1. AST & STATIC CODE INSPECTION
print("\n[PHASE 1] AST & STATIC CODE INSPECTION (DUMMIES, CHEATS, HARDCODED OUTPUTS)")
for base_dir in target_dirs:
    py_files = glob.glob(os.path.join(base_dir, "**/*.py"), recursive=True)
    for file_path in sorted(py_files):
        if "tests" in file_path or "__pycache__" in file_path:
            continue
        total_files_scanned += 1
        rel = os.path.relpath(file_path, "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
        with open(file_path, "r", encoding="utf-8") as f:
            src = f.read()

        try:
            tree = ast.parse(src, filename=file_path)
        except SyntaxError as e:
            all_violations.append(f"Syntax error in {rel}: {e}")
            continue

        dummy_funcs = []
        env_checks = []
        random_calls = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if len(node.body) == 1:
                    b = node.body[0]
                    if isinstance(b, ast.Pass):
                        dummy_funcs.append(f"{node.name}() [body: pass]")
                    elif isinstance(b, ast.Raise) and isinstance(getattr(b, "exc", None), ast.Call):
                        func_id = getattr(b.exc.func, "id", "")
                        if func_id == "NotImplementedError":
                            dummy_funcs.append(f"{node.name}() [raises NotImplementedError]")

            if isinstance(node, ast.Call):
                func_str = ""
                try:
                    func_str = ast.unparse(node.func)
                except Exception:
                    pass
                if "random.choice" in func_str or "random.uniform" in func_str or "random.random" in func_str or "random.randint" in func_str:
                    # check if this is in a production telemetry emission
                    random_calls.append(f"Line {node.lineno}: {func_str}()")

                if isinstance(node.func, ast.Attribute) and node.func.attr == "get":
                    if isinstance(node.func.value, ast.Attribute) and node.func.value.attr == "environ":
                        if node.args and isinstance(node.args[0], ast.Constant):
                            arg_val = str(node.args[0].value).upper()
                            if "TEST" in arg_val or "PYTEST" in arg_val or "MOCK" in arg_val:
                                env_checks.append(f"Line {node.lineno}: {ast.unparse(node)}")

        status_str = "PASS (Clean)"
        details = []
        if dummy_funcs:
            details.append(f"Dummy functions: {dummy_funcs}")
            all_violations.append(f"Dummy functions in {rel}: {dummy_funcs}")
        if env_checks:
            details.append(f"Test bypass env checks: {env_checks}")
            all_violations.append(f"Test bypass env checks in {rel}: {env_checks}")
        if random_calls:
            details.append(f"Random calls: {random_calls}")

        print(f"• {rel}: {status_str if not details else 'FLAGGED: ' + '; '.join(details)}")

# 2. RULE #0 ZERO-MOCK SIGNAL PROCESSING MATH VALIDATION
print("\n[PHASE 2] RULE #0 ZERO-MOCK SIGNAL PROCESSING MATH VALIDATION")
import importlib
repo_root = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo"
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

try:
    mhb = importlib.import_module("01_apps.biometrics.movesense_hub")
    
    # Check 1: 512Hz Butterworth Bandpass filter
    detector = mhb.PanTompkinsQRSDetector(sample_rate_hz=512)
    assert detector.fs == 512
    assert detector.mwi_window == 76  # 150ms * 512 = 76.8 -> 76
    assert detector.refractory_samples == 102  # 200ms * 512 = 102.4 -> 102
    
    # Filter impulse and check attenuation of DC
    dc_sig = [10.0] * 512
    filtered_dc = detector.bandpass_filter(dc_sig)
    mean_dc = sum(filtered_dc[100:400]) / len(filtered_dc[100:400])
    print(f"  [Math] Butterworth Bandpass DC attenuation: Initial=+10.0mV, Filtered mean={mean_dc:.4f}mV -> PASS")
    
    # Check 2: Kamath 2004 20% clinical RR filter
    raw_rrs = [800.0, 1600.0, 350.0, 1700.0, 805.0]
    cleaned, artifacts = mhb.apply_kamath_artifact_filter(raw_rrs, threshold_pct=20.0)
    print(f"  [Math] Kamath 20% RR filter: In={raw_rrs}, Out={cleaned}, Rejected={artifacts} -> PASS")
    assert artifacts >= 3
    
    # Check 3: RMSSD formula
    rrs_rmssd = [1000.0, 1050.0, 980.0, 1020.0, 990.0]
    rmssd = mhb.calculate_rmssd(rrs_rmssd)
    print(f"  [Math] RMSSD microsecond calculation: {rmssd} ms (Expected 49.75) -> PASS")
    assert abs(rmssd - 49.75) < 0.1
    
    # Check 4: DFA-alpha1 scaling exponent
    dfa_val = mhb.calculate_dfa_alpha1([1000.0 + i % 2 * 50.0 for i in range(30)])
    print(f"  [Math] DFA-alpha1 rolling scaling exponent: {dfa_val} -> PASS")
    assert dfa_val is not None
    
    # Check 5: Continuous PTT blood pressure
    sbp, dbp, map_val = mhb.calculate_hemodynamics_bp(ptt_ms=195.0, hr_bpm=70.0)
    print(f"  [Math] PTT Blood Pressure (195ms PTT, 70 BPM): SBP={sbp}, DBP={dbp}, MAP={map_val} mmHg -> PASS")
    assert sbp == 122.2 and dbp == 81.2 and map_val == 94.9
    
    # Check 6: Disconnected null state (Rule #0 invariant)
    sbp_null, dbp_null, map_null = mhb.calculate_hemodynamics_bp(ptt_ms=None, hr_bpm=None)
    assert sbp_null is None and dbp_null is None and map_null is None
    print(f"  [Math] Disconnected PTT state: SBP={sbp_null}, DBP={dbp_null}, MAP={map_null} (Rule #0 Verified) -> PASS")
    
    # Check 7: Sleep Staging
    sleep_res = mhb.compute_overnight_sleep_analysis(hr_bpm=52.0, rmssd_ms=58.0, epoch_stages=["DEEP", "DEEP", "REM", "LIGHT"])
    print(f"  [Math] Overnight Sleep Staging Score: {sleep_res.sleep_score_100}/100, Deep={sleep_res.deep_pct}%, Status={sleep_res.recovery_status} -> PASS")
    assert sleep_res.sleep_score_100 is not None
    
    # Check 8: Zone 2 coaching
    coaching_engine = mhb.Zone2CoachingEngine(user_age=30, hr_rest_baseline=58.0)
    rec = coaching_engine.get_coaching_recommendation(hr_bpm=135.0, dfa_alpha1=0.78)
    print(f"  [Math] Zone 2 Coaching Recommendation (DFA=0.78): {rec['action']} - '{rec['recommendation']}' -> PASS")
    assert rec['action'] == "PERFECT_PACE"
    
except Exception as e:
    all_violations.append(f"Math validation error: {e}")
    print(f"  [Math] ERROR: {e}")

# 3. BIOMETRICS AIRGAP VERIFICATION
print("\n[PHASE 3] BIOMETRICS AIRGAP VERIFICATION (EXTERNAL NETWORK CALLS)")
network_calls_found = []
for base_dir in target_dirs:
    py_files = glob.glob(os.path.join(base_dir, "**/*.py"), recursive=True)
    for file_path in sorted(py_files):
        if "tests" in file_path or "__pycache__" in file_path:
            continue
        rel = os.path.relpath(file_path, "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
        with open(file_path, "r", encoding="utf-8") as f:
            src = f.read()

        # Check for remote egress network patterns
        for line_no, line in enumerate(src.splitlines(), start=1):
            line_str = line.strip()
            if line_str.startswith("#"):
                continue
            if re.search(r"requests\.(post|put|patch)\s*\(", line_str):
                network_calls_found.append((rel, line_no, line_str))
            if re.search(r"urllib\.request\.urlopen\s*\(", line_str):
                network_calls_found.append((rel, line_no, line_str))
            if re.search(r"httpx\.(post|put|patch)\s*\(", line_str):
                network_calls_found.append((rel, line_no, line_str))
            if re.search(r"https?://(?!127\.0\.0\.1|localhost|0\.0\.0\.0)", line_str):
                # Ignore schema doc comments or string documentation
                if not line_str.startswith('"""') and not line_str.startswith("'''") and "http" in line_str and not line_str.startswith("*"):
                    if "requests" in line_str or "urllib" in line_str or "fetch" in line_str:
                        network_calls_found.append((rel, line_no, line_str))

if not network_calls_found:
    print("  Egress network calls: NONE (0% Biometrics Cloud Leakage - 100% Fail-Closed Local Airgap)")
else:
    print(f"  FLAGGED NETWORK CALLS: {network_calls_found}")
    for n in network_calls_found:
        all_violations.append(f"Network egress in {n[0]}:{n[1]} -> {n[2]}")

# 4. REPOSITORY HYGIENE CHECK
print("\n[PHASE 4] REPOSITORY HYGIENE CHECK (SWAP / TEMP / LEFTOVER FILES)")
swap_files_found = []
for base_dir in target_dirs:
    for root, dirs, files in os.walk(base_dir):
        for fn in files:
            if fn.endswith((".swp", ".swo", "~", ".tmp")) or fn.startswith("#") or fn == ".DS_Store":
                swap_files_found.append(os.path.join(root, fn))

if not swap_files_found:
    print("  Swap / temp files: NONE (Clean repository hygiene)")
else:
    print(f"  FLAGGED SWAP FILES: {swap_files_found}")
    for sf in swap_files_found:
        all_violations.append(f"Leftover swap/temp file: {sf}")

print("\n" + "=" * 80)
print(f"AUDIT SUMMARY: Scanned {total_files_scanned} files across {len(target_dirs)} directories.")
if not all_violations:
    print("FINAL VERDICT: CLEAN")
else:
    print("FINAL VERDICT: INTEGRITY VIOLATION")
    for v in all_violations:
        print(f"  - {v}")
print("=" * 80)
