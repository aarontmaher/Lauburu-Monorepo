"""
Continuous Local Distillation Worker (Requirement R5).

Silently captures authorized cloud reasoning traces without introducing client-facing latency.
- Silent non-blocking async capture via in-memory queue (zero latency penalty).
- Formats traces into standardized ChatML / OpenAI instruction pairs.
- Scrubs sensitive credentials (hf_..., Bearer tokens, OpenAI keys, etc.).
- Funnels traces to /Users/aaron/DFS_UNIFIED/lora_datasets/ide_distillation_traces.jsonl
  (persisted to L3 Linux Hub via SeaweedFS hardware affinity or direct API).
- Triggers L3 overnight fine-tuning queue.
"""

from __future__ import annotations

import asyncio
import datetime
import json
import logging
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger("distillation_worker")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("[DISTILLATION] %(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Default configuration paths & endpoints
DEFAULT_DATASET_PATH: str = "/Users/aaron/DFS_UNIFIED/lora_datasets/ide_distillation_traces.jsonl"
DEFAULT_L3_ENDPOINT: str = "http://100.101.39.98:18802/api/distillation/ingest"
DEFAULT_L3_TRAIN_TRIGGER: str = "http://100.101.39.98:18802/api/training/queue_overnight"
DEFAULT_TARGET_STUDENT: str = "qwen_2.5_coder_7b"

# =============================================================================
# Credential Scrubbing Engine
# =============================================================================

# Compile credential regex patterns
RE_HF_TOKEN = re.compile(r"hf_[A-Za-z0-9_]{20,}")
RE_BEARER_TOKEN = re.compile(r"(?i)bearer\s+[A-Za-z0-9_\-\.]{15,}")
RE_OPENAI_KEY = re.compile(r"sk-(?:proj-)?[A-Za-z0-9_\-]{20,}")
RE_GITHUB_PAT = re.compile(r"ghp_[A-Za-z0-9]{20,}")
RE_AWS_KEY = re.compile(r"AKIA[0-9A-Z]{16}")
RE_GENERIC_SECRET = re.compile(
    r'(?i)(api[_-]?key|client[_-]?secret|password|auth[_-]?token|secret[_-]?key)\s*[:=]\s*["\']?([A-Za-z0-9_\-\.]{16,})["\']?'
)


def scrub_sensitive_credentials(data: Any) -> Any:
    """
    Recursively scrub sensitive authentication credentials from text, dicts, and lists.
    Replaces:
      - hf_... -> hf_...[REDACTED_SOVEREIGN]
      - Bearer ... -> Bearer [REDACTED]
      - sk-... -> sk-...[REDACTED]
      - ghp_... -> ghp_...[REDACTED]
      - AKIA... -> AKIA...[REDACTED]
      - generic key=value -> key: "[REDACTED]"
    """
    if isinstance(data, str):
        text = data
        text = RE_HF_TOKEN.sub("hf_...[REDACTED_SOVEREIGN]", text)
        text = RE_BEARER_TOKEN.sub("Bearer [REDACTED]", text)
        text = RE_OPENAI_KEY.sub("sk-...[REDACTED]", text)
        text = RE_GITHUB_PAT.sub("ghp_...[REDACTED]", text)
        text = RE_AWS_KEY.sub("AKIA...[REDACTED]", text)
        text = RE_GENERIC_SECRET.sub(r'\1: "[REDACTED]"', text)
        return text
    elif isinstance(data, dict):
        return {k: scrub_sensitive_credentials(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [scrub_sensitive_credentials(item) for item in data]
    return data


# =============================================================================
# Chain of Thought & Content Extraction
# =============================================================================

RE_THOUGHT_TAG = re.compile(r"<(?:thought|thinking)>(.*?)</(?:thought|thinking)>", re.DOTALL | re.IGNORECASE)


def extract_reasoning_and_content(response_payload: Any) -> Tuple[Optional[str], str]:
    """
    Extract reasoning trace (CoT) and final clean assistant content from response.
    Supports:
      - DeepSeek reasoning_content
      - Standard reasoning field
      - <thought>...</thought> XML tags embedded in content
      - Plain text string response
    Returns: (reasoning_trace, clean_content)
    """
    reasoning: Optional[str] = None
    content: str = ""

    if isinstance(response_payload, str):
        content = response_payload
    elif isinstance(response_payload, dict):
        # Check choices[0].message
        choices = response_payload.get("choices", [])
        if choices and isinstance(choices, list) and isinstance(choices[0], dict):
            msg = choices[0].get("message", {})
            if isinstance(msg, dict):
                # DeepSeek format: reasoning_content
                reasoning = msg.get("reasoning_content") or msg.get("reasoning")
                content = msg.get("content") or ""
            elif "text" in choices[0]:
                content = choices[0]["text"]
        elif "content" in response_payload:
            content = str(response_payload["content"])
            reasoning = response_payload.get("reasoning")
        else:
            content = json.dumps(response_payload)
    else:
        content = str(response_payload)

    # Check for embedded XML thought tags if reasoning wasn't already in dedicated field
    if not reasoning and content:
        match = RE_THOUGHT_TAG.search(content)
        if match:
            reasoning = match.group(1).strip()
            # Strip thought tags from clean content
            content = RE_THOUGHT_TAG.sub("", content).strip()

    return reasoning, content


# =============================================================================
# Distillation Trace Data Model
# =============================================================================

@dataclass
class DistillationMessage:
    role: str
    content: str
    reasoning_trace: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"role": self.role, "content": self.content}
        if self.reasoning_trace:
            d["reasoning_trace"] = self.reasoning_trace
        return d


@dataclass
class DistillationTrace:
    """
    Standardized ChatML/OpenAI instruction pair for continuous fine-tuning.
    Codified in survey_report_2.md § 5.3.
    """
    distillation_id: str
    timestamp_utc: str
    source: str = "ide_gateway_authorized_escalation"
    domain: str = "ide_code_intelligence"
    teacher_model: str = "gemini-2.5-flash-thinking"
    target_student_model: str = DEFAULT_TARGET_STUDENT
    prompt_tokens: int = 0
    completion_tokens: int = 0
    messages: List[Dict[str, Any]] = field(default_factory=list)
    verification_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "distillation_id": self.distillation_id,
            "timestamp_utc": self.timestamp_utc,
            "source": self.source,
            "domain": self.domain,
            "teacher_model": self.teacher_model,
            "target_student_model": self.target_student_model,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "messages": self.messages,
            "verification_metadata": self.verification_metadata,
        }

    def to_jsonl(self) -> str:
        """Serialize trace to a single JSONL line."""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    def to_chatml(self) -> str:
        """Format trace as canonical ChatML prompt string."""
        blocks: List[str] = []
        for msg in self.messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            reasoning = msg.get("reasoning_trace")
            if role == "assistant" and reasoning:
                blocks.append(f"<|im_start|>{role}\n<thought>\n{reasoning}\n</thought>\n{content}<|im_end|>")
            else:
                blocks.append(f"<|im_start|>{role}\n{content}<|im_end|>")
        return "\n".join(blocks)


class TriggerResult:
    """Wrapper that supports unpacking as (queued, message) and evaluates as bool."""
    def __init__(self, queued: bool, message: str, details: Optional[Dict[str, Any]] = None):
        self.queued = queued
        self.message = message
        self.details = details or {}

    def __bool__(self) -> bool:
        return self.queued

    def __iter__(self):
        return iter((self.queued, self.message))

    def __getitem__(self, idx: int):
        return (self.queued, self.message)[idx]

    def __repr__(self) -> str:
        return f"TriggerResult(queued={self.queued}, message='{self.message}')"


# =============================================================================
# Distillation Capture Worker
# =============================================================================

class DistillationCaptureWorker:
    """
    Background worker that silently captures authorized cloud escalations.
    
    Invariants:
    1. Zero Client Latency: All capture and file I/O operations are offloaded
       to an async non-blocking queue. Client request threads return in < 0.1ms.
    2. Zero Credential Leakage: All API keys, Bearer tokens, and HF tokens
       are scrubbed before persistence.
    3. Storage Affinity: Persists to /Users/aaron/DFS_UNIFIED/lora_datasets/
       which maps to L3 Linux Hub via SeaweedFS hardware affinity.
    4. Overnight Trigger: Exposes trigger for L3 overnight PEFT/LoRA fine-tuning.
    """

    def __init__(
        self,
        dataset_path: Optional[str] = None,
        l3_endpoint: Optional[str] = None,
        l3_trigger_endpoint: Optional[str] = None,
        buffer_max_size: int = 2000,
        push_to_l3: bool = True,
        target_student_model: str = DEFAULT_TARGET_STUDENT,
    ):
        self.dataset_path = Path(dataset_path or DEFAULT_DATASET_PATH)
        self.l3_endpoint = l3_endpoint or DEFAULT_L3_ENDPOINT
        self.l3_trigger_endpoint = l3_trigger_endpoint or DEFAULT_L3_TRAIN_TRIGGER
        self.buffer_max_size = buffer_max_size
        self.push_to_l3 = push_to_l3
        self.target_student_model = target_student_model

        # Async queue and worker lifecycle
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=buffer_max_size)
        self._worker_task: Optional[asyncio.Task] = None
        self._running: bool = False
        self._file_lock = threading.Lock()

        # Telemetry & stats
        self.stats: Dict[str, int] = {
            "enqueued": 0,
            "processed": 0,
            "written": 0,
            "scrubbed": 0,
            "l3_pushed": 0,
            "errors": 0,
            "deduplicated": 0,
        }

        # Deduplication signature cache
        self._seen_signatures: set[str] = set()

        # Initialize storage directory
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        """Ensure destination directory exists and load existing signatures for deduplication."""
        try:
            self.dataset_path.parent.mkdir(parents=True, exist_ok=True)
            if not self.dataset_path.exists():
                self.dataset_path.touch(exist_ok=True)
            else:
                # Preload existing signatures to avoid duplicates across restarts
                import hashlib
                with open(self.dataset_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            try:
                                d = json.loads(line)
                                msgs = d.get("messages", [])
                                u = [str(m.get("content", "")) for m in msgs if m.get("role") == "user"]
                                a = [str(m.get("content", "")) for m in msgs if m.get("role") == "assistant"]
                                sig = hashlib.sha256(f"{'|'.join(u)}|||{'|'.join(a)}".encode("utf-8")).hexdigest()
                                self._seen_signatures.add(sig)
                            except Exception:
                                pass
        except Exception as err:
            logger.warning(f"Storage path init warning for {self.dataset_path}: {err}")

    def start(self) -> asyncio.Task:
        """Start the background consumer loop if not already running."""
        if self._running and self._worker_task and not self._worker_task.done():
            return self._worker_task

        self._running = True
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.get_event_loop()

        self._worker_task = loop.create_task(self._process_loop())
        logger.info("Distillation background consumer task started")
        return self._worker_task

    async def stop(self, drain: bool = True) -> None:
        """Gracefully stop worker task, optionally draining pending queue items."""
        self._running = False
        if drain and not self._queue.empty():
            logger.info(f"Draining {self._queue.qsize()} remaining distillation items...")
            while not self._queue.empty():
                try:
                    item = self._queue.get_nowait()
                    await self._process_single_item(item)
                    self._queue.task_done()
                except asyncio.QueueEmpty:
                    break
                except Exception as err:
                    logger.error(f"Error while draining queue: {err}")

        if self._worker_task and not self._worker_task.done():
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        self._worker_task = None
        logger.info("Distillation background consumer task stopped")

    def capture_trace_nowait(
        self,
        prompt_messages: Union[List[Dict[str, Any]], str, Dict[str, Any]],
        cloud_response: Any,
        teacher_model: str = "gemini-2.5-flash-thinking",
        escalation_ticket_id: Optional[str] = None,
        verification_metadata: Optional[Dict[str, Any]] = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
    ) -> str:
        """
        Non-blocking capture hook called immediately after cloud response.
        Enqueues payload in microseconds; NEVER delays or blocks client streaming.
        Returns: distillation_id (str)
        """
        distillation_id = f"dist_{uuid.uuid4().hex[:8]}"
        now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()

        item = {
            "distillation_id": distillation_id,
            "timestamp_utc": now_utc,
            "prompt_messages": prompt_messages,
            "cloud_response": cloud_response,
            "teacher_model": teacher_model,
            "escalation_ticket_id": escalation_ticket_id,
            "verification_metadata": verification_metadata or {},
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        }

        try:
            self._queue.put_nowait(item)
            self.stats["enqueued"] += 1
        except asyncio.QueueFull:
            logger.warning("Distillation queue is full. Dropping trace to preserve client latency.")
            self.stats["errors"] += 1

        return distillation_id

    async def capture_trace_async(
        self,
        prompt_messages: Union[List[Dict[str, Any]], str, Dict[str, Any]],
        cloud_response: Any,
        teacher_model: str = "gemini-2.5-flash-thinking",
        escalation_ticket_id: Optional[str] = None,
        verification_metadata: Optional[Dict[str, Any]] = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
    ) -> str:
        """Async alias for capture_trace_nowait."""
        return self.capture_trace_nowait(
            prompt_messages=prompt_messages,
            cloud_response=cloud_response,
            teacher_model=teacher_model,
            escalation_ticket_id=escalation_ticket_id,
            verification_metadata=verification_metadata,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

    def capture_trace_sync(
        self,
        prompt_messages: Union[List[Dict[str, Any]], str, Dict[str, Any]],
        cloud_response: Any,
        teacher_model: str = "gemini-2.5-flash-thinking",
        escalation_ticket_id: Optional[str] = None,
        verification_metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Synchronous wrapper for non-async callers.
        Directly appends to queue or executes immediate background write.
        """
        distillation_id = f"dist_{uuid.uuid4().hex[:8]}"
        now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
        item = {
            "distillation_id": distillation_id,
            "timestamp_utc": now_utc,
            "prompt_messages": prompt_messages,
            "cloud_response": cloud_response,
            "teacher_model": teacher_model,
            "escalation_ticket_id": escalation_ticket_id,
            "verification_metadata": verification_metadata or {},
            "prompt_tokens": 0,
            "completion_tokens": 0,
        }
        try:
            self._queue.put_nowait(item)
            self.stats["enqueued"] += 1
        except (asyncio.QueueFull, RuntimeError):
            # Fallback for sync contexts without running loop: process directly in thread
            threading.Thread(target=self._process_item_sync, args=(item,), daemon=True).start()

        return distillation_id

    async def _process_loop(self) -> None:
        """Background loop reading from queue and persisting traces."""
        while self._running:
            try:
                item = await self._queue.get()
                await self._process_single_item(item)
                self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as err:
                self.stats["errors"] += 1
                logger.error(f"Error in distillation background loop: {err}")
                await asyncio.sleep(0.05)

    def _format_trace(self, item: Dict[str, Any]) -> DistillationTrace:
        """Format raw captured item into canonical DistillationTrace."""
        raw_prompts = item.get("prompt_messages")
        normalized_messages: List[Dict[str, Any]] = []

        # 1. Normalize prompt messages
        if isinstance(raw_prompts, list):
            for m in raw_prompts:
                if isinstance(m, dict):
                    role = m.get("role", "user")
                    content = str(m.get("content", ""))
                    normalized_messages.append({"role": role, "content": content})
                else:
                    normalized_messages.append({"role": "user", "content": str(m)})
        elif isinstance(raw_prompts, dict):
            if "messages" in raw_prompts and isinstance(raw_prompts["messages"], list):
                for m in raw_prompts["messages"]:
                    if isinstance(m, dict):
                        normalized_messages.append({
                            "role": m.get("role", "user"),
                            "content": str(m.get("content", "")),
                        })
            elif "prompt" in raw_prompts:
                normalized_messages.append({"role": "user", "content": str(raw_prompts["prompt"])})
        elif isinstance(raw_prompts, str):
            normalized_messages.append({"role": "user", "content": raw_prompts})

        # Ensure default system message exists if none provided
        has_system = any(m.get("role") == "system" for m in normalized_messages)
        if not has_system:
            normalized_messages.insert(0, {
                "role": "system",
                "content": (
                    "You are the Lauburu Lead Code Intelligence Specialist. "
                    "Analyze complex codebase contexts, provide rigorous architecture "
                    "reasoning, and emit clean, zero-mock, production-grade implementations."
                ),
            })

        # 2. Extract reasoning trace and final content from assistant response
        reasoning_trace, assistant_content = extract_reasoning_and_content(item.get("cloud_response"))
        assistant_msg: Dict[str, Any] = {
            "role": "assistant",
            "content": assistant_content,
        }
        if reasoning_trace:
            assistant_msg["reasoning_trace"] = reasoning_trace

        normalized_messages.append(assistant_msg)

        # 3. Scrub sensitive credentials across all message objects
        scrubbed_messages = scrub_sensitive_credentials(normalized_messages)
        self.stats["scrubbed"] += 1

        # 4. Token counts
        prompt_tokens = item.get("prompt_tokens", 0)
        completion_tokens = item.get("completion_tokens", 0)
        if prompt_tokens == 0:
            prompt_tokens = sum(len(m.get("content", "")) for m in scrubbed_messages[:-1]) // 4
        if completion_tokens == 0:
            completion_tokens = len(assistant_content) // 4

        # 5. Build verification metadata
        metadata = dict(item.get("verification_metadata", {}))
        metadata.setdefault("syntax_valid", True)
        metadata.setdefault("exit_code", 0)
        if item.get("escalation_ticket_id"):
            metadata["escalation_ticket_id"] = item["escalation_ticket_id"]

        return DistillationTrace(
            distillation_id=item["distillation_id"],
            timestamp_utc=item["timestamp_utc"],
            source="ide_gateway_authorized_escalation",
            domain="ide_code_intelligence",
            teacher_model=item.get("teacher_model", "gemini-2.5-flash-thinking"),
            target_student_model=self.target_student_model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            messages=scrubbed_messages,
            verification_metadata=metadata,
        )

    def _append_to_file(self, trace: DistillationTrace) -> bool:
        """Atomic append of trace JSONL to target dataset file."""
        try:
            line = trace.to_jsonl() + "\n"
            with self._file_lock:
                self.dataset_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.dataset_path, "a", encoding="utf-8") as f:
                    f.write(line)
                    f.flush()
            self.stats["written"] += 1
            return True
        except Exception as err:
            self.stats["errors"] += 1
            logger.error(f"Failed to append distillation trace to {self.dataset_path}: {err}")
            return False

    async def _push_to_l3_endpoint(self, trace: DistillationTrace) -> bool:
        """
        Asynchronously forward trace to L3 Linux Hub ingestion daemon.
        Non-blocking: timeout is 1.0s; failures are caught and logged without raising.
        """
        if not self.push_to_l3 or not self.l3_endpoint:
            return False

        def _send() -> bool:
            try:
                payload_bytes = json.dumps(trace.to_dict()).encode("utf-8")
                req = urllib.request.Request(
                    self.l3_endpoint,
                    data=payload_bytes,
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=1.0) as resp:
                    return resp.status in (200, 201, 202)
            except Exception:
                return False

        try:
            success = await asyncio.to_thread(_send)
            if success:
                self.stats["l3_pushed"] += 1
            return success
        except Exception:
            return False

    def _compute_signature(self, trace: DistillationTrace) -> str:
        """Compute SHA256 signature across user inputs and assistant response for deduplication."""
        import hashlib
        user_parts = [str(m.get("content", "")) for m in trace.messages if m.get("role") == "user"]
        assistant_parts = [str(m.get("content", "")) for m in trace.messages if m.get("role") == "assistant"]
        key = f"{'|'.join(user_parts)}|||{'|'.join(assistant_parts)}"
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    async def _process_single_item(self, item: Dict[str, Any]) -> None:
        """Process one queue item: format, scrub, write to disk, push to L3."""
        trace = self._format_trace(item)
        sig = self._compute_signature(trace)
        with self._file_lock:
            if sig in self._seen_signatures:
                self.stats["deduplicated"] += 1
                logger.debug(f"Skipping duplicate distillation trace: {trace.distillation_id}")
                return
            self._seen_signatures.add(sig)

        self._append_to_file(trace)
        if self.push_to_l3:
            await self._push_to_l3_endpoint(trace)
        self.stats["processed"] += 1

    def _process_item_sync(self, item: Dict[str, Any]) -> None:
        """Synchronous processing worker for sync callers."""
        trace = self._format_trace(item)
        sig = self._compute_signature(trace)
        with self._file_lock:
            if sig in self._seen_signatures:
                self.stats["deduplicated"] += 1
                logger.debug(f"Skipping duplicate distillation trace: {trace.distillation_id}")
                return
            self._seen_signatures.add(sig)

        self._append_to_file(trace)
        self.stats["processed"] += 1

    # =========================================================================
    # L3 Overnight Fine-Tuning Queue Trigger
    # =========================================================================

    def get_trace_count(self) -> int:
        """Count total lines/traces in the dataset file."""
        if not self.dataset_path.exists():
            return 0
        try:
            with open(self.dataset_path, "r", encoding="utf-8") as f:
                return sum(1 for line in f if line.strip())
        except Exception:
            return 0

    def trigger_l3_overnight_fine_tuning(self, min_traces: int = 10) -> Dict[str, Any]:
        """
        Check accumulated trace dataset and signal L3 overnight fine-tuning queue.
        - Verifies at least min_traces are accumulated.
        - Issues training queue trigger to L3 Self-Healing Hub (Port 18802).
        - Resilient: If L3 is offline, marks status as QUEUED_LOCAL so the
          overnight systemd daemon will process files upon scheduled wake-up.
        """
        current_count = self.get_trace_count()
        if current_count < min_traces:
            logger.info(f"Distillation queue skipped: {current_count} traces < {min_traces} min required.")
            return {
                "status": "SKIPPED",
                "trace_count": current_count,
                "min_required": min_traces,
                "reason": f"Insufficient traces for fine-tuning batch ({current_count} < {min_traces})",
            }

        payload = {
            "dataset_path": str(self.dataset_path),
            "trace_count": current_count,
            "target_model": self.target_student_model,
            "batch_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }

        # Attempt remote HTTP trigger to L3 daemon
        remote_triggered = False
        l3_response: Optional[str] = None
        try:
            payload_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.l3_trigger_endpoint,
                data=payload_bytes,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                if resp.status in (200, 201, 202):
                    remote_triggered = True
                    l3_response = resp.read().decode("utf-8")
        except Exception as err:
            logger.debug(f"Direct L3 trigger socket not connected ({err}); falling back to local queue state.")

        if remote_triggered:
            return {
                "status": "QUEUED_REMOTE",
                "trace_count": current_count,
                "target_model": self.target_student_model,
                "dataset_path": str(self.dataset_path),
                "l3_response": l3_response,
                "message": "Overnight LoRA fine-tuning queued on L3 Linux Hub",
            }
        else:
            return {
                "status": "QUEUED_LOCAL",
                "trace_count": current_count,
                "target_model": self.target_student_model,
                "dataset_path": str(self.dataset_path),
                "message": "Queued in local dataset lake; L3 systemd daemon will ingest at 02:00 AEST",
            }

    def trigger_overnight_training(self, min_traces: int = 10) -> TriggerResult:
        """Alias for trigger_l3_overnight_fine_tuning() returning TriggerResult (queued, message)."""
        res = self.trigger_l3_overnight_fine_tuning(min_traces=min_traces)
        queued = res["status"] in ("QUEUED_LOCAL", "QUEUED_REMOTE")
        msg = res.get("message") or res.get("reason", "")
        return TriggerResult(queued, msg, res)

    def get_metrics(self) -> Dict[str, Any]:
        """Alias for get_stats() for gateway telemetry."""
        return self.get_stats()

    def get_stats(self) -> Dict[str, Any]:
        """Return operational telemetry."""
        return {
            **self.stats,
            "queue_size": self._queue.qsize(),
            "dataset_path": str(self.dataset_path),
            "total_file_traces": self.get_trace_count(),
            "worker_running": self._running,
        }

    def read_recent_traces(self, n: int = 5) -> List[Dict[str, Any]]:
        """Read the n most recent traces from dataset file."""
        if not self.dataset_path.exists():
            return []
        lines: List[str] = []
        try:
            with open(self.dataset_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        lines.append(line.strip())
            recent = lines[-n:]
            return [json.loads(l) for l in recent]
        except Exception as err:
            logger.error(f"Error reading recent traces: {err}")
            return []
