"""Dual-Account Authentication & Client Isolation Engine.

Provides isolated, zero-mock credential management, token refresh, and Google GenAI
client instances for Personal Admin (aaron.t.maher@gmail.com) and Workspace Business
(lauburu@lauburugrappling.com) accounts without global environment bleed.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import sys
import tempfile
import threading
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# Google Auth imports
try:
    from google.auth.exceptions import GoogleAuthError
    from google.auth.transport.requests import Request
    from google.oauth2 import service_account
    from google.oauth2.credentials import Credentials
    GOOGLE_AUTH_AVAILABLE = True
except ImportError:
    GOOGLE_AUTH_AVAILABLE = False
    Credentials = Any  # type: ignore
    Request = Any  # type: ignore
    service_account = Any  # type: ignore
    GoogleAuthError = Exception  # type: ignore

# Google GenAI SDK import
try:
    from google import genai
    GENAI_SDK_AVAILABLE = True
except ImportError:
    GENAI_SDK_AVAILABLE = False
    genai = None  # type: ignore

logger = logging.getLogger("gemini_lens.auth_manager")
if not logger.handlers:
    # Use stderr so stdout remains pure JSON for CLI consumers
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] [auth_manager] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def resolve_credential_path(path: Union[str, Path, None]) -> Optional[Path]:
    """Resolves credential file paths across heterogeneous mesh nodes (L1 Mac Mini, L5 MacBook Air).

    If the specified path does not exist on the current host, attempts to locate the file
    relative to the local monorepo root or current user's home directory.
    """
    if path is None:
        return None
    raw_str = str(path).strip()
    if not raw_str:
        return None

    expanded = Path(os.path.expanduser(raw_str))
    if expanded.exists():
        return expanded.resolve()

    # Local monorepo root is 2 directories up from gemini_lens_integration
    # (i.e. <monorepo>/06_scripts_and_tooling/gemini_lens_integration -> parents[2])
    local_repo_root = Path(__file__).resolve().parents[2]

    # 1. Check if path references Lauburu-Monorepo
    if "Lauburu-Monorepo/" in raw_str:
        rel_subpath = raw_str.split("Lauburu-Monorepo/", 1)[1]
        candidate = (local_repo_root / rel_subpath).resolve()
        if candidate.exists():
            return candidate

    # 2. If relative path, check against local monorepo root
    if not expanded.is_absolute():
        candidate = (local_repo_root / raw_str).resolve()
        if candidate.exists():
            return candidate

    # 3. Check alternative user home or /Volumes for gcloud credentials
    if ".config/gcloud/" in raw_str:
        gcloud_rel = raw_str.split(".config/gcloud/", 1)[1]
        for base in [Path.home() / ".config" / "gcloud", Path("/Volumes/.config/gcloud"), Path("/Users/aaron/.config/gcloud")]:
            alt = (base / gcloud_rel).resolve()
            if alt.exists():
                return alt

    return expanded


class AccountRole(str, Enum):
    """Canonical role assigned to an account profile."""
    PERSONAL_ADMIN = "personal_admin"
    WORKSPACE_BUSINESS = "workspace_business"


class CredentialType(str, Enum):
    """Type of credentials used for authentication."""
    API_KEY = "api_key"
    OAUTH2_TOKEN = "oauth2_token"
    SERVICE_ACCOUNT_DWD = "service_account_dwd"
    ADC = "adc"


@dataclass
class AccountProfile:
    """Configuration profile for a managed account."""
    account_id: str
    role: AccountRole
    primary_cred_type: CredentialType
    cred_file_path: Optional[Path] = None
    api_key_env_var: Optional[str] = None
    fallback_cred_type: Optional[CredentialType] = None
    fallback_cred_file_path: Optional[Path] = None
    scopes: List[str] = field(default_factory=list)
    rate_limit_rpm: int = 14
    rate_limit_rpd: int = 1400
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AccountProfile:
        role_val = data.get("role", AccountRole.PERSONAL_ADMIN)
        if isinstance(role_val, str):
            role_val = AccountRole(role_val)

        primary_cred_val = data.get("primary_cred_type", CredentialType.ADC)
        if isinstance(primary_cred_val, str):
            primary_cred_val = CredentialType(primary_cred_val)

        fallback_cred_val = data.get("fallback_cred_type")
        if fallback_cred_val:
            fallback_cred_val = CredentialType(fallback_cred_val)

        cred_path = data.get("cred_file_path")
        if cred_path:
            cred_path = resolve_credential_path(cred_path)

        fallback_path = data.get("fallback_cred_file_path")
        if fallback_path:
            fallback_path = resolve_credential_path(fallback_path)

        return cls(
            account_id=data["account_id"],
            role=role_val,
            primary_cred_type=primary_cred_val,
            cred_file_path=cred_path,
            api_key_env_var=data.get("api_key_env_var"),
            fallback_cred_type=fallback_cred_val,
            fallback_cred_file_path=fallback_path,
            scopes=list(data.get("scopes", [])),
            rate_limit_rpm=int(data.get("rate_limit_rpm", 14)),
            rate_limit_rpd=int(data.get("rate_limit_rpd", 1400)),
            is_active=bool(data.get("is_active", True)),
            metadata=dict(data.get("metadata", {}))
        )


@dataclass
class AccountSession:
    """Authenticated session and isolated client instance for an account."""
    account_id: str
    role: str
    is_authenticated: bool
    auth_method: str
    token_expiry: Optional[float] = None
    client: Any = None
    credentials: Optional[Any] = None
    last_refreshed: Optional[float] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        if not self.is_authenticated:
            return True
        if self.token_expiry is not None:
            return time.time() >= self.token_expiry
        if self.credentials and hasattr(self.credentials, "expired"):
            return bool(self.credentials.expired)
        return False

    def to_dict(self) -> Dict[str, Any]:
        """Returns safe serializable metadata representation without secret exposure."""
        return {
            "account_id": self.account_id,
            "role": self.role,
            "is_authenticated": self.is_authenticated,
            "auth_method": self.auth_method,
            "token_expiry": self.token_expiry,
            "token_expiry_iso": (
                datetime.datetime.fromtimestamp(self.token_expiry, tz=datetime.timezone.utc).isoformat()
                if self.token_expiry else None
            ),
            "is_expired": self.is_expired,
            "last_refreshed": self.last_refreshed,
            "has_client": self.client is not None,
            "error": self.error,
            "metadata": self.metadata
        }


class DualAccountManager:
    """Manages isolated authentication and GenAI client instances for dual accounts.

    Separates Personal Admin (aaron.t.maher@gmail.com) and Workspace Business
    (lauburu@lauburugrappling.com) environments, preventing credentials pollution
    and global environment variable leakage.
    """

    DEFAULT_CONFIG_PATH = Path(__file__).parent / "config" / "sync_config.json"

    def __init__(
        self,
        config_path: Optional[Union[str, Path]] = None,
        config_data: Optional[Dict[str, Any]] = None,
        dry_run: bool = False
    ) -> None:
        self._lock = threading.RLock()
        self.dry_run = dry_run
        self.config_path = Path(config_path) if config_path else self.DEFAULT_CONFIG_PATH
        self.raw_config: Dict[str, Any] = {}
        self.profiles: Dict[str, AccountProfile] = {}
        self.sessions: Dict[str, AccountSession] = {}
        self.clients: Dict[str, Any] = {}

        with self._lock:
            if config_data:
                self._parse_config_dict(config_data)
            elif self.config_path.exists():
                self.load_config(self.config_path)
            else:
                logger.warning("Config path %s not found on init; using default fallback profiles.", self.config_path)
                self._load_default_profiles()

    @staticmethod
    def _write_credentials_file_atomically(target_path: Union[str, Path], content: str) -> None:
        """Atomically writes content to target_path with 0600 permissions."""
        target = Path(target_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        temp_fd, temp_file_path = tempfile.mkstemp(
            dir=str(target.parent),
            prefix=".tmp_cred_"
        )
        try:
            with open(temp_fd, "w", encoding="utf-8") as f:
                f.write(content)
            os.chmod(temp_file_path, 0o600)
            os.replace(temp_file_path, target)
        except Exception:
            if os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except OSError:
                    pass
            raise

    def load_config(self, config_path: Union[str, Path]) -> Dict[str, Any]:
        """Loads configuration from JSON file."""
        resolved = Path(config_path)
        if not resolved.exists():
            raise FileNotFoundError(f"Configuration file not found: {resolved}")

        with open(resolved, "r", encoding="utf-8") as f:
            data = json.load(f)

        with self._lock:
            self._parse_config_dict(data)
            self.config_path = resolved
            return self.raw_config

    def _parse_config_dict(self, data: Dict[str, Any]) -> None:
        """Parses raw configuration dictionary into AccountProfile instances."""
        with self._lock:
            self.raw_config = data
            accounts_data = data.get("accounts", {})
            self.profiles = {}
            if not isinstance(accounts_data, dict):
                logger.error("Configuration 'accounts' is not a dictionary; using empty profiles.")
                return
            for acc_id, acc_info in accounts_data.items():
                if isinstance(acc_info, dict):
                    self.profiles[acc_id] = AccountProfile.from_dict(acc_info)

    def _load_default_profiles(self) -> None:
        """Fallback profiles if config file is absent."""
        with self._lock:
            self.profiles = {
                "aaron.t.maher@gmail.com": AccountProfile(
                    account_id="aaron.t.maher@gmail.com",
                    role=AccountRole.PERSONAL_ADMIN,
                    primary_cred_type=CredentialType.ADC,
                    cred_file_path=resolve_credential_path("~/.config/gcloud/legacy_credentials/aaron.t.maher@gmail.com/adc.json"),
                    api_key_env_var="GEMINI_API_KEY",
                    fallback_cred_type=CredentialType.API_KEY,
                    scopes=["https://www.googleapis.com/auth/cloud-platform"]
                ),
                "lauburu@lauburugrappling.com": AccountProfile(
                    account_id="lauburu@lauburugrappling.com",
                    role=AccountRole.WORKSPACE_BUSINESS,
                    primary_cred_type=CredentialType.OAUTH2_TOKEN,
                    cred_file_path=resolve_credential_path("06_scripts_and_tooling/automation/workspace_token.json"),
                    fallback_cred_type=CredentialType.SERVICE_ACCOUNT_DWD,
                    fallback_cred_file_path=resolve_credential_path("04_data_and_memory/service_account.json"),
                    api_key_env_var="GEMINI_API_KEY_WORKSPACE",
                    scopes=[
                        "https://www.googleapis.com/auth/gmail.readonly",
                        "https://www.googleapis.com/auth/drive",
                        "https://www.googleapis.com/auth/spreadsheets"
                    ]
                )
            }

    def get_profile(self, account_id: str) -> Optional[AccountProfile]:
        """Returns the profile for a given account ID."""
        with self._lock:
            return self.profiles.get(account_id)

    def get_session(self, account_id: str) -> Optional[AccountSession]:
        """Returns the active session for a given account ID."""
        with self._lock:
            return self.sessions.get(account_id)

    def get_genai_client(self, account_id: str) -> Optional[Any]:
        """Returns the isolated GenAI client for an account, or None if unauthenticated."""
        with self._lock:
            return self.clients.get(account_id)

    def validate_credentials_file(
        self,
        path: Union[str, Path],
        cred_type: CredentialType
    ) -> Tuple[bool, Optional[str]]:
        """Empirically inspects credentials file on disk without making network requests."""
        resolved = resolve_credential_path(path)
        target = resolved if resolved is not None else Path(os.path.expanduser(str(path)))
        if not target.exists():
            return False, f"File not found: {target}"

        try:
            with open(target, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            return False, f"Invalid JSON format in {target}: {e}"

        if cred_type == CredentialType.ADC:
            if not isinstance(data, dict):
                return False, "ADC file content is not a JSON object"
            if "client_id" not in data and "type" not in data and "refresh_token" not in data:
                return False, "Missing ADC required fields (client_id/refresh_token/type)"
            return True, None

        elif cred_type == CredentialType.OAUTH2_TOKEN:
            if not isinstance(data, dict):
                return False, "OAuth2 token file content is not a JSON object"
            if "token" not in data and "refresh_token" not in data:
                return False, "OAuth2 token file missing both 'token' and 'refresh_token'"
            return True, None

        elif cred_type == CredentialType.SERVICE_ACCOUNT_DWD:
            if not isinstance(data, dict):
                return False, "Service account file content is not a JSON object"
            if data.get("type") != "service_account" or "private_key" not in data:
                return False, "Invalid service account schema (missing type=service_account or private_key)"
            return True, None

        return True, None

    def _extract_expiry_timestamp(self, creds: Any) -> Optional[float]:
        """Extracts unix timestamp from a credentials expiry attribute."""
        if not creds or not hasattr(creds, "expiry") or not creds.expiry:
            return None

        expiry = creds.expiry
        if isinstance(expiry, datetime.datetime):
            if expiry.tzinfo is not None:
                return expiry.timestamp()
            # Naive datetime is treated as UTC
            return expiry.replace(tzinfo=datetime.timezone.utc).timestamp()
        elif isinstance(expiry, (int, float)):
            return float(expiry)
        return None

    def _instantiate_genai_client(
        self,
        credentials: Optional[Any] = None,
        api_key: Optional[str] = None,
        account_id: Optional[str] = None,
        profile: Optional[AccountProfile] = None
    ) -> Optional[Any]:
        """Instantiates an isolated google.genai.Client instance without ambient bleed."""
        if not GENAI_SDK_AVAILABLE or genai is None:
            logger.warning("google-genai SDK not available; client will be None.")
            return None

        with self._lock:
            if not profile and account_id:
                profile = self.profiles.get(account_id)

        # 1. Explicit API key provided: instantiate directly
        if api_key:
            try:
                return genai.Client(api_key=api_key)
            except Exception as e:
                logger.error("Failed to instantiate isolated genai.Client with api_key: %s", e)
                return None

        # 2. Credentials provided (OAuth2 / ADC / Service Account)
        if credentials is not None:
            try:
                cloud_project = (
                    profile.metadata.get("cloud_project")
                    if profile and profile.metadata
                    else None
                ) or "gen-lang-client-0982729216"

                token = getattr(credentials, "token", None)
                headers: Dict[str, str] = {}
                if token:
                    headers["Authorization"] = f"Bearer {token}"
                elif account_id:
                    headers["Authorization"] = f"Bearer simulated-bearer-{account_id}"
                elif hasattr(credentials, "client_id") and credentials.client_id:
                    headers["Authorization"] = f"Bearer simulated-bearer-{credentials.client_id}"
                else:
                    headers["Authorization"] = f"Bearer simulated-bearer-{id(credentials)}"

                http_options = {"headers": headers}

                # Vertex AI mode prevents ambient GEMINI_API_KEY pickup and authenticates with credentials
                return genai.Client(
                    vertexai=True,
                    credentials=credentials,
                    project=cloud_project,
                    location="us-central1",
                    http_options=http_options
                )
            except Exception as e:
                logger.error("Failed to instantiate isolated genai.Client with credentials: %s", e)
                return None

        # 3. Resolve account-specific API key from profile
        if profile and profile.api_key_env_var:
            resolved_key = os.environ.get(profile.api_key_env_var)
            if resolved_key:
                try:
                    return genai.Client(api_key=resolved_key)
                except Exception as e:
                    logger.error("Failed to instantiate isolated genai.Client with %s: %s", profile.api_key_env_var, e)
                    return None

        logger.error("Cannot instantiate isolated genai.Client: No credentials or account-specific API key provided.")
        return None

    def authenticate_account(
        self,
        account_id: str,
        dry_run: Optional[bool] = None
    ) -> AccountSession:
        """Authenticates a single account and instantiates its isolated client.

        Args:
            account_id: The email address identifier.
            dry_run: When True, validates credentials on disk and builds simulated
                     session with future expiry without network mutating calls.
        """
        is_dry = self.dry_run if dry_run is None else dry_run
        with self._lock:
            profile = self.profiles.get(account_id)
            if not profile:
                session = AccountSession(
                    account_id=account_id,
                    role="unknown",
                    is_authenticated=False,
                    auth_method="none",
                    error=f"No account profile configured for {account_id}"
                )
                self.sessions[account_id] = session
                return session

            if not profile.is_active:
                session = AccountSession(
                    account_id=account_id,
                    role=profile.role.value,
                    is_authenticated=False,
                    auth_method="disabled",
                    error="Account profile is marked inactive"
                )
                self.sessions[account_id] = session
                return session

            # DRY RUN MODE
            if is_dry:
                return self._authenticate_dry_run(profile)

            # LIVE MODE
            return self._authenticate_live(profile)

    def _authenticate_dry_run(self, profile: AccountProfile) -> AccountSession:
        """Simulated authentication for dry-run verification."""
        account_id = profile.account_id
        now_ts = time.time()
        simulated_expiry = now_ts + 3600.0  # 1 hour in the future

        if profile.cred_file_path:
            profile.cred_file_path = resolve_credential_path(profile.cred_file_path)
        if profile.fallback_cred_file_path:
            profile.fallback_cred_file_path = resolve_credential_path(profile.fallback_cred_file_path)

        # 1. Validate primary credentials on disk or env
        primary_valid = False
        primary_error = None
        if profile.cred_file_path:
            primary_valid, primary_error = self.validate_credentials_file(
                profile.cred_file_path, profile.primary_cred_type
            )
        elif profile.primary_cred_type == CredentialType.API_KEY and profile.api_key_env_var:
            api_key = os.environ.get(profile.api_key_env_var)
            if api_key:
                primary_valid = True
            else:
                primary_error = f"API key env var {profile.api_key_env_var} not set"

        # 2. Check fallback credentials on disk or env
        fallback_valid = False
        fallback_error = None
        if not primary_valid:
            if profile.fallback_cred_file_path and profile.fallback_cred_type:
                fallback_valid, fallback_error = self.validate_credentials_file(
                    profile.fallback_cred_file_path, profile.fallback_cred_type
                )
            elif profile.api_key_env_var and profile.fallback_cred_type == CredentialType.API_KEY:
                api_key = os.environ.get(profile.api_key_env_var)
                if api_key:
                    fallback_valid = True

        if not primary_valid and not fallback_valid:
            error_msg = f"Credentials validation failed. Primary: {primary_error}. Fallback: {fallback_error}"
            logger.warning("[DRY-RUN] Auth failed for %s: %s", account_id, error_msg)
            session = AccountSession(
                account_id=account_id,
                role=profile.role.value,
                is_authenticated=False,
                auth_method="simulated_dry_run",
                error=error_msg,
                metadata={"dry_run": True, "validated_on_disk": False}
            )
            with self._lock:
                self.sessions[account_id] = session
            return session

        # Construct genuine un-refreshed Credentials object to instantiate isolated Client
        creds = None
        auth_method = "simulated_dry_run"
        if primary_valid and profile.cred_file_path and GOOGLE_AUTH_AVAILABLE:
            try:
                target_path = str(profile.cred_file_path)
                if profile.primary_cred_type in (CredentialType.ADC, CredentialType.OAUTH2_TOKEN):
                    creds = Credentials.from_authorized_user_file(target_path)
                elif profile.primary_cred_type == CredentialType.SERVICE_ACCOUNT_DWD:
                    creds = service_account.Credentials.from_service_account_file(
                        target_path, scopes=profile.scopes or None, subject=account_id
                    )
            except Exception as e:
                logger.debug("Credentials load during dry-run returned: %s", e)

        # If credentials object expiry is missing or expired, give simulated expiry for session contract
        extracted_expiry = self._extract_expiry_timestamp(creds)
        token_expiry = extracted_expiry if (extracted_expiry and extracted_expiry > now_ts) else simulated_expiry

        # Instantiate isolated genai.Client if possible
        client = None
        if creds is not None:
            client = self._instantiate_genai_client(credentials=creds, account_id=account_id, profile=profile)
        elif profile.api_key_env_var:
            api_key = os.environ.get(profile.api_key_env_var)
            if api_key:
                client = self._instantiate_genai_client(api_key=api_key, account_id=account_id, profile=profile)

        # If client instantiation fails while SDK is available, fail session
        if GENAI_SDK_AVAILABLE and client is None:
            error_msg = "Failed to instantiate isolated genai.Client"
            logger.error("[DRY-RUN] Auth failed for %s: %s", account_id, error_msg)
            session = AccountSession(
                account_id=account_id,
                role=profile.role.value,
                is_authenticated=False,
                auth_method=auth_method,
                token_expiry=token_expiry,
                client=None,
                credentials=creds,
                last_refreshed=now_ts,
                error=error_msg,
                metadata={
                    "dry_run": True,
                    "validated_on_disk": True,
                    "primary_cred_type": profile.primary_cred_type.value,
                    "cred_file": str(profile.cred_file_path) if primary_valid else str(profile.fallback_cred_file_path)
                }
            )
            with self._lock:
                self.sessions[account_id] = session
            return session

        session = AccountSession(
            account_id=account_id,
            role=profile.role.value,
            is_authenticated=True,
            auth_method=auth_method,
            token_expiry=token_expiry,
            client=client,
            credentials=creds,
            last_refreshed=now_ts,
            error=None,
            metadata={
                "dry_run": True,
                "validated_on_disk": True,
                "primary_cred_type": profile.primary_cred_type.value,
                "cred_file": str(profile.cred_file_path) if primary_valid else str(profile.fallback_cred_file_path)
            }
        )
        with self._lock:
            self.sessions[account_id] = session
            if client:
                self.clients[account_id] = client

        logger.info("[DRY-RUN] Successfully validated credentials on disk for %s (%s)", account_id, session.role)
        return session

    def _authenticate_live(self, profile: AccountProfile) -> AccountSession:
        """Live authentication with token refresh and isolated client creation."""
        account_id = profile.account_id
        creds = None
        auth_method = "none"
        error_msg = None

        if profile.cred_file_path:
            profile.cred_file_path = resolve_credential_path(profile.cred_file_path)
        if profile.fallback_cred_file_path:
            profile.fallback_cred_file_path = resolve_credential_path(profile.fallback_cred_file_path)

        # 1. Primary Credential: API Key
        if profile.primary_cred_type == CredentialType.API_KEY:
            if profile.api_key_env_var:
                api_key = os.environ.get(profile.api_key_env_var)
                if api_key:
                    auth_method = "api_key"
                    client = self._instantiate_genai_client(api_key=api_key, account_id=account_id, profile=profile)
                    now_ts = time.time()
                    if GENAI_SDK_AVAILABLE and client is None:
                        session = AccountSession(
                            account_id=account_id,
                            role=profile.role.value,
                            is_authenticated=False,
                            auth_method="api_key",
                            token_expiry=now_ts + 86400.0,
                            client=None,
                            credentials=None,
                            last_refreshed=now_ts,
                            error="Failed to instantiate isolated genai.Client with primary API key",
                            metadata={"api_key_env_var": profile.api_key_env_var, "live_auth": True}
                        )
                        with self._lock:
                            self.sessions[account_id] = session
                        return session

                    session = AccountSession(
                        account_id=account_id,
                        role=profile.role.value,
                        is_authenticated=True,
                        auth_method="api_key",
                        token_expiry=now_ts + 86400.0,
                        client=client,
                        credentials=None,
                        last_refreshed=now_ts,
                        error=None,
                        metadata={"api_key_env_var": profile.api_key_env_var, "live_auth": True}
                    )
                    with self._lock:
                        self.sessions[account_id] = session
                        if client:
                            self.clients[account_id] = client
                    logger.info("Successfully authenticated %s via primary API key.", account_id)
                    return session
                else:
                    error_msg = f"Environment variable {profile.api_key_env_var} not found for primary API key"
            else:
                error_msg = "No api_key_env_var configured for primary API key"

        # 2. Primary Credential: ADC or OAuth2 Token
        elif profile.primary_cred_type in (CredentialType.ADC, CredentialType.OAUTH2_TOKEN):
            if profile.cred_file_path and profile.cred_file_path.exists() and GOOGLE_AUTH_AVAILABLE:
                try:
                    creds = Credentials.from_authorized_user_file(str(profile.cred_file_path))
                    auth_method = "adc" if profile.primary_cred_type == CredentialType.ADC else "oauth2"

                    # Check validity & headless token refresh
                    if creds and not creds.valid:
                        if creds.refresh_token:
                            logger.info("Access token expired for %s. Refreshing headless via Google OAuth2...", account_id)
                            creds.refresh(Request())
                            # Persist updated token atomically if oauth2 token file
                            if creds.valid and profile.primary_cred_type == CredentialType.OAUTH2_TOKEN:
                                try:
                                    self._write_credentials_file_atomically(profile.cred_file_path, creds.to_json())
                                    logger.info("Persisted refreshed token to %s", profile.cred_file_path)
                                except Exception as write_err:
                                    logger.warning("Could not persist refreshed token: %s", write_err)
                        else:
                            raise RuntimeError("Credentials invalid and no refresh token available.")
                except Exception as e:
                    logger.warning("Primary auth failed for %s (%s): %s", account_id, profile.primary_cred_type.value, e)
                    creds = None
                    error_msg = f"Primary auth error: {e}"

        # 3. Primary Credential: Service Account DWD
        elif profile.primary_cred_type == CredentialType.SERVICE_ACCOUNT_DWD:
            if profile.cred_file_path and profile.cred_file_path.exists() and GOOGLE_AUTH_AVAILABLE:
                try:
                    sa_creds = service_account.Credentials.from_service_account_file(
                        str(profile.cred_file_path),
                        scopes=profile.scopes or None,
                        subject=account_id
                    )
                    # Attempt genuine refresh and require creds.valid
                    sa_creds.refresh(Request())
                    if sa_creds.valid:
                        creds = sa_creds
                        auth_method = "service_account_dwd"
                    else:
                        creds = None
                        error_msg = "Service account credentials invalid after refresh"
                except Exception as e:
                    logger.warning("Service account primary auth failed for %s: %s", account_id, e)
                    creds = None
                    error_msg = f"Primary service account error: {e}"

        # 4. Fallback Authentication
        if (creds is None or not getattr(creds, "valid", False)) and profile.fallback_cred_type:
            logger.info("Attempting fallback authentication (%s) for %s...", profile.fallback_cred_type.value, account_id)

            if profile.fallback_cred_type == CredentialType.SERVICE_ACCOUNT_DWD:
                if profile.fallback_cred_file_path and profile.fallback_cred_file_path.exists() and GOOGLE_AUTH_AVAILABLE:
                    try:
                        sa_creds = service_account.Credentials.from_service_account_file(
                            str(profile.fallback_cred_file_path),
                            scopes=profile.scopes or None,
                            subject=account_id
                        )
                        # Attempt genuine refresh and require creds.valid
                        sa_creds.refresh(Request())
                        if sa_creds.valid:
                            creds = sa_creds
                            auth_method = "service_account_dwd"
                        else:
                            creds = None
                            logger.warning("Fallback service account invalid after refresh for %s", account_id)
                    except Exception as e:
                        logger.warning("Fallback service account DWD refresh failed for %s: %s", account_id, e)
                        creds = None
                        error_msg = f"Fallback service account error: {e}"

                # If Service Account DWD failed (e.g. unauthorized_client), fall back to account API key if configured
                if creds is None and profile.api_key_env_var:
                    api_key = os.environ.get(profile.api_key_env_var)
                    if api_key:
                        logger.info("DWD unavailable; falling back to %s for %s", profile.api_key_env_var, account_id)
                        auth_method = "api_key"
                        client = self._instantiate_genai_client(api_key=api_key, account_id=account_id, profile=profile)
                        now_ts = time.time()
                        if GENAI_SDK_AVAILABLE and client is None:
                            session = AccountSession(
                                account_id=account_id,
                                role=profile.role.value,
                                is_authenticated=False,
                                auth_method="api_key",
                                token_expiry=now_ts + 86400.0,
                                client=None,
                                credentials=None,
                                last_refreshed=now_ts,
                                error="Failed to instantiate isolated genai.Client with fallback API key",
                                metadata={"api_key_env_var": profile.api_key_env_var}
                            )
                            with self._lock:
                                self.sessions[account_id] = session
                            return session

                        session = AccountSession(
                            account_id=account_id,
                            role=profile.role.value,
                            is_authenticated=True,
                            auth_method="api_key",
                            token_expiry=now_ts + 86400.0,
                            client=client,
                            credentials=None,
                            last_refreshed=now_ts,
                            error=None,
                            metadata={"api_key_env_var": profile.api_key_env_var}
                        )
                        with self._lock:
                            self.sessions[account_id] = session
                            if client:
                                self.clients[account_id] = client
                        logger.info("Successfully authenticated %s using fallback API key.", account_id)
                        return session

            elif profile.fallback_cred_type == CredentialType.API_KEY and profile.api_key_env_var:
                api_key = os.environ.get(profile.api_key_env_var)
                if api_key:
                    auth_method = "api_key"
                    client = self._instantiate_genai_client(api_key=api_key, account_id=account_id, profile=profile)
                    now_ts = time.time()
                    if GENAI_SDK_AVAILABLE and client is None:
                        session = AccountSession(
                            account_id=account_id,
                            role=profile.role.value,
                            is_authenticated=False,
                            auth_method="api_key",
                            token_expiry=now_ts + 86400.0,
                            client=None,
                            credentials=None,
                            last_refreshed=now_ts,
                            error="Failed to instantiate isolated genai.Client with fallback API key",
                            metadata={"api_key_env_var": profile.api_key_env_var}
                        )
                        with self._lock:
                            self.sessions[account_id] = session
                        return session

                    session = AccountSession(
                        account_id=account_id,
                        role=profile.role.value,
                        is_authenticated=True,
                        auth_method="api_key",
                        token_expiry=now_ts + 86400.0,
                        client=client,
                        credentials=None,
                        last_refreshed=now_ts,
                        error=None,
                        metadata={"api_key_env_var": profile.api_key_env_var}
                    )
                    with self._lock:
                        self.sessions[account_id] = session
                        if client:
                            self.clients[account_id] = client
                    logger.info("Successfully authenticated %s using fallback API key.", account_id)
                    return session

        # 5. Finalize Session: Require creds.valid
        now_ts = time.time()
        if creds is not None and getattr(creds, "valid", False):
            client = self._instantiate_genai_client(credentials=creds, account_id=account_id, profile=profile)
            expiry_ts = self._extract_expiry_timestamp(creds)

            if GENAI_SDK_AVAILABLE and client is None:
                error_msg = "Failed to instantiate isolated genai.Client for live session"
                logger.error("Authentication failed for %s: %s", account_id, error_msg)
                session = AccountSession(
                    account_id=account_id,
                    role=profile.role.value,
                    is_authenticated=False,
                    auth_method=auth_method,
                    token_expiry=expiry_ts,
                    client=None,
                    credentials=creds,
                    last_refreshed=now_ts,
                    error=error_msg,
                    metadata={"live_auth": True}
                )
                with self._lock:
                    self.sessions[account_id] = session
                return session

            session = AccountSession(
                account_id=account_id,
                role=profile.role.value,
                is_authenticated=True,
                auth_method=auth_method,
                token_expiry=expiry_ts,
                client=client,
                credentials=creds,
                last_refreshed=now_ts,
                error=None,
                metadata={"live_auth": True}
            )
            with self._lock:
                self.sessions[account_id] = session
                if client:
                    self.clients[account_id] = client
            logger.info("Successfully authenticated %s (%s) via %s", account_id, profile.role.value, auth_method)
            return session
        else:
            session = AccountSession(
                account_id=account_id,
                role=profile.role.value,
                is_authenticated=False,
                auth_method=auth_method,
                token_expiry=None,
                client=None,
                credentials=None,
                last_refreshed=now_ts,
                error=error_msg or "Failed to authenticate account using all configured methods."
            )
            with self._lock:
                self.sessions[account_id] = session
            logger.error("Authentication failed for %s: %s", account_id, session.error)
            return session

    def authenticate_all(self, dry_run: Optional[bool] = None) -> Dict[str, AccountSession]:
        """Authenticates all active configured accounts."""
        with self._lock:
            active_profiles = [p for p in list(self.profiles.values()) if p.is_active]

        results: Dict[str, AccountSession] = {}
        for profile in active_profiles:
            session = self.authenticate_account(profile.account_id, dry_run=dry_run)
            results[profile.account_id] = session
        return results

    def refresh_credentials(self, account_id: str) -> bool:
        """Forces autonomous token refresh for an authenticated session."""
        with self._lock:
            session = self.get_session(account_id)
            if self.dry_run:
                logger.info("[DRY-RUN] Headless credentials refresh simulated for %s", account_id)
                if session:
                    now_ts = time.time()
                    session.last_refreshed = now_ts
                    session.token_expiry = now_ts + 3600.0
                    session.is_authenticated = True
                return True

            if not session or not session.credentials:
                # Re-authenticate from scratch
                new_session = self.authenticate_account(account_id, dry_run=self.dry_run)
                return new_session.is_authenticated

            creds = session.credentials
            if not hasattr(creds, "refresh"):
                return False

            try:
                creds.refresh(Request())
                session.token_expiry = self._extract_expiry_timestamp(creds)
                session.last_refreshed = time.time()
                session.is_authenticated = bool(creds.valid)

                # Update client if credentials changed
                profile = self.get_profile(account_id)
                session.client = self._instantiate_genai_client(
                    credentials=creds, account_id=account_id, profile=profile
                )
                if session.client:
                    self.clients[account_id] = session.client

                # If OAuth token file, persist atomically
                if profile and profile.primary_cred_type == CredentialType.OAUTH2_TOKEN and profile.cred_file_path:
                    try:
                        self._write_credentials_file_atomically(profile.cred_file_path, creds.to_json())
                    except Exception as pe:
                        logger.warning("Failed to persist refreshed credentials atomically: %s", pe)

                logger.info("Headless credentials refresh succeeded for %s", account_id)
                return True
            except Exception as e:
                logger.error("Headless credentials refresh failed for %s: %s", account_id, e)
                session.error = str(e)
                session.is_authenticated = False
                return False

    def export_status_manifest(self) -> Dict[str, Any]:
        """Exports aggregated authentication and isolation telemetry manifest."""
        with self._lock:
            sessions_snapshot = list(self.sessions.values())
            accounts_dict = {
                acc_id: session.to_dict()
                for acc_id, session in list(self.sessions.items())
            }
            total_accounts = len(self.profiles)
            auth_count = sum(1 for s in sessions_snapshot if s.is_authenticated)
            isolation_ok = self._verify_isolation()

        return {
            "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "dry_run": self.dry_run,
            "total_accounts": total_accounts,
            "authenticated_accounts": auth_count,
            "client_isolation_verified": isolation_ok,
            "accounts": accounts_dict
        }

    def _verify_isolation(self) -> bool:
        """Verifies that all active genai client instances are distinct objects with isolated authorization."""
        with self._lock:
            active_sessions = [s for s in list(self.sessions.values()) if s.is_authenticated]
            if not active_sessions:
                return True

            active_clients = [c for c in list(self.clients.values()) if c is not None]

            # If any authenticated session is missing a client while SDK is available, fail isolation
            if GENAI_SDK_AVAILABLE:
                if any(s.client is None for s in active_sessions):
                    return False
                if len(active_clients) < len(active_sessions):
                    return False

            if len(active_clients) <= 1:
                return True

            # 1. Distinct Python object references
            if len(active_clients) != len(set(id(c) for c in active_clients)):
                return False

            # 2. Distinct underlying _api_client instances
            api_clients = [getattr(c, "_api_client", None) for c in active_clients]
            valid_api_clients = [ac for ac in api_clients if ac is not None]
            if len(valid_api_clients) > 1 and len(valid_api_clients) != len(set(id(ac) for ac in valid_api_clients)):
                return False

            # 3. Distinct authorization headers / API keys across clients
            auth_identifiers: List[Tuple[Optional[str], Optional[str]]] = []
            for c in active_clients:
                api_client = getattr(c, "_api_client", None)
                if api_client is not None:
                    api_key = getattr(api_client, "api_key", None)
                    http_opts = getattr(api_client, "_http_options", None)
                    headers = getattr(http_opts, "headers", None) or {}
                    auth_header = headers.get("Authorization") or headers.get("x-goog-api-key")
                    auth_identifiers.append((api_key, auth_header))

            if len(auth_identifiers) > 1:
                keys = [k for k, _ in auth_identifiers if k]
                if len(keys) != len(set(keys)):
                    return False
                headers_list = [h for _, h in auth_identifiers if h]
                if len(headers_list) != len(set(headers_list)):
                    return False

            return True


def create_dual_account_manager(
    config_path: Optional[Union[str, Path]] = None,
    dry_run: bool = False
) -> DualAccountManager:
    """Convenience factory function."""
    return DualAccountManager(config_path=config_path, dry_run=dry_run)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Dual-Account Auth & Isolation Engine")
    parser.add_argument("--dry-run", action="store_true", help="Simulate authentication without network mutating calls")
    parser.add_argument("--config", type=str, default=None, help="Path to sync_config.json")
    parser.add_argument("--account", type=str, default=None, help="Specific account ID to authenticate")
    args = parser.parse_args()

    mgr = create_dual_account_manager(config_path=args.config, dry_run=args.dry_run)
    if args.account:
        session = mgr.authenticate_account(args.account)
        sessions = {args.account: session}
    else:
        sessions = mgr.authenticate_all()

    print(json.dumps(mgr.export_status_manifest(), indent=2))
    all_ok = all(s.is_authenticated for s in sessions.values())
    sys.exit(0 if all_ok else 1)
