#!/usr/bin/env python3
"""
================================================================================
Voice Coding App: AST Scope Slicing & Region Backspace Engine
================================================================================
Subsystem: 01_apps/automotive/voice_ast_backend.py
Version: 2.0.0-REGION-BACKSPACE-AST
Lauburu Mesh Ecosystem — 2026

Empowers hands-free in-vehicle voice pair-programming (Android Auto) with:
1. Region-Aware Voice Backspace: "backspace region", "delete block", "delete function <name>".
2. AST Scope Resolution: Parses Python / Kotlin / TypeScript syntax trees into named scopes.
3. Multi-Level Undo & Scope Rewind Stack: Restores previous AST snapshots instantly.
4. Voice Directive Router: Maps natural voice speech into structured code manipulations.
================================================================================
"""

import os
import sys
import ast
import json
import time
import re
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")


class RegionBackspaceEngine:
    """
    AST-aware region backspace and scope rewind engine for hands-free voice coding.
    """

    def __init__(self, initial_code: str = ""):
        self.current_code = initial_code
        self.history_stack: List[str] = [initial_code] if initial_code else []
        self.redo_stack: List[str] = []

    def load_code(self, code_str: str):
        self.current_code = code_str
        self.history_stack.append(code_str)
        self.redo_stack.clear()

    def parse_scopes(self) -> List[Dict[str, Any]]:
        """Parses AST functions, classes, and statement blocks with line ranges."""
        if not self.current_code.strip():
            return []

        try:
            tree = ast.parse(self.current_code)
        except SyntaxError:
            # Fallback to line-based heuristic if code is incomplete
            return self._line_based_scope_heuristic()

        scopes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                scopes.append({
                    "type": "function",
                    "name": node.name,
                    "start_line": node.lineno,
                    "end_line": getattr(node, "end_lineno", node.lineno + 5),
                    "header": f"def {node.name}(...)"
                })
            elif isinstance(node, ast.ClassDef):
                scopes.append({
                    "type": "class",
                    "name": node.name,
                    "start_line": node.lineno,
                    "end_line": getattr(node, "end_lineno", node.lineno + 10),
                    "header": f"class {node.name}:"
                })
            elif isinstance(node, (ast.If, ast.For, ast.While, ast.With)):
                scopes.append({
                    "type": "block",
                    "name": node.__class__.__name__.lower(),
                    "start_line": node.lineno,
                    "end_line": getattr(node, "end_lineno", node.lineno + 3),
                    "header": f"{node.__class__.__name__.lower()} statement"
                })

        return sorted(scopes, key=lambda x: x["start_line"])

    def _line_based_scope_heuristic(self) -> List[Dict[str, Any]]:
        lines = self.current_code.splitlines()
        scopes = []
        for idx, line in enumerate(lines, start=1):
            if line.strip().startswith("def "):
                m = re.search(r"def\s+([a-zA-Z0-9_]+)", line)
                name = m.group(1) if m else f"func_{idx}"
                scopes.append({"type": "function", "name": name, "start_line": idx, "end_line": idx + 5})
        return scopes

    def execute_voice_backspace(self, voice_command: str) -> Dict[str, Any]:
        """
        Interprets voice directives like:
        - "backspace region" -> deletes innermost active scope block
        - "delete function <name>" -> deletes named function
        - "backspace line <N>" / "delete line <N>" -> deletes line N
        - "undo last edit" / "rewind scope" -> pops history stack
        """
        cmd = voice_command.strip().lower()
        lines = self.current_code.splitlines()

        # 1. Undo command
        if "undo" in cmd or "rewind" in cmd:
            if len(self.history_stack) > 1:
                self.redo_stack.append(self.history_stack.pop())
                self.current_code = self.history_stack[-1]
                return {
                    "action": "UNDO_LAST_ACTION",
                    "status": "SUCCESS",
                    "message": "Rewound code to previous AST snapshot.",
                    "code": self.current_code
                }
            return {
                "action": "UNDO_LAST_ACTION",
                "status": "NOOP",
                "message": "History stack is empty; at initial snapshot.",
                "code": self.current_code
            }

        # 2. Delete function <name>
        match_func = re.search(r"(?:delete|backspace|remove)\s+(?:function|def)\s+([a-zA-Z0-9_]+)", cmd)
        if match_func:
            target_name = match_func.group(1)
            scopes = self.parse_scopes()
            matching = [s for s in scopes if s.get("type") == "function" and s.get("name") == target_name]
            if matching:
                scope = matching[0]
                start = scope["start_line"] - 1
                end = scope["end_line"]
                new_lines = lines[:start] + lines[end:]
                new_code = "\n".join(new_lines)
                self.load_code(new_code)
                return {
                    "action": "DELETE_FUNCTION_SCOPE",
                    "status": "SUCCESS",
                    "target": target_name,
                    "deleted_lines": f"{start+1}..{end}",
                    "code": self.current_code
                }
            return {
                "action": "DELETE_FUNCTION_SCOPE",
                "status": "NOT_FOUND",
                "message": f"Function '{target_name}' not found in AST."
            }

        # 3. Delete specific line
        match_line = re.search(r"(?:delete|backspace|remove)\s+line\s+(\d+)", cmd)
        if match_line:
            line_no = int(match_line.group(1))
            if 1 <= line_no <= len(lines):
                deleted_text = lines[line_no - 1]
                new_lines = lines[:line_no - 1] + lines[line_no:]
                new_code = "\n".join(new_lines)
                self.load_code(new_code)
                return {
                    "action": "DELETE_LINE",
                    "status": "SUCCESS",
                    "line_number": line_no,
                    "deleted_content": deleted_text.strip(),
                    "code": self.current_code
                }

        # 4. General "backspace region" / "delete block" -> delete last/innermost scope
        if "backspace region" in cmd or "delete block" in cmd or "clear scope" in cmd:
            scopes = self.parse_scopes()
            if scopes:
                # Target last scope
                last_scope = scopes[-1]
                start = last_scope["start_line"] - 1
                end = last_scope["end_line"]
                new_lines = lines[:start] + lines[end:]
                new_code = "\n".join(new_lines)
                self.load_code(new_code)
                return {
                    "action": "REGION_BACKSPACE",
                    "status": "SUCCESS",
                    "target_scope": last_scope["name"],
                    "deleted_lines": f"{start+1}..{end}",
                    "code": self.current_code
                }

        return {
            "action": "UNKNOWN_VOICE_DIRECTIVE",
            "status": "UNHANDLED",
            "message": f"Could not map voice directive '{voice_command}' to AST action."
        }


if __name__ == "__main__":
    sample_code = (
        "def compute_movesense_hr(ecg_signal):\n"
        "    hr = len(ecg_signal) * 60.0 / 512.0\n"
        "    return {'hr': hr}\n"
        "\n"
        "def deprecated_stub():\n"
        "    pass\n"
    )

    engine = RegionBackspaceEngine(sample_code)
    print("=== Region Backspace Engine Demo ===")
    print("Initial Code:")
    print(engine.current_code)
    print("\nScopes Detected:", json.dumps(engine.parse_scopes(), indent=2))

    res = engine.execute_voice_backspace("delete function deprecated_stub")
    print("\nAction Result:")
    print(json.dumps(res, indent=2))
    print("\nUpdated Code:")
    print(engine.current_code)
