#!/usr/bin/env python3
"""
================================================================================
Lauburu Sovereign Mesh: Multi-Account Free-Tier AI Credential & Quota Manager
================================================================================
Subsystem: 06_scripts_and_tooling/cloud_and_quota/multi_account_free_tier_manager.py
Version: 2.0.0-SOVEREIGN-DUAL-ACCOUNT

Governed by:
- Rule #0 & Rule #1 (Zero-Mock Empirical Truth Verification)
- Rule #2 (Tri-Vault Storage Synchronization)
- Rule #3 (Host Sanctuary & Dynamic RAM Governance Invariant)
- Rule #5 (Sovereign Token Masking: No raw keys in logs/stdout)
- Rule #6 (Multi-Provider Cloud Quota & Graduated Autonomy Protocol)

Architecture:
1. Dual-Account Management:
   - Personal Account: aaron.t.maher@gmail.com
   - Business Account: lauburu@lauburugrappling.com
2. Aggregated Quota Pooling:
   - Google AI Studio: 2 accounts x 1,500 RPD = 3,000 RPD (30 RPM aggregate)
   - Cloudflare Workers AI: 2 accounts x 10,000 neurons (~1,600 RPD)
   - Groq Fast Inference: 14,400 RPD (30 RPM)
   - NVIDIA NIM: 2,000 RPD
   - xAI Grok: 1,000 RPD
   - Google Jules AI: 300 tasks/day (60 concurrent VMs)
3. Smart Key Rotation:
   - Automatic round-robin, failover on 429/403/400 errors, per-account backoffs.
   - Strict 0600 file permissions and credential masking.
================================================================================
"""

from __future__ import annotations

import json
import logging
import os
import stat
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path("/Volumes/Lauburu-Monorepo")
USER_ENV = Path.home() / ".env"
MONO_ENV = REPO_ROOT / ".env"
VAULT_CONFIG = Path.home() / ".lauburu/config.yaml"
QUOTA_TRACKER_FILE = REPO_ROOT / "04_data_and_memory/data/cloud_api_quota_state.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [MultiAccountKeyManager] %(message)s"
)
logger = logging.getLogger("MultiAccountKeyManager")


@dataclass
class AccountCredential:
    account_email: str
    account_type: str  # 'personal' or 'business'
    provider: str      # 'google_gemini', 'cloudflare', 'groq', 'nvidia', 'xai', 'jules', 'hf'
    api_key: str
    account_id: Optional[str] = None
    daily_cap: int = 1500
    used_today: int = 0
    consecutive_errors: int = 0
    backoff_until: float = 0.0
    is_healthy: bool = True

    def mask(self) -> str:
        if not self.api_key:
            return "[EMPTY]"
        if len(self.api_key) <= 8:
            return "[REDACTED]"
        return f"{self.api_key[:4]}...[REDACTED_{self.account_type.upper()}]...{self.api_key[-4:]}"


class MultiAccountFreeTierManager:
    """
    Manages dual-account free-tier AI keys across aaron.t.maher@gmail.com and
    lauburu@lauburugrappling.com with round-robin balancing and automatic failover.
    """

    ACCOUNT_EMAILS = {
        "personal": "aaron.t.maher@gmail.com",
        "business": "lauburu@lauburugrappling.com",
    }

    def __init__(self):
        self._credentials: Dict[str, List[AccountCredential]] = {
            "google_gemini": [],
            "cloudflare": [],
            "groq": [],
            "nvidia": [],
            "xai": [],
            "jules": [],
            "hf": [],
        }
        self._provider_indices: Dict[str, int] = {k: 0 for k in self._credentials}
        self._load_all_sources()

    def _read_env_file(self, path: Path) -> Dict[str, str]:
        env_dict = {}
        if path.exists():
            try:
                for line in path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        env_dict[k.strip()] = v.strip().strip("\"'")
            except Exception as e:
                logger.warning(f"Could not read env file {path}: {e}")
        return env_dict

    def _load_all_sources(self) -> None:
        """Loads and consolidates credentials from process env, ~/.env, and repo .env."""
        merged: Dict[str, str] = {}
        merged.update(self._read_env_file(USER_ENV))
        merged.update(self._read_env_file(MONO_ENV))
        for k, v in os.environ.items():
            if v:
                merged[k] = v

        # 1. Google Gemini (Personal & Business)
        gemini_personal = (
            merged.get("GEMINI_API_KEY_PERSONAL")
            or merged.get("GEMINI_API_KEY_AARON")
            or merged.get("GEMINI_API_KEY")
            or merged.get("GOOGLE_API_KEY")
            or ""
        )
        gemini_lauburu = (
            merged.get("GEMINI_API_KEY_LAUBURU")
            or merged.get("GEMINI_API_KEY_BUSINESS")
            or ""
        )

        if gemini_personal:
            self._credentials["google_gemini"].append(
                AccountCredential(
                    account_email=self.ACCOUNT_EMAILS["personal"],
                    account_type="personal",
                    provider="google_gemini",
                    api_key=gemini_personal,
                    daily_cap=1500,
                )
            )
        if gemini_lauburu and gemini_lauburu != gemini_personal:
            self._credentials["google_gemini"].append(
                AccountCredential(
                    account_email=self.ACCOUNT_EMAILS["business"],
                    account_type="business",
                    provider="google_gemini",
                    api_key=gemini_lauburu,
                    daily_cap=1500,
                )
            )

        # 2. Cloudflare Workers AI (Personal & Business)
        cf_account_personal = merged.get("CLOUDFLARE_ACCOUNT_ID_PERSONAL") or merged.get("CLOUDFLARE_ACCOUNT_ID") or ""
        cf_token_personal = merged.get("CLOUDFLARE_API_TOKEN_PERSONAL") or merged.get("CLOUDFLARE_API_TOKEN") or ""
        cf_account_lauburu = merged.get("CLOUDFLARE_ACCOUNT_ID_LAUBURU") or ""
        cf_token_lauburu = merged.get("CLOUDFLARE_API_TOKEN_LAUBURU") or ""

        if cf_token_personal:
            self._credentials["cloudflare"].append(
                AccountCredential(
                    account_email=self.ACCOUNT_EMAILS["personal"],
                    account_type="personal",
                    provider="cloudflare",
                    api_key=cf_token_personal,
                    account_id=cf_account_personal,
                    daily_cap=800,
                )
            )
        if cf_token_lauburu and cf_token_lauburu != cf_token_personal:
            self._credentials["cloudflare"].append(
                AccountCredential(
                    account_email=self.ACCOUNT_EMAILS["business"],
                    account_type="business",
                    provider="cloudflare",
                    api_key=cf_token_lauburu,
                    account_id=cf_account_lauburu or cf_account_personal,
                    daily_cap=800,
                )
            )

        # 3. Groq
        groq_key = merged.get("GROQ_API_KEY") or ""
        if groq_key:
            self._credentials["groq"].append(
                AccountCredential(
                    account_email=self.ACCOUNT_EMAILS["personal"],
                    account_type="personal",
                    provider="groq",
                    api_key=groq_key,
                    daily_cap=14400,
                )
            )

        # 4. NVIDIA NIM
        nvidia_key = merged.get("NVIDIA_API_KEY") or ""
        if nvidia_key:
            self._credentials["nvidia"].append(
                AccountCredential(
                    account_email=self.ACCOUNT_EMAILS["personal"],
                    account_type="personal",
                    provider="nvidia",
                    api_key=nvidia_key,
                    daily_cap=2000,
                )
            )

        # 5. xAI Grok
        xai_key = merged.get("XAI_API_KEY") or ""
        if xai_key:
            self._credentials["xai"].append(
                AccountCredential(
                    account_email=self.ACCOUNT_EMAILS["personal"],
                    account_type="personal",
                    provider="xai",
                    api_key=xai_key,
                    daily_cap=1000,
                )
            )

        # 6. Hugging Face
        hf_token = merged.get("HF_TOKEN") or ""
        if hf_token:
            self._credentials["hf"].append(
                AccountCredential(
                    account_email=self.ACCOUNT_EMAILS["personal"],
                    account_type="personal",
                    provider="hf",
                    api_key=hf_token,
                    daily_cap=10000,
                )
            )

        # 7. Google Jules
        jules_token = merged.get("JULES_API_KEY") or merged.get("GITHUB_TOKEN") or ""
        if jules_token:
            self._credentials["jules"].append(
                AccountCredential(
                    account_email=self.ACCOUNT_EMAILS["personal"],
                    account_type="personal",
                    provider="jules",
                    api_key=jules_token,
                    daily_cap=300,
                )
            )

        logger.info(
            f"Initialized MultiAccountFreeTierManager: Google Gemini accounts={len(self._credentials['google_gemini'])}, "
            f"Cloudflare accounts={len(self._credentials['cloudflare'])}, Groq={len(self._credentials['groq'])}, "
            f"NVIDIA={len(self._credentials['nvidia'])}, xAI={len(self._credentials['xai'])}"
        )

    def register_account_key(
        self,
        provider: str,
        account_type: str,
        api_key: str,
        account_id: Optional[str] = None,
        persist: bool = True
    ) -> None:
        """Registers or updates a credential for a specific account and optionally persists it."""
        email = self.ACCOUNT_EMAILS.get(account_type, f"{account_type}@lauburugrappling.com")
        creds = self._credentials.setdefault(provider, [])
        existing = next((c for c in creds if c.account_type == account_type), None)

        if existing:
            existing.api_key = api_key
            existing.account_id = account_id or existing.account_id
            existing.is_healthy = True
            existing.consecutive_errors = 0
            existing.backoff_until = 0.0
        else:
            daily_cap = 1500 if provider == "google_gemini" else (800 if provider == "cloudflare" else 1000)
            creds.append(
                AccountCredential(
                    account_email=email,
                    account_type=account_type,
                    provider=provider,
                    api_key=api_key,
                    account_id=account_id,
                    daily_cap=daily_cap,
                )
            )

        if persist:
            self._persist_key(provider, account_type, api_key, account_id)

    def _persist_key(self, provider: str, account_type: str, api_key: str, account_id: Optional[str]) -> None:
        """Persists keys securely to ~/.env and repo .env with chmod 0600."""
        env_var_name = f"{provider.upper()}_API_KEY_{account_type.upper()}"
        if provider == "google_gemini":
            env_var_name = f"GEMINI_API_KEY_{account_type.upper()}"
        elif provider == "cloudflare":
            env_var_name = f"CLOUDFLARE_API_TOKEN_{account_type.upper()}"

        for env_path in [USER_ENV, MONO_ENV]:
            try:
                env_path.parent.mkdir(parents=True, exist_ok=True)
                lines = []
                found = False
                if env_path.exists():
                    for line in env_path.read_text(encoding="utf-8").splitlines():
                        if line.startswith(f"{env_var_name}=") or line.startswith(f"# {env_var_name}="):
                            lines.append(f"{env_var_name}={api_key}")
                            found = True
                        else:
                            lines.append(line)
                if not found:
                    lines.append(f"{env_var_name}={api_key}")

                if provider == "cloudflare" and account_id:
                    acc_var = f"CLOUDFLARE_ACCOUNT_ID_{account_type.upper()}"
                    lines = [l for l in lines if not l.startswith(f"{acc_var}=")]
                    lines.append(f"{acc_var}={account_id}")

                env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
                os.chmod(env_path, stat.S_IRUSR | stat.S_IWUSR)
            except Exception as e:
                logger.warning(f"Failed to persist key to {env_path}: {e}")

    def get_active_credential(self, provider: str) -> Optional[AccountCredential]:
        """Returns the next healthy credential in round-robin sequence for the given provider."""
        creds = self._credentials.get(provider, [])
        if not creds:
            return None

        now = time.time()
        healthy_creds = [c for c in creds if c.is_healthy and c.backoff_until <= now]

        if not healthy_creds:
            # Check if all are on backoff; pick the one with earliest backoff expiry
            earliest = min(creds, key=lambda c: c.backoff_until)
            if earliest.backoff_until <= now + 30.0:
                logger.info(f"All {provider} credentials on backoff; returning earliest recovering account {earliest.account_email}")
                return earliest
            return None

        idx = self._provider_indices.get(provider, 0) % len(healthy_creds)
        self._provider_indices[provider] = idx + 1
        return healthy_creds[idx]

    def record_usage(self, credential: AccountCredential, success: bool, status_code: Optional[int] = None) -> None:
        """Records API usage and applies dynamic backoff on rate limits or errors."""
        now = time.time()
        if success:
            credential.used_today += 1
            credential.consecutive_errors = 0
            credential.is_healthy = True
        else:
            credential.consecutive_errors += 1
            if status_code == 429:
                # Rate limited: backoff 60s
                credential.backoff_until = now + 60.0
                logger.warning(f"Account {credential.account_email} hit 429 RPM cap on {credential.provider}. Backing off 60s.")
            elif status_code in (400, 401, 403):
                # Auth error: backoff 300s or mark unhealthy if persistent
                if credential.consecutive_errors >= 2:
                    credential.is_healthy = False
                    credential.backoff_until = now + 3600.0
                    logger.error(f"Account {credential.account_email} failed auth on {credential.provider} (status {status_code}). Marked unhealthy.")
                else:
                    credential.backoff_until = now + 300.0
            else:
                credential.backoff_until = now + 15.0

    def get_aggregate_quota_status(self) -> Dict[str, Any]:
        """Returns total pooled capacity and usage across all accounts and providers."""
        summary = {
            "accounts": self.ACCOUNT_EMAILS,
            "providers": {},
            "total_daily_capacity": 0,
            "total_used_today": 0,
            "cost_usd": 0.00,
        }

        for provider, creds in self._credentials.items():
            prov_cap = sum(c.daily_cap for c in creds)
            prov_used = sum(c.used_today for c in creds)
            healthy_count = sum(1 for c in creds if c.is_healthy)
            summary["providers"][provider] = {
                "accounts_configured": len(creds),
                "healthy_accounts": healthy_count,
                "daily_cap": prov_cap,
                "used_today": prov_used,
                "accounts_detail": [
                    {
                        "email": c.account_email,
                        "type": c.account_type,
                        "used": c.used_today,
                        "cap": c.daily_cap,
                        "healthy": c.is_healthy,
                        "masked_key": c.mask(),
                    }
                    for c in creds
                ]
            }
            summary["total_daily_capacity"] += prov_cap
            summary["total_used_today"] += prov_used

        return summary


# Global singleton instance
multi_account_manager = MultiAccountFreeTierManager()


if __name__ == "__main__":
    status = multi_account_manager.get_aggregate_quota_status()
    print("\n" + "=" * 80)
    print("Lauburu Sovereign Mesh: Multi-Account Free-Tier AI Status")
    print("=" * 80)
    print(f"Personal Account: {status['accounts']['personal']}")
    print(f"Business Account: {status['accounts']['business']}")
    print(f"Total Daily Free Capacity: {status['total_daily_capacity']:,} tasks/day ($0.00)")
    print(f"Total Used Today: {status['total_used_today']:,}")
    print("-" * 80)
    for p, details in status["providers"].items():
        print(f"[{p.upper()}] Configured: {details['accounts_configured']}, Healthy: {details['healthy_accounts']}, Cap: {details['daily_cap']:,}/day")
        for acc in details["accounts_detail"]:
            print(f"   -> {acc['type'].upper()} ({acc['email']}): used={acc['used']}/{acc['cap']}, key={acc['masked_key']}, healthy={acc['healthy']}")
    print("=" * 80 + "\n")
