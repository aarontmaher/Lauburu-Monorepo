#!/usr/bin/env python3
"""
Exhaustive Line-by-Line AST & Pattern Code Crawler
Subsystem: 06_scripts_and_tooling/automation
Governed by: Rule #0 & Rule #1 (Zero-Mock & Truth Verification Rule)

Cuts across 01_apps, 00_core_infrastructure, 03_biometrics_and_telemetry,
08_business_and_commerce to detect:
1. Mock data / simulated biometric signals / synthetic telemetry
2. Fake timestamps, synthetic arrays in production paths
3. Hallucinated or stubbed-out methods (pass, NotImplementedError in live features)
4. Non-functional checkout or payment endpoints
"""
import os
import re
import ast
import json
import time
from pathlib import Path
from typing import Dict, List, Any

REPO_ROOT = Path("/Volumes/Lauburu-Monorepo")

TARGET_DIRS = [
    REPO_ROOT / "00_core_infrastructure",
    REPO_ROOT / "01_apps",
    REPO_ROOT / "03_biometrics_and_telemetry",
    REPO_ROOT / "08_business_and_commerce"
]

EXCLUDE_DIRS = {
    "node_modules", ".git", ".venv", "venv", "voice_venv", "site-packages", "__pycache__",
    ".idea", ".vscode", "dist", "build", ".dart_tool"
}

# Suspicious patterns indicating fake/mock telemetry in production
SUSPICIOUS_PATTERNS = [
    (re.compile(r'\b(faker|unittest\.mock|MagicMock)\b', re.IGNORECASE), "MOCK_LIBRARY_IMPORT", "CRITICAL"),
    (re.compile(r'\b(simulated_ecg|synthetic_hr|fake_telemetry|mock_sensor)\b', re.IGNORECASE), "SIMULATED_SENSOR_VAR", "CRITICAL"),
    (re.compile(r'np\.random\.(normal|rand|randn)\s*\(.*(ecg|heart_rate|hr|bpm|pressure)', re.IGNORECASE), "SYNTHETIC_BIOMETRIC_NOISE", "CRITICAL"),
    (re.compile(r'random\.(randint|uniform)\s*\(.*(60,\s*100|bpm|heart_rate)', re.IGNORECASE), "FAKE_BPM_GENERATION", "CRITICAL"),
    (re.compile(r'sk_test_[0-9a-zA-Z]{24,}', re.IGNORECASE), "HARDCODED_TEST_STRIPE_KEY", "WARNING"),
    (re.compile(r'#\s*TODO:?\s*(implement|finish|mock|fake)', re.IGNORECASE), "UNIMPLEMENTED_FEATURE_TODO", "MEDIUM"),
    (re.compile(r'\bdef\s+[a-zA-Z0-9_]+\([^)]*\):\s*(?:"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\')?\s*(?:pass|\.\.\.|raise NotImplementedError)', re.MULTILINE), "EMPTY_METHOD_STUB", "HIGH")
]

class ZeroMockCrawler:
    def __init__(self):
        self.scanned_files = 0
        self.scanned_lines = 0
        self.findings: List[Dict[str, Any]] = []

    def crawl(self):
        start_t = time.time()
        for t_dir in TARGET_DIRS:
            if not t_dir.exists():
                continue
            for root, dirs, files in os.walk(t_dir):
                dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith(".")]
                for f in files:
                    if f.endswith(('.py', '.dart', '.ts', '.tsx', '.js', '.sh', '.json')):
                        self.scan_file(Path(root) / f)

        elapsed = time.time() - start_t
        return {
            "scanned_files": self.scanned_files,
            "scanned_lines": self.scanned_lines,
            "elapsed_seconds": round(elapsed, 2),
            "total_findings": len(self.findings),
            "findings_by_severity": self.aggregate_severities(),
            "findings": self.findings
        }

    def scan_file(self, file_path: Path):
        self.scanned_files += 1
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return

        lines = content.splitlines()
        self.scanned_lines += len(lines)
        rel_path = str(file_path.relative_to(REPO_ROOT))

        # Check if this is explicitly a test/mock directory or benchmark
        is_test_or_benchmark = any(k in rel_path.lower() for k in ["test", "benchmark", "sandbox", "arena"])

        # Check regex patterns
        for pattern, finding_type, severity in SUSPICIOUS_PATTERNS:
            for i, line in enumerate(lines, 1):
                # Ignore test imports if inside test files, unless flagged
                if is_test_or_benchmark and finding_type in ["MOCK_LIBRARY_IMPORT"]:
                    continue
                match = pattern.search(line)
                if match:
                    self.findings.append({
                        "file": rel_path,
                        "line": i,
                        "type": finding_type,
                        "severity": severity,
                        "snippet": line.strip()[:140],
                        "in_test_or_benchmark": is_test_or_benchmark
                    })

        # If python, perform AST analysis for empty stubs in production
        if file_path.suffix == ".py" and not is_test_or_benchmark:
            self.ast_inspect(file_path, content, rel_path)

    def ast_inspect(self, file_path: Path, content: str, rel_path: str):
        try:
            tree = ast.parse(content, filename=str(file_path))
        except SyntaxError:
            return

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Check for empty body (only docstring and pass/...)
                body = node.body
                # Skip docstring if first statement
                if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
                    body = body[1:]
                if len(body) == 1:
                    stmt = body[0]
                    if isinstance(stmt, ast.Pass):
                        self.findings.append({
                            "file": rel_path,
                            "line": node.lineno,
                            "type": "STUBBED_PASS_FUNCTION",
                            "severity": "HIGH",
                            "snippet": f"def {node.name}(): pass",
                            "in_test_or_benchmark": False
                        })
                    elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and stmt.value.value is Ellipsis:
                        self.findings.append({
                            "file": rel_path,
                            "line": node.lineno,
                            "type": "STUBBED_ELLIPSIS_FUNCTION",
                            "severity": "HIGH",
                            "snippet": f"def {node.name}(): ...",
                            "in_test_or_benchmark": False
                        })

    def aggregate_severities(self) -> Dict[str, int]:
        counts = {"CRITICAL": 0, "HIGH": 0, "WARNING": 0, "MEDIUM": 0}
        for f in self.findings:
            sev = f.get("severity", "MEDIUM")
            counts[sev] = counts.get(sev, 0) + 1
        return counts

if __name__ == "__main__":
    crawler = ZeroMockCrawler()
    report = crawler.crawl()
    out_file = REPO_ROOT / "04_data_and_memory/data/zero_mock_ast_audit_report.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w") as f:
        json.dump(report, f, indent=2)
    print(f"Scanned {report['scanned_files']} files ({report['scanned_lines']} lines) in {report['elapsed_seconds']}s.")
    print(f"Total Findings: {report['total_findings']} | Severities: {report['findings_by_severity']}")
    print(f"Report written to {out_file}")
