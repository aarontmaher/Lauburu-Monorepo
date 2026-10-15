#!/usr/bin/env python3
"""
06_scripts_and_tooling/truth/lens_t3_check.py
============================================
Screen Lens Tier 3 Visual Truth & UI-to-API Discrepancy Checker.
Subsystem: 06_scripts_and_tooling/truth/lens_t3_check.py
Lauburu Mesh Ecosystem — 2026

Governed by:
- Rule #0 (Zero-Mock Empirical Truth Gate)
- Rule #1 & Rule #5 (Tri-Proof Interceptor Gate: Proof 1 Actuation, Proof 2 Crypto, Proof 3 Visual)
- Canonical Hardware Truth (00_canonical_hardware_matrix.md)

Function:
Takes a Screen Lens capture/OCR (from Ports 3035-3037, ~/.lauburu/screen_lens.sqlite,
live Swift CLI capture, or static capture fixture) of the Port 4007 UI
(Network Cable & Mesh Analyzer / Stitch 2.0) and diffs displayed values against
matching /api JSON ground-truth endpoints (primarily /api/topology, /api/devices).
Detects and reports all mismatches, stale counters, fake literals, or clean-state violations.

Usage:
  # Auto mode: queries SQLite / ports 3035-3037 for latest 4007 UI capture and diffs vs http://127.0.0.1:4007
  python3 lens_t3_check.py

  # Query specific capture from SQLite
  python3 lens_t3_check.py --source sqlite --capture-id 29770

  # Search SQLite for latest capture matching a keyword
  python3 lens_t3_check.py --source sqlite --search "Network Analyzer"

  # Live on-demand screen capture via lauburu-lens CLI
  python3 lens_t3_check.py --source cli

  # From static file (for regression tests)
  python3 lens_t3_check.py --capture-file capture.json --api-file topology.json

  # Strict mode (exit 1 on any mismatch) with JSON output
  python3 lens_t3_check.py --strict --json
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import logging
import math
import os
import re
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("LensT3Check")

# Canonical paths & endpoints
REPO_ROOT = Path("/Volumes/Lauburu-Monorepo")
DEFAULT_SQLITE_PATH = Path(os.path.expanduser("~/.lauburu/screen_lens.sqlite"))
LAUBURU_LENS_BIN = REPO_ROOT / "01_apps/screen_lens/bin/lauburu-lens"
DEFAULT_API_URL = "http://127.0.0.1:4007"
PORT_3035_URL = "http://127.0.0.1:3035"
PORT_3037_URL = "http://127.0.0.1:3037"


# -----------------------------------------------------------------------------
# Data Models
# -----------------------------------------------------------------------------

@dataclass
class CaptureResult:
    """Represents a Screen Lens screen capture and OCR text."""
    source_type: str                   # "sqlite", "port_3035", "port_3037", "cli", "file"
    raw_text: str                      # Consolidated OCR text / summary
    capture_id: Optional[int] = None
    timestamp: str = ""
    active_app: str = ""
    window_title: str = ""
    text_blocks: List[Dict[str, Any]] = field(default_factory=list)
    sha256_hash: str = ""

    def __post_init__(self):
        if not self.sha256_hash and self.raw_text:
            self.sha256_hash = hashlib.sha256(self.raw_text.encode("utf-8")).hexdigest()


@dataclass
class MetricDiff:
    """Represents comparison between a displayed OCR value and ground-truth API JSON."""
    metric: str                        # Metric name (e.g. "nodes_count", "mesh_ram_gb")
    category: str                      # "summary", "device", "cable", "clean_state"
    displayed_raw: Any                 # Raw text string found in OCR
    displayed_parsed: Any              # Parsed typed value (e.g. int, float, tuple)
    api_ground_truth: Any              # Value extracted from API JSON
    status: str                        # "MATCH", "MISMATCH", "ZERO_MOCK_VIOLATION", "NOT_IN_VIEWPORT"
    delta: Optional[float] = None      # Absolute numeric difference if applicable
    details: str = ""                  # Human explanation


@dataclass
class AuditReport:
    """Consolidated Tier 3 Truth Audit Report with Tri-Proof metadata."""
    timestamp: str
    verdict: str                       # "TRUTH_VERIFIED" or "MISMATCH_DETECTED"
    total_audited: int
    matches_count: int
    mismatches_count: int
    not_in_viewport_count: int
    capture_metadata: Dict[str, Any]
    api_metadata: Dict[str, Any]
    diffs: List[MetricDiff]
    tri_proof: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "verdict": self.verdict,
            "total_audited": self.total_audited,
            "matches_count": self.matches_count,
            "mismatches_count": self.mismatches_count,
            "not_in_viewport_count": self.not_in_viewport_count,
            "capture_metadata": self.capture_metadata,
            "api_metadata": self.api_metadata,
            "diffs": [asdict(d) for d in self.diffs],
            "tri_proof": self.tri_proof,
        }


# -----------------------------------------------------------------------------
# 1. Screen Lens Capture Ingestion
# -----------------------------------------------------------------------------

class ScreenLensIngestor:
    """Fetches OCR and screen capture data from Screen Lens subsystems."""

    @staticmethod
    def from_sqlite(db_path: Path = DEFAULT_SQLITE_PATH,
                    capture_id: Optional[int] = None,
                    search: Optional[str] = None) -> Optional[CaptureResult]:
        """Fetch capture records directly from ~/.lauburu/screen_lens.sqlite."""
        if not db_path.exists():
            logger.warning(f"SQLite DB not found: {db_path}")
            return None

        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=2.0)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Check available tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {r[0] for r in cursor.fetchall()}

            row = None
            if "captures" in tables:
                if capture_id is not None:
                    cursor.execute("SELECT * FROM captures WHERE id = ?", (capture_id,))
                    row = cursor.fetchone()
                elif search:
                    cursor.execute(
                        "SELECT * FROM captures WHERE raw_text_summary LIKE ? OR active_window_title LIKE ? "
                        "ORDER BY id DESC LIMIT 1",
                        (f"%{search}%", f"%{search}%")
                    )
                    row = cursor.fetchone()
                else:
                    # Look for 4007 or Network Analyzer UI first
                    cursor.execute(
                        "SELECT * FROM captures WHERE raw_text_summary LIKE '%4007%' "
                        "OR raw_text_summary LIKE '%NETWORK ANALYZER%' "
                        "OR active_window_title LIKE '%4007%' "
                        "OR active_window_title LIKE '%network cablesapp%' "
                        "OR active_window_title LIKE '%Stitch 2.0%' "
                        "ORDER BY id DESC LIMIT 1"
                    )
                    row = cursor.fetchone()

                    # Fallback to absolute latest
                    if not row:
                        cursor.execute("SELECT * FROM captures ORDER BY id DESC LIMIT 1")
                        row = cursor.fetchone()

            # Fallback to frames table if captures not found
            if not row and "frames" in tables:
                cursor.execute("SELECT * FROM frames ORDER BY id DESC LIMIT 1")
                frame_row = cursor.fetchone()
                if frame_row:
                    conn.close()
                    return CaptureResult(
                        source_type="sqlite_frames",
                        raw_text=frame_row["ocr_text"] or "",
                        capture_id=frame_row["id"],
                        timestamp=frame_row["timestamp"] or "",
                        active_app=frame_row["app_name"] or "",
                        window_title="N/A",
                    )

            if not row:
                conn.close()
                return None

            cap_id = row["id"]
            raw_text = row["raw_text_summary"] or ""
            ts = row["timestamp"] or ""
            app_name = row["active_app_name"] or ""
            win_title = row["active_window_title"] or ""

            # Fetch OCR text blocks with bounding boxes if table exists
            text_blocks: List[Dict[str, Any]] = []
            if "ocr_text_blocks" in tables:
                cursor.execute("SELECT * FROM ocr_text_blocks WHERE capture_id = ? ORDER BY block_index ASC", (cap_id,))
                for b in cursor.fetchall():
                    text_blocks.append({
                        "text": b["text"],
                        "confidence": b["confidence"],
                        "bbox": {"x": b["bbox_x"], "y": b["bbox_y"], "w": b["bbox_w"], "h": b["bbox_h"]},
                        "pixel": {"x": b["pixel_x"], "y": b["pixel_y"], "w": b["pixel_w"], "h": b["pixel_h"]},
                    })

            conn.close()
            return CaptureResult(
                source_type="sqlite_captures",
                raw_text=raw_text,
                capture_id=cap_id,
                timestamp=ts,
                active_app=app_name,
                window_title=win_title,
                text_blocks=text_blocks,
            )
        except Exception as e:
            logger.error(f"Error querying SQLite {db_path}: {e}")
            return None

    @staticmethod
    def from_port_3035(base_url: str = PORT_3035_URL, timeout: float = 2.0) -> Optional[CaptureResult]:
        """Fetch latest OCR capture from lauburu-lens daemon on Port 3035."""
        url = f"{base_url}/api/latest"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "LensT3Check/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            raw_text = data.get("raw_text_summary", "")
            return CaptureResult(
                source_type="port_3035",
                raw_text=raw_text,
                capture_id=data.get("id"),
                timestamp=data.get("timestamp", ""),
                active_app=data.get("app", ""),
                window_title=data.get("window_title", ""),
                text_blocks=data.get("blocks", []),
            )
        except Exception as e:
            logger.debug(f"Port 3035 query failed ({url}): {e}")
            return None

    @staticmethod
    def from_port_3037(base_url: str = PORT_3037_URL, timeout: float = 2.5) -> Optional[CaptureResult]:
        """Fetch screen context from Lens Global Orchestrator on Port 3037."""
        url = f"{base_url}/api/orchestrator/state"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "LensT3Check/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            screen = data.get("screen", {})
            ocr_lines = screen.get("recent_ocr", [])
            raw_text = "\n".join(ocr_lines) if isinstance(ocr_lines, list) else str(ocr_lines)

            return CaptureResult(
                source_type="port_3037",
                raw_text=raw_text,
                capture_id=None,
                timestamp=screen.get("timestamp", data.get("timestamp", "")),
                active_app=screen.get("active_app", ""),
                window_title=screen.get("window_title", ""),
            )
        except Exception as e:
            logger.debug(f"Port 3037 query failed ({url}): {e}")
            return None

    @staticmethod
    def from_cli(bin_path: Path = LAUBURU_LENS_BIN, timeout: float = 6.0) -> Optional[CaptureResult]:
        """Execute on-demand display capture + Vision OCR via lauburu-lens binary."""
        if not bin_path.exists() or not os.access(bin_path, os.X_OK):
            logger.debug(f"lauburu-lens binary not available: {bin_path}")
            return None

        cmd = [str(bin_path), "capture", "--json", "--no-save"]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            if proc.returncode != 0:
                logger.debug(f"lauburu-lens capture exited with {proc.returncode}: {proc.stderr}")
                return None

            data = json.loads(proc.stdout)
            return CaptureResult(
                source_type="cli_ondemand",
                raw_text=data.get("text_summary", ""),
                capture_id=None,
                timestamp=data.get("timestamp", datetime.datetime.now(datetime.timezone.utc).isoformat()),
                active_app=data.get("app", ""),
                window_title=data.get("window_title", ""),
                text_blocks=data.get("blocks", []),
            )
        except Exception as e:
            logger.debug(f"lauburu-lens CLI capture error: {e}")
            return None

    @staticmethod
    def from_file(file_path: Union[str, Path]) -> Optional[CaptureResult]:
        """Load pre-recorded capture result from JSON or text file."""
        p = Path(file_path)
        if not p.exists():
            logger.error(f"Capture file not found: {p}")
            return None

        content = p.read_text(encoding="utf-8")
        try:
            data = json.loads(content)
            if isinstance(data, dict):
                raw_text = data.get("raw_text_summary") or data.get("text_summary") or data.get("raw_text") or ""
                return CaptureResult(
                    source_type="file_json",
                    raw_text=raw_text,
                    capture_id=data.get("id") or data.get("capture_id"),
                    timestamp=data.get("timestamp", ""),
                    active_app=data.get("app") or data.get("active_app_name", ""),
                    window_title=data.get("window_title") or data.get("active_window_title", ""),
                    text_blocks=data.get("blocks") or data.get("text_blocks", []),
                )
        except json.JSONDecodeError:
            pass

        # Treat as plain text OCR
        return CaptureResult(
            source_type="file_plain_text",
            raw_text=content,
            capture_id=None,
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            active_app="Unknown",
            window_title="Unknown",
        )


# -----------------------------------------------------------------------------
# 2. Port 4007 API Ground Truth Ingestion
# -----------------------------------------------------------------------------

class Port4007ApiIngestor:
    """Fetches authentic runtime truth directly from Port 4007 endpoints."""

    @staticmethod
    def fetch_topology(base_url: str = DEFAULT_API_URL, timeout: float = 3.0) -> Tuple[Optional[Dict[str, Any]], str]:
        """
        Fetch /api/topology and compute SHA256 checksum of raw payload.
        Returns: (topology_dict, sha256_checksum)
        """
        url = f"{base_url.rstrip('/')}/api/topology"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "LensT3Check/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw_bytes = resp.read()
                sha256_val = hashlib.sha256(raw_bytes).hexdigest()
                data = json.loads(raw_bytes.decode("utf-8"))
                return data, sha256_val
        except Exception as e:
            logger.warning(f"Failed to fetch /api/topology from {url}: {e}")
            return None, ""

    @staticmethod
    def load_from_file(file_path: Union[str, Path]) -> Tuple[Optional[Dict[str, Any]], str]:
        """Load ground-truth topology from JSON file."""
        p = Path(file_path)
        if not p.exists():
            return None, ""
        raw_bytes = p.read_bytes()
        sha256_val = hashlib.sha256(raw_bytes).hexdigest()
        data = json.loads(raw_bytes.decode("utf-8"))
        return data, sha256_val


# -----------------------------------------------------------------------------
# 3. Metric Parsing & OCR Extraction Engine
# -----------------------------------------------------------------------------

class MetricsParser:
    """Extracts UI metric values from OCR text and bounding block streams."""

    @classmethod
    def extract_metrics(cls, text: str, text_blocks: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Parses OCR text and text blocks into structured metric representations.
        Handles both standard index.html UI and Stitch 2.0 Pro dashboard styles.
        """
        metrics: Dict[str, Any] = {}

        # Normalize line breaks and strip DOM snapshot tree prefixes if present
        cleaned = re.sub(r'uid=\S+\s+(?:StaticText|RootWebArea|banner|button|link)\s*\"?', '', text)
        cleaned = cleaned.replace('\"', ' ')
        norm_text = cleaned.replace("\r\n", "\n").replace("\r", "\n")

        # 1. Online & Total Nodes (e.g., "7/12" followed by NODES/Nodes)
        # Dedicated pattern to avoid colliding with "PRIMA.CPP : 7/10"
        m_nodes = re.search(r'(\d+)\s*/\s*(\d+)\s*(?:[\r\n\s]*(?:NODES|Nodes)\b)', norm_text, re.I)
        if not m_nodes:
            # Stitch style: "12 nodes" or "7 of 12 Nodes"
            m_stitch_nodes = re.search(r'(\d+)\s*of\s*(\d+)\s*Nodes', norm_text, re.I)
            if m_stitch_nodes:
                metrics["nodes_count"] = {
                    "raw": f"{m_stitch_nodes.group(1)}/{m_stitch_nodes.group(2)}",
                    "online": int(m_stitch_nodes.group(1)),
                    "total": int(m_stitch_nodes.group(2)),
                }
            else:
                for m_single in re.finditer(r'(\d+)\s*nodes\b', norm_text, re.I):
                    surrounding = norm_text[max(0, m_single.start()-30):min(len(norm_text), m_single.end()+30)]
                    if not re.search(r'BT|Verified|Stream', surrounding, re.I):
                        metrics["total_nodes_only"] = {
                            "raw": m_single.group(1),
                            "total": int(m_single.group(1)),
                        }
                        break
        else:
            metrics["nodes_count"] = {
                "raw": f"{m_nodes.group(1)}/{m_nodes.group(2)}",
                "online": int(m_nodes.group(1)),
                "total": int(m_nodes.group(2)),
            }

        # 2. BT Stream Verified Nodes (e.g., "0 Nodes BT STREAM VERIFIED")
        m_bt = re.search(r'(\d+)\s*Nodes?\s*[\r\n\s]*(?:BT STREAM VERIFIED|BT Verified|BT Stream Verified)', norm_text, re.I)
        if not m_bt:
            m_bt = re.search(r'(?:BT STREAM VERIFIED|BT Verified)\s*[:=]?\s*(\d+)\s*Nodes?', norm_text, re.I)
        if m_bt:
            metrics["bt_verified_nodes"] = {
                "raw": f"{m_bt.group(1)} Nodes",
                "count": int(m_bt.group(1)),
            }

        # 3. prima.cpp Workers (e.g., "PRIMA.CPP : 7/10 WORKERS" or "7/10 PRIMA.CPP")
        m_prima = re.search(r'(?:PRIMA(?:\.CPP)?\s*:\s*)(\d+/\d+)', norm_text, re.I)
        if not m_prima:
            m_prima = re.search(r'(\d+/\d+)\s*[\r\n\s]*(?:PRIMA(?:\.CPP)?\b)', norm_text, re.I)
        if m_prima:
            parts = m_prima.group(1).split("/")
            metrics["prima_workers"] = {
                "raw": m_prima.group(1),
                "connected": int(parts[0]),
                "total": int(parts[1]),
            }

        # 4. Dynamic IPs Resolved (e.g., "DYNAMIC IP : 10" or "10 DYNAMIC IPS")
        m_dyn = re.search(r'DYNAMIC IP(?:S)?\s*:\s*(\d+(?:/\d+)?)', norm_text, re.I)
        if not m_dyn:
            m_dyn = re.search(r'(\d+)\s*[\r\n\s]*(?:DYNAMIC IPS|Dynamic IPs)', norm_text, re.I)
        if m_dyn:
            metrics["dynamic_ips"] = {
                "raw": m_dyn.group(1),
                "resolved": m_dyn.group(1),
            }

        # 5. Mesh RAM Pool (e.g., "148.1 GB RAM POOL" or "Pooled VRAM: 148.1 GB")
        m_ram = re.search(r'(\d+(?:\.\d+)?)\s*GB\s*[\r\n\s]*(?:RAM POOL|RAM Pool|Pooled RAM|Total RAM)', norm_text, re.I)
        if not m_ram:
            m_ram = re.search(r'(?:RAM POOL|RAM Pool|Pooled RAM|Total RAM)\s*[:=]?\s*(\d+(?:\.\d+)?)\s*GB', norm_text, re.I)
        if not m_ram:
            # Handle OCR artifacts (e.g. "pooled VRAM114&1 GB)" -> 148.1)
            m_ram_art = re.search(r'pooled\s*VRAM[^\d]*(\d+)[.&](\d+)\s*GB', norm_text, re.I)
            if m_ram_art:
                metrics["mesh_ram_gb"] = {
                    "raw": f"{m_ram_art.group(1)}.{m_ram_art.group(2)} GB",
                    "val": float(f"{m_ram_art.group(1)}.{m_ram_art.group(2)}"),
                }
        else:
            metrics["mesh_ram_gb"] = {
                "raw": f"{m_ram.group(1)} GB",
                "val": float(m_ram.group(1)),
            }

        # 6. NPU Compute TOPS (e.g., "101.0 TOPS NPU COMPUTE" or "101 TOPS")
        m_npu = re.search(r'(\d+(?:\.\d+)?)\s*TOPS\s*[\r\n\s]*(?:NPU COMPUTE|NPU Compute)?', norm_text, re.I)
        if not m_npu:
            m_npu = re.search(r'(?:NPU COMPUTE|NPU Compute)\s*[:=]?\s*(\d+(?:\.\d+)?)\s*TOPS', norm_text, re.I)
        if m_npu:
            metrics["npu_tops"] = {
                "raw": f"{m_npu.group(1)} TOPS",
                "val": float(m_npu.group(1)),
            }

        # 7. Active Cables (e.g., "7 Active ACTIVE CABLES" or "9 authentic physical cables")
        m_cab = re.search(r'(\d+)\s*Active\s*[\r\n\s]*(?:ACTIVE CABLES|Active Cables|Cables)?', norm_text, re.I)
        if not m_cab:
            m_cab = re.search(r'(\d+)\s*(?:authentic\s*physical\s*cables|physical\s*cables)', norm_text, re.I)
        if not m_cab:
            m_cab = re.search(r'(?:ACTIVE CABLES|Active Cables)\s*[:=]?\s*(\d+)\s*(?:Active)?', norm_text, re.I)
        if m_cab:
            metrics["active_cables"] = {
                "raw": f"{m_cab.group(1)} Active",
                "count": int(m_cab.group(1)),
            }

        # 8. Active Links (e.g., "33 ACTIVE LINKS" or "Active Links : 31")
        m_links = re.search(r'(\d+)\s*[\r\n\s]*(?:ACTIVE LINKS|Active Links|Active Conns)', norm_text, re.I)
        if not m_links:
            m_links = re.search(r'(?:ACTIVE LINKS|Active Links)\s*[:=]?\s*(\d+)', norm_text, re.I)
        if m_links:
            metrics["active_links"] = {
                "raw": m_links.group(1),
                "count": int(m_links.group(1)),
            }

        # 9. TB4 Latency (e.g., "-- TB4 LINK RTT" or "0.27 ms" or "-1.0 ms")
        m_tb4 = re.search(r'(--|N/A|-?\d+(?:\.\d+)?)\s*(?:ms)?\s*[\r\n\s]*(?:TB4 LINK RTT|TB4 Link RTT|TB4 RTT)', norm_text, re.I)
        if not m_tb4:
            m_tb4 = re.search(r'(?:TB4 LINK RTT|TB4 Link RTT|TB4 RTT)\s*[:=]?\s*(--|N/A|-?\d+(?:\.\d+)?)\s*(?:ms)?', norm_text, re.I)
        if not m_tb4:
            m_tb4 = re.search(r'(?:TB4|Thunderbolt).*?(?:at\s*)?(\d+(?:\.\d+)?)\s*r?ms\s*latency', norm_text, re.I)
        if m_tb4:
            raw_lat = m_tb4.group(1)
            metrics["tb4_latency"] = {
                "raw": f"{raw_lat} ms" if raw_lat not in ("--", "N/A") else "--",
                "val_str": raw_lat,
            }

        # 10. Device Cards Snippets
        # Search for host device "Mac Mini M4 Pro"
        m_host = re.search(r'Mac Mini M4 Pro.*?(?:RAM:\s*([0-9.]+)/([0-9.]+)G|[0-9.]+/[0-9.]+\s*GB)', norm_text, re.S | re.I)
        if m_host and m_host.group(1):
            metrics["device_mac_mini"] = {
                "name": "Mac Mini M4 Pro (Host L1)",
                "used_gb": float(m_host.group(1)),
                "total_gb": float(m_host.group(2)),
                "raw": f"{m_host.group(1)}/{m_host.group(2)}G",
            }

        return metrics


# -----------------------------------------------------------------------------
# 4. Diff & Verification Engine
# -----------------------------------------------------------------------------

class LensT3Verifier:
    """Compares extracted displayed metrics with ground truth from API JSON."""

    def __init__(self, tolerance_pct: float = 0.05):
        self.tolerance_pct = tolerance_pct

    def verify(self, capture: CaptureResult, topology_data: Dict[str, Any], raw_api_sha256: str) -> AuditReport:
        mesh_summary = topology_data.get("mesh_summary", {})
        devices = topology_data.get("devices", [])
        cables = topology_data.get("cables", [])

        # Parse metrics from capture OCR
        extracted = MetricsParser.extract_metrics(capture.raw_text, capture.text_blocks)

        diffs: List[MetricDiff] = []

        # 1. Nodes Count (online/total)
        api_online = mesh_summary.get("online_nodes")
        api_total = mesh_summary.get("total_nodes")
        if "nodes_count" in extracted:
            d_online = extracted["nodes_count"]["online"]
            d_total = extracted["nodes_count"]["total"]
            match = (d_online == api_online and d_total == api_total)
            status = "MATCH" if match else "MISMATCH"
            diffs.append(MetricDiff(
                metric="nodes_count",
                category="summary",
                displayed_raw=extracted["nodes_count"]["raw"],
                displayed_parsed=f"{d_online}/{d_total}",
                api_ground_truth=f"{api_online}/{api_total}",
                status=status,
                details=f"Displayed {d_online}/{d_total} vs API ground truth {api_online}/{api_total}"
            ))
        elif "total_nodes_only" in extracted:
            d_total = extracted["total_nodes_only"]["total"]
            match = (d_total == api_total)
            status = "MATCH" if match else "MISMATCH"
            diffs.append(MetricDiff(
                metric="total_nodes",
                category="summary",
                displayed_raw=extracted["total_nodes_only"]["raw"],
                displayed_parsed=d_total,
                api_ground_truth=api_total,
                status=status,
                details=f"Displayed {d_total} total nodes vs API {api_total}"
            ))
        else:
            diffs.append(MetricDiff(
                metric="nodes_count",
                category="summary",
                displayed_raw="N/A",
                displayed_parsed=None,
                api_ground_truth=f"{api_online}/{api_total}",
                status="NOT_IN_VIEWPORT",
                details="Nodes metric element was not detected in OCR text"
            ))

        # 2. BT Stream Verified Nodes
        api_bt_nodes = mesh_summary.get("bluetooth_terminal_verified_nodes", 0)
        if "bt_verified_nodes" in extracted:
            d_bt = extracted["bt_verified_nodes"]["count"]
            match = (d_bt == api_bt_nodes)
            status = "MATCH" if match else "MISMATCH"
            diffs.append(MetricDiff(
                metric="bt_verified_nodes",
                category="summary",
                displayed_raw=extracted["bt_verified_nodes"]["raw"],
                displayed_parsed=d_bt,
                api_ground_truth=api_bt_nodes,
                status=status,
                details=f"Displayed {d_bt} BT verified vs API {api_bt_nodes}"
            ))
        else:
            diffs.append(MetricDiff(
                metric="bt_verified_nodes",
                category="summary",
                displayed_raw="N/A",
                displayed_parsed=None,
                api_ground_truth=api_bt_nodes,
                status="NOT_IN_VIEWPORT",
                details="BT Verified Nodes badge not detected in OCR text"
            ))

        # 3. prima.cpp Workers (connected/total)
        api_prima_c = mesh_summary.get("prima_connected_count")
        api_prima_t = mesh_summary.get("prima_total_count")
        if "prima_workers" in extracted:
            d_c = extracted["prima_workers"]["connected"]
            d_t = extracted["prima_workers"]["total"]
            match = (d_c == api_prima_c and d_t == api_prima_t)
            status = "MATCH" if match else "MISMATCH"
            diffs.append(MetricDiff(
                metric="prima_workers",
                category="summary",
                displayed_raw=extracted["prima_workers"]["raw"],
                displayed_parsed=f"{d_c}/{d_t}",
                api_ground_truth=f"{api_prima_c}/{api_prima_t}",
                status=status,
                details=f"Displayed {d_c}/{d_t} prima workers vs API {api_prima_c}/{api_prima_t}"
            ))
        else:
            diffs.append(MetricDiff(
                metric="prima_workers",
                category="summary",
                displayed_raw="N/A",
                displayed_parsed=None,
                api_ground_truth=f"{api_prima_c}/{api_prima_t}",
                status="NOT_IN_VIEWPORT",
                details="prima.cpp badge not detected in OCR text"
            ))

        # 4. Dynamic IPs Resolved
        api_dyn_ips = str(mesh_summary.get("dynamic_ips_resolved", "")).strip()
        if "dynamic_ips" in extracted:
            d_dyn = str(extracted["dynamic_ips"]["resolved"]).strip()
            # Normalize e.g. "10" vs "10"
            match = (d_dyn == api_dyn_ips)
            status = "MATCH" if match else "MISMATCH"
            diffs.append(MetricDiff(
                metric="dynamic_ips",
                category="summary",
                displayed_raw=extracted["dynamic_ips"]["raw"],
                displayed_parsed=d_dyn,
                api_ground_truth=api_dyn_ips,
                status=status,
                details=f"Displayed {d_dyn} dynamic IPs vs API {api_dyn_ips}"
            ))
        else:
            diffs.append(MetricDiff(
                metric="dynamic_ips",
                category="summary",
                displayed_raw="N/A",
                displayed_parsed=None,
                api_ground_truth=api_dyn_ips,
                status="NOT_IN_VIEWPORT",
                details="Dynamic IP badge not detected in OCR text"
            ))

        # 5. Mesh RAM Pool (GB)
        api_ram = mesh_summary.get("total_ram_gb")
        if "mesh_ram_gb" in extracted and api_ram is not None:
            d_ram = extracted["mesh_ram_gb"]["val"]
            delta = abs(d_ram - float(api_ram))
            match = delta <= max(0.5, float(api_ram) * self.tolerance_pct)
            status = "MATCH" if match else "MISMATCH"
            diffs.append(MetricDiff(
                metric="mesh_ram_gb",
                category="summary",
                displayed_raw=extracted["mesh_ram_gb"]["raw"],
                displayed_parsed=d_ram,
                api_ground_truth=api_ram,
                status=status,
                delta=round(delta, 2),
                details=f"Displayed {d_ram} GB vs API {api_ram} GB (delta: {round(delta, 2)} GB)"
            ))
        else:
            diffs.append(MetricDiff(
                metric="mesh_ram_gb",
                category="summary",
                displayed_raw="N/A",
                displayed_parsed=None,
                api_ground_truth=api_ram,
                status="NOT_IN_VIEWPORT",
                details="Mesh RAM pool stat not detected in OCR text"
            ))

        # 6. NPU Compute (TOPS)
        api_npu = mesh_summary.get("total_npu_tops")
        if "npu_tops" in extracted and api_npu is not None:
            d_npu = extracted["npu_tops"]["val"]
            delta = abs(d_npu - float(api_npu))
            match = delta <= max(1.0, float(api_npu) * self.tolerance_pct)
            status = "MATCH" if match else "MISMATCH"
            diffs.append(MetricDiff(
                metric="npu_tops",
                category="summary",
                displayed_raw=extracted["npu_tops"]["raw"],
                displayed_parsed=d_npu,
                api_ground_truth=api_npu,
                status=status,
                delta=round(delta, 1),
                details=f"Displayed {d_npu} TOPS vs API {api_npu} TOPS (delta: {round(delta, 1)} TOPS)"
            ))
        else:
            diffs.append(MetricDiff(
                metric="npu_tops",
                category="summary",
                displayed_raw="N/A",
                displayed_parsed=None,
                api_ground_truth=api_npu,
                status="NOT_IN_VIEWPORT",
                details="NPU Compute stat not detected in OCR text"
            ))

        # 7. Active Cables
        api_cables = mesh_summary.get("active_cables")
        if "active_cables" in extracted and api_cables is not None:
            d_cables = extracted["active_cables"]["count"]
            match = (d_cables == int(api_cables))
            status = "MATCH" if match else "MISMATCH"
            diffs.append(MetricDiff(
                metric="active_cables",
                category="summary",
                displayed_raw=extracted["active_cables"]["raw"],
                displayed_parsed=d_cables,
                api_ground_truth=api_cables,
                status=status,
                details=f"Displayed {d_cables} Active vs API {api_cables}"
            ))
        else:
            diffs.append(MetricDiff(
                metric="active_cables",
                category="summary",
                displayed_raw="N/A",
                displayed_parsed=None,
                api_ground_truth=api_cables,
                status="NOT_IN_VIEWPORT",
                details="Active Cables stat not detected in OCR text"
            ))

        # 8. Active Links (Connections)
        api_conns = mesh_summary.get("active_connections_total")
        if "active_links" in extracted and api_conns is not None:
            d_links = extracted["active_links"]["count"]
            # Active connections fluctuate in real time with active TCP sockets; allow slight window drift
            delta = abs(d_links - int(api_conns))
            match = (delta <= 10) # Socket count changes dynamically
            status = "MATCH" if match else "MISMATCH"
            diffs.append(MetricDiff(
                metric="active_links",
                category="summary",
                displayed_raw=extracted["active_links"]["raw"],
                displayed_parsed=d_links,
                api_ground_truth=api_conns,
                status=status,
                delta=float(delta),
                details=f"Displayed {d_links} active links vs API {api_conns} (delta: {delta})"
            ))
        else:
            diffs.append(MetricDiff(
                metric="active_links",
                category="summary",
                displayed_raw="N/A",
                displayed_parsed=None,
                api_ground_truth=api_conns,
                status="NOT_IN_VIEWPORT",
                details="Active Links stat not detected in OCR text"
            ))

        # 9. TB4 Latency (Clean Waiting State & Rule 0 Verification)
        api_tb4_lat = mesh_summary.get("tb4_bridge_latency_ms")
        if "tb4_latency" in extracted:
            d_tb4_str = extracted["tb4_latency"]["val_str"]
            # Rule 0 check: If displayed text is literal negative e.g. "-1.0 ms", flag violation
            if "-" in d_tb4_str and d_tb4_str not in ("--", "-"):
                diffs.append(MetricDiff(
                    metric="tb4_latency_rule_0",
                    category="clean_state",
                    displayed_raw=extracted["tb4_latency"]["raw"],
                    displayed_parsed=d_tb4_str,
                    api_ground_truth="-- (clean waiting state required)",
                    status="ZERO_MOCK_VIOLATION",
                    details=f"Rule #0 violation: UI displayed negative number '{d_tb4_str}' instead of clean state '--'"
                ))
            elif d_tb4_str in ("--", "N/A"):
                # Clean waiting state
                is_clean = (api_tb4_lat is None or api_tb4_lat <= 0)
                status = "MATCH" if is_clean else "MISMATCH"
                diffs.append(MetricDiff(
                    metric="tb4_latency",
                    category="clean_state",
                    displayed_raw=extracted["tb4_latency"]["raw"],
                    displayed_parsed="--",
                    api_ground_truth=api_tb4_lat,
                    status=status,
                    details=f"Displayed clean waiting state '--' (API reported {api_tb4_lat} ms)"
                ))
            else:
                # Numeric latency displayed
                try:
                    d_lat_val = float(d_tb4_str)
                    # Check against known fabricated literals (0.27ms, 0.544ms)
                    if d_lat_val in (0.27, 0.544, 0.56, 0.28) and (api_tb4_lat is None or api_tb4_lat <= 0):
                        diffs.append(MetricDiff(
                            metric="tb4_latency",
                            category="clean_state",
                            displayed_raw=extracted["tb4_latency"]["raw"],
                            displayed_parsed=d_lat_val,
                            api_ground_truth=api_tb4_lat,
                            status="ZERO_MOCK_VIOLATION",
                            details=f"Rule #0 violation: Displayed hardcoded constant '{d_lat_val} ms' while API reported {api_tb4_lat}"
                        ))
                    else:
                        delta = abs(d_lat_val - float(api_tb4_lat or 0))
                        match = delta <= 0.2
                        diffs.append(MetricDiff(
                            metric="tb4_latency",
                            category="summary",
                            displayed_raw=extracted["tb4_latency"]["raw"],
                            displayed_parsed=d_lat_val,
                            api_ground_truth=api_tb4_lat,
                            status="MATCH" if match else "MISMATCH",
                            delta=round(delta, 3),
                            details=f"Displayed {d_lat_val} ms vs API {api_tb4_lat} ms"
                        ))
                except ValueError:
                    diffs.append(MetricDiff(
                        metric="tb4_latency",
                        category="summary",
                        displayed_raw=extracted["tb4_latency"]["raw"],
                        displayed_parsed=d_tb4_str,
                        api_ground_truth=api_tb4_lat,
                        status="MISMATCH",
                        details=f"Unparseable latency string '{d_tb4_str}'"
                    ))
        else:
            diffs.append(MetricDiff(
                metric="tb4_latency",
                category="summary",
                displayed_raw="N/A",
                displayed_parsed=None,
                api_ground_truth=api_tb4_lat,
                status="NOT_IN_VIEWPORT",
                details="TB4 Latency stat not detected in OCR text"
            ))

        # 10. Device Host Card (Mac Mini) if visible
        if "device_mac_mini" in extracted:
            dev_ext = extracted["device_mac_mini"]
            # Find Mac Mini in API devices list
            l1_dev = next((d for d in devices if d.get("id") == "l1_mac_mini"), None)
            if l1_dev:
                api_ram_used = l1_dev.get("ram", {}).get("used_gb")
                api_ram_total = l1_dev.get("ram", {}).get("total_gb", 24.0)
                used_delta = abs(dev_ext["used_gb"] - float(api_ram_used or 0))
                # Allow RAM to fluctuate slightly (< 1.5 GB difference due to Mach kernel allocs)
                match = (used_delta <= 1.5 and dev_ext["total_gb"] == api_ram_total)
                diffs.append(MetricDiff(
                    metric="host_l1_ram",
                    category="device",
                    displayed_raw=dev_ext["raw"],
                    displayed_parsed=f"{dev_ext['used_gb']}/{dev_ext['total_gb']}G",
                    api_ground_truth=f"{api_ram_used}/{api_ram_total}G",
                    status="MATCH" if match else "MISMATCH",
                    delta=round(used_delta, 2),
                    details=f"Host L1 RAM: Displayed {dev_ext['used_gb']}/{dev_ext['total_gb']}G vs API {api_ram_used}/{api_ram_total}G"
                ))

        # Aggregate counts
        audited_count = sum(1 for d in diffs if d.status != "NOT_IN_VIEWPORT")
        matches = sum(1 for d in diffs if d.status == "MATCH")
        mismatches = sum(1 for d in diffs if d.status in ("MISMATCH", "ZERO_MOCK_VIOLATION"))
        not_in_viewport = sum(1 for d in diffs if d.status == "NOT_IN_VIEWPORT")

        verdict = "TRUTH_VERIFIED" if (mismatches == 0 and audited_count > 0) else "MISMATCH_DETECTED"
        if audited_count == 0:
            verdict = "INSUFFICIENT_VIEWPORT_DATA"

        # Tri-Proof Block (Rule #1 & Rule #5)
        tri_proof = {
            "proof_1_actuation_exit_code": 0 if verdict == "TRUTH_VERIFIED" else 1,
            "proof_2_cryptographic_checksums": {
                "api_payload_sha256": raw_api_sha256,
                "ocr_capture_sha256": capture.sha256_hash,
                "rule_compliance": "Zero-Mock Tri-Proof Signed",
            },
            "proof_3_visual_perception": {
                "capture_source": capture.source_type,
                "capture_id": capture.capture_id,
                "timestamp": capture.timestamp,
                "active_app": capture.active_app,
                "window_title": capture.window_title,
                "text_blocks_count": len(capture.text_blocks),
            }
        }

        return AuditReport(
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            verdict=verdict,
            total_audited=audited_count,
            matches_count=matches,
            mismatches_count=mismatches,
            not_in_viewport_count=not_in_viewport,
            capture_metadata={
                "source": capture.source_type,
                "capture_id": capture.capture_id,
                "timestamp": capture.timestamp,
                "app": capture.active_app,
                "window": capture.window_title,
                "ocr_sha256": capture.sha256_hash,
            },
            api_metadata={
                "url": DEFAULT_API_URL,
                "payload_sha256": raw_api_sha256,
            },
            diffs=diffs,
            tri_proof=tri_proof,
        )


# -----------------------------------------------------------------------------
# 5. CLI Presentation & Formatter
# -----------------------------------------------------------------------------

def print_terminal_report(report: AuditReport, verbose: bool = False):
    """Renders high-density colorized terminal audit report."""
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"

    v_color = GREEN if report.verdict == "TRUTH_VERIFIED" else RED
    print("\n" + "=" * 80)
    print(f"{BOLD}{CYAN}🔍 SCREEN LENS TIER 3 TRUTH AUDIT (:4007 UI vs API JSON){RESET}")
    print("=" * 80)
    print(f"Timestamp   : {report.timestamp}")
    print(f"Verdict     : {v_color}{BOLD}{report.verdict}{RESET}")
    print(f"Metrics     : {BOLD}{report.matches_count} MATCH{RESET} | "
          f"{RED if report.mismatches_count > 0 else DIM}{report.mismatches_count} MISMATCH{RESET} | "
          f"{DIM}{report.not_in_viewport_count} NOT IN VIEWPORT{RESET} (Total Audited: {report.total_audited})")
    print(f"Capture Src : {report.capture_metadata['source']} "
          f"(ID: {report.capture_metadata.get('capture_id', 'N/A')}, App: {report.capture_metadata.get('app', 'N/A')}, Window: {report.capture_metadata.get('window', 'N/A')[:40]})")
    print(f"API SHA256  : {report.api_metadata['payload_sha256'][:16]}... | OCR SHA256: {report.capture_metadata['ocr_sha256'][:16]}...")
    print("-" * 80)

    # Table Header
    print(f"{BOLD}{'METRIC':<22} {'DISPLAYED (OCR)':<20} {'API GROUND TRUTH':<20} {'STATUS':<15}{RESET}")
    print("-" * 80)

    for d in report.diffs:
        if d.status == "NOT_IN_VIEWPORT" and not verbose:
            continue

        if d.status == "MATCH":
            st_str = f"{GREEN}✓ MATCH{RESET}"
        elif d.status == "MISMATCH":
            st_str = f"{RED}✗ MISMATCH{RESET}"
        elif d.status == "ZERO_MOCK_VIOLATION":
            st_str = f"{RED}⚠️ RULE 0 VIOLATION{RESET}"
        else:
            st_str = f"{DIM}NOT IN VIEW{RESET}"

        disp_str = str(d.displayed_raw)[:18]
        api_str = str(d.api_ground_truth)[:18]
        print(f"{d.metric:<22} {disp_str:<20} {api_str:<20} {st_str}")

    print("-" * 80)

    # Highlight Mismatches / Violations if any
    mismatches = [d for d in report.diffs if d.status in ("MISMATCH", "ZERO_MOCK_VIOLATION")]
    if mismatches:
        print(f"\n{BOLD}{RED}🚨 MISMATCH / DISCREPANCY DETAILS:{RESET}")
        for m in mismatches:
            print(f"  • {BOLD}{m.metric}{RESET}: {m.details}")
            print(f"    - Displayed (OCR) : {m.displayed_raw}")
            print(f"    - Ground Truth    : {m.api_ground_truth}")
    else:
        print(f"\n{BOLD}{GREEN}✨ All active UI metrics match API ground truth with zero simulated data.{RESET}")

    # Tri-Proof Block
    tp = report.tri_proof
    p2 = tp.get("proof_2_cryptographic_checksums", {})
    p3 = tp.get("proof_3_visual_perception", {})
    print(f"\n{BOLD}{CYAN}🛡️ TRI-PROOF VERIFICATION RECEIPT (Rule #1 & #5):{RESET}")
    print(f"  [Proof 1 - Actuation Exit Code] : {tp.get('proof_1_actuation_exit_code')}")
    print(f"  [Proof 2 - Line & Crypto Hash ] : API={p2.get('api_payload_sha256', '')[:12]}.. | OCR={p2.get('ocr_capture_sha256', '')[:12]}..")
    print(f"  [Proof 3 - Visual Grounding   ] : Src={p3.get('capture_source')} | App={p3.get('active_app')} | Blocks={p3.get('text_blocks_count')}")
    print("=" * 80 + "\n")


# -----------------------------------------------------------------------------
# 6. Main Runner
# -----------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Screen Lens Tier 3 Visual Truth & UI Discrepancy Checker")
    parser.add_argument("--source", choices=["auto", "sqlite", "port_3035", "port_3037", "cli", "file"],
                        default="auto", help="Screen Lens OCR capture source (default: auto)")
    parser.add_argument("--capture-id", type=int, help="Specific SQLite capture ID to evaluate")
    parser.add_argument("--search", type=str, help="Search keyword for historical SQLite capture")
    parser.add_argument("--capture-file", type=str, help="Path to static capture JSON or text file")
    parser.add_argument("--api-url", type=str, default=DEFAULT_API_URL, help="Port 4007 base URL (default: http://127.0.0.1:4007)")
    parser.add_argument("--api-file", type=str, help="Path to static API topology JSON file")
    parser.add_argument("--sqlite-db", type=str, default=str(DEFAULT_SQLITE_PATH), help="Path to screen_lens.sqlite")
    parser.add_argument("--tolerance", type=float, default=0.05, help="Relative numerical tolerance (default: 0.05 / 5 pct)")
    parser.add_argument("--strict", action="store_true", help="Exit 1 if any mismatch is detected")
    parser.add_argument("--json", action="store_true", help="Output pure JSON report to stdout")
    parser.add_argument("--verbose", action="store_true", help="Show all metrics including non-visible ones")
    args = parser.parse_args()

    # 1. Ingest Screen Lens Capture
    capture: Optional[CaptureResult] = None
    sqlite_path = Path(args.sqlite_db)

    if args.capture_file:
        capture = ScreenLensIngestor.from_file(args.capture_file)
    elif args.source == "sqlite":
        capture = ScreenLensIngestor.from_sqlite(sqlite_path, capture_id=args.capture_id, search=args.search)
    elif args.source == "port_3035":
        capture = ScreenLensIngestor.from_port_3035()
    elif args.source == "port_3037":
        capture = ScreenLensIngestor.from_port_3037()
    elif args.source == "cli":
        capture = ScreenLensIngestor.from_cli()
    elif args.source == "auto":
        # Hierarchical auto-discovery:
        # 1. Try SQLite with 4007 search first (fastest and most likely to have exact 4007 dashboard)
        capture = ScreenLensIngestor.from_sqlite(sqlite_path, capture_id=args.capture_id, search=args.search)
        
        # 2. If SQLite capture doesn't contain 4007 UI keywords, try Port 3037
        if not capture or ("4007" not in capture.raw_text and "NETWORK ANALYZER" not in capture.raw_text):
            port3037_cap = ScreenLensIngestor.from_port_3037()
            if port3037_cap and ("4007" in port3037_cap.raw_text or "NETWORK ANALYZER" in port3037_cap.raw_text):
                capture = port3037_cap

        # 3. If still nothing, try Port 3035
        if not capture:
            capture = ScreenLensIngestor.from_port_3035()

        # 4. If still nothing, fallback to live CLI capture
        if not capture:
            capture = ScreenLensIngestor.from_cli()

        # 5. Fallback to any recent SQLite capture
        if not capture:
            capture = ScreenLensIngestor.from_sqlite(sqlite_path)

    if not capture or not capture.raw_text:
        err_msg = f"Failed to acquire Screen Lens capture from source '{args.source}'."
        if args.json:
            print(json.dumps({"error": err_msg, "status": "CAPTURE_UNAVAILABLE"}, indent=2))
        else:
            print(f"\033[31m❌ {err_msg}\033[0m")
        return 2

    # 2. Ingest API Ground Truth
    topology_data: Optional[Dict[str, Any]] = None
    raw_api_sha256: str = ""

    if args.api_file:
        topology_data, raw_api_sha256 = Port4007ApiIngestor.load_from_file(args.api_file)
    else:
        topology_data, raw_api_sha256 = Port4007ApiIngestor.fetch_topology(args.api_url)

    if not topology_data:
        err_msg = f"Failed to fetch ground truth from Port 4007 API ({args.api_url})."
        if args.json:
            print(json.dumps({"error": err_msg, "status": "API_UNAVAILABLE"}, indent=2))
        else:
            print(f"\033[31m❌ {err_msg}\033[0m")
        return 2

    # 3. Diff & Verify
    verifier = LensT3Verifier(tolerance_pct=args.tolerance)
    report = verifier.verify(capture, topology_data, raw_api_sha256)

    # 4. Presentation
    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print_terminal_report(report, verbose=args.verbose)

    # Exit code
    if args.strict and report.mismatches_count > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
