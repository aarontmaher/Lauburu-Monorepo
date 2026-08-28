"""
Canonical Multi-AI Quota Governor & Free-Tier Prioritizer
Version: 3.0.0-CANONICAL

Enforces user directive and resource governance:
- Priority Tier 1: Local AI (llama.cpp RPC 8081-8084 / Exo 52415) ($0 spend)
- Priority Tier 2: Cloudflare AI Free Tier ($0 spend, up to 10,000 req/day)
- Priority Tier 3: Gemini Free Tier / Gemini 3.7 Flash Ultra Allowance (up to 300 req / 24h)
- Priority Tier 4: Paid Cloud API Fallback (strictly capped)

Tracks request counters per 24-hour rolling window, rate limits, and health status.
"""

import time
import threading
from collections import deque
from typing import Dict, Any, List, Optional


class QuotaGovernor:
    """
    Thread-safe 24-hour rolling window quota governor and rate limiter.
    """

    def __init__(
        self,
        gemini_daily_limit: int = 300,
        cloudflare_daily_limit: int = 10000,
        window_seconds: float = 86400.0,
    ):
        self.window_seconds: float = window_seconds
        self.max_gemini_daily_requests: int = gemini_daily_limit
        self.max_cloudflare_daily_requests: int = cloudflare_daily_limit
        self.max_paid_daily_requests: int = 50  # Strictly capped fallback limit

        self._lock = threading.RLock()
        self._provider_health: Dict[str, bool] = {
            "local_llamacpp": True,
            "local_exo": True,
            "cloudflare_ai_free": True,
            "gemini_flash_free": True,
            "paid_cloud_fallback": False,  # Disabled by default
        }

        # Rolling window request timestamps per provider: deque of floats
        self._request_history: Dict[str, deque] = {
            "local_llamacpp": deque(),
            "local_exo": deque(),
            "cloudflare_ai_free": deque(),
            "gemini_flash_free": deque(),
            "paid_cloud_fallback": deque(),
        }

        # Token counters
        self._tokens_consumed: Dict[str, int] = {
            "local_llamacpp": 0,
            "local_exo": 0,
            "cloudflare_ai_free": 0,
            "gemini_flash_free": 0,
            "paid_cloud_fallback": 0,
        }

        # Explicit override counter for test compatibility
        self._explicit_gemini_count: Optional[int] = None

    @property
    def gemini_daily_requests_count(self) -> int:
        with self._lock:
            if self._explicit_gemini_count is not None:
                return self._explicit_gemini_count
            self._prune_history("gemini_flash_free")
            return len(self._request_history["gemini_flash_free"])

    @gemini_daily_requests_count.setter
    def gemini_daily_requests_count(self, count: int) -> None:
        with self._lock:
            self._explicit_gemini_count = count

    def set_provider_status(self, provider_id: str, is_online: bool) -> None:
        """Dynamically update provider online/healthy status."""
        with self._lock:
            self._provider_health[provider_id] = is_online

    def get_provider_status(self, provider_id: str) -> bool:
        """Check if provider is marked healthy and online."""
        with self._lock:
            return self._provider_health.get(provider_id, False)

    def _prune_history(self, provider_id: str) -> None:
        """Remove timestamps older than the rolling window."""
        cutoff = time.time() - self.window_seconds
        history = self._request_history.get(provider_id)
        if history:
            while history and history[0] < cutoff:
                history.popleft()

    def can_route_to(self, provider_id: str) -> bool:
        """Check if provider is online and within its rolling 24h quota."""
        with self._lock:
            if not self._provider_health.get(provider_id, False):
                return False

            if provider_id == "gemini_flash_free":
                return self.gemini_daily_requests_count < self.max_gemini_daily_requests
            elif provider_id == "cloudflare_ai_free":
                self._prune_history("cloudflare_ai_free")
                return len(self._request_history["cloudflare_ai_free"]) < self.max_cloudflare_daily_requests
            elif provider_id == "paid_cloud_fallback":
                self._prune_history("paid_cloud_fallback")
                return len(self._request_history["paid_cloud_fallback"]) < self.max_paid_daily_requests
            elif provider_id in ("local_llamacpp", "local_exo"):
                return True

            return False

    def record_request(self, provider_id: str, tokens: int = 0) -> None:
        """Record an executed request against the provider's rolling quota."""
        with self._lock:
            now = time.time()
            if provider_id not in self._request_history:
                self._request_history[provider_id] = deque()
                self._tokens_consumed[provider_id] = 0

            self._request_history[provider_id].append(now)
            self._tokens_consumed[provider_id] += tokens

            if provider_id == "gemini_flash_free" and self._explicit_gemini_count is not None:
                self._explicit_gemini_count += 1

    def get_optimal_provider(self, prefer_local: bool = True) -> Optional[str]:
        """
        Determines the optimal provider adhering to the strict tier hierarchy:
        1. local_llamacpp ($0 spend)
        2. local_exo ($0 spend)
        3. cloudflare_ai_free ($0 spend)
        4. gemini_flash_free (Ultra allowance up to 300 req/24h)
        5. paid_cloud_fallback (strictly capped)
        """
        with self._lock:
            tier_order = [
                "local_llamacpp",
                "local_exo",
                "cloudflare_ai_free",
                "gemini_flash_free",
                "paid_cloud_fallback",
            ] if prefer_local else [
                "cloudflare_ai_free",
                "gemini_flash_free",
                "local_llamacpp",
                "local_exo",
                "paid_cloud_fallback",
            ]

            for provider_id in tier_order:
                if self.can_route_to(provider_id):
                    return provider_id
            return None

    def get_quota_status(self) -> Dict[str, Any]:
        """Return comprehensive snapshot of quotas, rolling counts, and provider health."""
        with self._lock:
            for p in self._request_history:
                self._prune_history(p)

            gemini_used = self.gemini_daily_requests_count
            cf_used = len(self._request_history["cloudflare_ai_free"])
            paid_used = len(self._request_history["paid_cloud_fallback"])

            return {
                "window_seconds": self.window_seconds,
                "timestamp": time.time(),
                "providers": {
                    "local_llamacpp": {
                        "is_online": self._provider_health.get("local_llamacpp", False),
                        "tier": 1,
                        "cost": "$0.00",
                        "requests_24h": len(self._request_history["local_llamacpp"]),
                        "tokens_consumed": self._tokens_consumed["local_llamacpp"],
                        "quota_limit": "UNLIMITED",
                    },
                    "local_exo": {
                        "is_online": self._provider_health.get("local_exo", False),
                        "tier": 1,
                        "cost": "$0.00",
                        "requests_24h": len(self._request_history["local_exo"]),
                        "tokens_consumed": self._tokens_consumed["local_exo"],
                        "quota_limit": "UNLIMITED",
                    },
                    "cloudflare_ai_free": {
                        "is_online": self._provider_health.get("cloudflare_ai_free", False),
                        "tier": 2,
                        "cost": "$0.00",
                        "requests_24h": cf_used,
                        "quota_limit": self.max_cloudflare_daily_requests,
                        "remaining_quota": max(0, self.max_cloudflare_daily_requests - cf_used),
                        "tokens_consumed": self._tokens_consumed["cloudflare_ai_free"],
                    },
                    "gemini_flash_free": {
                        "is_online": self._provider_health.get("gemini_flash_free", False),
                        "tier": 3,
                        "cost": "$0.00 (Ultra Allowance)",
                        "requests_24h": gemini_used,
                        "quota_limit": self.max_gemini_daily_requests,
                        "remaining_quota": max(0, self.max_gemini_daily_requests - gemini_used),
                        "tokens_consumed": self._tokens_consumed["gemini_flash_free"],
                        "is_exhausted": gemini_used >= self.max_gemini_daily_requests,
                    },
                    "paid_cloud_fallback": {
                        "is_online": self._provider_health.get("paid_cloud_fallback", False),
                        "tier": 4,
                        "requests_24h": paid_used,
                        "quota_limit": self.max_paid_daily_requests,
                        "remaining_quota": max(0, self.max_paid_daily_requests - paid_used),
                        "tokens_consumed": self._tokens_consumed["paid_cloud_fallback"],
                    },
                },
                "optimal_provider": self.get_optimal_provider(),
            }

    def reset_window(self) -> None:
        """Reset rolling window counters (for testing or new cycle)."""
        with self._lock:
            self._explicit_gemini_count = None
            for p in self._request_history:
                self._request_history[p].clear()
                self._tokens_consumed[p] = 0


# Global singleton
_quota_governor_instance: Optional[QuotaGovernor] = None
_governor_lock = threading.Lock()


def get_quota_governor() -> QuotaGovernor:
    global _quota_governor_instance
    with _governor_lock:
        if _quota_governor_instance is None:
            _quota_governor_instance = QuotaGovernor()
        return _quota_governor_instance
