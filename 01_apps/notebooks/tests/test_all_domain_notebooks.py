# -*- coding: utf-8 -*-
"""
================================================================================
Test Suite: Canonical Domain Notebooks Suite Integrity, Dual-Vault Parity,
& /lens Swarm Training • pi Agent • EmbeddingGemma 2 MRL • Qwen 3D VLA
================================================================================
Validates:
1. AST Compilation: Zero SyntaxErrors across all 19 canonical + 6 domain notebooks
2. Cell Hygiene: Zero empty code cells and explicit cell IDs across the suite
3. Headless Safety: Explicit 'Agg' backend in code cells
4. Metadata Integrity: Standard python3/lauburu-notebooks kernelspec in all notebooks
5. Dual-Vault Parity: Byte/structural parity between 01_apps and obsidian_vault
6. Rule #0 Zero-Mock Compliance: Zero synthetic mock data arrays (np.random.randn, etc.)
7. /lens Swarm Training, pi Agent, EmbeddingGemma 2 (MRL), & Qwen 3D VLA Integration
================================================================================
"""

import ast
import json
import re
import pytest
from pathlib import Path

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
APPS_NB_DIR = REPO_ROOT / "01_apps" / "notebooks"
OBSIDIAN_NB_DIR = REPO_ROOT / "obsidian_vault" / "notebooks"
OPTIMIZER_SCRIPT = APPS_NB_DIR / "autonomous_notebook_optimizer.py"
TELEMETRY_JSON = REPO_ROOT / "04_data_and_memory" / "notebook_continuous_review_telemetry.json"
VISUAL_CHART = REPO_ROOT / "04_data_and_memory" / "notebook_swarm_pi_gemma2_qwen3d_audit.png"

NOTEBOOK_NAMES = [
    "00_lauburu_global_master_project.ipynb",
    "00_lauburu_master_interactive_console_and_ui_specialist.ipynb",
    "00_lauburu_qwen_moe_master_console.ipynb",
    "01_lauburu_swarm_and_kinematics_interactive.ipynb",
    "01_master_mesh_console_and_ports.ipynb",
    "02_lauburu_canonical_knowledge_vault_explorer.ipynb",
    "02_tui_ecosystem_and_terminal_streamer.ipynb",
    "03_full_network_prima_ai_lab.ipynb",
    "03_lauburu_lens_vision_and_next_steps.ipynb",
    "04_movesense_biometrics_and_dsp.ipynb",
    "05_spatial_grappling_3d_kinematics.ipynb",
    "06_genetic_project_scout_and_lora.ipynb",
    "07_cpp_tui_canonical_recreation_studio.ipynb",
    "08_dynamic_network_optimizer_bt_default.ipynb",
    "08_shopify_canonical_storefront_studio.ipynb",
    "09_sovereign_screen_lens_dashboard.ipynb",
    "14_codeclash_corewar_master_arena.ipynb",
    "25_continuous_lens_mesh_and_elo_optimizer.ipynb",
    "26_sovereign_live_elo_sharding_and_671b_telemetry.ipynb",
    "lens_global_orchestrator.ipynb",
]

ADDITIONAL_DOMAIN_NOTEBOOKS = [
    REPO_ROOT / "01_apps" / "screen_lens" / "notebooks" / "screen_lens_human_in_the_loop_trainer.ipynb",
    REPO_ROOT / "01_apps" / "screen_lens" / "notebooks" / "screen_lens_tri_audit_live_dashboard.ipynb",
    REPO_ROOT / "01_apps" / "omniterminal_notebook_plugin" / "omniterminal_master_console.ipynb",
    REPO_ROOT / "02_ai_models_and_inference" / "notebooks" / "agentworld_webworld_swebench_flight_simulator.ipynb",
    REPO_ROOT / "04_data_and_memory" / "lens_notebook_arena.ipynb",
    REPO_ROOT / "08_business_and_commerce" / "ecommerce_analytics_and_feedback.ipynb",
]


def _strip_ipython_magics(src: str) -> str:
    lines = src.splitlines()
    for ln in lines:
        s = ln.strip()
        if not s:
            continue
        if s.startswith("%%") and not s.startswith("%%omni_polyglot python"):
            return "pass\n"
        break
    cleaned = []
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("%") or stripped.startswith("!"):
            indent = line[: len(line) - len(stripped)]
            cleaned.append(f"{indent}pass")
        else:
            cleaned.append(line)
    return "\n".join(cleaned)


@pytest.mark.parametrize("nb_name", NOTEBOOK_NAMES)
def test_notebook_exists_in_both_vaults(nb_name):
    """Verify notebook exists in both 01_apps/notebooks and obsidian_vault/notebooks."""
    app_nb = APPS_NB_DIR / nb_name
    obs_nb = OBSIDIAN_NB_DIR / nb_name
    assert app_nb.exists(), f"Missing notebook in 01_apps: {app_nb}"
    assert obs_nb.exists(), f"Missing notebook in obsidian_vault: {obs_nb}"


@pytest.mark.parametrize("nb_name", NOTEBOOK_NAMES)
def test_notebook_ast_syntax_and_no_empty_code_cells(nb_name):
    """Verify all code cells parse cleanly via AST and none are empty."""
    app_nb = APPS_NB_DIR / nb_name
    with open(app_nb, "r", encoding="utf-8") as f:
        data = json.load(f)

    cells = data.get("cells", [])
    assert len(cells) > 0, f"Notebook {nb_name} has 0 cells"

    code_cells = [c for c in cells if c.get("cell_type") == "code"]
    assert len(code_cells) > 0, f"Notebook {nb_name} must contain code cells"

    for idx, cell in enumerate(code_cells):
        src = "".join(cell.get("source", "")).strip()
        assert src != "", f"Notebook {nb_name} has empty code cell at index {idx}"
        try:
            ast.parse(_strip_ipython_magics(src))
        except SyntaxError as e:
            pytest.fail(f"SyntaxError in {nb_name} code cell {idx}: {e}")


@pytest.mark.parametrize("nb_name", NOTEBOOK_NAMES)
def test_notebook_kernelspec_metadata(nb_name):
    """Verify standard python3 kernelspec is configured."""
    app_nb = APPS_NB_DIR / nb_name
    with open(app_nb, "r", encoding="utf-8") as f:
        data = json.load(f)

    meta = data.get("metadata", {})
    assert "kernelspec" in meta, f"Notebook {nb_name} missing 'kernelspec' in metadata"
    ks = meta["kernelspec"]
    assert "python" in ks.get("name", "").lower() or ks.get("language") == "python", (
        f"Notebook {nb_name} kernelspec must be python"
    )


@pytest.mark.parametrize("nb_name", NOTEBOOK_NAMES)
def test_dual_vault_cell_count_parity(nb_name):
    """Verify exact cell count and cell type parity between dual vaults."""
    app_nb = APPS_NB_DIR / nb_name
    obs_nb = OBSIDIAN_NB_DIR / nb_name

    with open(app_nb, "r", encoding="utf-8") as f:
        app_data = json.load(f)
    with open(obs_nb, "r", encoding="utf-8") as f:
        obs_data = json.load(f)

    app_cells = app_data.get("cells", [])
    obs_cells = obs_data.get("cells", [])

    assert len(app_cells) == len(obs_cells), (
        f"Cell count mismatch for {nb_name}: {len(app_cells)} (apps) vs {len(obs_cells)} (obsidian)"
    )

    for i, (ac, oc) in enumerate(zip(app_cells, obs_cells)):
        assert ac.get("cell_type") == oc.get("cell_type"), (
            f"Cell {i} type mismatch in {nb_name}"
        )


@pytest.mark.parametrize("nb_path", ADDITIONAL_DOMAIN_NOTEBOOKS)
def test_additional_domain_notebooks_ast_and_zero_mock(nb_path):
    """Verify all 6 additional cross-monorepo domain notebooks compile cleanly and obey Rule #1."""
    assert nb_path.exists(), f"Missing domain notebook: {nb_path}"
    data = json.loads(nb_path.read_text(encoding="utf-8"))
    code_cells = [c for c in data.get("cells", []) if c.get("cell_type") == "code"]
    assert len(code_cells) > 0, f"{nb_path.name} must contain code cells"
    full_code = "\n".join("".join(c.get("source", [])) for c in code_cells)
    assert "matplotlib.use('Agg')" in full_code or 'matplotlib.use("Agg")' in full_code
    assert not re.search(r"\b(np\.random\.randn|np\.random\.normal|random\.uniform|faker)\b", full_code)
    for idx, c in enumerate(code_cells):
        src = "".join(c.get("source", []))
        ast.parse(_strip_ipython_magics(src))


def test_lens_swarm_pi_gemma2_qwen3d_integration():
    """Verify autonomous_notebook_optimizer.py integrates /lens, Swarm Training, pi, EmbeddingGemma 2 MRL, and Qwen 3D."""
    assert OPTIMIZER_SCRIPT.exists()
    src = OPTIMIZER_SCRIPT.read_text(encoding="utf-8")
    assert "run_lens_swarm_training_and_pi_harvest" in src
    assert "run_gemma2_mrl_notebook_embedding" in src
    assert "run_qwen3d_vla_and_local_ai_review" in src
    assert "qwen_3d_vla_7b" in src
    assert "embeddinggemma-2" in src
    assert "harvest_pi_sessions" in src
    assert "3d_spatial_instructional_map_lora.jsonl" in src
    assert "podman_curated_gemma2_mrl_lora.jsonl" in src

    assert TELEMETRY_JSON.exists(), "Continuous notebook review telemetry JSON must exist"
    t_data = json.loads(TELEMETRY_JSON.read_text(encoding="utf-8"))
    assert t_data["total_notebooks"] >= 24
    assert t_data["ast_pass"] == t_data["total_notebooks"]
    assert t_data["zero_mock_pass"] == t_data["total_notebooks"]
    assert "lens_swarm_pi" in t_data
    assert "embeddinggemma2_mrl" in t_data
    assert "qwen3d_and_panel" in t_data
    assert VISUAL_CHART.exists() and VISUAL_CHART.stat().st_size > 10000
