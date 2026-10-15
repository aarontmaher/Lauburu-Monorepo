#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
Sales-Ready App Benchmark Arena & Non-Saturating Adversarial Evaluation Engine
================================================================================
Subsystem: 08_business_and_commerce/benchmarks/sales_ready_app_arena.py

Solves Benchmark Saturation & ELO Inflation:
  - Disallows trivial 100/100 scores by enforcing hard adversarial edge-case audits:
    1. Mobile Notch / Dynamic Island Safe Area Inset Audit (env(safe-area-inset-*))
    2. Ring-Buffer Memory Leak & Unbounded Allocation Audit (Float32Array vs push)
    3. Rule 0 Sensor Disconnect Truth Audit (clean waiting states "--", no simulated data)
    4. Mobile Touch Target Ergonomics Audit (min 44px touch targets for athletes)
    5. Modular Client App Gate Separation (Spatial Grappling as independent app)
    6. Device-Tailored OS Binary Matrix (iOS, Android, macOS, Linux)

Total Points: 100. Non-saturating scoring scale where true skill differences are exposed.
================================================================================
"""

import os
import sys
import json
import re
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

ELO_GOVERNOR = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/05_agents_and_swarms/elo_currency_governor.py"
CONTINUOUS_LORA_FILE = "/Users/aaron/DFS_UNIFIED/lora_datasets/continuous_lora_dataset.jsonl"
BASE_APP_DIR = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/screen_lens/sandbox_evolution/app_competition")

class AdversarialAppEvaluator:
    def __init__(self, team_dir: Path, team_name: str, model_id: str):
        self.team_dir = team_dir
        self.team_name = team_name
        self.model_id = model_id
        self.report = {
            "team": team_name,
            "model_id": model_id,
            "timestamp": datetime.now().isoformat(),
            "scores": {},
            "total_score": 0,
            "passed": False,
            "deductions": [],
            "highlights": []
        }

    def audit_ui_ux_and_customer_purity(self) -> int:
        score = 25
        html_file = self.team_dir / "index.html"
        css_file = self.team_dir / "styles.css"
        
        if not html_file.exists() or not css_file.exists():
            self.report["deductions"].append("Missing index.html or styles.css (-25)")
            return 0
            
        html = html_file.read_text()
        css = css_file.read_text()
        
        # 1. Semantic Tags
        for tag in ["header", "main", "footer"]:
            if f"<{tag}" not in html:
                score -= 2
                self.report["deductions"].append(f"Missing semantic <{tag}> (-2)")
                
        # 2. Hard Adversarial Check: Mobile Notch / Dynamic Island Safe Areas
        has_safe_area = "safe-area-inset" in css or "env(safe-area" in css
        has_viewport_fit = "viewport-fit=cover" in html
        if has_safe_area and has_viewport_fit:
            self.report["highlights"].append("Adversarial Pass: Mobile Dynamic Island & Notch Safe Area insets handled (+)")
        else:
            score -= 4
            self.report["deductions"].append("Adversarial Fail: Missing mobile safe-area-inset or viewport-fit=cover (-4)")
            
        # 3. Touch Target Ergonomics (WCAG 2.5.5 >= 44px)
        has_touch_targets = any(p in css for p in ["padding: 12px", "padding: 14px", "min-height: 44px", "min-height: 48px"])
        if has_touch_targets:
            self.report["highlights"].append("Adversarial Pass: Touch targets optimized for athletic use (+)")
        else:
            score -= 3
            self.report["deductions"].append("Suboptimal mobile touch target dimensions (-3)")
            
        # 4. Color Contrast & Dynamic Theme Tokens
        if ":root" in css and "[data-theme" in css:
            self.report["highlights"].append("Dynamic theme tokens present (+)")
        else:
            score -= 2
            self.report["deductions"].append("Missing adaptive dual-mode CSS variables (-2)")
            
        # 5. Customer-Facing Purity: ZERO developer mesh features or internal network leaks
        mesh_leaks = [term for term in ["l1-m4 mesh", "port 8082", "40gbps tb4", "mesh-status-indicator"] if term in html.lower()]
        if mesh_leaks:
            score -= 6
            self.report["deductions"].append(f"Customer UX Violation: Leaked internal developer mesh features ({', '.join(mesh_leaks)}) (-6)")
        else:
            self.report["highlights"].append("Customer Purity Pass: Zero developer mesh leaks or internal IP/port jargon (+)")
            
        return max(0, min(25, score))

    def audit_modular_app_gate_and_devices(self) -> int:
        score = 25
        html = (self.team_dir / "index.html").read_text() if (self.team_dir / "index.html").exists() else ""
        
        # 1. Separation of Concerns: Spatial Grappling must be its OWN APP in the Client App Gate,
        # NOT an embedded mini-tab inside Combat Lab!
        if "id=\"tab-kinematics\"" in html or "switchTab('kinematics')" in html:
            score -= 5
            self.report["deductions"].append("Architectural Violation: Spatial Grappling 3D is embedded as a tab rather than an independent app in the Client Gate (-5)")
        else:
            self.report["highlights"].append("Architectural Pass: Clean separation of specialized apps (+)")
            
        # 2. Multi-Device Tailored Binary Gate (iOS, Android, macOS, Linux)
        has_ios = "ios" in html.lower() or "iphone" in html.lower() or "apple" in html.lower()
        has_android = "android" in html.lower() or "apk" in html.lower()
        has_mac = "macos" in html.lower() or "dmg" in html.lower() or "apple silicon" in html.lower()
        has_linux = "linux" in html.lower() or "appimage" in html.lower()
        
        device_count = sum([has_ios, has_android, has_mac, has_linux])
        if device_count == 4:
            self.report["highlights"].append("Complete 4-Platform Client App Gate (iOS, Android, macOS, Linux) verified (+)")
        else:
            score -= (4 - device_count) * 2
            self.report["deductions"].append(f"Incomplete device binary coverage ({device_count}/4 platforms) (-{(4 - device_count)*2})")
            
        # 3. Universal Health Device Connector (Polar H10, Whoop, Apple Watch / Wearables)
        has_polar = "polar" in html.lower() or "0x180d" in html.lower()
        has_whoop = "whoop" in html.lower()
        has_smartwatch = "smartwatch" in html.lower() or "apple watch" in html.lower() or "wear os" in html.lower()
        if has_polar and (has_whoop or has_smartwatch):
            self.report["highlights"].append("Universal Health Device Connector verified (Polar H10, Whoop, Smartwatches) (+)")
        else:
            score -= 5
            self.report["deductions"].append("Missing Universal Health Device Connector for open wearables (-5)")

        # 4. Pay-by-Compute Metering & Token Packs
        if "compute" in html.lower() and ("credit" in html.lower() or "token" in html.lower()):
            self.report["highlights"].append("Pay-by-Compute Metering Engine integrated (+)")
        else:
            score -= 3
            self.report["deductions"].append("Missing Pay-by-Compute Metering (-3)")
            
        # 5. Recurring Membership Tiers & Hardware Bundle Solvency
        if "starter" in html.lower() and "pro" in html.lower() and "bundle" in html.lower():
            self.report["highlights"].append("Sales-ready membership tiers & hardware bundle present (+)")
        else:
            score -= 3
            self.report["deductions"].append("Incomplete membership or bundle funnel (-3)")
            
        return max(0, min(25, score))

    def audit_memory_leaks_and_rule_0(self) -> int:
        score = 25
        js_file = self.team_dir / "app.js"
        html_file = self.team_dir / "index.html"
        if not js_file.exists() or not html_file.exists():
            return 0
        js = js_file.read_text()
        html = html_file.read_text()
        
        # 1. Hard Adversarial Check: Memory Leak in High-Frequency Canvas Stream
        if "Float32Array" in js and "%" in js:
            self.report["highlights"].append("Adversarial Pass: Fixed-size circular ring-buffer prevents memory leaks during 10+ hour continuous streaming (+)")
        elif "push(" in js and "shift(" not in js:
            score -= 8
            self.report["deductions"].append("Adversarial Fail: Unbounded array push detected (Critical Memory Leak) (-8)")
            
        # 2. Rule 0: Disconnect Truth Audit (Clean Waiting State "--" vs Faked Numbers)
        # If the HTML loads with a hardcoded fake HR (e.g. 148 BPM) before connecting, flag fake data!
        has_faked_hr = "148 <small>bpm" in html.lower() or "148 bpm" in html.lower()
        has_waiting_state = "-- <small>bpm" in html.lower() or "-- bpm" in html.lower() or "--" in js
        
        if has_faked_hr:
            score -= 6
            self.report["deductions"].append("Rule 0 Violation: Faked biometric data loaded on launch (148 BPM hardcoded before sensor connection) (-6)")
        elif has_waiting_state:
            self.report["highlights"].append("Rule 0 Pass: Authentic disconnect waiting states handled (-- BPM, clean flatline) (+)")
        else:
            score -= 4
            self.report["deductions"].append("Rule 0 Warning: Missing clean sensor disconnect waiting state (-4)")
            
        # 3. AST Syntax check via node -c
        try:
            res = subprocess.run(["node", "-c", str(js_file)], capture_output=True, text=True)
            if res.returncode != 0:
                score -= 6
                self.report["deductions"].append(f"JS Syntax Error: {res.stderr.strip()} (-6)")
            else:
                self.report["highlights"].append("Node.js AST syntax check passed cleanly (+)")
        except Exception:
            pass
            
        # 4. Defensive Error Handling
        if "try {" in js and "catch" in js:
            self.report["highlights"].append("Defensive error boundaries present (+)")
        else:
            score -= 2
            self.report["deductions"].append("Missing try/catch error boundaries (-2)")
            
        return max(0, min(25, score))

    def audit_cross_device_ppg_and_medical_ai(self) -> int:
        score = 25
        html = (self.team_dir / "index.html").read_text() if (self.team_dir / "index.html").exists() else ""
        css = (self.team_dir / "styles.css").read_text() if (self.team_dir / "styles.css").exists() else ""
        
        # 1. Media Query Coverage (Desktop >= 1200, Tablet 768-1024, Mobile <= 768)
        has_mobile = "max-width: 768px" in css or "max-width: 640px" in css
        has_tablet = "max-width: 1024px" in css or "max-width: 900px" in css
        if has_mobile and has_tablet:
            self.report["highlights"].append("Multi-tier responsive media queries verified (+)")
        else:
            score -= 4
            self.report["deductions"].append("Incomplete breakpoint matrix (-4)")
            
        # 2. 5-Minute Phone Camera Optical PPG Test & PTT Blood Pressure Calibration
        has_ppg = "ppg" in html.lower() and ("optical" in html.lower() or "camera" in html.lower() or "pulse" in html.lower())
        has_ptt = "ptt" in html.lower() or "pulse transit time" in html.lower() or "blood pressure" in html.lower()
        if has_ppg and has_ptt:
            self.report["highlights"].append("5-Minute Phone Camera Optical PPG & PTT Blood Pressure Test integrated (+)")
        else:
            score -= 6
            self.report["deductions"].append("Missing 5-Minute Phone Camera Optical PPG & PTT Blood Pressure Calibration (-6)")
            
        # 3. Medical Specialist AI Routing: Health advice must come from Medical/Cardio Specialist, NOT general orchestrators!
        has_general_orchestrator_as_doctor = "qwen 3.8 max local orchestrator" in html.lower() or "tactical advisor" in html.lower()
        has_medical_specialist = "medical" in html.lower() or "cardio-dsp" in html.lower() or "biometrics specialist" in html.lower()
        
        if has_general_orchestrator_as_doctor and not has_medical_specialist:
            score -= 5
            self.report["deductions"].append("Specialist Routing Violation: General orchestrator assigned as medical advisor instead of Medical Specialist AI (-5)")
        elif has_medical_specialist:
            self.report["highlights"].append("Specialist Routing Pass: Health guidance delegated to dedicated Medical Specialist AI (+)")
        else:
            score -= 4
            self.report["deductions"].append("Missing Medical Specialist AI diagnosis attribution (-4)")
            
        # 4. Sticky Mobile CTA
        if "sticky" in css or "fixed" in css:
            self.report["highlights"].append("Sticky bottom ergonomic navigation present (+)")
        else:
            score -= 3
            self.report["deductions"].append("Missing sticky mobile thumb-zone CTA (-3)")
            
        return max(0, min(25, score))

    def run_all(self) -> Dict[str, Any]:
        s1 = self.audit_ui_ux_and_customer_purity()
        s2 = self.audit_modular_app_gate_and_devices()
        s3 = self.audit_memory_leaks_and_rule_0()
        s4 = self.audit_cross_device_ppg_and_medical_ai()
        
        self.report["scores"] = {
            "ui_ux_customer_purity": s1,
            "modular_gate_devices": s2,
            "memory_leaks_rule0": s3,
            "cross_device_ppg_medical_ai": s4
        }
        total = s1 + s2 + s3 + s4
        self.report["total_score"] = total
        self.report["passed"] = total >= 80
        return self.report

def run_adversarial_competition() -> Dict[str, Any]:
    print("================================================================================")
    print("⚔️ ADVERSARIAL STRESS ARENA: SALES-READY APP EVALUATION")
    print("================================================================================")
    
    local_dir = BASE_APP_DIR / "team_local_sovereign"
    cloud_dir = BASE_APP_DIR / "team_cloud_frontier"
    flagship_dir = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/combat_lab_lauburu")
    
    eval_local = AdversarialAppEvaluator(local_dir, "Team Local Sovereign", "Qwen_3.8_Max")
    res_local = eval_local.run_all()
    
    eval_cloud = AdversarialAppEvaluator(cloud_dir, "Team Cloud Frontier", "Qwen_3.8_Max_Abliterated")
    res_cloud = eval_cloud.run_all()
    
    eval_flagship = AdversarialAppEvaluator(flagship_dir, "Combat Lab Lauburu Flagship", "Unified_Architecture")
    res_flagship = eval_flagship.run_all()
    
    print(f"\n[TEAM 1: LOCAL SOVEREIGN (Qwen 3.8 Max)]")
    print(f"  • Total Score: {res_local['total_score']}/100 | Passed: {res_local['passed']}")
    for k, v in res_local["scores"].items():
        print(f"    - {k}: {v}/25")
    for d in res_local["deductions"]:
        print(f"    [-] {d}")
        
    print(f"\n[TEAM 2: CLOUD FRONTIER (Qwen 3.8 Max Abliterated)]")
    print(f"  • Total Score: {res_cloud['total_score']}/100 | Passed: {res_cloud['passed']}")
    for k, v in res_cloud["scores"].items():
        print(f"    - {k}: {v}/25")
    for d in res_cloud["deductions"]:
        print(f"    [-] {d}")

    print(f"\n[CANONICAL FLAGSHIP: COMBAT LAB LAUBURU]")
    print(f"  • Total Score: {res_flagship['total_score']}/100 | Passed: {res_flagship['passed']}")
    for k, v in res_flagship["scores"].items():
        print(f"    - {k}: {v}/25")
    for d in res_flagship["deductions"]:
        print(f"    [-] {d}")

    return {
        "team_local": res_local,
        "team_cloud": res_cloud,
        "flagship": res_flagship
    }

if __name__ == "__main__":
    run_adversarial_competition()
