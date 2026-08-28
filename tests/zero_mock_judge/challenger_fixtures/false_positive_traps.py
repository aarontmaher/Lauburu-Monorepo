"""
Adversarial Fixture Suite 3: False Positive Traps (Python)
==========================================================
Legitimate production code containing mathematical scaling, DSP algorithms,
physics formulas, hardware unit conversions, and error handlers that MUST NOT
be flagged as mock violations by ZeroMockStaticJudge.
"""

import math
from typing import Dict, Any, List, Optional

# Trap 1: Legitimate Signal Processing & DSP Normalization
def calculate_nyquist_frequency(sampling_rate_hz: float) -> float:
    """Standard Shannon-Nyquist sampling theorem limit (fs * 0.5)."""
    return sampling_rate_hz * 0.5

def calculate_fft_bin_frequency(bin_index: int, sample_rate: float, n_fft: int) -> float:
    """Standard discrete Fourier transform frequency bin center."""
    return (bin_index * sample_rate) / float(n_fft)

def calculate_snr_db(signal_power: float, noise_power: float) -> float:
    """Decibel ratio calculation: 10 * log10(P_signal / P_noise)."""
    if noise_power <= 0:
        return 0.0
    return 10.0 * math.log10(signal_power / noise_power)

def exponential_moving_average(current_sample: float, previous_ema: float, alpha: float = 0.2) -> float:
    """Exponential smoothing: alpha * current + (1 - alpha) * previous."""
    return alpha * current_sample + (1.0 - alpha) * previous_ema

# Trap 2: Legitimate Physics & Kinematics (Tatami Grappling World Model)
def calculate_joint_torque(force_newtons: float, lever_arm_meters: float, angle_rad: float) -> float:
    """Physics joint torque: tau = F * r * sin(theta)."""
    return force_newtons * lever_arm_meters * math.sin(angle_rad)

def calculate_angular_velocity(angle_delta_rad: float, dt_seconds: float) -> float:
    """Angular velocity: omega = delta_theta / dt."""
    if dt_seconds <= 0:
        return 0.0
    return angle_delta_rad / dt_seconds

# Trap 3: Legitimate Unit Conversions
def convert_bytes_to_mbps(byte_count: int, duration_sec: float) -> float:
    """Standard bit/byte rate conversion: (bytes * 8) / (sec * 1e6)."""
    if duration_sec <= 0:
        return 0.0
    return (byte_count * 8) / (duration_sec * 1000000.0)

def convert_seconds_to_ms(seconds: float) -> float:
    """Standard time conversion: sec * 1000."""
    return seconds * 1000.0

def convert_hours_to_seconds(hours: float) -> float:
    """Standard time conversion: hours * 3600."""
    return hours * 3600.0

# Trap 4: Legitimate Error Handlers Returning Explicit Null / Offline States
def query_node_telemetry_safe(node_ip: str) -> Dict[str, Any]:
    try:
        raise ConnectionRefusedError(f"Node {node_ip} offline")
    except Exception as e:
        # Truthful null/offline return
        return {
            "status": "OFFLINE",
            "node_ip": node_ip,
            "latency_ms": None,
            "throughput_mbps": 0.0,
            "devices_active": 0,
            "error": str(e)
        }

# Trap 5: Static Device Configuration Object (Metadata, Ports, Topology)
STATIC_TOPOLOGY_CONFIG = {
    "cluster_name": "lauburu_alpha",
    "head_node": {
        "id": "node_head",
        "name": "Linux Head Node",
        "role": "router",
        "port": 5050,
        "cores": 16,
        "total_memory_mb": 65536
    }
}
