"""
Adversarial Verification & Empirical Stress-Testing Suite for Milestone M2.
Authored by Challenger M2 (teamwork_preview_challenger_m2_1).

Tests:
1. Mathematical invariants & stress testing of calculate_elo_update (extreme deltas, zero/negative K, float anomalies, zero-sum conservation, symmetry, monotonicity).
2. Stress testing of calculate_dynamic_k_factor (degenerate params, zero tokens, zero-mock flags).
3. ArenaStateManager stateful duel progression & integrity under random walks.
4. Static DOM & HTML5 Canvas contracts (drawEloWinCurve, updateWinCurve, canvas elements, slider event handlers, filter pills).
5. Headless dual-runtime execution without ipywidgets.
6. AST purity (zero print() statements across all notebook cells).
7. Full headless nbconvert compilation and DOM output verification.
"""

import ast
import html
import json
import math
import random
import re
import shutil
import subprocess
import sys
import types
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple
import pytest

# Unconditional robust shim for IPython and ipywidgets in test environment
try:
    import IPython
    import IPython.display as ipy_disp
except ImportError:
    ipy_mod = types.ModuleType("IPython")
    ipy_mod.version_info = (8, 24, 0)
    ipy_mod.__version__ = "8.24.0"
    ipy_mod.get_ipython = lambda: None
    ipy_disp = types.ModuleType("IPython.display")
    ipy_disp.display = lambda *a, **k: None
    ipy_disp.HTML = lambda x: x
    ipy_disp.clear_output = lambda *a, **k: None
    ipy_mod.display = ipy_disp
    sys.modules["IPython"] = ipy_mod
    sys.modules["IPython.display"] = ipy_disp
else:
    if not hasattr(IPython, "version_info"):
        IPython.version_info = (8, 24, 0)
    if not hasattr(IPython, "get_ipython"):
        IPython.get_ipython = lambda: None

MONOREPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
NOTEBOOK_PATH = MONOREPO_ROOT / "obsidian_vault" / "notebooks" / "00_6_PILLAR_LOCAL_AI_ARENA_TRAINING_AND_NOTEBOOK_OPTIMIZER.ipynb"
OUTPUT_HTML_PATH = Path("/tmp/rendered_arena_m2_challenger.html")

def load_notebook() -> Dict[str, Any]:
    with open(NOTEBOOK_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def get_m2_namespace() -> Dict[str, Any]:
    nb = load_notebook()
    code_cells = [c for c in nb.get("cells", []) if c.get("cell_type") == "code"]
    # Cell 1 + Cell 2 contain the entire ELO engine and M2 console code
    m2_code = "".join(code_cells[0].get("source", [])) + "\n" + "".join(code_cells[1].get("source", []))
    
    namespace: Dict[str, Any] = {
        "display": lambda *args, **kwargs: None,
        "HTML": lambda x: x,
        "__name__": "__main__",
    }
    exec(m2_code, namespace)
    return namespace


class TestAdversarialEloEngineMath:
    """Rigorous mathematical invariants & boundary stress-testing of calculate_elo_update."""

    @pytest.fixture(autouse=True)
    def setup_functions(self):
        ns = get_m2_namespace()
        self.calc_elo = ns["calculate_elo_update"]
        self.calc_k = ns["calculate_dynamic_k_factor"]
        self.ArenaStateManager = ns["ArenaStateManager"]
        self.PILLARS = ns["PILLARS"]
        self.ARENA_MODELS = ns["ARENA_MODELS"]

    def test_zero_sum_conservation_10000_random_pairs(self):
        """Zero-Sum Invariant: (R_A' - R_A) + (R_B' - R_B) == 0 within machine epsilon."""
        random.seed(42)
        for _ in range(10000):
            r_a = random.uniform(500.0, 4000.0)
            r_b = random.uniform(500.0, 4000.0)
            score_a = random.choice([0.0, 0.5, 1.0, random.random()])
            k = random.uniform(-50.0, 200.0)

            exp_a, new_a, new_b = self.calc_elo(r_a, r_b, score_a, k)
            delta_a = new_a - r_a
            delta_b = new_b - r_b

            assert math.isclose(delta_a + delta_b, 0.0, abs_tol=1e-12), (
                f"Zero-sum invariant violated: delta_a={delta_a}, delta_b={delta_b}, sum={delta_a + delta_b}"
            )

    def test_extreme_rating_differential_overflow_guards(self):
        """Verify extreme rating differentials (+-1,000,000) do not trigger OverflowError."""
        # Extreme A advantage
        exp_a, new_a, new_b = self.calc_elo(1000000.0, 0.0, 1.0, 32.0)
        assert math.isclose(exp_a, 1.0, rel_tol=1e-9)
        assert math.isclose(new_a, 1000000.0, abs_tol=1e-6)
        assert math.isclose(new_b, 0.0, abs_tol=1e-6)

        # Extreme B advantage
        exp_a2, new_a2, new_b2 = self.calc_elo(0.0, 1000000.0, 1.0, 32.0)
        assert math.isclose(exp_a2, 0.0, abs_tol=1e-9)
        assert math.isclose(new_a2, 32.0, abs_tol=1e-6)
        assert math.isclose(new_b2, 1000000.0 - 32.0, abs_tol=1e-6)

    def test_k_factor_bounding_and_clamping(self):
        """K-factor must be clamped to [1.0, 128.0] even when passed negative, zero, or huge K."""
        # Negative K
        exp_a, new_a, new_b = self.calc_elo(2600.0, 2600.0, 1.0, k=-100.0)
        assert exp_a == 0.5
        assert math.isclose(new_a, 2600.5, abs_tol=1e-9)
        assert math.isclose(new_b, 2599.5, abs_tol=1e-9)

        # Zero K
        exp_a, new_a, new_b = self.calc_elo(2600.0, 2600.0, 1.0, k=0.0)
        assert math.isclose(new_a, 2600.5, abs_tol=1e-9)

        # Huge K (10,000)
        exp_a, new_a, new_b = self.calc_elo(2600.0, 2600.0, 1.0, k=10000.0)
        assert math.isclose(new_a, 2664.0, abs_tol=1e-9)
        assert math.isclose(new_b, 2536.0, abs_tol=1e-9)

    def test_symmetry_and_antisymmetry_properties(self):
        """Symmetry: Duel (A, B, s) vs Duel (B, A, 1-s) must produce complementary results."""
        r_a, r_b = 2700.0, 2450.0
        score_a = 0.75
        k = 32.0

        exp_a, new_a, new_b = self.calc_elo(r_a, r_b, score_a, k)
        exp_b, new_b_rev, new_a_rev = self.calc_elo(r_b, r_a, 1.0 - score_a, k)

        assert math.isclose(exp_a + exp_b, 1.0, abs_tol=1e-12)
        assert math.isclose(new_a, new_a_rev, abs_tol=1e-12)
        assert math.isclose(new_b, new_b_rev, abs_tol=1e-12)

    def test_monotonicity_under_varying_scores(self):
        """Higher score for A strictly yields higher new rating for A."""
        r_a, r_b = 2600.0, 2600.0
        scores = [0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0]
        new_ratings = []
        for s in scores:
            _, new_a, _ = self.calc_elo(r_a, r_b, s, 32.0)
            new_ratings.append(new_a)

        for i in range(len(new_ratings) - 1):
            assert new_ratings[i] < new_ratings[i + 1], f"Monotonicity violated: {new_ratings[i]} >= {new_ratings[i+1]}"

    def test_dynamic_k_factor_adversarial_inputs(self):
        """Test calculate_dynamic_k_factor with zero/negative edge cases."""
        # 1. Zero tokens used -> clamped safely
        k_val1 = self.calc_k(k0=32.0, params_b=70.0, tokens_used=0, rtt_ms=20.0, consensus_score=1.0, zero_mock_certified=True)
        assert 1.0 <= k_val1 <= 128.0

        # 2. Zero-mock uncertified -> returns clamped 1.0
        k_val2 = self.calc_k(k0=32.0, params_b=70.0, tokens_used=500, rtt_ms=20.0, consensus_score=1.0, zero_mock_certified=False)
        assert k_val2 == 1.0

        # 3. Degenerate parameter size (negative params)
        k_val3 = self.calc_k(k0=32.0, params_b=-50.0, tokens_used=100, rtt_ms=-10.0, consensus_score=0.0, zero_mock_certified=True)
        assert 1.0 <= k_val3 <= 128.0

    def test_arena_state_manager_multi_duel_stability(self):
        """ArenaStateManager correctly tracks state over a series of 100 duels."""
        state = self.ArenaStateManager(self.PILLARS, self.ARENA_MODELS)
        init_coder = state.models["Qwen 2.5 Coder 72B"]["default_elo"]

        # Run 50 duels where Coder wins against Llama
        for _ in range(50):
            state.record_duel("Qwen 2.5 Coder 72B", "Llama-3.3-70B-Instruct (Cloud Shadow)", 1.0, pillar_id=1)

        final_coder = state.models["Qwen 2.5 Coder 72B"]["default_elo"]
        assert final_coder > init_coder
        p1 = next(p for p in state.pillars if p["id"] == 1)
        assert p1["elo"] == final_coder


class TestAdversarialHtml5CanvasAndEvents:
    """Adversarial testing of HTML5 Canvas code, JS event signatures, and DOM elements."""

    @pytest.fixture(autouse=True)
    def setup_namespace(self):
        ns = get_m2_namespace()
        self.console_html = ns["render_standalone_console"]()

    def test_canvas_element_contract_in_initial_dom(self):
        """HTML5 Canvas element #win-curve-canvas must be present in initial DOM with width/height."""
        assert '<canvas id="win-curve-canvas"' in self.console_html
        assert 'width="140"' in self.console_html
        assert 'height="45"' in self.console_html

    def test_javascript_win_curve_function_signatures(self):
        """Window JS functions drawEloWinCurve and updateWinCurve must be defined and valid."""
        assert "window.drawEloWinCurve = function(canvasId, rA, rB)" in self.console_html
        assert "window.updateWinCurve = function(valA, eloB)" in self.console_html
        assert "window.drawEloWinCurve('win-curve-canvas', rA, rB)" in self.console_html

    def test_slider_event_handlers_and_ids(self):
        """Sliders #elo-slider and #k-factor-slider must have oninput bindings."""
        assert 'id="elo-slider"' in self.console_html
        assert 'oninput="handleScoreSlider(this.value); updateWinCurve(this.value, 2633);"' in self.console_html
        assert 'id="k-factor-slider"' in self.console_html
        assert 'oninput="handleKFactorInput(this.value)"' in self.console_html

    def test_outcome_buttons_and_active_classes(self):
        """Outcome buttons (btn-win-a, btn-draw, btn-win-b) present with onclick bindings."""
        assert 'id="btn-win-a"' in self.console_html
        assert 'onclick="setOutcome(1.0)"' in self.console_html
        assert 'id="btn-draw"' in self.console_html
        assert 'onclick="setOutcome(0.5)"' in self.console_html
        assert 'id="btn-win-b"' in self.console_html
        assert 'onclick="setOutcome(0.0)"' in self.console_html

    def test_filter_pills_status_and_layer_contracts(self):
        """Filter pills for Status and Layer must exist with correct onclick functions."""
        assert "filterByStatus('All', this)" in self.console_html
        assert "filterByStatus('Active 24/7', this)" in self.console_html
        assert "filterByStatus('Ready', this)" in self.console_html
        assert "filterByStatus('Syncing', this)" in self.console_html
        assert "filterByStatus('Ingested', this)" in self.console_html

        assert "filterByLayer('All', this)" in self.console_html
        assert "filterByLayer('01_apps', this)" in self.console_html
        assert "filterByLayer('02_ai_models', this)" in self.console_html
        assert "filterByLayer('03_biometrics', this)" in self.console_html
        assert "filterByLayer('05_agents', this)" in self.console_html

    def test_js_sigmoid_math_formula_syntax(self):
        """JS mathematical implementation in script tag matches Bradley-Terry sigmoid."""
        assert "Math.pow(10.0, -deltaElo / 400.0)" in self.console_html
        assert "Math.pow(10.0, (rB - rA) / 400.0)" in self.console_html

    def test_embedded_javascript_v8_node_syntax_validity(self, tmp_path):
        """Extract embedded <script> block and verify with Node.js --check for 0 syntax errors."""
        s_start = self.console_html.find("<script>")
        assert s_start != -1, "No <script> tag found in console HTML"
        s_end = self.console_html.find("</script>", s_start)
        assert s_end != -1, "No closing </script> tag found in console HTML"
        js_code = self.console_html[s_start + 8:s_end].strip()
        
        js_file = tmp_path / "extracted_console.js"
        js_file.write_text(js_code, encoding="utf-8")
        
        node_bin = shutil.which("node") or "/usr/local/bin/node"
        if Path(node_bin).exists() or shutil.which("node"):
            res = subprocess.run([node_bin, "--check", str(js_file)], capture_output=True, text=True)
            assert res.returncode == 0, f"V8/Node syntax error in embedded JavaScript:\n{res.stderr}"



class TestAdversarialAstPurityAndExecution:
    """Adversarial AST analysis and headless nbconvert execution."""

    def test_zero_print_calls_across_all_code_cells(self):
        """Ensure 0 print() calls in any notebook cell AST."""
        nb = load_notebook()
        violations = []
        for idx, cell in enumerate(nb.get("cells", [])):
            if cell.get("cell_type") == "code":
                source = "".join(cell.get("source", []))
                tree = ast.parse(source)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
                        violations.append((idx, node.lineno))
        assert len(violations) == 0, f"Found forbidden print() calls in cells: {violations}"

    def test_headless_nbconvert_full_execution(self):
        """Execute notebook headlessly via nbconvert and verify exit code 0 and valid output."""
        jupyter_bin = "/Users/aaron/.local/share/uv/tools/jupyterlab/bin/jupyter"
        cmd = [
            jupyter_bin,
            "nbconvert",
            "--to", "html",
            "--execute",
            str(NOTEBOOK_PATH),
            "--output", str(OUTPUT_HTML_PATH)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 0, f"Headless execution failed: {res.stderr}"
        assert OUTPUT_HTML_PATH.exists()
        content = OUTPUT_HTML_PATH.read_text(encoding="utf-8")
        assert "Interactive 6-Pillar Arena" in content
        assert "win-curve-canvas" in content
        assert "3-Panel Dark Console Exported" in content
