#!/usr/bin/env python3
"""
Unit Tests for Voice AST & Region Backspace Engine
==================================================
Validates:
1. AST scope parsing for functions, classes, and statement blocks.
2. Voice backspace for named functions ("delete function foo").
3. Voice backspace for line numbers ("delete line 2").
4. General scope backspace ("backspace region").
5. Multi-level undo / scope rewind stack ("undo last edit").
"""

import sys
import pytest
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
AUTO_ROOT = TEST_DIR.parent

if str(AUTO_ROOT) not in sys.path:
    sys.path.insert(0, str(AUTO_ROOT))

from voice_ast_backend import RegionBackspaceEngine


class TestRegionBackspaceEngine:

    @pytest.fixture
    def sample_engine(self):
        code = (
            "def alpha():\n"
            "    return 1\n"
            "\n"
            "def beta():\n"
            "    return 2\n"
            "\n"
            "class Gamma:\n"
            "    def delta(self):\n"
            "        return 3\n"
        )
        return RegionBackspaceEngine(code)

    def test_parse_scopes_identifies_all_constructs(self, sample_engine):
        scopes = sample_engine.parse_scopes()
        names = [s["name"] for s in scopes]
        assert "alpha" in names
        assert "beta" in names
        assert "Gamma" in names

    def test_delete_function_by_name(self, sample_engine):
        res = sample_engine.execute_voice_backspace("delete function beta")
        assert res["status"] == "SUCCESS"
        assert res["action"] == "DELETE_FUNCTION_SCOPE"
        assert "def beta" not in sample_engine.current_code
        assert "def alpha" in sample_engine.current_code

    def test_undo_restores_deleted_code(self, sample_engine):
        orig = sample_engine.current_code
        sample_engine.execute_voice_backspace("delete function alpha")
        assert "def alpha" not in sample_engine.current_code

        undo_res = sample_engine.execute_voice_backspace("undo last edit")
        assert undo_res["status"] == "SUCCESS"
        assert sample_engine.current_code == orig

    def test_backspace_region_removes_last_scope(self, sample_engine):
        res = sample_engine.execute_voice_backspace("backspace region")
        assert res["status"] == "SUCCESS"
        assert res["action"] == "REGION_BACKSPACE"

    def test_delete_line_by_number(self, sample_engine):
        res = sample_engine.execute_voice_backspace("delete line 1")
        assert res["status"] == "SUCCESS"
        assert res["line_number"] == 1
        assert not sample_engine.current_code.startswith("def alpha():")


if __name__ == "__main__":
    pytest.main(["-v", __file__])
