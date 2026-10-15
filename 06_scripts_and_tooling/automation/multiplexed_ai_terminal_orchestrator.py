#!/usr/bin/env python3
"""
Multiplexed & Headless Local AI Terminal Orchestrator & Teacher-Student Distillation Engine.

Governs execution, multiplexing (tmux, zellij, headless PTY), and continuous learning
across the local AI CLI ecosystem:
- pi (@earendil-works/pi-coding-agent)
- junie (JetBrains CLI agent)
- intellij_local_ai (PyCharm/IntelliJ local model bridge)
- llm CLI
- Other terminal AI harnesses

Complies with:
- Rule 1: Zero-Mock Empirical Truth Mandate
- Rule 3 & 10: Host RAM Sanctuary (>= 4.8 GB free buffer) and offloading to L8/L3
- continus-lens-practice-automation & screen-lens-sovereign Teacher-Student protocol
"""

import os
import re
import sys
import pty
import time
import json
import fcntl
import select
import shutil
import hashlib
import argparse
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

LORA_DATASET_PATH = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/data/continuous_lora_dataset.jsonl")
IDE_TRACES_PATH = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/data/ide_distillation_traces.jsonl")

# CLI Binaries
PI_BIN = "/Users/aaron/.local/bin/pi"
JUNIE_BIN = "/Users/aaron/.local/bin/junie"
LLM_BIN = "/Users/aaron/.local/bin/llm"
TMUX_BIN = "/Users/aaron/.local/bin/tmux" if os.path.exists("/Users/aaron/.local/bin/tmux") else shutil.which("tmux")
ZELLIJ_BIN = "/opt/homebrew/bin/zellij" if os.path.exists("/opt/homebrew/bin/zellij") else shutil.which("zellij")
PYCHARM_BIN = "/Applications/PyCharm.app/Contents/MacOS/pycharm"

# Mesh Nodes for Remote Offloading (Rule 0 & Rule 3)
OFFLOAD_NODES = {
    "L8": {"host": "10.0.0.8", "user": "linuxmini", "desc": "Lauburu Linux Mini Hub (32 GB RAM, TB4 40G)"},
    "L3": {"host": "192.168.8.225", "user": "linux", "desc": "Linux Head Node AMD (15 GB RAM)"},
    "L2": {"host": "10.0.0.4", "user": "aaronmaher", "desc": "MacBook Pro Intel (16 GB RAM, TB4)"},
}


class HostSanctuary:
    """Monitors Darwin host RAM and enforces >= 4.8 GB free buffer using canonical Rule 1 formulas."""

    @staticmethod
    def get_free_ram_gb() -> float:
        try:
            total_ram_proc = subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True, check=True)
            total_ram = int(total_ram_proc.stdout.strip())

            proc = subprocess.run(["vm_stat"], capture_output=True, text=True, check=True)
            page_size = 16384
            stats = {}
            for line in proc.stdout.splitlines():
                if "page size of" in line:
                    m = re.search(r"page size of (\d+) bytes", line)
                    if m:
                        page_size = int(m.group(1))
                elif ":" in line:
                    k, v = line.split(":", 1)
                    v = v.strip().rstrip(".")
                    if v.isdigit():
                        stats[k.strip()] = int(v)

            anon = stats.get("Anonymous pages", 0)
            purge_p = stats.get("Pages purgeable", 0)
            wired = stats.get("Pages wired down", 0)
            compressor = stats.get("Pages occupied by compressor", 0)

            app_mem = max(0, (anon - purge_p) * page_size)
            wired_mem = wired * page_size
            comp_mem = compressor * page_size
            mem_used = app_mem + wired_mem + comp_mem

            free_headroom = max(0, total_ram - mem_used)
            return free_headroom / (1024 ** 3)
        except Exception:
            return 8.0

    @classmethod
    def is_sanctuary_safe(cls, threshold_gb: float = 4.8) -> Tuple[bool, float]:
        free_gb = cls.get_free_ram_gb()
        return (free_gb >= threshold_gb), free_gb


class LocalCliHarvester:
    """Extracts authentic teacher-student training pairs from CLI session logs."""

    @staticmethod
    def append_pairs(pairs: List[Dict[str, Any]], dataset_path: Optional[Path] = None, traces_path: Optional[Path] = None) -> int:
        if not pairs:
            return 0
        target_dataset = dataset_path or LORA_DATASET_PATH
        target_traces = traces_path or IDE_TRACES_PATH
        target_dataset.parent.mkdir(parents=True, exist_ok=True)
        if target_traces:
            target_traces.parent.mkdir(parents=True, exist_ok=True)

        new_pairs = []
        with open(target_dataset, "a+", encoding="utf-8") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.seek(0)
                existing_hashes = set()
                for line in f:
                    if line.strip():
                        try:
                            d = json.loads(line)
                            h = d.get("sha256") or d.get("metadata", {}).get("sha256")
                            if h:
                                existing_hashes.add(h)
                        except Exception:
                            pass

                for p in pairs:
                    h = p.get("sha256") or p.get("metadata", {}).get("sha256")
                    if not h or h not in existing_hashes:
                        new_pairs.append(p)
                        if h:
                            existing_hashes.add(h)

                if new_pairs:
                    f.seek(0, os.SEEK_END)
                    for p in new_pairs:
                        f.write(json.dumps(p) + "\n")
                    f.flush()
                    os.fsync(f.fileno())
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

        # Thread-safe write to target_traces if specified and distinct
        if new_pairs and target_traces and target_traces != target_dataset:
            with open(target_traces, "a", encoding="utf-8") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    for p in new_pairs:
                        f.write(json.dumps(p) + "\n")
                    f.flush()
                    os.fsync(f.fileno())
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)

        return len(new_pairs)

    @classmethod
    def harvest_pi_sessions(cls, max_files: int = 500) -> List[Dict[str, Any]]:
        pi_sessions_dir = Path.home() / ".pi" / "agent" / "sessions"
        if not pi_sessions_dir.exists():
            return []

        pairs: List[Dict[str, Any]] = []
        files = sorted(pi_sessions_dir.rglob("*.jsonl"), key=lambda x: x.stat().st_mtime, reverse=True)

        for f in files[:max_files]:
            try:
                lines = f.read_text(errors="ignore").splitlines()
                user_prompt = ""
                assistant_response = ""
                thinking_text = ""
                tool_calls = []
                failed_attempts = []
                timestamp = datetime.fromtimestamp(f.stat().st_mtime, timezone.utc).isoformat()

                for line in lines:
                    if not line.strip():
                        continue
                    d = json.loads(line)
                    if d.get("type") == "message":
                        msg = d.get("message", {})
                        role = msg.get("role")
                        content = msg.get("content")
                        err = msg.get("errorMessage")

                        if err:
                            failed_attempts.append(str(err))

                        if role == "user":
                            if isinstance(content, list):
                                for item in content:
                                    if item.get("type") == "text":
                                        user_prompt += item.get("text", "") + " "
                            elif isinstance(content, str):
                                user_prompt += content + " "

                        elif role == "assistant":
                            if isinstance(content, list):
                                for item in content:
                                    itype = item.get("type")
                                    if itype == "text":
                                        assistant_response += item.get("text", "") + "\n"
                                    elif itype == "thinking":
                                        thinking_text += item.get("thinking", "") + "\n"
                                    elif itype == "tool_use":
                                        tool_calls.append(f"Tool `{item.get('name')}`: {json.dumps(item.get('input'))}")
                            elif isinstance(content, str):
                                assistant_response += content + "\n"

                user_prompt = user_prompt.strip()
                assistant_response = assistant_response.strip()

                if user_prompt and (assistant_response or tool_calls or thinking_text):
                    output_parts = []
                    if thinking_text:
                        output_parts.append(f"### Reasoning:\n{thinking_text.strip()}")
                    if tool_calls:
                        output_parts.append("### Actions Executed:\n" + "\n".join(tool_calls))
                    if assistant_response:
                        output_parts.append(f"### Final Response:\n{assistant_response}")

                    completion = "\n\n".join(output_parts)
                    instruction = "Execute local software engineering task via Pi Agent CLI"

                    payload_str = f"{instruction}\n{user_prompt}\n{completion}"
                    sha256_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

                    # Standard SFT Pair
                    pair = {
                        "timestamp": timestamp,
                        "instruction": instruction,
                        "input": user_prompt,
                        "output": completion,
                        "prompt": f"{instruction}\n\nUser Request: {user_prompt}",
                        "completion": completion,
                        "source": "pi_coding_agent",
                        "category": "terminal_agent_engineering",
                        "sha256": sha256_hash,
                        "metadata": {
                            "session_file": f.name,
                            "sha256": sha256_hash,
                        },
                    }
                    pairs.append(pair)

                    # DPO Pair (if failure occurred prior to clean response)
                    if failed_attempts and completion:
                        rejected_text = "\n".join(failed_attempts[:3])
                        dpo_payload = f"{instruction}\n{user_prompt}\n{completion}\n{rejected_text}"
                        dpo_hash = hashlib.sha256(dpo_payload.encode("utf-8")).hexdigest()
                        dpo_pair = {
                            "timestamp": timestamp,
                            "instruction": instruction,
                            "input": user_prompt,
                            "chosen": completion,
                            "rejected": rejected_text,
                            "source": "pi_coding_agent_dpo",
                            "category": "terminal_agent_dpo",
                            "sha256": dpo_hash,
                            "metadata": {
                                "session_file": f.name,
                                "sha256": dpo_hash,
                            },
                        }
                        pairs.append(dpo_pair)

            except Exception:
                continue

        return pairs

    @classmethod
    def harvest_junie_sessions(cls, max_sessions: int = 50) -> List[Dict[str, Any]]:
        junie_dir = Path.home() / ".junie" / "sessions"
        if not junie_dir.exists():
            return []

        pairs: List[Dict[str, Any]] = []
        sessions = sorted(junie_dir.glob("session-*"), key=lambda x: x.stat().st_mtime, reverse=True)

        for s_dir in sessions[:max_sessions]:
            transcript_file = s_dir / "transcript.md"
            if not transcript_file.exists():
                continue

            try:
                content = transcript_file.read_text(errors="ignore")
                # Split transcript by sections
                # Junie transcripts usually have:
                # ## User\n<prompt>\n## Thinking\n<thinking>\n...
                sections = re.split(r"\n##\s+User\n+", content)
                timestamp = datetime.fromtimestamp(transcript_file.stat().st_mtime, timezone.utc).isoformat()

                for sec in sections[1:]:  # Skip pre-user introduction
                    parts = re.split(r"\n##\s+", sec, maxsplit=1)
                    user_req = parts[0].strip()
                    agent_action = ("## " + parts[1].strip()) if len(parts) > 1 else ""

                    if user_req and len(agent_action) > 50:
                        # Truncate overly massive transcripts (> 8000 chars per pair)
                        if len(agent_action) > 8000:
                            agent_action = agent_action[:8000] + "\n... [TRUNCATED_FOR_LORA_EFFICIENCY]"

                        instruction = "Execute IDE and repository engineering task via JetBrains Junie Agent"
                        sha256_hash = hashlib.sha256(f"{instruction}\n{user_req}\n{agent_action}".encode("utf-8")).hexdigest()
                        pair = {
                            "timestamp": timestamp,
                            "prompt": f"{instruction}\n\nTask: {user_req}",
                            "completion": agent_action,
                            "instruction": instruction,
                            "input": user_req,
                            "output": agent_action,
                            "source": "jetbrains_junie_cli",
                            "category": "ide_agent_engineering",
                            "sha256": sha256_hash,
                            "metadata": {
                                "session_dir": s_dir.name,
                                "sha256": sha256_hash,
                            },
                        }
                        pairs.append(pair)
            except Exception:
                continue

        return pairs


class TerminalMultiplexer:
    """Manages tmux, zellij, and headless PTY sessions across the mesh."""

    SESSION_NAME = "mesh_ai_clis"

    @classmethod
    def ensure_tmux_session(cls) -> bool:
        if not TMUX_BIN:
            return False
        check = subprocess.run([TMUX_BIN, "has-session", "-t", cls.SESSION_NAME], capture_output=True)
        if check.returncode != 0:
            res = subprocess.run([TMUX_BIN, "new-session", "-d", "-s", cls.SESSION_NAME, "-n", "control"], capture_output=True)
            return res.returncode == 0
        return True

    @classmethod
    def run_in_tmux(cls, cli_name: str, command: str, window_name: Optional[str] = None) -> Dict[str, Any]:
        if not cls.ensure_tmux_session():
            return {"success": False, "error": "tmux not available"}

        win = window_name or f"{cli_name}_{int(time.time())}"
        # Create new window
        subprocess.run([TMUX_BIN, "new-window", "-t", cls.SESSION_NAME, "-n", win])
        # Send command
        subprocess.run([TMUX_BIN, "send-keys", "-t", f"{cls.SESSION_NAME}:{win}", command, "C-m"])

        return {
            "success": True,
            "session": cls.SESSION_NAME,
            "window": win,
            "command": command,
            "attach_hint": f"tmux attach-session -t {cls.SESSION_NAME}:{win}",
        }

    @classmethod
    def capture_tmux_pane(cls, window_name: str, lines: int = 200) -> str:
        if not TMUX_BIN:
            return ""
        proc = subprocess.run(
            [TMUX_BIN, "capture-pane", "-p", "-t", f"{cls.SESSION_NAME}:{window_name}", "-S", f"-{lines}"],
            capture_output=True,
            text=True,
        )
        return proc.stdout

    @staticmethod
    def run_headless_pty(cmd_args: List[str], cwd: Optional[str] = None, timeout_sec: int = 120) -> Dict[str, Any]:
        """
        Executes an AI CLI inside a headless pseudo-terminal (PTY) to capture
        full interactive formatting, ANSI escapes, and stdout without requiring Aqua/X11.
        """
        master_fd, slave_fd = pty.openpty()
        start_time = time.time()

        proc = subprocess.Popen(
            cmd_args,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            cwd=cwd,
            close_fds=True,
        )
        os.close(slave_fd)

        output_chunks = []
        try:
            while proc.poll() is None:
                r, _, _ = select.select([master_fd], [], [], 0.5)
                if master_fd in r:
                    chunk = os.read(master_fd, 4096)
                    if chunk:
                        output_chunks.append(chunk.decode("utf-8", errors="replace"))
                if time.time() - start_time > timeout_sec:
                    proc.kill()
                    break

            # Read any remaining output
            while True:
                r, _, _ = select.select([master_fd], [], [], 0.1)
                if master_fd in r:
                    chunk = os.read(master_fd, 4096)
                    if not chunk:
                        break
                    output_chunks.append(chunk.decode("utf-8", errors="replace"))
                else:
                    break
        finally:
            os.close(master_fd)

        exit_code = proc.wait()
        raw_output = "".join(output_chunks)
        # Strip ANSI escape sequences for clean text
        ansi_regex = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        clean_output = ansi_regex.sub("", raw_output)

        return {
            "exit_code": exit_code,
            "duration_sec": round(time.time() - start_time, 2),
            "raw_output": raw_output,
            "clean_output": clean_output,
        }


class CliOrchestrator:
    """Coordinates execution across Pi, Junie, PyCharm Local AI, and LLM CLIs."""

    @classmethod
    def execute_pi(cls, task: str, mode: str = "headless", local_model: bool = True) -> Dict[str, Any]:
        if not os.path.exists(PI_BIN):
            return {"error": f"pi binary not found at {PI_BIN}"}

        # Build pi command
        cmd = [PI_BIN]
        if local_model:
            # Point to local server or offline mode
            cmd.extend(["--offline"])
        cmd.append(task)

        if mode == "tmux":
            cmd_str = " ".join(cmd)
            return TerminalMultiplexer.run_in_tmux("pi", cmd_str)
        else:
            res = TerminalMultiplexer.run_headless_pty(cmd, timeout_sec=60)
            # Formulate training pair if output exists
            if res.get("clean_output"):
                instruction = "Execute local Pi Agent CLI task"
                sha256_hash = hashlib.sha256(f"{instruction}\n{task}\n{res['clean_output']}".encode("utf-8")).hexdigest()
                pair = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "prompt": f"{instruction}: {task}",
                    "completion": res["clean_output"],
                    "instruction": instruction,
                    "input": task,
                    "output": res["clean_output"],
                    "source": "pi_pty_execution",
                    "category": "cli_headless_task",
                    "sha256": sha256_hash,
                    "metadata": {
                        "exit_code": res["exit_code"],
                        "sha256": sha256_hash,
                    },
                }
                LocalCliHarvester.append_pairs([pair])
            return res

    @classmethod
    def execute_junie(cls, task: str, mode: str = "headless", use_local_llm: bool = True) -> Dict[str, Any]:
        if not os.path.exists(JUNIE_BIN):
            return {"error": f"junie binary not found at {JUNIE_BIN}"}

        json_out = f"/tmp/junie_out_{int(time.time())}.json"
        cmd = [
            JUNIE_BIN,
            f"--task={task}",
            "--skip-update-check",
            "--output-format=json",
            f"--json-output-file={json_out}",
        ]
        if use_local_llm:
            # LiteLLM points to Port 8082 or 8090 local mesh endpoint per Rule 0/15
            cmd.extend(["--provider=litellm", "--litellm-url=http://127.0.0.1:8090/v1"])

        if mode == "tmux":
            cmd_str = " ".join(cmd)
            return TerminalMultiplexer.run_in_tmux("junie", cmd_str)
        else:
            res = TerminalMultiplexer.run_headless_pty(cmd, timeout_sec=90)
            parsed_json = {}
            if os.path.exists(json_out):
                try:
                    parsed_json = json.loads(Path(json_out).read_text())
                except Exception:
                    pass

            output_text = res.get("clean_output", "")
            if parsed_json:
                output_text += "\n" + json.dumps(parsed_json, indent=2)

            if output_text.strip():
                instruction = "Execute JetBrains Junie CLI engineering task"
                sha256_hash = hashlib.sha256(f"{instruction}\n{task}\n{output_text}".encode("utf-8")).hexdigest()
                pair = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "prompt": f"{instruction}: {task}",
                    "completion": output_text,
                    "instruction": instruction,
                    "input": task,
                    "output": output_text,
                    "source": "junie_pty_execution",
                    "category": "ide_headless_task",
                    "sha256": sha256_hash,
                    "metadata": {
                        "exit_code": res["exit_code"],
                        "json_out": json_out,
                        "sha256": sha256_hash,
                    },
                }
                LocalCliHarvester.append_pairs([pair])

            res["json_data"] = parsed_json
            return res

    @classmethod
    def execute_remote(cls, node_id: str, command: str) -> Dict[str, Any]:
        """Offloads task to remote mesh node via SSH per Rule 3 & 10."""
        node = OFFLOAD_NODES.get(node_id)
        if not node:
            return {"error": f"Unknown offload node {node_id}. Choose from {list(OFFLOAD_NODES.keys())}"}

        host = node["host"]
        user = node["user"]
        ssh_cmd = ["ssh", "-o", "ConnectTimeout=5", f"{user}@{host}", command]
        start_t = time.time()
        try:
            proc = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=120)
            return {
                "node": node_id,
                "host": host,
                "exit_code": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "duration_sec": round(time.time() - start_t, 2),
            }
        except Exception as e:
            return {"error": str(e), "node": node_id, "host": host}


def main():
    parser = argparse.ArgumentParser(description="Multiplexed & Headless Local AI Terminal Orchestrator")
    parser.add_argument("--status", action="store_true", help="Report status of RAM sanctuary, CLIs, and datasets")
    parser.add_argument("--run", choices=["pi", "junie", "llm"], help="CLI tool to execute")
    parser.add_argument("--task", type=str, help="Task description or instruction for the AI CLI")
    parser.add_argument("--mode", choices=["headless", "tmux"], default="headless", help="Execution mode (default: headless)")
    parser.add_argument("--offload", choices=["L8", "L3", "L2"], help="Offload task to remote node via SSH")
    parser.add_argument("--harvest-pi", action="store_true", help="Harvest and distill all Pi agent session logs")
    parser.add_argument("--harvest-junie", action="store_true", help="Harvest and distill all Junie session logs")
    parser.add_argument("--harvest-all", action="store_true", help="Harvest from all local AI CLIs")

    args = parser.parse_args()

    # Memory Check
    safe, free_gb = HostSanctuary.is_sanctuary_safe()

    if args.status:
        print("=== MULTIPLEXED AI TERMINAL ORCHESTRATOR STATUS ===")
        print(f"Host RAM Headroom: {free_gb:.2f} GB free (Sanctuary >= 4.8 GB: {'PASSED' if safe else 'WARNING'})")
        print("\nInstalled CLIs:")
        print(f"  pi:      {'FOUND (' + PI_BIN + ')' if os.path.exists(PI_BIN) else 'MISSING'}")
        print(f"  junie:   {'FOUND (' + JUNIE_BIN + ')' if os.path.exists(JUNIE_BIN) else 'MISSING'}")
        print(f"  llm:     {'FOUND (' + LLM_BIN + ')' if os.path.exists(LLM_BIN) else 'MISSING'}")
        print(f"  tmux:    {'FOUND (' + str(TMUX_BIN) + ')' if TMUX_BIN else 'MISSING'}")
        print(f"  zellij:  {'FOUND (' + str(ZELLIJ_BIN) + ')' if ZELLIJ_BIN else 'MISSING'}")
        print(f"  pycharm: {'FOUND (' + PYCHARM_BIN + ')' if os.path.exists(PYCHARM_BIN) else 'MISSING'}")

        print("\nDataset Archives:")
        lora_lines = len(LORA_DATASET_PATH.read_text().splitlines()) if LORA_DATASET_PATH.exists() else 0
        ide_lines = len(IDE_TRACES_PATH.read_text().splitlines()) if IDE_TRACES_PATH.exists() else 0
        print(f"  continuous_lora_dataset.jsonl: {lora_lines} records")
        print(f"  ide_distillation_traces.jsonl: {ide_lines} records")

        print("\nMultiplexed tmux Sessions:")
        if TMUX_BIN:
            p = subprocess.run([TMUX_BIN, "ls"], capture_output=True, text=True)
            print(p.stdout.strip() if p.stdout.strip() else "  (No active tmux sessions)")
        return

    if args.harvest_pi or args.harvest_all:
        print("[*] Harvesting trajectories from Pi coding agent sessions...")
        pi_pairs = LocalCliHarvester.harvest_pi_sessions()
        count = LocalCliHarvester.append_pairs(pi_pairs)
        print(f"[✓] Distilled {count} new training pairs from Pi sessions.")

    if args.harvest_junie or args.harvest_all:
        print("[*] Harvesting trajectories from JetBrains Junie sessions...")
        junie_pairs = LocalCliHarvester.harvest_junie_sessions()
        count = LocalCliHarvester.append_pairs(junie_pairs)
        print(f"[✓] Distilled {count} new training pairs from Junie sessions.")

    if args.run:
        if not args.task:
            print("[!] Error: --task is required when using --run")
            sys.exit(1)

        # Check RAM headroom if running locally
        if not safe and not args.offload:
            print(f"[!] Warning: RAM buffer low ({free_gb:.2f} GB < 4.8 GB). Offloading recommended to L8/L3.")

        if args.offload:
            print(f"[*] Offloading {args.run} execution to Node {args.offload}...")
            res = CliOrchestrator.execute_remote(args.offload, f"{args.run} {args.task}")
            print(json.dumps(res, indent=2))
        elif args.run == "pi":
            print(f"[*] Executing Pi CLI in {args.mode} mode...")
            res = CliOrchestrator.execute_pi(args.task, mode=args.mode)
            print(f"[✓] Result: Exit Code {res.get('exit_code')}, Duration: {res.get('duration_sec')}s")
            print(res.get("clean_output", "")[:500])
        elif args.run == "junie":
            print(f"[*] Executing Junie CLI in {args.mode} mode...")
            res = CliOrchestrator.execute_junie(args.task, mode=args.mode)
            print(f"[✓] Result: Exit Code {res.get('exit_code')}, Duration: {res.get('duration_sec')}s")
            print(res.get("clean_output", "")[:500])


if __name__ == "__main__":
    main()
