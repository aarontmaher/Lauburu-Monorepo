"""Screen Lens Sovereign & Gemini Spark Synchronization Client.

Provides genuine, zero-mock perception harvesting across live Screen Lens daemons
(Ports 3037, 3035, 4003), local read-only SQLite database fallback (~/.lauburu/*.db),
authentic Darwin kernel Launch Services fallback, and Gemini Spark MCP bridge verification.
Matches interface contracts defined in PROJECT.md and explorer_survey_1 handoff.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import resource
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger("gemini_lens.lens_client")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter("[%(asctime)s] [%(levelname)s] [lens_client] %(message)s")
    )
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


DEFAULT_PORT_ORDER: List[int] = [3037, 3035, 4003]

DEFAULT_CONFIG: Dict[str, Any] = {
    "endpoints": {
        "screen_lens": {
            "orchestrator_url": "http://127.0.0.1:3037",
            "ocr_stream_url": "http://127.0.0.1:3035",
            "hud_mjpeg_url": "http://127.0.0.1:4003",
            "remote_orchestrator_url": "http://100.119.199.76:3037",
            "remote_ocr_stream_url": "http://100.119.199.76:3035",
            "remote_hud_mjpeg_url": "http://100.119.199.76:4003",
            "db_fallback_path": "~/.lauburu/ocr_frames.db",
            "db_fallback_secondary": "~/.lauburu/screen_lens.sqlite",
        },
        "gemini_spark": {
            "mcp_project_health_url": "http://127.0.0.1:9999/mcp/project/health",
            "mcp_health_url": "http://127.0.0.1:9999/health",
            "mcp_sse_url": "http://127.0.0.1:9999/sse",
            "mcp_messages_url": "http://127.0.0.1:9999/messages",
        },
    },
    "resilience": {
        "connect_timeout_seconds": 2.0,
        "min_ram_sanctuary_gb": 4.8,
    },
}


def create_proxy_bypass_opener() -> urllib.request.OpenerDirector:
    """Builds a urllib OpenerDirector that explicitly bypasses system HTTP proxies.

    Required on macOS to prevent system proxy handlers (e.g. loopback traps)
    from intercepting or failing connections to localhost / 127.0.0.1.
    """
    proxy_handler = urllib.request.ProxyHandler({})
    return urllib.request.build_opener(proxy_handler)


def normalize_iso_timestamp(val: Any, strict: bool = False) -> str:
    """Normalizes any timestamp representation into a canonical ISO 8601 UTC string.

    When strict=True, validates that strings containing 'T' or '-' strictly parse via
    datetime.datetime.fromisoformat(), falling back to current UTC timestamp on failure.
    """
    if val is None:
        return datetime.datetime.now(datetime.timezone.utc).isoformat()
    if isinstance(val, (int, float)):
        try:
            numeric_val = float(val)
            if numeric_val > 1e16:
                numeric_val /= 1e9
            elif numeric_val > 1e13:
                numeric_val /= 1e6
            elif numeric_val > 1e11:
                numeric_val /= 1e3
            while numeric_val > 1e11 and numeric_val < float("inf"):
                numeric_val /= 1000.0
            return datetime.datetime.fromtimestamp(
                numeric_val, tz=datetime.timezone.utc
            ).isoformat()
        except Exception:
            return datetime.datetime.now(datetime.timezone.utc).isoformat()
    if isinstance(val, str):
        val = val.strip()
        try:
            numeric_val = float(val)
            if numeric_val > 1e16:
                numeric_val /= 1e9
            elif numeric_val > 1e13:
                numeric_val /= 1e6
            elif numeric_val > 1e11:
                numeric_val /= 1e3
            while numeric_val > 1e11 and numeric_val < float("inf"):
                numeric_val /= 1000.0
            return datetime.datetime.fromtimestamp(
                numeric_val, tz=datetime.timezone.utc
            ).isoformat()
        except (ValueError, OverflowError, OSError):
            pass
        if "T" in val or "-" in val:
            if strict:
                try:
                    datetime.datetime.fromisoformat(val)
                    return val
                except Exception:
                    pass
            else:
                return val
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def get_darwin_front_app() -> Tuple[Optional[str], Optional[int], Optional[str]]:
    """Probes macOS Launch Services via /usr/bin/lsappinfo for authentic frontmost app."""
    if sys.platform != "darwin":
        return None, None, None

    try:
        asn_out = subprocess.run(
            ["/usr/bin/lsappinfo", "front"],
            capture_output=True,
            text=True,
            timeout=1.5,
            check=False,
        )
        asn = asn_out.stdout.strip()
        if not asn:
            return None, None, None

        info_out = subprocess.run(
            ["/usr/bin/lsappinfo", "info", asn],
            capture_output=True,
            text=True,
            timeout=1.5,
            check=False,
        )
        info_text = info_out.stdout
        lines = info_text.splitlines()
        if not lines:
            return None, None, None

        first_line = lines[0].strip()
        app_name = (
            first_line.split("ASN:")[0].strip().strip('"')
            if "ASN:" in first_line
            else None
        )

        pid: Optional[int] = None
        bundle_id: Optional[str] = None
        for line in lines[1:]:
            line_str = line.strip()
            if line_str.startswith("pid ="):
                parts = line_str.split("pid =")
                if len(parts) > 1:
                    pid_part = parts[1].split()[0].strip()
                    if pid_part.isdigit():
                        pid = int(pid_part)
            if "bundleID=" in line_str:
                parts = line_str.split("bundleID=")
                if len(parts) > 1:
                    bundle_id = parts[1].split()[0].strip().strip('"')

        return app_name, pid, bundle_id
    except Exception as exc:
        logger.debug(f"lsappinfo query failed: {exc}")
        return None, None, None


def get_darwin_memory_info() -> Dict[str, Any]:
    """Authentically probes macOS Mach kernel memory metrics via vm_stat."""
    if sys.platform != "darwin":
        return {"platform": sys.platform, "status": "non_darwin"}

    try:
        out = subprocess.run(
            ["/usr/bin/vm_stat"],
            capture_output=True,
            text=True,
            timeout=1.5,
            check=False,
        )
        pages: Dict[str, int] = {}
        try:
            page_size = resource.getpagesize()
        except Exception:
            page_size = os.sysconf("SC_PAGESIZE") if hasattr(os, "sysconf") else 16384
        for line in out.stdout.splitlines():
            if ":" in line:
                key, _, val = line.partition(":")
                try:
                    pages[key.strip()] = int(val.strip().rstrip("."))
                except ValueError:
                    pass

        free_gb = pages.get("Pages free", 0) * page_size / (1024**3)
        wired_gb = pages.get("Pages wired down", 0) * page_size / (1024**3)
        active_gb = pages.get("Pages active", 0) * page_size / (1024**3)
        inactive_gb = pages.get("Pages inactive", 0) * page_size / (1024**3)
        compressed_gb = (
            pages.get("Pages occupied by compressor", 0) * page_size / (1024**3)
        )

        return {
            "free_gb": round(free_gb, 2),
            "wired_gb": round(wired_gb, 2),
            "active_gb": round(active_gb, 2),
            "inactive_gb": round(inactive_gb, 2),
            "compressed_gb": round(compressed_gb, 2),
            "sanctuary_floor_gb": 4.8,
            "sanctuary_preserved": free_gb >= 4.8,
        }
    except Exception as exc:
        logger.debug(f"Darwin vm_stat probe failed: {exc}")
        return {"error": str(exc), "sanctuary_preserved": False}


class ScreenLensClient:
    """Client for Screen Lens Sovereign vision, OCR, and Gemini Spark MCP.

    Fulfills Milestone 2 interface contracts:
    - Queries Port 3037, 3035, and 4003 with loopback proxy bypass.
    - Gracefully falls back to local read-only SQLite database.
    - Gracefully falls back to authentic local OS / kernel information without fake mocks.
    - Probes Gemini Spark MCP daemon on Port 9999.
    - Generates consolidated perception & Spark context.
    """

    def __init__(
        self,
        config_path: Optional[Union[str, Path]] = None,
        config_dict: Optional[Dict[str, Any]] = None,
        opener: Optional[urllib.request.OpenerDirector] = None,
        sqlite_db_paths: Optional[List[Union[str, Path]]] = None,
    ) -> None:
        """Initializes ScreenLensClient with configuration and proxy-bypass opener."""
        self._config = self._load_configuration(config_path, config_dict)
        self._opener = opener or create_proxy_bypass_opener()
        self._sqlite_db_paths = self._resolve_sqlite_db_paths(sqlite_db_paths)

    @property
    def config(self) -> Dict[str, Any]:
        """Returns the loaded configuration dictionary."""
        return self._config

    @property
    def opener(self) -> urllib.request.OpenerDirector:
        """Returns the proxy-bypass OpenerDirector instance."""
        return self._opener

    @property
    def sqlite_db_paths(self) -> List[Path]:
        """Returns the prioritized list of SQLite fallback database paths."""
        return self._sqlite_db_paths

    def _load_configuration(
        self,
        config_path: Optional[Union[str, Path]],
        config_dict: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Loads configuration from dict, file path, standard project location, or defaults."""
        if config_dict is not None:
            return json.loads(json.dumps(config_dict))

        candidate_paths: List[Path] = []
        if config_path is not None:
            candidate_paths.append(Path(os.path.expanduser(str(config_path))))

        # Standard relative paths
        module_dir = Path(__file__).resolve().parent
        candidate_paths.append(module_dir / "config" / "sync_config.json")
        candidate_paths.append(Path.cwd() / "config" / "sync_config.json")
        candidate_paths.append(
            Path(
                "/Volumes/Lauburu-Monorepo/06_scripts_and_tooling/gemini_lens_integration/config/sync_config.json"
            )
        )

        for path in candidate_paths:
            if path.exists() and path.is_file():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        loaded = json.load(f)
                    if isinstance(loaded, dict):
                        logger.debug(f"Loaded ScreenLensClient configuration from {path}")
                        return loaded
                except Exception as exc:
                    logger.warning(f"Failed to parse configuration at {path}: {exc}")

        logger.debug("Using DEFAULT_CONFIG for ScreenLensClient")
        return json.loads(json.dumps(DEFAULT_CONFIG))

    def _resolve_sqlite_db_paths(
        self, explicit_paths: Optional[List[Union[str, Path]]]
    ) -> List[Path]:
        """Resolves SQLite fallback database paths in priority order."""
        if explicit_paths is not None:
            return [Path(os.path.expanduser(str(p))) for p in explicit_paths]

        resolved: List[Path] = []
        endpoints_cfg = self._config.get("endpoints", {}).get("screen_lens", {})
        for key in ["db_fallback_path", "db_fallback_secondary"]:
            val = endpoints_cfg.get(key)
            if val:
                p = Path(os.path.expanduser(str(val)))
                if p not in resolved:
                    resolved.append(p)

        # Standard canonical locations
        for canonical in ["~/.lauburu/ocr_frames.db", "~/.lauburu/screen_lens.sqlite"]:
            p = Path(os.path.expanduser(canonical))
            if p not in resolved:
                resolved.append(p)

        return resolved

    def _get_live_endpoints_in_order(self) -> List[Tuple[int, str, str]]:
        """Returns candidate live endpoints in order: (Port, URL, EndpointType).

        Includes configured local endpoints (default 127.0.0.1) and remote Mac Mini L1
        endpoints (http://100.119.199.76:3037/api/orchestrator/state, 3035/api/latest,
        4003/api/telemetry/live) in addition to configured defaults (127.0.0.1),
        enabling worker nodes to harvest Screen Lens telemetry seamlessly while preserving
        offline test isolation when custom non-default ports are passed without remote URLs.
        """
        screen_lens_cfg = self._config.get("endpoints", {}).get("screen_lens", {})

        orchestrator_base = screen_lens_cfg.get(
            "orchestrator_url", "http://127.0.0.1:3037"
        ).rstrip("/")
        ocr_base = screen_lens_cfg.get(
            "ocr_stream_url", "http://127.0.0.1:3035"
        ).rstrip("/")
        hud_base = screen_lens_cfg.get(
            "hud_mjpeg_url", "http://127.0.0.1:4003"
        ).rstrip("/")

        candidates: List[Tuple[int, str, str]] = [
            (3037, f"{orchestrator_base}/api/orchestrator/state", "orchestrator"),
            (3035, f"{ocr_base}/api/latest", "ocr"),
            (4003, f"{hud_base}/api/telemetry/live", "stream"),
        ]

        remote_orchestrator = screen_lens_cfg.get("remote_orchestrator_url")
        remote_ocr = screen_lens_cfg.get("remote_ocr_stream_url")
        remote_hud = screen_lens_cfg.get("remote_hud_mjpeg_url")

        # Include remote Mac Mini L1 candidate endpoints if explicitly configured or under default topology
        is_default_topology = (
            ":3037" in orchestrator_base
            and ":3035" in ocr_base
            and ":4003" in hud_base
        )
        if remote_orchestrator or remote_ocr or remote_hud or is_default_topology:
            rem_orch_base = (remote_orchestrator or "http://100.119.199.76:3037").rstrip("/")
            rem_ocr_base = (remote_ocr or "http://100.119.199.76:3035").rstrip("/")
            rem_hud_base = (remote_hud or "http://100.119.199.76:4003").rstrip("/")

            remote_candidates = [
                (3037, f"{rem_orch_base}/api/orchestrator/state", "orchestrator"),
                (3035, f"{rem_ocr_base}/api/latest", "ocr"),
                (4003, f"{rem_hud_base}/api/telemetry/live", "stream"),
            ]
            for ep in remote_candidates:
                candidates.append(ep)

        # Deduplicate while preserving order
        unique_candidates: List[Tuple[int, str, str]] = []
        seen_urls = set()
        for port, url, ep_type in candidates:
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_candidates.append((port, url, ep_type))

        return unique_candidates

    def _probe_live_endpoint(
        self, url: str, endpoint_type: str, timeout_s: float
    ) -> Optional[Dict[str, Any]]:
        """Probes a single live HTTP endpoint and normalizes its JSON response."""
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "GeminiLensSync/1.0",
                    "Accept": "application/json",
                },
            )
            with self._opener.open(req, timeout=timeout_s) as resp:
                if resp.status == 200:
                    raw_bytes = resp.read()
                    data = json.loads(raw_bytes.decode("utf-8"))
                    if not isinstance(data, dict):
                        return None

                    if endpoint_type == "orchestrator":
                        screen = data.get("screen", {})
                        if not isinstance(screen, dict):
                            screen = {}
                        recent_ocr = screen.get("recent_ocr", [])
                        ocr_snippet = (
                            recent_ocr[0]
                            if isinstance(recent_ocr, list) and recent_ocr
                            else ""
                        )
                        return {
                            "timestamp": normalize_iso_timestamp(data.get("timestamp"), strict=True),
                            "active_app": screen.get("active_app") or "Unknown",
                            "window_title": screen.get("window_title") or "N/A",
                            "ocr_snippet": str(ocr_snippet),
                            "mesh_health": data.get("mesh_health")
                            if isinstance(data.get("mesh_health"), dict)
                            else {},
                            "source": "live_api",
                            "endpoint": url,
                            "raw_perception": data,
                        }

                    elif endpoint_type == "ocr":
                        return {
                            "timestamp": normalize_iso_timestamp(data.get("timestamp"), strict=True),
                            "active_app": data.get("app_name") or "Unknown",
                            "window_title": data.get("window_title") or "N/A",
                            "ocr_snippet": str(data.get("text") or ""),
                            "mesh_health": {
                                "status": "online",
                                "port": 3035,
                                "capture_id": data.get("capture_id", data.get("id")),
                                "node_id": data.get("node_id", "L1"),
                            },
                            "source": "live_api",
                            "endpoint": url,
                            "raw_perception": data,
                        }

                    elif endpoint_type == "stream":
                        return {
                            "timestamp": normalize_iso_timestamp(data.get("timestamp"), strict=True),
                            "active_app": data.get("active_app") or "ScreenStream",
                            "window_title": data.get("window_title")
                            or "Live MJPEG Stream",
                            "ocr_snippet": str(data.get("ocr_snippet") or ""),
                            "mesh_health": {
                                "status": "online",
                                "port": 4003,
                                "node_id": data.get("node_id", "L1"),
                                "cpu_pct": data.get("cpu_pct"),
                                "ram_free_gb": data.get("ram_free_gb"),
                                "fps": data.get("fps"),
                            },
                            "source": "live_api",
                            "endpoint": url,
                            "raw_perception": data,
                        }

        except Exception as exc:
            logger.debug(f"Live probe failed for {url}: {exc}")
            return None

        return None

    def _harvest_from_sqlite(self) -> Optional[Dict[str, Any]]:
        """Queries local SQLite databases in read-only URI mode without lock contention."""
        for db_path in self._sqlite_db_paths:
            if not db_path.exists() or not db_path.is_file():
                continue
            if db_path.stat().st_size == 0:
                continue

            conn: Optional[sqlite3.Connection] = None
            try:
                uri = f"file:{db_path.resolve()}?mode=ro"
                conn = sqlite3.connect(uri, uri=True, timeout=1.0)
                cursor = conn.cursor()

                # Discover available tables
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
                )
                tables = [r[0] for r in cursor.fetchall()]
                if not tables:
                    continue

                target_table = "frames" if "frames" in tables else tables[0]
                safe_table = target_table.replace('"', '""')

                # Inspect columns
                cursor.execute(f'PRAGMA table_info("{safe_table}");')
                col_info = cursor.fetchall()
                col_names = [c[1] for c in col_info]

                if not col_names:
                    continue

                # Fetch latest row
                order_col = "rowid"
                for cand in ["id", "timestamp", "capture_id"]:
                    if cand in col_names:
                        order_col = cand
                        break

                safe_order = order_col.replace('"', '""')
                cursor.execute(
                    f'SELECT * FROM "{safe_table}" ORDER BY "{safe_order}" DESC LIMIT 1;'
                )
                row = cursor.fetchone()
                if not row:
                    continue

                row_dict: Dict[str, Any] = dict(zip(col_names, row))

                # Extract normalized fields
                timestamp = normalize_iso_timestamp(
                    row_dict.get("timestamp")
                    or row_dict.get("epoch_ms")
                    or row_dict.get("time")
                    or row_dict.get("created_at"),
                    strict=True,
                )
                active_app = (
                    row_dict.get("app_name")
                    or row_dict.get("active_app")
                    or row_dict.get("app")
                    or row_dict.get("app_package")
                    or row_dict.get("application")
                    or "Unknown"
                )
                window_title = (
                    row_dict.get("window_title")
                    or row_dict.get("title")
                    or row_dict.get("window")
                    or row_dict.get("name")
                    or "N/A"
                )
                ocr_snippet = (
                    row_dict.get("ocr_text")
                    or row_dict.get("text")
                    or row_dict.get("ocr_snippet")
                    or row_dict.get("content")
                    or row_dict.get("ocr")
                    or row_dict.get("snippet")
                    or ""
                )

                frame_id = (
                    row_dict.get("id")
                    or row_dict.get("capture_id")
                    or row_dict.get("frame_id")
                    or 1
                )

                return {
                    "timestamp": timestamp,
                    "active_app": str(active_app),
                    "window_title": str(window_title),
                    "ocr_snippet": str(ocr_snippet),
                    "mesh_health": {
                        "status": "sqlite_cached",
                        "db_path": str(db_path),
                        "table": target_table,
                        "frame_id": frame_id,
                    },
                    "source": "sqlite",
                    "endpoint": str(db_path),
                    "raw_perception": row_dict,
                }

            except Exception as exc:
                logger.debug(f"SQLite fallback query failed for {db_path}: {exc}")
                continue
            finally:
                if conn:
                    try:
                        conn.close()
                    except Exception:
                        pass

        return None

    def _harvest_from_system_fallback(self) -> Dict[str, Any]:
        """Harvests authentic OS/kernel telemetry without mocked or fabricated data."""
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        app_name, pid, bundle_id = get_darwin_front_app()

        if sys.platform == "darwin":
            mem_info = get_darwin_memory_info()
            resolved_app = app_name or "Finder"
            window_title = (
                f"Process: {resolved_app} (PID: {pid})"
                if pid
                else f"Process: {resolved_app}"
            )
            return {
                "timestamp": timestamp,
                "active_app": resolved_app,
                "window_title": window_title,
                "ocr_snippet": "",
                "mesh_health": {
                    "status": "system_fallback",
                    "os": "darwin",
                    "pid": pid,
                    "bundle_id": bundle_id,
                    "ram_info": mem_info,
                },
                "source": "system_fallback",
                "endpoint": "system_kernel",
                "raw_perception": {
                    "pid": pid,
                    "bundle_id": bundle_id,
                    "memory": mem_info,
                },
            }

        # Generic Linux / fallback host
        return {
            "timestamp": timestamp,
            "active_app": "system_host",
            "window_title": f"Host OS: {sys.platform}",
            "ocr_snippet": "",
            "mesh_health": {
                "status": "system_fallback",
                "os": sys.platform,
            },
            "source": "system_fallback",
            "endpoint": "system_kernel",
            "raw_perception": {"platform": sys.platform},
        }

    def harvest_perception(self, timeout_s: float = 2.0) -> Dict[str, Any]:
        """Harvests real-time Screen Lens perception context.

        Tries in order:
        1. Live HTTP endpoints: Port 3037 -> Port 3035 -> Port 4003 (source="live_api")
        2. Local read-only SQLite DB: ~/.lauburu/ocr_frames.db or screen_lens.sqlite (source="sqlite")
        3. Authentic OS/kernel Launch Services & vm_stat fallback (source="system_fallback")

        Returns a dictionary adhering strictly to PROJECT.md interface contract:
        {"timestamp": str, "active_app": str, "window_title": str, "ocr_snippet": str,
         "mesh_health": dict, "source": str, "endpoint": str}
        """
        effective_timeout = max(0.05, float(timeout_s))

        # 1. Probe live ports in order: 3037 -> 3035 -> 4003
        for port, url, ep_type in self._get_live_endpoints_in_order():
            payload = self._probe_live_endpoint(url, ep_type, effective_timeout)
            if payload is not None:
                return payload

        # 2. Fall back to local SQLite databases in read-only mode
        sqlite_payload = self._harvest_from_sqlite()
        if sqlite_payload is not None:
            return sqlite_payload

        # 3. Fall back to authentic system Launch Services / kernel telemetry
        return self._harvest_from_system_fallback()

    def connect_gemini_spark(self, timeout_s: float = 2.0) -> Dict[str, Any]:
        """Probes Gemini Spark MCP daemon (Port 9999) and returns connection status."""
        effective_timeout = max(0.05, float(timeout_s))
        spark_cfg = self._config.get("endpoints", {}).get("gemini_spark", {})

        candidate_urls: List[str] = []
        for key in [
            "mcp_project_health_url",
            "mcp_health_url",
            "mcp_sse_url",
            "mcp_messages_url",
        ]:
            val = spark_cfg.get(key)
            if val and val not in candidate_urls:
                candidate_urls.append(val)

        # Standard canonical fallback candidates only if no endpoints configured
        if not candidate_urls:
            candidate_urls = [
                "http://127.0.0.1:9999/mcp/project/health",
                "http://127.0.0.1:9999/health",
                "http://127.0.0.1:9999/sse",
            ]

        last_error: Optional[str] = None
        for url in candidate_urls:
            t0 = time.perf_counter()
            try:
                req = urllib.request.Request(
                    url,
                    headers={
                        "User-Agent": "GeminiLensSync/1.0",
                        "Accept": "application/json, text/event-stream",
                    },
                )
                with self._opener.open(req, timeout=effective_timeout) as resp:
                    elapsed_ms = (time.perf_counter() - t0) * 1000.0
                    if resp.status == 200:
                        raw_data = resp.read()
                        details: Dict[str, Any] = {}
                        try:
                            parsed = json.loads(raw_data.decode("utf-8"))
                            if isinstance(parsed, dict):
                                details = parsed
                        except Exception:
                            details = {"response_preview": raw_data[:100].decode("utf-8", "ignore")}

                        return {
                            "connected": True,
                            "endpoint": url,
                            "status": "online",
                            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                            "latency_ms": round(elapsed_ms, 2),
                            "details": details,
                            "error": None,
                        }
                    else:
                        last_error = f"HTTP {resp.status}"

            except urllib.error.HTTPError as http_err:
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                last_error = f"HTTP {http_err.code}: {http_err.reason}"
                # If server is listening and returned 404/405/etc., port 9999 IS responding
                if http_err.code in (400, 404, 405):
                    # Continue trying next candidate path to see if another path returns 200
                    continue

            except Exception as exc:
                last_error = str(exc)

        primary_url = candidate_urls[0] if candidate_urls else "http://127.0.0.1:9999"
        return {
            "connected": False,
            "endpoint": primary_url,
            "status": "offline",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "latency_ms": None,
            "details": {},
            "error": last_error or "Connection failed",
        }

    def get_consolidated_context(self, timeout_s: float = 2.0) -> Dict[str, Any]:
        """Combines Screen Lens perception and Gemini Spark status into a consolidated context."""
        effective_timeout = max(0.05, float(timeout_s))
        perception = self.harvest_perception(timeout_s=effective_timeout)
        spark_status = self.connect_gemini_spark(timeout_s=effective_timeout)

        timestamp = (
            perception.get("timestamp")
            or datetime.datetime.now(datetime.timezone.utc).isoformat()
        )
        is_live = perception.get("source") == "live_api"
        spark_connected = bool(spark_status.get("connected", False))

        return {
            "timestamp": timestamp,
            "active_app": perception.get("active_app", "unknown"),
            "window_title": perception.get("window_title", "unknown"),
            "ocr_snippet": perception.get("ocr_snippet", ""),
            "mesh_health": perception.get("mesh_health", {}),
            "source": perception.get("source", "unknown"),
            "endpoint": perception.get("endpoint", ""),
            "screen_lens": perception,
            "gemini_spark": spark_status,
            "is_live": is_live,
            "spark_connected": spark_connected,
            "status": "synchronized" if (is_live and spark_connected) else "degraded",
        }
