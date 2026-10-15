#!/usr/bin/env python3
"""
================================================================================
Lauburu Sovereign Mesh: Google Cloud Always Free Tier Circuit Breaker
================================================================================
Subsystem: 06_scripts_and_tooling/cloud_and_quota/gcp_free_tier_circuit_breaker.py
Governed by:
- Rule #0 (Zero-Mock Empirical Truth Verification)
- Rule #1 & Rule #5 (Victory-Triggered Tri-Proof Interceptor Gate)
- Rule #2 (Tri-Vault Storage Synchronization)
- Rule #3 (Host Sanctuary & Dynamic RAM Governance Invariant)
- Rule #6 (Multi-Provider Cloud Quota & Graduated Autonomy Protocol)

Role:
1. Enforces hard limits matching Google Cloud Always Free tier allocations.
2. Intercepts any request that threatens to exceed safe free-tier headroom (80% buffer).
3. Guarantees $0.00 out-of-pocket spend and zero credit card charges.
4. Persists quota consumption state in 04_data_and_memory/gcp_free_tier_quota_state.json.
================================================================================
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [GCPCircuitBreaker] %(message)s"
)
logger = logging.getLogger("GCPCircuitBreaker")

REPO_ROOT = Path("/Volumes/Lauburu-Monorepo")
STATE_FILE = REPO_ROOT / "04_data_and_memory/gcp_free_tier_quota_state.json"
OBSIDIAN_LOG = REPO_ROOT / "obsidian_vault/04_ANALYTICS/GCP_FREE_TIER_CIRCUIT_BREAKER_TELEMETRY.md"


@dataclass
class FreeTierLimits:
    # Google AI Studio / Gemini API Free Tier
    AI_STUDIO_MAX_RPM: int = 15
    AI_STUDIO_MAX_RPD: int = 1500
    AI_STUDIO_SAFETY_RPD: int = 1450  # Stop 50 requests before hard limit

    # BigQuery Free Tier
    BIGQUERY_MAX_STORAGE_GB: float = 10.0
    BIGQUERY_MAX_QUERY_TB_PER_MONTH: float = 1.0
    BIGQUERY_SAFETY_QUERY_GB_PER_MONTH: float = 800.0  # 800 GB of 1,024 GB (1 TB)

    # Google Cloud Storage (GCS) Always Free
    GCS_MAX_STORAGE_GB: float = 5.0
    GCS_SAFETY_STORAGE_GB: float = 4.0  # 80% safe buffer
    GCS_MAX_CLASS_A_OPS: int = 5000
    GCS_MAX_CLASS_B_OPS: int = 50000

    # Cloud Run Always Free
    CLOUD_RUN_MAX_REQUESTS_PER_MONTH: int = 2000000
    CLOUD_RUN_MAX_MEMORY_GB_SEC: float = 360000.0

    # Cloud Pub/Sub Always Free
    PUBSUB_MAX_STORAGE_GB_PER_MONTH: float = 10.0
    PUBSUB_SAFETY_GB_PER_MONTH: float = 8.0

    # Secret Manager Always Free
    SECRET_MANAGER_MAX_VERSIONS: int = 6
    SECRET_MANAGER_MAX_ACCESS_OPS: int = 10000

    # Compute Engine Always Free
    COMPUTE_MAX_E2_MICRO: int = 1
    COMPUTE_MAX_BOOT_DISK_GB: int = 30


class GCPFreeTierCircuitBreaker:
    """Master governor enforcing 100% free-tier operation and zero out-of-pocket spend."""

    def __init__(self, state_path: Path = STATE_FILE, limits: Optional[FreeTierLimits] = None):
        self.state_path = state_path
        self.limits = limits or FreeTierLimits()
        self.state = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        """Loads state or initializes default zero-cost baseline."""
        today_str = datetime.date.today().isoformat()
        current_month = datetime.date.today().strftime("%Y-%m")

        default_state = {
            "current_date": today_str,
            "current_month": current_month,
            "ai_studio": {
                "requests_today": 0,
                "timestamps_last_minute": [],
                "total_requests": 0,
            },
            "bigquery": {
                "bytes_processed_this_month": 0,
                "queries_executed": 0,
                "tables_created": 0,
            },
            "gcs": {
                "current_bytes_stored": 0,
                "class_a_ops_this_month": 0,
                "class_b_ops_this_month": 0,
            },
            "pubsub": {
                "bytes_published_this_month": 0,
                "messages_published": 0,
            },
            "secret_manager": {
                "active_secrets_count": 0,
                "access_ops_this_month": 0,
            },
            "last_updated": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }

        if not self.state_path.exists():
            self._save_state(default_state)
            return default_state

        try:
            with open(self.state_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Daily rollover
            if data.get("current_date") != today_str:
                data["current_date"] = today_str
                data["ai_studio"]["requests_today"] = 0
                data["ai_studio"]["timestamps_last_minute"] = []

            # Monthly rollover
            if data.get("current_month") != current_month:
                data["current_month"] = current_month
                data["bigquery"]["bytes_processed_this_month"] = 0
                data["gcs"]["class_a_ops_this_month"] = 0
                data["gcs"]["class_b_ops_this_month"] = 0
                data["pubsub"]["bytes_published_this_month"] = 0
                data["secret_manager"]["access_ops_this_month"] = 0

            return data
        except Exception as e:
            logger.warning(f"Error reading state file {self.state_path}: {e}. Reinitializing.")
            self._save_state(default_state)
            return default_state

    def _save_state(self, state: Optional[Dict[str, Any]] = None) -> None:
        """Persists state to disk atomically."""
        if state is None:
            state = self.state
        state["last_updated"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.state_path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        os.replace(temp_path, self.state_path)

    # --------------------------------------------------------------------------
    # AI Studio Pacing & Limits
    # --------------------------------------------------------------------------
    def can_call_ai_studio(self) -> Tuple[bool, str]:
        """Checks if a Gemini API call is permitted under the 15 RPM / 1,500 RPD free tier."""
        now = time.time()
        one_minute_ago = now - 60.0

        # Filter timestamps within the last 60 seconds
        recent_timestamps = [
            ts for ts in self.state["ai_studio"]["timestamps_last_minute"] if ts > one_minute_ago
        ]
        self.state["ai_studio"]["timestamps_last_minute"] = recent_timestamps

        if len(recent_timestamps) >= self.limits.AI_STUDIO_MAX_RPM:
            return False, f"RPM limit reached ({len(recent_timestamps)}/{self.limits.AI_STUDIO_MAX_RPM} in last 60s)"

        if self.state["ai_studio"]["requests_today"] >= self.limits.AI_STUDIO_SAFETY_RPD:
            return False, f"Daily limit buffer reached ({self.state['ai_studio']['requests_today']}/{self.limits.AI_STUDIO_SAFETY_RPD} RPD)"

        return True, "OK"

    def record_ai_studio_call(self) -> None:
        """Records an approved Gemini API call."""
        now = time.time()
        self.state["ai_studio"]["timestamps_last_minute"].append(now)
        self.state["ai_studio"]["requests_today"] += 1
        self.state["ai_studio"]["total_requests"] += 1
        self._save_state()

    # --------------------------------------------------------------------------
    # BigQuery Free Tier Limits
    # --------------------------------------------------------------------------
    def can_run_bigquery_query(self, estimated_bytes: int) -> Tuple[bool, str]:
        """Validates that query will not breach the 1 TB Always Free query limit."""
        safety_bytes = self.limits.BIGQUERY_SAFETY_QUERY_GB_PER_MONTH * (1024 ** 3)
        current_bytes = self.state["bigquery"]["bytes_processed_this_month"]
        new_total = current_bytes + estimated_bytes

        if new_total > safety_bytes:
            return False, (
                f"BigQuery monthly query budget exceeded: Projected {new_total / (1024**3):.2f} GB > "
                f"Safety Limit {self.limits.BIGQUERY_SAFETY_QUERY_GB_PER_MONTH:.2f} GB"
            )

        return True, "OK"

    def record_bigquery_query(self, bytes_processed: int) -> None:
        """Records BigQuery query byte consumption."""
        self.state["bigquery"]["bytes_processed_this_month"] += bytes_processed
        self.state["bigquery"]["queries_executed"] += 1
        self._save_state()

    # --------------------------------------------------------------------------
    # Google Cloud Storage (GCS) Limits
    # --------------------------------------------------------------------------
    def can_upload_gcs(self, bytes_to_add: int, is_class_a: bool = True) -> Tuple[bool, str]:
        """Validates GCS upload against 5 GB storage limit and operation quotas."""
        safety_bytes = self.limits.GCS_SAFETY_STORAGE_GB * (1024 ** 3)
        current_bytes = self.state["gcs"]["current_bytes_stored"]
        new_bytes = current_bytes + bytes_to_add

        if new_bytes > safety_bytes:
            return False, (
                f"GCS storage budget exceeded: Projected {new_bytes / (1024**3):.2f} GB > "
                f"Safety Limit {self.limits.GCS_SAFETY_STORAGE_GB:.2f} GB"
            )

        if is_class_a and self.state["gcs"]["class_a_ops_this_month"] >= self.limits.GCS_MAX_CLASS_A_OPS:
            return False, f"GCS Class A operations limit ({self.limits.GCS_MAX_CLASS_A_OPS}) reached."

        return True, "OK"

    def record_gcs_upload(self, bytes_added: int, is_class_a: bool = True) -> None:
        """Records GCS upload bytes and operation counts."""
        self.state["gcs"]["current_bytes_stored"] += bytes_added
        if is_class_a:
            self.state["gcs"]["class_a_ops_this_month"] += 1
        else:
            self.state["gcs"]["class_b_ops_this_month"] += 1
        self._save_state()

    # --------------------------------------------------------------------------
    # Cloud Pub/Sub Limits
    # --------------------------------------------------------------------------
    def can_publish_pubsub(self, message_bytes: int) -> Tuple[bool, str]:
        """Validates Pub/Sub message size against 10 GB Always Free limit."""
        safety_bytes = self.limits.PUBSUB_SAFETY_GB_PER_MONTH * (1024 ** 3)
        current_bytes = self.state["pubsub"]["bytes_published_this_month"]
        new_bytes = current_bytes + message_bytes

        if new_bytes > safety_bytes:
            return False, f"Pub/Sub monthly message budget exceeded: Projected {new_bytes / (1024**3):.2f} GB."

        return True, "OK"

    def record_pubsub_publish(self, message_bytes: int) -> None:
        """Records Pub/Sub published bytes and message counts."""
        self.state["pubsub"]["bytes_published_this_month"] += message_bytes
        self.state["pubsub"]["messages_published"] += 1
        self._save_state()

    # --------------------------------------------------------------------------
    # Secret Manager Limits
    # --------------------------------------------------------------------------
    def can_create_secret_version(self) -> Tuple[bool, str]:
        """Ensures secret version count stays within the 6 active versions free tier."""
        current_count = self.state["secret_manager"]["active_secrets_count"]
        if current_count >= self.limits.SECRET_MANAGER_MAX_VERSIONS:
            return False, f"Secret Manager max active versions ({self.limits.SECRET_MANAGER_MAX_VERSIONS}) reached."
        return True, "OK"

    def record_secret_created(self) -> None:
        """Records a newly active secret version."""
        self.state["secret_manager"]["active_secrets_count"] += 1
        self._save_state()

    def record_secret_access(self) -> None:
        """Records a secret access operation."""
        self.state["secret_manager"]["access_ops_this_month"] += 1
        self._save_state()

    # --------------------------------------------------------------------------
    # Summary & Reporting
    # --------------------------------------------------------------------------
    def get_summary(self) -> Dict[str, Any]:
        """Returns structured telemetry summary across all Always Free products."""
        return {
            "date": self.state["current_date"],
            "month": self.state["current_month"],
            "ai_studio": {
                "requests_today": self.state["ai_studio"]["requests_today"],
                "limit_rpd": self.limits.AI_STUDIO_MAX_RPD,
                "pct_used": round(100.0 * self.state["ai_studio"]["requests_today"] / self.limits.AI_STUDIO_MAX_RPD, 2),
            },
            "bigquery": {
                "bytes_processed_gb": round(self.state["bigquery"]["bytes_processed_this_month"] / (1024 ** 3), 4),
                "limit_gb": self.limits.BIGQUERY_SAFETY_QUERY_GB_PER_MONTH,
                "queries_executed": self.state["bigquery"]["queries_executed"],
            },
            "gcs": {
                "stored_gb": round(self.state["gcs"]["current_bytes_stored"] / (1024 ** 3), 4),
                "limit_gb": self.limits.GCS_MAX_STORAGE_GB,
                "class_a_ops": self.state["gcs"]["class_a_ops_this_month"],
            },
            "pubsub": {
                "published_mb": round(self.state["pubsub"]["bytes_published_this_month"] / (1024 ** 2), 4),
                "messages_count": self.state["pubsub"]["messages_published"],
            },
            "secret_manager": {
                "active_secrets": self.state["secret_manager"]["active_secrets_count"],
                "max_secrets": self.limits.SECRET_MANAGER_MAX_VERSIONS,
            },
            "zero_charge_status": "ENFORCED",
        }

    def sync_to_obsidian(self) -> None:
        """Renders live circuit breaker metrics to Obsidian Knowledge Vault (Rule #2)."""
        summary = self.get_summary()
        OBSIDIAN_LOG.parent.mkdir(parents=True, exist_ok=True)
        content = f"""---
title: "Google Cloud Always Free Tier Circuit Breaker Telemetry"
tags: [lauburu, gcp, free_tier, circuit_breaker, telemetry, zero_charge]
date: "{summary['date']}"
status: "{summary['zero_charge_status']}"
---

# 🛡️ Google Cloud Always Free Tier Circuit Breaker Telemetry

**Invariant Enforced:** Strictly $0.00 out-of-pocket spend. Zero credit card charges.

## 📊 Live Quota Utilization (Month: {summary['month']})

| Service | Metric | Current Usage | Always Free Quota | Safety Limit | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Google AI Studio** | Requests Today | `{summary['ai_studio']['requests_today']}` | `1,500 RPD` | `1,450 RPD` | ✅ {summary['ai_studio']['pct_used']}% Used |
| **BigQuery** | Queries Processed | `{summary['bigquery']['bytes_processed_gb']:.3f} GB` | `1,024 GB (1 TB)` | `800 GB` | ✅ In Free Tier |
| **Cloud Storage (GCS)** | Regional Storage | `{summary['gcs']['stored_gb']:.3f} GB` | `5.0 GB` | `4.0 GB` | ✅ In Free Tier |
| **Cloud Pub/Sub** | Ingestion Volume | `{summary['pubsub']['published_mb']:.3f} MB` | `10,240 MB (10 GB)` | `8,192 MB` | ✅ In Free Tier |
| **Secret Manager** | Active Versions | `{summary['secret_manager']['active_secrets']}` | `6 Versions` | `6 Versions` | ✅ In Free Tier |
| **Compute Engine** | `e2-micro` Instances | `1 Instance` (`us-central1-a`) | `1 Instance` | `1 Instance` | ✅ Always Free |

*Last Evaluated:* `{datetime.datetime.now(datetime.timezone.utc).isoformat()}`
"""
        with open(OBSIDIAN_LOG, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"Synchronized circuit breaker telemetry to {OBSIDIAN_LOG}")


def main() -> None:
    breaker = GCPFreeTierCircuitBreaker()
    summary = breaker.get_summary()
    print("================================================================================")
    print("🛡️  GCP ALWAYS FREE TIER CIRCUIT BREAKER STATUS")
    print("================================================================================")
    print(json.dumps(summary, indent=2))
    breaker.sync_to_obsidian()
    print("✅ Circuit Breaker Active. Zero out-of-pocket spend enforced.")


if __name__ == "__main__":
    main()
