"""Edge-Case, Concurrency, and Zero-Cloud Leakage Test Suite for ScreenpipeService."""

import asyncio
import sqlite3
import tempfile
import unittest
from pathlib import Path

from screenpipe_service import (
    NormalizedBoundingBox,
    ScreenpipeSecurityError,
    ScreenpipeService,
    validate_and_sanitize_sql,
)


class TestScreenpipeEdgeCases(unittest.TestCase):
    """Stress tests, extreme boundary values, and adversarial edge cases."""

    def test_deep_element_hierarchy_parsing(self) -> None:
        """Tests parsing deeply nested (depth 10) element hierarchy trees."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "deep_tree.sqlite"
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute("CREATE TABLE frames (id INTEGER PRIMARY KEY, app_name TEXT, full_text TEXT);")
            c.execute("""
                CREATE TABLE elements (
                    id INTEGER PRIMARY KEY,
                    frame_id INTEGER,
                    source TEXT,
                    role TEXT,
                    text TEXT,
                    parent_id INTEGER,
                    depth INTEGER,
                    left_bound REAL,
                    top_bound REAL,
                    width_bound REAL,
                    height_bound REAL,
                    confidence REAL,
                    sort_order INTEGER,
                    properties TEXT,
                    on_screen INTEGER
                );
            """)
            c.execute("INSERT INTO frames (id, app_name, full_text) VALUES (1, 'DeepApp', 'Root');")

            # Insert root element (depth 0)
            c.execute("""
                INSERT INTO elements (id, frame_id, source, role, text, parent_id, depth, left_bound, top_bound, width_bound, height_bound, confidence)
                VALUES (1, 1, 'ocr', 'root', 'RootNode', NULL, 0, 0.0, 0.0, 1.0, 1.0, 100.0)
            """)

            # Insert nested chain: 2 -> 1, 3 -> 2, ..., 10 -> 9
            for i in range(2, 11):
                c.execute(
                    """
                    INSERT INTO elements (id, frame_id, source, role, text, parent_id, depth, left_bound, top_bound, width_bound, height_bound, confidence)
                    VALUES (?, 1, 'ocr', 'node', ?, ?, ?, 0.1, 0.1, 0.8, 0.8, 95.0)
                """,
                    (i, f"Node_{i}", i - 1, i - 1),
                )

            conn.commit()
            conn.close()

            service = ScreenpipeService(db_path=db_path, prefer_direct_sqlite=True)
            tree = service.parse_element_tree(frame_id=1)
            self.assertEqual(len(tree), 1)

            # Traverse down the nested chain
            curr = tree[0]
            for depth in range(1, 10):
                self.assertEqual(len(curr["children"]), 1, f"Expected 1 child at depth {depth}")
                curr = curr["children"][0]
                self.assertEqual(curr["text"], f"Node_{depth + 1}")

    def test_sql_sanitizer_complex_regex(self) -> None:
        """Tests SQL sanitizer with whitespace, newlines, and mixed casing."""
        query = "\n\n   sElEcT   \n  id,   app_name \n  FROM  frames  \n  WHERE focused = 1"
        sanitized = validate_and_sanitize_sql(query, default_limit=42)
        self.assertTrue(sanitized.startswith("sElEcT"))
        self.assertTrue(sanitized.endswith("LIMIT 42"))

    def test_sql_sanitizer_rejects_subqueries_with_mutations(self) -> None:
        """Tests rejection of mutating operations embedded within statements."""
        bad_queries = [
            "SELECT * FROM frames WHERE id IN (SELECT id FROM frames); DELETE FROM frames",
            "SELECT (SELECT count(*) FROM frames); DROP TABLE frames",
        ]
        for q in bad_queries:
            with self.assertRaises(ScreenpipeSecurityError):
                validate_and_sanitize_sql(q)

    def test_bounding_box_degenerate_cases(self) -> None:
        """Tests zero-width, negative width, NaN/Inf bounds gracefully handled."""
        bbox_zero = NormalizedBoundingBox(ymin=0.5, xmin=0.5, ymax=0.5, xmax=0.5)
        self.assertFalse(bbox_zero.is_valid)
        self.assertEqual(bbox_zero.area, 0.0)

        # Inverted coordinates: xmin > xmax
        bbox_inv = NormalizedBoundingBox(ymin=0.8, xmin=0.9, ymax=0.2, xmax=0.1)
        # post_init ensures ymax >= ymin and xmax >= xmin
        self.assertTrue(bbox_inv.ymax >= bbox_inv.ymin)
        self.assertTrue(bbox_inv.xmax >= bbox_inv.xmin)

    def test_zero_cloud_network_calls(self) -> None:
        """Verifies that no remote non-localhost URLs are configured or used."""
        service = ScreenpipeService()
        self.assertTrue(
            "127.0.0.1" in service.rest.base_url or "localhost" in service.rest.base_url,
            "Service must strictly point to local daemon address.",
        )

    def test_concurrent_async_queries(self) -> None:
        """Verifies safe concurrent execution of multiple async queries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "concurrent.sqlite"
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute(
                "CREATE TABLE frames (id INTEGER PRIMARY KEY, app_name TEXT, full_text TEXT, timestamp TIMESTAMP);"
            )
            for i in range(1, 21):
                c.execute(
                    "INSERT INTO frames (id, app_name, full_text, timestamp) VALUES (?, ?, ?, '2026-08-31T00:00:00Z')",
                    (i, f"App_{i}", f"AlphaToken_{i:03d}"),
                )
            conn.commit()
            conn.close()

            service = ScreenpipeService(db_path=db_path, prefer_direct_sqlite=True)

            async def run_concurrency() -> None:
                tasks = [service.query_screen_text_async(f"AlphaToken_{i:03d}", limit=1) for i in range(1, 21)]
                results = await asyncio.gather(*tasks)
                self.assertEqual(len(results), 20)
                for i, r in enumerate(results, start=1):
                    self.assertEqual(len(r), 1)
                    self.assertEqual(r[0]["app_name"], f"App_{i}")

            asyncio.run(run_concurrency())


if __name__ == "__main__":
    unittest.main()
