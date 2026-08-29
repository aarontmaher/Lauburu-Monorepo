#!/usr/bin/env python3
"""
E2E Test Helpers & Reference Implementation Models
Lauburu Monorepo — Unified Front-Facing App Architecture & Multi-Mode Game Arena
================================================================================
Provides reference models, mathematical validators, OPML graph parsers,
PWA inspectors, and airgap boundary verifiers for all 16 features in PROJECT.md.
"""

import os
import re
import math
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional, Sequence, Union

PROJECT_ROOT = Path('/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo')
LORA_DATASETS_ROOT = Path('/Users/aaron/DFS_UNIFIED/lora_datasets')
TEAMWORK_PROJECTS_ROOT = Path('/Users/aaron/teamwork_projects')

CANONICAL_MODULES = [
    '00_core_infrastructure',
    '01_apps',
    '02_ai_models_and_inference',
    '03_biometrics_and_telemetry',
    '04_data_and_memory',
    '05_agents_and_swarms',
    '06_scripts_and_tooling',
    '07_docs_and_architecture',
    '08_business_and_commerce',
    '09_app_store_and_release',
    '10_spatial_grappling_kinematics',
    '11_security_and_governance',
    '12_continuous_lora_evolution'
]


def get_project_root() -> Path:
    return PROJECT_ROOT


def get_canonical_modules() -> List[str]:
    return CANONICAL_MODULES


def is_storage_healthy() -> Tuple[bool, Dict[str, Any]]:
    """Validates the Tri-Vault storage invariants (<3ms fast-path)."""
    obs_dir = PROJECT_ROOT / 'obsidian_vault'
    lora_dir = LORA_DATASETS_ROOT
    data_mem_dir = PROJECT_ROOT / '04_data_and_memory'
    
    obsidian_ok = obs_dir.is_dir()
    pyspark_ok = lora_dir.is_dir() or data_mem_dir.is_dir()
    
    try:
        import shutil
        free_bytes = shutil.disk_usage(str(PROJECT_ROOT)).free
        disk_free_gb = free_bytes / (1024 ** 3)
    except Exception:
        disk_free_gb = 0.0
        
    git_ok = (PROJECT_ROOT / '.git').exists()
    no_lock = not (PROJECT_ROOT / '.git' / 'index.lock').exists()
    
    healthy = obsidian_ok and pyspark_ok and (disk_free_gb >= 5.0) and git_ok and no_lock
    return healthy, {
        'obsidian_ok': obsidian_ok,
        'pyspark_ok': pyspark_ok,
        'disk_free_gb': round(disk_free_gb, 2),
        'git_ok': git_ok,
        'no_index_lock': no_lock,
        'is_healthy': healthy
    }


# ============================================================================
# F1: PWA & SERVICE WORKER HELPERS
# ============================================================================

def validate_pwa_manifest(manifest_path: Path) -> Tuple[bool, Dict[str, Any], List[str]]:
    """Validates standard W3C Web App Manifest fields."""
    errors = []
    if not manifest_path.exists():
        return False, {}, [f"Manifest file not found at {manifest_path}"]
    
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        return False, {}, [f"Invalid JSON manifest: {e}"]
    
    required_fields = ['name', 'short_name', 'start_url', 'display', 'icons']
    for req in required_fields:
        if req not in data:
            errors.append(f"Missing required manifest field: {req}")
            
    if 'display' in data and data['display'] not in ['standalone', 'fullscreen', 'minimal-ui', 'browser']:
        errors.append(f"Invalid display mode: {data['display']}")
        
    if 'icons' in data:
        if not isinstance(data['icons'], list) or len(data['icons']) == 0:
            errors.append("Icons field must be a non-empty array")
            
    return len(errors) == 0, data, errors


# ============================================================================
# F2: OPML & 3D TATAMI KINEMATICS GRAPH HELPERS
# ============================================================================

def parse_grappling_opml(opml_path: Path) -> Dict[str, Any]:
    """Parses grappling.opml and extracts node hierarchy and total node count."""
    if not opml_path.exists():
        return {'total_nodes': 0, 'root_nodes': [], 'categories': {}, 'max_depth': 0}
    
    try:
        tree = ET.parse(str(opml_path))
        root = tree.getroot()
        body = root.find('body')
        if body is None:
            return {'total_nodes': 0, 'root_nodes': [], 'categories': {}, 'max_depth': 0}
        
        all_nodes = []
        categories = {}
        
        def traverse(element: ET.Element, depth: int, parent_text: str):
            for child in element.findall('outline'):
                text = child.get('text', '') or child.get('title', '')
                node_type = child.get('type', 'node')
                node_info = {
                    'text': text,
                    'type': node_type,
                    'depth': depth,
                    'parent': parent_text,
                    'attributes': child.attrib
                }
                all_nodes.append(node_info)
                if depth == 1:
                    categories[text] = categories.get(text, 0) + 1
                traverse(child, depth + 1, text)

        traverse(body, 1, 'ROOT')
        max_depth = max((n['depth'] for n in all_nodes), default=0)
        return {
            'total_nodes': len(all_nodes),
            'nodes': all_nodes,
            'categories': categories,
            'max_depth': max_depth
        }
    except Exception as e:
        return {'total_nodes': 0, 'error': str(e), 'nodes': []}


# ============================================================================
# F3: WCAG 2.1 AA COLOR CONTRAST & ACCESSIBILITY HELPERS
# ============================================================================

def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join([c*2 for c in hex_color])
    return int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)


def relative_luminance(r: int, g: int, b: int) -> float:
    def srgb_to_lin(val: int) -> float:
        c = val / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * srgb_to_lin(r) + 0.7152 * srgb_to_lin(g) + 0.0722 * srgb_to_lin(b)


def calculate_contrast_ratio(hex1: str, hex2: str) -> float:
    """Calculates WCAG 2.1 contrast ratio between two hex colors."""
    r1, g1, b1 = hex_to_rgb(hex1)
    r2, g2, b2 = hex_to_rgb(hex2)
    l1 = relative_luminance(r1, g1, b1)
    l2 = relative_luminance(r2, g2, b2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return round((lighter + 0.05) / (darker + 0.05), 2)


# ============================================================================
# F4 & F10: AIRGAP & ZERO-MOCK VALIDATORS
# ============================================================================

def inspect_egress_payload_airgap_compliance(payload: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Asserts that NO raw biometric data (ECG arrays, raw microvolts, raw optical PPG waveforms,
    microsecond RR arrays) exists in outbound cloud payloads.
    """
    violations = []
    raw_forbidden_keys = [
        'raw_ecg', 'raw_ecg_samples', 'ecg_microvolts', 'raw_ppg', 'ppg_samples',
        'raw_optical_stream', 'unfiltered_rr_intervals', 'raw_waveform'
    ]
    
    def scan_dict(d: Any, path: str = ""):
        if isinstance(d, dict):
            for k, v in d.items():
                curr_path = f"{path}.{k}" if path else k
                if k.lower() in raw_forbidden_keys:
                    violations.append(f"Forbidden raw biometric key '{curr_path}' present in egress payload")
                if isinstance(v, list) and len(v) > 20 and all(isinstance(x, (int, float)) for x in v):
                    # Check for large raw continuous telemetry arrays
                    if any(term in k.lower() for term in ['ecg', 'ppg', 'pulse', 'lead', 'wave']):
                        violations.append(f"Raw continuous numeric biometric array detected at '{curr_path}' ({len(v)} elements)")
                scan_dict(v, curr_path)
        elif isinstance(d, list):
            for i, item in enumerate(d):
                scan_dict(item, f"{path}[{i}]")
                
    scan_dict(payload)
    return len(violations) == 0, violations


# ============================================================================
# F5, F6, F7, F8, F9: REFERENCE BIOMETRICS DSP & CARDIORESPIRATORY MATH
# ============================================================================

def generate_synthetic_synthetic_ecg_beat(fs: int = 512, bpm: float = 60.0, duration_sec: float = 5.0) -> List[float]:
    """Generates a reference physiological ECG waveform for algorithm verification."""
    total_samples = int(fs * duration_sec)
    signal = [0.0] * total_samples
    samples_per_beat = int((60.0 / bpm) * fs)
    
    for b_start in range(int(0.2 * fs), total_samples - samples_per_beat, samples_per_beat):
        # P wave
        p_peak = b_start + int(0.12 * fs)
        # Q wave
        q_peak = b_start + int(0.18 * fs)
        # R peak (sharp +1.5 mV)
        r_peak = b_start + int(0.20 * fs)
        # S wave
        s_peak = b_start + int(0.22 * fs)
        # T wave
        t_peak = b_start + int(0.35 * fs)
        
        for i in range(max(0, b_start), min(total_samples, b_start + samples_per_beat)):
            t_rel = (i - b_start) / fs
            # P wave gaussian
            p_val = 0.15 * math.exp(-((i - p_peak) ** 2) / (2 * (0.02 * fs) ** 2))
            # QRS complex
            q_val = -0.15 * math.exp(-((i - q_peak) ** 2) / (2 * (0.01 * fs) ** 2))
            r_val = 1.50 * math.exp(-((i - r_peak) ** 2) / (2 * (0.012 * fs) ** 2))
            s_val = -0.25 * math.exp(-((i - s_peak) ** 2) / (2 * (0.01 * fs) ** 2))
            # T wave
            t_val = 0.30 * math.exp(-((i - t_peak) ** 2) / (2 * (0.04 * fs) ** 2))
            
            signal[i] += (p_val + q_val + r_val + s_val + t_val)
            
    return signal


def reference_pan_tompkins_qrs(ecg_signal: Sequence[float], fs: int = 512) -> Tuple[List[int], List[float]]:
    """Reference Pan-Tompkins 1985 implementation."""
    if not ecg_signal or len(ecg_signal) < int(fs * 0.5):
        return [], []
    
    n = len(ecg_signal)
    # Bandpass difference filter
    filtered = [0.0] * n
    for i in range(2, n - 2):
        filtered[i] = ecg_signal[i] - 0.5 * (ecg_signal[i - 2] + ecg_signal[i + 2])
        
    # 5-point derivative
    deriv = [0.0] * n
    scale = fs / 8.0
    for i in range(2, n - 2):
        deriv[i] = (-filtered[i - 2] - 2.0 * filtered[i - 1] + 2.0 * filtered[i + 1] + filtered[i + 2]) * scale / fs
        
    # Squaring
    squared = [x * x for x in deriv]
    
    # 150ms MWI
    mwi_win = max(2, int(0.150 * fs))
    mwi = [0.0] * n
    curr_sum = sum(squared[:min(mwi_win, n)])
    for i in range(n):
        if i >= mwi_win:
            curr_sum += squared[i] - squared[i - mwi_win]
        elif i > 0:
            curr_sum += squared[i]
        mwi[i] = curr_sum / float(min(i + 1, mwi_win))
        
    # Find peaks above threshold
    threshold = max(mwi) * 0.30 if mwi else 0.0
    peaks = []
    refractory = int(0.200 * fs)
    last_p = -refractory
    
    for i in range(1, n - 1):
        if mwi[i] > threshold and mwi[i] > mwi[i - 1] and mwi[i] >= mwi[i + 1]:
            if i - last_p >= refractory:
                # Find R apex in raw signal
                s_start = max(0, i - mwi_win)
                s_end = min(n, i + mwi_win)
                r_apex = max(range(s_start, s_end), key=lambda idx: ecg_signal[idx])
                peaks.append(r_apex)
                last_p = r_apex
                
    rr_intervals = []
    for i in range(1, len(peaks)):
        rr_ms = ((peaks[i] - peaks[i - 1]) / float(fs)) * 1000.0
        if 250.0 <= rr_ms <= 2200.0:
            rr_intervals.append(round(rr_ms, 1))
            
    return peaks, rr_intervals


def reference_kamath_artifact_filter(rr_intervals: Sequence[float], threshold_pct: float = 20.0) -> Tuple[List[float], int]:
    """Kamath 2004 20% clinical RR artifact filter."""
    if not rr_intervals or len(rr_intervals) < 2:
        return [float(x) for x in (rr_intervals or [])], 0
        
    thresh = threshold_pct / 100.0
    cleaned = [float(rr_intervals[0])]
    artifacts = 0
    
    for i in range(1, len(rr_intervals)):
        prev = cleaned[-1]
        curr = float(rr_intervals[i])
        if prev > 0 and (abs(curr - prev) / prev) <= thresh:
            cleaned.append(curr)
        else:
            artifacts += 1
            cleaned.append(prev)  # Zero-order hold interpolation
            
    return cleaned, artifacts


def reference_calculate_rmssd(rr_intervals: Sequence[float]) -> Optional[float]:
    if not rr_intervals or len(rr_intervals) < 2:
        return None
    diffs = [float(rr_intervals[i]) - float(rr_intervals[i - 1]) for i in range(1, len(rr_intervals))]
    sum_sq = sum(d * d for d in diffs)
    return round(math.sqrt(sum_sq / float(len(rr_intervals) - 1)), 2)


def reference_calculate_ptt_bp(ptt_ms: Optional[float], hr_bpm: Optional[float]) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """Reference Hemodynamic PTT Blood Pressure Inversion formula."""
    if ptt_ms is None or ptt_ms <= 0:
        return None, None, None
    delta_ptt = 200.0 - float(ptt_ms)
    hr_adj = ((float(hr_bpm) - 70.0) * 0.15) if hr_bpm else 0.0
    sbp = round(max(80.0, min(220.0, 120.0 + (delta_ptt * 0.45) + hr_adj)), 1)
    dbp = round(max(50.0, min(130.0, 80.0 + (delta_ptt * 0.25) + (hr_adj * 0.5))), 1)
    map_val = round((sbp + 2.0 * dbp) / 3.0, 1)
    return sbp, dbp, map_val


def reference_uth_sorensen_vo2max(hr_max: float, hr_rest: float) -> float:
    """Uth-Sørensen formula: VO2max = 15.3 * (HR_max / HR_rest)."""
    return round(15.3 * (float(hr_max) / max(float(hr_rest), 35.0)), 1)


# ============================================================================
# F11, F12, F13: SMOLAGENTS & ARENA GAME MODES
# ============================================================================

VALID_GAME_MODES = [
    "EDGE_ORCHESTRATOR_CLASSIC",
    "SMOLAGENTS_PYTHON_DUEL",
    "MULTI_MODEL_AGI_SWARM",
    "AIRGAP_MESH_VS_CLOUD_CHAOS"
]

def validate_tactical_objective_schema(payload: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validates the Tactical Intent Summary schema required by PROJECT.md."""
    errors = []
    if not isinstance(payload, dict):
        return False, ["Payload is not a dictionary"]
        
    summary = payload.get("tactical_intent_summary") or payload
    required_keys = ["red_faction_intent", "blue_faction_intent", "user_biological_state", "combat_narrative"]
    for rk in required_keys:
        if rk not in summary or not isinstance(summary[rk], str) or len(summary[rk].strip()) == 0:
            errors.append(f"Missing or invalid required summary key: {rk}")
            
    return len(errors) == 0, errors
