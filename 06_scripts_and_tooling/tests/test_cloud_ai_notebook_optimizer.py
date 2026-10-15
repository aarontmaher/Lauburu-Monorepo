#!/usr/bin/env python3
"""
Unit Tests for Cloud AI Notebook Optimizer
==========================================
Validates:
1. Generation of the canonical Qwen MoE Master Console notebook.
2. Full AST parsing and static syntax validation across all code cells.
3. Dual-path synchronization between 01_apps/notebooks and obsidian_vault/notebooks.
"""

import sys
import pytest
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
SCRIPTS_ROOT = TEST_DIR.parent

if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))
if str(SCRIPTS_ROOT / "cloud_and_quota") not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT / "cloud_and_quota"))

from cloud_ai_notebook_optimizer import CloudAINotebookOptimizer


class TestCloudAINotebookOptimizer:

    def test_generate_master_console_notebook(self):
        opt = CloudAINotebookOptimizer()
        nb_path = opt.generate_master_console_notebook()
        assert nb_path.exists()
        assert nb_path.name == "00_lauburu_qwen_moe_master_console.ipynb"

    def test_audit_notebook_passes_ast_validation(self):
        opt = CloudAINotebookOptimizer()
        nb_path = opt.generate_master_console_notebook()
        audit = opt.audit_notebook(nb_path)
        assert audit["ast_syntax_valid"] is True
        assert len(audit["ast_errors"]) == 0
        assert audit["code_cells"] >= 4
        assert audit["status"] == "OPTIMIZED & VERIFIED"

    def test_vault_synchronization(self):
        opt = CloudAINotebookOptimizer()
        opt.generate_master_console_notebook()
        vault_nb = opt.vault_dir / "00_lauburu_qwen_moe_master_console.ipynb"
        assert vault_nb.exists()


if __name__ == "__main__":
    pytest.main(["-v", __file__])
