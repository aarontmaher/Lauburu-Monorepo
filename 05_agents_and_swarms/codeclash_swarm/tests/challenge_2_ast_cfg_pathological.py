"""
Adversarial Stress Test Harness 2: AST & CFG Pathological Code Constructs.
Empirical Challenger: Challenger 1 (CodeClash Swarm)
"""
import ast
import dis
import json
import math
import sys
import time
from typing import Any, Dict, List, Tuple

sys.path.insert(0, "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/05_agents_and_swarms/codeclash_swarm")
from ast_analysis_specialist import (
    ASTAnalysisSpecialist,
    BytecodeDecompiler,
    ASTDeobfuscator,
    PythonCFGBuilder,
    parse_ast,
    build_cfg,
    decompile_bytecode,
    deobfuscate_ast,
)


def test_deeply_nested_asts() -> Dict[str, Any]:
    """Test parser and CFG builder on deeply nested ASTs (500+ levels)."""
    results = {}

    # 1. 500-level nested BinOps: 1 + (1 + (1 + ...))
    sys.setrecursionlimit(5000)
    nesting_depth = 500
    nested_expr = "1"
    for _ in range(nesting_depth):
        nested_expr = f"({nested_expr} + 1)"
    deep_expr_code = f"def deep_binop():\n    return {nested_expr}\n"

    start = time.perf_counter()
    report_binop = parse_ast(deep_expr_code, language="python")
    dur_binop = (time.perf_counter() - start) * 1000.0

    results["nested_binop_500"] = {
        "depth": nesting_depth,
        "parsed_successfully": not report_binop.has_syntax_errors,
        "functions_found": report_binop.functions,
        "duration_ms": dur_binop,
        "complexity": report_binop.cyclomatic_complexity_total,
    }

    # 2. 100-level nested If statements
    if_lines = ["def deep_if(x):"]
    for i in range(100):
        indent = "    " * (i + 1)
        if_lines.append(f"{indent}if x > {i}:")
    indent = "    " * 101
    if_lines.append(f"{indent}return 42")
    for i in range(99, -1, -1):
        indent = "    " * (i + 1)
        if_lines.append(f"{indent}else:\n{indent}    return -{i}")
    deep_if_code = "\n".join(if_lines)

    start = time.perf_counter()
    report_if = parse_ast(deep_if_code, language="python")
    dur_if = (time.perf_counter() - start) * 1000.0

    results["nested_if_100"] = {
        "depth": 100,
        "parsed_successfully": not report_if.has_syntax_errors,
        "functions_found": report_if.functions,
        "duration_ms": dur_if,
        "complexity": report_if.cyclomatic_complexity_total,
    }

    # 3. 50-level nested Try/Except blocks
    try_lines = ["def deep_try():"]
    for i in range(50):
        indent = "    " * (i + 1)
        try_lines.append(f"{indent}try:")
    indent = "    " * 51
    try_lines.append(f"{indent}raise ValueError('deep')")
    for i in range(49, -1, -1):
        indent = "    " * (i + 1)
        try_lines.append(f"{indent}except ValueError:\n{indent}    pass")
    deep_try_code = "\n".join(try_lines)

    start = time.perf_counter()
    report_try = parse_ast(deep_try_code, language="python")
    dur_try = (time.perf_counter() - start) * 1000.0

    results["nested_try_50"] = {
        "depth": 50,
        "parsed_successfully": not report_try.has_syntax_errors,
        "functions_found": report_try.functions,
        "duration_ms": dur_try,
        "complexity": report_try.cyclomatic_complexity_total,
    }

    return results


def test_cyclic_and_complex_cfg_branching() -> Dict[str, Any]:
    """Test CFG extraction on cyclic, multi-exit, break/continue, and complex loops."""
    test_cases = {
        "nested_while_break_continue": """
def complex_loops(n):
    total = 0
    i = 0
    while i < n:
        j = 0
        while j < n:
            if j == 5:
                break
            elif j % 2 == 0:
                j += 1
                continue
            total += i * j
            j += 1
        if total > 1000:
            return total
        i += 1
    return total
""",
        "infinite_loop_multiple_returns": """
def multi_exit_loop(flag_a, flag_b):
    while True:
        if flag_a:
            return 1
        if flag_b:
            return 2
        break
    return 0
""",
        "unreachable_code_after_returns": """
def unreachable_blocks(x):
    if x > 0:
        return x * 2
        print("unreachable 1")
        x += 10
    else:
        return -x
        print("unreachable 2")
    print("unreachable 3")
    return 0
""",
        "mutual_recursion": """
def is_even(n):
    if n == 0:
        return True
    return is_odd(n - 1)

def is_odd(n):
    if n == 0:
        return False
    return is_even(n - 1)
""",
        "try_except_finally_cascade": """
def try_cascade(a, b):
    try:
        if a > 0:
            try:
                res = a / b
                return res
            except ZeroDivisionError:
                return -1
        else:
            raise ValueError("Negative a")
    except ValueError as e:
        return 0
    except Exception:
        return -999
    return 100
"""
    }

    results = {}
    for name, code in test_cases.items():
        start = time.perf_counter()
        report = parse_ast(code, language="python")
        dur = (time.perf_counter() - start) * 1000.0

        cfgs_info = {}
        for fn_name, cfg in report.cfgs.items():
            # Check invariant: M = E - N + 2
            E = len(cfg.edges)
            N = len(cfg.blocks)
            expected_M = max(1, E - N + 2)
            cfgs_info[fn_name] = {
                "blocks_count": N,
                "edges_count": E,
                "cyclomatic_complexity": cfg.cyclomatic_complexity,
                "formula_matches": (cfg.cyclomatic_complexity == expected_M),
                "entry_block": cfg.entry_block_id,
                "exit_blocks": cfg.exit_block_ids,
            }

        results[name] = {
            "parsed_successfully": not report.has_syntax_errors,
            "functions": report.functions,
            "cfgs": cfgs_info,
            "duration_ms": dur,
        }

    return results


def test_zero_statement_functions_and_empty_constructs() -> Dict[str, Any]:
    """Test AST analysis against zero-statement functions, empty files, pass-only, and ellipses."""
    cases = {
        "pass_only": "def empty_pass(): pass",
        "docstring_only": 'def doc_only(): """This is a docstring."""',
        "ellipsis_only": "def ellipsis_fn(): ...",
        "multiple_pass": "def multi_pass():\n    pass\n    pass\n    pass\n",
        "async_empty": "async def async_empty(): pass",
        "lambda_simple": "f = lambda x: x * 2",
        "empty_module": "",
        "comment_only": "# Only comments\n# Line 2\n",
        "type_annotated_stub": "def typed_stub(x: int, y: str = 'default') -> bool: ...",
    }

    results = {}
    for name, code in cases.items():
        start = time.perf_counter()
        report = parse_ast(code, language="python")
        dur = (time.perf_counter() - start) * 1000.0

        results[name] = {
            "parsed_successfully": not report.has_syntax_errors,
            "functions": report.functions,
            "symbols_count": len(report.symbols),
            "complexity_total": report.cyclomatic_complexity_total,
            "duration_ms": dur,
        }

    return results


def test_python_313_match_case_blocks() -> Dict[str, Any]:
    """Test AST parser and CFG builder on complex Python pattern matching blocks."""
    match_code = """
def pattern_dispatch(command):
    match command:
        case "quit" | "exit":
            return 0
        case ["load", filename]:
            return f"Loading {filename}"
        case ["save", filename, *options]:
            return f"Saving {filename} with {options}"
        case {"action": "move", "dx": dx, "dy": dy} if dx != 0 or dy != 0:
            return (dx, dy)
        case {"action": "jump", "power": p}:
            return p * 1.5
        case int(val) | float(val) if val > 0:
            return val * 10
        case _:
            return -1
"""
    start = time.perf_counter()
    report = parse_ast(match_code, language="python")
    dur = (time.perf_counter() - start) * 1000.0

    return {
        "code_snippet": "match command with 7 cases",
        "parsed_successfully": not report.has_syntax_errors,
        "functions": report.functions,
        "symbols": [s.name for s in report.symbols],
        "cyclomatic_complexity": report.cyclomatic_complexity_total,
        "duration_ms": dur,
    }


def test_bytecodes_with_obfuscated_constants() -> Dict[str, Any]:
    """Test bytecode decompiler & deobfuscator on unusual and obfuscated constants."""
    def sample_obfuscated_func():
        _0x1 = 10000000000000000000000000000000000000000000000000
        _0x2 = float('inf')
        _0x3 = float('-inf')
        _0x4 = float('nan')
        _0x5 = -0.0
        _0x6 = 10 + 20 * 3
        _0x7 = "obfuscated_string_\u202e\u202d_test"
        _0x8 = ((1, 2), (3, (4, 5)))
        return _0x1 + _0x6

    code_obj = sample_obfuscated_func.__code__
    start = time.perf_counter()
    decomp = decompile_bytecode(code_obj)
    dur_decomp = (time.perf_counter() - start) * 1000.0

    start = time.perf_counter()
    deob = deobfuscate_ast(decomp.reconstructed_code)
    dur_deob = (time.perf_counter() - start) * 1000.0

    return {
        "constants_in_code": [str(c) for c in code_obj.co_consts if not hasattr(c, "co_code")],
        "decompilation_valid_syntax": decomp.is_valid_syntax,
        "decompiled_code": decomp.reconstructed_code,
        "decomp_duration_ms": dur_decomp,
        "deobfuscated_identifiers": deob.deobfuscated_identifiers,
        "deobfuscated_valid_syntax": deob.is_valid_syntax,
        "deobfuscated_code": deob.reconstructed_code,
        "deob_duration_ms": dur_deob,
    }


def main():
    print("=== STARTING CHALLENGE 2: AST & CFG PATHOLOGICAL CODE CONSTRUCTS ===")

    print("\n[Phase 1] Deeply Nested ASTs (500+ levels BinOp, 100 levels If, 50 levels Try)...")
    nested_res = test_deeply_nested_asts()
    for k, v in nested_res.items():
        print(f"  {k}: Success={v['parsed_successfully']}, Complexity={v['complexity']}, Time={v['duration_ms']:.2f}ms")

    print("\n[Phase 2] Cyclic & Multi-Exit CFG Branching Structures...")
    cfg_res = test_cyclic_and_complex_cfg_branching()
    for k, v in cfg_res.items():
        all_formulas = all(cfg['formula_matches'] for cfg in v['cfgs'].values())
        print(f"  {k}: Success={v['parsed_successfully']}, Functions={v['functions']}, M_Formulas_OK={all_formulas}, Time={v['duration_ms']:.2f}ms")

    print("\n[Phase 3] Zero-Statement Functions & Degenerate Constructs...")
    zero_res = test_zero_statement_functions_and_empty_constructs()
    for k, v in zero_res.items():
        print(f"  {k}: Success={v['parsed_successfully']}, Functions={v['functions']}, Symbols={v['symbols_count']}, Time={v['duration_ms']:.2f}ms")

    print("\n[Phase 4] Complex Python 3.13 Pattern Matching (match/case)...")
    match_res = test_python_313_match_case_blocks()
    print(f"  Match/Case: Success={match_res['parsed_successfully']}, Functions={match_res['functions']}, Complexity={match_res['cyclomatic_complexity']}, Time={match_res['duration_ms']:.2f}ms")

    print("\n[Phase 5] Bytecode with Obfuscated Constants & Stack Simulation...")
    const_res = test_bytecodes_with_obfuscated_constants()
    print(f"  Constants: {const_res['constants_in_code'][:5]}...")
    print(f"  Decompile Valid Syntax : {const_res['decompilation_valid_syntax']} ({const_res['decomp_duration_ms']:.2f}ms)")
    print(f"  Deobfuscate Identifiers: {const_res['deobfuscated_identifiers']} ({const_res['deob_duration_ms']:.2f}ms)")

    report = {
        "campaign": "AST & CFG Pathological Constructs Stress",
        "timestamp": time.time(),
        "nested_asts": nested_res,
        "cyclic_cfgs": cfg_res,
        "zero_statements": zero_res,
        "match_case": match_res,
        "obfuscated_constants": const_res,
    }

    with open("/Users/aaron/.agents/teamwork_preview_challenger_1/ast_cfg_stress_results.json", "w") as f:
        json.dump(report, f, indent=2)

    print("\n=== CHALLENGE 2 COMPLETE: Saved to ast_cfg_stress_results.json ===")


if __name__ == "__main__":
    main()
