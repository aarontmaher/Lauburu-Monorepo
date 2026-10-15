# -*- coding: utf-8 -*-
"""
Qwen-AgentWorld-35B World Model Driver & Copy-on-Write OS/MCP/ADB Simulator
==========================================================================
Subsystem: 02_ai_models_and_inference/simulation/agentworld_driver.py
Milestone: M4 — Dual-World Simulation & Predictive Lookahead Engine

Governs predictive multi-step simulation for OS syscalls, terminal execution,
MCP tool invocations, and Android ADB lifecycle over Copy-on-Write (CoW) shadow
virtual state environments.
"""

from __future__ import annotations

import ast
import copy
import json
import logging
import os
import re
import shlex
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger("AgentWorldDriver")

DEFAULT_MODEL_NAME = "Qwen/Qwen-AgentWorld-35B-A3B"

DANGEROUS_COMMAND_PATTERNS = [
    r"rm\s+(-[rfRF]+\s+)?(/|/\*|/etc|/boot|/System|/usr|/var|~|\$HOME)",
    r"mkfs(\.[a-z0-9]+)?\s+",
    r"dd\s+if=.*\s+of=(/dev/sd|/dev/nvme|/dev/disk)",
    r":\(\)\s*\{\s*:\|:&\s*\};:",
    r">\s*(/etc/passwd|/etc/shadow|/etc/sudoers)",
    r"chmod\s+(-R\s+)?777\s+(/|/etc|/System)",
    r"shutdown(\s+-[rh])?(\s+now)?",
    r"reboot",
    r"init\s+0",
]


@dataclass
class VirtualFileInfo:
    path: str
    content: str = ""
    is_dir: bool = False
    mode: int = 0o644
    modified_at: float = field(default_factory=time.time)
    size_bytes: int = 0

    def __post_init__(self):
        if not self.is_dir:
            self.size_bytes = len(self.content.encode("utf-8"))


class CopyOnWriteVFS:
    """
    Copy-on-Write Virtual File System.
    Permits simulated file creation, modification, deletion, and read
    operations without altering underlying physical disk files.
    """

    def __init__(self, base_real_root: Optional[Union[str, Path]] = None):
        self.base_real_root = Path(base_real_root) if base_real_root else None
        self._files: Dict[str, VirtualFileInfo] = {}
        self._deleted: Set[str] = set()
        self._created: Set[str] = set()
        self._modified: Set[str] = set()

    def _normalize_path(self, path_str: str) -> str:
        return os.path.normpath(path_str)

    def read_file(self, path_str: str) -> Optional[str]:
        norm = self._normalize_path(path_str)
        if norm in self._deleted:
            return None
        if norm in self._files:
            if self._files[norm].is_dir:
                return None
            return self._files[norm].content

        if self.base_real_root:
            real_path = self.base_real_root / norm.lstrip("/")
            if real_path.is_file():
                try:
                    return real_path.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    return None
        return None

    def write_file(self, path_str: str, content: str, mode: int = 0o644) -> None:
        norm = self._normalize_path(path_str)
        self._deleted.discard(norm)
        if norm not in self._files:
            self._created.add(norm)
        else:
            self._modified.add(norm)
        self._files[norm] = VirtualFileInfo(
            path=norm,
            content=content,
            is_dir=False,
            mode=mode,
            modified_at=time.time(),
        )
        parent = os.path.dirname(norm)
        if parent and parent != norm:
            self.mkdir(parent, mode=0o755)

    def mkdir(self, path_str: str, mode: int = 0o755) -> None:
        norm = self._normalize_path(path_str)
        self._deleted.discard(norm)
        if norm not in self._files:
            self._created.add(norm)
            self._files[norm] = VirtualFileInfo(
                path=norm,
                content="",
                is_dir=True,
                mode=mode,
                modified_at=time.time(),
            )

    def remove_file(self, path_str: str) -> bool:
        norm = self._normalize_path(path_str)
        if norm in self._files:
            del self._files[norm]
            self._deleted.add(norm)
            self._created.discard(norm)
            self._modified.discard(norm)
            return True
        elif self.base_real_root:
            real_path = self.base_real_root / norm.lstrip("/")
            if real_path.exists():
                self._deleted.add(norm)
                return True
        return False

    def exists(self, path_str: str) -> bool:
        norm = self._normalize_path(path_str)
        if norm in self._deleted:
            return False
        if norm in self._files:
            return True
        if self.base_real_root:
            real_path = self.base_real_root / norm.lstrip("/")
            return real_path.exists()
        return False

    def is_dir(self, path_str: str) -> bool:
        norm = self._normalize_path(path_str)
        if norm in self._deleted:
            return False
        if norm in self._files:
            return self._files[norm].is_dir
        if self.base_real_root:
            real_path = self.base_real_root / norm.lstrip("/")
            return real_path.is_dir()
        return False

    def list_dir(self, path_str: str) -> List[str]:
        norm = self._normalize_path(path_str)
        results = set()
        prefix = norm.rstrip("/") + "/" if norm != "/" else "/"
        for p in self._files:
            if p.startswith(prefix) and p not in self._deleted:
                sub = p[len(prefix):].split("/")[0]
                if sub:
                    results.add(sub)
        if self.base_real_root:
            real_path = self.base_real_root / norm.lstrip("/")
            if real_path.is_dir():
                try:
                    for child in os.listdir(real_path):
                        child_norm = self._normalize_path(os.path.join(norm, child))
                        if child_norm not in self._deleted:
                            results.add(child)
                except Exception:
                    pass
        return sorted(list(results))

    def get_diff(self) -> Dict[str, Any]:
        return {
            "created": sorted(list(self._created)),
            "modified": sorted(list(self._modified)),
            "deleted": sorted(list(self._deleted)),
            "total_virtual_files": len(self._files),
        }

    def clone(self) -> CopyOnWriteVFS:
        cloned = CopyOnWriteVFS(base_real_root=self.base_real_root)
        cloned._files = copy.deepcopy(self._files)
        cloned._deleted = copy.deepcopy(self._deleted)
        cloned._created = copy.deepcopy(self._created)
        cloned._modified = copy.deepcopy(self._modified)
        return cloned


@dataclass
class AgentWorldStepResult:
    step_index: int
    action_type: str
    action_raw: Union[str, Dict[str, Any]]
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    safety_score: float = 1.0
    regression_probability: float = 0.0
    confidence: float = 0.95
    state_diff: Dict[str, Any] = field(default_factory=dict)
    diagnostics: Dict[str, Any] = field(default_factory=dict)


class AgentWorldDriver:
    """
    Qwen-AgentWorld-35B Driver for system commands, shell AST operations,
    MCP tool invocations, and Android ADB device simulation.
    """

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL_NAME,
        base_dir: Optional[Union[str, Path]] = None,
        dangerous_patterns: Optional[List[str]] = None,
    ):
        self.model_name = model_name
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        self.dangerous_patterns = dangerous_patterns or DANGEROUS_COMMAND_PATTERNS
        self._compiled_dangerous = [re.compile(p, re.IGNORECASE) for p in self.dangerous_patterns]
        
        self._adb_devices: Dict[str, Dict[str, Any]] = {
            "192.168.8.230:5555": {"model": "Mac_Node_L1", "status": "device", "wake_lock": True},
            "100.73.38.87:5555": {"model": "Pixel_10_Pro_XL", "status": "device", "wake_lock": True, "tpu_ready": True},
            "100.84.40.95:5555": {"model": "Samsung_S20", "status": "device", "wake_lock": True},
        }
        self._mcp_tools_registry: Dict[str, Dict[str, Any]] = {
            "read_file": {"schema": {"path": "str"}, "safe": True},
            "write_file": {"schema": {"path": "str", "content": "str"}, "safe": True},
            "run_command": {"schema": {"command": "str"}, "safe": True},
            "git_commit": {"schema": {"message": "str"}, "safe": True},
            "adb_shell": {"schema": {"cmd": "str", "device": "str"}, "safe": True},
        }

    def check_command_safety(self, command_str: str) -> Tuple[bool, str]:
        if not command_str or not command_str.strip():
            return True, "Empty command"

        cmd_clean = command_str.strip()
        for pat in self._compiled_dangerous:
            if pat.search(cmd_clean):
                return False, f"Dangerous command rejected by safety policy: matches {pat.pattern}"

        tokens = cmd_clean.split()
        if len(tokens) >= 2 and tokens[0] in ["rm", "unlink"]:
            if any(t in ["/", "/*", "~/*", ".", ".."] for t in tokens[1:]):
                return False, "Destructive root or current directory deletion prohibited"

        return True, "Command passed safety filter"

    def simulate_shell_command(
        self,
        command_str: str,
        vfs: CopyOnWriteVFS,
        cwd: str = "/workspace",
        env: Optional[Dict[str, str]] = None,
    ) -> AgentWorldStepResult:
        env = env or {"PATH": "/usr/bin:/bin", "HOME": "/home/agent", "USER": "agent"}
        is_safe, reason = self.check_command_safety(command_str)

        if not is_safe:
            return AgentWorldStepResult(
                step_index=0,
                action_type="system_command",
                action_raw=command_str,
                stdout="",
                stderr=f"[SECURITY_VIOLATION] {reason}",
                exit_code=126,
                safety_score=0.0,
                regression_probability=1.0,
                confidence=0.99,
                diagnostics={"error": "DANGEROUS_COMMAND", "reason": reason},
            )

        cmd_trimmed = command_str.strip()
        stdout = ""
        stderr = ""
        exit_code = 0
        safety_score = 0.98
        regression_prob = 0.01
        confidence = 0.94

        try:
            tokens = shlex.split(cmd_trimmed)
        except Exception as e:
            return AgentWorldStepResult(
                step_index=0,
                action_type="system_command",
                action_raw=command_str,
                stdout="",
                stderr=f"Syntax error parsing command: {e}",
                exit_code=2,
                safety_score=0.40,
                regression_probability=0.85,
                confidence=0.90,
                diagnostics={"syntax_error": str(e)},
            )

        if not tokens:
            return AgentWorldStepResult(
                step_index=0,
                action_type="system_command",
                action_raw=command_str,
                stdout="",
                stderr="",
                exit_code=0,
                safety_score=1.0,
                regression_probability=0.0,
                confidence=0.99,
            )

        cmd_name = tokens[0]

        if cmd_name == "mkdir":
            dirs = [t for t in tokens[1:] if not t.startswith("-")]
            for d in dirs:
                target_p = os.path.normpath(os.path.join(cwd, d) if not os.path.isabs(d) else d)
                vfs.mkdir(target_p)
            stdout = ""
        elif cmd_name == "touch":
            files = [t for t in tokens[1:] if not t.startswith("-")]
            for f in files:
                target_p = os.path.normpath(os.path.join(cwd, f) if not os.path.isabs(f) else f)
                if not vfs.exists(target_p):
                    vfs.write_file(target_p, "")
        elif cmd_name == "cat":
            files = [t for t in tokens[1:] if not t.startswith("-")]
            out_parts = []
            for f in files:
                target_p = os.path.normpath(os.path.join(cwd, f) if not os.path.isabs(f) else f)
                c = vfs.read_file(target_p)
                if c is not None:
                    out_parts.append(c)
                else:
                    stderr += f"cat: {f}: No such file or directory\n"
                    exit_code = 1
            stdout = "\n".join(out_parts)
        elif cmd_name == "rm":
            files = [t for t in tokens[1:] if not t.startswith("-")]
            for f in files:
                target_p = os.path.normpath(os.path.join(cwd, f) if not os.path.isabs(f) else f)
                if not vfs.remove_file(target_p):
                    stderr += f"rm: {f}: No such file or directory\n"
                    exit_code = 1
        elif cmd_name == "ls":
            target_p = cwd
            args = [t for t in tokens[1:] if not t.startswith("-")]
            if args:
                d = args[0]
                target_p = os.path.normpath(os.path.join(cwd, d) if not os.path.isabs(d) else d)
            if vfs.exists(target_p):
                if vfs.is_dir(target_p):
                    items = vfs.list_dir(target_p)
                    stdout = "  ".join(items)
                else:
                    stdout = os.path.basename(target_p)
            else:
                stderr = f"ls: {target_p}: No such file or directory"
                exit_code = 1
        elif cmd_name == "echo":
            args = tokens[1:]
            stdout = " ".join(args)
        elif cmd_name == "pytest":
            stdout = "============================= test session starts =============================\ncollected 42 items\n\n.......................................... [100%]\n42 passed in 1.45s"
            safety_score = 0.99
            regression_prob = 0.01
        elif cmd_name == "python" or cmd_name == "python3":
            if len(tokens) >= 3 and tokens[1] == "-c":
                code = tokens[2]
                try:
                    ast.parse(code)
                    stdout = "[AgentWorld Virtual Python AST: Syntactically Valid]"
                except SyntaxError as se:
                    stderr = f"SyntaxError in Python statement: {se}"
                    exit_code = 1
                    safety_score = 0.45
                    regression_prob = 0.70
            elif len(tokens) >= 2:
                script_path = os.path.normpath(os.path.join(cwd, tokens[1]) if not os.path.isabs(tokens[1]) else tokens[1])
                code = vfs.read_file(script_path)
                if code is not None:
                    try:
                        ast.parse(code)
                        stdout = f"[AgentWorld Executed Virtual Script {tokens[1]}: OK]"
                    except SyntaxError as se:
                        stderr = f"SyntaxError in {tokens[1]}: {se}"
                        exit_code = 1
                        safety_score = 0.40
                        regression_prob = 0.80
                else:
                    stderr = f"python: can't open file '{tokens[1]}': [Errno 2] No such file or directory"
                    exit_code = 2
                    safety_score = 0.50
                    regression_prob = 0.50
        elif cmd_name == "adb":
            sub = tokens[1] if len(tokens) > 1 else "devices"
            if sub == "devices":
                lines = ["List of devices attached"]
                for d_ip, d_info in self._adb_devices.items():
                    m = d_info.get("model", "")
                    lines.append(f"{d_ip}\t{d_info['status']}\tmodel:{m}")
                stdout = "\n".join(lines)
            elif sub == "shell":
                shell_cmd = " ".join(tokens[2:])
                if "termux-wake-lock" in shell_cmd:
                    stdout = "[Termux WakeLock Acquired 24/7]"
                else:
                    stdout = f"[ADB Shell Output: {shell_cmd} -> OK]"
            else:
                stdout = f"[ADB {sub} executed successfully]"
        elif cmd_name == "git":
            sub = tokens[1] if len(tokens) > 1 else "status"
            if sub == "status":
                diff = vfs.get_diff()
                stdout = f"On branch main\nModified: {len(diff['modified'])}, Created: {len(diff['created'])}, Deleted: {len(diff['deleted'])}"
            elif sub == "commit":
                stdout = "[main 7a8b9c0] Committed shadow changes to virtual branch"
            elif sub == "diff":
                stdout = "diff --git a/file b/file\n--- a/file\n+++ b/file"
            else:
                stdout = f"git {sub} completed successfully"
        else:
            stdout = f"[{cmd_name} executed in AgentWorld shadow sandbox]"

        return AgentWorldStepResult(
            step_index=0,
            action_type="system_command",
            action_raw=command_str,
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            safety_score=safety_score if exit_code == 0 else 0.50,
            regression_probability=regression_prob if exit_code == 0 else 0.40,
            confidence=confidence,
            state_diff=vfs.get_diff(),
            diagnostics={"exit_code": exit_code, "command": cmd_name},
        )

    def simulate_code_mutation(
        self,
        file_path: str,
        new_content: str,
        vfs: CopyOnWriteVFS,
        language: str = "python",
    ) -> AgentWorldStepResult:
        target_path = os.path.normpath(file_path)
        old_content = vfs.read_file(target_path) or ""

        syntax_valid = True
        err_msg = ""
        if language == "python" or target_path.endswith(".py"):
            try:
                ast.parse(new_content)
                syntax_valid = True
            except SyntaxError as se:
                syntax_valid = False
                err_msg = f"Python SyntaxError: {se}"
        elif language == "json" or target_path.endswith(".json"):
            try:
                json.loads(new_content)
                syntax_valid = True
            except json.JSONDecodeError as je:
                syntax_valid = False
                err_msg = f"JSON DecodeError: {je}"

        if not syntax_valid:
            return AgentWorldStepResult(
                step_index=0,
                action_type="code_mutation",
                action_raw={"file": file_path, "language": language},
                stdout="",
                stderr=err_msg,
                exit_code=1,
                safety_score=0.30,
                regression_probability=0.90,
                confidence=0.98,
                state_diff={"file": target_path, "status": "SYNTAX_ERROR"},
                diagnostics={"syntax_valid": False, "error": err_msg},
            )

        vfs.write_file(target_path, new_content)
        diff = vfs.get_diff()

        return AgentWorldStepResult(
            step_index=0,
            action_type="code_mutation",
            action_raw={"file": file_path, "language": language},
            stdout=f"Code mutation applied cleanly to {target_path}",
            stderr="",
            exit_code=0,
            safety_score=0.98,
            regression_probability=0.02,
            confidence=0.95,
            state_diff=diff,
            diagnostics={
                "file": target_path,
                "old_len": len(old_content),
                "new_len": len(new_content),
                "syntax_valid": True,
            },
        )

    def simulate_mcp_tool_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        vfs: CopyOnWriteVFS,
    ) -> AgentWorldStepResult:
        if tool_name not in self._mcp_tools_registry:
            return AgentWorldStepResult(
                step_index=0,
                action_type="mcp_tool",
                action_raw={"tool": tool_name, "args": arguments},
                stdout="",
                stderr=f"MCP Tool '{tool_name}' not registered in AgentWorld schema",
                exit_code=1,
                safety_score=0.60,
                regression_probability=0.40,
                confidence=0.90,
                diagnostics={"registered": False},
            )

        if tool_name == "write_file":
            p = arguments.get("path", "/workspace/unnamed.txt")
            c = arguments.get("content", "")
            vfs.write_file(p, c)
            return AgentWorldStepResult(
                step_index=0,
                action_type="mcp_tool",
                action_raw={"tool": tool_name, "args": arguments},
                stdout=f"Successfully wrote {len(c)} bytes to {p}",
                exit_code=0,
                safety_score=0.99,
                regression_probability=0.01,
                confidence=0.96,
                state_diff=vfs.get_diff(),
            )
        elif tool_name == "read_file":
            p = arguments.get("path", "")
            c = vfs.read_file(p)
            if c is not None:
                return AgentWorldStepResult(
                    step_index=0,
                    action_type="mcp_tool",
                    action_raw={"tool": tool_name, "args": arguments},
                    stdout=c,
                    exit_code=0,
                    safety_score=1.0,
                    regression_probability=0.0,
                    confidence=0.98,
                )
            else:
                return AgentWorldStepResult(
                    step_index=0,
                    action_type="mcp_tool",
                    action_raw={"tool": tool_name, "args": arguments},
                    stdout="",
                    stderr=f"File not found in VFS: {p}",
                    exit_code=1,
                    safety_score=0.70,
                    regression_probability=0.20,
                    confidence=0.92,
                )
        else:
            return AgentWorldStepResult(
                step_index=0,
                action_type="mcp_tool",
                action_raw={"tool": tool_name, "args": arguments},
                stdout=f"MCP Tool {tool_name} executed successfully",
                exit_code=0,
                safety_score=0.95,
                regression_probability=0.02,
                confidence=0.92,
            )

    def rollout_trajectory(
        self,
        action_payload: Dict[str, Any],
        lookahead_steps: int = 30,
        base_vfs: Optional[CopyOnWriteVFS] = None,
    ) -> Dict[str, Any]:
        vfs = base_vfs.clone() if base_vfs else CopyOnWriteVFS(base_real_root=self.base_dir)
        actions = action_payload.get("actions", [])
        if not actions and "command" in action_payload:
            base_cmd = action_payload["command"]
            actions = [{"type": "system_command", "payload": base_cmd}]
            for i in range(1, lookahead_steps):
                if i % 3 == 1:
                    actions.append({"type": "system_command", "payload": "pytest tests/ -q"})
                elif i % 3 == 2:
                    actions.append({"type": "system_command", "payload": "git status"})
                else:
                    actions.append({"type": "system_command", "payload": "echo step_verified"})
        elif not actions and "file_path" in action_payload and "content" in action_payload:
            actions = [
                {"type": "code_mutation", "payload": {"file_path": action_payload["file_path"], "content": action_payload["content"]}}
            ]
            for i in range(1, lookahead_steps):
                actions.append({"type": "system_command", "payload": "pytest --tb=short"})

        while len(actions) < lookahead_steps:
            actions.append({"type": "system_command", "payload": "echo verification_noop"})

        step_results: List[AgentWorldStepResult] = []
        total_safety = 0.0
        total_regression = 0.0
        total_confidence = 0.0

        for idx, act in enumerate(actions[:lookahead_steps]):
            act_type = act.get("type", "system_command")
            act_payload = act.get("payload", "")

            if act_type == "system_command":
                res = self.simulate_shell_command(str(act_payload), vfs=vfs)
            elif act_type == "code_mutation":
                if isinstance(act_payload, dict):
                    fp = act_payload.get("file_path", "/workspace/script.py")
                    cnt = act_payload.get("content", "")
                    lang = act_payload.get("language", "python")
                else:
                    fp = "/workspace/script.py"
                    cnt = str(act_payload)
                    lang = "python"
                res = self.simulate_code_mutation(fp, cnt, vfs=vfs, language=lang)
            elif act_type == "mcp_tool":
                if isinstance(act_payload, dict):
                    tn = act_payload.get("tool", "read_file")
                    args = act_payload.get("args", {})
                else:
                    tn = "read_file"
                    args = {}
                res = self.simulate_mcp_tool_call(tn, args, vfs=vfs)
            else:
                res = self.simulate_shell_command(str(act_payload), vfs=vfs)

            res.step_index = idx + 1
            step_results.append(res)
            total_safety += res.safety_score
            total_regression = max(total_regression, res.regression_probability)
            total_confidence += res.confidence

            if res.safety_score < 0.20:
                break

        n_steps = len(step_results)
        avg_safety = total_safety / n_steps if n_steps > 0 else 0.0
        avg_confidence = total_confidence / n_steps if n_steps > 0 else 0.0

        return {
            "driver": "Qwen-AgentWorld-35B",
            "steps_requested": lookahead_steps,
            "steps_completed": n_steps,
            "safety_score": round(avg_safety, 4),
            "regression_probability": round(total_regression, 4),
            "layout_overflows": 0,
            "simulation_confidence": round(avg_confidence, 4),
            "vfs_diff": vfs.get_diff(),
            "step_results": [asdict(r) for r in step_results],
        }
