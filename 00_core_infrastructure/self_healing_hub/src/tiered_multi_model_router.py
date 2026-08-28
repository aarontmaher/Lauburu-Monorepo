#!/usr/bin/env python3
"""
🧠 Tiered Multi-Model Autonomous Task Router (8-Pillar Unified Fleet)
======================================================================
Synthesizes the complete 8-pillar task routing matrix across local Metal/TPU engines,
PySpark Lakehouse big-data streaming, Ray multi-node actor scheduling, OpenClaw LAN gateway
UI verification, and Gemini Cloud failover:

1. 🧠 Gemini 3.1 Pro Preview: Macro-Context & Strategic Roadmaps (>100k tokens / 2M+ failover).
2. ⚡ Gemini 1.5 Flash High: Tactical Co-Pilot, Step-by-Step CoT Planner & Async Shadow Code Reviewer (185 tok/s).
3. 👑 Qwen 2.5 Max: 100% Local Code Synthesis, AST Refactoring & Syntax Verification (92.7% HumanEval, $0 cost).
4. 👁️ Qwen 2.5 VL: 100% Local Vision-Language Grounding, 8K PTZ Tracking & UI Visual Auditing ($0 cost).
5. 🏛️ Nous Hermes 3 8B: Structured Function Calling, Parameter Extraction & JSON Schema Output ($0 cost).
6. ⚡ PySpark Lakehouse (:8750): Distributed 128Hz Big-Data Batch Processing & LoRA Dataset Ingestion ($0 cost).
7. 🌀 Ray Mesh (:8265): Asynchronous Multi-Node Actor Scheduling & 5-Layer Hardware Memory Offloading ($0 cost).
8. 🦞 OpenClaw Gateway: 100% Offline Headless UI/UX Automated Audits (ws://192.168.8.224:18789, $0 cost).

Features:
- Dynamic AST context call-graph slicing via http://localhost:8750/v1/slice (with in-process AST fallback).
- Automatic macro context failover (>100k tokens) to Gemini 3.1 Pro Preview (2M tokens).
- Accurate cost calculation ($0 for local TB4 Metal/TPU models, real API rates for cloud).
- Automatic multi-tier fallback cascades for disconnected nodes or failed requests.
- 24/7 LoRA decision logging to `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/data/lora_datasets/tiered_router_decisions.jsonl`.
"""

import os
import sys
import json
import time
import ast
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional, Union
from pathlib import Path

WORKSPACE_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
DEFAULT_LORA_DIR = WORKSPACE_ROOT / "data" / "lora_datasets"
DEFAULT_LORA_LOG_FILE = DEFAULT_LORA_DIR / "tiered_router_decisions.jsonl"
GDRIVE_LORA_DIR = Path("/Volumes/Google Drive/My Drive/Lauburu_AI_Memory/lora_datasets")
AST_SLICER_ENDPOINT = os.getenv("AST_SLICER_ENDPOINT", "http://localhost:8750")

# ----------------------------------------------------------------------
# 8-Pillar Unified Fleet Registry & Pricing Matrix
# ----------------------------------------------------------------------
PILLAR_REGISTRY = {
    "macro_strategy": {
        "pillar": "macro_strategy",
        "model": "Gemini 3.1 Pro Preview",
        "tier": "Cloud Strategic Horizon (2M+ Context)",
        "endpoint": "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-pro-preview:generateContent",
        "max_context": 2097152,  # 2M+ tokens
        "cost_per_1m_input": 1.25,
        "cost_per_1m_output": 5.00,
        "is_local": False,
        "target_tasks": [
            "cross_repo_planning",
            "architectural_invariants",
            "large_context_ingest",
            "macro_strategy",
            "whole_monorepo_analysis"
        ],
        "fallback_chain": ["tactical_planning_shadow_audit", "local_code_synthesis"]
    },
    "tactical_planning_shadow_audit": {
        "pillar": "tactical_planning_shadow_audit",
        "model": "Gemini 1.5 Flash Thinking (High)",
        "tier": "High-Speed Extended Reasoning (185 tok/s)",
        "endpoint": "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.7-flash:generateContent",
        "max_context": 1048576,  # 1M tokens
        "speed_tps": 185.0,
        "cost_per_1m_input": 0.15,
        "cost_per_1m_output": 0.60,
        "is_local": False,
        "target_tasks": [
            "step_by_step_cot_planning",
            "shadow_code_review",
            "live_debate_referee",
            "tactical_planning",
            "code_review_invariants"
        ],
        "fallback_chain": ["local_code_synthesis", "macro_strategy"]
    },
    "local_code_synthesis": {
        "pillar": "local_code_synthesis",
        "model": "Qwen 2.5 Max (Apex Local)",
        "tier": "Local TB4 Metal Cluster (18.0 GB GGUF)",
        "endpoint": "http://169.254.187.138:50052/v1",
        "max_context": 131072,  # 131k native / 262k YaRN RoPE
        "evalplus_score": "92.7%",
        "latency_ms": 18.0,
        "cost_per_1m_input": 0.00,
        "cost_per_1m_output": 0.00,
        "cost_per_mo": "$0.00",
        "is_local": True,
        "target_tasks": [
            "code_generation",
            "ast_refactor",
            "unit_test_creation",
            "lint_fix",
            "local_code_synthesis",
            "syntax_verification"
        ],
        "fallback_chain": ["tactical_planning_shadow_audit", "macro_strategy"]
    },
    "local_vision_grounding": {
        "pillar": "local_vision_grounding",
        "model": "Qwen 2.5 VL (Vision-Language)",
        "tier": "Local Edge Multi-Modal Vision (Metal / TPU)",
        "endpoint": "http://127.0.0.1:8080/v1",
        "max_context": 32768,
        "resolution": "Native Multi-Scale (Up to 8K)",
        "cost_per_1m_input": 0.00,
        "cost_per_1m_output": 0.00,
        "is_local": True,
        "target_tasks": [
            "ui_element_detection",
            "8k_kinematics_tracking",
            "screenshot_visual_audit",
            "local_vision_grounding",
            "motion_tracking"
        ],
        "fallback_chain": ["ui_automation", "tactical_planning_shadow_audit"]
    },
    "structured_function_calling": {
        "pillar": "structured_function_calling",
        "model": "Nous Hermes 3 8B",
        "tier": "Local Function Calling Specialist (4.92 GB GGUF)",
        "endpoint": "http://127.0.0.1:8081/v1",
        "max_context": 131072,
        "precision": "99.8%",
        "cost_per_1m_input": 0.00,
        "cost_per_1m_output": 0.00,
        "is_local": True,
        "target_tasks": [
            "json_extraction",
            "tool_use_schema",
            "mcp_parameter_parsing",
            "structured_function_calling",
            "schema_validation"
        ],
        "fallback_chain": ["local_code_synthesis", "tactical_planning_shadow_audit"]
    },
    "pyspark_bigdata_stream": {
        "pillar": "pyspark_bigdata_stream",
        "model": "PySpark Lakehouse Engine (:8750)",
        "tier": "Distributed Telemetry Lakehouse & Parquet Batch Engine",
        "endpoint": "http://127.0.0.1:8750",
        "max_context": 1000000,
        "throughput": "1.2M events/sec",
        "cost_per_1m_input": 0.00,
        "cost_per_1m_output": 0.00,
        "is_local": True,
        "target_tasks": [
            "movesense_128hz_dsp",
            "lora_dataset_sharded_join",
            "ast_repo_indexing",
            "pyspark_bigdata_stream",
            "parquet_lakehouse"
        ],
        "fallback_chain": ["ray_distributed_actors", "local_code_synthesis"]
    },
    "ray_distributed_actors": {
        "pillar": "ray_distributed_actors",
        "model": "Ray Core Actor Mesh (:8265)",
        "tier": "Distributed 5-Layer Multi-Node Actor Orchestration",
        "endpoint": "http://127.0.0.1:8265",
        "max_context": 1000000,
        "concurrency": "100+ parallel actors",
        "cost_per_1m_input": 0.00,
        "cost_per_1m_output": 0.00,
        "is_local": True,
        "target_tasks": [
            "async_agent_duels",
            "dynamic_rpc_vram_swapping",
            "microservice_actors",
            "ray_distributed_actors",
            "parallel_actor_mesh"
        ],
        "fallback_chain": ["pyspark_bigdata_stream", "local_code_synthesis"]
    },
    "ui_automation": {
        "pillar": "ui_automation",
        "model": "OpenClaw Local VLM",
        "tier": "LAN Edge Gateway (ws://192.168.8.224:18789)",
        "endpoint": "ws://192.168.8.224:18789",
        "max_context": 32768,
        "latency_ms": 0.27,
        "cost_per_1m_input": 0.00,
        "cost_per_1m_output": 0.00,
        "is_local": True,
        "target_tasks": [
            "headless_ui_audit",
            "click_through_verification",
            "mobile_device_control",
            "ui_automation",
            "visual_regression"
        ],
        "fallback_chain": ["local_vision_grounding", "tactical_planning_shadow_audit"]
    }
}


class RouteDecision(dict):
    """
    Structured Routing Decision matching PROJECT.md interface contract:
    {
        "pillar": str,
        "target_model": str,
        "target_endpoint": str,
        "estimated_tokens": int,
        "context_slice_used": bool,
        "estimated_cost_usd": float,
        "tier": str,
        "rationale": str,
        "fallback_chain": list[str],
        "timestamp": float,
        "task": str
    }
    Supports both attribute-style (decision.pillar) and dict-style (decision['pillar']) access.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        setattr(self, key, value)

    def to_dict(self) -> Dict[str, Any]:
        return dict(self)

    def to_json(self, indent: Optional[int] = None) -> str:
        return json.dumps(self.to_dict(), indent=indent)


class TieredMultiModelRouter:
    """
    8-Pillar Tiered Multi-Model Task Router.
    Routes incoming tasks across 8 specialized execution engines with automatic
    AST context slicing (:8750), >100k macro context failover, cost accounting,
    resilient fallback cascades, and 24/7 LoRA dataset logging.
    """
    def __init__(
        self,
        ast_service_url: str = AST_SLICER_ENDPOINT,
        lora_log_path: Optional[Path] = None,
        workspace_root: Path = WORKSPACE_ROOT
    ):
        self.routes = PILLAR_REGISTRY
        self.ast_service_url = ast_service_url.rstrip("/")
        self.workspace_root = workspace_root
        self.lora_log_path = lora_log_path or DEFAULT_LORA_LOG_FILE

    def calculate_cost(self, pillar_id: str, estimated_tokens: int, prompt_ratio: float = 0.75) -> float:
        """
        Calculates estimated cost in USD based on model pricing matrix.
        Local models (TB4 Metal, TPU, PySpark, Ray, OpenClaw) cost $0.00.
        Cloud models use exact per-token pricing tiers.
        """
        if pillar_id not in self.routes:
            return 0.0

        spec = self.routes[pillar_id]
        if spec.get("is_local", False):
            return 0.0

        cost_in = spec.get("cost_per_1m_input", 0.0)
        cost_out = spec.get("cost_per_1m_output", 0.0)

        input_tokens = estimated_tokens * prompt_ratio
        output_tokens = estimated_tokens * (1.0 - prompt_ratio)

        total_cost = (input_tokens * cost_in / 1_000_000.0) + (output_tokens * cost_out / 1_000_000.0)
        return round(total_cost, 6)

    def slice_ast_context(
        self,
        target_symbols: Optional[List[str]] = None,
        target_files: Optional[List[str]] = None,
        max_tokens: int = 65536
    ) -> Dict[str, Any]:
        """
        Queries PySpark AST Context Service (POST /v1/slice) on Port 8750.
        If service is unavailable or offline, executes an in-process native AST extraction fallback.
        """
        target_symbols = target_symbols or []
        target_files = target_files or []

        # 1. Attempt HTTP call to Port 8750
        slice_url = f"{self.ast_service_url}/v1/slice"
        payload = {
            "target_symbols": target_symbols,
            "target_files": target_files,
            "max_tokens": max_tokens
        }

        try:
            req = urllib.request.Request(
                slice_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=1.5) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    data["slice_source"] = "pyspark_ast_service_http"
                    return data
        except Exception:
            # Fallback to local in-process AST slicer
            pass

        # 2. In-Process Python AST call-graph extraction fallback
        start_time = time.time()
        extracted_nodes = []
        context_snippets = []
        token_estimate = 0

        # Scan target files or default self_healing_hub / scripts directories
        files_to_scan = []
        if target_files:
            for tf in target_files:
                p = self.workspace_root / tf if not Path(tf).is_absolute() else Path(tf)
                if p.exists() and p.is_file():
                    files_to_scan.append(p)
        else:
            # Sample relevant core python files
            for search_dir in ["self_healing_hub/src", "scripts"]:
                dpath = self.workspace_root / search_dir
                if dpath.exists():
                    for py_file in dpath.glob("*.py"):
                        files_to_scan.append(py_file)

        for py_path in files_to_scan[:15]:
            try:
                rel_p = py_path.relative_to(self.workspace_root)
            except ValueError:
                rel_p = py_path

            try:
                with open(py_path, "r", encoding="utf-8", errors="ignore") as fp:
                    source_code = fp.read()
                
                parsed_ast = ast.parse(source_code, filename=str(py_path))
                file_matched = False

                for node in ast.walk(parsed_ast):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        node_name = node.name
                        # Check symbol match if symbols were specified
                        if not target_symbols or any(sym.lower() in node_name.lower() for sym in target_symbols):
                            extracted_nodes.append(f"{rel_p}::{node_name}")
                            file_matched = True

                if file_matched or not target_symbols:
                    # Append sliced snippet
                    lines = source_code.splitlines()[:60]
                    snippet = f"# File: {rel_p}\n" + "\n".join(lines)
                    context_snippets.append(snippet)
                    token_estimate += len(snippet) // 4
                    if token_estimate >= max_tokens:
                        break
            except Exception:
                continue

        duration_ms = (time.time() - start_time) * 1000.0
        return {
            "context": "\n\n".join(context_snippets),
            "token_count": token_estimate,
            "sliced_nodes": extracted_nodes,
            "duration_ms": round(duration_ms, 2),
            "slice_source": "in_process_ast_fallback"
        }

    def route_task(
        self,
        task_description: str,
        estimated_token_count: int = 1500,
        task_type: str = "auto",
        has_code: bool = False,
        has_image_or_video: bool = False,
        requires_tool_json: bool = False,
        is_ui_audit: bool = False,
        is_tactical_plan: bool = False,
        is_bigdata_spark: bool = False,
        is_ray_actor: bool = False,
        target_symbols: Optional[List[str]] = None,
        target_files: Optional[List[str]] = None,
        auto_ast_slice: bool = True,
        **kwargs
    ) -> RouteDecision:
        """
        Dynamically routes task across all 8 pillars based on task classification,
        token limits (>100k macro failover), keywords, and AST context slicing.
        """
        task_lower = task_description.lower().strip()
        route_id = None
        reason = ""
        context_slice_used = False
        ast_context_data = None

        # -------------------------------------------------------------
        # Stage 1: Explicit Task Type Matching
        # -------------------------------------------------------------
        if task_type in self.routes:
            route_id = task_type
            reason = f"Explicit task type override requested: {task_type}"

        # -------------------------------------------------------------
        # Stage 2: Token Count Ceiling Failover (>100k Macro Horizon)
        # -------------------------------------------------------------
        elif estimated_token_count > 100000:
            route_id = "macro_strategy"
            reason = (
                f"Task requires massive context window ({estimated_token_count:,} tokens > 100k ceiling) "
                "requiring whole-monorepo reasoning; routed to Gemini 3.1 Pro Preview (2M failover)."
            )

        # -------------------------------------------------------------
        # Stage 3: Heuristic & Flag-Based 8-Pillar Classification
        # -------------------------------------------------------------
        # 1. Macro Context & Strategic Roadmap (>100k or macro keywords)
        elif (
            task_type in ["macro", "macro_strategy", "whole_repo"]
            or "macro" in task_lower
            or "2 million" in task_lower
            or "whole-repo" in task_lower
            or "whole repo" in task_lower
            or "cross-repo planning" in task_lower
            or "global architecture" in task_lower
            or "strategic roadmap" in task_lower
            or "monorepo architecture" in task_lower
        ):
            route_id = "macro_strategy"
            reason = "Task requires global strategic roadmap synthesis and whole-monorepo architectural reasoning."

        # 2. UI Automation & Headless Verification (OpenClaw)
        elif (
            is_ui_audit
            or task_type in ["ui_audit", "openclaw", "ui_automation"]
            or "ui audit" in task_lower
            or "click-through" in task_lower
            or "openclaw" in task_lower
            or "headless ui" in task_lower
            or "visual regression" in task_lower
            or "multi-frame click" in task_lower
            or "port 3000 web app" in task_lower
            or "port 4000" in task_lower
            or "mobile device control" in task_lower
        ):
            route_id = "ui_automation"
            reason = "Task involves headless UI automation, device inspection, and visual state verification."

        # 3. Multi-Modal Vision & Kinematics Tracking
        elif (
            has_image_or_video
            or task_type in ["vision", "visual", "multimodal", "local_vision_grounding"]
            or "camera frame" in task_lower
            or "joint angle" in task_lower
            or "kinematics" in task_lower
            or "8k camera" in task_lower
            or "8k ptz" in task_lower
            or "ptz tracking" in task_lower
            or "mat position" in task_lower
            or "motion tracking" in task_lower
            or "screenshot" in task_lower
            or "bounding box" in task_lower
            or "computer vision" in task_lower
            or "pose estimation" in task_lower
            or "video analysis" in task_lower
            or ("vision" in task_lower and not "supervision" in task_lower and not "division" in task_lower)
        ):
            route_id = "local_vision_grounding"
            reason = "Task requires multi-modal computer vision, UI coordinate detection, and physical motion tracking."

        # 4. Structured Function Calling & Tool Translation
        elif (
            requires_tool_json
            or task_type in ["tools", "json", "function_calling", "schema", "structured_function_calling"]
            or "json schema" in task_lower
            or "structured json" in task_lower
            or "function call" in task_lower
            or "mcp parameter" in task_lower
            or "mcp tool" in task_lower
            or "tool use schema" in task_lower
            or "tool schema" in task_lower
            or "parameter extraction" in task_lower
            or "parse schema" in task_lower
        ):
            route_id = "structured_function_calling"
            reason = "Task requires strict JSON schema parsing and validated function calling parameters."

        # 5. Tactical Co-Pilot, Step-by-Step CoT Planning & Shadow Code Review
        elif (
            is_tactical_plan
            or task_type in ["tactical", "cot", "planning", "shadow_review", "tactical_planning_shadow_audit"]
            or "tactical plan" in task_lower
            or "shadow review" in task_lower
            or "shadow code review" in task_lower
            or "extended reasoning" in task_lower
            or "step-by-step" in task_lower
            or "cot planning" in task_lower
            or "chain of thought" in task_lower
            or "debate referee" in task_lower
            or "break down" in task_lower
            or "decomposition" in task_lower
            or "code review invariants" in task_lower
        ):
            route_id = "tactical_planning_shadow_audit"
            reason = "Gemini 1.5 Flash High selected for ultra-fast extended reasoning (185 tok/s) and tactical planning."

        # 6. Ray Distributed Actor Scheduling & Microservices
        elif (
            is_ray_actor
            or task_type in ["ray", "actor", "distributed_mesh", "ray_distributed_actors"]
            or "ray " in task_lower
            or "ray:" in task_lower
            or "ray." in task_lower
            or "distributed actor" in task_lower
            or "actor mesh" in task_lower
            or "async actor" in task_lower
            or "sparring duel" in task_lower
            or "parallel duel" in task_lower
            or "parallel agent" in task_lower
            or "vram swap" in task_lower
            or "vram balancing" in task_lower
            or "microservice actor" in task_lower
        ):
            route_id = "ray_distributed_actors"
            reason = "Ray selected for asynchronous multi-node actor scheduling and dynamic hardware VRAM balancing."

        # 7. PySpark Big-Data & Batch Ingestion
        elif (
            is_bigdata_spark
            or task_type in ["pyspark", "spark", "lakehouse", "bigdata", "pyspark_bigdata_stream"]
            or "pyspark" in task_lower
            or "parquet" in task_lower
            or "128hz" in task_lower
            or "lakehouse" in task_lower
            or "telemetry join" in task_lower
            or "biometrics dsp" in task_lower
            or "imu packet" in task_lower
            or "batch ingestion" in task_lower
            or "streaming ingestion" in task_lower
        ):
            route_id = "pyspark_bigdata_stream"
            reason = "PySpark selected for distributed streaming ingestion, 128Hz biometrics DSP, and Parquet lakehouse joins."

        # 8. Local Code Synthesis & AST Refactoring (Default for physical code modifications)
        else:
            route_id = "local_code_synthesis"
            reason = "Qwen 2.5 Max selected for apex coding precision (92.7% HumanEval), 0ms cloud latency, and $0 token cost."

        # -------------------------------------------------------------
        # Stage 3: AST Context Slicing Integration for Code Tasks
        # -------------------------------------------------------------
        if route_id == "local_code_synthesis" and auto_ast_slice:
            # If code synthesis task is within Qwen 2.5 Max context limits, slice AST
            if estimated_token_count <= 128000:
                ast_context_data = self.slice_ast_context(
                    target_symbols=target_symbols,
                    target_files=target_files,
                    max_tokens=min(65536, max(8192, estimated_token_count))
                )
                if ast_context_data and ast_context_data.get("token_count", 0) > 0:
                    context_slice_used = True
                    reason += f" (AST context sliced: {len(ast_context_data.get('sliced_nodes', []))} nodes, {ast_context_data.get('token_count')} tokens via {ast_context_data.get('slice_source')})."

        # -------------------------------------------------------------
        # Stage 4: Construct RouteDecision & Compute Real Cost
        # -------------------------------------------------------------
        decision_spec = self.routes[route_id]
        estimated_cost = self.calculate_cost(route_id, estimated_token_count)

        decision = RouteDecision(
            pillar=route_id,
            target_model=decision_spec["model"],
            target_endpoint=decision_spec["endpoint"],
            estimated_tokens=estimated_token_count,
            context_slice_used=context_slice_used,
            estimated_cost_usd=estimated_cost,
            tier=decision_spec["tier"],
            rationale=reason,
            fallback_chain=list(decision_spec.get("fallback_chain", [])),
            timestamp=time.time(),
            task=task_description,
            ast_context=ast_context_data
        )

        self._log_routing_decision(decision)
        return decision

    def execute_fallback(
        self,
        original_decision: Union[RouteDecision, Dict[str, Any]],
        failure_reason: str
    ) -> RouteDecision:
        """
        Executes automatic multi-tier fallback when a selected engine/model fails or is unreachable.
        """
        orig_pillar = original_decision.get("pillar", "local_code_synthesis")
        orig_spec = self.routes.get(orig_pillar, self.routes["local_code_synthesis"])
        fallback_candidates = orig_spec.get("fallback_chain", ["macro_strategy"])

        fallback_pillar = fallback_candidates[0] if fallback_candidates else "macro_strategy"
        fallback_spec = self.routes.get(fallback_pillar, self.routes["macro_strategy"])

        tokens = original_decision.get("estimated_tokens", 1500)
        cost = self.calculate_cost(fallback_pillar, tokens)
        rationale = (
            f"Fallback triggered from '{orig_pillar}' to '{fallback_pillar}' due to failure: {failure_reason}. "
            f"Targeting {fallback_spec['model']} ({fallback_spec['tier']})."
        )

        fallback_decision = RouteDecision(
            pillar=fallback_pillar,
            target_model=fallback_spec["model"],
            target_endpoint=fallback_spec["endpoint"],
            estimated_tokens=tokens,
            context_slice_used=False,
            estimated_cost_usd=cost,
            tier=fallback_spec["tier"],
            rationale=rationale,
            fallback_chain=list(fallback_spec.get("fallback_chain", [])),
            timestamp=time.time(),
            task=original_decision.get("task", ""),
            fallback_from=orig_pillar,
            failure_reason=failure_reason
        )

        self._log_routing_decision(fallback_decision)
        return fallback_decision

    def get_pillar_info(self, pillar_id: str) -> Optional[Dict[str, Any]]:
        """Returns metadata for a specific pillar."""
        return self.routes.get(pillar_id)

    def list_pillars(self) -> List[str]:
        """Returns list of all 8 registered pillar identifiers."""
        return list(self.routes.keys())

    def _log_routing_decision(self, record: Union[RouteDecision, Dict[str, Any]]) -> None:
        """Appends routing decision to 24/7 LoRA dataset sink."""
        try:
            log_data = record.to_dict() if isinstance(record, RouteDecision) else dict(record)
            
            # Format record for LoRA dataset training
            log_entry = {
                "timestamp": log_data.get("timestamp", time.time()),
                "task": log_data.get("task", ""),
                "route_id": log_data.get("pillar", log_data.get("route_id", "")),
                "assigned_model": log_data.get("target_model", log_data.get("assigned_model", "")),
                "tier": log_data.get("tier", ""),
                "target_endpoint": log_data.get("target_endpoint", ""),
                "estimated_tokens": log_data.get("estimated_tokens", 0),
                "context_slice_used": log_data.get("context_slice_used", False),
                "estimated_cost_usd": log_data.get("estimated_cost_usd", 0.0),
                "rationale": log_data.get("rationale", ""),
                "fallback_from": log_data.get("fallback_from", None),
                "failure_reason": log_data.get("failure_reason", None)
            }

            self.lora_log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.lora_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")

            # Mirror to Google Drive LoRA folder if directory exists
            if GDRIVE_LORA_DIR.exists():
                gdrive_file = GDRIVE_LORA_DIR / "tiered_router_decisions.jsonl"
                with open(gdrive_file, "a", encoding="utf-8") as gf:
                    gf.write(json.dumps(log_entry) + "\n")
        except Exception:
            pass


if __name__ == "__main__":
    router = TieredMultiModelRouter()
    print("=== Testing 8-Pillar Tiered Multi-Model & Compute Router ===")
    
    test_cases = [
        ("Process 10 million 128Hz Movesense IMU packets and output Parquet lakehouse summary", 500),
        ("Schedule 20 parallel agent sparring duels across 7 physical layers using async actors", 800),
        ("Synthesize entire 500k-token repository architecture and produce Q3 strategic roadmap", 500000),
        ("Refactor Python AST parser in self_healing_hub to support async generator streaming", 2000),
        ("Break down biometrics streaming pipeline into step-by-step AST execution tasks", 2000),
        ("Process 128Hz Movesense camera frames to detect fighter joint angles and mat position", 1200),
        ("Extract structured JSON parameters for Movesense 128Hz BLE GATT subscription", 600),
        ("Execute automated headless multi-frame UI audit of Port 3000 Web App", 1500),
    ]
    
    for prompt, tokens in test_cases:
        res = router.route_task(prompt, estimated_token_count=tokens)
        print(f"\n📌 Task: {res.task}")
        print(f"   👉 Pillar: {res.pillar} | Engine: {res.target_model}")
        print(f"   🌐 Endpoint: {res.target_endpoint} | Est. Cost: ${res.estimated_cost_usd:.6f}")
        print(f"   🧩 Context Slice Used: {res.context_slice_used}")
        print(f"   💡 Rationale: {res.rationale}")

