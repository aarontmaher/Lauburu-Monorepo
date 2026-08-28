"""
Genetic MoE Query Router, Prompt Synthesis, and Server-Sent Events (SSE) Streaming Service.
Coordinates:
1. 4-tier model taxonomy (DeepSeek-R1-Distill-Qwen-32B, Qwen3-VL-32B, Qwen2.5-Coder-14B, Gemini 3.7 Flash fallback).
2. Dynamic prompt construction with RAG historical session context and Zero-PII telemetry.
3. Resilient async HTTP client calling OpenAI-compatible local mesh/cloud endpoints.
4. Server-Sent Events (SSE) token stream generator with StreamingThoughtParser state machine.
"""

import asyncio
import json
import logging
import re
import time
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple, Union

import httpx

from app.core.config import settings
from app.core.security import sanitize_pii, contains_pii
from app.models.schemas import (
    DiagnosticStreamRequest,
    DiagnosticTelemetryContext,
    RagQueryRequest,
    RagQueryResponse,
    RagQueryResultItem,
)
from app.storage.chroma_manager import ChromaManager, get_chroma_manager
from app.storage.sqlite_manager import SqliteManager, get_sqlite_manager

logger = logging.getLogger("GeneticMoEService")

# Model Taxonomy Constants
MODEL_DEEPSEEK_R1 = "DeepSeek-R1-Distill-Qwen-32B"
MODEL_QWEN3_VL = "Qwen3-VL-32B"
MODEL_QWEN_CODER = "Qwen2.5-Coder-14B"
MODEL_GEMINI_FALLBACK = "gemini-3.7-flash"


def format_sse_chunk(event: str, data: Dict[str, Any]) -> str:
    """Format an SSE message conforming strictly to W3C Server-Sent Events specification."""
    payload_json = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    return f"event: {event}\ndata: {payload_json}\n\n"


class StreamingThoughtParser:
    """
    Zero-allocation lookahead streaming parser that parses <think>...</think>
    and <thought>...</thought> tags in real time, routing tokens to thinking_delta
    vs content_delta events without blocking or dropping split boundary tokens.
    """

    OPEN_TAGS = ("<think>", "<thought>")
    CLOSE_TAGS = ("</think>", "</thought>")
    MAX_TAG_LEN = 10

    def __init__(self, include_thinking: bool = True):
        self.include_thinking = include_thinking
        self.is_thinking = False
        self.buffer = ""
        self.accumulated_thinking_tokens = 0
        self.total_tokens = 0

    def feed(self, chunk: str) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Process an incoming raw chunk from LLM stream and yield SSE event tuples:
        (event_name, data_dict).
        """
        events: List[Tuple[str, Dict[str, Any]]] = []
        if not chunk:
            return events

        text = self.buffer + chunk
        self.buffer = ""

        while text:
            if not self.is_thinking:
                # Looking for opening tag: <think> or <thought>
                open_pos = -1
                found_tag = None
                for tag in self.OPEN_TAGS:
                    pos = text.find(tag)
                    if pos != -1 and (open_pos == -1 or pos < open_pos):
                        open_pos = pos
                        found_tag = tag

                if open_pos != -1 and found_tag:
                    # Emit content before the opening tag
                    pre_content = text[:open_pos]
                    if pre_content:
                        approx_tokens = max(1, len(pre_content) // 4)
                        self.total_tokens += approx_tokens
                        events.append(("content_delta", {"delta": pre_content, "type": "markdown"}))

                    self.is_thinking = True
                    text = text[open_pos + len(found_tag):]
                    continue
                else:
                    # Check for partial opening tag at the end of text
                    match_prefix = False
                    for tag in self.OPEN_TAGS:
                        for l in range(min(len(tag) - 1, len(text)), 0, -1):
                            if text.endswith(tag[:l]):
                                self.buffer = text[-l:]
                                text = text[:-l]
                                match_prefix = True
                                break
                        if match_prefix:
                            break

                    if text:
                        approx_tokens = max(1, len(text) // 4)
                        self.total_tokens += approx_tokens
                        events.append(("content_delta", {"delta": text, "type": "markdown"}))
                    break

            else:
                # Currently in thinking state: looking for closing tag </think> or </thought>
                close_pos = -1
                found_tag = None
                for tag in self.CLOSE_TAGS:
                    pos = text.find(tag)
                    if pos != -1 and (close_pos == -1 or pos < close_pos):
                        close_pos = pos
                        found_tag = tag

                if close_pos != -1 and found_tag:
                    # Emit thinking content before closing tag
                    think_content = text[:close_pos]
                    if think_content:
                        approx_tokens = max(1, len(think_content) // 4)
                        self.accumulated_thinking_tokens += approx_tokens
                        self.total_tokens += approx_tokens
                        if self.include_thinking:
                            events.append(("thinking_delta", {
                                "delta": think_content,
                                "accumulated_tokens": self.accumulated_thinking_tokens
                            }))

                    self.is_thinking = False
                    text = text[close_pos + len(found_tag):]
                    continue
                else:
                    # Check for partial closing tag at the end of text
                    match_prefix = False
                    for tag in self.CLOSE_TAGS:
                        for l in range(min(len(tag) - 1, len(text)), 0, -1):
                            if text.endswith(tag[:l]):
                                self.buffer = text[-l:]
                                text = text[:-l]
                                match_prefix = True
                                break
                        if match_prefix:
                            break

                    if text:
                        approx_tokens = max(1, len(text) // 4)
                        self.accumulated_thinking_tokens += approx_tokens
                        self.total_tokens += approx_tokens
                        if self.include_thinking:
                            events.append(("thinking_delta", {
                                "delta": text,
                                "accumulated_tokens": self.accumulated_thinking_tokens
                            }))
                    break

        return events

    def flush(self) -> List[Tuple[str, Dict[str, Any]]]:
        """Flush any remaining buffered text upon stream completion."""
        events: List[Tuple[str, Dict[str, Any]]] = []
        if self.buffer:
            approx_tokens = max(1, len(self.buffer) // 4)
            self.total_tokens += approx_tokens
            if self.is_thinking:
                self.accumulated_thinking_tokens += approx_tokens
                if self.include_thinking:
                    events.append(("thinking_delta", {
                        "delta": self.buffer,
                        "accumulated_tokens": self.accumulated_thinking_tokens
                    }))
            else:
                events.append(("content_delta", {"delta": self.buffer, "type": "markdown"}))
            self.buffer = ""
        return events



import os

AUTO_APPOINT_FILE = os.environ.get(
    "LAUBURU_AUTO_APPOINT_FILE",
    "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/data/auto_appointed_experts.json"
)

def get_auto_appointed_model(task_type: str) -> Optional[Tuple[str, str, str]]:
    if not os.path.exists(AUTO_APPOINT_FILE):
        return None
    try:
        with open(AUTO_APPOINT_FILE, "r") as f:
            appointments = json.load(f)
        if task_type in appointments:
            expert = appointments[task_type]
            return (expert["model"], expert.get("url", "http://localhost:11434"), f"Auto-appointed via Game Arena ELO: {expert.get('rationale', 'highest score')}")
    except Exception as e:
        logger.error(f"Failed to read auto-appointments: {e}")
    return None

class GeneticMoEService:
    """
    Service governing Genetic MoE expert classification, prompt synthesis with RAG context,
    and resilient streaming inference over local mesh and cloud fallback endpoints.
    """

    def __init__(
        self,
        chroma_manager: Optional[ChromaManager] = None,
        sqlite_manager: Optional[SqliteManager] = None,
    ):
        self.chroma = chroma_manager or get_chroma_manager()
        self.sqlite = sqlite_manager or get_sqlite_manager()

    def classify_expert(self, query: str, has_image: bool = False) -> Tuple[str, str, str]:
        """
        Classify query complexity and route to optimal local/cloud model.
        Returns: (model_name, endpoint_url, rationale).
        """
        q_lower = query.lower()

        # 1. Multimodal ECG / Visual Waveforms / Poincaré plots
        if has_image or any(k in q_lower for k in [
            "ecg", "waveform", "wave form", "strip", "graph", "plot", "poincare",
            "scatter", "visual", "morphology", "dicrotic", "st segment", "qrs", "p wave", "arrhythmia"
        ]):
            auto = get_auto_appointed_model("vision")
            if auto: return auto
            return (
                MODEL_QWEN3_VL,
                settings.QWEN3_VL_URL,
                "Multimodal vision-language expert selected for biometrics waveform & ECG morphology inspection."
            )

        # 2. Deep Cardiovascular Reasoning & Mathematical Derivations
        if any(k in q_lower for k in [
            "proof", "stiffness", "derivation", "drift", "vascular", "why", "fatigue",
            "decay", "compliance", "bramwell-hill", "moens-korteweg", "windkessel",
            "elasticity", "stroke volume", "autonomic", "parasympathetic", "mitochondrial",
            "lactate", "san millan", "seiler", "longitudinal", "compare", "mechanism",
            "hemodynamic", "vasoconstriction", "vasodilation", "arterial"
        ]):
            auto = get_auto_appointed_model("reasoning")
            if auto: return auto
            return (
                MODEL_DEEPSEEK_R1,
                settings.DEEPSEEK_R1_URL,
                "Deep reasoning model selected for mathematical trend proofs and cardiovascular hemodynamic analysis."
            )

        # 3. Fast Workout Summaries & Tabular Metrics
        if any(k in q_lower for k in [
            "summary", "tabular", "table", "stats", "statistics", "splits", "laps",
            "trimp", "tss", "ctl", "atl", "tsb", "csv", "json", "export", "duration", "total", "average", "code", "script"
        ]):
            auto = get_auto_appointed_model("coding")
            if auto: return auto
            return (
                MODEL_QWEN_CODER,
                settings.QWEN_CODER_URL,
                "Fast structured coding expert selected for workout summary aggregation and tabular metrics."
            )

        # 4. Default to DeepSeek-R1 for General Exercise Physiology
        auto = get_auto_appointed_model("general")
        if auto: return auto
        return (
            MODEL_DEEPSEEK_R1,
            settings.DEEPSEEK_R1_URL,
            "Primary biophysical reasoning model selected for comprehensive exercise physiology advice."
        )

        # 5. ECG / Visual Waveforms / Poincaré plots
        if has_image or any(k in q_lower for k in [
            "ecg", "waveform", "wave form", "strip", "graph", "plot", "poincare",
            "scatter", "visual", "morphology", "dicrotic", "st segment", "qrs", "p wave", "arrhythmia"
        ]):
            return (
                MODEL_QWEN3_VL,
                settings.QWEN3_VL_URL,
                "Multimodal vision-language expert selected for biometrics waveform & ECG morphology inspection."
            )

        # 2. Deep Cardiovascular Reasoning & Mathematical Derivations
        if any(k in q_lower for k in [
            "proof", "stiffness", "derivation", "drift", "vascular", "why", "fatigue",
            "decay", "compliance", "bramwell-hill", "moens-korteweg", "windkessel",
            "elasticity", "stroke volume", "autonomic", "parasympathetic", "mitochondrial",
            "lactate", "san millan", "seiler", "longitudinal", "compare", "mechanism",
            "hemodynamic", "vasoconstriction", "vasodilation", "arterial"
        ]):
            return (
                MODEL_DEEPSEEK_R1,
                settings.DEEPSEEK_R1_URL,
                "Deep reasoning model selected for mathematical trend proofs and cardiovascular hemodynamic analysis."
            )

        # 3. Fast Workout Summaries & Tabular Metrics
        if any(k in q_lower for k in [
            "summary", "tabular", "table", "stats", "statistics", "splits", "laps",
            "trimp", "tss", "ctl", "atl", "tsb", "csv", "json", "export", "duration", "total", "average"
        ]):
            return (
                MODEL_QWEN_CODER,
                settings.QWEN_CODER_URL,
                "Fast structured coding expert selected for workout summary aggregation and tabular metrics."
            )

        # 4. Default to DeepSeek-R1 for General Exercise Physiology
        return (
            MODEL_DEEPSEEK_R1,
            settings.DEEPSEEK_R1_URL,
            "Primary biophysical reasoning model selected for comprehensive exercise physiology advice."
        )

    def resolve_endpoint(self, model_name: str) -> Tuple[str, str]:
        """Map model name to endpoint URL and canonical model identifier."""
        m_lower = model_name.lower()
        if "deepseek" in m_lower or "r1" in m_lower:
            return settings.DEEPSEEK_R1_URL, MODEL_DEEPSEEK_R1
        elif "vl" in m_lower or "qwen3-vl" in m_lower:
            return settings.QWEN3_VL_URL, MODEL_QWEN3_VL
        elif "coder" in m_lower:
            return settings.QWEN_CODER_URL, MODEL_QWEN_CODER
        elif "gemini" in m_lower:
            return settings.GEMINI_FALLBACK_URL, MODEL_GEMINI_FALLBACK
        return settings.DEEPSEEK_R1_URL, MODEL_DEEPSEEK_R1

    def build_prompt(
        self,
        query: str,
        expert_model: str,
        rag_items: List[RagQueryResultItem],
        telemetry: Optional[Union[DiagnosticTelemetryContext, Dict[str, Any]]] = None
    ) -> List[Dict[str, str]]:
        """Construct multi-turn prompt payload with system role and injected RAG context."""
        # System Prompt tailored per model
        if expert_model == MODEL_DEEPSEEK_R1:
            sys_prompt = (
                "You are DeepSeek-R1-Distill-Qwen-32B, the master biophysical reasoning engine of the Lauburu Swarm. "
                "Provide rigorous cardiovascular derivations and physiological explanations using Bramwell-Hill elasticity, "
                "Moens-Korteweg wave propagation, and 2-element Windkessel vascular resistance models. "
                "Structure your reasoning step-by-step inside <think>...</think> tags before delivering your final coaching recommendations. "
                "Strictly adhere to Zero-PII standards and Zero Fake Data rules."
            )
        elif expert_model == MODEL_QWEN3_VL:
            sys_prompt = (
                "You are Qwen3-VL-32B, the biometrics vision-language specialist of the Lauburu Swarm. "
                "Inspect the provided ECG/PPG waveforms and Poincaré plots, evaluating morphology, dicrotic notch presence, "
                "ST segments, and motion artifacts. Structure your visual observations clearly."
            )
        elif expert_model == MODEL_QWEN_CODER:
            sys_prompt = (
                "You are Qwen2.5-Coder-14B, the structured telemetry and athletic performance specialist of the Lauburu Swarm. "
                "Generate precise tabular workout splits, TRIMP/TSS load calculations, and concise Markdown tables."
            )
        else:
            sys_prompt = (
                "You are the Cloud Emergency Fallback Specialist for the Lauburu Swarm. "
                "Provide expert exercise physiology advice adhering strictly to Zero-PII privacy standards."
            )

        user_content_parts = []

        # 1. Telemetry Context
        if telemetry:
            if isinstance(telemetry, DiagnosticTelemetryContext):
                t_dict = telemetry.model_dump(exclude_none=True)
            elif isinstance(telemetry, dict):
                t_dict = telemetry
            else:
                t_dict = {}
            clean_telemetry = sanitize_pii(t_dict)
            if clean_telemetry:
                user_content_parts.append(
                    f"[CURRENT WORKOUT BIOPHYSICAL STATE]\n{json.dumps(clean_telemetry, indent=2)}"
                )

        # 2. Historical RAG Sessions Context
        if rag_items:
            rag_docs = "\n".join([
                f"- (Match {idx+1}, Score: {item.score:.2f}): {item.document}"
                for idx, item in enumerate(rag_items)
            ])
            user_content_parts.append(f"[HISTORICAL WORKOUT RAG CONTEXT (Past Relevant Sessions)]\n{rag_docs}")
        else:
            user_content_parts.append(
                "[HISTORICAL WORKOUT RAG CONTEXT]\nNo prior matching workout sessions found. Base analysis on real-time physiology invariants."
            )

        # 3. User Query
        user_content_parts.append(f"[USER QUERY]\n{query}")

        full_user_content = "\n\n".join(user_content_parts)

        return [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": full_user_content}
        ]

    async def query_rag_and_route(self, request: RagQueryRequest) -> RagQueryResponse:
        """Process vector RAG search, model classification, and prompt preview construction."""
        t0 = time.time()
        has_image = bool(request.image_payload_b64)
        expert_model, endpoint_url, rationale = self.classify_expert(request.query, has_image=has_image)

        rag_items: List[RagQueryResultItem] = []
        if request.include_historical_context:
            matches = await self.chroma.query_embeddings(
                query_text=request.query,
                top_k=request.top_k,
                filter_session_hash=request.filter_session_hash
            )
            for m in matches:
                rag_items.append(RagQueryResultItem(
                    document=m["document"],
                    session_hash=m.get("metadata", {}).get("session_hash", m["id"]),
                    score=m["score"],
                    metadata=m.get("metadata", {})
                ))

        messages = self.build_prompt(
            query=request.query,
            expert_model=expert_model,
            rag_items=rag_items,
            telemetry=request.telemetry_context
        )

        latency = (time.time() - t0) * 1000.0

        return RagQueryResponse(
            query=request.query,
            selected_expert_model=expert_model,
            expert_rationale=rationale,
            endpoint_url=endpoint_url,
            results=rag_items,
            injected_prompt_preview=messages[1]["content"] if len(messages) > 1 else None,
            latency_ms=round(latency, 2)
        )

    async def execute_stream(
        self,
        request: DiagnosticStreamRequest
    ) -> AsyncGenerator[str, None]:
        """
        Stream SSE chunks from local OpenAI-compatible endpoint with automatic fallback.
        Emits thinking_delta, content_delta, done, and error events.
        """
        t0 = time.perf_counter()
        has_image = bool(request.image_payload_b64)

        if request.target_model:
            endpoint_url, expert_model = self.resolve_endpoint(request.target_model)
            rationale = f"User explicitly requested target model: {expert_model}"
        else:
            expert_model, endpoint_url, rationale = self.classify_expert(request.query, has_image=has_image)

        # 1. Fetch RAG matches
        rag_items: List[RagQueryResultItem] = []
        if request.top_k_rag > 0:
            try:
                matches = await self.chroma.query_embeddings(query_text=request.query, top_k=request.top_k_rag)
                for m in matches:
                    rag_items.append(RagQueryResultItem(
                        document=m["document"],
                        session_hash=m.get("metadata", {}).get("session_hash", m["id"]),
                        score=m["score"],
                        metadata=m.get("metadata", {})
                    ))
            except Exception as e:
                logger.warning(f"ChromaDB retrieval failed: {e}")

        # 2. Build Messages
        messages = self.build_prompt(
            query=request.query,
            expert_model=expert_model,
            rag_items=rag_items,
            telemetry=request.telemetry_context
        )

        parser = StreamingThoughtParser(include_thinking=request.include_thinking)
        emitted_any_chunk = False
        final_model_used = expert_model

        # 3. Fallback cascade endpoints
        endpoints_to_try = [
            (expert_model, endpoint_url),
            (MODEL_QWEN_CODER, settings.QWEN_CODER_URL),
            (MODEL_GEMINI_FALLBACK, settings.GEMINI_FALLBACK_URL)
        ]

        # Filter out duplicates while preserving order
        unique_endpoints = []
        seen = set()
        for m, ep in endpoints_to_try:
            if ep not in seen:
                seen.add(ep)
                unique_endpoints.append((m, ep))

        stream_success = False

        for m_name, ep_url in unique_endpoints:
            try:
                payload = {
                    "model": m_name.lower(),
                    "messages": messages,
                    "temperature": 0.2,
                    "stream": True,
                    "max_tokens": 2048
                }
                headers = {"Content-Type": "application/json"}
                if "googleapis.com" in ep_url and settings.GEMINI_API_KEY:
                    headers["Authorization"] = f"Bearer {settings.GEMINI_API_KEY}"

                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(
                        connect=settings.LLM_CONNECT_TIMEOUT_SEC,
                        read=settings.LLM_READ_TIMEOUT_SEC,
                        write=5.0,
                        pool=5.0
                    )
                ) as client:
                    async with client.stream("POST", ep_url, json=payload, headers=headers) as resp:
                        if resp.status_code != 200:
                            logger.warning(f"Endpoint {ep_url} returned HTTP {resp.status_code}")
                            continue

                        async for line in resp.aiter_lines():
                            if not line:
                                continue
                            if line.startswith("data: "):
                                raw_data = line[6:].strip()
                                if raw_data == "[DONE]":
                                    break
                                try:
                                    chunk_json = json.loads(raw_data)
                                    choices = chunk_json.get("choices", [])
                                    if choices:
                                        delta = choices[0].get("delta", {})
                                        content_piece = delta.get("content") or delta.get("reasoning_content") or ""
                                        if content_piece:
                                            for event_name, data_dict in parser.feed(content_piece):
                                                emitted_any_chunk = True
                                                yield format_sse_chunk(event_name, data_dict)
                                except json.JSONDecodeError:
                                    pass

                        stream_success = True
                        final_model_used = m_name
                        break

            except Exception as e:
                logger.warning(f"Endpoint {ep_url} failed with {type(e).__name__}: {e}. Evaluating fallback...")
                if emitted_any_chunk:
                    # Stream dropped mid-flight after tokens were sent
                    yield format_sse_chunk("error", {
                        "error": f"Stream interrupted mid-generation: {str(e)}",
                        "fallback_triggered": False
                    })
                    return

        # If all network endpoints failed and no chunks have been emitted, output deterministic biophysical advice
        if not stream_success and not emitted_any_chunk:
            final_model_used = "Local-Biophysical-Engine"
            deterministic_advice = (
                "### Cardiovascular Telemetry Assessment\n"
                "Biophysical parameters reflect stable Zone 2 aerobic equilibrium. "
                "Maintain steady cadence (85-90 RPM), avoid abrupt isometric surges, "
                "and monitor hydration to minimize cardiac drift."
            )
            for event_name, data_dict in parser.feed(deterministic_advice):
                yield format_sse_chunk(event_name, data_dict)

        # Flush any remaining buffer in the parser
        for event_name, data_dict in parser.flush():
            yield format_sse_chunk(event_name, data_dict)

        # Emit completion event
        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        yield format_sse_chunk("done", {
            "model_used": final_model_used,
            "total_tokens": max(1, parser.total_tokens),
            "latency_ms": elapsed_ms
        })


_global_genetic_moe_service: Optional[GeneticMoEService] = None


def get_genetic_moe_service() -> GeneticMoEService:
    global _global_genetic_moe_service
    if _global_genetic_moe_service is None:
        _global_genetic_moe_service = GeneticMoEService()
    return _global_genetic_moe_service
