"""
Compute Offset and 70% Gross Margin Calculator.
Calculates the physical electricity and hardware depreciation costs of running the Lauburu 7-layer AI Mesh
and offsets them against Shopify SaaS subscription pricing and token credit quotas.
"""

import math
from typing import Any, Dict


class ComputeOffsetCalculator:
    """
    Empirical physical cost and gross margin engine for the Lauburu AI Mesh.
    Enforces a strict 70% gross margin target on all SaaS tiers.
    """

    ELECTRICITY_COST_PER_KWH: float = 0.25  # AUD
    MAC_MINI_POWER_W: float = 75.0
    MACBOOK_PRO_POWER_W: float = 90.0
    LINUX_NODE_POWER_W: float = 65.0
    NETWORK_OVERHEAD_W: float = 40.0

    TOTAL_MESH_POWER_W: float = (
        MAC_MINI_POWER_W + MACBOOK_PRO_POWER_W + LINUX_NODE_POWER_W + NETWORK_OVERHEAD_W
    )  # 270.0 W

    TARGET_GROSS_MARGIN: float = 0.70  # 70% target

    @classmethod
    def calculate_task_cost(
        cls,
        duration_seconds: int,
        is_heavy_moe: bool = True,
    ) -> float:
        """
        Calculates physical hardware power + depreciation cost for an AI inference or training task.
        """
        mesh_kw = cls.TOTAL_MESH_POWER_W / 1000.0
        kwh_consumed = mesh_kw * (duration_seconds / 3600.0)
        electricity_cost = kwh_consumed * cls.ELECTRICITY_COST_PER_KWH

        # Hardware depreciation per task ($0.02 for 70B MoE sharding, $0.005 for edge 3B)
        hardware_depreciation = 0.02 if is_heavy_moe else 0.005

        return electricity_cost + hardware_depreciation

    @classmethod
    def calculate_required_credits(
        cls,
        physical_cost: float,
        target_margin: float = 0.70,
        credit_value_usd: float = 0.01,
    ) -> int:
        """
        Converts physical cost to required SaaS credits to achieve target gross margin.
        Default assumption: 1 credit = $0.01 USD.
        """
        required_revenue = physical_cost / max(0.01, (1.0 - target_margin))
        credits_needed = math.ceil(required_revenue / credit_value_usd)
        return max(1, credits_needed)

    @classmethod
    def calculate_subscription_gross_margin(
        cls,
        monthly_price_usd: float,
        monthly_compute_seconds: int,
        is_heavy_moe: bool = True,
    ) -> Dict[str, Any]:
        """
        Evaluates the gross margin of a given monthly subscription price against expected compute load.
        """
        physical_cost = cls.calculate_task_cost(monthly_compute_seconds, is_heavy_moe=is_heavy_moe)
        gross_profit = monthly_price_usd - physical_cost
        margin_pct = (gross_profit / monthly_price_usd) if monthly_price_usd > 0 else 0.0

        return {
            "monthly_price_usd": monthly_price_usd,
            "monthly_compute_seconds": monthly_compute_seconds,
            "physical_cost_aud": round(physical_cost, 4),
            "gross_profit_usd": round(gross_profit, 4),
            "gross_margin_pct": round(margin_pct * 100.0, 2),
            "target_70pct_met": margin_pct >= cls.TARGET_GROSS_MARGIN,
        }

    @classmethod
    def estimate_max_monthly_tasks(
        cls,
        monthly_price_usd: float,
        avg_task_sec: int = 45,
        is_heavy_moe: bool = True,
        target_margin: float = 0.70,
    ) -> int:
        """
        Estimates the maximum number of tasks a subscriber can run per month while preserving the target gross margin.
        """
        single_task_cost = cls.calculate_task_cost(avg_task_sec, is_heavy_moe=is_heavy_moe)
        max_allowable_cost = monthly_price_usd * (1.0 - target_margin)
        if single_task_cost <= 0:
            return 0
        return int(max_allowable_cost // single_task_cost)
