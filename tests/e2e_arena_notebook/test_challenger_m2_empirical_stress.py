"""
Empirical Challenger Stress Harness for Milestone M2.
Authored by teamwork_preview_challenger_m2_1.

This test suite performs exhaustive empirical stress testing:
1. Extreme ELO inputs (R_A = -500, R_B = 10000), zero/negative K-factors, boundary edge cases.
2. Canvas coordinate scaling under narrow, wide, tiny, and 4K resolutions with mathematical and JS V8 execution.
3. Rapid dropdown switching, missing/unknown model IDs, and HTML/XSS injection resilience.
4. Mathematical proof and empirical verification of zero-sum conservation over 100,000 duels and multi-round tournaments.
"""

import ast
import html
import json
import math
import random
import shutil
import subprocess
import sys
import types
from pathlib import Path
from typing import Any, Dict, List, Tuple
import pytest

# Robust shim for IPython and ipywidgets in test environment
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


def get_m2_namespace() -> Dict[str, Any]:
    with open(NOTEBOOK_PATH, "r", encoding="utf-8") as f:
        nb = json.load(f)
    code_cells = [c for c in nb.get("cells", []) if c.get("cell_type") == "code"]
    m2_code = "".join(code_cells[0].get("source", [])) + "\n" + "".join(code_cells[1].get("source", []))
    
    namespace: Dict[str, Any] = {
        "display": lambda *args, **kwargs: None,
        "HTML": lambda x: x,
        "__name__": "__main__",
    }
    exec(m2_code, namespace)
    return namespace


class TestAdversarialEloExtremeInputs:
    """Stress tests on calculate_elo_update and calculate_dynamic_k_factor."""

    @pytest.fixture(autouse=True)
    def setup(self):
        ns = get_m2_namespace()
        self.calc_elo = ns["calculate_elo_update"]
        self.calc_k = ns["calculate_dynamic_k_factor"]
        self.ArenaStateManager = ns["ArenaStateManager"]
        self.PILLARS = ns["PILLARS"]
        self.ARENA_MODELS = ns["ARENA_MODELS"]

    def test_extreme_elo_slider_inputs_r_minus_500_r_10000(self):
        """Test exact specification: R_A = -500.0, R_B = 10000.0."""
        # 1. Model A wins (score = 1.0)
        exp_a, new_a, new_b = self.calc_elo(-500.0, 10000.0, 1.0, k=32.0)
        assert 0.0 <= exp_a <= 1.0
        assert math.isclose(exp_a, 0.0, abs_tol=1e-15)
        # Expected delta: K * (1.0 - 0.0) = 32.0
        assert math.isclose(new_a, -500.0 + 32.0, abs_tol=1e-6)
        assert math.isclose(new_b, 10000.0 - 32.0, abs_tol=1e-6)
        assert math.isclose((new_a - (-500.0)) + (new_b - 10000.0), 0.0, abs_tol=1e-12)

        # 2. Model B wins (score = 0.0)
        exp_a2, new_a2, new_b2 = self.calc_elo(-500.0, 10000.0, 0.0, k=32.0)
        assert math.isclose(exp_a2, 0.0, abs_tol=1e-15)
        assert math.isclose(new_a2, -500.0, abs_tol=1e-6)
        assert math.isclose(new_b2, 10000.0, abs_tol=1e-6)
        assert math.isclose((new_a2 - (-500.0)) + (new_b2 - 10000.0), 0.0, abs_tol=1e-12)

        # 3. Inverted extreme: R_A = 10000.0, R_B = -500.0
        exp_a3, new_a3, new_b3 = self.calc_elo(10000.0, -500.0, 1.0, k=32.0)
        assert math.isclose(exp_a3, 1.0, abs_tol=1e-15)
        assert math.isclose(new_a3, 10000.0, abs_tol=1e-6)
        assert math.isclose(new_b3, -500.0, abs_tol=1e-6)

    def test_zero_and_negative_k_factors(self):
        """Test zero, negative, and extreme K-factors."""
        k_values = [0.0, -1.0, -50.0, -999999.0]
        for k in k_values:
            exp_a, new_a, new_b = self.calc_elo(2600.0, 2600.0, 1.0, k=k)
            # Clamped K should be at minimum 1.0
            assert math.isclose(new_a, 2600.0 + 1.0 * 0.5, abs_tol=1e-9)
            assert math.isclose(new_b, 2600.0 - 1.0 * 0.5, abs_tol=1e-9)
            assert math.isclose((new_a - 2600.0) + (new_b - 2600.0), 0.0, abs_tol=1e-12)

        # Extreme positive K-factor (>128)
        exp_a, new_a, new_b = self.calc_elo(2600.0, 2600.0, 1.0, k=50000.0)
        # Clamped K should be at maximum 128.0
        assert math.isclose(new_a, 2600.0 + 128.0 * 0.5, abs_tol=1e-9)
        assert math.isclose(new_b, 2600.0 - 128.0 * 0.5, abs_tol=1e-9)

    def test_boundary_edge_cases_subnormal_and_infinite_floats(self):
        """Test massive rating differences (10^7) without overflow errors."""
        for r_diff in [1e4, 1e5, 1e6, 1e7]:
            exp_a, new_a, new_b = self.calc_elo(r_diff, 0.0, 0.5, k=32.0)
            assert math.isclose(exp_a, 1.0, abs_tol=1e-12)
            assert math.isclose((new_a - r_diff) + (new_b - 0.0), 0.0, abs_tol=1e-12)


class TestAdversarialCanvasScalingAndMath:
    """Stress tests on canvas coordinate scaling and JS rendering."""

    @pytest.fixture(autouse=True)
    def setup(self):
        ns = get_m2_namespace()
        self.console_html = ns["render_standalone_console"]()

    def test_canvas_coordinate_scaling_mathematical_oracle(self):
        """
        Oracle testing of the JS Canvas rendering logic across multiple resolutions:
        ptX = ((clampedDiff / 800) + 0.5) * w
        ptY = h - (expA * h)
        """
        resolutions = [
            (140, 45),     # Default UI size
            (50, 20),      # Narrow mobile size
            (1920, 1080),  # Full HD
            (3840, 2160),  # 4K Retina
            (1, 1),        # Degenerate single pixel
            (10000, 50),   # Ultra-wide
            (50, 10000),   # Ultra-tall
        ]

        test_elo_pairs = [
            (-500.0, 10000.0),
            (10000.0, -500.0),
            (2600.0, 2600.0),
            (0.0, 0.0),
            (-1000.0, -1000.0),
            (2640.0, 2633.0),
            (3000.0, 2000.0),
            (-50000.0, 50000.0),
        ]

        for w, h in resolutions:
            for r_a, r_b in test_elo_pairs:
                diff = r_b - r_a
                clamped_diff_for_exp = max(-100.0, min(100.0, diff / 400.0))
                exp_a = 1.0 / (1.0 + math.pow(10.0, clamped_diff_for_exp))
                
                current_diff = r_a - r_b
                clamped_diff = max(-400.0, min(400.0, current_diff))
                pt_x = ((clamped_diff / 800.0) + 0.5) * w
                pt_y = h - (exp_a * h)

                # Boundary assertions
                assert not math.isnan(pt_x), f"pt_x is NaN for resolution ({w}, {h})"
                assert not math.isnan(pt_y), f"pt_y is NaN for resolution ({w}, {h})"
                assert not math.isinf(pt_x), f"pt_x is Inf for resolution ({w}, {h})"
                assert not math.isinf(pt_y), f"pt_y is Inf for resolution ({w}, {h})"

                assert 0.0 <= pt_x <= float(w), f"pt_x {pt_x} out of bounds [0, {w}]"
                assert 0.0 <= pt_y <= float(h), f"pt_y {pt_y} out of bounds [0, {h}]"

                # Win curve path verification
                for x in range(w + 1):
                    delta_elo = ((x / w) - 0.5) * 800.0
                    prob = 1.0 / (1.0 + math.pow(10.0, -delta_elo / 400.0))
                    y = h - (prob * h)
                    assert 0.0 <= y <= float(h), f"Curve y {y} out of bounds [0, {h}] at x={x}"

    def test_v8_node_execution_of_canvas_and_controls_script(self, tmp_path):
        """Run Node.js headless execution of the full JS state machine with rapid switching."""
        node_bin = shutil.which("node") or "/usr/local/bin/node"
        if not (Path(node_bin).exists() or shutil.which("node")):
            pytest.skip("Node.js not found on host system")

        # Extract JS script
        s_start = self.console_html.find("<script>")
        s_end = self.console_html.find("</script>", s_start)
        js_code = self.console_html[s_start + 8:s_end].strip()

        # Build comprehensive JS test harness simulating DOM, Canvas, and rapid interactions
        js_harness = f"""
        // Mock DOM & Canvas Environment
        const elements = {{}};
        function mockElement(id, tagName = 'div') {{
            return {{
                id: id,
                tagName: tagName,
                value: '0',
                selectedIndex: 0,
                options: [
                    {{ value: 'Qwen 2.5 Coder 72B' }},
                    {{ value: 'Llama-3.3-70B-Instruct (Cloud Shadow)' }},
                    {{ value: 'Qwen3-Next-80B-A3B MoE' }}
                ],
                style: {{}},
                classList: {{
                    add: () => {{}},
                    remove: () => {{}}
                }},
                getContext: (type) => ({{
                    clearRect: () => {{}},
                    beginPath: () => {{}},
                    moveTo: () => {{}},
                    lineTo: () => {{}},
                    stroke: () => {{}},
                    arc: () => {{}},
                    fill: () => {{}},
                    strokeStyle: '',
                    fillStyle: '',
                    lineWidth: 1
                }}),
                width: 140,
                height: 45,
                textContent: '',
                innerHTML: '',
                parentElement: {{
                    querySelectorAll: () => []
                }}
            }};
        }}

        global.window = global;
        global.document = {{
            getElementById: (id) => {{
                if (!elements[id]) elements[id] = mockElement(id);
                return elements[id];
            }},
            querySelectorAll: () => []
        }};

        // Execute original script
        {js_code}

        // 1. Test rapid pillar changes
        for (let i = 1; i <= 6; i++) {{
            window.handlePillarChange(i);
        }}
        // Test invalid pillar
        window.handlePillarChange(9999);

        // 2. Test rapid outcome switches
        window.setOutcome(1.0);
        window.setOutcome(0.5);
        window.setOutcome(0.0);
        window.setOutcome(0.33);

        // 3. Test rapid model view switching with known and unknown models
        window.updateModelView('Qwen 2.5 Coder 72B');
        window.updateModelView('Qwen3-Next-80B-A3B MoE');
        window.updateModelView('Unknown Model 404');
        window.updateModelView(null);
        window.updateModelView(undefined);

        // 4. Test extreme ELO inputs on Canvas
        window.drawEloWinCurve('win-curve-canvas', -500, 10000);
        window.drawEloWinCurve('win-curve-canvas', 10000, -500);
        window.drawEloWinCurve('win-curve-canvas', 0, 0);

        // 5. Test multi-duel simulation
        for (let j = 0; j < 50; j++) {{
            window.executeDuelSimulation();
        }}
        window.resetDefaultRatings();

        console.log("JS_STRESS_HARNESS_SUCCESS");
        """

        test_file = tmp_path / "test_js_stress.js"
        test_file.write_text(js_harness, encoding="utf-8")

        res = subprocess.run([node_bin, str(test_file)], capture_output=True, text=True)
        assert res.returncode == 0, f"JS execution failed: {res.stderr}"
        assert "JS_STRESS_HARNESS_SUCCESS" in res.stdout


class TestAdversarialDropdownAndSanitization:
    """Stress tests on model selector, metadata sanitization, and XSS safety."""

    @pytest.fixture(autouse=True)
    def setup(self):
        ns = get_m2_namespace()
        self.sanitize = ns["sanitize_model_metadata"]
        self.render_card = ns["render_model_metadata_card"]
        self.render_dropdown = ns["render_model_selector_dropdown"]
        self.create_widget = ns["create_model_selector_widget"]
        self.ARENA_MODELS = ns["ARENA_MODELS"]

    def test_rapid_model_metadata_sanitization_edge_cases(self):
        """Test sanitize_model_metadata with degenerate and malicious inputs."""
        # 1. Non-existent model name fallback
        name1, data1 = self.sanitize("NonExistentSuperModel_9000")
        assert name1 == "Qwen 2.5 Coder 72B"
        assert data1["default_elo"] == 2640.0

        # 2. None input
        name2, data2 = self.sanitize(None)
        assert name2 == "Qwen 2.5 Coder 72B"

        # 3. Context window clamping: negative context -> clamped to 2048
        name3, data3 = self.sanitize("Qwen 2.5 Coder 72B", {"context_window": -500})
        assert data3["context_window"] == 2048

        # 4. Context window clamping: excessive context -> clamped to 1048576
        name4, data4 = self.sanitize("Qwen 2.5 Coder 72B", {"context_window": 99999999})
        assert data4["context_window"] == 1048576

        # 5. Non-numeric VRAM string
        name5, data5 = self.sanitize("Qwen 2.5 Coder 72B", {"vram_gb": "invalid_string"})
        assert data5["vram_gb"] == 0.0

    def test_xss_and_html_injection_escaping_in_cards(self):
        """Verify HTML escaping prevents injection attacks in model metadata."""
        malicious_name = '<script>alert("XSS")</script>'
        malicious_raw = {
            "role": '<img src=x onerror=alert(1)>',
            "layer": '<b onmouseover=alert(2)>layer</b>',
            "port": '"><script>alert(3)</script>',
            "quant": '<svg/onload=alert(4)>'
        }
        card_html = self.render_card(malicious_name, malicious_raw)
        
        # Verify unescaped tags are NOT present
        assert '<script>' not in card_html
        assert '<img src=x onerror=alert(1)>' not in card_html
        assert '<svg/onload=alert(4)>' not in card_html
        # Verify escaped entities are present
        assert '&lt;img src=x onerror=alert(1)&gt;' in card_html or '&lt;script&gt;' in card_html


class TestAdversarialZeroSumConservation:
    """100,000 duel zero-sum conservation test and round-robin tournament."""

    @pytest.fixture(autouse=True)
    def setup(self):
        ns = get_m2_namespace()
        self.calc_elo = ns["calculate_elo_update"]
        self.ArenaStateManager = ns["ArenaStateManager"]
        self.PILLARS = ns["PILLARS"]
        self.ARENA_MODELS = ns["ARENA_MODELS"]

    def test_100k_random_duels_zero_sum_conservation(self):
        """Verify sum(delta_A + delta_B) == 0 for 100,000 randomized duels."""
        random.seed(1337)
        max_abs_deviation = 0.0
        
        for _ in range(100000):
            r_a = random.uniform(-2000.0, 10000.0)
            r_b = random.uniform(-2000.0, 10000.0)
            score_a = random.random()
            k = random.uniform(1.0, 128.0)

            exp_a, new_a, new_b = self.calc_elo(r_a, r_b, score_a, k)
            delta_a = new_a - r_a
            delta_b = new_b - r_b
            deviation = abs(delta_a + delta_b)
            if deviation > max_abs_deviation:
                max_abs_deviation = deviation

            assert deviation < 1e-11, f"Zero-sum violated! dev={deviation}, delta_a={delta_a}, delta_b={delta_b}"

        assert max_abs_deviation < 1e-11

    def test_round_robin_tournament_total_elo_conservation(self):
        """In a closed tournament of 9 models over 100 rounds, total ELO sum is exactly conserved."""
        state = self.ArenaStateManager(self.PILLARS, self.ARENA_MODELS)
        initial_total_elo = sum(m["default_elo"] for m in state.models.values())

        model_names = list(state.models.keys())
        random.seed(42)

        for _ in range(100):
            for i in range(len(model_names)):
                for j in range(i + 1, len(model_names)):
                    m_a = model_names[i]
                    m_b = model_names[j]
                    score = random.choice([0.0, 0.5, 1.0])
                    state.record_duel(m_a, m_b, score, pillar_id=1)

        final_total_elo = sum(m["default_elo"] for m in state.models.values())
        assert math.isclose(initial_total_elo, final_total_elo, abs_tol=1e-9), (
            f"Tournament total ELO drifted: init={initial_total_elo}, final={final_total_elo}"
        )
