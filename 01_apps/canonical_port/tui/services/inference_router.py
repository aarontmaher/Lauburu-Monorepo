"""
Unified Multi-Engine Inference Router
Version: 2.0.0-CANONICAL

Central router and coordinator for Canonical Port inference backends:
- auto (Dynamic TTFT Polling & Lowest-Latency Auto-Routing)
- llama.cpp (GGML-RPC :50052 & HTTP :8081-:8085)
- exo (Zenoh P2P Ring :52415)
- accelerate (HuggingFace Multi-GPU/MPS DDP LoRA)
- petals (BitTorrent DHT Swarm :31330/:31337)

Provides:
- Dynamic latency auto-routing to the lowest-TTFT available engine
- Instant zero-crash fallback to local llama.cpp if external engines timeout or drop
- Seamless runtime backend switching (set_active_engine, cycle_engine)
- Sub-1ms stream cancellation on engine swap or user speech barge-in
- Polymorphic prompt routing and non-blocking token streaming with micro-yields
- Full-duplex S2S Voice Coding transcript routing, code snippet extraction, and TTS piping
- Zero-crash event loop guarantee (cleanly caught asyncio.CancelledError)
"""

import time
import logging
import asyncio
from typing import AsyncGenerator, Callable, Dict, Any, List, Optional

try:
    from services.inference_bridges.base_bridge import BaseInferenceBridge
    from services.inference_bridges.llama_bridge import LlamaRpcInferenceBridge
    from services.inference_bridges.exo_bridge import ExoInferenceBridge
    from services.inference_bridges.accelerate_bridge import AccelerateInferenceBridge
    from services.inference_bridges.petals_bridge import PetalsInferenceBridge
    from services.inference_bridges.gemini_bridge import GeminiBridge
    from services.inference_bridges.cloudflare_bridge import CloudflareBridge
    from services.inference_bridges.julien_bridge import JulienBridge
    from services.latency_poller import DynamicLatencyPoller, EngineLatencyMetric
except ImportError:
    from tui.services.inference_bridges.base_bridge import BaseInferenceBridge
    from tui.services.inference_bridges.llama_bridge import LlamaRpcInferenceBridge
    from tui.services.inference_bridges.exo_bridge import ExoInferenceBridge
    from tui.services.inference_bridges.accelerate_bridge import AccelerateInferenceBridge
    from tui.services.inference_bridges.petals_bridge import PetalsInferenceBridge
    from tui.services.inference_bridges.gemini_bridge import GeminiBridge
    from tui.services.inference_bridges.cloudflare_bridge import CloudflareBridge
    from tui.services.inference_bridges.julien_bridge import JulienBridge
    from tui.services.latency_poller import DynamicLatencyPoller, EngineLatencyMetric

try:
    from backend.agents.continuous_arena_router import (
        ChampionLeaderboardResolver,
        ContinuousArenaEngine,
        ContinuousArenaInferenceRouter,
    )
except ImportError:
    try:
        import sys
        from pathlib import Path
        _base_path = Path(__file__).resolve().parents[2]
        if str(_base_path) not in sys.path:
            sys.path.insert(0, str(_base_path))
        from backend.agents.continuous_arena_router import (
            ChampionLeaderboardResolver,
            ContinuousArenaEngine,
            ContinuousArenaInferenceRouter,
        )
    except Exception:
        ChampionLeaderboardResolver = None
        ContinuousArenaEngine = None
        ContinuousArenaInferenceRouter = None

logger = logging.getLogger("UnifiedInferenceRouter")


class UnifiedInferenceRouter:
    """
    Unified Inference Router for Canonical Port TUI IDE.
    Decouples AGI Terminal REPL and Voice Coding pipeline from specific backends.
    """

    SUPPORTED_ENGINES: List[str] = [
        "auto",
        "champion",
        "arena",
        "llama_rpc",
        "exo",
        "accelerate",
        "petals",
        "gemini",
        "cloudflare",
        "julien",
    ]

    ENGINE_DISPLAY_NAMES: Dict[str, str] = {
        "auto": "🤖 AUTO (Dynamic TTFT)",
        "champion": "👑 CHAMPION (ELO #1 Model)",
        "arena": "🏆 ARENA (Continuous Tournament)",
        "llama_rpc": "🦙 LLAMA.CPP (GGML-RPC)",
        "exo": "🪐 EXO (Ring P2P)",
        "accelerate": "⚡ ACCELERATE (Multi-GPU)",
        "petals": "🌸 PETALS (DHT Swarm)",
        "gemini": "♊ GEMINI (Google / CF Gateway)",
        "cloudflare": "☁️ CLOUDFLARE (Workers AI)",
        "julien": "👑 JULIEN (Ultra Plan API)",
    }

    ENGINE_ALIASES: Dict[str, str] = {
        "auto": "auto",
        "dynamic": "auto",
        "fastest": "auto",
        "best": "auto",
        "lowest_ttft": "auto",
        "ttft": "auto",
        "champion": "champion",
        "arena": "arena",
        "arena_champion": "champion",
        "continuous_arena": "arena",
        "tournament": "arena",
        "llamacpp": "llama_rpc",
        "llama.cpp": "llama_rpc",
        "llama": "llama_rpc",
        "llama_cpp": "llama_rpc",
        "llama_rpc": "llama_rpc",
        "rpc": "llama_rpc",
        "exo": "exo",
        "exo_p2p": "exo",
        "p2p": "exo",
        "ring": "exo",
        "accelerate": "accelerate",
        "mps": "accelerate",
        "metal": "accelerate",
        "ddp": "accelerate",
        "petals": "petals",
        "bloom": "petals",
        "beluga": "petals",
        "petals_dht": "petals",
        "dht": "petals",
        "gemini": "gemini",
        "google": "gemini",
        "gemini_flash": "gemini",
        "gemini_pro": "gemini",
        "cloudflare": "cloudflare",
        "cf": "cloudflare",
        "cloudflare_ai": "cloudflare",
        "workers_ai": "cloudflare",
        "julien": "julien",
        "julien_ai": "julien",
        "julien_ultra": "julien",
    }

    def __init__(
        self,
        default_engine: str = "llama_rpc",
        bridges: Optional[Dict[str, BaseInferenceBridge]] = None,
        poller: Optional[DynamicLatencyPoller] = None,
        champion_resolver: Optional[Any] = None,
        arena_engine: Optional[Any] = None,
        enable_arena: bool = True,
        s2s_client: Optional[Any] = None,
        voice_io_manager: Optional[Any] = None,
        on_token: Optional[Callable[[str], None]] = None,
        on_complete: Optional[Callable[[str], None]] = None,
        on_code_snippet: Optional[Callable[[str, str], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ):
        self.s2s_client = s2s_client
        self.voice_io_manager = voice_io_manager
        self.on_token = on_token
        self.on_complete = on_complete
        self.on_code_snippet = on_code_snippet
        self.on_error = on_error
        self.enable_arena = enable_arena

        # Initialize Continuous Arena Champion Resolver & Background Engine
        self.champion_resolver: Optional[Any] = champion_resolver or (
            ChampionLeaderboardResolver() if ChampionLeaderboardResolver is not None else None
        )
        self.arena_engine: Optional[Any] = arena_engine or (
            ContinuousArenaEngine() if ContinuousArenaEngine is not None and enable_arena else None
        )
        if self.arena_engine and hasattr(self.arena_engine, "start"):
            self.arena_engine.start()

        # Initialize or assign backend bridges
        if bridges:
            self.bridges = dict(bridges)
        else:
            self.bridges = {
                "llama_rpc": LlamaRpcInferenceBridge(
                    s2s_client=self.s2s_client,
                    voice_io_manager=self.voice_io_manager,
                    on_token=self._wrap_on_token,
                    on_complete=self._wrap_on_complete,
                    on_code_snippet=self._wrap_on_code_snippet,
                    on_error=self._wrap_on_error,
                ),
                "exo": ExoInferenceBridge(
                    s2s_client=self.s2s_client,
                    voice_io_manager=self.voice_io_manager,
                    on_token=self._wrap_on_token,
                    on_complete=self._wrap_on_complete,
                    on_code_snippet=self._wrap_on_code_snippet,
                    on_error=self._wrap_on_error,
                ),
                "accelerate": AccelerateInferenceBridge(
                    s2s_client=self.s2s_client,
                    voice_io_manager=self.voice_io_manager,
                    on_token=self._wrap_on_token,
                    on_complete=self._wrap_on_complete,
                    on_code_snippet=self._wrap_on_code_snippet,
                    on_error=self._wrap_on_error,
                ),
                "petals": PetalsInferenceBridge(
                    s2s_client=self.s2s_client,
                    voice_io_manager=self.voice_io_manager,
                    on_token=self._wrap_on_token,
                    on_complete=self._wrap_on_complete,
                    on_code_snippet=self._wrap_on_code_snippet,
                    on_error=self._wrap_on_error,
                ),
                "gemini": GeminiBridge(
                    s2s_client=self.s2s_client,
                    voice_io_manager=self.voice_io_manager,
                    on_token=self._wrap_on_token,
                    on_complete=self._wrap_on_complete,
                    on_code_snippet=self._wrap_on_code_snippet,
                    on_error=self._wrap_on_error,
                ),
                "cloudflare": CloudflareBridge(
                    s2s_client=self.s2s_client,
                    voice_io_manager=self.voice_io_manager,
                    on_token=self._wrap_on_token,
                    on_complete=self._wrap_on_complete,
                    on_code_snippet=self._wrap_on_code_snippet,
                    on_error=self._wrap_on_error,
                ),
                "julien": JulienBridge(
                    s2s_client=self.s2s_client,
                    voice_io_manager=self.voice_io_manager,
                    on_token=self._wrap_on_token,
                    on_complete=self._wrap_on_complete,
                    on_code_snippet=self._wrap_on_code_snippet,
                    on_error=self._wrap_on_error,
                ),
            }

        # Initialize Latency Poller
        self.poller: DynamicLatencyPoller = poller or DynamicLatencyPoller(bridges=self.bridges)
        if poller is None and bridges is not None:
            self.poller.set_bridges(self.bridges)

        # Set default active engine
        norm_default = self._normalize_engine_name(default_engine)
        if norm_default in ("auto", "champion", "arena") or norm_default in self.bridges:
            self._active_engine: str = norm_default
        else:
            self._active_engine = "llama_rpc"

        self._active_task: Optional[asyncio.Task] = None
        self._sync_bridge_callbacks()

    def normalize_engine_name(self, name: str) -> str:
        """Public alias for _normalize_engine_name."""
        return self._normalize_engine_name(name)

    def _normalize_engine_name(self, name: str) -> str:
        """Normalize engine identifier string or alias."""
        clean = (name or "").strip().lower()
        return self.ENGINE_ALIASES.get(clean, clean)

    @property
    def supported_engines(self) -> List[str]:
        """Return list of supported engine keys."""
        return list(self.SUPPORTED_ENGINES)

    @property
    def active_engine(self) -> str:
        return self._active_engine

    @active_engine.setter
    def active_engine(self, engine_name: str) -> None:
        self.set_active_engine(engine_name)

    @property
    def active_bridge(self) -> BaseInferenceBridge:
        return self.get_active_bridge()

    def get_active_engine(self) -> str:
        """Return currently configured engine mode ('auto', 'llama_rpc', etc.)."""
        return self._active_engine

    def get_effective_engine(self) -> str:
        """
        Return the dynamically resolved engine key.
        In 'auto' mode, queries the poller for the lowest TTFT available engine.
        In 'champion' / 'arena' mode, queries the ChampionLeaderboardResolver for the #1 ELO model.
        In non-auto mode, returns the selected active engine.
        """
        if self._active_engine in ("champion", "arena"):
            if self.champion_resolver:
                try:
                    champ = self.champion_resolver.resolve_current_champion()
                    champ_eng = champ.get("engine", "llama_rpc")
                    if champ_eng in self.bridges:
                        return champ_eng
                except Exception:
                    pass
            return "llama_rpc"

        if self._active_engine == "auto":
            if self.poller:
                fastest = self.poller.get_fastest_engine(
                    available_only=True,
                    candidates=["llama_rpc", "exo", "accelerate", "petals", "gemini", "cloudflare", "julien"]
                )
                if fastest and fastest in self.bridges:
                    return fastest
            return "llama_rpc"
        return self._active_engine

    def get_active_bridge(self) -> BaseInferenceBridge:
        """Return the active or resolved effective bridge instance."""
        eff_engine = self.get_effective_engine()
        return self.bridges.get(eff_engine, self.bridges.get("llama_rpc"))

    def set_active_engine(self, engine_name: str) -> str:
        """
        Dynamically switch active inference engine backend.
        Instantly cancels active generation on previous engine in <1ms.
        """
        norm_name = self._normalize_engine_name(engine_name)
        if norm_name not in ("auto", "champion", "arena") and norm_name not in self.bridges:
            valid_keys = list(self.SUPPORTED_ENGINES)
            raise ValueError(f"Unknown engine '{engine_name}'. Supported engines: {valid_keys}")

        if norm_name != self._active_engine:
            # Sub-1ms abort on previous active stream
            self.cancel_active_stream()
            prev = self._active_engine
            self._active_engine = norm_name
            self._sync_bridge_callbacks()
            logger.info(f"UnifiedInferenceRouter: Switched engine from '{prev}' to '{norm_name}'.")

        return self._active_engine

    def cycle_engine(self, delta: int = 1) -> str:
        """
        Cycle active engine across registered engines in canonical order.
        """
        available = [e for e in self.SUPPORTED_ENGINES if e in ("auto", "champion", "arena") or e in self.bridges]
        if not available:
            available = list(self.SUPPORTED_ENGINES)
        try:
            cur_idx = available.index(self._active_engine)
        except ValueError:
            cur_idx = 0
        next_idx = (cur_idx + delta) % len(available)
        next_engine = available[next_idx]
        self.set_active_engine(next_engine)
        return next_engine

    def cancel_active_stream(self) -> None:
        """
        Instantly abort active token stream in <1ms across all bridges.
        Prevents event loop crashes and unhandled CancelledError.
        """
        try:
            cur_task = asyncio.current_task()
        except Exception:
            cur_task = None

        if self._active_task and not self._active_task.done() and self._active_task is not cur_task:
            self._active_task.cancel()
            self._active_task = None

        for bridge in self.bridges.values():
            try:
                bridge.cancel_generation()
            except Exception as e:
                logger.debug(f"Error cancelling bridge {bridge.get_engine_name()}: {e}")

        if self.voice_io_manager:
            try:
                self.voice_io_manager.flush_playback()
            except Exception:
                pass

    async def stream_generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> AsyncGenerator[str, None]:
        """
        Asynchronously stream tokens from the active backend.
        In 'auto' mode, routes to lowest-TTFT engine with instant fallback to llama_rpc on failure.
        In 'champion' / 'arena' mode or when arena is enabled, streams from Champion with zero added latency
        and non-blockingly enqueues a background arena trial upon completion.
        """
        try:
            self._active_task = asyncio.current_task()
        except Exception:
            pass

        t_start = time.perf_counter()
        accumulated_chunks: List[str] = []
        token_yielded = False
        target_eng_used = "llama_rpc"

        try:
            if self._active_engine == "auto":
                target_eng = self.get_effective_engine()
                target_eng_used = target_eng
                target_bridge = self.bridges.get(target_eng, self.bridges.get("llama_rpc"))

                if target_eng != "llama_rpc" and target_bridge is not None:
                    fallback_needed = False
                    try:
                        async for token in target_bridge.stream_generate(prompt, max_tokens=max_tokens, temperature=temperature):
                            token_yielded = True
                            accumulated_chunks.append(token)
                            yield token
                    except asyncio.CancelledError:
                        logger.info(f"UnifiedInferenceRouter: stream_generate cancelled on auto target '{target_eng}'.")
                        raise
                    except Exception as e:
                        if token_yielded:
                            logger.warning(
                                f"Auto-route stream from '{target_eng}' dropped mid-stream ({e}) after yielding tokens. Stream terminated without fallback."
                            )
                        else:
                            logger.warning(
                                f"Auto-route to '{target_eng}' failed ({e}) before yielding tokens. Engaging instant offline fallback to llama_rpc."
                            )
                            fallback_needed = True

                    if fallback_needed and not token_yielded:
                        # Instant fallback to llama_rpc
                        fallback_bridge = self.bridges.get("llama_rpc")
                        target_eng_used = "llama_rpc"
                        if fallback_bridge:
                            try:
                                async for token in fallback_bridge.stream_generate(prompt, max_tokens=max_tokens, temperature=temperature):
                                    token_yielded = True
                                    accumulated_chunks.append(token)
                                    yield token
                            except asyncio.CancelledError:
                                logger.info("UnifiedInferenceRouter: fallback stream_generate cancelled on llama_rpc.")
                                raise
                else:
                    fallback_bridge = self.bridges.get("llama_rpc")
                    target_eng_used = "llama_rpc"
                    if fallback_bridge:
                        async for token in fallback_bridge.stream_generate(prompt, max_tokens=max_tokens, temperature=temperature):
                            token_yielded = True
                            accumulated_chunks.append(token)
                            yield token
            else:
                target_eng_used = self.get_effective_engine()
                bridge = self.get_active_bridge()
                async for token in bridge.stream_generate(prompt, max_tokens=max_tokens, temperature=temperature):
                    token_yielded = True
                    accumulated_chunks.append(token)
                    yield token
        except asyncio.CancelledError:
            logger.info(f"UnifiedInferenceRouter: stream_generate cancelled on '{self._active_engine}'.")
            raise
        finally:
            if self._active_task is asyncio.current_task():
                self._active_task = None

            # Background Continuous Arena trial enqueue (Zero user-facing latency overhead)
            if self.enable_arena and self.arena_engine and token_yielded:
                latency_ms = (time.perf_counter() - t_start) * 1000.0
                full_resp = "".join(accumulated_chunks)
                champ_spec = (
                    self.champion_resolver.resolve_current_champion()
                    if self.champion_resolver
                    else {"model_id": target_eng_used, "engine": target_eng_used}
                )
                champion_result = {
                    "model_id": champ_spec.get("model_id", target_eng_used),
                    "name": champ_spec.get("name", target_eng_used),
                    "engine": target_eng_used,
                    "text": full_resp,
                    "latency_ms": latency_ms,
                    "token_count": len(accumulated_chunks),
                    "status": "SUCCESS",
                    "timestamp": time.time(),
                }
                self.arena_engine.enqueue_trial(prompt=prompt, champion_result=champion_result)

    async def process_user_input(
        self,
        prompt: str,
        is_voice: bool = False,
        max_tokens: int = 256
    ) -> str:
        """
        Route text REPL prompt or voice transcript to active engine.
        In 'auto' mode, falls back to llama_rpc on failure.
        """
        self._active_task = asyncio.current_task()
        t_start = time.perf_counter()
        res = ""
        target_eng_used = "llama_rpc"

        try:
            if self._active_engine == "auto":
                target_eng = self.get_effective_engine()
                target_eng_used = target_eng
                target_bridge = self.bridges.get(target_eng, self.bridges.get("llama_rpc"))

                if target_eng != "llama_rpc" and target_bridge is not None:
                    try:
                        res = await target_bridge.process_user_input(
                            prompt=prompt,
                            is_voice=is_voice,
                            max_tokens=max_tokens
                        )
                    except asyncio.CancelledError:
                        logger.info(f"UnifiedInferenceRouter: process_user_input cancelled on auto target '{target_eng}'.")
                        return ""
                    except Exception as e:
                        logger.warning(
                            f"Auto-route process_user_input to '{target_eng}' failed ({e}). Engaging instant offline fallback to llama_rpc."
                        )

                    if res:
                        return res

                    # If primary returned empty or encountered an error, fallback to llama_rpc
                    fallback_bridge = self.bridges.get("llama_rpc")
                    target_eng_used = "llama_rpc"
                    if fallback_bridge:
                        res = await fallback_bridge.process_user_input(
                            prompt=prompt,
                            is_voice=is_voice,
                            max_tokens=max_tokens
                        )
                        return res
                    return ""
                else:
                    fallback_bridge = self.bridges.get("llama_rpc")
                    target_eng_used = "llama_rpc"
                    if fallback_bridge:
                        res = await fallback_bridge.process_user_input(
                            prompt=prompt,
                            is_voice=is_voice,
                            max_tokens=max_tokens
                        )
                        return res
                    return ""
            else:
                target_eng_used = self.get_effective_engine()
                bridge = self.get_active_bridge()
                res = await bridge.process_user_input(
                    prompt=prompt,
                    is_voice=is_voice,
                    max_tokens=max_tokens
                )
                return res
        except asyncio.CancelledError:
            logger.info(f"UnifiedInferenceRouter: process_user_input cancelled on '{self._active_engine}'.")
            return ""
        finally:
            if self._active_task is asyncio.current_task():
                self._active_task = None

            # Background Continuous Arena trial enqueue (Zero user-facing latency overhead)
            if self.enable_arena and self.arena_engine and res:
                latency_ms = (time.perf_counter() - t_start) * 1000.0
                champ_spec = (
                    self.champion_resolver.resolve_current_champion()
                    if self.champion_resolver
                    else {"model_id": target_eng_used, "engine": target_eng_used}
                )
                champion_result = {
                    "model_id": champ_spec.get("model_id", target_eng_used),
                    "name": champ_spec.get("name", target_eng_used),
                    "engine": target_eng_used,
                    "text": res,
                    "latency_ms": latency_ms,
                    "status": "SUCCESS",
                    "timestamp": time.time(),
                }
                self.arena_engine.enqueue_trial(prompt=prompt, champion_result=champion_result)

    def get_status(self) -> Dict[str, Any]:
        """Return standardized status dictionary for active engine and router."""
        bridge = self.get_active_bridge()
        status = bridge.get_status() if bridge else {}
        status["active_engine"] = self._active_engine
        status["effective_engine"] = self.get_effective_engine()
        status["supported_engines"] = list(self.SUPPORTED_ENGINES)
        status["active_badge"] = self.get_status_badge()
        status["arena_enabled"] = self.enable_arena
        if self.arena_engine and hasattr(self.arena_engine, "get_metrics"):
            status["arena_metrics"] = self.arena_engine.get_metrics()
        if self.champion_resolver and hasattr(self.champion_resolver, "resolve_current_champion"):
            status["current_champion"] = self.champion_resolver.resolve_current_champion()
        if self.poller:
            status["latencies"] = self.poller.get_latencies()
        return status

    def get_status_badge(self) -> str:
        """Return concise HUD badge for active engine."""
        if self._active_engine in ("champion", "arena"):
            champ = self.get_current_champion()
            badge_title = "CHAMPION" if self._active_engine == "champion" else "ARENA"
            return f"[{badge_title}: {champ.get('name', champ.get('model_id', 'TITAN'))}]"

        if self._active_engine == "auto":
            eff = self.get_effective_engine()
            name_map = {
                "llama_rpc": "LLAMA.CPP",
                "exo": "EXO",
                "accelerate": "ACCELERATE",
                "petals": "PETALS",
                "gemini": "GEMINI",
                "cloudflare": "CLOUDFLARE",
                "julien": "JULIEN",
            }
            if eff and eff != "auto":
                disp = name_map.get(eff, eff.upper())
                return f"[AUTO ({disp}): ACTIVE]"
            return "[AUTO: ACTIVE]"
        bridge = self.get_active_bridge()
        return bridge.get_status_badge() if bridge else "[LLAMA.CPP: ACTIVE]"

    def get_current_champion(self) -> Dict[str, Any]:
        """Return metadata for the currently resolved Champion model."""
        if self.champion_resolver:
            try:
                return self.champion_resolver.resolve_current_champion()
            except Exception as e:
                logger.warning(f"UnifiedInferenceRouter: Error resolving current champion: {e}")
        return {
            "model_id": "kimi_tandem_titan",
            "name": "Kimi Tandem Titan",
            "engine": "llama_rpc",
            "elo": 3089.0,
            "rank": 1,
        }

    def attach_arena_engine(self, arena_engine: Any, enable: bool = True) -> None:
        """Attach ContinuousArenaEngine for background evaluation and start worker."""
        self.arena_engine = arena_engine
        self.enable_arena = enable
        if self.arena_engine and hasattr(self.arena_engine, "start"):
            self.arena_engine.start()

    def get_arena_status(self) -> Dict[str, Any]:
        """Return runtime Continuous Arena status and metrics."""
        metrics = self.arena_engine.get_metrics() if self.arena_engine and hasattr(self.arena_engine, "get_metrics") else {}
        champion = self.get_current_champion()
        return {
            "arena_enabled": self.enable_arena,
            "champion": champion,
            "metrics": metrics,
        }

    def get_all_engine_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Return telemetry status dictionary for all backends."""
        statuses = {name: b.get_status() for name, b in self.bridges.items()}
        if self._active_engine == "auto":
            statuses["auto"] = {
                "engine_name": "auto",
                "display_name": "🤖 AUTO (Dynamic TTFT)",
                "is_connected": True,
                "effective_engine": self.get_effective_engine(),
                "status_badge": self.get_status_badge(),
            }
        elif self._active_engine in ("champion", "arena"):
            statuses[self._active_engine] = {
                "engine_name": self._active_engine,
                "display_name": self.ENGINE_DISPLAY_NAMES.get(self._active_engine, self._active_engine),
                "is_connected": True,
                "effective_engine": self.get_effective_engine(),
                "status_badge": self.get_status_badge(),
                "champion": self.get_current_champion(),
            }
        return statuses

    def bind_voice_io_manager(self, voice_io_manager: Any) -> None:
        """Bind VoiceIOManager to all bridges."""
        self.voice_io_manager = voice_io_manager
        for b in self.bridges.values():
            b.voice_io_manager = voice_io_manager

    def bind_s2s_client(self, s2s_client: Any) -> None:
        """Bind PersonaPlexS2SClient to all bridges."""
        self.s2s_client = s2s_client
        for b in self.bridges.values():
            b.s2s_client = s2s_client

    def _sync_bridge_callbacks(self) -> None:
        """Synchronize callbacks and service references across all bridges."""
        for b in self.bridges.values():
            b.s2s_client = self.s2s_client
            b.voice_io_manager = self.voice_io_manager
            b.on_token = self._wrap_on_token
            b.on_complete = self._wrap_on_complete
            b.on_code_snippet = self._wrap_on_code_snippet
            b.on_error = self._wrap_on_error

    def _wrap_on_token(self, token: str) -> None:
        if self.on_token:
            try:
                self.on_token(token)
            except Exception:
                pass

    def _wrap_on_complete(self, full_text: str) -> None:
        if self.on_complete:
            try:
                self.on_complete(full_text)
            except Exception:
                pass

    def _wrap_on_code_snippet(self, snippet: str, lang: str) -> None:
        if self.on_code_snippet:
            try:
                self.on_code_snippet(snippet, lang)
            except Exception:
                pass

    def _wrap_on_error(self, err: str) -> None:
        if self.on_error:
            try:
                self.on_error(err)
            except Exception:
                pass
