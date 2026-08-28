"""
conftest.py — Unified Test Fixtures & Environment Setup for Router AI Daemon (smolagi)
Authoritative Specifications: ORIGINAL_REQUEST.md & PROJECT.md
"""

import os
import sys
import json
import math
import hmac
import hashlib
import tempfile
import threading
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

import pytest

# Ensure daemon root is on python path
DAEMON_ROOT = Path(__file__).resolve().parent.parent
if str(DAEMON_ROOT) not in sys.path:
    sys.path.insert(0, str(DAEMON_ROOT))


# ---------------------------------------------------------------------------
# Reference Specifications & Mathematical Models (Contract Enforcers)
# ---------------------------------------------------------------------------

class ReferenceDecisionEngine:
    """Mathematical reference implementation of Dual-Core Consensus & Micro-Debate."""
    
    @staticmethod
    def compute_divergence(d1: Dict[str, Any], d2: Dict[str, Any], wp: float = 0.60, wc: float = 0.40) -> float:
        """
        Divergence Formula:
        Δ = I(a1 != a2) * 1.0 + I(a1 == a2) * [ (||p1 - p2|| / ||p_max||) * wp + |c1 - f2| * wc ]
        """
        a1, a2 = d1.get("action"), d2.get("action")
        if a1 != a2:
            return 1.0
        
        # Calculate parameter distance normalized by parameter magnitudes
        p1 = d1.get("params", {})
        p2 = d2.get("params", {})
        all_keys = set(p1.keys()).union(set(p2.keys()))
        if not all_keys:
            param_dist = 0.0
        else:
            diffs = []
            max_magnitudes = []
            for k in all_keys:
                v1 = p1.get(k, 0.0)
                v2 = p2.get(k, 0.0)
                if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
                    diffs.append((float(v1) - float(v2)) ** 2)
                    max_magnitudes.append(max(abs(float(v1)), abs(float(v2)), 1.0) ** 2)
                else:
                    diffs.append(0.0 if v1 == v2 else 1.0)
                    max_magnitudes.append(1.0)
            
            numerator = math.sqrt(sum(diffs))
            denominator = math.sqrt(sum(max_magnitudes))
            param_dist = min(1.0, numerator / max(1.0, denominator))

        c1 = float(d1.get("confidence", 0.8))
        f2 = float(d2.get("fitness", 0.8))
        conf_diff = abs(c1 - f2)

        return (param_dist * wp) + (conf_diff * wc)

    @staticmethod
    def calculate_utility(candidate: Dict[str, Any]) -> float:
        """
        Utility Vector:
        u1: RAM/Safety (w1=0.30)
        u2: Latency/SLA (w2=0.25)
        u3: Mesh Resilience (w3=0.20)
        u4: Token Frugality (w4=0.15)
        u5: Historical Accuracy (w5=0.10)
        """
        weights = [0.30, 0.25, 0.20, 0.15, 0.10]
        u = [
            candidate.get("u1_safety", 0.9),
            candidate.get("u2_latency", 0.85),
            candidate.get("u3_resilience", 0.8),
            candidate.get("u4_frugality", 0.95),
            candidate.get("u5_accuracy", 0.9),
        ]
        return sum(w * val for w, val in zip(weights, u))

    @staticmethod
    def compute_cosine_accord(v1: List[float], v2: List[float]) -> float:
        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)


class ReferenceEloEngine:
    """Mathematical reference implementation of David vs Goliath ELO & Waste Tax."""

    @staticmethod
    def calculate_expected_score(rating_a: float, rating_b: float) -> Tuple[float, float]:
        ea = 1.0 / (1.0 + 10.0 ** ((rating_b - rating_a) / 400.0))
        eb = 1.0 - ea
        return ea, eb

    @staticmethod
    def calculate_david_multiplier(
        param_goliath_b: float,
        param_david_b: float,
        ram_goliath_mb: float,
        ram_david_mb: float,
        tokens_goliath: int,
        tokens_david: int,
        task_complexity: float,
        alpha: float = 0.30,
        beta: float = 0.20,
        delta: float = 0.15,
    ) -> float:
        """
        μ_D = (P_G / P_D)^α * (M_G / M_D)^β * (T_G / (T_D + 1))^δ * Ω_task
        Clamped to [1.0, 50.0]
        """
        p_ratio = max(1.0, param_goliath_b / max(0.001, param_david_b))
        m_ratio = max(1.0, ram_goliath_mb / max(1.0, ram_david_mb))
        t_ratio = max(1.0, (tokens_goliath + 1.0) / (tokens_david + 1.0))
        
        mu_d = (p_ratio ** alpha) * (m_ratio ** beta) * (t_ratio ** delta) * max(0.1, task_complexity)
        return max(1.0, min(50.0, mu_d))

    @staticmethod
    def calculate_goliath_multiplier(
        param_david_b: float,
        param_goliath_b: float,
        ram_david_mb: float,
        ram_goliath_mb: float,
        task_complexity: float,
        alpha: float = 0.30,
        beta: float = 0.20,
    ) -> float:
        """
        μ_G = (P_D / P_G)^α * (M_D / M_G)^β * (1.0 / max(0.10, Ω_task))
        Clamped to [0.01, 1.0]
        """
        p_ratio = min(1.0, max(0.0001, param_david_b / max(0.001, param_goliath_b)))
        m_ratio = min(1.0, max(0.0001, ram_david_mb / max(1.0, ram_goliath_mb)))
        
        mu_g = (p_ratio ** alpha) * (m_ratio ** beta) * (1.0 / max(0.10, task_complexity))
        return max(0.01, min(1.0, mu_g))

    @staticmethod
    def calculate_waste_tax(
        spend_usd: float,
        tokens_wasted: int,
        spurious_calls: int,
        mesh_drain_index: float,
        optimization_score: float,
        threshold: float = 0.50,
        lambda_base: float = 50.0,
        c0: float = 0.05,
        t0: float = 2048.0,
        gamma: float = 1.25,
    ) -> float:
        """
        Waste Tax formula:
        Tax_waste = -Λ_base * [ wc*(C/C0) + wt*(T/T0) + wm*Ψ + wa*N ]^γ * (1.0 - ΔΦ)
        If ΔΦ >= threshold: Tax = 0.0
        """
        if optimization_score >= threshold:
            return 0.0
        
        wc, wt, wm, wa = 0.35, 0.25, 0.25, 0.15
        term_cost = wc * (spend_usd / c0)
        term_tokens = wt * (tokens_wasted / t0)
        term_mesh = wm * mesh_drain_index
        term_calls = wa * float(spurious_calls)

        inner_sum = max(0.0, term_cost + term_tokens + term_mesh + term_calls)
        penalty = lambda_base * (inner_sum ** gamma) * (1.0 - optimization_score)
        return -abs(penalty)


class ReferenceAssetPackager:
    """Reference implementation for 5-class asset packaging conforming to JSON Schema."""

    VALID_CLASSES = {"code_component", "cli_tool", "mcp_server", "sdk_package", "surplus_compute"}

    @classmethod
    def package_asset(
        cls,
        asset_type: str,
        title: str,
        description: str,
        version: str,
        tags: List[str],
        technical_spec: Dict[str, Any],
        monetization: Dict[str, Any],
        provenance: Dict[str, Any],
        raw_content: bytes,
        hmac_key: str = "lauburu_secret_master_key",
    ) -> Dict[str, Any]:
        if asset_type not in cls.VALID_CLASSES:
            raise ValueError(f"Invalid asset class: {asset_type}")

        payload_sha256 = hashlib.sha256(raw_content).hexdigest()
        asset_id = f"urn:lauburu:asset:{asset_type.split('_')[0]}:{payload_sha256[:16]}"

        manifest = {
            "content_encoding": "raw_text_json",
            "payload_sha256": payload_sha256,
            "payload_data_or_uri": raw_content.decode("utf-8", errors="replace"),
        }

        # Consensus signature
        sig_data = f"{asset_id}:{version}:{payload_sha256}".encode("utf-8")
        sig_hmac = hmac.new(hmac_key.encode("utf-8"), sig_data, hashlib.sha256).hexdigest()

        payload = {
            "schema_version": "1.0.0",
            "asset_id": asset_id,
            "asset_type": asset_type,
            "title": title,
            "description": description,
            "version": version,
            "tags": tags,
            "technical_spec": technical_spec,
            "monetization": monetization,
            "provenance": provenance,
            "payload_manifest": manifest,
            "consensus_signature": {
                "dual_core_ratified": True,
                "smolagi_vote": "RATIFIED",
                "genetic_router_vote": "RATIFIED",
                "hmac_sha256": sig_hmac,
            },
        }
        return payload


# ---------------------------------------------------------------------------
# Pytest Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_workspace(tmp_path):
    """Provides an isolated temporary workspace directory."""
    ws = tmp_path / "workspace"
    ws.mkdir(parents=True, exist_ok=True)
    return ws


@pytest.fixture
def mock_tmpfs(tmp_path):
    """Simulates volatile tmpfs storage on the router."""
    tmpfs = tmp_path / "tmpfs"
    tmpfs.mkdir(parents=True, exist_ok=True)
    (tmpfs / "models").mkdir()
    (tmpfs / "secrets").mkdir()
    (tmpfs / "business_queue").mkdir()
    (tmpfs / "telemetry").mkdir()
    return tmpfs


@pytest.fixture
def mock_mesh_matrix():
    """Provides the 7-Layer Lauburu Physical Mesh hardware topology matrix."""
    return {
        "GW": {"name": "GL_iNet_Router", "ip": "192.168.8.1", "ram_mb": 1024.0, "ai_cap_mb": 300.0, "type": "arm64"},
        "L1": {"name": "Mac_Node", "ip": "192.168.8.230", "ram_mb": 24576.0, "ai_cap_mb": 22118.4, "type": "arm64"},
        "L2": {"name": "MacBook_Pro", "ip": "192.168.8.127", "ram_mb": 16384.0, "ai_cap_mb": 14336.0, "type": "arm64"},
        "L3": {"name": "Linux_Head_Node", "ip": "192.168.8.224", "ram_mb": 16384.0, "ai_cap_mb": 13107.2, "type": "x86_64"},
        "L4": {"name": "Linux_Tablet", "ip": "100.81.92.125", "ram_mb": 8192.0, "ai_cap_mb": 6144.0, "type": "x86_64"},
        "L5": {"name": "MacBook_Air", "ip": "192.168.8.222", "ram_mb": 16384.0, "ai_cap_mb": 14336.0, "type": "arm64"},
        "L6": {"name": "Pixel_10_Pro_XL", "ip": "100.73.38.87", "ram_mb": 16384.0, "ai_cap_mb": 12800.0, "type": "arm64"},
        "L7": {"name": "Samsung_S20", "ip": "100.84.40.95", "ram_mb": 12288.0, "ai_cap_mb": 9216.0, "type": "arm64"},
    }


@pytest.fixture
def mock_specialist_specs():
    """Provides the 6 canonical heterogeneous specialist definitions."""
    return [
        {
            "id": "spec_posix_healer",
            "model": "SmolLM2-135M-Instruct",
            "quant": "IQ1_S",
            "ram_mb": 42.0,
            "specialty": "posix_healer",
            "target_layer": "GW",
        },
        {
            "id": "spec_movesense_dsp",
            "model": "SmolLM2-360M-Instruct",
            "quant": "IQ2_XXS",
            "ram_mb": 98.0,
            "specialty": "movesense_dsp",
            "target_layer": "L4",
        },
        {
            "id": "spec_ast_surgeon",
            "model": "Qwen2.5-Coder-0.5B",
            "quant": "Q4_K_M",
            "ram_mb": 210.0,
            "specialty": "ast_surgeon",
            "target_layer": "L3",
        },
        {
            "id": "spec_tb4_dma",
            "model": "SmolLM2-135M-Instruct",
            "quant": "IQ2_XXS",
            "ram_mb": 55.0,
            "specialty": "tb4_dma",
            "target_layer": "L1",
        },
        {
            "id": "spec_hf_turbo",
            "model": "SmolLM2-135M-Instruct",
            "quant": "IQ1_S",
            "ram_mb": 42.0,
            "specialty": "hf_turbo",
            "target_layer": "GW",
        },
        {
            "id": "spec_ui_fuzzer",
            "model": "DeepSeek-R1-Distill-1.5B",
            "quant": "IQ2_XXS",
            "ram_mb": 280.0,
            "specialty": "ui_fuzzer",
            "target_layer": "L7",
        },
    ]


@pytest.fixture
def ref_decision_engine():
    return ReferenceDecisionEngine


@pytest.fixture
def ref_elo_engine():
    return ReferenceEloEngine


@pytest.fixture
def ref_asset_packager():
    return ReferenceAssetPackager
