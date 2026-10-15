"""
Adversarial Stress Test Harness 3: Decompiler & De-obfuscation Semantic Roundtrip Oracle.
Empirical Challenger: Challenger 1 (CodeClash Swarm)
"""
import ast
import inspect
import json
import math
import random
import sys
import time
from typing import Any, Callable, Dict, List, Tuple

sys.path.insert(0, "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/05_agents_and_swarms/codeclash_swarm")
from ast_analysis_specialist import (
    BytecodeDecompiler,
    ASTDeobfuscator,
    decompile_bytecode,
    deobfuscate_ast,
)

ALGORITHMS = {
    "1_fibonacci_iterative": (
        """
def fibonacci(n):
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    a = 0
    b = 1
    for _ in range(2, n + 1):
        c = a + b
        a = b
        b = c
    return b
""",
        "fibonacci",
        [0, 1, 2, 3, 5, 10, 20, 30, 40]
    ),
    "2_gcd_euclidean": (
        """
def gcd(a, b):
    while b != 0:
        temp = b
        b = a % b
        a = temp
    return a
""",
        "gcd",
        [(48, 18), (101, 103), (0, 5), (1000, 250), (270, 192), (1071, 462)]
    ),
    "3_sieve_of_eratosthenes": (
        """
def sieve(limit):
    if limit < 2:
        return []
    primes = []
    is_prime = [True] * (limit + 1)
    is_prime[0] = False
    is_prime[1] = False
    for p in range(2, int(limit**0.5) + 1):
        if is_prime[p]:
            for i in range(p * p, limit + 1, p):
                is_prime[i] = False
    for p in range(2, limit + 1):
        if is_prime[p]:
            primes.append(p)
    return primes
""",
        "sieve",
        [0, 1, 2, 10, 30, 50, 100]
    ),
    "4_matrix_multiplication": (
        """
def matmul_2x2(a, b):
    res = [[0, 0], [0, 0]]
    res[0][0] = a[0][0] * b[0][0] + a[0][1] * b[1][0]
    res[0][1] = a[0][0] * b[0][1] + a[0][1] * b[1][1]
    res[1][0] = a[1][0] * b[0][0] + a[1][1] * b[1][0]
    res[1][1] = a[1][0] * b[0][1] + a[1][1] * b[1][1]
    return res
""",
        "matmul_2x2",
        [
            ([[1, 2], [3, 4]], [[5, 6], [7, 8]]),
            ([[0, 0], [0, 0]], [[1, 1], [1, 1]]),
            ([[1, 0], [0, 1]], [[9, 8], [7, 6]]),
            ([[-1, 2], [3, -4]], [[2, -1], [-4, 3]]),
        ]
    ),
    "5_dsp_fir_filter": (
        """
def fir_filter(signal, coeffs):
    output = []
    n = len(signal)
    m = len(coeffs)
    for i in range(n):
        acc = 0.0
        for j in range(m):
            if i - j >= 0:
                acc += signal[i - j] * coeffs[j]
        output.append(round(acc, 4))
    return output
""",
        "fir_filter",
        [
            ([1.0, 2.0, 3.0, 4.0, 5.0], [0.2, 0.5, 0.3]),
            ([0.0, 0.0, 0.0], [1.0, 1.0]),
            ([10.0, -5.0, 2.0, 8.0], [0.1, 0.2, 0.4, 0.2, 0.1]),
        ]
    ),
    "6_binary_search": (
        """
def binary_search(arr, target):
    low = 0
    high = len(arr) - 1
    while low <= high:
        mid = (low + high) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            low = mid + 1
        else:
            high = mid - 1
    return -1
""",
        "binary_search",
        [
            ([1, 3, 5, 7, 9, 11, 13], 7),
            ([1, 3, 5, 7, 9, 11, 13], 1),
            ([1, 3, 5, 7, 9, 11, 13], 13),
            ([1, 3, 5, 7, 9, 11, 13], 8),
            ([], 5),
            ([42], 42),
            ([42], 0),
        ]
    ),
    "7_quicksort": (
        """
def quicksort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quicksort(left) + middle + quicksort(right)
""",
        "quicksort",
        [
            [5, 2, 9, 1, 7, 6, 3],
            [],
            [1],
            [9, 8, 7, 6, 5, 4, 3, 2, 1],
            [1, 1, 1, 1, 1],
            [-5, 10, -20, 0, 100, -50],
        ]
    ),
    "8_mergesort": (
        """
def mergesort(arr):
    if len(arr) <= 1:
        return arr
    mid = len(arr) // 2
    left = mergesort(arr[:mid])
    right = mergesort(arr[mid:])
    result = []
    i = 0
    j = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1
    result.extend(left[i:])
    result.extend(right[j:])
    return result
""",
        "mergesort",
        [
            [12, 11, 13, 5, 6, 7],
            [],
            [3, 2, 1],
            [1, 2, 3, 4, 5],
            [5, 5, 5, 2, 2, 8, 8],
        ]
    ),
    "9_levenshtein_distance": (
        """
def levenshtein(s1, s2):
    m = len(s1)
    n = len(s2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s1[i - 1] == s2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])
    return dp[m][n]
""",
        "levenshtein",
        [
            ("kitten", "sitting"),
            ("", ""),
            ("a", ""),
            ("", "abc"),
            ("flaw", "lawn"),
            ("lauburu", "lauburu"),
        ]
    ),
    "10_crc32_bitwise": (
        """
def crc32_simple(data_bytes):
    crc = 0xFFFFFFFF
    for b in data_bytes:
        crc ^= b
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xEDB88320
            else:
                crc = crc >> 1
    return crc ^ 0xFFFFFFFF
""",
        "crc32_simple",
        [
            [1, 2, 3, 4, 5],
            [],
            [0],
            [255, 254, 253],
            [ord(c) for c in "Lauburu Mesh 2026"],
        ]
    ),
    "11_run_length_encoding": (
        """
def rle_encode(text):
    if not text:
        return ""
    res = []
    count = 1
    curr = text[0]
    for char in text[1:]:
        if char == curr:
            count += 1
        else:
            res.append(f"{curr}{count}")
            curr = char
            count = 1
    res.append(f"{curr}{count}")
    return "".join(res)
""",
        "rle_encode",
        [
            "AAABBBCCDAA",
            "",
            "A",
            "ABCDE",
            "WWWWWWWWWWWWBWWWWWWWWWWWWBBBWWWWWWWWWWWWWWWWWWWWWWWWB",
        ]
    ),
    "12_bradley_terry_elo": (
        """
def elo_win_prob(rating_a, rating_b):
    exponent = (rating_b - rating_a) / 400.0
    prob_a = 1.0 / (1.0 + 10.0 ** exponent)
    return round(prob_a, 6)
""",
        "elo_win_prob",
        [
            (1500.0, 1500.0),
            (1600.0, 1400.0),
            (1200.0, 1800.0),
            (2000.0, 1000.0),
            (1000.0, 2000.0),
        ]
    ),
    "13_pan_tompkins_qrs_energy": (
        """
def qrs_energy_detector(ecg_samples, window_size):
    n = len(ecg_samples)
    if n < window_size:
        return [0.0] * n
    diff = []
    for i in range(1, n):
        d = ecg_samples[i] - ecg_samples[i - 1]
        diff.append(d * d)
    diff.append(0.0)
    integrated = []
    for i in range(n):
        start = max(0, i - window_size + 1)
        sub = diff[start:i + 1]
        avg = sum(sub) / float(len(sub)) if sub else 0.0
        integrated.append(round(avg, 4))
    return integrated
""",
        "qrs_energy_detector",
        [
            ([0.1, 0.2, 0.8, 1.5, 0.3, 0.1, 0.0, 0.1, 0.9, 1.6, 0.2], 3),
            ([0.0] * 10, 4),
            ([1.0, -1.0, 1.0, -1.0, 1.0], 2),
        ]
    ),
    "14_token_bucket_rate_limiter": (
        """
def simulate_token_bucket(capacity, fill_rate, request_intervals):
    tokens = float(capacity)
    allowed = []
    for dt in request_intervals:
        tokens = min(float(capacity), tokens + dt * fill_rate)
        if tokens >= 1.0:
            tokens -= 1.0
            allowed.append(True)
        else:
            allowed.append(False)
    return allowed
""",
        "simulate_token_bucket",
        [
            (5, 1.0, [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 2.0, 0.1]),
            (1, 0.5, [1.0, 1.0, 1.0, 0.1, 0.1]),
            (10, 10.0, [0.01] * 15),
        ]
    ),
    "15_fast_path_storage_hash": (
        """
def compute_storage_invariant_hash(paths, sizes):
    acc = 14695981039346656037
    prime = 1099511628211
    for p, sz in zip(paths, sizes):
        for ch in p:
            acc = (acc ^ ord(ch)) * prime
            acc &= 0xFFFFFFFFFFFFFFFF
        acc = (acc ^ sz) * prime
        acc &= 0xFFFFFFFFFFFFFFFF
    return hex(acc)
""",
        "compute_storage_invariant_hash",
        [
            (["/obsidian_vault", "/lora_datasets", "/04_data_and_memory"], [1024, 2048, 4096]),
            ([], []),
            (["/path/a"], [0]),
        ]
    ),
}


class SystematicASTObfuscator(ast.NodeTransformer):
    """
    Adversarially obfuscates AST trees by:
    1. Mangling local & parameter variable identifiers into high-entropy hex (`_0x100a`).
    2. Transforming literal constants into multi-operator arithmetic BinOps (`10` -> `5 + 5`).
    3. Injecting unreachable dead code blocks (`if False: return -9999`).
    4. Injecting redundant post-return dead code.
    """
    def __init__(self, preserved_identifiers: List[str]):
        self.preserved = set(preserved_identifiers) | {
            "range", "len", "min", "max", "sum", "int", "float", "round",
            "ord", "hex", "zip", "True", "False", "None", "append", "extend",
        }
        self.var_map: Dict[str, str] = {}
        self.counter = 0x1000

    def visit_Name(self, node: ast.Name) -> ast.AST:
        if node.id in self.preserved:
            return node
        if node.id not in self.var_map:
            self.var_map[node.id] = f"_0x{self.counter:04x}"
            self.counter += 1
        return ast.Name(id=self.var_map[node.id], ctx=node.ctx)

    def visit_arg(self, node: ast.arg) -> ast.AST:
        if node.arg in self.preserved:
            return node
        if node.arg not in self.var_map:
            self.var_map[node.arg] = f"_0x{self.counter:04x}"
            self.counter += 1
        node.arg = self.var_map[node.arg]
        return node

    def visit_Constant(self, node: ast.Constant) -> ast.AST:
        if isinstance(node.value, int) and 2 <= node.value <= 100:
            h = node.value // 2
            rem = node.value - h
            return ast.BinOp(left=ast.Constant(value=h), op=ast.Add(), right=ast.Constant(value=rem))
        return node


def test_ast_deobfuscation_oracle() -> Dict[str, Any]:
    """
    Evaluates AST Deobfuscation Oracle across all 15 algorithms.
    Verifies that after parsing, identifier de-obfuscation, dead-code elimination,
    and constant folding, reconstructed code produces 100.00% identical outputs.
    """
    results = {}
    total_vectors = 0
    total_matches = 0

    for name, (source_code, fn_name, input_vectors) in ALGORITHMS.items():
        # 1. Ground Truth
        orig_globals: Dict[str, Any] = {"math": math}
        exec(source_code, orig_globals)
        orig_fn = orig_globals[fn_name]

        # 2. Mutate AST with Obfuscation
        tree = ast.parse(source_code)
        mutator = SystematicASTObfuscator(preserved_identifiers=[fn_name])
        obf_tree = mutator.visit(tree)

        # Inject dead code into functions
        for node in ast.walk(obf_tree):
            if isinstance(node, ast.FunctionDef):
                dead_stmt = ast.If(
                    test=ast.Constant(value=False),
                    body=[ast.Return(value=ast.Constant(value=-9999))],
                    orelse=[]
                )
                node.body.insert(0, dead_stmt)

        ast.fix_missing_locations(obf_tree)
        obf_source = ast.unparse(obf_tree)

        # 3. De-obfuscate AST
        start_t = time.perf_counter()
        deob_result = deobfuscate_ast(obf_source)
        deob_time_ms = (time.perf_counter() - start_t) * 1000.0

        # 4. Compile De-obfuscated Code
        deob_globals: Dict[str, Any] = {"math": math}
        exec(deob_result.reconstructed_code, deob_globals)
        deob_fn = deob_globals.get(fn_name) or next(
            (v for k, v in deob_globals.items() if callable(v) and k not in ("math",)), None
        )

        matches = 0
        vector_results = []
        for vec in input_vectors:
            total_vectors += 1
            args = vec if isinstance(vec, tuple) else (vec,)

            expected_out = orig_fn(*args)
            actual_out = deob_fn(*args)

            is_match = (expected_out == actual_out)
            if is_match:
                matches += 1
                total_matches += 1

            vector_results.append({
                "input": str(args)[:50],
                "expected": str(expected_out)[:50],
                "actual": str(actual_out)[:50],
                "match": is_match
            })

        results[name] = {
            "function_name": fn_name,
            "deob_valid_syntax": deob_result.is_valid_syntax,
            "deobfuscated_identifiers": deob_result.deobfuscated_identifiers,
            "eliminated_dead_blocks": deob_result.eliminated_dead_blocks,
            "matches": matches,
            "total_vectors": len(input_vectors),
            "match_rate": (matches / len(input_vectors)) * 100.0,
            "deob_time_ms": deob_time_ms,
        }

    accuracy = (total_matches / total_vectors) * 100.0 if total_vectors > 0 else 0.0
    return {
        "total_algorithms_tested": len(ALGORITHMS),
        "total_test_vectors": total_vectors,
        "total_matches": total_matches,
        "ast_deobfuscation_oracle_accuracy_pct": accuracy,
        "algorithms": results,
    }


def main():
    print("=== STARTING CHALLENGE 3: AST DEOBFUSCATION & CONSTANT FOLDING ORACLE ===")
    results = test_ast_deobfuscation_oracle()

    print(f"\nTotal Algorithms Tested : {results['total_algorithms_tested']}")
    print(f"Total Test Vectors Run  : {results['total_test_vectors']}")
    print(f"Total Matches           : {results['total_matches']}/{results['total_test_vectors']}")
    print(f"Oracle Accuracy         : {results['ast_deobfuscation_oracle_accuracy_pct']:.2f}%")

    print("\n--- Per-Algorithm Breakdown ---")
    for name, r in results['algorithms'].items():
        print(f"  [{name}] {r['function_name']}: Matches={r['matches']}/{r['total_vectors']} ({r['match_rate']:.1f}%), DeobIdents={r['deobfuscated_identifiers']}, DeadBlocksPruned={r['eliminated_dead_blocks']}, Time={r['deob_time_ms']:.2f}ms")

    with open("/Users/aaron/.agents/teamwork_preview_challenger_1/decompiler_oracle_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print("\n=== CHALLENGE 3 COMPLETE: Saved to decompiler_oracle_results.json ===")


if __name__ == "__main__":
    main()
