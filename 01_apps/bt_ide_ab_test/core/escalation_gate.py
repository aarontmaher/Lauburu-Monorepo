"""
Manual Cloud Escalation Gate (Requirement R4).

Intercepts incoming IDE requests that exceed the local model context ceiling
(LOCAL_CONTEXT_MAX = 8,192 tokens) or trigger system saturation.
Enforces strict Zero-Cloud-Leakage:
- Dual-mode blocking:
    Mode A: Terminal interactive prompt for TTY sessions.
    Mode B: Non-blocking HTTP ticket ledger with 30s timeout and REST approval hook
            (/api/escalation/authorize) for IDE extensions (Continue.dev / VSCode).
- Default to HTTP 403 / REJECT on timeout or cancellation.
- NEVER auto-route to cloud without explicit manual authorization.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger("escalation_gate")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("[ESCALATION GATE] %(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Default configuration constants
LOCAL_CONTEXT_MAX: int = 8192
DEFAULT_TIMEOUT_SECONDS: float = 30.0
DEFAULT_LEDGER_PATH: str = "/tmp/lauburu_active_escalations.json"


class EscalationStatus(str, Enum):
    """Lifecycle states of an escalation ticket."""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    TIMED_OUT = "TIMED_OUT"
    CANCELLED = "CANCELLED"
    TRUNCATE = "TRUNCATE"


@dataclass
class EscalationTicket:
    """
    Escalation ticket generated when context exceeds local ceiling.
    Follows canonical interface contract in PROJECT.md § 4.3.
    """
    ticket_id: str
    token_count: int
    context_limit: int
    target_cloud_model: str
    status: str = EscalationStatus.PENDING.value
    created_at: float = field(default_factory=time.time)
    expires_at: float = 0.0
    payload_summary: Optional[Dict[str, Any]] = None
    reason: str = ""

    def __post_init__(self):
        if self.expires_at == 0.0:
            self.expires_at = self.created_at + DEFAULT_TIMEOUT_SECONDS

    @property
    def tokens(self) -> int:
        """Alias for token_count."""
        return self.token_count

    @property
    def limit(self) -> int:
        """Alias for context_limit."""
        return self.context_limit

    def is_pending(self) -> bool:
        return self.status == EscalationStatus.PENDING.value

    def is_approved(self) -> bool:
        return self.status == EscalationStatus.APPROVED.value

    def is_expired(self, now: Optional[float] = None) -> bool:
        current_time = now if now is not None else time.time()
        return current_time > self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        """Convert ticket to dictionary format."""
        return {
            "ticket_id": self.ticket_id,
            "token_count": self.token_count,
            "tokens": self.token_count,
            "context_limit": self.context_limit,
            "limit": self.context_limit,
            "target_cloud_model": self.target_cloud_model,
            "target_model": self.target_cloud_model,
            "status": self.status,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "payload_summary": self.payload_summary,
            "reason": self.reason,
        }


class TicketResolutionResult:
    """Wrapper that supports both boolean check and 2-tuple unpacking (success, ticket)."""
    def __init__(self, success: bool, ticket: Optional[EscalationTicket]):
        self.success = success
        self.ticket = ticket

    def __bool__(self) -> bool:
        return self.success

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, bool):
            return self.success is other
        return super().__eq__(other)

    def __iter__(self):
        return iter((self.success, self.ticket))

    def __getitem__(self, idx: int):
        return (self.success, self.ticket)[idx]

    def __repr__(self) -> str:
        return f"TicketResolutionResult(success={self.success}, ticket={self.ticket})"


@dataclass
class EscalationResult:
    """Result of an escalation interception check."""
    authorized: bool
    status: str
    ticket: Optional[EscalationTicket] = None
    reason: str = ""
    error_code: Optional[int] = None
    error_response: Optional[Dict[str, Any]] = None

    def __bool__(self) -> bool:
        return self.authorized

    def __iter__(self):
        """Allow unpacking as (auth_ok, reason)."""
        return iter((self.authorized, self.reason))

    def __getitem__(self, idx: int):
        return (self.authorized, self.reason)[idx]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "authorized": self.authorized,
            "status": self.status,
            "ticket": self.ticket.to_dict() if self.ticket else None,
            "reason": self.reason,
            "error_code": self.error_code,
            "error_response": self.error_response,
        }


class ManualCloudEscalationGate:
    """
    Manual Cloud Escalation Gate enforcing Zero-Cloud-Leakage.
    
    1. Detects context overflows (> LOCAL_CONTEXT_MAX tokens).
    2. Blocks execution until explicit authorization is granted:
       - TTY Interactive Prompt (CLI mode)
       - Non-blocking HTTP Ticket Ledger with 30s timeout and REST approval hook (IDE extension mode)
    3. Strict Zero-Cloud-Leakage: Defaults to HTTP 403 / REJECT on timeout or cancellation.
    """

    def __init__(
        self,
        context_limit: int = LOCAL_CONTEXT_MAX,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        ledger_path: Optional[str] = None,
        tokenize_endpoint: Optional[str] = None,
    ):
        self.context_limit = context_limit
        self.timeout_seconds = timeout_seconds
        self.ledger_path = Path(ledger_path or DEFAULT_LEDGER_PATH)
        self.tokenize_endpoint = tokenize_endpoint
        
        # State stores (thread-safe / async safe)
        self._tickets: Dict[str, EscalationTicket] = {}
        self._events: Dict[str, asyncio.Event] = {}
        self._lock = asyncio.Lock()

        # Initialize or clean ledger
        self._init_ledger()

    def _init_ledger(self) -> None:
        """Initialize the active escalation ledger file on disk."""
        try:
            self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
            if not self.ledger_path.exists():
                self._write_ledger_file([])
        except Exception as err:
            logger.warning(f"Could not initialize escalation ledger at {self.ledger_path}: {err}")

    def _write_ledger_file(self, data: List[Dict[str, Any]]) -> None:
        """Atomic write to ledger file."""
        try:
            tmp_path = self.ledger_path.with_suffix(".tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            tmp_path.replace(self.ledger_path)
        except Exception as err:
            logger.debug(f"Ledger file write error: {err}")

    def _sync_ledger(self) -> None:
        """Sync in-memory pending tickets to disk ledger."""
        active = [
            t.to_dict() for t in self._tickets.values()
            if t.status == EscalationStatus.PENDING.value
        ]
        self._write_ledger_file(active)

    def estimate_tokens(self, payload: Any) -> int:
        """
        Estimate token count from payload (string, message list, or dict).
        Uses fast standard character-ratio heuristic (chars / 3.8 + message overhead),
        with optional fallback to local llama-server tokenization if endpoint is active.
        """
        if payload is None:
            return 0

        # Optional live tokenization endpoint probe (with fast timeout)
        if self.tokenize_endpoint:
            try:
                import urllib.request
                data = json.dumps({"content": str(payload)}).encode("utf-8")
                req = urllib.request.Request(
                    self.tokenize_endpoint,
                    data=data,
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=0.25) as resp:
                    if resp.status == 200:
                        parsed = json.loads(resp.read().decode("utf-8"))
                        if "tokens" in parsed and isinstance(parsed["tokens"], list):
                            return len(parsed["tokens"])
            except Exception:
                pass  # Fall back to heuristic seamlessly

        # Fast heuristic estimation
        text_content: List[str] = []
        message_overhead = 0

        if isinstance(payload, str):
            text_content.append(payload)
        elif isinstance(payload, list):
            for item in payload:
                if isinstance(item, dict):
                    message_overhead += 4
                    for v in item.values():
                        if isinstance(v, str):
                            text_content.append(v)
                elif isinstance(item, str):
                    text_content.append(item)
        elif isinstance(payload, dict):
            if "messages" in payload and isinstance(payload["messages"], list):
                for msg in payload["messages"]:
                    message_overhead += 4
                    if isinstance(msg, dict):
                        for k, v in msg.items():
                            if isinstance(v, str):
                                text_content.append(v)
                            elif isinstance(v, (dict, list)):
                                text_content.append(json.dumps(v))
            elif "prompt" in payload:
                prompt_val = payload["prompt"]
                if isinstance(prompt_val, str):
                    text_content.append(prompt_val)
                elif isinstance(prompt_val, list):
                    text_content.extend(str(p) for p in prompt_val)
            else:
                for v in payload.values():
                    if isinstance(v, str):
                        text_content.append(v)
                    elif isinstance(v, (dict, list)):
                        text_content.append(json.dumps(v))
        else:
            text_content.append(str(payload))

        full_text = " ".join(text_content)
        if not full_text.strip():
            return message_overhead

        # Character ratio heuristic for code/English BPE tokenizers
        estimated = int(len(full_text) / 3.8) + message_overhead
        return max(1, estimated)

    def is_overflow(self, payload: Any) -> Tuple[bool, int]:
        """
        Check if payload token count exceeds local context ceiling.
        Returns: (is_overflow: bool, token_count: int)
        """
        tokens = self.estimate_tokens(payload)
        return (tokens > self.context_limit), tokens

    def create_ticket(
        self,
        payload: Any,
        target_cloud_model: str = "gemini-2.5-flash",
        timeout: Optional[float] = None,
        custom_ticket_id: Optional[str] = None,
    ) -> EscalationTicket:
        """Create and register a new pending escalation ticket."""
        token_count = self.estimate_tokens(payload)
        ticket_id = custom_ticket_id or f"esc_{uuid.uuid4().hex[:8]}"
        effective_timeout = timeout if timeout is not None else self.timeout_seconds
        now = time.time()

        # Build payload summary without storing large raw buffers
        summary: Dict[str, Any] = {
            "token_count": token_count,
            "target_model": target_cloud_model,
        }
        if isinstance(payload, dict):
            if "messages" in payload and isinstance(payload["messages"], list):
                summary["message_count"] = len(payload["messages"])
                if payload["messages"]:
                    first_msg = payload["messages"][0]
                    summary["first_role"] = first_msg.get("role", "unknown")
                    first_content = str(first_msg.get("content", ""))
                    summary["preview"] = first_content[:120] + ("..." if len(first_content) > 120 else "")
            elif "prompt" in payload:
                prompt_str = str(payload["prompt"])
                summary["preview"] = prompt_str[:120] + ("..." if len(prompt_str) > 120 else "")

        ticket = EscalationTicket(
            ticket_id=ticket_id,
            token_count=token_count,
            context_limit=self.context_limit,
            target_cloud_model=target_cloud_model,
            status=EscalationStatus.PENDING.value,
            created_at=now,
            expires_at=now + effective_timeout,
            payload_summary=summary,
        )

        self._tickets[ticket_id] = ticket
        self._events[ticket_id] = asyncio.Event()
        self._sync_ledger()

        logger.info(
            f"🚨 Ticket created: {ticket_id} | Tokens: {token_count:,} > {self.context_limit:,} | "
            f"Target: {target_cloud_model} | Timeout: {effective_timeout}s"
        )
        return ticket

    def get_ticket(self, ticket_id: str) -> Optional[EscalationTicket]:
        """Fetch ticket by ID."""
        return self._tickets.get(ticket_id)

    def list_pending_tickets(self) -> List[EscalationTicket]:
        """List all currently pending tickets that have not expired."""
        now = time.time()
        return [
            t for t in self._tickets.values()
            if t.status == EscalationStatus.PENDING.value and not t.is_expired(now)
        ]

    def list_all_tickets(self) -> List[EscalationTicket]:
        """List all tickets in memory."""
        return list(self._tickets.values())

    def list_tickets(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List active and historical escalation tickets as dictionaries.
        Supports status filtering (e.g. status='PENDING').
        """
        self.clean_expired_tickets()
        tickets = list(self._tickets.values())
        if status:
            status_upper = status.strip().upper()
            tickets = [t for t in tickets if t.status == status_upper]
        return [t.to_dict() for t in tickets]

    def clean_expired_tickets(self) -> int:
        """Sweep and transition overdue pending tickets to TIMED_OUT."""
        now = time.time()
        count = 0
        for ticket in self._tickets.values():
            if ticket.status == EscalationStatus.PENDING.value and ticket.is_expired(now):
                ticket.status = EscalationStatus.TIMED_OUT.value
                ticket.reason = "Expired without manual authorization"
                event = self._events.get(ticket.ticket_id)
                if event and not event.is_set():
                    event.set()
                count += 1
        if count > 0:
            self._sync_ledger()
        return count

    def resolve_ticket(
        self,
        ticket_id: str,
        action: str,
        reason: str = "",
    ) -> TicketResolutionResult:
        """
        Resolve a pending ticket with an explicit action.
        Valid actions: APPROVE, REJECT, CANCEL, TRUNCATE.
        Sets the associated event to unblock waiting async requests.
        Returns: TicketResolutionResult (unpacks as (resolved, ticket) and evaluates as bool).
        """
        ticket = self._tickets.get(ticket_id)
        if not ticket:
            logger.warning(f"Resolution failed: ticket {ticket_id} not found")
            return TicketResolutionResult(False, None)

        if ticket.status != EscalationStatus.PENDING.value:
            logger.warning(f"Resolution ignored: ticket {ticket_id} already resolved with status {ticket.status}")
            return TicketResolutionResult(False, ticket)

        action_upper = action.strip().upper()
        if action_upper in ("APPROVE", "APPROVED", "A", "YES", "Y"):
            ticket.status = EscalationStatus.APPROVED.value
            ticket.reason = reason or "User manually authorized cloud escalation"
        elif action_upper in ("TRUNCATE", "T"):
            ticket.status = EscalationStatus.TRUNCATE.value
            ticket.reason = reason or "User requested local context truncation/paging"
        elif action_upper in ("CANCEL", "CANCELLED", "C"):
            ticket.status = EscalationStatus.CANCELLED.value
            ticket.reason = reason or "User cancelled request"
        else:
            # Default to REJECT for any denial or unrecognized input
            ticket.status = EscalationStatus.REJECTED.value
            ticket.reason = reason or "User rejected cloud escalation"

        event = self._events.get(ticket_id)
        if event:
            event.set()

        self._sync_ledger()
        logger.info(f"Ticket {ticket_id} resolved: status={ticket.status}, reason={ticket.reason}")
        return TicketResolutionResult(True, ticket)

    def format_rejection_response(
        self,
        ticket: Optional[EscalationTicket],
        reason: str = "",
    ) -> Dict[str, Any]:
        """
        Format standardized OpenAI-compatible HTTP 403 Forbidden error response.
        Ensures IDE extensions and clients receive strict, parseable rejection payloads.
        """
        ticket_id = ticket.ticket_id if ticket else "none"
        tokens = ticket.token_count if ticket else 0
        limit = ticket.context_limit if ticket else self.context_limit
        status = ticket.status if ticket else EscalationStatus.REJECTED.value

        error_message = (
            f"Cloud escalation denied by user or policy. Payload of {tokens:,} tokens "
            f"exceeds local context limit of {limit:,} tokens. Status: {status}."
        )
        if reason:
            error_message += f" Reason: {reason}"

        return {
            "error": {
                "message": error_message,
                "type": "escalation_rejected",
                "param": "context_length",
                "code": 403,
                "ticket_id": ticket_id,
                "status": status,
                "token_count": tokens,
                "context_limit": limit,
            }
        }

    async def prompt_tty_user(
        self,
        ticket: EscalationTicket,
        timeout: Optional[float] = None,
    ) -> Tuple[bool, str]:
        """
        Mode A: Terminal interactive prompt for TTY sessions.
        Reads stdin asynchronously with timeout protection.
        Defaults to REJECT if timeout expires or invalid input is given.
        """
        effective_timeout = timeout if timeout is not None else self.timeout_seconds
        overflow = ticket.token_count - ticket.context_limit

        banner = f"""
================================================================================
🚨 MANUAL CLOUD ESCALATION GATE: CONTEXT OVERFLOW DETECTED
--------------------------------------------------------------------------------
Ticket ID:       {ticket.ticket_id}
Payload Size:    {ticket.token_count:,} tokens (Local Limit: {ticket.context_limit:,} tokens)
Overflow:        +{overflow:,} tokens
Proposed Target: {ticket.target_cloud_model}
Privacy Status:  External API invocation required for full context resolution.

Options:
  [A] Authorize Escalation (Transmit payload to Cloud API)
  [R] Reject Escalation (Default: keep data 100% local airgapped)
  [T] Truncate Context (Summarize / Page locally to stay <= {ticket.context_limit:,} tokens)

Select option [A/R/T] (Default: R, Timeout: {effective_timeout:.1f}s): """

        sys.stdout.write(banner)
        sys.stdout.flush()

        def _blocking_read() -> str:
            try:
                return sys.stdin.readline().strip()
            except (EOFError, KeyboardInterrupt):
                return "R"

        try:
            choice = await asyncio.wait_for(
                asyncio.to_thread(_blocking_read),
                timeout=effective_timeout,
            )
            choice_clean = choice.strip().upper()
            if choice_clean in ("A", "APPROVE", "YES", "Y"):
                self.resolve_ticket(ticket.ticket_id, "APPROVE", "Authorized via interactive TTY")
                return True, "USER_APPROVED_TTY"
            elif choice_clean in ("T", "TRUNCATE"):
                self.resolve_ticket(ticket.ticket_id, "TRUNCATE", "Truncate requested via interactive TTY")
                return False, "USER_TRUNCATE_TTY"
            else:
                self.resolve_ticket(ticket.ticket_id, "REJECT", "Rejected via interactive TTY")
                return False, "USER_REJECTED_TTY"
        except asyncio.TimeoutError:
            print("\n[ESCALATION GATE] ⏰ Interactive TTY prompt timed out. Defaulting to REJECT.")
            self.resolve_ticket(ticket.ticket_id, "REJECT", "TTY prompt timed out (default REJECT)")
            return False, "TTY_TIMEOUT_REJECTED"
        except Exception as err:
            logger.warning(f"Error during TTY prompt: {err}")
            self.resolve_ticket(ticket.ticket_id, "REJECT", f"TTY prompt exception: {err}")
            return False, "TTY_ERROR_REJECTED"

    async def intercept_and_await_authorization(
        self,
        payload: Any,
        target_cloud_model: str = "gemini-2.5-flash",
        is_tty: Optional[bool] = None,
        timeout: Optional[float] = None,
    ) -> EscalationResult:
        """
        Master Interception Routine.
        
        1. Checks whether payload exceeds context ceiling.
        2. If within limits: returns authorized=True immediately.
        3. If overflow:
           - Mode A (TTY): prompts user directly on terminal.
           - Mode B (HTTP): registers ticket and awaits REST resolution hook.
        4. Enforces strict Zero-Cloud-Leakage:
           - Returns authorized=False with HTTP 403 on denial, timeout, or error.
        """
        overflow, token_count = self.is_overflow(payload)
        if not overflow:
            return EscalationResult(
                authorized=True,
                status="LOCAL_WITHIN_LIMITS",
                ticket=None,
                reason=f"Payload of {token_count:,} tokens is within local limit ({self.context_limit:,})",
                error_code=None,
                error_response=None,
            )

        effective_timeout = timeout if timeout is not None else self.timeout_seconds
        ticket = self.create_ticket(
            payload=payload,
            target_cloud_model=target_cloud_model,
            timeout=effective_timeout,
        )

        # Determine interactive vs headless/ticket mode
        tty_mode = is_tty if is_tty is not None else sys.stdin.isatty()

        if tty_mode:
            # Mode A: Interactive TTY prompt
            authorized, prompt_status = await self.prompt_tty_user(ticket, timeout=effective_timeout)
            if authorized:
                return EscalationResult(
                    authorized=True,
                    status=EscalationStatus.APPROVED.value,
                    ticket=ticket,
                    reason=ticket.reason,
                    error_code=200,
                )
            else:
                return EscalationResult(
                    authorized=False,
                    status=ticket.status,
                    ticket=ticket,
                    reason=ticket.reason or prompt_status,
                    error_code=403,
                    error_response=self.format_rejection_response(ticket, reason=prompt_status),
                )

        # Mode B: Non-blocking HTTP ticket ledger (IDE extensions / Continue.dev)
        event = self._events.get(ticket.ticket_id)
        if not event:
            # Safety fallback: reject if event creation failed
            ticket.status = EscalationStatus.REJECTED.value
            return EscalationResult(
                authorized=False,
                status=EscalationStatus.REJECTED.value,
                ticket=ticket,
                reason="Ticket event initialization failed",
                error_code=403,
                error_response=self.format_rejection_response(ticket, "Ticket event initialization failed"),
            )

        try:
            await asyncio.wait_for(event.wait(), timeout=effective_timeout)
            # Ticket resolved via REST endpoint (/api/escalation/authorize)
            if ticket.status == EscalationStatus.APPROVED.value:
                return EscalationResult(
                    authorized=True,
                    status=EscalationStatus.APPROVED.value,
                    ticket=ticket,
                    reason=ticket.reason,
                    error_code=200,
                )
            else:
                return EscalationResult(
                    authorized=False,
                    status=ticket.status,
                    ticket=ticket,
                    reason=ticket.reason or f"Ticket resolved with status {ticket.status}",
                    error_code=403,
                    error_response=self.format_rejection_response(ticket, reason=ticket.reason),
                )
        except asyncio.TimeoutError:
            ticket.status = EscalationStatus.TIMED_OUT.value
            ticket.reason = f"Escalation authorization timed out after {effective_timeout:.1f}s"
            self._sync_ledger()
            logger.warning(f"🚨 Escalation ticket {ticket.ticket_id} TIMED OUT. Zero-leakage 403 enforced.")
            return EscalationResult(
                authorized=False,
                status=EscalationStatus.TIMED_OUT.value,
                ticket=ticket,
                reason=ticket.reason,
                error_code=403,
                error_response=self.format_rejection_response(ticket, reason=ticket.reason),
            )
        finally:
            self._events.pop(ticket.ticket_id, None)

    # =========================================================================
    # REST API Helper Handlers (For Gateway integration)
    # =========================================================================

    def handle_rest_authorize(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle REST authorization request: POST /api/escalation/authorize
        Body format: {"ticket_id": "esc_...", "action": "APPROVE"|"REJECT"|"TRUNCATE", "reason": "..."}
        """
        ticket_id = request_data.get("ticket_id")
        action = request_data.get("action", "REJECT")
        reason = request_data.get("reason", "")

        if not ticket_id:
            return {"success": False, "error": "ticket_id is required", "status_code": 400}

        success = self.resolve_ticket(ticket_id=ticket_id, action=action, reason=reason)
        ticket = self.get_ticket(ticket_id)

        if not success:
            return {
                "success": False,
                "error": "Ticket not found or already resolved",
                "ticket_id": ticket_id,
                "status_code": 404 if not ticket else 409,
            }

        return {
            "success": True,
            "ticket_id": ticket_id,
            "action": action,
            "status": ticket.status if ticket else "UNKNOWN",
            "reason": ticket.reason if ticket else "",
            "status_code": 200,
        }

    def handle_rest_list_tickets(self, pending_only: bool = True) -> Dict[str, Any]:
        """
        Handle GET /api/escalation/tickets
        Returns listing of pending or all active tickets.
        """
        self.clean_expired_tickets()
        tickets = self.list_pending_tickets() if pending_only else self.list_all_tickets()
        return {
            "success": True,
            "count": len(tickets),
            "tickets": [t.to_dict() for t in tickets],
        }

    def handle_rest_ticket_status(self, ticket_id: str) -> Dict[str, Any]:
        """
        Handle GET /api/escalation/tickets/{ticket_id}
        """
        ticket = self.get_ticket(ticket_id)
        if not ticket:
            return {"success": False, "error": f"Ticket {ticket_id} not found", "status_code": 404}

        return {
            "success": True,
            "ticket": ticket.to_dict(),
            "status_code": 200,
        }
