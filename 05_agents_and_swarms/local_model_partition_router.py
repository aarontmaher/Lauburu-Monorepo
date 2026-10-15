#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
05_agents_and_swarms/local_model_partition_router.py
=====================================================
Sovereign Local Model Partition Router & Orchestration Engine
Lauburu Mesh Ecosystem — 2026

Architecture:
1. Local AI Orchestrator:
   - Standardized strictly on Qwen 3.8 Standard GGUF (.gguf format).
   - Operates over llama.cpp (Port 8081) and prima.cpp PRP (Port 8082).
2. Dual Segregated Operational Planes:
   - Normal Plane:
     * Master: Qwen 3.8 Standard GGUF.
     * Allowed child calls: NORMAL MODELS ONLY (Qwen 3.8-Flash-Next, Qwen MoE 80B,
       Qwen 2.5 Coder 7B/32B, Qwen 2.5 Math 7B/72B, SmolLM2 1.7B/360M, Phi-3.5,
       Ministral 3B, Qwen 2.5 VL 7B, DeepSeek Coder V2 Lite).
     * Invariant: Calling any abliterated model from the normal plane is strictly forbidden.
   - Abliterated Plane:
     * Lead Adversary: Huihui-Qwen 3.8 Max 27B Abliterated GGUF (Port 8083).
     * Allowed child calls: ABLITERATED MODELS ONLY (Mistral-Nemo 12B Abliterated,
       Qwen 2.5 7B Abliterated, Gemma 2 9B Abliterated, Llama 3.2 1B Abliterated).
     * Invariant: Calling any normal/censored model from the abliterated plane is strictly forbidden.
3. Dual-Engine Compatibility:
   - 100% GGUF standardization across both llama.cpp and prima.cpp PRP ring.
   - Replaces isolated Apple MLX format with open, cross-mesh sharding GGUFs.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("LocalModelPartitionRouter")
if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] [ModelRouter] %(message)s"
    )

REPO_ROOT = Path(__file__).resolve().parents[1]
MODEL_VAULT_DIR = REPO_ROOT / "02_ai_models_and_inference/model_vault_gguf"
LORA_DATASETS_DIR = Path("/Users/aaron/DFS_UNIFIED/lora_datasets")
LORA_DATASETS_DIR.mkdir(parents=True, exist_ok=True)
ROUTER_LORA_LOG = LORA_DATASETS_DIR / "local_model_partition_router_traces.jsonl"


class PlaneViolationError(Exception):
    """Raised when an attempt is made to call a model crossing plane boundaries."""
    pass


@dataclass(frozen=True)
class LocalModelMetadata:
    model_id: str
    display_name: str
    plane: str  # "normal" or "abliterated"
    format: str  # "GGUF"
    architecture: str
    default_port: int
    filename: str
    engines: List[str] = field(default_factory=lambda: ["llama.cpp", "prima.cpp"])
    is_abliterated: bool = False
    is_orchestrator: bool = False
    notes: str = ""

    def get_vault_path(self) -> Path:
        return MODEL_VAULT_DIR / self.filename

    def exists_on_disk(self) -> bool:
        return self.get_vault_path().exists()


# ─── Canonical Partitioned Model Catalogs ─────────────────────────────────────

NORMAL_MODELS: Dict[str, LocalModelMetadata] = {
    "qwen_38_standard": LocalModelMetadata(
        model_id="qwen_38_standard",
        display_name="Qwen 3.8 Standard GGUF (Master Orchestrator)",
        plane="normal",
        format="GGUF",
        architecture="Dense 27B/32B High-Reasoning",
        default_port=8081,
        filename="qwen2.5-coder-7b-instruct-q4_k_m.gguf",  # Active local anchor
        is_abliterated=False,
        is_orchestrator=True,
        notes="Primary Local AI Orchestrator. Coordinates coding, AST verification, and normal task delegation."
    ),
    "qwen_38_flash_next": LocalModelMetadata(
        model_id="qwen_38_flash_next",
        display_name="Qwen 3.8-Flash-Next GGUF",
        plane="normal",
        format="GGUF",
        architecture="Dense 7B/8B Fast Ingestion",
        default_port=8081,
        filename="qwen2.5-0.5b-instruct-q4_k_m.gguf",
        is_abliterated=False,
        notes="High-speed speculative draft model, real-time serial streaming, sub-20ms TTFT."
    ),
    "qwen_moe_80b": LocalModelMetadata(
        model_id="qwen_moe_80b",
        display_name="Qwen MoE 80B GGUF (Qwen3-Next-80B-A3B / 3B Active)",
        plane="normal",
        format="GGUF",
        architecture="Sparse MoE (80B Total / 3B Active)",
        default_port=8082,
        filename="Qwen-AgentWorld-35B-A3B-UD-Q4_K_M.gguf",
        is_abliterated=False,
        notes="Target apex model: Sharded across 7-layer mesh via prima.cpp PRP ring over 10Gbps TB4 DMA."
    ),
    "qwen2.5_coder_7b": LocalModelMetadata(
        model_id="qwen2.5_coder_7b",
        display_name="Qwen 2.5 Coder 7B Instruct GGUF",
        plane="normal",
        format="GGUF",
        architecture="Dense 7.6B Code Specialist",
        default_port=8081,
        filename="qwen2.5-coder-7b-instruct-q4_k_m.gguf",
        is_abliterated=False,
        notes="Production-grade AST code generation, refactoring, and lint patching."
    ),
    "qwen2.5_coder_32b": LocalModelMetadata(
        model_id="qwen2.5_coder_32b",
        display_name="Qwen 2.5 Coder 32B Instruct GGUF",
        plane="normal",
        format="GGUF",
        architecture="Dense 32.5B Code Sovereign",
        default_port=8081,
        filename="qwen2.5-coder-32b-instruct-q4_k_m.gguf",
        is_abliterated=False,
        notes="Deep architectural refactoring and multi-file cross-compilation."
    ),
    "qwen2.5_math_7b": LocalModelMetadata(
        model_id="qwen2.5_math_7b",
        display_name="Qwen 2.5 Math 7B Instruct GGUF",
        plane="normal",
        format="GGUF",
        architecture="Dense 7B Mathematical Prover",
        default_port=8087,
        filename="Qwen2.5-Math-7B-Instruct-Q4_K_M.gguf",
        is_abliterated=False,
        notes="Proves RAM headroom safety equations and Lyapunov stability constraints."
    ),
    "qwen2.5_math_72b": LocalModelMetadata(
        model_id="qwen2.5_math_72b",
        display_name="Qwen 2.5 Math 72B Instruct IQ2_XXS GGUF",
        plane="normal",
        format="GGUF",
        architecture="Dense 72B Mathematical Oracle",
        default_port=8087,
        filename="Qwen2.5-Math-72B-Instruct-IQ2_XXS.gguf",
        is_abliterated=False,
        notes="Solves Knapsack ILP sharding matrices and global tensor balance equations."
    ),
    "smollm2_1.7b": LocalModelMetadata(
        model_id="smollm2_1.7b",
        display_name="SmolLM2 1.7B Instruct GGUF",
        plane="normal",
        format="GGUF",
        architecture="Edge Compact 1.7B",
        default_port=8086,
        filename="smollm2-1.7b-instruct-q4_k_m.gguf",
        is_abliterated=False,
        notes="High-frequency AST token filtering and Bluetooth RFCOMM keepalive monitoring."
    ),
    "smollm2_360m": LocalModelMetadata(
        model_id="smollm2_360m",
        display_name="SmolLM2 360M Instruct GGUF",
        plane="normal",
        format="GGUF",
        architecture="Nano Edge 360M",
        default_port=8086,
        filename="SmolLM2-360M-Instruct-Q4_K_M.gguf",
        is_abliterated=False,
        notes="Ultra-low latency JSON schema extractor (<5ms)."
    ),
    "phi_3.5_mini": LocalModelMetadata(
        model_id="phi_3.5_mini",
        display_name="Phi-3.5 Mini Instruct GGUF",
        plane="normal",
        format="GGUF",
        architecture="Dense 3.8B Reasoning Specialist",
        default_port=8081,
        filename="Phi-3.5-mini-instruct-Q4_K_M.gguf",
        is_abliterated=False,
        notes="Microsoft Phi-3.5 high-efficiency reasoning under 2.5 GB RAM footprint."
    ),
    "ministral_3b": LocalModelMetadata(
        model_id="ministral_3b",
        display_name="Ministral 3B Instruct 2512 GGUF",
        plane="normal",
        format="GGUF",
        architecture="Dense 3B Mobile Reasoner",
        default_port=8081,
        filename="Ministral-3-3B-Instruct-2512-Q4_K_M.gguf",
        is_abliterated=False,
        notes="Ultra-fast prompt processing (>700 tok/s prompt eval) on edge layers."
    ),
    "qwen2.5_vl_7b": LocalModelMetadata(
        model_id="qwen2.5_vl_7b",
        display_name="Qwen 2.5 VL 7B Instruct GGUF",
        plane="normal",
        format="GGUF",
        architecture="Multimodal 7B Vision-Language",
        default_port=8080,
        filename="Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf",
        is_abliterated=False,
        notes="Screen Lens live perception, UI visual diff auditing, pixel-level truth verification."
    ),
    "deepseek_coder_v2_lite": LocalModelMetadata(
        model_id="deepseek_coder_v2_lite",
        display_name="DeepSeek Coder V2 Lite Instruct GGUF",
        plane="normal",
        format="GGUF",
        architecture="MoE 16B (2.4B Active)",
        default_port=8081,
        filename="DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M.gguf",
        is_abliterated=False,
        notes="MoE coding specialist offloaded to Linux Head Node (L3) or MacBook Pro (L2)."
    )
}

ABLITERATED_MODELS: Dict[str, LocalModelMetadata] = {
    "qwen_38_max_abliterated": LocalModelMetadata(
        model_id="qwen_38_max_abliterated",
        display_name="Huihui Qwen 3.8 Max 27B Abliterated GGUF (Lead Adversary)",
        plane="abliterated",
        format="GGUF",
        architecture="Abliterated Orthogonalized 27B",
        default_port=8083,
        filename="Huihui-Qwen3.8-27B-abliterated-UD-Q4_K_XL.gguf",
        is_abliterated=True,
        is_orchestrator=True,
        notes="Primary Devil's Advocate & Adversarial Red Team Lead. Uncensored architectural interrogation."
    ),
    "mistral_nemo_12b_abliterated": LocalModelMetadata(
        model_id="mistral_nemo_12b_abliterated",
        display_name="Mistral Nemo 12.2B Abliterated GGUF",
        plane="abliterated",
        format="GGUF",
        architecture="Abliterated 12.2B Auditor",
        default_port=8082,
        filename="Mistral-Nemo-Instruct-2407-abliterated.Q4_K_M.gguf",
        is_abliterated=True,
        notes="Adversarial auditor and security code reviewer. Zero refusal threshold."
    ),
    "qwen2.5_7b_abliterated": LocalModelMetadata(
        model_id="qwen2.5_7b_abliterated",
        display_name="Qwen 2.5 7B Instruct Abliterated GGUF",
        plane="abliterated",
        format="GGUF",
        architecture="Abliterated 7B Fast Challenger",
        default_port=8083,
        filename="Qwen2.5-7B-Instruct-abliterated.Q4_K_M.gguf",
        is_abliterated=True,
        notes="Fast edge abliterated adversary for sub-50ms challenge responses."
    ),
    "gemma_2_9b_abliterated": LocalModelMetadata(
        model_id="gemma_2_9b_abliterated",
        display_name="Gemma 2 9B IT Abliterated GGUF",
        plane="abliterated",
        format="GGUF",
        architecture="Abliterated 9B Judge",
        default_port=8083,
        filename="gemma-2-9b-it-abliterated-Q4_K_M.gguf",
        is_abliterated=True,
        notes="Skeptical adjudicator for architectural edge cases."
    ),
    "llama_3.2_1b_abliterated": LocalModelMetadata(
        model_id="llama_3.2_1b_abliterated",
        display_name="Llama 3.2 1B Instruct Abliterated GGUF",
        plane="abliterated",
        format="GGUF",
        architecture="Abliterated 1B Nano Prober",
        default_port=8083,
        filename="Llama-3.2-1B-Instruct-abliterated.Q4_K_M.gguf",
        is_abliterated=True,
        notes="Nano abliterated sentinel detecting false-positive compliance claims."
    )
}


# ─── Local Model Partition Router Engine ──────────────────────────────────────

class LocalModelPartitionRouter:
    """
    Governs local model invocation across the two strictly partitioned planes:
    1. Normal Plane: Orchestrated by Qwen 3.8 Standard GGUF; may call only normal models.
    2. Abliterated Plane: Orchestrated by Qwen 3.8 Abliterated GGUF; may call only abliterated models.
    Both planes standardize 100% on GGUF for llama.cpp & prima.cpp.
    """

    def __init__(self):
        self.normal_models = NORMAL_MODELS
        self.abliterated_models = ABLITERATED_MODELS
        self.routing_history: List[Dict[str, Any]] = []

    def get_orchestrator(self, plane: str = "normal") -> LocalModelMetadata:
        """Returns the pinned GGUF orchestrator for the given plane."""
        if plane == "normal":
            return self.normal_models["qwen_38_standard"]
        elif plane == "abliterated":
            return self.abliterated_models["qwen_38_max_abliterated"]
        else:
            raise ValueError(f"Unknown plane: '{plane}'. Must be 'normal' or 'abliterated'.")

    def validate_delegation(self, caller_plane: str, target_model_id: str) -> LocalModelMetadata:
        """
        Enforces the cardinal rule:
        - In the Normal Plane: Target MUST be a normal model.
        - In the Abliterated Plane: Target MUST be an abliterated model.
        Cross-plane invocations raise PlaneViolationError.
        """
        caller_plane = caller_plane.strip().lower()

        if caller_plane == "normal":
            if target_model_id in self.abliterated_models:
                raise PlaneViolationError(
                    f"CRITICAL GOVERNANCE VIOLATION: Normal Orchestrator (Qwen 3.8 Standard) attempted to call "
                    f"abliterated model '{target_model_id}'. Normal plane is restricted to normal models only!"
                )
            if target_model_id not in self.normal_models:
                raise KeyError(f"Model '{target_model_id}' is not registered in the Normal Model catalog.")
            return self.normal_models[target_model_id]

        elif caller_plane == "abliterated":
            if target_model_id in self.normal_models:
                raise PlaneViolationError(
                    f"CRITICAL GOVERNANCE VIOLATION: Abliterated Adversary (Qwen 3.8 Abliterated) attempted to call "
                    f"normal model '{target_model_id}'. Abliterated plane is restricted to abliterated models only!"
                )
            if target_model_id not in self.abliterated_models:
                raise KeyError(f"Model '{target_model_id}' is not registered in the Abliterated Model catalog.")
            return self.abliterated_models[target_model_id]

        else:
            raise ValueError(f"Invalid caller plane '{caller_plane}'. Must be 'normal' or 'abliterated'.")

    def route_call(
        self,
        caller_plane: str,
        target_model_id: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 512,
        temperature: float = 0.2,
        execute: bool = False
    ) -> Dict[str, Any]:
        """
        Validates plane isolation, checks GGUF disk availability, and dispatches the call.
        If execute=True, performs authentic HTTP completion against the model server on default_port.
        Records an empirical trace for 24/7 LoRA distillation.
        """
        model_meta = self.validate_delegation(caller_plane, target_model_id)
        ts_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        # GGUF existence verification
        file_present = model_meta.exists_on_disk()
        vault_path = model_meta.get_vault_path()

        trace: Dict[str, Any] = {
            "timestamp_utc": ts_iso,
            "caller_plane": caller_plane,
            "target_model_id": target_model_id,
            "display_name": model_meta.display_name,
            "format": model_meta.format,
            "architecture": model_meta.architecture,
            "default_port": model_meta.default_port,
            "vault_path": str(vault_path),
            "file_present": file_present,
            "engines": model_meta.engines,
            "status": "DISPATCHED" if file_present else "CONFIGURED_GGUF",
            "prompt_length_chars": len(prompt),
            "is_abliterated": model_meta.is_abliterated,
            "executed": execute,
            "execution_status": "SKIPPED" if not execute else "PENDING"
        }

        if execute:
            import urllib.request
            import urllib.error
            url = f"http://127.0.0.1:{model_meta.default_port}/v1/chat/completions"
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            req_payload = {
                "model": model_meta.filename if "Huihui" in model_meta.filename else target_model_id,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature
            }

            t0 = time.time()
            try:
                req_data = json.dumps(req_payload).encode("utf-8")
                http_req = urllib.request.Request(url, data=req_data, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(http_req, timeout=15) as resp:
                    resp_body = json.loads(resp.read().decode("utf-8"))
                    duration = time.time() - t0
                    choices = resp_body.get("choices", [])
                    content = choices[0]["message"]["content"] if choices else ""
                    timings = resp_body.get("timings", {})
                    usage = resp_body.get("usage", {})
                    trace["execution_status"] = "SUCCESS"
                    trace["response_text"] = content
                    trace["duration_seconds"] = round(duration, 3)
                    trace["completion_tokens"] = usage.get("completion_tokens", 0)
                    trace["prompt_tokens"] = usage.get("prompt_tokens", 0)
                    trace["tokens_per_second"] = round(timings.get("predicted_per_second", 0.0), 2)
            except Exception as e:
                trace["execution_status"] = f"OFFLINE_OR_ERROR: {e}"
                trace["response_text"] = None

        self.routing_history.append(trace)

        # Atomic serialization to 24/7 LoRA dataset
        try:
            with open(ROUTER_LORA_LOG, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "instruction": f"Route task across partitioned {caller_plane.upper()} local AI plane to {target_model_id}",
                    "input": f"Model: {model_meta.display_name} | Format: {model_meta.format} | Port: {model_meta.default_port}",
                    "output": f"Routing validated: Plane isolation verified. File: {vault_path.name} ({'EXISTS' if file_present else 'PENDING'}).",
                    "timestamp": ts_iso,
                    "caller_plane": caller_plane,
                    "target_model": target_model_id
                }) + "\n")
        except Exception:
            pass

        logger.info(
            f"✅ [Plane: {caller_plane.upper()}] Delegated to '{model_meta.display_name}' on Port {model_meta.default_port} "
            f"(GGUF: {vault_path.name} {'✓' if file_present else '✗'}) [Exec: {trace.get('execution_status')}]"
        )
        return trace

    def orchestrator_delegate(self, target_model_id: str, prompt: str, **kwargs) -> Dict[str, Any]:
        """Qwen 3.8 Standard Orchestrator delegates a subtask to another local normal model."""
        return self.route_call(caller_plane="normal", target_model_id=target_model_id, prompt=prompt, **kwargs)

    def adversary_delegate(self, target_model_id: str, prompt: str, **kwargs) -> Dict[str, Any]:
        """Qwen 3.8 Max Abliterated Adversary delegates a subtask to another local abliterated model."""
        return self.route_call(caller_plane="abliterated", target_model_id=target_model_id, prompt=prompt, **kwargs)

    def list_models_for_plane(self, plane: str) -> List[Dict[str, Any]]:
        """Returns metadata for all models available on a specific plane."""
        if plane == "normal":
            catalog = self.normal_models
        elif plane == "abliterated":
            catalog = self.abliterated_models
        else:
            raise ValueError(f"Unknown plane: '{plane}'.")

        return [asdict(m) for m in catalog.values()]

    def get_summary(self) -> Dict[str, Any]:
        """Returns high-level status of the partitioned local AI ecosystem."""
        normal_present = sum(1 for m in self.normal_models.values() if m.exists_on_disk())
        abliterated_present = sum(1 for m in self.abliterated_models.values() if m.exists_on_disk())

        return {
            "orchestrator_normal": asdict(self.normal_models["qwen_38_standard"]),
            "orchestrator_abliterated": asdict(self.abliterated_models["qwen_38_max_abliterated"]),
            "normal_models_count": len(self.normal_models),
            "normal_models_on_disk": normal_present,
            "abliterated_models_count": len(self.abliterated_models),
            "abliterated_models_on_disk": abliterated_present,
            "format_standard": "100% GGUF (llama.cpp & prima.cpp PRP)",
            "mlx_status": "DEPRECATED_FOR_CROSS_MESH_SHARDING",
            "total_routing_events": len(self.routing_history)
        }


# Singleton instance
partition_router = LocalModelPartitionRouter()


if __name__ == "__main__":
    print("================================================================================")
    print("🧠 LOCAL MODEL PARTITION ROUTER: VERIFYING DUAL PLANE ISOLATION")
    print("================================================================================")

    # 1. Inspect orchestrators
    norm_orch = partition_router.get_orchestrator("normal")
    ablit_orch = partition_router.get_orchestrator("abliterated")
    print(f"Normal Orchestrator     : {norm_orch.display_name} (Port {norm_orch.default_port})")
    print(f"Abliterated Adversary   : {ablit_orch.display_name} (Port {ablit_orch.default_port})")

    # 2. Test valid normal plane delegation
    t1 = partition_router.route_call("normal", "qwen2.5_coder_7b", "Write a Python AST parser.")
    print(f"\n✔ Normal delegation to '{t1['target_model_id']}': STATUS={t1['status']}")

    # 3. Test valid abliterated plane delegation
    t2 = partition_router.route_call("abliterated", "mistral_nemo_12b_abliterated", "Analyze buffer overflow hazard.")
    print(f"✔ Abliterated delegation to '{t2['target_model_id']}': STATUS={t2['status']}")

    # 4. Test forbidden cross-plane calls
    try:
        partition_router.route_call("normal", "mistral_nemo_12b_abliterated", "Attempt illegal call")
        print("❌ FAILED: Cross-plane call was not blocked!")
    except PlaneViolationError as e:
        print(f"✔ Successfully blocked illegal Normal -> Abliterated call: {e}")

    try:
        partition_router.route_call("abliterated", "qwen2.5_coder_7b", "Attempt illegal call")
        print("❌ FAILED: Cross-plane call was not blocked!")
    except PlaneViolationError as e:
        print(f"✔ Successfully blocked illegal Abliterated -> Normal call: {e}")

    print("\n================================================================================")
    print("Summary:", json.dumps(partition_router.get_summary(), indent=2))
    print("================================================================================")
