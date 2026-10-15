import pytest
import sys
import os
import sqlite3
from pathlib import Path

# Add src and android_pixel to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "android_pixel")))

from pixel_accessibility_lens_bridge import (
    PixelAccessibilityBridge,
    AccessibilityNode,
    DEFAULT_FIXTURE_PATH
)


@pytest.fixture
def bridge(tmp_path):
    """Provides a PixelAccessibilityBridge instance with an isolated test SQLite database."""
    test_db = tmp_path / "test_screen_lens.sqlite"
    return PixelAccessibilityBridge(db_path=test_db)


@pytest.fixture
def xml_fixture_text():
    """Reads the authentic Pixel 10 Pro XL fixture XML from disk."""
    assert DEFAULT_FIXTURE_PATH.exists(), f"Authentic fixture missing: {DEFAULT_FIXTURE_PATH}"
    return DEFAULT_FIXTURE_PATH.read_text(encoding="utf-8")


def test_fixture_integrity_and_node_parsing(bridge, xml_fixture_text):
    """Verifies that the authentic XML fixture parses cleanly into structured nodes."""
    nodes, parse_ms = bridge.parse_xml_content(xml_fixture_text)
    
    assert len(nodes) == 61, f"Expected 61 nodes in authentic fixture, got {len(nodes)}"
    assert parse_ms < 10.0, f"Parsing took too long: {parse_ms:.2f} ms"
    
    # Check packages
    packages = {n.package for n in nodes if n.package}
    assert "com.twitter.android" in packages


def test_bounds_and_centroid_calculation():
    """Verifies mathematical correctness of centroid calculations for touch actuation."""
    # Test typical bounds: [1507,906][1606,1005]
    l, t, r, b, cx, cy, w, h = PixelAccessibilityBridge.parse_bounds("[1507,906][1606,1005]")
    assert l == 1507
    assert t == 906
    assert r == 1606
    assert b == 1005
    assert w == 99
    assert h == 99
    assert cx == 1507 + (99 // 2)  # 1556
    assert cy == 906 + (99 // 2)   # 955

    # Test edge case with empty or invalid bounds
    assert PixelAccessibilityBridge.parse_bounds("") == (0, 0, 0, 0, 0, 0, 0, 0)
    assert PixelAccessibilityBridge.parse_bounds("invalid") == (0, 0, 0, 0, 0, 0, 0, 0)


def test_semantic_icon_grounding(bridge, xml_fixture_text):
    """Verifies that icon semantic descriptions (invisible to optical OCR) are captured."""
    nodes, _ = bridge.parse_xml_content(xml_fixture_text)
    
    # Extract all content-desc attributes where text is empty
    icon_labels = [n.content_desc for n in nodes if n.content_desc and not n.text]
    
    expected_icons = [
        "Reply",
        "Repost",
        "Like",
        "Bookmark",
        "Share",
        "Explain this post with Grok",
        "Post options",
        "Photos",
        "GIF",
        "Open full composer"
    ]
    
    for expected in expected_icons:
        assert expected in icon_labels, f"Expected icon '{expected}' missing from captured labels: {icon_labels}"


def test_interactive_actionable_filtering(bridge, xml_fixture_text):
    """Verifies actionable element filtering and reply text-field discovery."""
    nodes, _ = bridge.parse_xml_content(xml_fixture_text)
    actionable = [n for n in nodes if n.is_actionable]
    
    assert len(actionable) >= 30, f"Expected >= 30 actionable nodes, got {len(actionable)}"
    
    # Locate reply input field
    reply_fields = [n for n in nodes if n.resource_id == "post-detail-reply-text-field"]
    assert len(reply_fields) == 1
    reply_node = reply_fields[0]
    assert reply_node.clickable is True
    assert reply_node.class_name == "android.widget.EditText"
    assert reply_node.centroid_x == 1095
    assert reply_node.centroid_y == 956


def test_sqlite_ingestion_and_fts_readiness(bridge, xml_fixture_text):
    """Verifies ingestion into isolated SQLite database and queryable table structures."""
    nodes, parse_ms = bridge.parse_xml_content(xml_fixture_text)
    event_id = bridge.ingest_to_sqlite(nodes, parse_ms, device_id="pixel_10_pro_xl_test")
    assert event_id > 0

    conn = sqlite3.connect(str(bridge.db_path))
    cur = conn.cursor()
    
    # Check pixel_accessibility_events table
    cur.execute("SELECT device_id, app_package, total_nodes, actionable_nodes, semantic_summary FROM pixel_accessibility_events WHERE id = ?", (event_id,))
    row = cur.fetchone()
    assert row is not None
    assert row[0] == "pixel_10_pro_xl_test"
    assert row[1] == "com.twitter.android"
    assert row[2] == 61
    assert "Explain this post with Grok" in row[4]
    
    # Check frames table
    cur.execute("SELECT app_name, frame_path, ocr_text FROM frames WHERE id = ?", (event_id,))
    frame_row = cur.fetchone()
    assert frame_row is not None
    assert frame_row[0] == "X (Twitter)"
    assert frame_row[1] == "HEADLESS_ACCESSIBILITY_IPC"
    assert "Photos" in frame_row[2]
    
    conn.close()


def test_benchmark_vs_ocr_metrics(bridge, xml_fixture_text):
    """Verifies empirical benchmark measurements and speedup calculations."""
    results = bridge.benchmark_vs_ocr(xml_fixture_text, iterations=20)
    
    assert results["iterations"] == 20
    assert results["accessibility_avg_ms"] < 2.0
    assert results["speedup_factor"] > 200.0  # Typically > 1000x
    assert results["bandwidth_reduction_pct"] > 99.0
    assert results["icon_descs_captured"] >= 10
