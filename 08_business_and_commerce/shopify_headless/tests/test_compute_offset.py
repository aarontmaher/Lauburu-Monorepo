"""
Unit tests for ComputeOffsetCalculator (70% gross margin math & mesh power modeling).
"""

import pytest

from shopify_headless.services.compute_offset import ComputeOffsetCalculator


def test_task_cost_calculation():
    # 45 seconds task on 270W mesh
    # kW = 0.270
    # kWh = 0.270 * (45 / 3600) = 0.003375 kWh
    # Electricity @ $0.25/kWh = 0.00084375 AUD
    # Depreciation = 0.02 (heavy MoE)
    # Total = ~0.02084375 AUD
    cost_heavy = ComputeOffsetCalculator.calculate_task_cost(duration_seconds=45, is_heavy_moe=True)
    assert 0.020 < cost_heavy < 0.022

    cost_light = ComputeOffsetCalculator.calculate_task_cost(duration_seconds=45, is_heavy_moe=False)
    assert 0.005 < cost_light < 0.007


def test_calculate_required_credits():
    # Physical cost $0.02 AUD
    # At 70% gross margin: required revenue = 0.02 / (1 - 0.70) = 0.02 / 0.30 = $0.0667 USD
    # At $0.01/credit = 7 credits
    credits_needed = ComputeOffsetCalculator.calculate_required_credits(physical_cost=0.02, target_margin=0.70)
    assert credits_needed == 7

    # Zero/minimal cost should return at least 1 credit
    assert ComputeOffsetCalculator.calculate_required_credits(physical_cost=0.0001) >= 1


def test_calculate_subscription_gross_margin():
    # $29/mo plan with 10 hours (36,000s) compute
    # Mesh cost for 10 hours:
    # kWh = 0.270 * 10 = 2.7 kWh
    # Electricity = 2.7 * 0.25 = 0.675 AUD
    # Depreciation = 0.02 * 1 = 0.02 (single continuous run)
    # Total cost < $1.00 AUD
    # Margin on $29 should easily exceed 70%
    result = ComputeOffsetCalculator.calculate_subscription_gross_margin(
        monthly_price_usd=29.00,
        monthly_compute_seconds=36000,
        is_heavy_moe=True,
    )
    assert result["monthly_price_usd"] == 29.00
    assert result["target_70pct_met"] is True
    assert result["gross_margin_pct"] > 70.0


def test_estimate_max_monthly_tasks():
    # $29 plan, 70% margin -> $8.70 allowable cost
    # Single task ~ $0.0208 AUD
    # Max tasks ~ 417
    max_tasks = ComputeOffsetCalculator.estimate_max_monthly_tasks(
        monthly_price_usd=29.00,
        avg_task_sec=45,
        is_heavy_moe=True,
        target_margin=0.70,
    )
    assert max_tasks > 350
