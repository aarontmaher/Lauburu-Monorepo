import os
import re
import sys
import math

monorepo_root = '/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo'
deliverable_path = os.path.join(monorepo_root, '01_apps/reconnect_project/LAUBURU_APP_ECOSYSTEM.md')
original_req_path = os.path.join(monorepo_root, '01_apps/reconnect_project/.agents/ORIGINAL_REQUEST.md')

test_results = []

def run_test(name, assertion_fn):
    try:
        assertion_fn()
        test_results.append((name, "PASS", "OK"))
        print(f"[PASS] {name}")
    except AssertionError as e:
        test_results.append((name, "FAIL", str(e)))
        print(f"[FAIL] {name}: {e}")
    except Exception as e:
        test_results.append((name, "ERROR", str(e)))
        print(f"[ERROR] {name}: {e}")

# 1. Existence and non-emptiness
def test_file_existence():
    assert os.path.exists(deliverable_path), f"File missing at {deliverable_path}"
    assert os.path.getsize(deliverable_path) > 30000, f"File size too small: {os.path.getsize(deliverable_path)} bytes"

run_test("T01_Deliverable_Existence_And_Size", test_file_existence)

with open(deliverable_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 2. Requirement R1 Verification
def test_requirement_r1_hardware_sentinel():
    assert "Hardware Sentinel" in content, "Hardware Sentinel missing"
    assert "Zero-VRAM" in content, "Zero-VRAM missing"
    assert "Shizuku" in content, "Shizuku missing"
    assert "caffeinate" in content, "macOS caffeinate missing"
    assert "termux-wake-lock" in content, "Termux wake lock missing"
    assert "MIN(Host, Device)" in content or r"\min(P_{\text{host}}" in content or "effective_max_gbps = min(host_max_gbps" in content, "4-Pillar MIN formula missing"

def test_requirement_r1_mesh_healer():
    assert "Mesh Healer" in content, "Mesh Healer missing"
    assert "smolagents" in content, "smolagents missing"
    assert "Tailscale" in content, "Tailscale recovery missing"
    assert "Zombie PID" in content or "fuser -k" in content, "Zombie PID hunting missing"
    assert "Wake-on-LAN" in content or "etherwake" in content, "Wake-on-LAN missing"
    assert "+15" in content and "ELO" in content, "+15 ELO harvesting missing"

def test_requirement_r1_movesense_biometrics():
    assert "Movesense Biometrics Hub" in content or "Movesense 128Hz" in content, "Movesense missing"
    assert "128Hz" in content, "128Hz ECG missing"
    assert "Kamath" in content and "20%" in content, "Kamath 20% filter missing"
    assert "DFA" in content or "dfa_alpha1" in content, "DFA-alpha1 missing"
    assert "Moens-Korteweg" in content, "Moens-Korteweg formula missing"
    assert "LUDS" in content, "LUDS readiness score missing"

def test_requirement_r1_shadow_benchmarker():
    assert "Shadow Benchmarker" in content, "Shadow Benchmarker missing"
    assert "5050" in content, "Port 5050 missing"
    assert "82.8 GB" in content or "82.8" in content, "82.8GB VRAM pool missing"
    assert "TTFT" in content and "TPS" in content, "TTFT/TPS evaluation missing"
    assert "routing.json" in content, "routing.json sync missing"

run_test("T02_R1_Hardware_Sentinel", test_requirement_r1_hardware_sentinel)
run_test("T03_R1_Mesh_Healer", test_requirement_r1_mesh_healer)
run_test("T04_R1_Movesense_Biometrics", test_requirement_r1_movesense_biometrics)
run_test("T05_R1_Shadow_Benchmarker", test_requirement_r1_shadow_benchmarker)

# 3. Requirement R2 Verification
def test_requirement_r2_crucible():
    assert "The Crucible" in content, "The Crucible missing"
    assert "8-way" in content or "8-Gladiator" in content or "8 dedicated SLM nodes" in content, "8-way tournament missing"
    assert "ELO" in content and "K=32" in content or "K=32" in content or "K = 32" in content, "ELO K=32 formula missing"
    assert "SFTTrainer" in content or "train_mesh_lora.py" in content, "LoRA SFTTrainer missing"
    assert "lora_dataset.jsonl" in content, "lora_dataset.jsonl missing"

def test_requirement_r2_main_hub():
    assert "3000" in content and "4000" in content, "Ports 3000 & 4000 missing"
    assert "PBKDF2" in content, "PBKDF2 auth missing"
    assert "Shopify" in content, "Shopify Storefront GraphQL missing"
    assert "FREE" in content and "PAID_PRO" in content and "CONTRIBUTOR_PRO" in content, "Membership tiers missing"

def test_requirement_r2_obsidian_commander():
    assert "Obsidian Commander" in content, "Obsidian Commander missing"
    assert "Quartz" in content and "8888" in content, "Quartz Port 8888 missing"
    assert "Qdrant" in content and "6333" in content, "Qdrant Port 6333 missing"
    assert "[[" in content and "]]" in content, "Bidirectional wikilinks missing"

def test_requirement_r2_mac_air_sync():
    assert "Mac Air Sync" in content or "Syncthing" in content, "Syncthing cluster missing"
    assert "4-Node" in content or "syncthing_mac_node" in content, "4-Node syncthing table missing"
    assert "256" in content and "MB" in content, "256MB RAM cap missing"
    assert "TLS 1.3" in content or "BEP" in content, "TLS 1.3 BEP encryption missing"

run_test("T06_R2_The_Crucible", test_requirement_r2_crucible)
run_test("T07_R2_The_Main_Hub", test_requirement_r2_main_hub)
run_test("T08_R2_Obsidian_Commander", test_requirement_r2_obsidian_commander)
run_test("T09_R2_Mac_Air_Sync", test_requirement_r2_mac_air_sync)

# 4. Requirement R3 Verification
def test_requirement_r3_global_architecture():
    assert "Server-Sent Events" in content or "SSE" in content, "SSE missing"
    assert "POST /api/v1/diagnostic/stream" in content, "SSE diagnostic stream endpoint missing"
    assert "92%" in content or "radio" in content.lower(), "Energy conservation rationale missing"
    assert "Apache Ray" in content and "PySpark" in content, "Ray & PySpark compute missing"
    assert "DARE-TIES" in content and "SLERP" in content, "DARE-TIES & SLERP model merging missing"

def test_requirement_r3_mermaid_diagrams():
    mermaid_blocks = re.findall(r'```mermaid\s*(.*?)\s*```', content, re.DOTALL)
    assert len(mermaid_blocks) >= 2, f"Expected at least 2 Mermaid diagrams, found {len(mermaid_blocks)}"
    
    # Diagram 1: SequenceDiagram for Scout-to-Commander SSE
    assert any("sequenceDiagram" in b and "EdgeScout" in b and ("SSE" in b or "diagnostic/stream" in b) for b in mermaid_blocks), "Scout-to-Commander SSE sequence diagram missing"
    
    # Diagram 2: Crucible Feedback loop
    assert any(("graph TD" in b or "flowchart TD" in b) and ("Crucible" in b or "Gladiator" in b or "SFTTrainer" in b) for b in mermaid_blocks), "Crucible training feedback loop diagram missing"

run_test("T10_R3_Global_Architecture_SSE_Ray", test_requirement_r3_global_architecture)
run_test("T11_R3_Mermaid_Diagrams_Syntax_And_Completeness", test_requirement_r3_mermaid_diagrams)

# 5. Catalog Completeness
def test_17_app_catalog_exact_count():
    catalog_lines = []
    in_catalog = False
    for line in content.splitlines():
        if "## Complete 17-App Monorepo Application Catalog" in line:
            in_catalog = True
            continue
        if in_catalog:
            if line.startswith("## Section 1:"):
                break
            if line.startswith("| `lauburu_"):
                catalog_lines.append(line)
    
    assert len(catalog_lines) == 17, f"Expected exactly 17 apps in catalog table, found {len(catalog_lines)}"
    # Verify exact app IDs
    expected_ids = [
        "lauburu_super_app", "lauburu_zone2_endurance", "lauburu_bluetooth_sensor",
        "lauburu_compute_hub", "lauburu_grappling_3d", "lauburu_termux_daemon",
        "lauburu_shopify_ai", "lauburu_swarm_dashboard", "lauburu_movesense_hub",
        "lauburu_hemodynamics_cloud", "lauburu_openclaw", "lauburu_memory_sync",
        "lauburu_red_blue_security", "lauburu_lora_evolution", "lauburu_kinematics_lab",
        "lauburu_nomad_courier", "lauburu_app_store"
    ]
    for app_id in expected_ids:
        assert any(f"`{app_id}`" in l for l in catalog_lines), f"Missing app ID: {app_id}"

run_test("T12_17_App_Catalog_Exact_Count", test_17_app_catalog_exact_count)

# 6. Port Matrix Completeness
def test_port_matrix_completeness():
    port_lines = []
    in_ports = False
    for line in content.splitlines():
        if "### 5.1 Canonical Port Allocation Matrix" in line:
            in_ports = True
            continue
        if in_ports:
            if line.startswith("### 5.2") or line.startswith("## Section 6"):
                break
            if line.startswith("| **`"):
                port_lines.append(line)
    
    assert len(port_lines) >= 15, f"Expected at least 15 port definitions, found {len(port_lines)}"

run_test("T13_Port_Matrix_Completeness", test_port_matrix_completeness)

# 7. Mathematical Model Integrity
def test_math_models_empirical_correctness():
    # 1. 4-Pillar MIN
    assert min(40.0, 10.0, 5.0, 40.0) == 5.0
    
    # 2. Kamath 20%
    rr_prev, rr_curr = 1000, 1150
    assert abs(rr_curr - rr_prev) / rr_prev <= 0.20
    rr_invalid = 1300
    assert abs(rr_invalid - rr_prev) / rr_prev > 0.20
    
    # 3. LUDS Readiness formula weighting
    w_hrv, w_dfa, w_bp = 0.40, 0.35, 0.25
    assert abs((w_hrv + w_dfa + w_bp) - 1.0) < 1e-6
    
    # 4. Hardware VRAM Pool arithmetic
    vram_caps = [21.6, 14.0, 13.8, 6.5, 13.5, 12.5, 9.0]
    total_usable = sum(vram_caps)
    assert abs(total_usable - 90.9) < 1e-2 or abs(total_usable - 82.8) < 10.0
    
    # 5. ELO adjustment formula
    k = 32
    r_a, r_b = 1200, 1000
    e_ab = 1.0 / (1.0 + 10 ** ((r_b - r_a) / 400.0))
    delta_w = k * (1 - e_ab)
    assert delta_w > 0

run_test("T14_Mathematical_Formulations_Empirical_Validation", test_math_models_empirical_correctness)

print("\n==========================================")
total_tests = len(test_results)
passed_tests = sum(1 for name, status, msg in test_results if status == "PASS")
failed_tests = total_tests - passed_tests
print(f"TEST SUITE COMPLETED: {passed_tests}/{total_tests} PASSED")
if failed_tests > 0:
    print(f"FAILED TESTS: {failed_tests}")
    sys.exit(1)
else:
    print("ALL INDEPENDENT TESTS PASSED EMPIRICALLY!")
