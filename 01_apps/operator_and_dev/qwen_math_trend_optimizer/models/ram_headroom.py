"""
Closed-Form RAM Headroom Governor Equations.
============================================
Subsystem: 01_apps/operator_and_dev/qwen_math_trend_optimizer/models/ram_headroom.py
"""

from ..core.models import RamHeadroomProof

def compute_ram_safety_headroom(
    host_physical_ram_gb: float = 24.0,
    governor_ceiling_pct: float = 0.90,
    model_base_vram_gb: float = 14.50,
    batch_size: int = 2,
    lora_rank: int = 32,
    grad_accum: int = 1,
    context_tokens: int = 32768
) -> RamHeadroomProof:
    """
    Evaluates RAM safety headroom under 21.6 GB dynamic host ceiling:
    Headroom = Cap (21.6GB) - [Base + KV + Act] >= 2.50 GB
    """
    v_cap = round(host_physical_ram_gb * governor_ceiling_pct, 2)
    v_base = round(model_base_vram_gb, 2)
    v_kv = round((context_tokens / 32768.0) * 2.10, 2)
    v_act = round((batch_size * lora_rank * 0.02 * grad_accum) + 0.52, 2)
    v_total = round(v_base + v_kv + v_act, 2)
    v_headroom = round(v_cap - v_total, 2)

    is_safe = (v_headroom >= 2.50) and (v_total <= v_cap)
    status = (
        f"CERTIFIED_HEALTHY (Headroom: {v_headroom:.2f} GB)"
        if is_safe else
        f"REJECTED_OOM_RISK (Headroom: {v_headroom:.2f} GB < 2.50 GB)"
    )

    equation = f"Headroom = Cap ({v_cap}GB) - [Base ({v_base}GB) + KV ({v_kv}GB) + Act ({v_act}GB)] = {v_headroom:.2f}GB >= 2.50GB"

    return RamHeadroomProof(
        host_physical_ram_gb=host_physical_ram_gb,
        governor_ceiling_gb=v_cap,
        base_model_vram_gb=v_base,
        kv_cache_vram_gb=v_kv,
        activation_vram_gb=v_act,
        total_active_vram_gb=v_total,
        ram_headroom_gb=v_headroom,
        is_safe=is_safe,
        status=status,
        equation=equation
    )
