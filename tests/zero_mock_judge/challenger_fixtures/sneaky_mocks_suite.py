"""
Adversarial Fixture Suite 1: Sneaky Mock Patterns (Python)
==========================================================
Constructed by Challenger 1 to stress-test AST scanner evasion vectors:
1. Arithmetic / bitwise / algebraic obfuscation of synthetic multipliers (single_tp * 2.0).
2. Indirect string concatenation / formatting / template formatting for latency strings.
3. Computed / dictionary comprehension fallback payloads in except blocks.
4. Nested fallback structures and class-based mock encapsulation.
5. Obfuscated simulation comments and indirect random calls.
"""

import math
import sys

# Vector 1: Obfuscated synthetic math multipliers
def sneaky_tp_multiplier_bitwise(single_tp):
    # Left shift equivalent to * 2 (single_tp * 2.0)
    return int(single_tp) << 1

def sneaky_tp_multiplier_div(single_tp):
    # Division by 0.5 equivalent to * 2.0
    return single_tp / 0.5

def sneaky_tp_multiplier_algebraic(single_tp):
    # single_tp * (1.5 + 0.5)
    return single_tp * (1.5 + 0.5)

def sneaky_tp_multiplier_variable_factor(single_tp):
    # Decoupled scaling constant
    scale_factor = 2.0
    return single_tp * scale_factor

def sneaky_tp_multiplier_exponent(single_tp):
    # single_tp * (2 ** 1)
    return single_tp * (2 ** 1)

# Vector 2: String formatting / indirect latency construction
def sneaky_hardcoded_latency_fstring():
    ms_val = 0.28
    return {
        "id": "stealth_node_1",
        "latency": f"{ms_val}ms (DMA)",
        "status": "APPLIED"
    }

def sneaky_hardcoded_latency_concat():
    return {
        "id": "stealth_node_2",
        "latency": "0." + "28ms (DMA)",
        "status": "ONLINE"
    }

def sneaky_hardcoded_latency_comprehension():
    keys = ["latency", "status"]
    vals = ["0.28ms", "ACTIVE"]
    return {k: v for k, v in zip(keys, vals)}

# Vector 3: Nested & indirect fallback dictionary in except blocks
def sneaky_except_fallback_deep_nested():
    try:
        raise ConnectionError("Link dropped")
    except Exception:
        # Nested payload to bypass top-level key matching
        fallback = {
            "dark_fleet_payload": {
                "status": "FLEET_DARK_ACTIVE",
                "devices_active": 6,
                "latency_ms": 0.28
            }
        }
        return fallback

def sneaky_except_fallback_builder():
    try:
        raise TimeoutError("Socket timeout")
    except Exception:
        # Build dictionary incrementally
        res = {}
        res["status"] = "FLEET_DARK_ACTIVE"
        res["devices_active"] = 6
        return res

# Vector 4: Obfuscated simulation comments & random telemetry
def sneaky_simulation_call():
    # S.i.m.u.l.a.t.i.n.g failover
    # Synthetic network response generator
    import random as rnd
    # Use aliased random call
    telemetry_val = rnd.uniform(10.0, 95.0)
    return telemetry_val
