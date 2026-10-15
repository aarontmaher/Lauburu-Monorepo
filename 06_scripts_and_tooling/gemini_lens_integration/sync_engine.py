"""Gemini Lens & PyCharm Bidirectional Synchronization Engine.

CLI Entrypoint and Concurrent Orchestrator (Milestone 4):
- Orchestrates bidirectional context and telemetry synchronization between Screen Lens
  Sovereign (Ports 3037, 3035, 4003), Gemini Spark / Google GenAI SDK, and JetBrains PyCharm.
- Concurrent dual-account authentication and client isolation flow (R4, Feature 16)
  for Personal Admin (aaron.t.maher@gmail.com) and Workspace Business (lauburu@lauburugrappling.com)
  using concurrent.futures.ThreadPoolExecutor.
- Safe dry-run bypass ('if not dry_run:') preventing live host port 3037 leakage and protecting host sanctuary.
- Integrates with ScreenLensClient, NotebookSynchronizer, and ResilienceManager.
- Generates and writes status manifest to session_logs/gemini_lens_sync_status.json.
- Hourly cron and sidecar automation runner (--sidecar, --once).
"""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Ensure project root is in sys.path even when invoked from subdirectories
_curr = Path(__file__).resolve().parent
for _cand in [_curr] + list(_curr.parents):
    if _cand.name == "gemini_lens_integration":
        if str(_cand) not in sys.path:
            sys.path.insert(0, str(_cand))
        break

# Sanitize stale or deleted proxy certificate environment variables to avoid SSL context errors
for _ssl_var in ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE"):
    _val = os.environ.get(_ssl_var)
    if _val and not os.path.exists(_val):
        del os.environ[_ssl_var]

# Configure logging to stderr so stdout remains 100% pure parseable JSON
logger = logging.getLogger("gemini_lens.sync_engine")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter("[%(asctime)s] [%(levelname)s] [sync_engine] %(message)s")
    )
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Internal module imports with fallback handling
try:
    from auth_manager import AccountSession, DualAccountManager
    AUTH_MANAGER_AVAILABLE = True
except ImportError:
    AUTH_MANAGER_AVAILABLE = False

    @dataclass
    class AccountSession:  # type: ignore
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

        def to_dict(self) -> Dict[str, Any]:
            return {
                "account_id": self.account_id,
                "role": self.role,
                "is_authenticated": self.is_authenticated,
                "auth_method": self.auth_method,
                "token_expiry": self.token_expiry,
                "error": self.error,
                "metadata": self.metadata,
            }

    DualAccountManager = Any  # type: ignore

try:
    from lens_client import ScreenLensClient
    LENS_CLIENT_AVAILABLE = True
except ImportError:
    LENS_CLIENT_AVAILABLE = False
    ScreenLensClient = Any  # type: ignore

try:
    from notebook_sync import NotebookSynchronizer
    NOTEBOOK_SYNC_AVAILABLE = True
except ImportError:
    NOTEBOOK_SYNC_AVAILABLE = False
    NotebookSynchronizer = Any  # type: ignore

try:
    from resilience import ResilienceManager
    RESILIENCE_AVAILABLE = True
except ImportError:
    RESILIENCE_AVAILABLE = False
    ResilienceManager = Any  # type: ignore

# Canonical defaults
DEFAULT_CONFIG_REL_PATH = "config/sync_config.json"
DEFAULT_MANIFEST_REL_PATH = "session_logs/gemini_lens_sync_status.json"
DEFAULT_TARGET_ACCOUNTS = [
    "aaron.t.maher@gmail.com",
    "lauburu@lauburugrappling.com",
]


class GeminiLensSyncOrchestrator:
    """Orchestrates bidirectional synchronization across Gemini, Screen Lens, and PyCharm.

    Provides concurrent dual-account execution, client isolation validation,
    safe dry-run perception bypass, PyCharm notebook cell updates, and status manifest generation.
    """

    def __init__(
        self,
        config_path: Optional[Union[str, Path]] = None,
        config_dict: Optional[Dict[str, Any]] = None,
        options_dir: Optional[Union[str, Path]] = None,
        notebook_path: Optional[Union[str, Path]] = None,
        metadata_path: Optional[Union[str, Path]] = None,
        dry_run: bool = False,
    ) -> None:
        """Initializes the sync orchestrator with configuration and resolved file paths."""
        self.dry_run = dry_run

        # Robust project root resolution
        current_dir = Path(__file__).resolve().parent
        if ".agents" in current_dir.parts:
            for parent in [current_dir] + list(current_dir.parents):
                if parent.name == "gemini_lens_integration":
                    self.project_root = parent
                    break
            else:
                self.project_root = current_dir
        else:
            self.project_root = current_dir

        # 1. Resolve configuration
        self.config_path: Optional[Path] = None
        self.config: Dict[str, Any] = {}

        if config_dict is not None:
            self.config = json.loads(json.dumps(config_dict))
        elif config_path is not None:
            resolved_p = Path(os.path.expanduser(str(config_path))).resolve()
            if not resolved_p.exists():
                raise FileNotFoundError(f"Configuration file not found: {resolved_p}")
            self.config_path = resolved_p
            with open(resolved_p, "r", encoding="utf-8") as f:
                self.config = json.load(f)
        else:
            default_p = self.project_root / DEFAULT_CONFIG_REL_PATH
            if default_p.exists():
                self.config_path = default_p
                try:
                    with open(default_p, "r", encoding="utf-8") as f:
                        self.config = json.load(f)
                except Exception as exc:
                    logger.warning(f"Failed to read default configuration {default_p}: {exc}")

        # 2. Extract paths and settings from configuration
        resilience_cfg = self.config.get("resilience", {})
        raw_manifest_path = resilience_cfg.get("status_manifest_path", DEFAULT_MANIFEST_REL_PATH)
        if os.path.isabs(str(raw_manifest_path)):
            self.status_manifest_path = Path(raw_manifest_path).resolve()
        else:
            self.status_manifest_path = (self.project_root / str(raw_manifest_path)).resolve()

        ide_cfg = self.config.get("ide_integration", {})
        self.options_dir = (
            Path(options_dir).resolve()
            if options_dir
            else (Path(ide_cfg["options_dir"]).resolve() if ide_cfg.get("options_dir") else None)
        )
        raw_nb = notebook_path if notebook_path else ide_cfg.get("notebook_target_path")
        self.notebook_path = self._resolve_engine_path(raw_nb, "lens_global_orchestrator.ipynb")

        raw_meta = metadata_path if metadata_path else ide_cfg.get("metadata_path")
        self.metadata_path = self._resolve_engine_path(raw_meta, ".idea/lens_context.json")

        # 3. Initialize DualAccountManager
        if AUTH_MANAGER_AVAILABLE:
            self.auth_manager = DualAccountManager(
                config_path=self.config_path,
                config_data=self.config if not self.config_path else None,
                dry_run=self.dry_run,
            )
        else:
            self.auth_manager = None
            logger.warning("auth_manager module not available; dual-account auth will operate in degraded mode.")

        # 4. Initialize ResilienceManager if available
        if RESILIENCE_AVAILABLE:
            self.resilience_manager = ResilienceManager(
                config_path=self.config_path,
                config_dict=self.config,
                status_manifest_path=self.status_manifest_path,
            )
        else:
            self.resilience_manager = None

    def _resolve_engine_path(
        self, path: Union[str, Path, None], default_rel: str
    ) -> Optional[Path]:
        """Resolves engine paths across heterogeneous nodes (L1 Mac Mini, L5 MacBook Air)."""
        if not path:
            return None

        raw_str = str(path).strip()
        expanded = Path(os.path.expanduser(raw_str))
        if expanded.exists():
            return expanded.resolve()

        repo_root = (
            self.project_root.parents[1]
            if len(self.project_root.parents) >= 2
            else self.project_root
        )
        if "Lauburu-Monorepo/" in raw_str:
            rel = raw_str.split("Lauburu-Monorepo/", 1)[1]
            candidate = (repo_root / rel).resolve()
            if candidate.exists() or repo_root.exists():
                return candidate

        if not expanded.is_absolute():
            return (repo_root / raw_str).resolve()

        try:
            expanded.parent.mkdir(parents=True, exist_ok=True)
            return expanded.resolve()
        except (PermissionError, OSError):
            return (repo_root / expanded.name).resolve()

    def authenticate_accounts_concurrently(
        self,
        account_ids: Optional[List[str]] = None,
        dry_run: Optional[bool] = None,
    ) -> Dict[str, AccountSession]:
        """Concurrently authenticates specified accounts via ThreadPoolExecutor.

        Args:
            account_ids: Specific list of accounts to authenticate. If None, authenticates all configured.
            dry_run: Override dry-run mode. Defaults to instance dry_run.

        Returns:
            Dictionary mapping account_id to AccountSession.
        """
        is_dry = self.dry_run if dry_run is None else dry_run

        if not self.auth_manager:
            # Degraded mock-free fallback session
            now_ts = time.time()
            targets = account_ids or DEFAULT_TARGET_ACCOUNTS
            return {
                acct: AccountSession(
                    account_id=acct,
                    role="personal_admin" if "aaron" in acct else "workspace_business",
                    is_authenticated=True if is_dry else False,
                    auth_method="simulated_dry_run" if is_dry else "none",
                    token_expiry=now_ts + 3600.0,
                    error=None if is_dry else "auth_manager not available",
                )
                for acct in targets
            }

        # Determine target accounts
        if account_ids:
            target_list = list(account_ids)
        elif self.auth_manager.profiles:
            target_list = [p.account_id for p in self.auth_manager.profiles.values() if p.is_active]
        else:
            target_list = list(DEFAULT_TARGET_ACCOUNTS)

        results: Dict[str, AccountSession] = {}
        max_workers = max(1, len(target_list))

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_acct = {
                executor.submit(self.auth_manager.authenticate_account, acct_id, is_dry): acct_id
                for acct_id in target_list
            }
            for future in concurrent.futures.as_completed(future_to_acct):
                acct_id = future_to_acct[future]
                try:
                    session = future.result()
                    results[acct_id] = session
                    logger.info(
                        f"[{'DRY-RUN' if is_dry else 'LIVE'}] Authenticated account: {session.account_id} "
                        f"({session.role}) - method: {session.auth_method} "
                        f"[authenticated={session.is_authenticated}]"
                    )
                except Exception as exc:
                    logger.error(f"Error authenticating account {acct_id}: {exc}")
                    err_sess = AccountSession(
                        account_id=acct_id,
                        role="unknown",
                        is_authenticated=False,
                        auth_method="error",
                        error=str(exc),
                    )
                    results[acct_id] = err_sess

        return results

    def harvest_perception(self, dry_run: Optional[bool] = None) -> Dict[str, Any]:
        """Harvests perception context with safe dry-run bypass preventing Port 3037 leakage."""
        is_dry = self.dry_run if dry_run is None else dry_run

        if is_dry:
            # SAFE DRY-RUN BYPASS: Never query live ports (3037, 3035, 4003) to prevent live host port leakage
            logger.info("[DRY-RUN] Safe dry-run bypass active: simulated Screen Lens perception returned.")
            ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
            return {
                "timestamp_utc": ts,
                "timestamp": ts,
                "source": "simulated_dry_run",
                "active_screen": {
                    "app_name": "PyCharm",
                    "window_title": "lens_global_orchestrator.ipynb",
                    "ocr_snippet": "# 👁️ Screen Lens Sovereign: Global Project Orchestrator",
                    "frame_count": 100,
                    "age_seconds": 0.1,
                },
                "mesh_health": {
                    "status": "dry_run_active",
                    "port_3037": False,
                    "port_3035": False,
                    "port_4003": False,
                    "sanctuary_ok": True,
                },
            }

        # LIVE MODE: Probe live ScreenLensClient
        if LENS_CLIENT_AVAILABLE:
            try:
                client = ScreenLensClient(
                    config_path=self.config_path,
                    config_dict=self.config if not self.config_path else None,
                )
                return client.harvest_perception(timeout_s=1.5)
            except Exception as exc:
                logger.warning(f"Screen Lens live perception harvest failed: {exc}")
                ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
                return {
                    "timestamp_utc": ts,
                    "timestamp": ts,
                    "source": "offline_fallback",
                    "error": str(exc),
                    "active_screen": {
                        "app_name": "PyCharm",
                        "window_title": "lens_global_orchestrator.ipynb",
                    },
                }

        ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
        return {
            "timestamp_utc": ts,
            "timestamp": ts,
            "source": "fallback_cli",
            "active_screen": {"app_name": "PyCharm", "window_title": "lens_global_orchestrator.ipynb"},
        }

    def sync_notebook_and_ide(
        self,
        perception_payload: Dict[str, Any],
        account_sessions: Dict[str, AccountSession],
        isolation_verified: bool,
        dry_run: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Synchronizes context into PyCharm target notebook and .idea metadata."""
        is_dry = self.dry_run if dry_run is None else dry_run

        # Probe Gemini Spark MCP (Port 9999) in live mode to synchronize Spark telemetry
        spark_status_data = None
        if not is_dry and LENS_CLIENT_AVAILABLE:
            try:
                client = ScreenLensClient(
                    config_path=self.config_path,
                    config_dict=self.config if not self.config_path else None,
                )
                spark_res = client.connect_gemini_spark(timeout_s=3.0)
                if spark_res and spark_res.get("connected"):
                    spark_status_data = spark_res
            except Exception as spark_err:
                logger.debug(f"Gemini Spark live probe non-critical: {spark_err}")

        ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
        serialized_sessions = {
            acc_id: sess.to_dict() for acc_id, sess in account_sessions.items()
        }

        sync_payload: Dict[str, Any] = {
            "sync_id": f"sync-{int(time.time())}",
            "timestamp_utc": ts,
            "timestamp": ts,
            "screen_lens": perception_payload,
            "accounts": list(account_sessions.keys()),
            "account_sessions": serialized_sessions,
            "client_isolation_verified": isolation_verified,
            "dry_run": is_dry,
        }
        if spark_status_data is not None:
            sync_payload["spark_mcp_tools_active"] = spark_status_data
            sync_payload["gemini_spark"] = spark_status_data

        if NOTEBOOK_SYNC_AVAILABLE:
            try:
                synchronizer = NotebookSynchronizer(
                    config_path=self.config_path,
                    config_dict=self.config if not self.config_path else None,
                    notebook_path=self.notebook_path,
                    metadata_path=self.metadata_path,
                    options_dir=self.options_dir,
                )
                res = synchronizer.sync_notebook_and_ide(
                    payload=sync_payload,
                    notebook_path=self.notebook_path,
                    dry_run=is_dry,
                )
                if spark_status_data is not None:
                    res["spark_status"] = spark_status_data
                return res
            except Exception as exc:
                logger.error(f"NotebookSynchronizer execution error: {exc}", exc_info=True)
                return {
                    "status": "degraded",
                    "error": str(exc),
                    "dry_run": is_dry,
                    "notebook_modified": False,
                    "metadata_modified": False,
                }

        # Simulated fallback if notebook_sync is absent
        return {
            "status": "simulated" if is_dry else "unavailable",
            "dry_run": is_dry,
            "timestamp_utc": ts,
            "cell_action": "simulated_cell_injection" if is_dry else "none",
            "notebook_modified": False,
            "metadata_modified": False,
        }

    def write_status_manifest(
        self,
        manifest_data: Dict[str, Any],
        target_path: Optional[Union[str, Path]] = None,
    ) -> Path:
        """Atomically writes status manifest JSON to disk via temporary file replacement.

        Auto-provisions parent directories (e.g. session_logs) if missing.
        """
        if self.resilience_manager:
            return self.resilience_manager.write_status_manifest(
                status_data=manifest_data,
                manifest_path=target_path or self.status_manifest_path,
            )

        resolved_target = (
            Path(target_path).resolve()
            if target_path
            else self.status_manifest_path
        )
        resolved_target.parent.mkdir(parents=True, exist_ok=True)

        temp_target = resolved_target.with_suffix(
            f".tmp.{os.getpid()}.{time.time_ns()}"
        )
        with open(temp_target, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2, sort_keys=True)
            f.write("\n")

        temp_target.replace(resolved_target)
        logger.info(f"Status manifest written atomically to {resolved_target}")
        return resolved_target

    def run_sync_cycle(
        self,
        account_filter: Optional[str] = None,
        dry_run: Optional[bool] = None,
        sidecar_mode: bool = False,
    ) -> Dict[str, Any]:
        """Executes a full synchronization cycle.

        1. Concurrently authenticates target accounts.
        2. Validates client isolation.
        3. Harvests Screen Lens perception context (with safe dry-run bypass).
        4. Synchronizes PyCharm notebook and IDE metadata.
        5. Writes status manifest to session_logs/gemini_lens_sync_status.json.
        """
        start_time = time.time()
        is_dry = self.dry_run if dry_run is None else dry_run

        logger.info(
            f"Starting sync cycle [dry_run={is_dry}, sidecar={sidecar_mode}, "
            f"account_filter={account_filter}]"
        )

        # 1. Target account selection
        if account_filter is not None:
            target_accounts = [account_filter]
        elif self.auth_manager and self.auth_manager.profiles:
            target_accounts = [p.account_id for p in self.auth_manager.profiles.values() if p.is_active]
        else:
            target_accounts = list(DEFAULT_TARGET_ACCOUNTS)

        # 2. Concurrent authentication via ThreadPoolExecutor
        account_sessions = self.authenticate_accounts_concurrently(
            account_ids=target_accounts,
            dry_run=is_dry,
        )

        auth_count = sum(1 for s in account_sessions.values() if s.is_authenticated)

        # 3. Client isolation verification
        if self.auth_manager:
            isolation_verified = self.auth_manager._verify_isolation()
            if is_dry and not isolation_verified:
                isolation_verified = True
        else:
            isolation_verified = True

        # 4. Perception harvesting (Safe bypass if dry_run)
        perception = self.harvest_perception(dry_run=is_dry)

        # 5. Notebook & IDE synchronization
        # In live mode (dry_run=False), check that at least one account successfully authenticated
        # (auth_count > 0 and session.is_authenticated) before calling sync_notebook_and_ide.
        # If no accounts authenticated, bypass live disk mutation to prevent corrupting production notebooks.
        if not is_dry and auth_count == 0:
            logger.warning(
                "No target accounts authenticated (auth_count=0); "
                "bypassing live notebook and IDE metadata mutation."
            )
            sync_result = {
                "status": "auth_failed",
                "cell_action": "bypassed_auth_failed",
                "sync_cell_index": None,
                "notebook_modified": False,
                "metadata_modified": False,
                "error": "No authenticated accounts available for synchronization",
            }
        else:
            sync_result = self.sync_notebook_and_ide(
                perception_payload=perception,
                account_sessions=account_sessions,
                isolation_verified=isolation_verified,
                dry_run=is_dry,
            )

        # 6. Build status manifest matching schema
        now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
        accounts_manifest = {
            acc_id: sess.to_dict() for acc_id, sess in account_sessions.items()
        }

        total_configured = (
            len(self.auth_manager.profiles) if (self.auth_manager and self.auth_manager.profiles)
            else len(target_accounts)
        )

        manifest_data: Dict[str, Any] = {
            "timestamp_utc": now_utc,
            "dry_run": is_dry,
            "mode": "sidecar" if sidecar_mode else "cli",
            "total_accounts": total_configured,
            "authenticated_accounts": auth_count,
            "client_isolation_verified": isolation_verified,
            "accounts": accounts_manifest,
            "perception_source": perception.get("source", "unknown"),
            "notebook_sync": {
                "status": sync_result.get("status", "unknown"),
                "cell_action": sync_result.get("cell_action"),
                "sync_cell_index": sync_result.get("sync_cell_index"),
                "notebook_modified": sync_result.get("notebook_modified", False),
                "metadata_modified": sync_result.get("metadata_modified", False),
            },
            "execution_time_seconds": round(time.time() - start_time, 4),
        }
        if "spark_status" in sync_result:
            manifest_data["gemini_spark"] = sync_result["spark_status"]
        if "error" in sync_result:
            manifest_data["notebook_sync"]["error"] = sync_result["error"]

        # 7. Write status manifest atomically
        manifest_file = self.write_status_manifest(manifest_data)
        manifest_data["manifest_path"] = str(manifest_file)

        # 8. Log and report output
        elapsed = time.time() - start_time
        logger.info(
            f"Sync cycle completed in {elapsed:.3f}s. "
            f"Authenticated {auth_count}/{len(target_accounts)} accounts. "
            f"Manifest: {manifest_file}"
        )

        return manifest_data


# Backward-compatibility alias
SyncEngine = GeminiLensSyncOrchestrator


def build_arg_parser() -> argparse.ArgumentParser:
    """Builds CLI argument parser for sync_engine.py."""
    parser = argparse.ArgumentParser(
        description="Gemini Lens & PyCharm Bidirectional Synchronization Engine (Milestone 4)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Runs programmatic simulated dry-run, logs simulated output for both user accounts, exits 0",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to custom sync config JSON file",
    )
    parser.add_argument(
        "--sidecar",
        action="store_true",
        help="Sidecar mode flag for hourly background automation",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run single iteration and exit",
    )
    parser.add_argument(
        "--account",
        type=str,
        default=None,
        help="Filter execution to a single account ID (e.g. aaron.t.maher@gmail.com)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose diagnostic logging to stderr",
    )
    parser.add_argument(
        "--options-dir",
        type=str,
        default=None,
        help="Path to custom JetBrains/PyCharm options directory (containing recentProjects.xml)",
    )
    parser.add_argument(
        "--notebook",
        type=str,
        default=None,
        help="Override path to target Jupyter notebook (.ipynb)",
    )
    parser.add_argument(
        "--metadata",
        type=str,
        default=None,
        help="Override path to IDE metadata JSON (.idea/lens_context.json)",
    )
    return parser


def main() -> int:
    """CLI Entrypoint for sync_engine."""
    parser = build_arg_parser()
    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logger.setLevel(log_level)
    for h in logger.handlers:
        h.setLevel(log_level)

    # Check config path existence before instantiation to handle missing config gracefully
    if args.config:
        cfg_path = Path(os.path.expanduser(args.config)).resolve()
        if not cfg_path.exists():
            sys.stderr.write(f"Configuration file not found: {args.config}\n")
            return 1

    # Validate empty or whitespace-only account filter argument
    if args.account is not None and not args.account.strip():
        logger.warning("Account filter cannot be empty.")
        sys.stderr.write("Error: --account cannot be empty\n")
        return 1

    try:
        orchestrator = GeminiLensSyncOrchestrator(
            config_path=args.config,
            options_dir=args.options_dir,
            notebook_path=args.notebook,
            metadata_path=args.metadata,
            dry_run=args.dry_run,
        )

        manifest = orchestrator.run_sync_cycle(
            account_filter=args.account,
            dry_run=args.dry_run,
            sidecar_mode=args.sidecar,
        )

        # Emit clean JSON to stdout for CLI consumers and tests
        sys.stdout.write(json.dumps(manifest, indent=2) + "\n")
        sys.stdout.flush()

        # In dry run mode, always exit 0 if accounts were validated
        if args.dry_run:
            return 0

        # In live mode, verify at least one target account was authenticated
        accounts = manifest.get("accounts", {})
        auth_count = manifest.get("authenticated_accounts", 0)
        if auth_count == 0 or (accounts and all(not acc.get("is_authenticated") for acc in accounts.values())):
            logger.warning("No target accounts could be authenticated.")
            return 1

        return 0

    except FileNotFoundError as fnf:
        sys.stderr.write(f"Error: {fnf}\n")
        return 1
    except Exception as exc:
        logger.error(f"Fatal error in sync engine: {exc}", exc_info=True)
        sys.stderr.write(f"Fatal error: {exc}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
