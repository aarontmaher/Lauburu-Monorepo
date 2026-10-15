"""Screenpipe Service: Sovereign Visual Context, Metal Vision OCR & Local SQLite Integration.

This module provides a 100% local, zero-cloud-dependent interface to the Screenpipe Rust core
daemon on macOS Apple Silicon (M4 Pro). It exposes ultra-low-latency read-only immutable SQLite
queries, an authenticated REST HTTP client with automated secrets discovery, Apple Silicon Metal
Vision OCR & Accessibility tree parsing with normalized bounding boxes [ymin, xmin, ymax, xmax],
and seamless automatic fallback when the REST API is degraded or offline.

Features:
- F1_SCREENPIPE_SQLITE: Ultra-low-latency immutable read-only direct SQLite interface querying
  ~/.screenpipe/db.sqlite for frames, elements, ui_events, and memories.
- F2_SCREENPIPE_REST_CLIENT: Authenticated REST HTTP client (http://localhost:3030) with auto-discovery
  of API keys from ~/.screenpipe/secrets.sqlite or SCREENPIPE_API_KEY, enforcing mandatory LIMIT
  and SELECT-only execution for raw SQL.
- F3_SCREENPIPE_METAL_VISION: Normalized bounding boxes [ymin, xmin, ymax, xmax], OCR confidence scoring,
  hierarchical accessibility tree parsing, and window/app indexing.
- Robust Fallback: Seamless automatic fallback from REST to Direct SQLite on 503/403/connection errors.
- Zero-Mock & Airgapped: Strictly local, 0% external cloud telemetry calls, Rule #0 compliant.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import re
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("lauburu.screenpipe_service")


# ============================================================================
# Exceptions
# ============================================================================


class ScreenpipeError(Exception):
    """Base exception for all Screenpipe service operations."""


class ScreenpipeAuthError(ScreenpipeError):
    """Raised when authentication with the Screenpipe daemon fails (HTTP 401/403)."""


class ScreenpipeQueryError(ScreenpipeError):
    """Raised when a SQL or REST query fails or is rejected."""


class ScreenpipeSecurityError(ScreenpipeQueryError):
    """Raised when a SQL query violates security invariants (e.g., mutating or unconstrained)."""


class ScreenpipeConnectionError(ScreenpipeError):
    """Raised when the Screenpipe REST daemon is unreachable or unresponsive."""


# ============================================================================
# Data Models & Normalized Geometry
# ============================================================================


@dataclass
class NormalizedBoundingBox:
    """Normalized bounding box coordinates in range [0.0, 1.0].

    Follows standard Vision/VLM ordering: [ymin, xmin, ymax, xmax].
    """

    ymin: float = 0.0
    xmin: float = 0.0
    ymax: float = 0.0
    xmax: float = 0.0

    def __post_init__(self) -> None:
        # Clamp coordinates to [0.0, 1.0]
        self.ymin = max(0.0, min(1.0, float(self.ymin)))
        self.xmin = max(0.0, min(1.0, float(self.xmin)))
        self.ymax = max(self.ymin, min(1.0, float(self.ymax)))
        self.xmax = max(self.xmin, min(1.0, float(self.xmax)))

    @property
    def width(self) -> float:
        """Width of the bounding box (0.0 - 1.0)."""
        return max(0.0, self.xmax - self.xmin)

    @property
    def height(self) -> float:
        """Height of the bounding box (0.0 - 1.0)."""
        return max(0.0, self.ymax - self.ymin)

    @property
    def center_x(self) -> float:
        """Horizontal center point (0.0 - 1.0)."""
        return (self.xmin + self.xmax) / 2.0

    @property
    def center_y(self) -> float:
        """Vertical center point (0.0 - 1.0)."""
        return (self.ymin + self.ymax) / 2.0

    @property
    def area(self) -> float:
        """Normalized area of the bounding box (0.0 - 1.0)."""
        return self.width * self.height

    @property
    def is_valid(self) -> bool:
        """True if the bounding box has non-zero area."""
        return self.width > 0.0 and self.height > 0.0

    def to_list(self) -> list[float]:
        """Return coordinates as [ymin, xmin, ymax, xmax]."""
        return [
            round(self.ymin, 6),
            round(self.xmin, 6),
            round(self.ymax, 6),
            round(self.xmax, 6),
        ]

    def to_dict(self) -> dict[str, float]:
        """Return coordinates as dictionary."""
        return {
            "ymin": round(self.ymin, 6),
            "xmin": round(self.xmin, 6),
            "ymax": round(self.ymax, 6),
            "xmax": round(self.xmax, 6),
            "width": round(self.width, 6),
            "height": round(self.height, 6),
            "center_x": round(self.center_x, 6),
            "center_y": round(self.center_y, 6),
        }

    def scale_to_pixels(self, screen_width: int, screen_height: int) -> dict[str, int]:
        """Scale normalized coordinates to absolute integer pixel bounds."""
        left = round(self.xmin * screen_width)
        top = round(self.ymin * screen_height)
        right = round(self.xmax * screen_width)
        bottom = round(self.ymax * screen_height)
        return {
            "left": left,
            "top": top,
            "right": right,
            "bottom": bottom,
            "width": max(0, right - left),
            "height": max(0, bottom - top),
        }

    @classmethod
    def from_bounds(
        cls,
        left_bound: float | None,
        top_bound: float | None,
        width_bound: float | None,
        height_bound: float | None,
    ) -> NormalizedBoundingBox:
        """Construct a NormalizedBoundingBox from Screenpipe left/top/width/height columns."""
        l = float(left_bound) if left_bound is not None else 0.0
        t = float(top_bound) if top_bound is not None else 0.0
        w = float(width_bound) if width_bound is not None else 0.0
        h = float(height_bound) if height_bound is not None else 0.0

        ymin = max(0.0, min(1.0, t))
        xmin = max(0.0, min(1.0, l))
        ymax = max(ymin, min(1.0, t + h))
        xmax = max(xmin, min(1.0, l + w))
        return cls(ymin=ymin, xmin=xmin, ymax=ymax, xmax=xmax)

    @classmethod
    def from_list(cls, coords: Sequence[float]) -> NormalizedBoundingBox:
        """Construct from [ymin, xmin, ymax, xmax] list/tuple."""
        if len(coords) != 4:
            raise ValueError(
                f"Expected 4 elements [ymin, xmin, ymax, xmax], got {len(coords)}"
            )
        return cls(ymin=coords[0], xmin=coords[1], ymax=coords[2], xmax=coords[3])


@dataclass
class ElementRecord:
    """Represents a discrete OCR text word/line or Accessibility Tree node."""

    id: int | None = None
    frame_id: int = 0
    source: str = "ocr"  # "ocr" | "accessibility"
    role: str = ""  # "word", "line", "paragraph", "AXButton", "AXTextField", etc.
    text: str | None = None
    parent_id: int | None = None
    depth: int = 0
    bbox: NormalizedBoundingBox = field(default_factory=NormalizedBoundingBox)
    confidence: float = 1.0  # Normalized 0.0 to 1.0
    sort_order: int = 0
    properties: str | None = None
    on_screen: bool = True
    children: list[ElementRecord] = field(default_factory=list)

    def to_dict(self, include_children: bool = True) -> dict[str, Any]:
        """Convert record to dictionary representation."""
        data: dict[str, Any] = {
            "id": self.id,
            "frame_id": self.frame_id,
            "source": self.source,
            "role": self.role,
            "text": self.text,
            "parent_id": self.parent_id,
            "depth": self.depth,
            "bbox": self.bbox.to_list(),
            "bbox_details": self.bbox.to_dict(),
            "confidence": round(self.confidence, 4),
            "sort_order": self.sort_order,
            "properties": self.properties,
            "on_screen": self.on_screen,
        }
        if include_children:
            data["children"] = [
                child.to_dict(include_children=True) for child in self.children
            ]
        return data


@dataclass
class FrameRecord:
    """Represents a recorded timeline frame captured by ScreenCaptureKit."""

    id: int = 0
    timestamp: str | None = None
    app_name: str | None = None
    window_name: str | None = None
    focused: bool | None = None
    browser_url: str | None = None
    device_name: str = ""
    snapshot_path: str | None = None
    accessibility_text: str | None = None
    accessibility_tree_json: str | None = None
    full_text: str | None = None
    text_json: str | None = None
    elements: list[ElementRecord] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert frame record to dictionary representation."""
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "app_name": self.app_name,
            "window_name": self.window_name,
            "focused": self.focused,
            "browser_url": self.browser_url,
            "device_name": self.device_name,
            "snapshot_path": self.snapshot_path,
            "accessibility_text": self.accessibility_text,
            "full_text": self.full_text,
            "elements_count": len(self.elements),
            "elements": [e.to_dict(include_children=False) for e in self.elements],
        }


@dataclass
class UiEventRecord:
    """Represents a user input event (click, type, scroll, focus switch)."""

    id: int = 0
    timestamp: str | None = None
    session_id: str | None = None
    relative_ms: int = 0
    event_type: str = ""
    x: int | None = None
    y: int | None = None
    delta_x: int | None = None
    delta_y: int | None = None
    button: int | None = None
    click_count: int | None = None
    key_code: int | None = None
    modifiers: int | None = None
    text_content: str | None = None
    app_name: str | None = None
    app_pid: int | None = None
    window_title: str | None = None
    browser_url: str | None = None
    element_role: str | None = None
    element_name: str | None = None
    element_bounds: str | None = None
    frame_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert UI event to dictionary representation."""
        return asdict(self)


@dataclass
class MemoryRecord:
    """Represents an episodic or semantic memory item."""

    id: int | None = None
    content: str = ""
    source: str = "user"
    source_context: str | None = None
    tags: list[str] = field(default_factory=list)
    importance: float = 0.5
    frame_id: int | None = None
    created_at: str | None = None
    updated_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert memory record to dictionary."""
        return asdict(self)


@dataclass
class ScreenpipeHealthInfo:
    """Health information reported by the Screenpipe daemon or direct SQLite probe."""

    status: str = "unknown"  # "ok", "degraded", "offline", "unhealthy"
    status_code: int = 200
    daemon_version: str | None = None
    last_frame_timestamp: str | None = None
    last_audio_timestamp: str | None = None
    monitors: list[dict[str, Any]] = field(default_factory=list)
    sqlite_available: bool = False
    rest_available: bool = False
    raw_health: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert health info to dictionary representation."""
        return asdict(self)


# ============================================================================
# Security & SQL Safety Verification
# ============================================================================

_FORBIDDEN_SQL_PATTERNS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|PRAGMA|ATTACH|DETACH|REPLACE|TRUNCATE|EXECUTE|GRANT|REVOKE|VACUUM)\b",
    re.IGNORECASE,
)
_LIMIT_PATTERN = re.compile(r"\bLIMIT\s+(\d+)", re.IGNORECASE)
_SAFE_STATEMENT_START = re.compile(r"^\s*(SELECT|WITH|EXPLAIN)\b", re.IGNORECASE)


def validate_and_sanitize_sql(
    query: str,
    default_limit: int = 100,
    max_limit: int = 10000,
) -> str:
    """Validates that a SQL query is strictly read-only and enforces a LIMIT clause.

    Args:
        query: Raw SQL query string.
        default_limit: Default LIMIT to append if absent.
        max_limit: Maximum permissible LIMIT integer (10000 max).

    Returns:
        Sanitized SQL query string guaranteed to have a valid LIMIT clause.

    Raises:
        ScreenpipeSecurityError: If query is mutating, contains forbidden statements,
                                  or attempts multiple statement injection.
    """
    clean = query.strip()
    if not clean:
        raise ScreenpipeSecurityError("Empty SQL query is not permitted.")

    # Strip trailing semicolons and check for multiple statements
    stripped = clean.rstrip(";")
    if ";" in stripped:
        raise ScreenpipeSecurityError(
            "Multiple SQL statements separated by semicolons are strictly rejected."
        )

    # Ensure statement begins with SELECT, WITH, or EXPLAIN
    if not _SAFE_STATEMENT_START.match(stripped):
        raise ScreenpipeSecurityError(
            "Query rejected: /raw_sql and direct queries only allow SELECT, WITH, and EXPLAIN statements."
        )

    # Check for forbidden mutating keywords
    match = _FORBIDDEN_SQL_PATTERNS.search(stripped)
    if match:
        raise ScreenpipeSecurityError(
            f"Query rejected: forbidden mutating or administrative keyword '{match.group(1)}' detected."
        )

    # Check for LIMIT clause
    limit_match = _LIMIT_PATTERN.search(stripped)
    if limit_match:
        limit_val = int(limit_match.group(1))
        if limit_val > max_limit:
            # Clamp limit to max_limit
            start_pos, end_pos = limit_match.span()
            stripped = stripped[:start_pos] + f"LIMIT {max_limit}" + stripped[end_pos:]
    else:
        # Append default limit
        stripped = f"{stripped} LIMIT {default_limit}"

    return stripped


# ============================================================================
# F1: Ultra-Low-Latency Direct SQLite Engine (F1_SCREENPIPE_SQLITE)
# ============================================================================


class ScreenpipeDirectSqlite:
    """High-performance, immutable read-only SQLite direct interface for ~/.screenpipe/db.sqlite.

    Utilizes SQLite URI mode file:...db.sqlite?mode=ro&immutable=1 to eliminate lock contention
    with the active Screenpipe Rust daemon write transactions.
    """

    def __init__(self, db_path: str | Path | None = None) -> None:
        if db_path:
            self.db_path = Path(db_path).expanduser().resolve()
        else:
            self.db_path = (Path.home() / ".screenpipe" / "db.sqlite").resolve()

    def is_available(self) -> bool:
        """Returns True if the database file exists and is readable."""
        return self.db_path.exists() and os.access(self.db_path, os.R_OK)

    def get_connection(self) -> sqlite3.Connection:
        """Opens a read-only SQLite connection using URI mode with immutable flag."""
        if not self.is_available():
            raise ScreenpipeError(
                f"Screenpipe database not found or unreadable at {self.db_path}"
            )

        # Attempt immutable mode first for absolute zero lock overhead
        uri_immutable = f"file:{self.db_path}?mode=ro&immutable=1"
        try:
            conn = sqlite3.connect(uri_immutable, uri=True, timeout=5.0)
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.OperationalError:
            # Fallback to standard read-only mode with busy timeout
            uri_ro = f"file:{self.db_path}?mode=ro"
            conn = sqlite3.connect(uri_ro, uri=True, timeout=5.0)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA busy_timeout = 5000")
            return conn

    def execute_query(
        self,
        query: str,
        params: tuple | list | dict = (),
        enforce_safety: bool = True,
    ) -> list[dict[str, Any]]:
        """Executes a sanitized read-only SQL query against the local database.

        Args:
            query: SQL query string.
            params: Query parameters.
            enforce_safety: If True, applies SELECT-only and LIMIT enforcement.

        Returns:
            List of row dictionaries.
        """
        if enforce_safety:
            query = validate_and_sanitize_sql(query)

        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
        except sqlite3.Error as e:
            raise ScreenpipeQueryError(f"SQLite execution error: {e}") from e
        finally:
            conn.close()

    async def execute_query_async(
        self,
        query: str,
        params: tuple | list | dict = (),
        enforce_safety: bool = True,
    ) -> list[dict[str, Any]]:
        """Asynchronously executes a read-only SQL query without blocking the event loop."""
        return await asyncio.to_thread(
            self.execute_query, query, params, enforce_safety
        )

    def get_recent_frames(
        self,
        limit: int = 5,
        app_name: str | None = None,
    ) -> list[FrameRecord]:
        """Retrieves recent frames along with their associated bounding box elements."""
        limit = min(max(1, limit), 1000)
        params: list[Any] = []
        where_clause = ""
        if app_name:
            where_clause = "WHERE app_name = ?"
            params.append(app_name)

        query = f"""
            SELECT id, timestamp, app_name, window_name, focused, browser_url,
                   device_name, snapshot_path, accessibility_text, accessibility_tree_json,
                   full_text, text_json
            FROM frames
            {where_clause}
            ORDER BY id DESC
            LIMIT {limit}
        """
        rows = self.execute_query(query, params, enforce_safety=False)
        frames: list[FrameRecord] = []
        for r in rows:
            frame_id = r["id"]
            elements = self.get_elements_for_frame(frame_id)
            frame = FrameRecord(
                id=frame_id,
                timestamp=str(r["timestamp"]) if r["timestamp"] else None,
                app_name=r["app_name"],
                window_name=r["window_name"],
                focused=bool(r["focused"]) if r["focused"] is not None else None,
                browser_url=r["browser_url"],
                device_name=r["device_name"] or "",
                snapshot_path=r["snapshot_path"],
                accessibility_text=r["accessibility_text"],
                accessibility_tree_json=r["accessibility_tree_json"],
                full_text=r["full_text"],
                text_json=r["text_json"],
                elements=elements,
            )
            frames.append(frame)
        return frames

    def get_elements_for_frame(
        self,
        frame_id: int,
        source: str | None = None,
    ) -> list[ElementRecord]:
        """Retrieves and normalizes all OCR and accessibility elements for a frame."""
        params: list[Any] = [frame_id]
        where_source = ""
        if source:
            where_source = "AND source = ?"
            params.append(source)

        query = f"""
            SELECT id, frame_id, source, role, text, parent_id, depth,
                   left_bound, top_bound, width_bound, height_bound,
                   confidence, sort_order, properties, on_screen
            FROM elements
            WHERE frame_id = ? {where_source}
            ORDER BY depth ASC, sort_order ASC, id ASC
            LIMIT 5000
        """
        rows = self.execute_query(query, params, enforce_safety=False)
        elements: list[ElementRecord] = []
        for r in rows:
            # Handle confidence normalization: screenpipe stores 0-100 or 0-1
            raw_conf = float(r["confidence"]) if r["confidence"] is not None else 1.0
            norm_conf = (
                raw_conf / 100.0 if raw_conf > 1.0 else max(0.0, min(1.0, raw_conf))
            )

            bbox = NormalizedBoundingBox.from_bounds(
                left_bound=r["left_bound"],
                top_bound=r["top_bound"],
                width_bound=r["width_bound"],
                height_bound=r["height_bound"],
            )

            elem = ElementRecord(
                id=r["id"],
                frame_id=r["frame_id"],
                source=r["source"] or "ocr",
                role=r["role"] or "",
                text=r["text"],
                parent_id=r["parent_id"],
                depth=int(r["depth"] or 0),
                bbox=bbox,
                confidence=norm_conf,
                sort_order=int(r["sort_order"] or 0),
                properties=r["properties"],
                on_screen=bool(r["on_screen"]) if r["on_screen"] is not None else True,
            )
            elements.append(elem)
        return elements

    def get_frame_by_id(self, frame_id: int) -> FrameRecord | None:
        """Fetches a specific frame and its elements by ID."""
        query = """
            SELECT id, timestamp, app_name, window_name, focused, browser_url,
                   device_name, snapshot_path, accessibility_text, accessibility_tree_json,
                   full_text, text_json
            FROM frames
            WHERE id = ?
            LIMIT 1
        """
        rows = self.execute_query(query, [frame_id], enforce_safety=False)
        if not rows:
            return None
        r = rows[0]
        elements = self.get_elements_for_frame(frame_id)
        return FrameRecord(
            id=r["id"],
            timestamp=str(r["timestamp"]) if r["timestamp"] else None,
            app_name=r["app_name"],
            window_name=r["window_name"],
            focused=bool(r["focused"]) if r["focused"] is not None else None,
            browser_url=r["browser_url"],
            device_name=r["device_name"] or "",
            snapshot_path=r["snapshot_path"],
            accessibility_text=r["accessibility_text"],
            accessibility_tree_json=r["accessibility_tree_json"],
            full_text=r["full_text"],
            text_json=r["text_json"],
            elements=elements,
        )

    def get_recent_ui_events(
        self,
        limit: int = 50,
        event_type: str | None = None,
    ) -> list[UiEventRecord]:
        """Retrieves recent user input events (clicks, typing, focus changes)."""
        limit = min(max(1, limit), 1000)
        params: list[Any] = []
        where_clause = ""
        if event_type:
            where_clause = "WHERE event_type = ?"
            params.append(event_type)

        query = f"""
            SELECT id, timestamp, session_id, relative_ms, event_type,
                   x, y, delta_x, delta_y, button, click_count, key_code,
                   modifiers, text_content, app_name, app_pid, window_title,
                   browser_url, element_role, element_name, element_bounds, frame_id
            FROM ui_events
            {where_clause}
            ORDER BY id DESC
            LIMIT {limit}
        """
        rows = self.execute_query(query, params, enforce_safety=False)
        events: list[UiEventRecord] = []
        for r in rows:
            events.append(
                UiEventRecord(
                    id=r["id"],
                    timestamp=str(r["timestamp"]) if r["timestamp"] else None,
                    session_id=r["session_id"],
                    relative_ms=int(r["relative_ms"] or 0),
                    event_type=r["event_type"] or "",
                    x=r["x"],
                    y=r["y"],
                    delta_x=r["delta_x"],
                    delta_y=r["delta_y"],
                    button=r["button"],
                    click_count=r["click_count"],
                    key_code=r["key_code"],
                    modifiers=r["modifiers"],
                    text_content=r["text_content"],
                    app_name=r["app_name"],
                    app_pid=r["app_pid"],
                    window_title=r["window_title"],
                    browser_url=r["browser_url"],
                    element_role=r["element_role"],
                    element_name=r["element_name"],
                    element_bounds=r["element_bounds"],
                    frame_id=r["frame_id"],
                )
            )
        return events

    def get_memories(
        self,
        limit: int = 50,
        tag: str | None = None,
        min_importance: float | None = None,
    ) -> list[MemoryRecord]:
        """Retrieves episodic memories with optional tag and importance filtering."""
        limit = min(max(1, limit), 1000)
        clauses: list[str] = []
        params: list[Any] = []
        if min_importance is not None:
            clauses.append("importance >= ?")
            params.append(min_importance)
        if tag:
            clauses.append("tags LIKE ?")
            params.append(f"%{tag}%")

        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        query = f"""
            SELECT id, content, source, source_context, tags, importance,
                   frame_id, created_at, updated_at
            FROM memories
            {where}
            ORDER BY id DESC
            LIMIT {limit}
        """
        rows = self.execute_query(query, params, enforce_safety=False)
        memories: list[MemoryRecord] = []
        for r in rows:
            raw_tags = r["tags"]
            parsed_tags: list[str] = []
            if raw_tags:
                try:
                    parsed_tags = (
                        json.loads(raw_tags) if raw_tags.startswith("[") else [raw_tags]
                    )
                except (json.JSONDecodeError, TypeError):
                    parsed_tags = [raw_tags]

            memories.append(
                MemoryRecord(
                    id=r["id"],
                    content=r["content"] or "",
                    source=r["source"] or "user",
                    source_context=r["source_context"],
                    tags=parsed_tags,
                    importance=float(r["importance"] or 0.5),
                    frame_id=r["frame_id"],
                    created_at=str(r["created_at"]) if r["created_at"] else None,
                    updated_at=str(r["updated_at"]) if r["updated_at"] else None,
                )
            )
        return memories

    def search_text(
        self,
        query: str,
        limit: int = 10,
        content_type: str = "all",
    ) -> list[dict[str, Any]]:
        """Performs full-text or substring search across OCR, elements, and audio transcripts."""
        limit = min(max(1, limit), 500)
        clean_q = query.strip()
        if not clean_q:
            return []

        results: list[dict[str, Any]] = []

        # 1. Try frames FTS5 or LIKE
        if content_type in ("all", "ocr"):
            try:
                fts_query = """
                    SELECT f.id as frame_id, f.timestamp, f.app_name, f.window_name,
                           f.full_text as text, 'ocr' as content_type,
                           1.0 as score
                    FROM frames f
                    WHERE f.full_text LIKE ? OR f.accessibility_text LIKE ?
                    ORDER BY f.id DESC
                    LIMIT ?
                """
                like_param = f"%{clean_q}%"
                rows = self.execute_query(
                    fts_query, [like_param, like_param, limit], enforce_safety=False
                )
                for r in rows:
                    results.append(
                        {
                            "frame_id": r["frame_id"],
                            "timestamp": str(r["timestamp"])
                            if r["timestamp"]
                            else None,
                            "app_name": r.get("app_name"),
                            "window_name": r.get("window_name"),
                            "text": r["text"] or "",
                            "content_type": "ocr",
                            "score": 1.0,
                            "bbox": None,
                        }
                    )
            except (ScreenpipeError, sqlite3.Error, OSError) as e:
                logger.debug("FTS frames query error: %s", e)
                try:
                    simple_query = "SELECT id as frame_id, full_text as text, app_name FROM frames WHERE full_text LIKE ? ORDER BY id DESC LIMIT ?"
                    rows = self.execute_query(
                        simple_query, [f"%{clean_q}%", limit], enforce_safety=False
                    )
                    for r in rows:
                        results.append(
                            {
                                "frame_id": r["frame_id"],
                                "timestamp": None,
                                "app_name": r.get("app_name"),
                                "window_name": None,
                                "text": r["text"] or "",
                                "content_type": "ocr",
                                "score": 1.0,
                                "bbox": None,
                            }
                        )
                except (ScreenpipeError, sqlite3.Error, OSError) as err:
                    logger.debug("Frames search fallback error: %s", err)

        # 2. Try elements table for fine-grained bounding boxes
        if len(results) < limit and content_type in ("all", "ocr"):
            try:
                elem_limit = limit - len(results)
                elem_query = """
                    SELECT e.id as element_id, e.frame_id, e.role, e.text, e.confidence,
                           e.left_bound, e.top_bound, e.width_bound, e.height_bound,
                           f.app_name, f.window_name, f.timestamp
                    FROM elements e
                    LEFT JOIN frames f ON e.frame_id = f.id
                    WHERE e.text LIKE ?
                    ORDER BY e.id DESC
                    LIMIT ?
                """
                elem_rows = self.execute_query(
                    elem_query, [f"%{clean_q}%", elem_limit], enforce_safety=False
                )
                for r in elem_rows:
                    bbox = NormalizedBoundingBox.from_bounds(
                        r["left_bound"],
                        r["top_bound"],
                        r["width_bound"],
                        r["height_bound"],
                    )
                    results.append(
                        {
                            "frame_id": r["frame_id"],
                            "element_id": r["element_id"],
                            "timestamp": str(r["timestamp"])
                            if r["timestamp"]
                            else None,
                            "app_name": r["app_name"],
                            "window_name": r["window_name"],
                            "text": r["text"] or "",
                            "content_type": "ocr_element",
                            "score": float(r["confidence"] or 1.0)
                            / (100.0 if (r["confidence"] or 0) > 1.0 else 1.0),
                            "bbox": bbox.to_list(),
                            "bbox_details": bbox.to_dict(),
                        }
                    )
            except (ScreenpipeError, sqlite3.Error, OSError) as e:
                logger.debug("Elements search error: %s", e)

        # 3. Audio transcriptions search if requested
        if len(results) < limit and content_type in ("all", "audio"):
            try:
                audio_limit = limit - len(results)
                audio_query = """
                    SELECT a.id, a.timestamp, a.transcription as text, 'audio' as content_type,
                           a.device, a.transcription_engine, 1.0 as score
                    FROM audio_transcriptions a
                    WHERE a.transcription LIKE ?
                    ORDER BY a.id DESC
                    LIMIT ?
                """
                audio_rows = self.execute_query(
                    audio_query, [f"%{clean_q}%", audio_limit], enforce_safety=False
                )
                for r in audio_rows:
                    results.append(
                        {
                            "frame_id": None,
                            "audio_id": r["id"],
                            "timestamp": str(r["timestamp"])
                            if r["timestamp"]
                            else None,
                            "app_name": "Audio",
                            "window_name": r["device"] or "Microphone",
                            "text": r["text"] or "",
                            "content_type": "audio",
                            "score": 1.0,
                            "bbox": None,
                        }
                    )
            except (ScreenpipeError, sqlite3.Error, OSError) as e:
                logger.debug("Audio transcript search error: %s", e)

        return results[:limit]

    def get_active_windows(self, limit: int = 20) -> list[dict[str, Any]]:
        """Aggregates active application windows recorded in recent frames."""
        query = f"""
            SELECT DISTINCT app_name, window_name, browser_url, focused, MAX(timestamp) as last_seen, MAX(id) as latest_frame_id
            FROM frames
            WHERE app_name IS NOT NULL AND app_name != ''
            GROUP BY app_name, window_name
            ORDER BY latest_frame_id DESC
            LIMIT {limit}
        """
        return self.execute_query(query, enforce_safety=False)


# ============================================================================
# F2: Authenticated REST HTTP Client (F2_SCREENPIPE_REST_CLIENT)
# ============================================================================

class ScreenpipeRestClient:
    """Authenticated HTTP client for the Screenpipe Rust Core REST API (http://localhost:3030).

    Automatically discovers authorization keys from ~/.screenpipe/secrets.sqlite or
    environment variables. Enforces memory safety and SELECT-only validation on /raw_sql.
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:3030",
        api_key: str | None = None,
        secrets_path: str | Path | None = None,
        timeout: float = 5.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = float(timeout)
        self.secrets_path = (
            Path(secrets_path).expanduser().resolve()
            if secrets_path
            else (Path.home() / ".screenpipe" / "secrets.sqlite").resolve()
        )
        self._api_key: str | None = self._resolve_api_key(explicit_key=api_key)

    def _resolve_api_key(self, explicit_key: str | None = None) -> str | None:
        """Discovers API key from explicit arg, env var, or secrets.sqlite."""
        if explicit_key:
            return explicit_key.strip()

        env_key = os.environ.get("SCREENPIPE_API_KEY") or os.environ.get(
            "SCREENPIPE_LOCAL_API_KEY"
        )
        if env_key:
            return env_key.strip()

        if self.secrets_path.exists():
            try:
                uri = f"file:{self.secrets_path}?mode=ro&immutable=1"
                conn = sqlite3.connect(uri, uri=True, timeout=2.0)
                c = conn.cursor()
                c.execute("SELECT value FROM secrets WHERE key = 'api_auth_key'")
                row = c.fetchone()
                conn.close()
                if row and row[0]:
                    val = row[0]
                    if isinstance(val, bytes):
                        try:
                            return base64.b64decode(val).decode("utf-8").strip()
                        except (ValueError, UnicodeDecodeError):
                            return val.decode("utf-8", errors="ignore").strip()
                    elif isinstance(val, str):
                        try:
                            return (
                                base64.b64decode(val.encode("utf-8"))
                                .decode("utf-8")
                                .strip()
                            )
                        except (ValueError, UnicodeDecodeError):
                            return val.strip()
            except (sqlite3.Error, OSError) as e:
                logger.debug("Failed to read secrets.sqlite: %s", e)

        return None

    def set_api_key(self, api_key: str) -> None:
        """Manually update the API key."""
        self._api_key = api_key.strip()

    @property
    def api_key(self) -> str | None:
        """Current active API key."""
        return self._api_key

    def _headers(self) -> dict[str, str]:
        """Builds HTTP request headers including Authorization Bearer token."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Lauburu-ScreenpipeClient/1.0",
        }
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    def _request(
        self,
        endpoint: str,
        method: str = "GET",
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | str | None = None,
    ) -> Any:
        """Executes an HTTP request to the Screenpipe daemon."""
        url = f"{self.base_url}{endpoint}"
        if params:
            clean_params = {k: v for k, v in params.items() if v is not None}
            if clean_params:
                url = f"{url}?{urllib.parse.urlencode(clean_params)}"

        payload_bytes: bytes | None = None
        if data is not None:
            if isinstance(data, str):
                payload_bytes = data.encode("utf-8")
            else:
                payload_bytes = json.dumps(data).encode("utf-8")

        req = urllib.request.Request(
            url=url,
            data=payload_bytes,
            headers=self._headers(),
            method=method,
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body_bytes = resp.read()
                if not body_bytes:
                    return {}
                try:
                    return json.loads(body_bytes.decode("utf-8"))
                except json.JSONDecodeError:
                    return body_bytes.decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            err_body = ""
            try:
                err_body = e.read().decode("utf-8")
            except (OSError, UnicodeDecodeError):
                pass

            if e.code in (401, 403):
                raise ScreenpipeAuthError(
                    f"Screenpipe REST API authentication rejected (HTTP {e.code}): {err_body}"
                ) from e
            elif e.code == 400:
                raise ScreenpipeQueryError(
                    f"Screenpipe REST API rejected bad request (HTTP 400): {err_body}"
                ) from e
            elif e.code == 404:
                raise ScreenpipeQueryError(
                    f"Resource not found (HTTP 404): {url}"
                ) from e
            elif e.code == 503:
                raise ScreenpipeConnectionError(
                    f"Screenpipe daemon degraded/unavailable (HTTP 503): {err_body}"
                ) from e
            else:
                raise ScreenpipeError(
                    f"Screenpipe HTTP Error {e.code}: {err_body}"
                ) from e
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            raise ScreenpipeConnectionError(
                f"Failed to connect to Screenpipe daemon at {self.base_url}: {e}"
            ) from e

    def get_health(self) -> dict[str, Any]:
        """Probes daemon health (/health, unauthenticated)."""
        return self._request("/health", method="GET")

    def search(
        self,
        q: str | None = None,
        content_type: str = "all",
        limit: int = 20,
        offset: int = 0,
        start_time: str | None = None,
        end_time: str | None = None,
        app_name: str | None = None,
        window_name: str | None = None,
        order: str = "descending",
    ) -> dict[str, Any]:
        """Executes authenticated multi-modal search across OCR and audio transcripts.

        Args:
            q: Search query string.
            content_type: 'all' | 'ocr' | 'audio'
            limit: Maximum items to return (1-1000).
            offset: Pagination offset.
            start_time: ISO 8601 timestamp string.
            end_time: ISO 8601 timestamp string.
            app_name: Filter by application name.
            window_name: Filter by window title.
            order: 'ascending' | 'descending'
        """
        valid_types = ("all", "ocr", "audio")
        if content_type.lower() not in valid_types:
            raise ScreenpipeQueryError(
                f"Invalid content_type '{content_type}'. Expected one of: {valid_types}"
            )

        valid_orders = ("ascending", "descending")
        if order.lower() not in valid_orders:
            raise ScreenpipeQueryError(
                f"Invalid order '{order}'. Expected one of: {valid_orders}"
            )

        params = {
            "q": q,
            "content_type": content_type.lower(),
            "limit": min(max(1, limit), 1000),
            "offset": max(0, offset),
            "start_time": start_time,
            "end_time": end_time,
            "app_name": app_name,
            "window_name": window_name,
            "order": order.lower(),
        }
        return self._request("/search", method="GET", params=params)

    def search_keyword(
        self,
        query: str,
        fuzzy_match: bool = False,
        limit: int = 20,
        offset: int = 0,
        start_time: str | None = None,
        end_time: str | None = None,
        app_names: list[str] | None = None,
        order: str = "descending",
    ) -> list[dict[str, Any]]:
        """Fast keyword search optimized for substring/fuzzy matching."""
        params: dict[str, Any] = {
            "query": query,
            "fuzzy_match": "true" if fuzzy_match else "false",
            "limit": min(max(1, limit), 500),
            "offset": max(0, offset),
            "start_time": start_time,
            "end_time": end_time,
            "order": order,
        }
        if app_names:
            params["app_names"] = ",".join(app_names)
        res = self._request("/search/keyword", method="GET", params=params)
        return res if isinstance(res, list) else res.get("data", [])

    def get_frame(self, frame_id: int, fallback: bool = True) -> dict[str, Any]:
        """Retrieves complete frame record by ID."""
        return self._request(
            f"/frames/{frame_id}",
            method="GET",
            params={"fallback": "true" if fallback else "false"},
        )

    def get_frame_context(self, frame_id: int) -> dict[str, Any]:
        """Retrieves consolidated OCR text, extracted accessibility nodes, and URLs for a frame."""
        return self._request(f"/frames/{frame_id}/context", method="GET")

    def get_frame_elements(
        self, frame_id: int, source: str | None = None
    ) -> list[dict[str, Any]]:
        """Retrieves element tree for a specific frame."""
        params = {"source": source} if source else None
        res = self._request(f"/frames/{frame_id}/elements", method="GET", params=params)
        return res if isinstance(res, list) else res.get("data", [])

    def get_elements(
        self,
        frame_id: int | None = None,
        source: str | None = None,
        role: str | None = None,
        on_screen: bool | None = None,
        q: str | None = None,
        app_name: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Queries UI and OCR elements with filtering."""
        params = {
            "frame_id": frame_id,
            "source": source,
            "role": role,
            "on_screen": "true"
            if on_screen is True
            else ("false" if on_screen is False else None),
            "q": q,
            "app_name": app_name,
            "limit": min(max(1, limit), 1000),
            "offset": max(0, offset),
        }
        return self._request("/elements", method="GET", params=params)

    def raw_sql(self, query: str) -> list[dict[str, Any]]:
        """Executes read-only SQL query via the REST API gateway.

        Enforces mandatory SELECT-only and LIMIT constraints.
        """
        sanitized_query = validate_and_sanitize_sql(query)
        payload = {"query": sanitized_query}
        res = self._request("/raw_sql", method="POST", data=payload)
        return res if isinstance(res, list) else []

    def get_memories(
        self,
        q: str | None = None,
        tags: list[str] | None = None,
        min_importance: float | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Retrieves episodic memories via REST."""
        params: dict[str, Any] = {
            "q": q,
            "min_importance": min_importance,
            "limit": min(max(1, limit), 500),
            "offset": max(0, offset),
        }
        if tags:
            params["tags"] = ",".join(tags)
        res = self._request("/memories", method="GET", params=params)
        return res if isinstance(res, list) else res.get("data", [])

    def add_memory(
        self,
        content: str,
        source: str = "agent",
        source_context: str | None = None,
        tags: list[str] | None = None,
        importance: float = 0.5,
        frame_id: int | None = None,
    ) -> dict[str, Any]:
        """Creates a new episodic memory record."""
        payload: dict[str, Any] = {
            "content": content,
            "source": source,
            "source_context": source_context,
            "tags": tags or [],
            "importance": float(importance),
            "frame_id": frame_id,
        }
        return self._request("/memories", method="POST", data=payload)

    def get_activity_summary(
        self, start_time: str, end_time: str | None = None
    ) -> dict[str, Any]:
        """Retrieves activity ledger summary for a time window."""
        params = {"start_time": start_time, "end_time": end_time}
        return self._request("/activity-summary", method="GET", params=params)

    def get_monitors(self) -> list[dict[str, Any]]:
        """Discovers active physical displays."""
        res = self._request("/vision/list", method="GET")
        return res if isinstance(res, list) else res.get("data", [])

    # Async API Wrappers
    async def get_health_async(self) -> dict[str, Any]:
        """Asynchronous get_health wrapper."""
        return await asyncio.to_thread(self.get_health)

    async def search_async(self, **kwargs: Any) -> dict[str, Any]:
        """Asynchronous search wrapper."""
        return await asyncio.to_thread(self.search, **kwargs)

    async def raw_sql_async(self, query: str) -> list[dict[str, Any]]:
        """Asynchronous raw_sql wrapper."""
        return await asyncio.to_thread(self.raw_sql, query)


# ============================================================================
# F3: Unified Screenpipe Service + Metal Vision Parser + Automatic Fallback
# ============================================================================


class ScreenpipeService:
    """Unified sovereign service uniting Direct SQLite, REST API, and Metal Vision OCR.

    Provides automated fallback to direct SQLite when Port 3030 is degraded or offline,
    structured bounding box transformations, window indexing, and hierarchical element trees.
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:3030",
        api_key: str | None = None,
        db_path: str | Path | None = None,
        secrets_path: str | Path | None = None,
        prefer_direct_sqlite: bool = False,
        auto_fallback: bool = True,
        timeout: float = 3.0,
    ) -> None:
        """Initializes the unified ScreenpipeService.

        Args:
            base_url: Base REST URL for Screenpipe daemon.
            api_key: Explicit API key (if omitted, auto-discovered from secrets.sqlite / env).
            db_path: Path to ~/.screenpipe/db.sqlite.
            secrets_path: Path to ~/.screenpipe/secrets.sqlite.
            prefer_direct_sqlite: If True, defaults to SQLite direct queries for minimum latency.
            auto_fallback: If True, automatically falls back to SQLite if REST fails.
            timeout: HTTP timeout in seconds.
        """
        self.prefer_direct_sqlite = prefer_direct_sqlite
        self.auto_fallback = auto_fallback
        self.timeout = timeout

        self.sqlite = ScreenpipeDirectSqlite(db_path=db_path)
        self.rest = ScreenpipeRestClient(
            base_url=base_url,
            api_key=api_key,
            secrets_path=secrets_path,
            timeout=timeout,
        )

        self._fallback_active: bool = False
        self._last_fallback_reason: str | None = None

    @property
    def fallback_active(self) -> bool:
        """True if the service is currently routing requests through SQLite fallback."""
        return self._fallback_active

    @property
    def last_fallback_reason(self) -> str | None:
        """Reason description for the most recent fallback invocation."""
        return self._last_fallback_reason

    def get_health_status(self) -> dict[str, Any]:
        """Probes overall subsystem health across REST daemon and direct SQLite.

        Returns:
            Dict containing unified health metrics, fallback status, and monitor lists.
        """
        sqlite_ok = self.sqlite.is_available()
        rest_ok = False
        raw_health: dict[str, Any] = {}
        status = "offline"

        try:
            raw_health = self.rest.get_health()
            rest_ok = True
            # Screenpipe returns status 'ok' or 'degraded' (e.g. no microphone)
            daemon_status = raw_health.get("status", "ok")
            status = "ok" if daemon_status == "ok" else "degraded"
        except ScreenpipeConnectionError:
            rest_ok = False
            status = "degraded" if sqlite_ok else "offline"
        except (ScreenpipeError, OSError) as e:
            rest_ok = False
            status = "degraded" if sqlite_ok else "unhealthy"
            raw_health = {"error": str(e)}

        last_frame_time = raw_health.get("last_frame_timestamp")
        if not last_frame_time and sqlite_ok:
            try:
                recent = self.sqlite.execute_query(
                    "SELECT timestamp FROM frames ORDER BY id DESC LIMIT 1",
                    enforce_safety=False,
                )
                if recent and recent[0]["timestamp"]:
                    last_frame_time = str(recent[0]["timestamp"])
            except (sqlite3.Error, OSError) as e:
                logger.debug("Failed to query last frame time: %s", e)

        monitors = []
        if rest_ok:
            try:
                monitors = self.rest.get_monitors()
            except (ScreenpipeError, OSError) as e:
                logger.debug("Failed to get monitors: %s", e)

        return {
            "status": status,
            "rest_api_healthy": rest_ok,
            "sqlite_healthy": sqlite_ok,
            "fallback_active": self._fallback_active,
            "last_fallback_reason": self._last_fallback_reason,
            "last_frame_timestamp": last_frame_time,
            "monitors": monitors,
            "details": raw_health,
        }

    def get_latest_frame_context(self, limit: int = 5) -> list[dict[str, Any]]:
        """Retrieves recent frames with normalized bounding boxes and window titles.

        Contract method for ScreenpipeService ↔ HermesCodeActionDispatcher.

        Args:
            limit: Number of recent frames to inspect.

        Returns:
            List of structured frame context dictionaries.
        """
        limit = min(max(1, limit), 100)

        # 1. Direct SQLite mode or preferred
        if self.prefer_direct_sqlite or not self.rest.api_key:
            return self._get_latest_frame_context_sqlite(limit)

        # 2. Try REST API first with graceful fallback
        try:
            search_res = self.rest.search(
                content_type="ocr", limit=limit, order="descending"
            )
            data = search_res.get("data", []) if isinstance(search_res, dict) else []
            if data:
                self._fallback_active = False
                contexts: list[dict[str, Any]] = []
                for item in data:
                    content = item.get("content", {})
                    frame_id = content.get("frame_id") or item.get("frame_id")
                    app_name = content.get("app_name") or item.get("app_name")
                    window_name = content.get("window_name") or item.get("window_name")
                    text = content.get("text") or item.get("text") or ""
                    timestamp = content.get("timestamp") or item.get("timestamp")

                    # Fetch elements if frame_id available
                    elements_list: list[dict[str, Any]] = []
                    if frame_id:
                        try:
                            elem_res = self.rest.get_frame_elements(int(frame_id))
                            for elem in elem_res:
                                bbox = NormalizedBoundingBox.from_bounds(
                                    elem.get("left_bound") or elem.get("left"),
                                    elem.get("top_bound") or elem.get("top"),
                                    elem.get("width_bound") or elem.get("width"),
                                    elem.get("height_bound") or elem.get("height"),
                                )
                                elements_list.append(
                                    {
                                        "role": elem.get("role", "word"),
                                        "text": elem.get("text", ""),
                                        "source": elem.get("source", "ocr"),
                                        "confidence": float(
                                            elem.get("confidence") or 1.0
                                        ),
                                        "bbox": bbox.to_list(),
                                        "bbox_details": bbox.to_dict(),
                                    }
                                )
                        except (ScreenpipeError, OSError) as e:
                            logger.debug("Element retrieval error: %s", e)

                    contexts.append(
                        {
                            "frame_id": frame_id,
                            "timestamp": timestamp,
                            "app_name": app_name,
                            "window_name": window_name,
                            "text": text,
                            "full_text": text,
                            "elements": elements_list,
                        }
                    )
                return contexts
            else:
                # If REST returned empty, check SQLite directly
                return self._get_latest_frame_context_sqlite(limit)
        except (ScreenpipeConnectionError, ScreenpipeAuthError, ScreenpipeError) as e:
            if self.auto_fallback:
                self._fallback_active = True
                self._last_fallback_reason = (
                    f"REST API failed ({e}), fell back to direct SQLite."
                )
                logger.warning(self._last_fallback_reason)
                return self._get_latest_frame_context_sqlite(limit)
            raise

    def _get_latest_frame_context_sqlite(self, limit: int) -> list[dict[str, Any]]:
        """Direct SQLite frame retrieval helper."""
        frames = self.sqlite.get_recent_frames(limit=limit)
        results: list[dict[str, Any]] = []
        for f in frames:
            text = f.full_text or f.accessibility_text or ""
            elements_data = [
                {
                    "id": e.id,
                    "role": e.role,
                    "text": e.text,
                    "source": e.source,
                    "depth": e.depth,
                    "confidence": e.confidence,
                    "bbox": e.bbox.to_list(),
                    "bbox_details": e.bbox.to_dict(),
                }
                for e in f.elements
            ]
            results.append(
                {
                    "frame_id": f.id,
                    "timestamp": f.timestamp,
                    "app_name": f.app_name,
                    "window_name": f.window_name,
                    "browser_url": f.browser_url,
                    "focused": f.focused,
                    "text": text,
                    "full_text": text,
                    "accessibility_text": f.accessibility_text,
                    "elements": elements_data,
                }
            )
        return results

    def query_screen_text(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Searches indexed screen text via REST /search or direct SQLite FTS5.

        Contract method for ScreenpipeService ↔ HermesCodeActionDispatcher.

        Args:
            query: Search query text.
            limit: Maximum matches to return.

        Returns:
            List of search match dictionaries with normalized bounding boxes.
        """
        limit = min(max(1, limit), 100)
        clean_q = query.strip()
        if not clean_q:
            return []

        # 1. Fast direct SQLite if preferred
        if self.prefer_direct_sqlite or not self.rest.api_key:
            return self.sqlite.search_text(clean_q, limit=limit)

        # 2. Try REST search with fallback
        try:
            res = self.rest.search(q=clean_q, limit=limit, order="descending")
            data = res.get("data", []) if isinstance(res, dict) else []
            if data:
                self._fallback_active = False
                matches: list[dict[str, Any]] = []
                for item in data:
                    content = item.get("content", {})
                    frame_id = content.get("frame_id") or item.get("frame_id")
                    matches.append(
                        {
                            "frame_id": frame_id,
                            "timestamp": content.get("timestamp")
                            or item.get("timestamp"),
                            "app_name": content.get("app_name") or item.get("app_name"),
                            "window_name": content.get("window_name")
                            or item.get("window_name"),
                            "text": content.get("text") or item.get("text") or "",
                            "content_type": item.get("type", "ocr"),
                            "score": float(item.get("score") or 1.0),
                            "bbox": None,
                        }
                    )
                return matches
            else:
                return self.sqlite.search_text(clean_q, limit=limit)
        except (ScreenpipeConnectionError, ScreenpipeAuthError, ScreenpipeError) as e:
            if self.auto_fallback:
                self._fallback_active = True
                self._last_fallback_reason = (
                    f"REST search failed ({e}), fell back to direct SQLite."
                )
                logger.warning(self._last_fallback_reason)
                return self.sqlite.search_text(clean_q, limit=limit)
            raise

    def parse_element_tree(self, frame_id: int) -> list[dict[str, Any]]:
        """Constructs a hierarchical element tree (DOM/Accessibility representation) for a frame.

        Args:
            frame_id: Target frame ID.

        Returns:
            List of root element dictionaries containing nested children.
        """
        # Fetch elements from SQLite (or REST)
        elements = self.sqlite.get_elements_for_frame(frame_id)
        if not elements and self.rest.api_key:
            try:
                raw_elems = self.rest.get_frame_elements(frame_id)
                for r in raw_elems:
                    bbox = NormalizedBoundingBox.from_bounds(
                        r.get("left_bound") or r.get("left"),
                        r.get("top_bound") or r.get("top"),
                        r.get("width_bound") or r.get("width"),
                        r.get("height_bound") or r.get("height"),
                    )
                    elements.append(
                        ElementRecord(
                            id=r.get("id"),
                            frame_id=frame_id,
                            source=r.get("source", "ocr"),
                            role=r.get("role", "word"),
                            text=r.get("text"),
                            parent_id=r.get("parent_id"),
                            depth=int(r.get("depth") or 0),
                            bbox=bbox,
                            confidence=float(r.get("confidence") or 1.0),
                            sort_order=int(r.get("sort_order") or 0),
                            properties=r.get("properties"),
                            on_screen=bool(r.get("on_screen", True)),
                        )
                    )
            except (ScreenpipeError, OSError) as e:
                logger.debug("Failed to get frame elements via REST: %s", e)

        if not elements:
            return []

        # Index elements by ID
        elem_map: dict[int, ElementRecord] = {}
        for elem in elements:
            if elem.id is not None:
                elem_map[elem.id] = elem

        root_elements: list[ElementRecord] = []
        for elem in elements:
            if elem.parent_id is not None and elem.parent_id in elem_map:
                elem_map[elem.parent_id].children.append(elem)
            else:
                root_elements.append(elem)

        return [r.to_dict(include_children=True) for r in root_elements]

    def get_active_windows(self, limit: int = 10) -> list[dict[str, Any]]:
        """Returns indexed active windows from recorded frames."""
        return self.sqlite.get_active_windows(limit=limit)

    def get_focused_window(self) -> dict[str, Any] | None:
        """Returns the currently or most recently focused window."""
        query = """
            SELECT id as frame_id, timestamp, app_name, window_name, browser_url
            FROM frames
            WHERE focused = 1 AND app_name IS NOT NULL AND app_name != ''
            ORDER BY id DESC
            LIMIT 1
        """
        rows = self.sqlite.execute_query(query, enforce_safety=False)
        if rows:
            return rows[0]
        # Fallback to latest frame
        fallback_query = """
            SELECT id as frame_id, timestamp, app_name, window_name, browser_url
            FROM frames
            WHERE app_name IS NOT NULL AND app_name != ''
            ORDER BY id DESC
            LIMIT 1
        """
        fallback_rows = self.sqlite.execute_query(fallback_query, enforce_safety=False)
        return fallback_rows[0] if fallback_rows else None

    def execute_sql(
        self, query: str, params: tuple | list | dict = ()
    ) -> list[dict[str, Any]]:
        """Executes safe read-only SQL via REST /raw_sql or fallback direct SQLite."""
        sanitized = validate_and_sanitize_sql(query)
        if not self.prefer_direct_sqlite and self.rest.api_key:
            try:
                res = self.rest.raw_sql(sanitized)
                self._fallback_active = False
                return res
            except (
                ScreenpipeConnectionError,
                ScreenpipeAuthError,
                ScreenpipeError,
            ) as e:
                if not self.auto_fallback:
                    raise
                self._fallback_active = True
                self._last_fallback_reason = (
                    f"REST /raw_sql failed ({e}), fell back to direct SQLite."
                )
                logger.warning(self._last_fallback_reason)

        return self.sqlite.execute_query(sanitized, params, enforce_safety=False)

    def get_memories(
        self,
        limit: int = 50,
        tag: str | None = None,
        min_importance: float | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieves episodic memories."""
        if not self.prefer_direct_sqlite and self.rest.api_key:
            try:
                tags_list = [tag] if tag else None
                res = self.rest.get_memories(
                    tags=tags_list, min_importance=min_importance, limit=limit
                )
                self._fallback_active = False
                return res
            except Exception as e:
                if not self.auto_fallback:
                    raise
                self._fallback_active = True
                self._last_fallback_reason = (
                    f"REST get_memories failed ({e}), fell back to direct SQLite."
                )

        memories = self.sqlite.get_memories(
            limit=limit, tag=tag, min_importance=min_importance
        )
        return [m.to_dict() for m in memories]

    def add_memory(
        self,
        content: str,
        source: str = "agent",
        source_context: str | None = None,
        tags: list[str] | None = None,
        importance: float = 0.5,
        frame_id: int | None = None,
    ) -> dict[str, Any]:
        """Adds a memory record via REST."""
        return self.rest.add_memory(
            content=content,
            source=source,
            source_context=source_context,
            tags=tags,
            importance=importance,
            frame_id=frame_id,
        )

    # ========================================================================
    # Async Methods
    # ========================================================================

    async def get_health_status_async(self) -> dict[str, Any]:
        """Asynchronous health probe."""
        return await asyncio.to_thread(self.get_health_status)

    async def get_latest_frame_context_async(
        self, limit: int = 5
    ) -> list[dict[str, Any]]:
        """Asynchronous frame context retrieval."""
        return await asyncio.to_thread(self.get_latest_frame_context, limit)

    async def query_screen_text_async(
        self, query: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Asynchronous text query."""
        return await asyncio.to_thread(self.query_screen_text, query, limit)

    async def parse_element_tree_async(self, frame_id: int) -> list[dict[str, Any]]:
        """Asynchronous element tree construction."""
        return await asyncio.to_thread(self.parse_element_tree, frame_id)

    async def get_active_windows_async(self, limit: int = 10) -> list[dict[str, Any]]:
        """Asynchronous active windows list."""
        return await asyncio.to_thread(self.get_active_windows, limit)

    async def get_focused_window_async(self) -> dict[str, Any] | None:
        """Asynchronous focused window lookup."""
        return await asyncio.to_thread(self.get_focused_window)

    async def execute_sql_async(
        self, query: str, params: tuple | list | dict = ()
    ) -> list[dict[str, Any]]:
        """Asynchronous SQL execution."""
        return await asyncio.to_thread(self.execute_sql, query, params)

    async def get_memories_async(
        self,
        limit: int = 50,
        tag: str | None = None,
        min_importance: float | None = None,
    ) -> list[dict[str, Any]]:
        """Asynchronous memory retrieval."""
        return await asyncio.to_thread(self.get_memories, limit, tag, min_importance)

    async def add_memory_async(
        self,
        content: str,
        source: str = "agent",
        source_context: str | None = None,
        tags: list[str] | None = None,
        importance: float = 0.5,
        frame_id: int | None = None,
    ) -> dict[str, Any]:
        """Asynchronous memory creation."""
        return await asyncio.to_thread(
            self.add_memory, content, source, source_context, tags, importance, frame_id
        )
