"""
Multi-Transport Latency Proofs & Inverse-Variance Weighting.
===========================================================
Subsystem: 01_apps/operator_and_dev/qwen_math_trend_optimizer/models/latency_proofs.py
"""

from typing import Dict, List, Any
from ..core.models import LatencyProof

def compute_inverse_variance_weights(
    tb4_rtt: float = 0.27,
    wg_rtt: float = 1.85,
    wifi_rtt: float = 4.20
) -> List[LatencyProof]:
    """
    Computes closed-form inverse-variance packet striping weights:
    w_i = (1 / rtt_i^2) / sum(1 / rtt_j^2)
    """
    inv_tb4 = 1.0 / (max(tb4_rtt, 0.05) ** 2)
    inv_wg = 1.0 / (max(wg_rtt, 0.05) ** 2)
    inv_wifi = 1.0 / (max(wifi_rtt, 0.05) ** 2)
    total_inv = inv_tb4 + inv_wg + inv_wifi

    w_tb4 = round(inv_tb4 / total_inv, 4)
    w_wg = round(inv_wg / total_inv, 4)
    w_wifi = round(inv_wifi / total_inv, 4)

    return [
        LatencyProof("10Gbps Thunderbolt 4 DMA", tb4_rtt, w_tb4, is_optimal_primary=True),
        LatencyProof("Tailscale WireGuard L3 Mesh", wg_rtt, w_wg, is_optimal_primary=False),
        LatencyProof("Wi-Fi 7 Local MLO", wifi_rtt, w_wifi, is_optimal_primary=False),
    ]
