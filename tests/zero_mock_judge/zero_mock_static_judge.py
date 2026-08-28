#!/usr/bin/env python3
"""
Zero-Mock Static AST & Pattern Judge
====================================
Exhaustive static analyzer detecting mock literals, synthetic math,
hardcoded telemetry values, simulation comments, and fake fallbacks
across Python and JavaScript/TypeScript codebases.

Detection Rules:
- Rule 1: Hardcoded latency / bandwidth strings & numbers in device objects.
- Rule 2: Synthetic math multipliers (e.g. single_tp_mbps * 2.0, load * 5, (1000/RTT) * 4.5).
- Rule 3: Static default node arrays pre-marked ACTIVE/APPLIED/ONLINE.
- Rule 4: Hardcoded fallback dictionaries (e.g. {"status": "FLEET_DARK_ACTIVE", "devices_active": 6}).
- Rule 5: Simulation comments and synthetic sleep loops simulating latency.
- Rule 6: Unverified Math.random() / random loops in telemetry pipelines.
"""

import ast
import json
import os
import re
import sys
import tokenize
import io
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple


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
    language: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Telemetry property names that must never be hardcoded literals in device/status arrays
TELEMETRY_KEYS_REGEX = re.compile(
    r"^(latency|latency_ms|ping|ping_ms|rtt|rtt_ms|throughput|throughput_mbps|bandwidth|bandwidth_mbps|rx_bytes|tx_bytes|speed|speed_mbps|single_tp|single_tp_mbps|merged_tp|merged_tp_mbps|pixel_tp|tp_mbps|battery_level)$",
    re.IGNORECASE
)

# Latency string format (e.g. "0.28ms", "0.45ms (Ethernet)", "1.2ms (Wi-Fi 7)", "15us", "2.5s")
LATENCY_STRING_REGEX = re.compile(
    r"^([0-9]+(\.[0-9]+)?)\s*(ms|us|µs|s|ns)(\s*\([A-Za-z0-9\s_\-\/]+\))?$",
    re.IGNORECASE
)

# Active status strings pre-assigned to static device objects
ACTIVE_STATUS_VALUES = {"APPLIED", "ACTIVE", "ONLINE", "HEALTHY", "CONNECTED", "FLEET_DARK_ACTIVE"}


class PythonAstJudge(ast.NodeVisitor):
    """AST analyzer for Python source files (.py)."""

    def __init__(self, file_path: str, source_lines: List[str]):
        self.file_path = file_path
        self.source_lines = source_lines
        self.violations: List[Violation] = []
        self._current_function: Optional[str] = None
        self._in_except_handler: bool = False

    def _get_line_snippet(self, lineno: int) -> str:
        if 1 <= lineno <= len(self.source_lines):
            return self.source_lines[lineno - 1].strip()
        return ""

    def visit_FunctionDef(self, node: ast.FunctionDef):
        prev = self._current_function
        self._current_function = node.name
        self.generic_visit(node)
        self._current_function = prev

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        prev = self._current_function
        self._current_function = node.name
        self.generic_visit(node)
        self._current_function = prev

    def visit_Assign(self, node: ast.Assign):
        # Exempt judge rule definition tables (e.g. FORBIDDEN_FALLBACK_SIGNATURES, PROHIBITED_MOCK_SIGNATURES)
        is_rule_def = any(
            isinstance(t, ast.Name) and t.id in (
                "FORBIDDEN_FALLBACK_SIGNATURES", "PROHIBITED_MOCK_SIGNATURES",
                "PROHIBITED_MOCK_STRINGS", "FORBIDDEN_SIGNATURES"
            )
            for t in node.targets
        )
        if is_rule_def:
            return
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        prev = self._in_except_handler
        self._in_except_handler = True

        # Rule 4: Hardcoded fallback assignments inside exception handlers
        for stmt in node.body:
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    # Check assignment to status_data or metrics dictionary
                    target_name = self._get_target_name(target)
                    if target_name and re.search(r"(status|metrics|telemetry|node_info|device_info|tp_mbps|throughput|latency)", target_name, re.I):
                        # If assigning a non-null dictionary or constant literal
                        if isinstance(stmt.value, ast.Dict):
                            # Check keys in dict
                            for key_node, val_node in zip(stmt.value.keys, stmt.value.values):
                                k_str = self._get_const_str(key_node)
                                if k_str and k_str in ("status", "devices_active", "throughput_mbps", "latency"):
                                    val_val = self._get_const_val(val_node)
                                    if val_val in ACTIVE_STATUS_VALUES or (isinstance(val_val, (int, float)) and val_val > 0):
                                        self.violations.append(Violation(
                                            file_path=self.file_path,
                                            line_number=stmt.lineno,
                                            column=stmt.col_offset,
                                            rule_id="ZM-AST-PY-04",
                                            rule_name="Hardcoded Fallback Dictionary in Except Handler",
                                            severity="CRITICAL",
                                            offending_code=self._get_line_snippet(stmt.lineno),
                                            message=f"Hardcoded fallback '{k_str}': {val_val!r} assigned to '{target_name}' in exception handler instead of explicit null/error.",
                                            language="Python"
                                        ))
                        elif isinstance(stmt.value, ast.Constant):
                            val_val = stmt.value.value
                            if val_val not in (None, 0, 0.0, "", False, "OFFLINE", "ERROR", "UNREACHABLE", "DISCONNECTED"):
                                if re.search(r"(throughput|speed|latency|ping|mbps|devices_active)", target_name, re.I):
                                    self.violations.append(Violation(
                                        file_path=self.file_path,
                                        line_number=stmt.lineno,
                                        column=stmt.col_offset,
                                        rule_id="ZM-AST-PY-01",
                                        rule_name="Hardcoded Telemetry Fallback in Except Handler",
                                        severity="CRITICAL",
                                        offending_code=self._get_line_snippet(stmt.lineno),
                                        message=f"Non-null static fallback assigned to '{target_name}': {val_val!r} in exception handler.",
                                        language="Python"
                                    ))

        self.generic_visit(node)
        self._in_except_handler = prev

    def visit_BinOp(self, node: ast.BinOp):
        """Rule 2: Synthetic math multipliers (e.g. single_tp * 2.0, single_tp * 0.5, load * 5, (1000/RTT) * 4.5)."""
        if isinstance(node.op, (ast.Mult, ast.Div)):
            left_name = self._extract_var_identifier(node.left)
            right_val = self._get_const_val(node.right)
            right_name = self._extract_var_identifier(node.right)
            left_val = self._get_const_val(node.left)

            # Check if one operand is a telemetry metric identifier and the other is an arbitrary synthetic constant multiplier
            # Target patterns: single_tp * 2.0, single_tp_mbps * 0.5, pixel_tp = single_tp * 0.5, load * 5, (1000 / RTT) * 4.5
            metric_match = None
            multiplier = None

            if left_name and re.search(r"(single_tp|pixel_tp|merged_tp|throughput|tp_mbps|rtt_factor|load_factor|loadavg|cpu_load|link_speed)", left_name, re.I):
                if isinstance(right_val, (int, float)) and right_val not in (0, 1, 1.0, 1024, 1000, 1e6, 1e9, 60, 3600, 8):
                    # Check if standard unit conversion (e.g., bits to bytes / 8 or ms to s / 1000)
                    metric_match = left_name
                    multiplier = right_val
            elif right_name and re.search(r"(single_tp|pixel_tp|merged_tp|throughput|tp_mbps|loadavg|cpu_load)", right_name, re.I):
                if isinstance(left_val, (int, float)) and left_val not in (0, 1, 1.0, 1024, 1000, 1e6, 1e9, 60, 3600, 8):
                    metric_match = right_name
                    multiplier = left_val

            # Also check nested expressions like (1000 / RTT) * 4.5
            if not metric_match and isinstance(node.left, ast.BinOp):
                nested_left_name = self._extract_var_identifier(node.left.right) or self._extract_var_identifier(node.left.left)
                if nested_left_name and re.search(r"(rtt|ping|latency)", nested_left_name, re.I):
                    if isinstance(right_val, (int, float)):
                        metric_match = f"{nested_left_name}_formula"
                        multiplier = right_val

            if metric_match is not None and multiplier is not None:
                # Exclude standard statistical/DSP normalization formulas if explicitly documented or unit tests
                self.violations.append(Violation(
                    file_path=self.file_path,
                    line_number=node.lineno,
                    column=node.col_offset,
                    rule_id="ZM-AST-PY-02",
                    rule_name="Synthetic Math Multiplier on Telemetry Metric",
                    severity="HIGH",
                    offending_code=self._get_line_snippet(node.lineno),
                    message=f"Synthetic multiplier detected: metric '{metric_match}' scaled by constant factor '{multiplier}' without empirical socket measurement.",
                    language="Python"
                ))

        self.generic_visit(node)

    def visit_Dict(self, node: ast.Dict):
        """Rule 1 & Rule 3: Hardcoded telemetry and static ACTIVE device definitions."""
        has_id = False
        has_applied_or_active = False
        has_hardcoded_latency = False
        latency_val = None

        for k, v in zip(node.keys, node.values):
            k_str = self._get_const_str(k)
            v_val = self._get_const_val(v)

            if k_str:
                if k_str in ("id", "device_id", "node_id", "name", "ip"):
                    has_id = True

                if k_str == "status" and isinstance(v_val, str) and v_val.upper() in ACTIVE_STATUS_VALUES:
                    has_applied_or_active = True

                if TELEMETRY_KEYS_REGEX.match(k_str):
                    # Check if value is a hardcoded string or number
                    if isinstance(v_val, str) and LATENCY_STRING_REGEX.match(v_val.strip()):
                        has_hardcoded_latency = True
                        latency_val = v_val
                        self.violations.append(Violation(
                            file_path=self.file_path,
                            line_number=node.lineno,
                            column=node.col_offset,
                            rule_id="ZM-AST-PY-01",
                            rule_name="Hardcoded Telemetry String Literal",
                            severity="CRITICAL",
                            offending_code=self._get_line_snippet(node.lineno),
                            message=f"Hardcoded latency string '{v_val}' assigned to key '{k_str}' in dictionary object.",
                            language="Python"
                        ))
                    elif isinstance(v_val, (int, float)) and v_val > 0 and k_str not in ("battery_level", "rx_bytes", "tx_bytes"):
                        self.violations.append(Violation(
                            file_path=self.file_path,
                            line_number=node.lineno,
                            column=node.col_offset,
                            rule_id="ZM-AST-PY-01",
                            rule_name="Hardcoded Telemetry Number Literal",
                            severity="CRITICAL",
                            offending_code=self._get_line_snippet(node.lineno),
                            message=f"Hardcoded numeric telemetry literal '{v_val}' assigned to key '{k_str}' in dictionary.",
                            language="Python"
                        ))

        # Check for static device definitions pre-marked ACTIVE
        if has_id and has_applied_or_active and not self._in_except_handler:
            self.violations.append(Violation(
                file_path=self.file_path,
                line_number=node.lineno,
                column=node.col_offset,
                rule_id="ZM-AST-PY-03",
                rule_name="Static Node Dictionary Pre-Marked ACTIVE",
                severity="HIGH",
                offending_code=self._get_line_snippet(node.lineno),
                message=f"Device dictionary statically initialized with active/applied status instead of dynamic discovery state.",
                language="Python"
            ))

        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        """Rule 6: Randomization in telemetry calculation."""
        func_name = self._extract_call_name(node.func)
        if func_name and re.search(r"(random\.(random|uniform|randint|choice|randrange)|np\.random|numpy\.random)", func_name):
            # Check if this call is within a function dealing with telemetry/metrics/hardware
            func_scope = self._current_function or ""
            file_name = os.path.basename(self.file_path).lower()
            if re.search(r"(telemetry|metric|speed|benchmark|throughput|latency|dark_mode|mesh|node)", func_scope + " " + file_name, re.I):
                self.violations.append(Violation(
                    file_path=self.file_path,
                    line_number=node.lineno,
                    column=node.col_offset,
                    rule_id="ZM-AST-PY-06",
                    rule_name="Unverified Randomization in Telemetry Pipeline",
                    severity="CRITICAL",
                    offending_code=self._get_line_snippet(node.lineno),
                    message=f"Pseudo-random call '{func_name}' detected inside telemetry/metrics context.",
                    language="Python"
                ))

        self.generic_visit(node)

    def _get_target_name(self, target: ast.AST) -> Optional[str]:
        if isinstance(target, ast.Name):
            return target.id
        if isinstance(target, ast.Attribute):
            return target.attr
        return None

    def _get_const_str(self, node: Optional[ast.AST]) -> Optional[str]:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        return None

    def _get_const_val(self, node: Optional[ast.AST]) -> Any:
        if isinstance(node, ast.Constant):
            return node.value
        return None

    def _extract_var_identifier(self, node: ast.AST) -> Optional[str]:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return node.attr
        return None

    def _extract_call_name(self, node: ast.AST) -> Optional[str]:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            val = self._extract_call_name(node.value)
            return f"{val}.{node.attr}" if val else node.attr
        return None


class JsTsScanner:
    """Scanner for JavaScript / TypeScript / JSX / TSX / MJS source files."""

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
            line_len = len(line) + 1  # include newline
            if cur + line_len > char_index:
                line_num = i + 1
                col_num = char_index - cur
                break
            cur += line_len
        return line_num, col_num

    def _get_line_snippet(self, line_num: int) -> str:
        if 1 <= line_num <= len(self.source_lines):
            return self.source_lines[line_num - 1].strip()
        return ""

    def scan(self) -> List[Violation]:
        # Exemption check: If entire file is an animation or tagged
        is_animation = "/* @verified-visual-animation */" in self.source_text

        # 1. Rule 1: Hardcoded latency / throughput strings and numbers in JS objects (e.g. latency: "0.28ms (DMA)", throughput: "50.0 Mbps", throughput: 10.0, ping: 15)
        pattern_latency = re.compile(
            r"""["']?(?P<key>\b(latency|latency_ms|ping|ping_ms|rtt|rtt_ms|throughput|throughput_mbps|bandwidth|bandwidth_mbps|speed|speed_mbps|single_tp|single_tp_mbps|merged_tp|merged_tp_mbps|pixel_tp|tp_mbps)\b)["']?\s*:\s*(["'](?P<str_val>[0-9]+(\.[0-9]+)?\s*(ms|us|µs|s|ns|mbps|gbps|kbps|mb/s|gb/s|kb/s)(\s*\([^)"']+\))?|[0-9]+(\.[0-9]+)?)[\"']|`(?P<tmpl_val>[^`]*[0-9]+(\.[0-9]+)?\s*(ms|us|µs|s|ns|mbps|gbps|kbps)[^`]*)`|(?P<num_val>[1-9][0-9]*(\.[0-9]+)?|0\.[0-9]+[1-9][0-9]*|0\.[1-9][0-9]*))""",
            re.IGNORECASE
        )
        for m in pattern_latency.finditer(self.source_text):
            line_num, col_num = self._get_line_and_col(m.start())
            val = m.group('str_val') or m.group('tmpl_val') or m.group('num_val') or m.group(0)
            self.violations.append(Violation(
                file_path=self.file_path,
                line_number=line_num,
                column=col_num,
                rule_id="ZM-JS-01",
                rule_name="Hardcoded Telemetry Property in JS Object",
                severity="CRITICAL",
                offending_code=self._get_line_snippet(line_num),
                message=f"Hardcoded telemetry property '{m.group('key')}: {val}' detected in JS/TS object literal.",
                language="JavaScript/TypeScript"
            ))

        # 2. Rule 3: Static node array pre-marked with status: "APPLIED" / "ACTIVE" / "ONLINE" / "CONNECTED"
        pattern_static_fleet = re.compile(
            r"""(const|let|var)\s+(?P<varname>[A-Za-z0-9_$]+)\s*=\s*\[\s*\{[^\]]*status\s*:\s*["'](APPLIED|ACTIVE|ONLINE|CONNECTED|FLEET_DARK_ACTIVE)["']""",
            re.IGNORECASE | re.DOTALL
        )
        for m in pattern_static_fleet.finditer(self.source_text):
            line_num, col_num = self._get_line_and_col(m.start())
            self.violations.append(Violation(
                file_path=self.file_path,
                line_number=line_num,
                column=col_num,
                rule_id="ZM-JS-03",
                rule_name="Static Default Node Array Pre-Marked Active",
                severity="HIGH",
                offending_code=self._get_line_snippet(line_num),
                message=f"Static device array '{m.group('varname')}' initialized with pre-marked active/applied status instead of dynamic REST/WS hydration.",
                language="JavaScript/TypeScript"
            ))

        # 3. Rule 2: Synthetic math multipliers in JS (e.g. single_tp * 2.0, single_tp * 0.5, load * 5)
        pattern_synthetic_mult = re.compile(
            r"""\b(?P<var>(single_tp|single_tp_mbps|pixel_tp|merged_tp|throughput|loadavg|cpu_load|link_speed))\s*\*\s*(?P<factor>0\.[0-9]+|[2-9](\.[0-9]+)?)\b""",
            re.IGNORECASE
        )
        for m in pattern_synthetic_mult.finditer(self.source_text):
            line_num, col_num = self._get_line_and_col(m.start())
            self.violations.append(Violation(
                file_path=self.file_path,
                line_number=line_num,
                column=col_num,
                rule_id="ZM-JS-02",
                rule_name="Synthetic Math Multiplier in JS Telemetry",
                severity="HIGH",
                offending_code=self._get_line_snippet(line_num),
                message=f"Synthetic multiplier detected on '{m.group('var')}' (* {m.group('factor')}).",
                language="JavaScript/TypeScript"
            ))

        # 4. Rule 4: Hardcoded fallback objects in catch blocks or functions
        pattern_fallback_dict = re.compile(
            r"""(devices_active\s*:\s*[1-9][0-9]*|status\s*:\s*["']FLEET_DARK_ACTIVE["'])""",
            re.IGNORECASE
        )
        for m in pattern_fallback_dict.finditer(self.source_text):
            line_num, col_num = self._get_line_and_col(m.start())
            self.violations.append(Violation(
                file_path=self.file_path,
                line_number=line_num,
                column=col_num,
                rule_id="ZM-JS-04",
                rule_name="Hardcoded Fallback Status Object in JS",
                severity="CRITICAL",
                offending_code=self._get_line_snippet(line_num),
                message=f"Hardcoded status/devices fallback literal detected: '{m.group(0)}'.",
                language="JavaScript/TypeScript"
            ))

        # 5. Rule 5: Simulated UI Timers (e.g. setTimeout(() => setStatus('ONLINE'), 1000))
        pattern_sim_timeout = re.compile(
            r"""setTimeout\s*\(\s*(\(\)\s*=>|function\s*\(\))\s*\{?[^}]*(SUCCESS|ONLINE|CONNECTED|APPLIED|FLEET_DARK_ACTIVE)[^}]*\}?,\s*[0-9]+\)""",
            re.IGNORECASE
        )
        for m in pattern_sim_timeout.finditer(self.source_text):
            line_num, col_num = self._get_line_and_col(m.start())
            self.violations.append(Violation(
                file_path=self.file_path,
                line_number=line_num,
                column=col_num,
                rule_id="ZM-JS-05",
                rule_name="Simulated Async Success Timeout",
                severity="CRITICAL",
                offending_code=self._get_line_snippet(line_num),
                message="Simulated UI timer detected transitioning state to ONLINE/APPLIED without real backend confirmation.",
                language="JavaScript/TypeScript"
            ))

        # 6. Rule 6: Math.random() in non-animation telemetry pipelines
        if not is_animation:
            pattern_random = re.compile(
                r"""\bMath\.random\s*\(\s*\)""",
                re.IGNORECASE
            )
            for m in pattern_random.finditer(self.source_text):
                line_num, col_num = self._get_line_and_col(m.start())
                snippet = self._get_line_snippet(line_num)
                # Check if this line is an unverified simulation loop
                self.violations.append(Violation(
                    file_path=self.file_path,
                    line_number=line_num,
                    column=col_num,
                    rule_id="ZM-JS-06",
                    rule_name="Unverified Math.random() in Telemetry/UI Pipeline",
                    severity="CRITICAL" if re.search(r"(vx|vy|radius|hue|latency|status|speed|throughput|node|device)", snippet, re.I) else "MEDIUM",
                    offending_code=snippet,
                    message="Math.random() call detected. If this is a purely visual canvas particle effect, tag with '/* @verified-visual-animation */'.",
                    language="JavaScript/TypeScript"
                ))

        return self.violations


class CrossLanguageCommentJudge:
    """Scans code comments and lexical tokens for explicit simulation remarks and mock names."""

    SIMULATION_COMMENT_REGEX = re.compile(
        r"""(#|//|/\*)\s*(?P<comment>(Simulating|Simulated|Mocking|Fake|Synthetic|Placeholder)\s+(the\s+)?(failover|data|telemetry|metrics|benchmark|logic|response|devices|status))""",
        re.IGNORECASE
    )

    MOCK_VARIABLE_DECLARATION = re.compile(
        r"""\b(?P<var>(mock|dummy|fake|simulated|placeholder)_(data|devices|metrics|stats|telemetry|nodes|fleet|response))\s*=""",
        re.IGNORECASE
    )

    def __init__(self, file_path: str, source_text: str, language: str):
        self.file_path = file_path
        self.source_text = source_text
        self.language = language
        self.source_lines = source_text.splitlines()
        self.violations: List[Violation] = []

    def scan(self) -> List[Violation]:
        for idx, line in enumerate(self.source_lines, start=1):
            # Check simulation comments (Rule 5)
            match_comment = self.SIMULATION_COMMENT_REGEX.search(line)
            if match_comment:
                self.violations.append(Violation(
                    file_path=self.file_path,
                    line_number=idx,
                    column=match_comment.start(),
                    rule_id="ZM-COM-05",
                    rule_name="Explicit Simulation Comment Detected",
                    severity="HIGH",
                    offending_code=line.strip(),
                    message=f"Explicit simulation comment detected: '{match_comment.group('comment')}'.",
                    language=self.language
                ))

            # Check mock variable declarations (Rule 4)
            match_var = self.MOCK_VARIABLE_DECLARATION.search(line)
            if match_var:
                self.violations.append(Violation(
                    file_path=self.file_path,
                    line_number=idx,
                    column=match_var.start(),
                    rule_id="ZM-LEX-04",
                    rule_name="Mock/Dummy Variable Declaration",
                    severity="CRITICAL",
                    offending_code=line.strip(),
                    message=f"Mock variable declaration '{match_var.group('var')}' detected in production code.",
                    language=self.language
                ))

        return self.violations


class ZeroMockStaticJudge:
    """Master Static AST & Regex Judge orchestrating all detection rules across files and directories."""

    SUPPORTED_EXTENSIONS: Set[str] = {
        ".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".json"
    }

    IGNORED_DIRS: Set[str] = {
        "node_modules", ".git", "__pycache__", ".venv", "venv", ".pytest_cache", ".agents"
    }

    def __init__(self, ignore_test_files: bool = True, target_dir: Optional[str] = None):
        self.ignore_test_files = ignore_test_files
        self.target_dir = target_dir

    def is_test_file(self, file_path: str, target_dir: Optional[str] = None) -> bool:
        norm = file_path.replace("\\", "/").lower()
        basename = os.path.basename(norm)
        if (
            basename.startswith("test_")
            or basename.endswith("_test.py")
            or basename.startswith("stress_test")
            or basename.startswith("run_adversarial")
            or basename.endswith(".test.js")
            or basename.endswith(".spec.ts")
            or basename.endswith(".test.ts")
        ):
            return True

        active_target = target_dir or self.target_dir
        if active_target:
            target_norm = str(Path(active_target).resolve()).replace("\\", "/").lower()
            file_abs = str(Path(file_path).resolve()).replace("\\", "/").lower()
            if file_abs.startswith(target_norm):
                rel_path = file_abs[len(target_norm):].lstrip("/")
                rel_parts = rel_path.split("/")[:-1]
                if "tests" in rel_parts or "test" in rel_parts or "challenger_fixtures" in rel_parts:
                    return True
                return False

        parts = norm.split("/")
        if "tests" in parts or "test" in parts:
            return True
        return False

    def audit_file(self, file_path: str) -> List[Violation]:
        path = Path(file_path).resolve()
        if not path.exists() or not path.is_file():
            return []

        if self.ignore_test_files and self.is_test_file(str(path), target_dir=self.target_dir):
            # Don't audit the test suite itself unless requested
            return []

        suffix = path.suffix.lower()
        if suffix not in self.SUPPORTED_EXTENSIONS:
            return []

        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception as e:
            return []

        violations: List[Violation] = []
        lines = content.splitlines()

        # 1. Lexical & Comment scan (all languages)
        lang = "Python" if suffix == ".py" else ("JSON" if suffix == ".json" else "JavaScript/TypeScript")
        comment_judge = CrossLanguageCommentJudge(str(path), content, lang)
        violations.extend(comment_judge.scan())

        # 2. Language-specific AST/token inspection
        if suffix == ".py":
            try:
                tree = ast.parse(content, filename=str(path))
                py_judge = PythonAstJudge(str(path), lines)
                py_judge.visit(tree)
                violations.extend(py_judge.violations)
            except SyntaxError as e:
                # If syntax error in python file, log syntax error violation
                violations.append(Violation(
                    file_path=str(path),
                    line_number=e.lineno or 1,
                    column=e.offset or 0,
                    rule_id="ZM-SYNTAX-ERR",
                    rule_name="Python Syntax Error",
                    severity="HIGH",
                    offending_code=e.text.strip() if e.text else "",
                    message=f"Syntax error during AST parse: {e.msg}",
                    language="Python"
                ))
        elif suffix in (".js", ".jsx", ".ts", ".tsx", ".mjs"):
            js_scanner = JsTsScanner(str(path), content)
            violations.extend(js_scanner.scan())
        elif suffix == ".json":
            # JSON file analysis: check for static mock latency values in device objects
            try:
                data = json.loads(content)
                self._audit_json_node(str(path), data, violations, "$")
            except json.JSONDecodeError:
                pass

        return violations

    def _audit_json_node(self, file_path: str, node: Any, violations: List[Violation], json_path: str):
        if isinstance(node, dict):
            for k, v in node.items():
                current_path = f"{json_path}.{k}"
                if TELEMETRY_KEYS_REGEX.match(k):
                    if isinstance(v, str) and LATENCY_STRING_REGEX.match(v.strip()):
                        violations.append(Violation(
                            file_path=file_path,
                            line_number=1,
                            column=0,
                            rule_id="ZM-JSON-01",
                            rule_name="Hardcoded Telemetry String in JSON",
                            severity="CRITICAL",
                            offending_code=f'"{k}": "{v}"',
                            message=f"Hardcoded latency string '{v}' at JSON path '{current_path}'.",
                            language="JSON"
                        ))
                self._audit_json_node(file_path, v, violations, current_path)
        elif isinstance(node, list):
            for i, item in enumerate(node):
                self._audit_json_node(file_path, item, violations, f"{json_path}[{i}]")

    def audit_directory(self, target_dir: str) -> List[Violation]:
        root_path = Path(target_dir).resolve()
        if not root_path.exists() or not root_path.is_dir():
            return []

        self.target_dir = str(root_path)
        all_violations: List[Violation] = []

        for root, dirs, files in os.walk(root_path):
            # Prune ignored directories
            dirs[:] = [d for d in dirs if d not in self.IGNORED_DIRS]

            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in self.SUPPORTED_EXTENSIONS:
                    fpath = os.path.join(root, file)
                    all_violations.extend(self.audit_file(fpath))

        return all_violations

    def calculate_score(self, violations: List[Violation]) -> float:
        """
        Scoring formula:
        Score = 100 - (30 * N_critical) - (15 * N_high) - (5 * N_medium) - (1 * N_low)
        Bounded between 0.0 and 100.0.
        """
        penalties = {
            "CRITICAL": 30.0,
            "HIGH": 15.0,
            "MEDIUM": 5.0,
            "LOW": 1.0
        }
        total_penalty = sum(penalties.get(v.severity.upper(), 5.0) for v in violations)
        return max(0.0, round(100.0 - total_penalty, 2))

    def generate_report(self, target_path: str, violations: List[Violation]) -> Dict[str, Any]:
        score = self.calculate_score(violations)
        severity_counts = {
            "CRITICAL": 0,
            "HIGH": 0,
            "MEDIUM": 0,
            "LOW": 0
        }
        rule_counts: Dict[str, int] = {}

        for v in violations:
            sev = v.severity.upper()
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
            rule_counts[v.rule_id] = rule_counts.get(v.rule_id, 0) + 1

        is_clean = (len(violations) == 0) and (score == 100.0)

        return {
            "audit_target": target_path,
            "verdict": "ZERO_MOCK_CERTIFIED" if is_clean else "MOCK_VIOLATIONS_DETECTED",
            "score": score,
            "total_violations": len(violations),
            "severity_summary": severity_counts,
            "rule_distribution": rule_counts,
            "violations": [v.to_dict() for v in violations]
        }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Zero-Mock Static AST & Regex Judge")
    parser.add_argument("--target-dir", type=str, default=".", help="Target directory to audit")
    parser.add_argument("--target-file", type=str, default=None, help="Specific file to audit")
    parser.add_argument("--json-output", type=str, default=None, help="Save structured JSON report to path")
    parser.add_argument("--fail-under", type=float, default=100.0, help="Fail threshold score (default: 100.0)")
    parser.add_argument("--include-tests", action="store_true", help="Include test files in audit")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print verbose violation details")

    args = parser.parse_args()

    judge = ZeroMockStaticJudge(ignore_test_files=not args.include_tests)

    if args.target_file:
        violations = judge.audit_file(args.target_file)
        target = args.target_file
    else:
        violations = judge.audit_directory(args.target_dir)
        target = args.target_dir

    report = judge.generate_report(target, violations)

    print(f"\n=======================================================")
    print(f" ZERO-MOCK STATIC AST & PATTERN AUDIT REPORT")
    print(f"=======================================================")
    print(f" Target:      {target}")
    print(f" Verdict:     {report['verdict']}")
    print(f" Truth Score: {report['score']} / 100.0")
    print(f" Violations:  {report['total_violations']}")
    print(f" Breakdown:   CRITICAL={report['severity_summary']['CRITICAL']}, HIGH={report['severity_summary']['HIGH']}, MEDIUM={report['severity_summary']['MEDIUM']}")
    print(f"-------------------------------------------------------")

    if violations:
        print("\nTOP VIOLATIONS DETECTED:")
        for idx, v in enumerate(violations[:20], 1):
            print(f" [{idx}] {v.severity} [{v.rule_id}] {v.file_path}:{v.line_number}")
            print(f"     Offense: {v.offending_code}")
            print(f"     Detail:  {v.message}\n")
        if len(violations) > 20:
            print(f" ... and {len(violations) - 20} more violations.")

    if args.json_output:
        out_path = Path(args.json_output).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"Saved JSON report to: {out_path}")

    sys.exit(0 if report["score"] >= args.fail_under else 1)


if __name__ == "__main__":
    main()
