"""
Canonical Base Async Inference Bridge
Version: 1.0.0-CANONICAL

Abstract Base Class for all Canonical Port non-blocking async inference bridges:
- llama.cpp (GGML-RPC :50052 & HTTP :8081-:8085)
- exo (Zenoh P2P Ring :52415)
- accelerate (HuggingFace Multi-GPU/MPS DDP LoRA)
- petals (BitTorrent DHT Swarm :31330/:31337)

Provides unified streaming token generation, instant barge-in cancellation (<1ms),
code snippet extraction, and full-duplex Voice Coding TTS piping.
"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator, Callable, Dict, Any, List, Optional, Tuple
import asyncio
import re
import time
import logging

logger = logging.getLogger("BaseInferenceBridge")


class BaseInferenceBridge(ABC):
    """
    Abstract Base Class for Canonical Port Async Inference Bridges.
    All inference backends implement this contract for polymorphic routing.
    """

    def __init__(
        self,
        s2s_client: Optional[Any] = None,
        voice_io_manager: Optional[Any] = None,
        on_token: Optional[Callable[[str], None]] = None,
        on_complete: Optional[Callable[[str], None]] = None,
        on_code_snippet: Optional[Callable[[str, str], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ):
        self.s2s_client = s2s_client
        self.voice_io_manager = voice_io_manager

        # UI / Event callbacks
        self.on_token = on_token
        self.on_complete = on_complete
        self.on_code_snippet = on_code_snippet
        self.on_error = on_error

        # Runtime & concurrency state
        self._is_generating: bool = False
        self._generation_cancelled: bool = False
        self._current_task: Optional[asyncio.Task] = None
        self._mock_tokens: Optional[List[str]] = None
        self._current_full_response: str = ""

        # Telemetry
        self.total_tokens_generated: int = 0
        self.last_generation_time_ms: float = 0.0
        self.latency_ms: float = 0.0

    @property
    def engine_name(self) -> str:
        """Alias for get_engine_name()."""
        return self.get_engine_name()

    @property
    def display_name(self) -> str:
        """Alias for get_display_name()."""
        return self.get_display_name()

    @abstractmethod
    def get_engine_name(self) -> str:
        """Return unique machine identifier (e.g., 'llama_rpc', 'exo', 'accelerate', 'petals')."""
        raise NotImplementedError

    @abstractmethod
    def get_display_name(self) -> str:
        """Return human-readable display label."""
        raise NotImplementedError

    @abstractmethod
    async def connect(self, timeout: Optional[float] = None) -> bool:
        """Non-blocking connection and socket health verification."""
        raise NotImplementedError

    @abstractmethod
    def is_connected(self) -> bool:
        """Return boolean connectivity state."""
        raise NotImplementedError

    @abstractmethod
    async def stream_generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> AsyncGenerator[str, None]:
        """
        Asynchronously yield generated token chunks with <15ms dispatch latency.
        Must check `self._generation_cancelled` and cleanly handle cancellation.
        """
        raise NotImplementedError

    def cancel(self) -> None:
        """Alias for cancel_generation()."""
        self.cancel_generation()

    def cancel_generation(self) -> None:
        """
        Instantly abort active token stream in <1ms without blocking the event loop.
        Flushes speaker audio buffers on barge-in.
        """
        self._generation_cancelled = True
        try:
            cur_task = asyncio.current_task()
        except Exception:
            cur_task = None

        if self._current_task and not self._current_task.done() and self._current_task is not cur_task:
            self._current_task.cancel()
            self._current_task = None

        if self.voice_io_manager:
            try:
                self.voice_io_manager.flush_playback()
            except Exception:
                pass
        logger.info(f"{self.get_engine_name()}: Generation cancelled.")

    def set_mock_tokens(self, tokens: Optional[List[str]]) -> None:
        """Set explicit mock token stream for deterministic testing."""
        self._mock_tokens = tokens

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Return standardized telemetry dictionary snapshot."""
        raise NotImplementedError

    @abstractmethod
    def get_status_badge(self) -> str:
        """Return concise HUD badge string (e.g. '[LLAMA.CPP: ACTIVE]')."""
        raise NotImplementedError

    async def process_user_input(
        self,
        prompt: str,
        is_voice: bool = False,
        max_tokens: int = 256
    ) -> str:
        """
        Process prompt, dispatch token callbacks, extract code blocks,
        and pipe synthesized speech text to Voice Coding S2S client.
        """
        self._current_full_response = ""
        self._generation_cancelled = False
        collected_tokens: List[str] = []
        t0 = time.perf_counter()

        try:
            async for token in self.stream_generate(prompt, max_tokens=max_tokens):
                if self._generation_cancelled:
                    break
                collected_tokens.append(token)
                self._current_full_response += token
                if self.on_token:
                    try:
                        self.on_token(token)
                    except Exception as e:
                        logger.debug(f"on_token callback error: {e}")

            full_text = "".join(collected_tokens)

            # Extract code snippets if present
            code_snippets = self._extract_code_snippets(full_text)
            for snippet, lang in code_snippets:
                if self.on_code_snippet:
                    try:
                        self.on_code_snippet(snippet, lang)
                    except Exception as e:
                        logger.debug(f"on_code_snippet callback error: {e}")

            # If voice mode is active and S2S client is present, send TTS synthesis command
            if is_voice and self.s2s_client and not self._generation_cancelled:
                speech_text = self._sanitize_for_tts(full_text)
                if speech_text:
                    try:
                        if hasattr(self.s2s_client, "send_control"):
                            self.s2s_client.send_control({
                                "type": "tts_synthesize",
                                "text": speech_text
                            })
                        elif hasattr(self.s2s_client, "send_tts_synthesize"):
                            res = self.s2s_client.send_tts_synthesize(speech_text)
                            if asyncio.iscoroutine(res):
                                await res
                    except Exception as e:
                        logger.debug(f"Error sending TTS synthesis control frame: {e}")

            if self.on_complete and not self._generation_cancelled:
                try:
                    self.on_complete(full_text)
                except Exception as e:
                    logger.debug(f"on_complete callback error: {e}")

            return full_text

        except asyncio.CancelledError:
            self._generation_cancelled = True
            logger.info(f"{self.get_engine_name()}: process_user_input cancelled.")
            return "".join(collected_tokens)
        except Exception as e:
            logger.error(f"{self.get_engine_name()} bridge error: {e}")
            if self.on_error:
                try:
                    self.on_error(str(e))
                except Exception:
                    pass
            return "".join(collected_tokens)
        finally:
            self.last_generation_time_ms = (time.perf_counter() - t0) * 1000.0

    def _extract_code_snippets(self, text: str) -> List[Tuple[str, str]]:
        """Extract Markdown code blocks or Python function definitions from generated text."""
        snippets: List[Tuple[str, str]] = []
        pattern = r"```([a-zA-Z0-9_]*)\n(.*?)```"
        matches = re.findall(pattern, text, re.DOTALL)
        for lang, code in matches:
            clean_code = code.strip()
            if clean_code:
                snippets.append((clean_code, lang.strip() or "python"))

        if not snippets:
            clean = text.strip()
            if clean.startswith("def ") or clean.startswith("class "):
                snippets.append((clean, "python"))

        return snippets

    def _sanitize_for_tts(self, text: str) -> str:
        """Strip markdown code blocks and symbols to produce clean speech for TTS."""
        clean = re.sub(r"```.*?```", " [Code snippet injected into editor buffer] ", text, flags=re.DOTALL)
        clean = re.sub(r"[#*_`~]", "", clean)
        clean = " ".join(clean.split())
        return clean.strip()
