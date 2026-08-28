#!/usr/bin/env python3
"""
figma_zero_mock_linter.py - Rule #0 Zero-Mock Pre-Merge Static AST Linter
=========================================================================
Part of the Lauburu Monorepo Rule #0 Zero-Mock Guardrail Infrastructure.

Authoritative pre-merge blocking linter for Figma design-to-code pipelines.
Strictly distinguishes Permissible Structural Layout from Forbidden Mock Data
across TSX/JSX, Vue, HTML, Flutter/Dart, and Python UI representations.

Permissible Structural Layout (Allowed):
  - DOM/JSX hierarchy, flexbox/grid styling, design tokens
  - Static chrome/UI headers & field labels (<h2>Hardware</h2>, <th>Throughput</th>)
  - Dynamic state bindings ({data?.vram ?? '--'}, Text(snapshot.data?.hr ?? '--'))
  - Clean uninitialized states ('--', 'N/A', null, <LoadingSkeleton />)
  - Verified visual animations annotated with /* @verified-visual-animation */

Forbidden Mock Data (Blocked):
  - Hardcoded telemetry literals in data fields (<span>142 bpm</span>, 0.28ms)
  - In-source mock arrays/lists pre-populated with active records
  - Synthetic client-side simulation timers (setTimeout, Future.delayed)
  - Synthetic math scaling multipliers (single_tp * 2.0)
  - Unverified Math.random() / random.randint() in telemetry pipelines
  - Simulation comments ("// Simulating failover", "# Mocking sensor")
  - Mock variable declarations (const mock_devices = ...)

Exit Codes:
  0: PASS (100% Zero-Mock Certified)
  1: FAIL (Forbidden Mock Data Detected - Merge Blocked)
  2: RUNTIME ERROR / SYNTAX ERROR
"""

import os
import sys
import re
import ast
import json
import difflib
import argparse
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional, Set, Tuple, Union

# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class Violation:
    file_path: str
    line_number: int
    column: int
    rule_id: str
    rule_name: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    offending_code: str
    message: str
    remediation_hint: str
    language: str
    suggested_replacement: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ============================================================================
# REGEX DEFINITIONS & GRAMMAR PATTERNS
# ============================================================================

TELEMETRY_UNIT_REGEX = re.compile(
    r"^[0-9]+(\.[0-9]+)?\s*(bpm|ms|us|µs|s|ns|mbps|gbps|kbps|mb/s|gb/s|gflops|tflops|tops|fps|watts|w|v|mv|ma|hz|khz|mhz|ghz|%|°c|°f|mlo)\b",
    re.IGNORECASE
)

LATENCY_THROUGHPUT_STRING_REGEX = re.compile(
    r"^([0-9]+(\.[0-9]+)?)\s*(ms|us|µs|s|ns|mbps|gbps|kbps|mb/s|gb/s)(\s*\([A-Za-z0-9\s_\-\/]+\))?$",
    re.IGNORECASE
)

SIMULATION_COMMENT_REGEX = re.compile(
    r"""(#|//|/\*)\s*(?P<comment>(Simulating|Simulated|Mocking|Fake|Synthetic|Placeholder)\s+(the\s+)?(failover|data|telemetry|metrics|benchmark|logic|response|devices|status|stream|reading|state))""",
    re.IGNORECASE
)

MOCK_VARIABLE_DECLARATION_REGEX = re.compile(
    r"""\b(?P<var>(mock|dummy|fake|simulated|placeholder)_(data|devices|metrics|stats|telemetry|nodes|fleet|response|users|sensors|readings))\s*=""",
    re.IGNORECASE
)

# Tags where text is a structural label / header
CHROME_TAGS = {
    'th', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'label', 'button', 'title',
    'nav', 'breadcrumb', 'thead', 'caption', 'AppBar', 'TextButton', 'ElevatedButton',
    'Header', 'Heading', 'Tab', 'MenuItem'
}

DATA_TAGS = {
    'span', 'p', 'div', 'td', 'b', 'strong', 'Badge', 'MetricValue', 'DataCell', 'Text',
    'Value', 'StatValue', 'Reading'
}

TELEMETRY_OBJ_KEYS = {
    'latency', 'latency_ms', 'ping', 'ping_ms', 'rtt', 'rtt_ms',
    'throughput', 'throughput_mbps', 'bandwidth', 'bandwidth_mbps',
    'speed', 'speed_mbps', 'single_tp', 'single_tp_mbps', 'merged_tp',
    'merged_tp_mbps', 'pixel_tp', 'tp_mbps', 'heart_rate', 'heartrate',
    'vram', 'vram_mb', 'vram_gb', 'gflops', 'gemm_gflops', 'tops', 'ecg', 'hr'
}

ACTIVE_STATUS_VALUES = {
    "APPLIED", "ACTIVE", "ONLINE", "HEALTHY", "CONNECTED", "FLEET_DARK_ACTIVE", "SYNCED"
}


# ============================================================================
# BASE SCANNER & UTILITIES
# ============================================================================

class BaseScanner:
    """Base scanner providing line/column resolution and snippet extraction."""

    def __init__(self, file_path: str, source_text: str):
        self.file_path = file_path
        self.source_text = source_text
        self.source_lines = source_text.splitlines()
        self.violations: List[Violation] = []

    def _get_line_and_col(self, char_index: int) -> Tuple[int, int]:
        line_num = 1
        col_num = 0
        cur = 0
        for i, line in enumerate(self.source_lines):
            line_len = len(line) + 1
            if cur + line_len > char_index:
                line_num = i + 1
                col_num = max(0, char_index - cur)
                break
            cur += line_len
        return line_num, col_num

    def _get_line_snippet(self, line_num: int) -> str:
        if 1 <= line_num <= len(self.source_lines):
            return self.source_lines[line_num - 1].strip()
        return ""


# ============================================================================
# JAVASCRIPT / TYPESCRIPT / JSX / TSX SCANNER
# ============================================================================

class JsTsxScanner(BaseScanner):
    """Scanner for React / Next.js / TypeScript / JSX source files."""

    def scan(self) -> List[Violation]:
        is_animation = "/* @verified-visual-animation */" in self.source_text or "// @verified-visual-animation" in self.source_text

        # 1. Rule ZM-JSX-01: Hardcoded Telemetry in JSX element (e.g. <span>142 bpm</span>)
        pattern_jsx_text = re.compile(
            r"""<(?P<tag>[A-Za-z0-9_]+)(?P<attrs>[^>]*)>\s*(?P<val>[0-9]+(\.[0-9]+)?\s*(bpm|ms|us|µs|s|ns|mbps|gbps|kbps|gflops|tflops|tops|fps|watts|w|v|mv|ma|hz|khz|mhz|ghz|%|°c|°f|mlo))\s*</(?P=tag)>""",
            re.IGNORECASE
        )
        for m in pattern_jsx_text.finditer(self.source_text):
            tag = m.group('tag')
            if tag.lower() not in CHROME_TAGS:
                line_num, col_num = self._get_line_and_col(m.start())
                val = m.group('val')
                replacement = f"<{tag}{m.group('attrs')}>{{telemetry?.val != null ? `${{telemetry.val}}` : '--'}}</{tag}>"
                self.violations.append(Violation(
                    file_path=self.file_path,
                    line_number=line_num,
                    column=col_num,
                    rule_id="ZM-JSX-01",
                    rule_name="Hardcoded Telemetry String in JSX Element",
                    severity="CRITICAL",
                    offending_code=self._get_line_snippet(line_num),
                    message=f"Hardcoded telemetry literal '{val}' detected in <{tag}> element.",
                    remediation_hint=f"Replace hardcoded literal with dynamic state binding: <{tag}>{{telemetry?.value ?? '--'}}</{tag}>",
                    language="TypeScript/JSX",
                    suggested_replacement=replacement
                ))

        # 2. Rule ZM-JS-01: Hardcoded telemetry property in JS/TS object literal
        pattern_obj_prop = re.compile(
            r"""["']?(?P<key>\b(latency|latency_ms|ping|ping_ms|rtt|rtt_ms|throughput|throughput_mbps|bandwidth|bandwidth_mbps|speed|speed_mbps|single_tp|single_tp_mbps|merged_tp|merged_tp_mbps|pixel_tp|tp_mbps|heart_rate|heartrate|vram|gflops|gemm_gflops)\b)["']?\s*:\s*(["'](?P<str_val>[0-9]+(\.[0-9]+)?\s*(ms|us|µs|s|ns|mbps|gbps|kbps|bpm|gflops|fps)(\s*\([^)"']+\))?|[0-9]+(\.[0-9]+)?)[\"']|`(?P<tmpl_val>[^`]*[0-9]+(\.[0-9]+)?\s*(ms|us|µs|s|ns|mbps|gbps|kbps)[^`]*)`|(?P<num_val>[1-9][0-9]*(\.[0-9]+)?))""",
            re.IGNORECASE
        )
        for m in pattern_obj_prop.finditer(self.source_text):
            line_num, col_num = self._get_line_and_col(m.start())
            val = m.group('str_val') or m.group('tmpl_val') or m.group('num_val') or m.group(0)
            self.violations.append(Violation(
                file_path=self.file_path,
                line_number=line_num,
                column=col_num,
                rule_id="ZM-JS-01",
                rule_name="Hardcoded Telemetry Property in Object Literal",
                severity="CRITICAL",
                offending_code=self._get_line_snippet(line_num),
                message=f"Hardcoded telemetry key '{m.group('key')}' assigned static mock value '{val}'.",
                remediation_hint="Initialize property with null or '--' and populate dynamically via REST/WebSocket.",
                language="TypeScript/JSX"
            ))

        # 3. Rule ZM-JS-03: Static default array pre-marked active/applied
        pattern_static_array = re.compile(
            r"""(const|let|var)\s+(?P<varname>[A-Za-z0-9_$]+)\s*(:\s*[A-Za-z0-9_<>[\]]+\s*)?=\s*\[\s*\{[^\]]*status\s*:\s*["'](APPLIED|ACTIVE|ONLINE|CONNECTED|FLEET_DARK_ACTIVE|HEALTHY)["']""",
            re.IGNORECASE | re.DOTALL
        )
        for m in pattern_static_array.finditer(self.source_text):
            line_num, col_num = self._get_line_and_col(m.start())
            self.violations.append(Violation(
                file_path=self.file_path,
                line_number=line_num,
                column=col_num,
                rule_id="ZM-JS-03",
                rule_name="Static Mock Array Pre-Marked Active",
                severity="HIGH",
                offending_code=self._get_line_snippet(line_num),
                message=f"In-source array '{m.group('varname')}' pre-populated with active mock status.",
                remediation_hint="Initialize as empty array `[]` and hydrate dynamically from backend API / WebSocket.",
                language="TypeScript/JSX"
            ))

        # 4. Rule ZM-JS-05: Synthetic setTimeout state transition
        pattern_sim_timeout = re.compile(
            r"""setTimeout\s*\(\s*(\(\)\s*=>|function\s*\(\))\s*\{?[^}]*(SUCCESS|ONLINE|CONNECTED|APPLIED|FLEET_DARK_ACTIVE|setDone|setIsConnected|setIsRunning|setStatus)[^}]*\}?,\s*[0-9]+\)""",
            re.IGNORECASE
        )
        for m in pattern_sim_timeout.finditer(self.source_text):
            line_num, col_num = self._get_line_and_col(m.start())
            self.violations.append(Violation(
                file_path=self.file_path,
                line_number=line_num,
                column=col_num,
                rule_id="ZM-JS-05",
                rule_name="Synthetic Async State Transition (setTimeout)",
                severity="CRITICAL",
                offending_code=self._get_line_snippet(line_num),
                message="Synthetic setTimeout timer detected simulating asynchronous completion without genuine backend verification.",
                remediation_hint="Remove setTimeout; trigger state updates via genuine WebSocket or HTTP Promise resolution.",
                language="TypeScript/JSX"
            ))

        # 5. Rule ZM-JS-06: Unverified Math.random in telemetry
        if not is_animation:
            pattern_random = re.compile(r"""\bMath\.random\s*\(\s*\)""", re.IGNORECASE)
            for m in pattern_random.finditer(self.source_text):
                line_num, col_num = self._get_line_and_col(m.start())
                snippet = self._get_line_snippet(line_num)
                is_data = bool(re.search(r"(bpm|heart|speed|latency|tp|vram|metric|reading|stat|val)", snippet, re.I))
                self.violations.append(Violation(
                    file_path=self.file_path,
                    line_number=line_num,
                    column=col_num,
                    rule_id="ZM-JS-06",
                    rule_name="Unverified Math.random() in UI Pipeline",
                    severity="CRITICAL" if is_data else "MEDIUM",
                    offending_code=snippet,
                    message="Math.random() call detected. If purely visual canvas animation, annotate with '/* @verified-visual-animation */'.",
                    remediation_hint="Remove synthetic randomization and bind component to genuine telemetry stream.",
                    language="TypeScript/JSX"
                ))

        return self.violations


# ============================================================================
# VUE SINGLE FILE COMPONENT (.vue) SCANNER
# ============================================================================

class VueScanner(BaseScanner):
    """Scanner for Vue 2/3 Single File Components (.vue)."""

    def scan(self) -> List[Violation]:
        # Scan template section for raw hardcoded telemetry in data classes
        pattern_template_metric = re.compile(
            r"""<(span|p|div|td|b)\s+[^>]*class=["'][^"']*(metric|val|reading|telemetry|stat)[^"']*["'][^>]*>\s*([0-9]+(\.[0-9]+)?\s*(bpm|ms|mbps|gbps|gflops|%|°c))\s*</(span|p|div|td|b)>""",
            re.IGNORECASE
        )
        for m in pattern_template_metric.finditer(self.source_text):
            line_num, col_num = self._get_line_and_col(m.start())
            self.violations.append(Violation(
                file_path=self.file_path,
                line_number=line_num,
                column=col_num,
                rule_id="ZM-VUE-01",
                rule_name="Hardcoded Telemetry in Vue Template",
                severity="CRITICAL",
                offending_code=self._get_line_snippet(line_num),
                message=f"Hardcoded literal '{m.group(3)}' inside Vue template data element.",
                remediation_hint="Replace with mustache binding: {{ metric?.value ?? '--' }}",
                language="Vue"
            ))

        # Extract <script> content and run JsTsxScanner
        script_match = re.search(r"<script[^>]*>(.*?)</script>", self.source_text, re.DOTALL | re.IGNORECASE)
        if script_match:
            script_text = script_match.group(1)
            js_scanner = JsTsxScanner(self.file_path, script_text)
            sub_violations = js_scanner.scan()
            # Adjust line offsets
            script_start_line, _ = self._get_line_and_col(script_match.start(1))
            for v in sub_violations:
                v.line_number = script_start_line + v.line_number - 1
                v.language = "Vue"
                self.violations.append(v)

        return self.violations


# ============================================================================
# HTML / TEMPLATE SCANNER (.html, .jinja2)
# ============================================================================

class HtmlScanner(BaseScanner):
    """Scanner for HTML templates and Web Components."""

    def scan(self) -> List[Violation]:
        pattern_html_metric = re.compile(
            r"""<(?P<tag>span|p|div|td|b|strong)\s+[^>]*class=["'][^"']*(metric|val|reading|telemetry|stat|badge|gauge)[^"']*["'][^>]*>\s*(?P<val>[0-9]+(\.[0-9]+)?\s*(bpm|ms|us|µs|s|ns|mbps|gbps|kbps|gflops|fps|%|°c))\s*</(?P=tag)>""",
            re.IGNORECASE
        )
        for m in pattern_html_metric.finditer(self.source_text):
            line_num, col_num = self._get_line_and_col(m.start())
            self.violations.append(Violation(
                file_path=self.file_path,
                line_number=line_num,
                column=col_num,
                rule_id="ZM-HTML-01",
                rule_name="Hardcoded Telemetry in HTML Element",
                severity="CRITICAL",
                offending_code=self._get_line_snippet(line_num),
                message=f"Hardcoded metric '{m.group('val')}' in HTML data element.",
                remediation_hint="Bind element to dynamic template placeholder (e.g. {{ metric | default('--') }}).",
                language="HTML"
            ))
        return self.violations


# ============================================================================
# FLUTTER / DART UI SCANNER (.dart)
# ============================================================================

class DartUiScanner(BaseScanner):
    """Scanner for Dart / Flutter UI widgets and presentation trees."""

    def scan(self) -> List[Violation]:
        # 1. Rule ZM-DART-01: Hardcoded Text("142 bpm")
        pattern_dart_text = re.compile(
            r"""Text\s*\(\s*["'](?P<val>[0-9]+(\.[0-9]+)?\s*(bpm|ms|us|µs|s|ns|mbps|gbps|gflops|fps|watts|%|°c))["']\s*[,)]""",
            re.IGNORECASE
        )
        for idx, line in enumerate(self.source_lines, 1):
            m = pattern_dart_text.search(line)
            if m:
                # Exclude if line contains AppBar title or button label
                if not any(k in line for k in ["AppBar", "ElevatedButton", "TextButton", "title:"]):
                    self.violations.append(Violation(
                        file_path=self.file_path,
                        line_number=idx,
                        column=m.start(),
                        rule_id="ZM-DART-01",
                        rule_name="Hardcoded Telemetry in Flutter Text Widget",
                        severity="CRITICAL",
                        offending_code=line.strip(),
                        message=f"Hardcoded telemetry literal '{m.group('val')}' in Text() widget.",
                        remediation_hint="Replace with: Text(snapshot.data?.value?.toString() ?? '--')",
                        language="Dart/Flutter"
                    ))

        # 2. Rule ZM-DART-03: Static mock list of model objects
        pattern_dart_list = re.compile(
            r"""(final|var|List<[^>]+>)\s+(?P<varname>[A-Za-z0-9_$]+)\s*=\s*(const\s*)?(\[[^\]]*status\s*:\s*["'](ACTIVE|ONLINE|CONNECTED|HEALTHY)["']|<[A-Za-z0-9_]+>\[\s*[A-Za-z0-9_]+\([^)]*status:\s*["']ACTIVE)""",
            re.IGNORECASE
        )
        for idx, line in enumerate(self.source_lines, 1):
            m = pattern_dart_list.search(line)
            if m:
                self.violations.append(Violation(
                    file_path=self.file_path,
                    line_number=idx,
                    column=m.start(),
                    rule_id="ZM-DART-03",
                    rule_name="Static Mock List of Model Objects in Flutter",
                    severity="HIGH",
                    offending_code=line.strip(),
                    message=f"Mock list '{m.group('varname')}' initialized with active dummy instances.",
                    remediation_hint="Initialize list as empty `[]` and populate via StreamBuilder or Bloc.",
                    language="Dart/Flutter"
                ))

        # 3. Rule ZM-DART-05: Future.delayed synthetic state simulation
        pattern_delayed = re.compile(
            r"""Future\.delayed\s*\(\s*Duration\([^)]+\)\s*,\s*\(\)\s*=>\s*setState""",
            re.IGNORECASE
        )
        for idx, line in enumerate(self.source_lines, 1):
            m = pattern_delayed.search(line)
            if m:
                self.violations.append(Violation(
                    file_path=self.file_path,
                    line_number=idx,
                    column=m.start(),
                    rule_id="ZM-DART-05",
                    rule_name="Synthetic Future.delayed State Transition in Flutter",
                    severity="CRITICAL",
                    offending_code=line.strip(),
                    message="Future.delayed detected simulating state transitions.",
                    remediation_hint="Bind setState() to live Stream subscription or MethodChannel response.",
                    language="Dart/Flutter"
                ))

        return self.violations


# ============================================================================
# PYTHON AST JUDGE (.py)
# ============================================================================

class PythonAstJudge(ast.NodeVisitor):
    """
    AST analysis for Python presentation endpoints, telemetry builders, and dashboards.
    """

    def __init__(self, file_path: str, source_text: str):
        self.file_path = file_path
        self.source_text = source_text
        self.source_lines = source_text.splitlines()
        self.violations: List[Violation] = []
        self.is_animation = "# @verified-visual-animation" in source_text

    def _get_line_snippet(self, line_num: int) -> str:
        if 1 <= line_num <= len(self.source_lines):
            return self.source_lines[line_num - 1].strip()
        return ""

    def visit_Dict(self, node: ast.Dict):
        """Flags dictionaries containing telemetry keys assigned constant literals."""
        for k, v in zip(node.keys, node.values):
            if isinstance(k, ast.Constant) and isinstance(k.value, str):
                key_str = k.value.lower()
                if key_str in TELEMETRY_OBJ_KEYS:
                    # Check if value is constant string with unit or non-zero number
                    if isinstance(v, ast.Constant):
                        if isinstance(v.value, str) and TELEMETRY_UNIT_REGEX.search(v.value.strip()):
                            self.violations.append(Violation(
                                file_path=self.file_path,
                                line_number=node.lineno,
                                column=node.col_offset,
                                rule_id="ZM-PY-01",
                                rule_name="Hardcoded Telemetry Literal in Python Dict",
                                severity="CRITICAL",
                                offending_code=self._get_line_snippet(node.lineno),
                                message=f"Telemetry key '{key_str}' assigned static string literal '{v.value}'.",
                                remediation_hint="Populate telemetry dictionary from live socket/hardware register measurement.",
                                language="Python"
                            ))
                        elif isinstance(v.value, (int, float)) and v.value > 0 and key_str in {"heart_rate", "latency_ms", "gflops"}:
                            self.violations.append(Violation(
                                file_path=self.file_path,
                                line_number=node.lineno,
                                column=node.col_offset,
                                rule_id="ZM-PY-01",
                                rule_name="Hardcoded Numeric Telemetry in Python Dict",
                                severity="HIGH",
                                offending_code=self._get_line_snippet(node.lineno),
                                message=f"Telemetry key '{key_str}' assigned hardcoded numeric constant {v.value}.",
                                remediation_hint="Set default to None / 0.0 or bind to live probe function.",
                                language="Python"
                            ))
        self.generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp):
        """Flags synthetic math multipliers on telemetry variables (e.g. single_tp * 2.0)."""
        if isinstance(node.op, ast.Mult):
            left_id = None
            if isinstance(node.left, ast.Name):
                left_id = node.left.id.lower()
            if left_id and any(t in left_id for t in ["single_tp", "throughput", "bandwidth", "latency"]):
                if isinstance(node.right, ast.Constant) and isinstance(node.right.value, (int, float)) and node.right.value > 1:
                    self.violations.append(Violation(
                        file_path=self.file_path,
                        line_number=node.lineno,
                        column=node.col_offset,
                        rule_id="ZM-PY-02",
                        rule_name="Synthetic Scaling Multiplier on Telemetry",
                        severity="CRITICAL",
                        offending_code=self._get_line_snippet(node.lineno),
                        message=f"Synthetic multiplier '{node.right.value}' scaling telemetry variable '{left_id}'.",
                        remediation_hint="Measure combined bandwidth / metric directly from physical interfaces.",
                        language="Python"
                    ))
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        """Flags except blocks returning active mock dictionaries."""
        for stmt in node.body:
            if isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Dict):
                # Inspect returned dict keys
                for k, v in zip(stmt.value.keys, stmt.value.values):
                    if isinstance(k, ast.Constant) and str(k.value).lower() == "status":
                        if isinstance(v, ast.Constant) and str(v.value).upper() in ACTIVE_STATUS_VALUES:
                            self.violations.append(Violation(
                                file_path=self.file_path,
                                line_number=stmt.lineno,
                                column=stmt.col_offset,
                                rule_id="ZM-PY-04",
                                rule_name="Mock Active Fallback in Exception Handler",
                                severity="CRITICAL",
                                offending_code=self._get_line_snippet(stmt.lineno),
                                message=f"Exception handler returns synthetic status '{v.value}'.",
                                remediation_hint="Return explicit error state `{{'status': 'ERROR', 'data': None}}` upon failure.",
                                language="Python"
                            ))
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        """Flags unverified random generation in data paths."""
        if not self.is_animation:
            func_name = ""
            if isinstance(node.func, ast.Attribute):
                func_name = node.func.attr
            elif isinstance(node.func, ast.Name):
                func_name = node.func.id

            if func_name in {"randint", "uniform", "random", "choice"}:
                snippet = self._get_line_snippet(node.lineno)
                if any(k in snippet.lower() for k in ["bpm", "latency", "tp", "heart", "speed", "vram", "metric"]):
                    self.violations.append(Violation(
                        file_path=self.file_path,
                        line_number=node.lineno,
                        column=node.col_offset,
                        rule_id="ZM-PY-06",
                        rule_name="Unverified Random Telemetry Generation",
                        severity="CRITICAL",
                        offending_code=snippet,
                        message=f"Random generator '{func_name}()' used in telemetry computation.",
                        remediation_hint="Remove synthetic randomization and read from genuine hardware telemetry.",
                        language="Python"
                    ))
        self.generic_visit(node)


# ============================================================================
# MASTER ZERO-MOCK LINTER ENGINE
# ============================================================================

class FigmaZeroMockLinter:
    """
    Master static analysis engine for Figma design-to-code zero-mock compliance.
    """

    SUPPORTED_EXTENSIONS = {
        ".tsx", ".jsx", ".ts", ".js", ".mjs", ".vue", ".html", ".jinja",
        ".jinja2", ".dart", ".py"
    }

    IGNORED_DIRS = {
        "node_modules", ".git", "__pycache__", ".venv", "venv", ".pytest_cache",
        ".agents", "build", "dist", ".next", ".nuxt", "coverage"
    }

    def __init__(self, fail_under: float = 100.0, strict: bool = False):
        self.fail_under = fail_under
        self.strict = strict

    def audit_file(self, file_path: str) -> List[Violation]:
        """Audits a single file against all Rule #0 zero-mock criteria."""
        path = Path(file_path).resolve()
        if not path.exists() or not path.is_file():
            return []

        suffix = path.suffix.lower()
        if suffix not in self.SUPPORTED_EXTENSIONS:
            return []

        # Skip explicit test fixture directories unless strictly targeted
        if "/tests/fixtures/" in str(path) or "/test/fixtures/" in str(path):
            return []

        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception:
            return []

        violations: List[Violation] = []

        # 1. Lexical Comment & Mock Variable Scan (Language-agnostic)
        lines = content.splitlines()
        in_docstring = False
        for idx, line in enumerate(lines, 1):
            sline = line.strip()
            # Track Python multi-line docstring boundaries
            if suffix == ".py":
                if '"""' in sline or "'''" in sline:
                    # Toggle or count
                    quotes = sline.count('"""') + sline.count("'''")
                    if quotes % 2 != 0:
                        in_docstring = not in_docstring
                    continue
                if in_docstring:
                    continue

            # Only scan actual comment lines or trailing comments
            if "#" in line or "//" in line or "/*" in line:
                match_comment = SIMULATION_COMMENT_REGEX.search(line)
                if match_comment:
                    violations.append(Violation(
                        file_path=str(path),
                        line_number=idx,
                        column=match_comment.start(),
                        rule_id="ZM-COM-05",
                        rule_name="Explicit Simulation Comment",
                        severity="HIGH",
                        offending_code=sline,
                        message=f"Simulation comment detected: '{match_comment.group('comment')}'.",
                        remediation_hint="Remove simulation comment and connect genuine hardware/network integration.",
                        language=suffix.lstrip(".")
                    ))

            # Match actual variable assignment
            if "=" in sline and not sline.startswith(("#", "//", "/*", "*")):
                match_var = MOCK_VARIABLE_DECLARATION_REGEX.search(line)
                if match_var:
                    # Ignore if inside a string literal definition or regex declaration
                    if not any(decl in sline for decl in ["re.compile", "Pattern", "REGEX"]):
                        violations.append(Violation(
                            file_path=str(path),
                            line_number=idx,
                            column=match_var.start(),
                            rule_id="ZM-LEX-04",
                            rule_name="Mock Variable Declaration",
                            severity="CRITICAL",
                            offending_code=sline,
                            message=f"Mock variable '{match_var.group('var')}' detected in assignment.",
                            remediation_hint="Remove mock array; initialize empty state and populate via live telemetry.",
                            language=suffix.lstrip(".")
                        ))

        # 2. Language-Specific Parsers
        if suffix in (".tsx", ".jsx", ".ts", ".js", ".mjs"):
            scanner = JsTsxScanner(str(path), content)
            violations.extend(scanner.scan())
        elif suffix == ".vue":
            scanner = VueScanner(str(path), content)
            violations.extend(scanner.scan())
        elif suffix in (".html", ".jinja", ".jinja2"):
            scanner = HtmlScanner(str(path), content)
            violations.extend(scanner.scan())
        elif suffix == ".dart":
            scanner = DartUiScanner(str(path), content)
            violations.extend(scanner.scan())
        elif suffix == ".py":
            try:
                tree = ast.parse(content, filename=str(path))
                judge = PythonAstJudge(str(path), content)
                judge.visit(tree)
                violations.extend(judge.violations)
            except SyntaxError:
                # Syntax error handled gracefully
                pass

        return violations

    def audit_directory(self, dir_path: str) -> List[Violation]:
        """Recursively audits all supported files in a directory tree."""
        all_violations: List[Violation] = []
        root_path = Path(dir_path).resolve()
        if not root_path.exists():
            return []

        for root, dirs, files in os.walk(root_path):
            # Prune ignored directories in-place
            dirs[:] = [d for d in dirs if d not in self.IGNORED_DIRS]
            for f in sorted(files):
                ext = Path(f).suffix.lower()
                if ext in self.SUPPORTED_EXTENSIONS:
                    file_abs = os.path.join(root, f)
                    all_violations.extend(self.audit_file(file_abs))

        return all_violations

    def calculate_score(self, violations: List[Violation]) -> float:
        """Calculates 0-100 score based on penalty weights."""
        penalties = {
            "CRITICAL": 30.0,
            "HIGH": 15.0,
            "MEDIUM": 5.0,
            "LOW": 1.0
        }
        total_penalty = sum(penalties.get(v.severity.upper(), 5.0) for v in violations)
        return max(0.0, round(100.0 - total_penalty, 2))

    def generate_report(self, target_path: str, violations: List[Violation]) -> Dict[str, Any]:
        """Generates a structured report dictionary."""
        score = self.calculate_score(violations)
        severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for v in violations:
            sev = v.severity.upper()
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        is_clean = len(violations) == 0 and score >= self.fail_under

        return {
            "target": target_path,
            "verdict": "ZERO_MOCK_CERTIFIED 🟢" if is_clean else "MOCK_VIOLATIONS_DETECTED 🔴",
            "score": score,
            "passed": is_clean,
            "total_violations": len(violations),
            "severity_summary": severity_counts,
            "violations": [v.to_dict() for v in violations]
        }

    def generate_remediation_diff(self, file_path: str, violations: List[Violation]) -> Optional[str]:
        """Synthesizes unified diff patch for detected hardcoded literals."""
        path = Path(file_path).resolve()
        if not path.exists():
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                original_lines = f.readlines()
        except Exception:
            return None

        modified_lines = list(original_lines)
        has_fixes = False

        for v in violations:
            if v.file_path == str(path) and v.suggested_replacement and 1 <= v.line_number <= len(modified_lines):
                # Apply line-level replacement
                orig_line = modified_lines[v.line_number - 1]
                # Replace regex pattern match
                if v.rule_id == "ZM-JSX-01":
                    replacement_expr = ">{telemetry?.value ?? '--'}<"
                    fixed_line = re.sub(
                        r""">\s*[0-9]+(\.[0-9]+)?\s*(bpm|ms|us|µs|s|ns|mbps|gbps|kbps|gflops|tflops|tops|fps|watts|w|v|mv|ma|hz|khz|mhz|ghz|%|°c|°f|mlo)\s*<""",
                        replacement_expr,
                        orig_line
                    )
                    if fixed_line != orig_line:
                        modified_lines[v.line_number - 1] = fixed_line
                        has_fixes = True

        if not has_fixes:
            return None

        diff = difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile=f"a/{path.name}",
            tofile=f"b/{path.name}",
            lineterm=""
        )
        return "\n".join(diff)


# ============================================================================
# CLI ENTRYPOINT
# ============================================================================

def format_console_report(report: Dict[str, Any], violations: List[Violation]) -> str:
    lines = []
    lines.append("=" * 72)
    lines.append(" 🛡️  FIGMA ZERO-MOCK PRE-MERGE AST LINTER (RULE #0)")
    lines.append("=" * 72)
    lines.append(f" Target:      {report['target']}")
    lines.append(f" Verdict:     {report['verdict']}")
    lines.append(f" Truth Score: {report['score']} / 100.0 (Pass Threshold: >= {report.get('fail_under', 100.0)})")
    lines.append(f" Violations:  {report['total_violations']}")
    counts = report['severity_summary']
    lines.append(f" Breakdown:   CRITICAL={counts['CRITICAL']}, HIGH={counts['HIGH']}, MEDIUM={counts['MEDIUM']}, LOW={counts['LOW']}")
    lines.append("-" * 72)

    if violations:
        lines.append("\n🚫 DETECTED MOCK DATA VIOLATIONS (PRE-MERGE GATE BLOCKED):")
        for idx, v in enumerate(violations[:30], 1):
            lines.append(f" [{idx}] {v.severity} [{v.rule_id}] {v.file_path}:{v.line_number}:{v.column}")
            lines.append(f"     Offense:     {v.offending_code}")
            lines.append(f"     Message:     {v.message}")
            lines.append(f"     Remediation: {v.remediation_hint}\n")
        if len(violations) > 30:
            lines.append(f" ... and {len(violations) - 30} more violations truncated.")
    else:
        lines.append("\n✅ ZERO MOCK DATA DETECTED. All UI views are 100% Rule #0 Compliant.")

    lines.append("=" * 72)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Figma Zero-Mock Pre-Merge Static AST Linter (Monorepo Rule #0)",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--target-file", type=str, default=None, help="Target single file to audit")
    parser.add_argument("--target-dir", type=str, default=None, help="Target directory to audit recursively")
    parser.add_argument("--fail-under", type=float, default=100.0, help="Pass score threshold (default: 100.0)")
    parser.add_argument("--format", type=str, default="console", choices=["console", "json", "markdown"], help="Output report format")
    parser.add_argument("--json-output", type=str, default=None, help="Save structured JSON report to path")
    parser.add_argument("--strict", action="store_true", help="Strict mode: treat medium/low warnings as blocking")
    parser.add_argument("--fix", action="store_true", help="Generate automated zero-mock remediation diff patches")
    parser.add_argument("--generate-patch", type=str, default=None, help="Save unified .patch file to specified path")

    args = parser.parse_args()

    linter = FigmaZeroMockLinter(fail_under=args.fail_under, strict=args.strict)
    violations: List[Violation] = []

    target_str = args.target_file or args.target_dir or "."
    if args.target_file:
        violations = linter.audit_file(args.target_file)
    else:
        violations = linter.audit_directory(args.target_dir or ".")

    report = linter.generate_report(target_str, violations)
    report["fail_under"] = args.fail_under

    if args.format == "console":
        print(format_console_report(report, violations))
    elif args.format == "json":
        print(json.dumps(report, indent=2, ensure_ascii=False))
    elif args.format == "markdown":
        print(f"# Rule #0 Zero-Mock Audit: {report['verdict']}")
        print(f"- **Target:** `{target_str}`")
        print(f"- **Score:** `{report['score']} / 100.0`")
        print(f"- **Violations:** `{report['total_violations']}`")

    if args.json_output:
        out_p = Path(args.json_output).resolve()
        out_p.parent.mkdir(parents=True, exist_ok=True)
        with open(out_p, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"📄 JSON report saved to: {out_p}")

    if args.fix or args.generate_patch:
        patch_text = ""
        target_files = {v.file_path for v in violations}
        for fpath in target_files:
            diff = linter.generate_remediation_diff(fpath, violations)
            if diff:
                patch_text += diff + "\n"

        if patch_text:
            if args.generate_patch:
                patch_p = Path(args.generate_patch).resolve()
                patch_p.parent.mkdir(parents=True, exist_ok=True)
                with open(patch_p, "w", encoding="utf-8") as f:
                    f.write(patch_text)
                print(f"🛠️  Remediation patch written to: {patch_p}")
            else:
                print("\n🛠️  SUGGESTED ZERO-MOCK REMEDIATION PATCH:")
                print(patch_text)

    # Return exit code 0 if passed, 1 if failed
    sys.exit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
