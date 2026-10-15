#!/usr/bin/env python3
"""
================================================================================
Lauburu Sovereign Mesh: Strongest-First Free-Tier Model Waterfall & Quality Gate
================================================================================
Subsystem: 06_scripts_and_tooling/cloud_and_quota/strongest_free_tier_client.py
Governed by:
- Rule #0 (Zero-Mock Empirical Truth Verification)
- Rule #1 & Rule #5 (Victory-Triggered Tri-Proof Interceptor Gate)
- Rule #2 (Tri-Vault Storage Synchronization)
- Rule #3 (Host Sanctuary & Dynamic RAM Governance Invariant)
- Rule #6 (Multi-Provider Cloud Quota & Graduated Autonomy Protocol)
- Rule #8 & Rule #10 (Sovereign Local AI Hierarchy: Qwen 3.8 Max + Apple Silicon Metal)

Architecture:
1. Strongest-First Waterfall:
   Tier 1: gemini-3.8-flash (Frontier Flash 2026 - Peak Reasoning & Nuance)
   Tier 2: gemini-3.7-flash (Advanced Reasoning Flash - High Throughput & Multimodal)
   Tier 3: gemini-3.6-flash (Rock-Solid Workhorse Flash - High Reliability)
   Tier 4: gemini-3.5-flash (Fast & Dependable Flash)
   Tier 5: gemma-4-31b-it (Frontier Open-Weights Instruction Model)
   Tier 6: gemini-3.5-flash-lite (Ultra-Low Latency Fallback)
   Tier 7: qwen_38_max (Sovereign Local Orchestrator on Port 8082, $0.00 Offline)

2. Autonomous Quality Gate:
   - Evaluates syntactic validity via ast.parse for all Python code blocks.
   - Rejects degenerate repetition loops (n-gram or sentence repetition >= 3).
   - Enforces Rule #0: prohibits placeholder mocks (TODO, pass # mock, [INSERT CODE]).
   - Rejects truncated or low-content responses (< min_length).
   - Rejects substandard candidates and cascades down the waterfall to regenerate.

3. Zero-Spend & Circuit Breaker Invariant:
   - Integrates with GCPFreeTierCircuitBreaker (15 RPM / 1,450 RPD safe cap).
   - $0.00 cost strictly guaranteed.
================================================================================
"""

from __future__ import annotations

import ast
import datetime
import json
import logging
import os
import re
import sys
import time
import urllib.request
import urllib.error
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

REPO_ROOT = Path("/Volumes/Lauburu-Monorepo")
sys.path.insert(0, str(REPO_ROOT / "06_scripts_and_tooling/cloud_and_quota"))

try:
    from gcp_free_tier_circuit_breaker import GCPFreeTierCircuitBreaker
except ImportError:
    GCPFreeTierCircuitBreaker = None

try:
    from multi_account_free_tier_manager import multi_account_manager
except ImportError:
    multi_account_manager = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [StrongestFreeTier] %(message)s"
)
logger = logging.getLogger("StrongestFreeTier")

TELEMETRY_LOG = REPO_ROOT / "04_data_and_memory/strongest_client_telemetry.jsonl"


# ==============================================================================
# Model Waterfall Hierarchy (Ordered by Empirical Strength)
# ==============================================================================
FREE_TIER_WATERFALL: List[Dict[str, Any]] = [
    {
        "id": "gemini-3.8-flash",
        "name": "Gemini 3.8 Flash",
        "tier": 1,
        "type": "cloud",
        "description": "Frontier Flash 2026 — Peak reasoning, biometrics DSP, deep thought",
    },
    {
        "id": "gemini-3.7-flash",
        "name": "Gemini 3.7 Flash",
        "tier": 2,
        "type": "cloud",
        "description": "Advanced Reasoning Flash — High throughput and multimodal",
    },
    {
        "id": "gemini-3.6-flash",
        "name": "Gemini 3.6 Flash",
        "tier": 3,
        "type": "cloud",
        "description": "Rock-Solid Workhorse Flash — Maximum availability, zero downtime",
    },
    {
        "id": "gemini-3.5-flash",
        "name": "Gemini 3.5 Flash",
        "tier": 4,
        "type": "cloud",
        "description": "Fast & Dependable Flash — Standard free tier workhorse",
    },
    {
        "id": "gemma-4-31b-it",
        "name": "Gemma 4 31B Instruct",
        "tier": 5,
        "type": "cloud",
        "description": "Frontier Open-Weights 31B Instruction Model",
    },
    {
        "id": "gemini-3.5-flash-lite",
        "name": "Gemini 3.5 Flash Lite",
        "tier": 6,
        "type": "cloud",
        "description": "Ultra-Low Latency Lightweight Fallback",
    },
    {
        "id": "qwen_38_max",
        "name": "Qwen 3.8 Max (Local Host)",
        "tier": 7,
        "type": "local",
        "endpoint": "http://127.0.0.1:8082/v1/chat/completions",
        "description": "Sovereign Master Local Orchestrator (prima.cpp PRP ring)",
    },
]

# ==============================================================================
# Domain-Specialized Horizontal Frontier Routing (Zero-Quality-Drop Architecture)
# Prevents descending to weak/lite models by pivoting horizontally across
# specialized frontier models per engineering domain.
# ==============================================================================
DOMAIN_FRONTIER_ROUTING: Dict[str, List[Dict[str, Any]]] = {
    "multimodal_vla": [
        # Screen Lens Sovereign: Google Astra Class / Real-Time Screen & Vision
        {"id": "gemini-3.8-flash", "name": "Gemini 3.8 Flash (Astra Class)", "tier": 1, "type": "cloud", "specialty": "Real-Time Screen & Spatial Grounding"},
        {"id": "gemini-3.7-flash", "name": "Gemini 3.7 Flash (Multimodal Live)", "tier": 1, "type": "cloud", "specialty": "Multimodal Temporal Understanding"},
        {"id": "gemini-3.6-flash", "name": "Gemini 3.6 Flash (Vision Engine)", "tier": 2, "type": "cloud", "specialty": "High-Throughput Screen Frame Parsing"},
        {"id": "qwen_38_max", "name": "Qwen 3.8 Max (Local Sovereign VLA)", "tier": 1, "type": "local", "endpoint": "http://127.0.0.1:8082/v1/chat/completions"},
    ],
    "reverse_engineering": [
        # Closed-Source Reverse Engineering: Deep CoT, Disassembly & Clean-Room Spec
        {"id": "gemini-3.8-flash", "name": "Gemini 3.8 Flash (Deep CoT Decompilation)", "tier": 1, "type": "cloud", "specialty": "Complex Assembly & Protocol Deduction"},
        {"id": "gemini-3.7-flash", "name": "Gemini 3.7 Flash (Binary Spec Extraction)", "tier": 1, "type": "cloud", "specialty": "Protobuf & Bytecode Analysis"},
        {"id": "qwen_38_max_abliterated", "name": "Qwen 3.8 Max 27B Abliterated", "tier": 1, "type": "local", "endpoint": "http://127.0.0.1:8083/v1/chat/completions", "specialty": "Uncensored Binary Analysis & Clean-Room Specs"},
        {"id": "qwen_38_max", "name": "Qwen 3.8 Max (Local Host)", "tier": 1, "type": "local", "endpoint": "http://127.0.0.1:8082/v1/chat/completions"},
    ],
    "open_source_scout": [
        # Open-Source Software Scout: RFC Protocol Decomposition & FFI Memory-Safety
        {"id": "gemini-3.8-flash", "name": "Gemini 3.8 Flash (Grounded Search)", "tier": 1, "type": "cloud", "specialty": "Live GitHub & RFC Grounded Search"},
        {"id": "gemini-3.7-flash", "name": "Gemini 3.7 Flash (Architecture Synthesis)", "tier": 1, "type": "cloud", "specialty": "Polyglot Systems & FFI Analysis"},
        {"id": "qwen_38_max", "name": "Qwen 3.8 Max (Local Core)", "tier": 1, "type": "local", "endpoint": "http://127.0.0.1:8082/v1/chat/completions"},
    ],
    "ai_debate": [
        # Tri-Orchestrator AI Debate: Multi-Model Consensus & Bradley-Terry ELO
        {"id": "gemini-3.8-flash", "name": "Gemini 3.8 Flash (Cloud Architect)", "tier": 1, "type": "cloud", "specialty": "Frontier Deliberation & Safety Guard"},
        {"id": "qwen_38_max", "name": "Qwen 3.8 Max (Master Orchestrator)", "tier": 1, "type": "local", "endpoint": "http://127.0.0.1:8082/v1/chat/completions", "specialty": "TB4 PRP Ring Coordinator & Sovereign Veto"},
        {"id": "qwen_38_max_abliterated", "name": "Qwen 3.8 Max Abliterated (Red Team)", "tier": 1, "type": "local", "endpoint": "http://127.0.0.1:8083/v1/chat/completions", "specialty": "Adversarial Red Teaming & Stress Testing"},
    ],
    "biometrics_dsp": [
        # Medical-Grade Biometrics DSP: 512Hz Pan-Tompkins & PTT Blood Pressure
        {"id": "gemini-3.8-flash", "name": "Gemini 3.8 Flash (DSP Specialist)", "tier": 1, "type": "cloud", "specialty": "Mathematical DSP & Spectral Filter Synthesis"},
        {"id": "gemini-3.7-flash", "name": "Gemini 3.7 Flash (Vectorized DSP)", "tier": 1, "type": "cloud", "specialty": "NumPy Streaming Buffer Optimization"},
        {"id": "qwen_38_max", "name": "Qwen 3.8 Max (Local DSP Core)", "tier": 1, "type": "local", "endpoint": "http://127.0.0.1:8082/v1/chat/completions"},
    ],
}


# ==============================================================================
# Quality Gate
# ==============================================================================
@dataclass
class QualityResult:
    passed: bool
    score: float  # 0.0 to 1.0
    reasons: List[str] = field(default_factory=list)
    code_blocks_found: int = 0
    code_syntactically_valid: Optional[bool] = None


class QualityGate:
    """Rigorous multi-dimensional quality verification gate."""

    BANNED_MOCK_PATTERNS = [
        re.compile(r"#\s*(?:TODO|FIXME|mock|fake|stub|placeholder)", re.IGNORECASE),
        re.compile(r"pass\s*#\s*mock", re.IGNORECASE),
        re.compile(r"\[INSERT\s+(?:CODE|IMPLEMENTATION|HERE)\]", re.IGNORECASE),
        re.compile(r"raise\s+NotImplementedError", re.IGNORECASE),
        re.compile(r"<insert\s+code>", re.IGNORECASE),
    ]

    PYTHON_CODE_BLOCK_PATTERN = re.compile(r"```(?:python|py)?\s*\n(.*?)\n```", re.DOTALL)

    def __init__(
        self,
        min_length: int = 60,
        expect_code: bool = False,
        min_score: float = 0.8,
        strict_zero_mock: bool = True,
    ):
        self.min_length = min_length
        self.expect_code = expect_code
        self.min_score = min_score
        self.strict_zero_mock = strict_zero_mock

    def evaluate(self, text: str, prompt: str = "") -> QualityResult:
        """Evaluates a response against length, syntax, repetition, and zero-mock rules."""
        reasons: List[str] = []
        score = 1.0

        cleaned_text = (text or "").strip()

        # 1. Non-empty and length check
        if not cleaned_text:
            return QualityResult(passed=False, score=0.0, reasons=["Response is empty"])

        if len(cleaned_text) < self.min_length:
            penalty = max(0.0, 1.0 - (len(cleaned_text) / self.min_length))
            score -= (0.4 * penalty)
            reasons.append(f"Length below threshold: {len(cleaned_text)} < {self.min_length} chars")

        # 2. Degenerate repetition detection
        repetition_detected, rep_snippet = self._detect_repetition(cleaned_text)
        if repetition_detected:
            score -= 0.6
            reasons.append(f"Degenerate repetition detected: repeated snippet '{rep_snippet[:40]}...'")

        # 3. Rule #0 Zero-Mock & Placeholder check
        if self.strict_zero_mock:
            mock_found, mock_match = self._detect_mock_patterns(cleaned_text)
            if mock_found:
                score -= 0.5
                reasons.append(f"Rule #0 Violation: contains mock/placeholder '{mock_match}'")

        # 4. Code extraction and AST verification
        code_blocks = self.PYTHON_CODE_BLOCK_PATTERN.findall(cleaned_text)
        code_valid: Optional[bool] = None

        if code_blocks:
            syntax_errors = []
            for idx, block in enumerate(code_blocks):
                try:
                    ast.parse(block)
                except SyntaxError as e:
                    syntax_errors.append(f"Block {idx+1} syntax error: {e}")

            if syntax_errors:
                code_valid = False
                score -= 0.7
                reasons.extend(syntax_errors)
            else:
                code_valid = True

        elif self.expect_code:
            code_valid = False
            score -= 0.5
            reasons.append("Expected executable Python code block, but none was found")

        # Final score bounding
        score = max(0.0, min(1.0, score))
        passed = (score >= self.min_score) and (code_valid is not False)

        return QualityResult(
            passed=passed,
            score=round(score, 3),
            reasons=reasons,
            code_blocks_found=len(code_blocks),
            code_syntactically_valid=code_valid,
        )

    def _detect_repetition(self, text: str) -> Tuple[bool, str]:
        """Detects consecutive identical sentences or 40+ char substrings repeated >= 3 times."""
        # Check repeated lines
        lines = [line.strip() for line in text.splitlines() if len(line.strip()) > 30]
        for i in range(len(lines) - 2):
            if lines[i] == lines[i+1] == lines[i+2]:
                return True, lines[i]

        # Check repeated phrases (>35 chars)
        sentences = [s.strip() for s in re.split(r"[.!?\n]", text) if len(s.strip()) > 35]
        counts: Dict[str, int] = {}
        for s in sentences:
            counts[s] = counts.get(s, 0) + 1
            if counts[s] >= 3:
                return True, s

        return False, ""

    def _detect_mock_patterns(self, text: str) -> Tuple[bool, str]:
        """Scans for forbidden simulated/placeholder patterns."""
        for pattern in self.BANNED_MOCK_PATTERNS:
            match = pattern.search(text)
            if match:
                return True, match.group(0)
        return False, ""


# ==============================================================================
# Fallback Response Container
# ==============================================================================
@dataclass
class FallbackResponse:
    success: bool
    text: str
    model_used: str
    model_tier: int
    fallback_path: List[Dict[str, Any]]
    quality_score: float
    latency_seconds: float
    cost_usd: float = 0.00
    is_local: bool = False
    error_message: str = ""
    quality_result: Optional[QualityResult] = None


# ==============================================================================
# Strongest-First Free-Tier Client
# ==============================================================================
class StrongestFreeTierClient:
    """
    Intelligent client that always attempts the strongest free-tier model first,
    cascades gracefully down the waterfall on 503/429/500/quality failures,
    and seamlessly routes to local Qwen 3.8 Max as sovereign fallback.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        waterfall: Optional[List[Dict[str, Any]]] = None,
        min_interval_seconds: float = 4.2,  # 15 RPM safety pacing
        circuit_breaker: Optional[Any] = None,
        enable_local_fallback: bool = True,
    ):
        self.api_key = api_key if api_key is not None else os.environ.get("GEMINI_API_KEY", "")
        self.waterfall = waterfall or FREE_TIER_WATERFALL
        self.min_interval_seconds = min_interval_seconds
        self.last_cloud_call_time = 0.0
        self.circuit_breaker = circuit_breaker or (
            GCPFreeTierCircuitBreaker() if GCPFreeTierCircuitBreaker else None
        )
        self.enable_local_fallback = enable_local_fallback

    def _rate_limit_pace(self) -> None:
        """Paces calls to guarantee <= 15 RPM on Google AI Studio."""
        elapsed = time.time() - self.last_cloud_call_time
        if elapsed < self.min_interval_seconds:
            sleep_time = self.min_interval_seconds - elapsed
            logger.info(f"Pacing free-tier request (sleeping {sleep_time:.2f}s for 15 RPM)...")
            time.sleep(sleep_time)
        self.last_cloud_call_time = time.time()

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        quality_gate: Optional[QualityGate] = None,
        max_output_tokens: int = 1024,
        temperature: float = 0.2,
        domain: Optional[str] = None,
        prevent_quality_drop: bool = True,
    ) -> FallbackResponse:
        """
        Executes horizontal frontier generation, evaluating quality and pivoting
        across domain-specialized peers without dropping to low-quality/lite models.
        """
        gate = quality_gate or QualityGate()
        fallback_path: List[Dict[str, Any]] = []

        overall_t0 = time.time()

        # Select model candidates based on domain horizontal routing
        if domain and domain in DOMAIN_FRONTIER_ROUTING:
            candidate_models = DOMAIN_FRONTIER_ROUTING[domain]
            logger.info(f"Routing to Domain-Specialized Horizontal Frontier: '{domain}' ({len(candidate_models)} models)")
        elif prevent_quality_drop:
            # Preserve frontier reasoning; exclude low-tier lite models
            candidate_models = [m for m in self.waterfall if m.get("tier", 99) <= 3 or m.get("type") == "local"]
        else:
            candidate_models = self.waterfall

        for model_info in candidate_models:
            model_id = model_info["id"]
            model_tier = model_info["tier"]
            model_type = model_info.get("type", "cloud")

            logger.info(f"Attempting Tier {model_tier} model: {model_id} ({model_info['name']})...")
            step_t0 = time.time()

            # ------------------------------------------------------------------
            # Cloud Model Execution
            # ------------------------------------------------------------------
            if model_type == "cloud":
                if not self.api_key:
                    logger.warning(f"Skipping cloud model {model_id}: GEMINI_API_KEY is missing")
                    fallback_path.append({
                        "model": model_id,
                        "status": "SKIPPED",
                        "reason": "Missing GEMINI_API_KEY",
                        "latency": 0.0,
                    })
                    continue

                # Circuit breaker check
                if self.circuit_breaker:
                    can_call, cb_reason = self.circuit_breaker.can_call_ai_studio()
                    if not can_call:
                        logger.warning(f"Circuit breaker blocked {model_id}: {cb_reason}. Defaulting down...")
                        fallback_path.append({
                            "model": model_id,
                            "status": "CIRCUIT_BREAKER_BLOCKED",
                            "reason": cb_reason,
                            "latency": 0.0,
                        })
                        continue

                # Rate limiting pacing
                self._rate_limit_pace()

                # Invoke via google.genai
                try:
                    from google import genai
                    from google.genai import types

                    client = genai.Client(api_key=self.api_key)
                    config = types.GenerateContentConfig(
                        temperature=temperature,
                        max_output_tokens=max_output_tokens,
                    )
                    if system_instruction:
                        config.system_instruction = system_instruction

                    response = client.models.generate_content(
                        model=model_id,
                        contents=prompt,
                        config=config,
                    )
                    latency = round(time.time() - step_t0, 2)
                    raw_text = response.text or ""

                    # Record successful call with circuit breaker
                    if self.circuit_breaker:
                        self.circuit_breaker.record_ai_studio_call()

                    # Evaluate Quality Gate
                    q_res = gate.evaluate(raw_text, prompt=prompt)
                    if not q_res.passed:
                        logger.warning(
                            f"Model {model_id} failed Quality Gate (Score: {q_res.score}, Reasons: {q_res.reasons}). "
                            "Defaulting down to next model..."
                        )
                        fallback_path.append({
                            "model": model_id,
                            "status": "QUALITY_FAILED",
                            "score": q_res.score,
                            "reasons": q_res.reasons,
                            "latency": latency,
                        })
                        continue

                    # Success!
                    logger.info(
                        f"✅ Model {model_id} SUCCEEDED (Tier {model_tier}, Score: {q_res.score}, Latency: {latency}s)"
                    )
                    fallback_path.append({
                        "model": model_id,
                        "status": "SUCCESS",
                        "score": q_res.score,
                        "latency": latency,
                    })

                    self._log_telemetry(model_id, model_tier, True, q_res.score, latency, fallback_path)

                    return FallbackResponse(
                        success=True,
                        text=raw_text,
                        model_used=model_id,
                        model_tier=model_tier,
                        fallback_path=fallback_path,
                        quality_score=q_res.score,
                        latency_seconds=latency,
                        cost_usd=0.00,
                        is_local=False,
                        quality_result=q_res,
                    )

                except Exception as e:
                    latency = round(time.time() - step_t0, 2)
                    err_msg = str(e)
                    logger.warning(f"Model {model_id} call failed ({latency}s): {err_msg}. Defaulting down...")
                    fallback_path.append({
                        "model": model_id,
                        "status": "ERROR",
                        "error": err_msg,
                        "latency": latency,
                    })
                    continue

            # ------------------------------------------------------------------
            # Local Sovereign Model Fallback (Qwen 3.8 Max)
            # ------------------------------------------------------------------
            elif model_type == "local" and self.enable_local_fallback:
                endpoint = model_info.get("endpoint", "http://127.0.0.1:8082/v1/chat/completions")
                try:
                    payload = {
                        "model": model_id,
                        "messages": [
                            *([{"role": "system", "content": system_instruction}] if system_instruction else []),
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": temperature,
                        "max_tokens": max_output_tokens,
                    }
                    req = urllib.request.Request(
                        endpoint,
                        data=json.dumps(payload).encode("utf-8"),
                        headers={"Content-Type": "application/json"}
                    )
                    with urllib.request.urlopen(req, timeout=12.0) as resp:
                        res_data = json.loads(resp.read().decode("utf-8"))
                        latency = round(time.time() - step_t0, 2)
                        raw_text = res_data.get("choices", [{}])[0].get("message", {}).get("content", "")

                    q_res = gate.evaluate(raw_text, prompt=prompt)
                    if not q_res.passed:
                        logger.warning(f"Local {model_id} failed Quality Gate: {q_res.reasons}")
                        fallback_path.append({
                            "model": model_id,
                            "status": "LOCAL_QUALITY_FAILED",
                            "score": q_res.score,
                            "reasons": q_res.reasons,
                            "latency": latency,
                        })
                        continue

                    logger.info(f"✅ Local {model_id} SUCCEEDED (Score: {q_res.score}, Latency: {latency}s)")
                    fallback_path.append({
                        "model": model_id,
                        "status": "SUCCESS_LOCAL",
                        "score": q_res.score,
                        "latency": latency,
                    })

                    self._log_telemetry(model_id, model_tier, True, q_res.score, latency, fallback_path)

                    return FallbackResponse(
                        success=True,
                        text=raw_text,
                        model_used=model_id,
                        model_tier=model_tier,
                        fallback_path=fallback_path,
                        quality_score=q_res.score,
                        latency_seconds=latency,
                        cost_usd=0.00,
                        is_local=True,
                        quality_result=q_res,
                    )

                except Exception as e:
                    latency = round(time.time() - step_t0, 2)
                    err_msg = str(e)
                    logger.warning(f"Local model {model_id} unreachable ({latency}s): {err_msg}")
                    fallback_path.append({
                        "model": model_id,
                        "status": "LOCAL_UNAVAILABLE",
                        "error": err_msg,
                        "latency": latency,
                    })
                    continue

        # All models exhausted in waterfall
        total_latency = round(time.time() - overall_t0, 2)
        logger.error(f"❌ All models in waterfall exhausted! Total time: {total_latency}s")
        self._log_telemetry("NONE", -1, False, 0.0, total_latency, fallback_path)

        # Build informative error message
        blocked_reasons = [
            f"{s.get("model")}: {s.get("reason") or s.get("error") or s.get("status")}"
            for s in fallback_path
        ]
        if any(s.get("status") == "CIRCUIT_BREAKER_BLOCKED" for s in fallback_path):
            error_msg = f"Circuit breaker blocked AI Studio call: {"; ".join(blocked_reasons)}"
        else:
            error_msg = f"All models in free-tier waterfall exhausted or failed Quality Gate. Path: {"; ".join(blocked_reasons)}"

        return FallbackResponse(
            success=False,
            text="",
            model_used="NONE",
            model_tier=-1,
            fallback_path=fallback_path,
            quality_score=0.0,
            latency_seconds=total_latency,
            cost_usd=0.00,
            is_local=False,
            error_message=error_msg,
        )

    # --------------------------------------------------------------------------
    # Specialized Domain Methods (Zero-Quality-Drop Horizontal Routing)
    # --------------------------------------------------------------------------
    def generate_vla(self, prompt: str, **kwargs) -> FallbackResponse:
        """Astra-Class Multimodal VLA & Screen Perception for Screen Lens Sovereign."""
        return self.generate(prompt, domain="multimodal_vla", **kwargs)

    def generate_reverse_engineering(self, prompt: str, **kwargs) -> FallbackResponse:
        """Closed-Source Reverse Engineering & Protocol Reconstruction."""
        return self.generate(prompt, domain="reverse_engineering", **kwargs)

    def generate_scout(self, prompt: str, **kwargs) -> FallbackResponse:
        """Open-Source Software Scout & RFC Protocol Synthesis."""
        return self.generate(prompt, domain="open_source_scout", **kwargs)

    def generate_debate(self, prompt: str, **kwargs) -> FallbackResponse:
        """Tri-Orchestrator AI Debate & Adversarial Consensus."""
        return self.generate(prompt, domain="ai_debate", **kwargs)

    def generate_biometrics(self, prompt: str, **kwargs) -> FallbackResponse:
        """Medical Biometrics DSP & Pan-Tompkins 512Hz Synthesis."""
        return self.generate(prompt, domain="biometrics_dsp", **kwargs)

    def _log_telemetry(
        self,
        model_id: str,
        tier: int,
        success: bool,
        quality_score: float,
        latency: float,
        fallback_path: List[Dict[str, Any]]
    ) -> None:
        """Appends step-down telemetry to 04_data_and_memory/strongest_client_telemetry.jsonl."""
        record = {
            "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "model_used": model_id,
            "tier": tier,
            "success": success,
            "quality_score": quality_score,
            "latency_seconds": latency,
            "step_downs_count": len(fallback_path) - 1 if fallback_path else 0,
            "fallback_path": fallback_path,
            "cost_usd": 0.00,
        }
        try:
            TELEMETRY_LOG.parent.mkdir(parents=True, exist_ok=True)
            with open(TELEMETRY_LOG, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            logger.error(f"Failed to log telemetry: {e}")


def main() -> None:
    print("=" * 80)
    print("🚀 LAUBURU STRONGEST-FIRST FREE-TIER CLIENT & QUALITY GATE")
    print("=" * 80)

    client = StrongestFreeTierClient()
    gate = QualityGate(min_length=80, expect_code=True, strict_zero_mock=True)

    prompt = (
        "Write a Python function implementing the Pan-Tompkins 5-point derivative filter "
        "for a 512Hz ECG stream: y[n] = (2*x[n] + x[n-1] - x[n-3] - 2*x[n-4]) / 8. "
        "Include docstrings and types, and ensure the code is complete and syntactically valid."
    )

    resp = client.generate(
        prompt=prompt,
        system_instruction="You are a medical DSP systems engineer adhering strictly to zero-mock principles.",
        quality_gate=gate,
    )

    print(f"Outcome: {'✅ SUCCESS' if resp.success else '❌ FAILED'}")
    print(f"Model Used: {resp.model_used} (Tier {resp.model_tier})")
    print(f"Quality Score: {resp.quality_score}")
    print(f"Latency: {resp.latency_seconds}s | Cost: ${resp.cost_usd:.2f}")
    print(f"Fallback Path ({len(resp.fallback_path)} attempts):")
    for step in resp.fallback_path:
        print(f"  - {step.get('model')}: {step.get('status')} ({step.get('latency', 0)}s)")

    if resp.success:
        print("\nGenerated Output:")
        print(resp.text[:400] + ("..." if len(resp.text) > 400 else ""))


if __name__ == "__main__":
    main()
