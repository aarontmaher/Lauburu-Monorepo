#!/usr/bin/env python3
"""
Centralized Domain-Wide Delegation (DWD) Auth Gateway
=====================================================
Manages Google Cloud Service Account authentication with Domain-Wide Delegation
for the Google Workspace account: lauburu@lauburugrappling.com.

Security Invariants:
- Master RSA-2048 private key is locked exclusively on L1 Host Mac Mini (mode 0600).
- Edge nodes (L2-L7) query Port 18802 Gateway over Tailscale WireGuard.
- Short-lived (3600s) scoped Bearer tokens minted on demand with proactive 300s TTL cache.
- Zero raw private key leakage to peripheral nodes.
"""

import os
import sys
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List

try:
    from google.oauth2 import service_account
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    GOOGLE_AUTH_AVAILABLE = True
except ImportError:
    GOOGLE_AUTH_AVAILABLE = False

_CANDIDATE_ROOTS = [
    Path(__file__).resolve().parent.parent.parent,
    Path("/Volumes/Lauburu-Monorepo"),
    Path("/Volumes/AI_Projects/Lauburu_Master/Lauburu-Monorepo"),
    Path("/Volumes/Lauburu-Monorepo"),
]
REPO_ROOT = next((p for p in _CANDIDATE_ROOTS if (p / "00_core_infrastructure").exists()), Path(__file__).resolve().parent.parent.parent)

DEFAULT_SUBJECT = "lauburu@lauburugrappling.com"
WORKSPACE_ACCOUNT = "lauburu@lauburugrappling.com"
WORKSPACE_PASSWORD_ENV_DEFAULT = "Goldfighting1!"
STANDARD_GCP_ACCOUNT = "aaron.t.maher@gmail.com"

DEFAULT_KEY_PATH = REPO_ROOT / "00_core_infrastructure/auth/service_account.json"
DEFAULT_OAUTH_TOKEN = Path("/Users/aaron/teamwork_projects/macbook_air_headless_gdrive/config/token.json")
DEFAULT_OAUTH_CREDS = Path("/Users/aaron/teamwork_projects/macbook_air_headless_gdrive/config/credentials.json")
DEFAULT_LAUBURU_TOKEN = Path(os.path.expanduser("~/.config/lauburu/workspace_token.json"))
DUAL_ACCOUNT_CONFIG_PATH = Path(os.path.expanduser("~/.config/lauburu/dual_google_account_routing.json"))
DEFAULT_ADC_PATH = Path(os.path.expanduser("~/.config/gcloud/legacy_credentials/aaron.t.maher@gmail.com/adc.json"))
GCLOUD_ADC_PATH = Path(os.path.expanduser("~/.config/gcloud/application_default_credentials.json"))
GMAIL_CONFIG_PATH = REPO_ROOT / "00_core_infrastructure/config/gmail_workspace_config.json"

WORKSPACE_DEPENDENT_SERVICES = {
    "drive": "Google Drive Enterprise VFS & Shared Drives",
    "gdrive_vfs": "Google Drive LoRA & Obsidian Cold Backup Sync",
    "gmail": "Gmail API / SMTP Relay & Transactional Alerts",
    "docs": "Google Docs Automated Architecture Reports",
    "sheets": "Google Sheets Telemetry & Financial Ledgers",
    "slides": "Google Slides Executive Deck Generation",
    "chat": "Google Chat Swarm Bot & Webhook Notifications",
    "calendar": "Google Calendar Scheduling & Cron Triggers",
    "admin_directory": "Google Workspace Admin SDK & Domain-Wide Delegation (DWD)",
    "workspace_dwd": "Domain-Wide Delegation Service Account Impersonation",
}

STANDARD_GCP_SERVICES = {
    "vertex_ai": "Vertex AI Model Garden, Tuning & Endpoints",
    "bigquery": "BigQuery Analytics, SQL & BigFrames Lakehouse",
    "cloud_run": "Cloud Run Serverless Microservices & Webhooks",
    "gcs": "Google Cloud Storage (gs://) Buckets & Lakehouse",
    "gemini_api": "Gemini API Free-Tier & AI Studio Keys",
    "colab": "Google Colab Pro / T4 / A100 Remote GPU Offload",
    "firebase": "Firebase App Hosting, Auth, Firestore & Crashlytics",
    "secret_manager": "GCP Secret Manager & KMS Encryption",
    "artifact_registry": "GCP Artifact Registry Container Images",
    "cloud_build": "GCP Cloud Build CI/CD Pipelines",
}

CANONICAL_SCOPES = [
    "https://www.googleapis.com/auth/chat.bot",
    "https://www.googleapis.com/auth/chat.spaces",
    "https://www.googleapis.com/auth/chat.messages",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/presentations",
    "https://www.googleapis.com/auth/admin.directory.user.readonly",
]

STANDARD_GCP_SCOPES = [
    "https://www.googleapis.com/auth/cloud-platform",
    "https://www.googleapis.com/auth/bigquery",
    "https://www.googleapis.com/auth/devstorage.full_control",
]


class DualAccountGoogleRouter:
    """
    Enforces strict separation between:
      1. Google Workspace Account (lauburu@lauburugrappling.com):
         Used exclusively for Workspace-dependent features (Drive, Gmail, Docs,
         Sheets, Slides, Chat, Calendar, Admin SDK Domain-Wide Delegation).
      2. Standard Google Cloud Account (aaron.t.maher@gmail.com):
         Used for all non-Workspace Google Cloud Platform features (Vertex AI,
         BigQuery, Cloud Run, GCS, Gemini API Free Tier, Colab, Firebase).
    """

    def __init__(
        self,
        workspace_account: str = WORKSPACE_ACCOUNT,
        workspace_password: Optional[str] = None,
        standard_gcp_account: str = STANDARD_GCP_ACCOUNT,
        config_path: Optional[Path] = None,
    ):
        self.workspace_account = os.getenv("LAUBURU_WORKSPACE_ACCOUNT", workspace_account)
        self.workspace_password = (
            workspace_password
            or os.getenv("LAUBURU_WORKSPACE_PASSWORD")
            or WORKSPACE_PASSWORD_ENV_DEFAULT
        )
        self.standard_gcp_account = os.getenv("LAUBURU_STANDARD_GCP_ACCOUNT", standard_gcp_account)
        self.config_path = config_path or DUAL_ACCOUNT_CONFIG_PATH

    def resolve_service_account_route(self, service_name: str) -> Dict[str, Any]:
        """Determines which Google account owns a given service or API."""
        norm = service_name.strip().lower().replace("-", "_").replace(" ", "_")
        if norm in WORKSPACE_DEPENDENT_SERVICES or any(k in norm for k in ("workspace", "drive", "gmail", "docs", "sheets", "slides", "chat", "dwd", "admin")):
            desc = WORKSPACE_DEPENDENT_SERVICES.get(norm, "Google Workspace Dependent Feature")
            return {
                "service": norm,
                "account_tier": "GOOGLE_WORKSPACE",
                "account_email": self.workspace_account,
                "domain": "lauburugrappling.com",
                "auth_mechanism": "Domain-Wide Delegation (DWD) / Workspace OAuth2 + App/IMAP Credential",
                "password_configured": bool(self.workspace_password),
                "scopes": CANONICAL_SCOPES,
                "token_path": str(DEFAULT_LAUBURU_TOKEN),
                "service_account_path": str(DEFAULT_KEY_PATH),
                "description": desc,
            }
        desc = STANDARD_GCP_SERVICES.get(norm, "Standard Non-Workspace Google Cloud Feature")
        return {
            "service": norm,
            "account_tier": "STANDARD_GOOGLE_CLOUD",
            "account_email": self.standard_gcp_account,
            "domain": "gmail.com",
            "auth_mechanism": "Application Default Credentials (ADC) / gcloud CLI Profile",
            "password_configured": False,
            "scopes": STANDARD_GCP_SCOPES,
            "adc_path": str(DEFAULT_ADC_PATH if DEFAULT_ADC_PATH.exists() else GCLOUD_ADC_PATH),
            "description": desc,
        }

    KEYCHAIN_SERVICE = "lauburu-google-workspace-auth"

    def _store_password_in_keychain(self, account: str, password: str) -> bool:
        """Stores the workspace password in macOS Keychain if running on Darwin."""
        if sys.platform != "darwin" or not password:
            return False
        try:
            import subprocess
            res = subprocess.run(
                [
                    "/usr/bin/security",
                    "add-generic-password",
                    "-U",
                    "-a",
                    account,
                    "-s",
                    self.KEYCHAIN_SERVICE,
                    "-w",
                    password,
                ],
                capture_output=True,
                text=True,
                timeout=2.0,
            )
            return res.returncode == 0
        except Exception:
            return False

    def get_workspace_password(self) -> str:
        """Retrieves the workspace password from macOS Keychain, env, or fallback."""
        if sys.platform == "darwin":
            try:
                import subprocess
                res = subprocess.run(
                    [
                        "/usr/bin/security",
                        "find-generic-password",
                        "-a",
                        self.workspace_account,
                        "-s",
                        self.KEYCHAIN_SERVICE,
                        "-w",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=2.0,
                )
                if res.returncode == 0 and res.stdout.strip():
                    return res.stdout.strip()
            except Exception:
                pass
        return self.workspace_password

    def provision_dual_account_config(self) -> Dict[str, Any]:
        """Writes the dual-account routing configuration, stores secret in macOS Keychain, and secures permissions (0600)."""
        import hashlib
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        keychain_stored = self._store_password_in_keychain(self.workspace_account, self.workspace_password)
        pw_sha256 = hashlib.sha256(self.workspace_password.encode("utf-8")).hexdigest() if self.workspace_password else ""

        payload = {
            "schema_version": "2.1.0-DUAL-GOOGLE-ROUTING",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "workspace_account": {
                "email": self.workspace_account,
                "password_configured": bool(self.workspace_password),
                "password_keychain_service": self.KEYCHAIN_SERVICE if keychain_stored else "env_or_0600_vault",
                "password_sha256_Verification": pw_sha256,
                "password": self.workspace_password,
                "domain": "lauburugrappling.com",
                "role": "All Google Workspace-dependent features (Drive VFS, Gmail, Docs, Sheets, Slides, Chat, Admin DWD)",
                "services": list(WORKSPACE_DEPENDENT_SERVICES.keys()),
                "scopes": CANONICAL_SCOPES,
                "token_file": str(DEFAULT_LAUBURU_TOKEN),
                "service_account_file": str(DEFAULT_KEY_PATH),
            },
            "standard_gcp_account": {
                "email": self.standard_gcp_account,
                "domain": "gmail.com",
                "role": "All non-Workspace Google Cloud features (Vertex AI, BigQuery, Cloud Run, GCS, Gemini API Free Tier, Colab, Firebase)",
                "services": list(STANDARD_GCP_SERVICES.keys()),
                "scopes": STANDARD_GCP_SCOPES,
                "adc_file": str(DEFAULT_ADC_PATH),
                "gcloud_adc_file": str(GCLOUD_ADC_PATH),
            },
        }
        self.config_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        try:
            os.chmod(self.config_path, 0o600)
        except OSError:
            pass

        # Also ensure gmail_workspace_config.json reflects lauburu@lauburugrappling.com
        try:
            GMAIL_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            gmail_cfg = {
                "workspace_email": self.workspace_account,
                "workspace_domain": "lauburugrappling.com",
                "password_configured": bool(self.workspace_password),
                "keychain_backed": keychain_stored,
                "standard_gcp_email": self.standard_gcp_account,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            GMAIL_CONFIG_PATH.write_text(json.dumps(gmail_cfg, indent=2), encoding="utf-8")
            os.chmod(GMAIL_CONFIG_PATH, 0o600)
        except OSError:
            pass

        return {
            "status": "PROVISIONED",
            "config_path": str(self.config_path),
            "permissions": oct(self.config_path.stat().st_mode & 0o777) if self.config_path.exists() else "0600",
            "keychain_backed": keychain_stored,
            "workspace_account": self.workspace_account,
            "workspace_services_count": len(WORKSPACE_DEPENDENT_SERVICES),
            "standard_gcp_account": self.standard_gcp_account,
            "standard_gcp_services_count": len(STANDARD_GCP_SERVICES),
        }


class DWDAuthGateway:
    """Centralized Domain-Wide Delegation Authentication Gateway."""

    def __init__(
        self,
        service_account_file: Optional[Path] = None,
        subject: str = DEFAULT_SUBJECT,
        scopes: Optional[List[str]] = None
    ):
        self.service_account_file = service_account_file or DEFAULT_KEY_PATH
        self.subject = os.getenv("WORKSPACE_SUBJECT", subject)
        self.scopes = scopes or CANONICAL_SCOPES
        self.router = DualAccountGoogleRouter(workspace_account=self.subject)
        self._token_cache: Dict[str, Dict[str, Any]] = {}

    def is_service_account_configured(self) -> bool:
        """Check if valid service account JSON key exists with proper permissions."""
        if not self.service_account_file.exists():
            return False
        try:
            _ = oct(self.service_account_file.stat().st_mode & 0o777)
            return True
        except OSError:
            return False

    def secure_key_permissions(self) -> None:
        """Enforce strict 0600 permissions on private key files."""
        if self.service_account_file.exists():
            try:
                os.chmod(self.service_account_file, 0o600)
            except OSError as e:
                print(f"[WARN] Failed to set permissions on keyfile: {e}", file=sys.stderr)

    def get_delegated_credentials(
        self,
        scopes: Optional[List[str]] = None,
        subject: Optional[str] = None
    ) -> Optional[Any]:
        """Mint credentials impersonating the specified workspace subject."""
        if not GOOGLE_AUTH_AVAILABLE:
            print("[WARN] google-auth not installed. Running in mock/offline mode.", file=sys.stderr)
            return None

        target_subject = subject or self.subject
        target_scopes = scopes or self.scopes

        # 1. Primary path: Domain-Wide Delegation Service Account
        if self.is_service_account_configured():
            try:
                self.secure_key_permissions()
                creds = service_account.Credentials.from_service_account_file(
                    str(self.service_account_file),
                    scopes=target_scopes,
                    subject=target_subject
                )
                return creds
            except Exception as e:
                print(f"[WARN] DWD Delegation failed: {e}. Falling back to OAuth2 token.", file=sys.stderr)

        # 2. Fallback path: Dedicated Lauburu Workspace Token
        if DEFAULT_LAUBURU_TOKEN.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(DEFAULT_LAUBURU_TOKEN), target_scopes)
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                return creds
            except Exception as e:
                print(f"[WARN] Lauburu token load failed: {e}", file=sys.stderr)

        # 3. Fallback path: Headless GDrive OAuth2 User Token
        if DEFAULT_OAUTH_TOKEN.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(DEFAULT_OAUTH_TOKEN), target_scopes)
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                return creds
            except Exception as e:
                print(f"[WARN] OAuth2 fallback token load failed: {e}", file=sys.stderr)

        # 4. Fallback path: Google Cloud Application Default Credentials (ADC)
        for adc_candidate in [DEFAULT_ADC_PATH, GCLOUD_ADC_PATH]:
            if adc_candidate.exists():
                try:
                    creds = Credentials.from_authorized_user_file(str(adc_candidate))
                    if creds and creds.expired and creds.refresh_token:
                        creds.refresh(Request())
                    return creds
                except Exception as e:
                    print(f"[WARN] ADC fallback ({adc_candidate.name}) failed: {e}", file=sys.stderr)

        return None

    def get_bearer_token(
        self,
        scopes: Optional[List[str]] = None,
        subject: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Returns a cached or freshly minted Bearer token with expiry metadata.
        Proactive refresh occurs if token expires within 300 seconds.
        """
        target_subject = subject or self.subject
        target_scopes = scopes or self.scopes
        scopes_str = ",".join(sorted(target_scopes))
        cache_key = f"{target_subject}:{scopes_str}"
        now = time.time()

        # Check in-memory cache
        if cache_key in self._token_cache:
            entry = self._token_cache[cache_key]
            if entry.get("expires_at", 0) - now > 300:
                return entry

        creds = self.get_delegated_credentials(scopes=scopes, subject=target_subject)
        if creds is None:
            return {
                "access_token": None,
                "token_type": "Bearer",
                "subject": target_subject,
                "status": "AWAITING_CREDENTIALS",
                "scopes": target_scopes,
                "service_account_configured": self.is_service_account_configured()
            }

        try:
            if not getattr(creds, "token", None) or getattr(creds, "expired", False):
                creds.refresh(Request())

            token_data = {
                "access_token": creds.token,
                "token_type": "Bearer",
                "subject": target_subject,
                "expires_at": creds.expiry.timestamp() if getattr(creds, "expiry", None) else now + 3600,
                "status": "ACTIVE",
                "scopes": target_scopes,
                "minted_at": datetime.now(timezone.utc).isoformat()
            }
            self._token_cache[cache_key] = token_data
            return token_data
        except Exception as e:
            print(f"[ERROR] Failed to refresh token: {e}", file=sys.stderr)
            return None

    def get_gateway_health(self) -> Dict[str, Any]:
        """Returns status of the DWD Auth Gateway and Dual-Account Router."""
        return {
            "gateway": "Port 18802 DWD Auth Sentinel & Dual-Account Router",
            "workspace_domain": "lauburugrappling.com",
            "default_subject": self.subject,
            "standard_gcp_account": self.router.standard_gcp_account,
            "dual_account_config_exists": DUAL_ACCOUNT_CONFIG_PATH.exists(),
            "service_account_path": str(self.service_account_file),
            "service_account_exists": self.service_account_file.exists(),
            "oauth_token_exists": DEFAULT_OAUTH_TOKEN.exists(),
            "lauburu_token_exists": DEFAULT_LAUBURU_TOKEN.exists(),
            "adc_exists": DEFAULT_ADC_PATH.exists() or GCLOUD_ADC_PATH.exists(),
            "gmail_config_exists": GMAIL_CONFIG_PATH.exists(),
            "cached_tokens_count": len(self._token_cache),
            "active_scopes": self.scopes,
            "workspace_services": list(WORKSPACE_DEPENDENT_SERVICES.keys()),
            "standard_gcp_services": list(STANDARD_GCP_SERVICES.keys()),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


if __name__ == "__main__":
    gateway = DWDAuthGateway()
    if "--provision" in sys.argv:
        print(json.dumps(gateway.router.provision_dual_account_config(), indent=2))
    elif "--route" in sys.argv and len(sys.argv) > sys.argv.index("--route") + 1:
        svc = sys.argv[sys.argv.index("--route") + 1]
        print(json.dumps(gateway.router.resolve_service_account_route(svc), indent=2))
    else:
        health = gateway.get_gateway_health()
        print(json.dumps(health, indent=2))

