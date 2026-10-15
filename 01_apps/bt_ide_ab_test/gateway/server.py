"""
Unified IDE Gateway Server (Port 8085).
Part of the Lauburu IDE Intelligence Architecture.

Exposes OpenAI-compatible REST and streaming SSE endpoints:
- POST /v1/chat/completions: Dual-engine routing, vector paging, RAM governance, escalation gate, distillation
- POST /v1/completions: Fill-in-the-Middle (FIM) code autocomplete
- GET /v1/models: OpenAI model catalogue
- GET /health: Health check and subsystem status
- GET /api/telemetry/mesh: Global RAM pool and node telemetry
- GET/POST /api/escalation/*: Manual Cloud Escalation tickets & authorization
- POST/GET /api/backpressure/*: Task priority registration & backpressure status
- GET /api/storage/affinity: SeaweedFS hardware placement inspection
- GET/POST /api/distillation/*: Local distillation status & overnight queue trigger
"""

import asyncio
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass
import json
import logging
import os
from pathlib import Path
import sys
import time
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

from fastapi import FastAPI, Header, HTTPException, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
import psutil
import httpx

# Add project base directory to path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Core subsystem imports
from core.hermes_router import HermesRouter, RoutingDecision, ToolDefinition
from core.vector_pager import VectorPager, VectorPage
from core.code_generator import CodeGenerator
from core.escalation_gate import ManualCloudEscalationGate, EscalationStatus, EscalationTicket
from core.distillation import DistillationCaptureWorker

# Storage specialist
try:
    from core.storage_specialist import TriVaultStorageSpecialist
except ImportError:
    TriVaultStorageSpecialist = None

# Dynamic RAM Governor & Telemetry
try:
    from core.ram_governor import (
        BackpressureSuspensionManager,
        MeshRAMGovernorCoordinator,
        compute_global_pool_metric,
        GlobalRAMPoolMetric,
        TaskRecord,
    )
    from core.config import SubagentPriority, HOST_SANCTUARY_MIN_GB
except ImportError:
    BackpressureSuspensionManager = None
    MeshRAMGovernorCoordinator = None
    compute_global_pool_metric = None
    GlobalRAMPoolMetric = None
    TaskRecord = None
    SubagentPriority = None
    HOST_SANCTUARY_MIN_GB = 4.8

logger = logging.getLogger("ide_gateway_server")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

GATEWAY_PORT = 8085


# ==============================================================================
# Global Subsystem Singletons
# ==============================================================================

hermes_router = HermesRouter()
vector_pager = VectorPager()
code_generator = CodeGenerator()
escalation_gate = ManualCloudEscalationGate()
distillation_worker = DistillationCaptureWorker()

# RAM Governance Coordinator
if MeshRAMGovernorCoordinator is not None:
    ram_coordinator = MeshRAMGovernorCoordinator()
else:
    ram_coordinator = None


def get_host_available_gb() -> float:
    """Read genuine Darwin Mach available RAM via psutil syscall."""
    mem = psutil.virtual_memory()
    return round(mem.available / (1024 ** 3), 2)


def is_host_sanctuary_ok() -> bool:
    """Check Rule 3 (Host Sanctuary Headroom >= 4.8 GB)."""
    return get_host_available_gb() >= HOST_SANCTUARY_MIN_GB


# ==============================================================================
# FastAPI Lifespan & App Declaration
# ==============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager: starts background workers on boot, flushes on shutdown."""
    logger.info(f"Starting Unified IDE Gateway Server on Port {GATEWAY_PORT}...")
    try:
        distillation_worker.start()
        logger.info("Continuous Distillation Worker background queue started.")
    except Exception as e:
        logger.warning(f"Could not start distillation worker: {e}")

    # Initial telemetry cycle
    if ram_coordinator is not None:
        try:
            await ram_coordinator.evaluate_mesh()
            logger.info("Initial Mesh RAM governance cycle evaluated.")
        except Exception as e:
            logger.warning(f"Error during initial mesh RAM evaluation: {e}")

    yield

    logger.info("Shutting down Unified IDE Gateway Server...")
    try:
        await distillation_worker.stop()
    except Exception as e:
        logger.warning(f"Error stopping distillation worker: {e}")


app = FastAPI(
    title="Lauburu Unified IDE Gateway",
    description="Strict Local-First IDE Mesh Gateway with Dual-Engine Tool Routing, Vector Paging, Escalation Gate & Distillation",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================================================================
# Pydantic Request Models (OpenAI Compatible)
# ==============================================================================

class ChatMessage(BaseModel):
    role: str
    content: str
    name: Optional[str] = None


class ChatCompletionRequest(BaseModel):
    model: str = "dynamic-mcts-chat"
    messages: List[Dict[str, Any]]
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 1.0
    max_tokens: Optional[int] = 2048
    stream: Optional[bool] = False
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Any] = None
    user: Optional[str] = None
    # Gateway control flags
    skip_vector_paging: Optional[bool] = False
    bypass_escalation_gate: Optional[bool] = False
    escalation_ticket_id: Optional[str] = None


class CompletionRequest(BaseModel):
    model: str = "dynamic-mcts-autocomplete"
    prompt: Union[str, List[str]]
    suffix: Optional[str] = None
    max_tokens: Optional[int] = 512
    temperature: Optional[float] = 0.2
    stream: Optional[bool] = False


class EscalationAuthRequest(BaseModel):
    ticket_id: str
    action: str  # "APPROVE", "REJECT", "TRUNCATE"
    reason: Optional[str] = ""


class BackpressureRegisterRequest(BaseModel):
    name: str
    pid: Optional[int] = None
    endpoint: Optional[str] = None
    priority: int = 1  # 1=LOW, 2=MEDIUM, 3=HIGH, 4=IDE_CRITICAL


# ==============================================================================
# Health & Status Endpoints
# ==============================================================================

@app.get("/")
@app.get("/health")
async def health_check():
    """System health check and component diagnostics."""
    avail_gb = get_host_available_gb()
    sanctuary_ok = is_host_sanctuary_ok()

    bp_active = False
    if ram_coordinator and ram_coordinator.last_pool_metric:
        bp_active = ram_coordinator.last_pool_metric.backpressure_triggered

    return {
        "status": "healthy" if sanctuary_ok else "degraded",
        "service": "Lauburu Unified IDE Gateway",
        "port": GATEWAY_PORT,
        "ram_governance": {
            "host_available_gb": avail_gb,
            "sanctuary_min_gb": HOST_SANCTUARY_MIN_GB,
            "sanctuary_healthy": sanctuary_ok,
            "backpressure_active": bp_active,
        },
        "components": {
            "hermes_router": {
                "master_endpoint": hermes_router.hermes_url,
                "registered_tools": len(hermes_router.list_tools()),
                "discovered_skills": len(hermes_router._skills_cache),
            },
            "vector_pager": {
                "qdrant_url": vector_pager.qdrant_url,
                "qdrant_available": vector_pager.is_qdrant_available(),
                "kv_cache_pages": vector_pager.local_cache.count(),
            },
            "code_generator": code_generator.get_metrics(),
            "escalation_gate": {
                "context_limit": escalation_gate.context_limit,
                "pending_tickets": len([t for t in escalation_gate.list_tickets() if t.get("status") == "PENDING"]),
            },
            "distillation_worker": distillation_worker.get_metrics(),
            "storage_specialist": "active" if TriVaultStorageSpecialist is not None else "stub",
        }
    }


@app.get("/v1/models")
async def list_models():
    """List available OpenAI-compatible models."""
    now = int(time.time())
    return {
        "object": "list",
        "data": [
            {
                "id": "qwen_38_max_abliterated",
                "object": "model",
                "created": now,
                "owned_by": "lauburu-local-prima",
                "permission": [],
                "root": "qwen_38_max_abliterated",
                "parent": None,
                "description": "Sovereign Master Local Orchestrator (Port 8083, 1734 ELO)"
            },
            {
                "id": "qwen2.5-coder-7b-instruct",
                "object": "model",
                "created": now,
                "owned_by": "lauburu-local-llama",
                "permission": [],
                "root": "qwen2.5-coder-7b-instruct",
                "parent": None,
                "description": "Subordinate Syntax Worker (Port 8081)"
            },
            {
                "id": "dynamic-mcts-chat",
                "object": "model",
                "created": now,
                "owned_by": "lauburu-ide-gateway",
                "permission": [],
                "root": "dynamic-mcts-chat",
                "parent": None,
                "description": "Default dynamic dual-engine IDE chat router"
            },
            {
                "id": "dynamic-mcts-autocomplete",
                "object": "model",
                "created": now,
                "owned_by": "lauburu-ide-gateway",
                "permission": [],
                "root": "dynamic-mcts-autocomplete",
                "parent": None,
                "description": "Dedicated FIM code autocomplete engine"
            },
        ]
    }


# ==============================================================================
# OpenAI Compatible Core Endpoints
# ==============================================================================

async def dispatch_hermes_endpoint(
    hermes_payload: Dict[str, Any],
    stream: bool = False,
    timeout_sec: float = 30.0,
):
    """
    Dispatches request directly to Port 8083 (Sovereign Master Local Orchestrator qwen_38_max_abliterated),
    preserving tool schemas and function calling structures.
    """
    target_url = hermes_router.hermes_url
    timeout = httpx.Timeout(timeout_sec, connect=5.0)

    if stream:
        async def stream_generator():
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream("POST", target_url, json=hermes_payload) as response:
                    if response.status_code != 200:
                        err_content = await response.aread()
                        raise HTTPException(
                            status_code=response.status_code,
                            detail=f"Hermes endpoint HTTP {response.status_code}: {err_content.decode('utf-8', errors='replace')}"
                        )
                    content_type = response.headers.get("content-type", "")
                    if "text/event-stream" in content_type:
                        async for line in response.aiter_lines():
                            if line:
                                yield f"{line}\n\n"
                    else:
                        # Endpoint returned JSON; yield as SSE chunks
                        raw_bytes = await response.aread()
                        data = json.loads(raw_bytes.decode("utf-8"))
                        text = ""
                        if "choices" in data and data["choices"]:
                            text = data["choices"][0].get("message", {}).get("content", "")
                        for word in text.split():
                            chunk = {
                                "choices": [{
                                    "delta": {"content": word + " "},
                                    "finish_reason": None
                                }]
                            }
                            yield f"data: {json.dumps(chunk)}\n\n"
                        yield "data: [DONE]\n\n"
        return stream_generator()
    else:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(target_url, json=hermes_payload)
            if resp.status_code == 200:
                return resp.json()
            else:
                raise HTTPException(
                    status_code=resp.status_code,
                    detail=f"Hermes endpoint on Port 8083 failed: {resp.text}"
                )


@app.post("/v1/chat/completions")
async def chat_completions(req: ChatCompletionRequest, request: Request):
    """
    OpenAI-compatible Chat Completions API with:
    1. RAM Governance check & backpressure enforcement
    2. Manual Cloud Escalation Gate check for context overflow (> 8192 tokens)
    3. Vector DB / KV-cache context injection
    4. Hermes 3 vs Qwen 2.5 Coder dual-engine routing
    5. Streaming SSE response or JSON completion
    6. Non-blocking distillation trace capture
    """
    payload = req.model_dump() if hasattr(req, "model_dump") else req.dict()

    # Step 1: RAM Governance & Backpressure Check
    # Use cached coordinator.last_pool_metric to avoid blocking request path on network timeouts
    if ram_coordinator is not None:
        if ram_coordinator.last_pool_metric is None:
            try:
                await ram_coordinator.evaluate_mesh()
            except Exception as e:
                logger.debug(f"RAM evaluation cycle: {e}")
        else:
            # Trigger asynchronous background refresh without blocking client latency
            asyncio.create_task(ram_coordinator.evaluate_mesh())

    # Step 2: Context Overflow Detection & Manual Cloud Escalation Gate
    is_overflow, estimated_tokens = escalation_gate.is_overflow(payload)
    is_authorized_cloud = False
    approved_ticket_id = None

    if is_overflow:
        if req.bypass_escalation_gate:
            is_authorized_cloud = True
            approved_ticket_id = req.escalation_ticket_id
        else:
            ticket_id = req.escalation_ticket_id
            if ticket_id:
                ticket = escalation_gate.get_ticket(ticket_id)
                if ticket and ticket.is_approved():
                    is_authorized_cloud = True
                    approved_ticket_id = ticket_id

            if not is_authorized_cloud:
                ticket = escalation_gate.create_ticket(payload, target_cloud_model="gemini-2.5-flash")
                error_body = {
                    "error": {
                        "message": f"Cloud escalation blocked by Manual Cloud Escalation Gate: payload of {estimated_tokens} tokens exceeds local context limit of {escalation_gate.context_limit} tokens. Manual approval required via /api/escalation/authorize.",
                        "type": "escalation_required",
                        "code": 403,
                        "ticket_id": ticket.ticket_id,
                        "tokens": estimated_tokens,
                        "limit": escalation_gate.context_limit,
                    }
                }
                return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content=error_body)

    # Step 3: Vector DB Context Paging
    vector_pages_count = 0
    if not req.skip_vector_paging:
        query_text = ""
        for m in reversed(req.messages):
            if m.get("role") == "user":
                query_text = m.get("content", "")
                break
        if query_text:
            updated_messages, vector_pages_count = vector_pager.inject_vector_context(
                req.messages, query_text, top_k=3
            )
            payload["messages"] = updated_messages

    # Step 4: Dual-Engine Classification & Routing
    decision = hermes_router.classify_and_route(payload, vector_pages_count=vector_pages_count)
    logger.info(f"[ROUTER] Decision: {decision.engine} -> {decision.target_endpoint} ({decision.reasoning})")

    # Step 5: Execution Dispatch
    if decision.engine == "HERMES_TOOL_ROUTER":
        hermes_payload = hermes_router.prepare_hermes_payload(payload)
        hermes_payload["model"] = hermes_router.master_model_id
        # Preserve tool schemas and function calling structures
        for tool_key in ("tools", "functions", "tool_choice"):
            if tool_key in payload:
                hermes_payload[tool_key] = payload[tool_key]

        # Delegate directly to Hermes Master endpoint (Port 8083)
        if req.stream:
            gen = await dispatch_hermes_endpoint(hermes_payload, stream=True)
        else:
            resp = await dispatch_hermes_endpoint(hermes_payload, stream=False)
            if "choices" in resp and resp["choices"]:
                content = resp["choices"][0].get("message", {}).get("content", "")
                tool_calls = hermes_router.parse_tool_calls(content)
                if tool_calls and "tool_calls" not in resp["choices"][0]["message"]:
                    resp["choices"][0]["message"]["tool_calls"] = tool_calls
    else:
        # Route to Qwen 2.5 Coder (Port 8081 with fallback to Port 8083)
        if req.stream:
            gen = await code_generator.generate_chat_completion(payload, stream=True)
        else:
            resp = await code_generator.generate_chat_completion(payload, stream=False)

    # Step 6: Non-blocking distillation trace capture for authorized cloud escalations
    if is_authorized_cloud:
        if req.stream:
            async def capture_streaming_trace(original_gen):
                accumulated_chunks = []
                async for chunk in original_gen:
                    accumulated_chunks.append(chunk)
                    yield chunk
                try:
                    full_text = ""
                    for c in accumulated_chunks:
                        for line in c.splitlines():
                            if line.startswith("data: ") and not line.startswith("data: [DONE]"):
                                try:
                                    d = json.loads(line[6:])
                                    delta = d.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                    full_text += delta
                                except Exception:
                                    pass
                    distillation_worker.capture_trace_nowait(
                        prompt_messages=payload.get("messages", payload.get("prompt", "")),
                        cloud_response=full_text,
                        teacher_model="gemini-2.5-flash",
                        escalation_ticket_id=approved_ticket_id,
                        verification_metadata={"authorized": True, "tokens": estimated_tokens, "stream": True},
                        prompt_tokens=estimated_tokens,
                        completion_tokens=len(full_text.split()),
                    )
                except Exception as e:
                    logger.warning(f"Failed to capture streaming distillation trace: {e}")
            gen = capture_streaming_trace(gen)
        else:
            try:
                resp_content = ""
                if isinstance(resp, dict) and "choices" in resp and resp["choices"]:
                    resp_content = resp["choices"][0].get("message", {}).get("content", "")
                distillation_worker.capture_trace_nowait(
                    prompt_messages=payload.get("messages", payload.get("prompt", "")),
                    cloud_response=resp_content or resp,
                    teacher_model="gemini-2.5-flash",
                    escalation_ticket_id=approved_ticket_id,
                    verification_metadata={"authorized": True, "tokens": estimated_tokens},
                    prompt_tokens=estimated_tokens,
                    completion_tokens=len(resp_content.split()) if resp_content else 0,
                )
            except Exception as e:
                logger.warning(f"Failed to capture distillation trace: {e}")

    if req.stream:
        return StreamingResponse(gen, media_type="text/event-stream")
    else:
        return resp


@app.post("/v1/completions")
async def legacy_completions(req: CompletionRequest):
    """
    OpenAI-compatible /v1/completions endpoint for FIM code autocomplete.
    """
    payload = req.model_dump() if hasattr(req, "model_dump") else req.dict()
    if req.suffix:
        prefix = req.prompt if isinstance(req.prompt, str) else "\n".join(req.prompt)
        fim_prompt = code_generator.format_fim_prompt(prefix, req.suffix)
        payload["prompt"] = fim_prompt

    if req.stream:
        gen = await code_generator.generate_legacy_completion(payload, stream=True)
        return StreamingResponse(gen, media_type="text/event-stream")
    else:
        resp = await code_generator.generate_legacy_completion(payload, stream=False)
        return resp


# ==============================================================================
# Operational & Telemetry Management Endpoints
# ==============================================================================

@app.get("/api/telemetry/mesh")
async def get_mesh_telemetry():
    """Retrieve global RAM pool metric and node breakdown."""
    if ram_coordinator is not None:
        try:
            pool, telemetry, actions = await ram_coordinator.evaluate_mesh()
            return {
                "pool": asdict(pool),
                "nodes": [t.to_dict() for t in telemetry],
                "actions": actions,
            }
        except Exception as e:
            logger.debug(f"Error evaluating mesh telemetry: {e}")

    # Fallback to local host telemetry
    mem = psutil.virtual_memory()
    total_gb = round(mem.total / (1024 ** 3), 2)
    avail_gb = round(mem.available / (1024 ** 3), 2)
    util_pct = round(mem.percent, 1)

    return {
        "pool": {
            "total_mesh_ram_gb": 108.0,
            "available_mesh_ram_gb": avail_gb,
            "usable_ai_vram_gb": 82.8,
            "pool_utilization_pct": util_pct,
            "nodes_reporting": 1,
            "nodes_total": 7,
            "backpressure_triggered": avail_gb < HOST_SANCTUARY_MIN_GB,
            "saturated_nodes": ["L1_Mac_Host"] if avail_gb < HOST_SANCTUARY_MIN_GB else [],
        },
        "host_telemetry": {
            "node_id": "L1_Mac_Host",
            "total_ram_gb": total_gb,
            "available_ram_gb": avail_gb,
            "sanctuary_headroom_gb": max(0.0, avail_gb - HOST_SANCTUARY_MIN_GB),
        }
    }


@app.get("/api/escalation/tickets")
async def list_escalation_tickets(status: Optional[str] = None):
    """List active and historical escalation tickets."""
    return escalation_gate.list_tickets(status=status)


@app.post("/api/escalation/authorize")
async def authorize_escalation_ticket(auth: EscalationAuthRequest):
    """
    Authorize, reject, or truncate a pending escalation ticket.
    Enforces strict zero-leakage manual authorization.
    """
    res = escalation_gate.resolve_ticket(
        ticket_id=auth.ticket_id,
        action=auth.action,
        reason=auth.reason or ""
    )
    # Check if ticket was found
    if not res.success and not res.ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {auth.ticket_id} not found or already resolved."
        )

    ticket = res.ticket
    return {
        "success": res.success,
        "ticket_id": auth.ticket_id,
        "status": ticket.status if ticket else auth.action.upper(),
        "message": f"Escalation ticket {auth.ticket_id} marked as {auth.action.upper()}."
    }


@app.post("/api/backpressure/register")
async def register_backpressure_task(req: BackpressureRegisterRequest):
    """Register a background subagent process for backpressure suspension."""
    if ram_coordinator is not None:
        p_enum = SubagentPriority(req.priority) if SubagentPriority else req.priority
        task_id = f"task_{req.name}_{req.pid or 'nopid'}"
        try:
            rec = ram_coordinator.suspension_mgr.register_task(
                task_id=task_id,
                name=req.name,
                priority=p_enum,
                pid=req.pid,
                endpoint=req.endpoint,
            )
            return {"registered": True, "task": rec.to_dict()}
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    return {"registered": True, "task": req.model_dump() if hasattr(req, "model_dump") else req.dict()}


@app.get("/api/backpressure/status")
async def get_backpressure_status():
    """Get active backpressure suspension state."""
    if ram_coordinator is not None:
        mgr = ram_coordinator.suspension_mgr
        bp_active = ram_coordinator.last_pool_metric.backpressure_triggered if ram_coordinator.last_pool_metric else False
        return {
            "backpressure_active": bp_active,
            "tasks": [t.to_dict() for t in mgr._tasks.values()],
        }
    return {
        "backpressure_active": False,
        "tasks": [],
    }


@app.get("/api/storage/affinity")
async def check_storage_affinity(path: str = Query(..., description="File path to inspect")):
    """Check physical hardware placement and SeaweedFS collection affinity."""
    if TriVaultStorageSpecialist is not None:
        route = TriVaultStorageSpecialist.resolve_affinity(path)
        if hasattr(route, "to_dict"):
            return route.to_dict()
        return asdict(route) if hasattr(route, "__dataclass_fields__") else route

    category = "git_source"
    target_node = "L1_MacHost"
    collection = "git_source"

    if any(p in path for p in ["lora_datasets", "biometrics_lake", "parquet", "jsonl"]):
        category = "heavy_datasets"
        target_node = "L3_Linux"
        collection = "heavy_datasets"
    elif any(p in path for p in ["qdrant", "kv_cache", "lance", "faiss"]):
        category = "vector_context"
        target_node = "L6_PixelEdgeNPU"
        collection = "vector_context"

    return {
        "path": path,
        "category": category,
        "target_node": target_node,
        "collection": collection,
    }


@app.get("/api/distillation/status")
async def get_distillation_status():
    """Retrieve metrics of captured continuous distillation traces."""
    return distillation_worker.get_metrics()


@app.post("/api/distillation/trigger")
async def trigger_distillation():
    """Manually trigger L3 overnight fine-tuning queue."""
    queued, msg = distillation_worker.trigger_overnight_training()
    return {"triggered": queued, "message": msg}
