"""
AST Compiler Gate & Rule #0 Zero-Mock Validator.

Ensures all code blocks in training records are:
1. Syntactically valid Python (via ast.parse)
2. 100% free of synthetic mock arrays, fake data stubs, or simulation placeholders
3. Free of empty function/class stubs (e.g. def func(): pass / ...)

Quarantines non-compliant records to quarantine_anomalies.jsonl.
"""

from __future__ import annotations

import ast
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


class ASTCompilerGate:
    """
    Validates Python code snippets and training records against syntax errors
    and Rule #0 Zero-Mock violations.
    """

    CODE_BLOCK_REGEX = re.compile(r"```(?:python|py)?\s*\n(.*?)\n```", re.DOTALL)

    # Prohibited mock/simulation tokens and anti-patterns
    MOCK_PATTERNS = [
        re.compile(r"\bmock_data\b", re.IGNORECASE),
        re.compile(r"\bfrom unittest\.mock import\b"),
        re.compile(r"\bimport unittest\.mock\b"),
        re.compile(r"\bMagicMock\b"),
        re.compile(r"\bfake_ecg\s*=\s*\[", re.IGNORECASE),
        re.compile(r"\bsimulate_telemetry\b", re.IGNORECASE),
        re.compile(r"\bdummy_payload\b", re.IGNORECASE),
        re.compile(r"\bpytest\.mock\b"),
        re.compile(r"\bcreate_autospec\b"),
        re.compile(r"\bfake_tensor\b", re.IGNORECASE),
    ]

    DEFAULT_QUARANTINE_PATH = "/Users/aaron/DFS_UNIFIED/lora_datasets/quarantine_anomalies.jsonl"

    @classmethod
    def _is_empty_body(cls, body: List[ast.stmt]) -> bool:
        """
        Checks if a function or class body contains only pass, docstring, or ellipsis.
        """
        if not body:
            return True

        # Filter out docstrings (Expr with Constant string)
        meaningful_stmts = []
        for stmt in body:
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
                if isinstance(stmt.value.value, str):
                    continue  # Docstring
                if stmt.value.value is ...:
                    continue  # Ellipsis
            elif isinstance(stmt, ast.Pass):
                continue  # Pass
            meaningful_stmts.append(stmt)

        return len(meaningful_stmts) == 0

    @classmethod
    def validate_code_snippet(cls, code: str) -> Tuple[bool, str]:
        """
        Validates an extracted Python code snippet.
        Returns:
            (is_valid: bool, reason: str)
        """
        code_clean = code.strip()
        if not code_clean:
            return True, "EMPTY_CODE_SNIPPET"

        # 1. AST Syntax Check
        try:
            tree = ast.parse(code_clean)
        except SyntaxError as e:
            # Check if this might be a diff snippet (lines starting with + or -)
            lines = code_clean.splitlines()
            if any(l.startswith("+") or l.startswith("-") for l in lines):
                # Attempt to parse stripped diff
                stripped = "\n".join(
                    l[1:] if (l.startswith("+") or l.startswith(" ")) else l
                    for l in lines
                    if not l.startswith("-")
                )
                try:
                    tree = ast.parse(stripped)
                except SyntaxError:
                    return False, f"SYNTAX_ERROR: Line {e.lineno}: {e.msg}"
            else:
                return False, f"SYNTAX_ERROR: Line {e.lineno}: {e.msg}"

        # 2. Rule #0 Mock & Simulation Check
        for pattern in cls.MOCK_PATTERNS:
            match = pattern.search(code_clean)
            if match:
                return False, f"RULE_0_MOCK_DETECTED: Matched pattern '{pattern.pattern}' on '{match.group(0)}'"

        # 3. Empty Stub Check
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if cls._is_empty_body(node.body):
                    return False, f"RULE_0_EMPTY_STUB: Function '{node.name}' contains only pass/ellipsis"
            elif isinstance(node, ast.ClassDef):
                if cls._is_empty_body(node.body):
                    # Classes subclassing Exception or Protocol might legitimately be empty,
                    # but pure dummy classes are flagged
                    base_names = [getattr(b, "id", "") for b in node.bases if isinstance(b, ast.Name)]
                    if not any("Exception" in b or "Error" in b or "Protocol" in b for b in base_names):
                        return False, f"RULE_0_EMPTY_STUB: Class '{node.name}' contains empty pass body"

        return True, "VALID_AST"

    @classmethod
    def validate_record(cls, record: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Scans all text in a record for Python code blocks and validates each one.
        Returns:
            (is_valid: bool, status_reason: str)
        """
        # Collect all string values from record
        text_parts: List[str] = []
        for k, v in record.items():
            if isinstance(v, str):
                text_parts.append(v)
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        for sub_v in item.values():
                            if isinstance(sub_v, str):
                                text_parts.append(sub_v)
                    elif isinstance(item, str):
                        text_parts.append(item)

        full_text = "\n".join(text_parts)
        code_blocks = cls.CODE_BLOCK_REGEX.findall(full_text)

        if not code_blocks:
            # Check if any field is directly pure python code without markdown tags
            for k in ("solution", "code", "heal_action", "patch"):
                if k in record and isinstance(record[k], str) and record[k].strip():
                    valid, reason = cls.validate_code_snippet(record[k])
                    if not valid:
                        return False, f"Field '{k}': {reason}"

            return True, "NO_CODE_BLOCKS"

        for idx, block in enumerate(code_blocks):
            valid, reason = cls.validate_code_snippet(block)
            if not valid:
                return False, f"CodeBlock #{idx + 1}: {reason}"

        return True, "ALL_BLOCKS_VALID"

    @classmethod
    def filter_and_quarantine(
        cls,
        records: List[Dict[str, Any]],
        quarantine_path: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Filters a list of records through the AST compiler gate.
        Compliant records are returned as valid.
        Failing records are quarantined to disk and returned as quarantined list.
        """
        valid_records: List[Dict[str, Any]] = []
        quarantined_records: List[Dict[str, Any]] = []

        target_path = quarantine_path or cls.DEFAULT_QUARANTINE_PATH

        for r in records:
            is_valid, reason = cls.validate_record(r)
            if is_valid:
                valid_records.append(r)
            else:
                q_item = dict(r)
                q_item["_quarantine_reason"] = reason
                quarantined_records.append(q_item)

        if quarantined_records:
            try:
                os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
                with open(target_path, "a", encoding="utf-8") as f:
                    for item in quarantined_records:
                        f.write(json.dumps(item) + "\n")
                logger.info(f"Quarantined {len(quarantined_records)} anomalous records to {target_path}")
            except Exception as e:
                logger.warning(f"Failed to write to quarantine file {target_path}: {e}")

        return valid_records, quarantined_records
