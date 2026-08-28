#!/usr/bin/env python3
"""
E2E Test Helpers & Reference Implementation Models
Lauburu Monorepo Unification & Tri-Vault Storage Synchronization
"""

import os
import re
import json
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

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
        free_bytes = shutil.disk_usage(str(PROJECT_ROOT)).free
        disk_free_gb = free_bytes / (1024 ** 3)
    except Exception:
        disk_free_gb = 0.0
        
    git_ok = (PROJECT_ROOT / '.git').exists()
    no_lock = not (PROJECT_ROOT / '.git' / 'index.lock').exists()
    
    healthy = obsidian_ok and pyspark_ok and (disk_free_gb >= 10.0) and git_ok and no_lock
    return healthy, {
        'obsidian_ok': obsidian_ok,
        'pyspark_ok': pyspark_ok,
        'disk_free_gb': round(disk_free_gb, 2),
        'git_ok': git_ok,
        'no_index_lock': no_lock,
        'is_healthy': healthy
    }

def scan_all_symlinks(root: Path, max_depth: int = 5) -> List[Dict[str, Any]]:
    """Scans directory for symlinks and analyzes their target health and relative nature."""
    symlinks = []
    for dirpath, dirnames, filenames in os.walk(str(root)):
        # Calculate current depth relative to root
        rel_dir = os.path.relpath(dirpath, str(root))
        depth = 0 if rel_dir == '.' else len(rel_dir.split(os.sep))
        if depth > max_depth:
            continue
            
        # Check files
        for name in filenames + dirnames:
            full_path = os.path.join(dirpath, name)
            if os.path.islink(full_path):
                raw_target = os.readlink(full_path)
                is_relative = not os.path.isabs(raw_target)
                target_exists = os.path.exists(full_path)
                symlinks.append({
                    'path': full_path,
                    'raw_target': raw_target,
                    'is_relative': is_relative,
                    'target_exists': target_exists,
                    'is_broken': not target_exists
                })
    return symlinks

def extract_wikilinks(text: str) -> List[str]:
    """Extracts all [[Wikilink]] targets from markdown text."""
    pattern = r'\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]'
    matches = re.findall(pattern, text)
    return [m.strip() for m in matches if m.strip()]

def validate_jsonl_record(line: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """Validates a single line from a LoRA training dataset."""
    stripped = line.strip()
    if not stripped:
        return False, None, 'EMPTY_LINE'
    try:
        data = json.loads(stripped)
        if not isinstance(data, dict):
            return False, None, 'NOT_A_DICT'
        # Check for standard instruction or prompt format
        has_alpaca = 'instruction' in data and ('output' in data or 'response' in data)
        has_sharegpt = 'conversations' in data or 'messages' in data
        has_prompt = 'prompt' in data and ('response' in data or 'completion' in data)
        has_telemetry = 'timestamp' in data or 'metric' in data or 'task_id' in data or 'verdict' in data
        if has_alpaca or has_sharegpt or has_prompt or has_telemetry:
            return True, data, None
        return True, data, None # Valid JSON dict
    except json.JSONDecodeError as e:
        return False, None, f'JSON_DECODE_ERROR: {str(e)}'

def reference_pan_tompkins_detector(ecg_signal: List[float], fs: int = 512) -> Dict[str, Any]:
    """
    Deterministic Reference Pan-Tompkins QRS detector.
    Stages: Bandpass Filter -> Derivative -> Squaring -> Moving Window Integration -> Thresholding.
    """
    if not ecg_signal or len(ecg_signal) < int(fs * 0.5):
        return {
            'qrs_count': 0,
            'heart_rate_bpm': None,
            'qrs_indices': [],
            'status': 'INSUFFICIENT_DATA'
        }
        
    n = len(ecg_signal)
    
    # 1. Bandpass filter simulation (High pass + Low pass differences)
    # Simple 5-point moving average difference
    b_filtered = []
    for i in range(n):
        val = (ecg_signal[i] - ecg_signal[i-4]) if i >= 4 else 0.0
        b_filtered.append(val)
        
    # 2. Five-point derivative filter: y[n] = (2x[n] + x[n-1] - x[n-3] - 2x[n-4]) / 8
    derivative = [0.0] * n
    for i in range(4, n):
        derivative[i] = (2.0 * b_filtered[i] + b_filtered[i-1] - b_filtered[i-3] - 2.0 * b_filtered[i-4]) / 8.0
        
    # 3. Squaring function: y[n] = (x[n])^2
    squared = [x * x for x in derivative]
    
    # 4. Moving Window Integration (window ~ 150ms)
    window_size = max(1, int(0.150 * fs))
    integrated = [0.0] * n
    current_sum = 0.0
    for i in range(n):
        current_sum += squared[i]
        if i >= window_size:
            current_sum -= squared[i - window_size]
        integrated[i] = current_sum / window_size
        
    # 5. Adaptive Thresholding & Peak Search
    mean_energy = sum(integrated) / max(1, n)
    threshold = mean_energy * 1.5
    
    qrs_peaks = []
    min_refractory = int(0.200 * fs) # 200ms refractory period
    last_peak = -min_refractory
    
    for i in range(1, n - 1):
        if integrated[i] > threshold and integrated[i] > integrated[i-1] and integrated[i] >= integrated[i+1]:
            if (i - last_peak) >= min_refractory:
                qrs_peaks.append(i)
                last_peak = i
                
    qrs_count = len(qrs_peaks)
    duration_sec = n / fs
    if qrs_count >= 2 and duration_sec > 0:
        hr = (qrs_count / duration_sec) * 60.0
    else:
        hr = None
        
    return {
        'qrs_count': qrs_count,
        'heart_rate_bpm': round(hr, 1) if hr is not None else None,
        'qrs_indices': qrs_peaks,
        'status': 'HEALTHY' if qrs_count > 0 else 'NO_QRS_DETECTED'
    }

def reference_dfa_alpha1(rr_intervals_ms: List[float]) -> Dict[str, Any]:
    """
    Reference Detrended Fluctuation Analysis (DFA-alpha1) for heart rate variability.
    Short-term fractal scaling exponent (4 to 16 beats).
    """
    if not rr_intervals_ms or len(rr_intervals_ms) < 16:
        return {
            'alpha1': None,
            'status': 'INSUFFICIENT_DATA',
            'aerobic_zone': 'UNKNOWN'
        }
        
    import math
    
    # 1. Integrate the profile
    mean_rr = sum(rr_intervals_ms) / len(rr_intervals_ms)
    y = []
    cum = 0.0
    for r in rr_intervals_ms:
        cum += (r - mean_rr)
        y.append(cum)
        
    # 2. Fluctuation F(n) for box sizes 4 to 16
    box_sizes = [4, 6, 8, 12, 16]
    log_n = []
    log_fn = []
    
    for box in box_sizes:
        num_boxes = len(y) // box
        if num_boxes == 0:
            continue
        squared_errors = []
        for b in range(num_boxes):
            chunk = y[b * box : (b + 1) * box]
            # Linear trend fitting
            x_vals = list(range(box))
            x_mean = sum(x_vals) / box
            y_mean = sum(chunk) / box
            
            num = sum((x_vals[i] - x_mean) * (chunk[i] - y_mean) for i in range(box))
            den = sum((x_vals[i] - x_mean) ** 2 for i in range(box))
            slope = num / den if den != 0 else 0.0
            intercept = y_mean - slope * x_mean
            
            for i in range(box):
                fitted = slope * x_vals[i] + intercept
                err = chunk[i] - fitted
                squared_errors.append(err * err)
                
        if squared_errors:
            f_n = math.sqrt(sum(squared_errors) / len(squared_errors))
            if f_n > 0:
                log_n.append(math.log(box))
                log_fn.append(math.log(f_n))
                
    # 3. Linear regression on log(n) vs log(F(n)) -> slope = alpha1
    if len(log_n) >= 3:
        x_mean = sum(log_n) / len(log_n)
        y_mean = sum(log_fn) / len(log_fn)
        num = sum((log_n[i] - x_mean) * (log_fn[i] - y_mean) for i in range(len(log_n)))
        den = sum((log_n[i] - x_mean) ** 2 for i in range(len(log_n)))
        alpha1 = num / den if den != 0 else 1.0
        
        # Zone 2 threshold: alpha1 ~ 0.75 is aerobic threshold
        if alpha1 >= 0.75:
            zone = 'ZONE_2_AEROBIC'
        elif alpha1 >= 0.5:
            zone = 'ZONE_3_TEMPO'
        else:
            zone = 'ZONE_4_5_ANAEROBIC'
            
        return {
            'alpha1': round(alpha1, 3),
            'status': 'VALID',
            'aerobic_zone': zone
        }
        
    return {
        'alpha1': 1.0,
        'status': 'FALLBACK_ESTIMATE',
        'aerobic_zone': 'ZONE_2_AEROBIC'
    }
