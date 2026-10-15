"""
5-Tier Verification Suite for CodeClash Swarm AST Analysis Specialist & Polyglot Engine.
Tests:
- Polyglot Parsers (Python, Rust MIR, Go, TypeScript)
- Control Flow Graph (CFG) & Cyclomatic Complexity
- Python VM Bytecode Stack Simulation & Decompilation
- AST De-obfuscation & Dead-Code Elimination (DCE)
- Adversarial Test Synthesis & Sandboxed Execution
- CLI Subcommands & JSON Serialization
"""
import ast
import json
import os
import subprocess
import sys
import tempfile
import pytest

# Ensure module path is accessible
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ast_analysis_specialist import (
    ASTAnalysisSpecialist,
    PythonCFGBuilder,
    BytecodeDecompiler,
    ASTDeobfuscator,
    AdversarialTestSynthesizer,
    parse_ast,
    build_cfg,
    decompile_bytecode,
    deobfuscate_ast,
    generate_adversarial_tests,
)
from models.schemas import (
    LanguageType,
    SymbolScope,
    SymbolRecord,
    BasicBlock,
    CFGEdge,
    CFGResult,
    ASTAnalysisReport,
    DecompilationResult,
    AdversarialTestResult,
)


class TestPolyglotASTParsers:
    """Tier 1: Polyglot AST parsing and symbol resolution across 4 languages."""

    def test_python_ast_parsing(self):
        source = """
import math

class DataProcessor:
    def process(self, x: int, y: int) -> float:
        z = x + y
        if z > 0:
            return math.sqrt(z)
        return 0.0
"""
        report = parse_ast(source, language="python")
        assert report.language == LanguageType.PYTHON
        assert "DataProcessor" in report.classes
        assert "process" in report.functions
        assert not report.has_syntax_errors
        assert report.cyclomatic_complexity_total >= 2

        sym_names = [s.name for s in report.symbols]
        assert "DataProcessor" in sym_names or "process" in sym_names or "x" in sym_names

    def test_rust_mir_and_ast_parsing(self):
        rust_source = """
pub struct Point {
    pub x: i32,
    pub y: i32,
}

pub fn calculate_distance(p: Point) -> i32 {
    if p.x > 0 {
        p.x + p.y
    } else {
        p.y - p.x
    }
}
"""
        report = parse_ast(rust_source, language="rust")
        assert report.language == LanguageType.RUST
        assert "calculate_distance" in report.functions
        assert "Point" in report.classes
        assert "calculate_distance" in report.cfgs
        cfg = report.cfgs["calculate_distance"]
        assert len(cfg.blocks) >= 2
        assert len(cfg.edges) >= 1

    def test_go_ast_parsing(self):
        go_source = """
package telemetry

type PacketHeader struct {
    Version int
    Length  int
}

func ValidatePacket(hdr PacketHeader, payload []byte) bool {
    if hdr.Length > 0 && len(payload) == hdr.Length {
        return true
    }
    return false
}
"""
        report = parse_ast(go_source, language="go")
        assert report.language == LanguageType.GO
        assert "ValidatePacket" in report.functions
        assert "PacketHeader" in report.classes
        assert any(s.name == "hdr" for s in report.symbols)

    def test_typescript_ast_parsing(self):
        ts_source = """
export interface SessionConfig {
    timeoutMs: number;
}

export class AuthClient {
    private token: string;
}

export async function authenticateUser(username: string, token: string): Promise<boolean> {
    if (username.length > 0 && token.length > 0) {
        return true;
    }
    return false;
}
"""
        report = parse_ast(ts_source, language="typescript")
        assert report.language == LanguageType.TYPESCRIPT
        assert "authenticateUser" in report.functions
        assert "AuthClient" in report.classes
        assert any("SessionConfig" in c for c in report.classes)


class TestCFGBuilder:
    """Tier 2: Control Flow Graph statement-level partitioning and edge typing."""

    def test_python_cfg_branching(self):
        source = """
def check_temperature(temp):
    if temp > 100:
        state = "BOILING"
        return state
    elif temp < 0:
        state = "FREEZING"
        return state
    else:
        state = "LIQUID"
        return state
"""
        report = parse_ast(source, language="python")
        cfg = report.cfgs["check_temperature"]

        # Check edge types
        edge_types = [e.edge_type for e in cfg.edges]
        assert "true_branch" in edge_types
        assert "false_branch" in edge_types
        assert "return" in edge_types

        # Check entry and exit blocks
        assert cfg.entry_block_id in cfg.blocks
        assert cfg.blocks[cfg.entry_block_id].is_entry

    def test_python_cfg_loops(self):
        source = """
def compute_sum(n):
    total = 0
    for i in range(n):
        total += i
    return total
"""
        report = parse_ast(source, language="python")
        cfg = report.cfgs["compute_sum"]
        edge_types = [e.edge_type for e in cfg.edges]
        assert "loop_step" in edge_types
        assert "loop_back" in edge_types
        assert "loop_exit" in edge_types

    def test_cyclomatic_complexity_calculation(self):
        source = """
def complex_fn(a, b, c):
    if a > 0:
        if b > 0:
            return a + b
        else:
            return a - b
    else:
        if c > 0:
            return a * c
        return 0
"""
        report = parse_ast(source, language="python")
        cfg = report.cfgs["complex_fn"]
        # M = E - N + 2
        assert cfg.cyclomatic_complexity >= 4


class TestBytecodeDecompiler:
    """Tier 3: Python VM Bytecode Stack Simulation and Roundtrip Decompilation."""

    def test_decompile_arithmetic_function(self):
        def sample_arith(a, b):
            c = a + b * 2
            return c

        result = decompile_bytecode(sample_arith)
        assert result.original_format == "bytecode"
        assert result.is_valid_syntax
        assert result.roundtrip_ast_verified
        assert "def sample_arith(a, b):" in result.reconstructed_code
        assert "return" in result.reconstructed_code

    def test_decompile_module_code_object(self):
        code_str = """
def multiply_and_offset(x, factor, offset):
    val = x * factor + offset
    return val
"""
        compiled = compile(code_str, "<test>", "exec")
        result = decompile_bytecode(compiled)
        assert result.is_valid_syntax
        assert result.roundtrip_ast_verified
        assert "multiply_and_offset" in result.reconstructed_code


class TestASTDeobfuscator:
    """Tier 4: AST De-obfuscation, Constant Folding & Dead-Code Elimination (DCE)."""

    def test_identifier_renaming_and_folding(self):
        obfuscated = """
def _0xbeef(_0x1111, _0x2222):
    _0x3333 = 10 + 20
    _0x4444 = 5 * 2
    if False:
        dead_stmt = 999
    if True:
        live_stmt = 100
    return _0x1111 + _0x3333
    unreachable_code = 42
"""
        result = deobfuscate_ast(obfuscated)
        assert result.is_valid_syntax
        assert result.roundtrip_ast_verified
        assert result.deobfuscated_identifiers >= 3
        assert result.eliminated_dead_blocks >= 2

        # Verify constant folding took place (10 + 20 -> 30)
        assert "30" in result.reconstructed_code
        # Verify dead code was eliminated
        assert "dead_stmt" not in result.reconstructed_code
        assert "unreachable_code" not in result.reconstructed_code
        # Verify obfuscated identifiers are replaced
        assert "_0xbeef" not in result.reconstructed_code


class TestAdversarialTestSynthesizer:
    """Tier 5: Adversarial Boundary Test Suite Synthesis & Execution."""

    def test_synthesize_and_run_pytest(self):
        code = """
def safe_divide(x, y):
    if y == 0:
        raise ZeroDivisionError("Cannot divide by zero")
    return x / y
"""
        result = generate_adversarial_tests(code, language="python")
        assert result.test_cases_count >= 20
        assert "numerical_limits" in result.boundary_types_covered
        assert "unicode_and_format_strings" in result.boundary_types_covered
        assert "collections_and_null" in result.boundary_types_covered
        assert result.execution_passed
        assert result.execution_time_ms > 0
        assert "@pytest.mark.parametrize" in result.test_code

    def test_synthesize_cargo_test_harness(self):
        rust_code = """
pub fn compute_square(n: i32) -> i32 {
    n * n
}
"""
        result = generate_adversarial_tests(rust_code, language="rust")
        assert result.test_cases_count >= 3
        assert "numerical_limits" in result.boundary_types_covered
        assert "#[cfg(test)]" in result.test_code
        assert "compute_square" in result.test_code


class TestCLIInterface:
    """CLI Integration tests for standalone invocations."""

    def test_cli_parse_json(self):
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as tf:
            tf.write("def sample_fn(a, b):\n    return a + b\n")
            tf_path = tf.name

        cli_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ast_analysis_specialist.py"))
        res = subprocess.run(
            [sys.executable, cli_path, "--parse", tf_path, "--json"],
            capture_output=True,
            text=True,
        )
        os.remove(tf_path)

        assert res.returncode == 0
        data = json.loads(res.stdout)
        assert data["language"] == "python"
        assert "sample_fn" in data["functions"]

    def test_cli_cfg_generation(self):
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as tf:
            tf.write("def branching_fn(x):\n    if x > 0:\n        return 1\n    return 0\n")
            tf_path = tf.name

        cli_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ast_analysis_specialist.py"))
        res = subprocess.run(
            [sys.executable, cli_path, "--cfg", tf_path, "--json"],
            capture_output=True,
            text=True,
        )
        os.remove(tf_path)

        assert res.returncode == 0
        data = json.loads(res.stdout)
        assert "branching_fn" in data
        assert len(data["branching_fn"]["blocks"]) >= 2

    def test_cli_deobfuscate(self):
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as tf:
            tf.write("def _0x1234():\n    return 10 + 20\n")
            tf_path = tf.name

        cli_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ast_analysis_specialist.py"))
        res = subprocess.run(
            [sys.executable, cli_path, "--deobfuscate", tf_path, "--json"],
            capture_output=True,
            text=True,
        )
        os.remove(tf_path)

        assert res.returncode == 0
        data = json.loads(res.stdout)
        assert data["is_valid_syntax"]
        assert "30" in data["reconstructed_code"]
