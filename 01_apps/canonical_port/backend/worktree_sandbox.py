"""
Git Worktree Sandboxing Manager
backend/worktree_sandbox.py

Provides isolated, ephemeral Git Worktree environments for autonomous subagent code modification.
Guarantees that 01_apps and the primary repository are NEVER directly mutated by AI subagents.

Key Responsibilities:
  1. Dynamic Worktree Creation: Spawns isolated branched Git Worktrees in /tmp/lauburu_worktrees/
     via `git worktree add -b <branch_name> <worktree_dir> <base_commit>`.
  2. Input Sanitization & Security: Prevents directory traversal and sanitizes task slugs for Git branches.
  3. Isolation Verification: Programmatically asserts that modifications inside worktree do not leak to primary tree.
  4. Active Worktree Registry: Tracks all spawned sandboxes with timestamps and metadata.
  5. Teardown & Self-Healing Pruning: Robust cleanup using `git worktree remove --force` and `git worktree prune`.

Derived from: ORIGINAL_REQUEST.md §R1, PROJECT.md §Interface Contracts
"""

import os
import re
import time
import shutil
import logging
import subprocess
import pty
import select
import shlex
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Callable, Union

logger = logging.getLogger("WorktreeSandbox")


class WorktreeError(Exception):
    """Raised when a Git worktree operation fails or security boundaries are violated."""
    pass


class WorktreeSandbox:
    """
    Git Worktree Sandbox Manager.
    Ensures 01_apps is never directly mutated by AI subagents by creating
    dynamic isolated branched Git Worktrees in /tmp/lauburu_worktrees/.
    """
    DEFAULT_BASE_DIR: str = "/tmp/lauburu_worktrees"

    def __init__(self, base_dir: Optional[str] = None, repo_root: Optional[str] = None):
        self.base_dir = os.path.abspath(base_dir or self.DEFAULT_BASE_DIR)
        self.repo_root = os.path.abspath(repo_root or self._find_repo_root())
        os.makedirs(self.base_dir, exist_ok=True)
        self._active_worktrees: Dict[str, Dict[str, Any]] = {}

    def _find_repo_root(self) -> str:
        """Finds the root of the current Git working tree."""
        try:
            res = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                check=True,
                cwd=os.path.dirname(__file__)
            )
            return res.stdout.strip()
        except Exception:
            candidates = [
                os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")),
                os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
                os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
                "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo",
            ]
            for c in candidates:
                if os.path.isdir(os.path.join(c, ".git")) or os.path.isfile(os.path.join(c, ".git")):
                    return c
            return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    def _sanitize_name(self, name: str) -> str:
        """
        Sanitizes task name for valid git branch and directory naming.
        Removes invalid characters, collapses multiple underscores, and returns lowercase slug.
        """
        clean = re.sub(r"[^a-zA-Z0-9]", "_", name.strip())
        clean = re.sub(r"_+", "_", clean).strip("_")
        return clean.lower() or "unnamed_task"

    def create_worktree(self, task_name: str, base_commit: str = "HEAD") -> Dict[str, Any]:
        """
        Creates a dynamic branched Git Worktree in self.base_dir.
        Returns metadata dict:
          {"id": str, "task_name": str, "worktree_path": str, "branch": str, "created_at": float, "status": "CREATED"}
        """
        timestamp = int(time.time() * 1000)
        sanitized = self._sanitize_name(task_name)
        worktree_id = f"tui_{sanitized}_{timestamp}"
        branch_name = f"subagent/{worktree_id}"
        worktree_path = os.path.join(self.base_dir, worktree_id)

        # Path traversal guard
        abs_target = os.path.abspath(worktree_path)
        if not abs_target.startswith(self.base_dir):
            raise WorktreeError(f"Security Violation: Path traversal detected in task_name '{task_name}'.")

        # Execute git worktree add -b <branch> <path> <base_commit>
        try:
            cmd = ["git", "worktree", "add", "-b", branch_name, worktree_path, base_commit]
            res = subprocess.run(
                cmd,
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=True
            )
            logger.info(f"[WORKTREE] Created worktree {worktree_id} at {worktree_path} on branch {branch_name}")
        except subprocess.CalledProcessError as e:
            # Clean up leftover directory if git created one before failing
            if os.path.exists(worktree_path):
                shutil.rmtree(worktree_path, ignore_errors=True)
            err_msg = (e.stderr or e.stdout or "Unknown git error").strip()
            raise WorktreeError(f"Failed to create Git worktree: {err_msg}")
        except Exception as e:
            if os.path.exists(worktree_path):
                shutil.rmtree(worktree_path, ignore_errors=True)
            raise WorktreeError(f"Failed to create Git worktree: {e}")

        metadata = {
            "id": worktree_id,
            "task_name": task_name,
            "worktree_path": worktree_path,
            "branch": branch_name,
            "created_at": time.time(),
            "status": "CREATED"
        }
        self._active_worktrees[worktree_path] = metadata
        return metadata

    def cleanup_worktree(self, worktree_path: str, force: bool = True) -> bool:
        """
        Removes the worktree cleanly, deletes the associated branch, and prunes git metadata.
        Returns True if the worktree directory was removed or already nonexistent.
        """
        abs_path = os.path.abspath(worktree_path)
        metadata = self._active_worktrees.pop(abs_path, None)
        branch = metadata.get("branch") if metadata else None

        # 1. Execute `git worktree remove --force <path>`
        try:
            cmd = ["git", "worktree", "remove"]
            if force:
                cmd.append("--force")
            cmd.append(abs_path)
            subprocess.run(cmd, cwd=self.repo_root, capture_output=True, text=True)
        except Exception as e:
            logger.debug(f"[WORKTREE] git worktree remove warning: {e}")

        # 2. Execute `git worktree prune`
        try:
            subprocess.run(["git", "worktree", "prune"], cwd=self.repo_root, capture_output=True, text=True)
        except Exception as e:
            logger.debug(f"[WORKTREE] git worktree prune warning: {e}")

        # 3. Delete ephemeral branch if branch name is known or derivable
        if branch:
            try:
                subprocess.run(["git", "branch", "-D", branch], cwd=self.repo_root, capture_output=True, text=True)
            except Exception as e:
                logger.debug(f"[WORKTREE] git branch -D warning: {e}")
        else:
            # Fallback: if folder name starts with "tui_", try deleting subagent/tui_... branch
            folder_name = os.path.basename(abs_path)
            if folder_name.startswith("tui_"):
                try:
                    subprocess.run(["git", "branch", "-D", f"subagent/{folder_name}"], cwd=self.repo_root, capture_output=True, text=True)
                except Exception:
                    pass

        # 4. Ensure physical directory is completely removed
        if os.path.exists(abs_path):
            try:
                shutil.rmtree(abs_path, ignore_errors=True)
            except Exception as e:
                logger.warning(f"[WORKTREE] shutil.rmtree failed on {abs_path}: {e}")

        return not os.path.exists(abs_path)

    def verify_sandbox_isolation(
        self,
        worktree_path: str,
        relative_test_file: str = "01_apps/canonical_port/test_mutation.txt"
    ) -> bool:
        """
        Verifies that mutations inside worktree do not affect the primary working tree.
        Writes a test file inside worktree_path and asserts it is ABSENT in primary repo_root.
        """
        abs_worktree = os.path.abspath(worktree_path)
        if not os.path.isdir(abs_worktree):
            return False

        wt_file = os.path.join(abs_worktree, relative_test_file)
        primary_file = os.path.join(self.repo_root, relative_test_file)

        os.makedirs(os.path.dirname(wt_file), exist_ok=True)
        try:
            with open(wt_file, "w", encoding="utf-8") as f:
                f.write(f"isolation_verification_test_{time.time()}")

            exists_in_wt = os.path.isfile(wt_file)
            exists_in_primary = os.path.isfile(primary_file)

            return exists_in_wt and not exists_in_primary
        finally:
            if os.path.exists(wt_file):
                try:
                    os.remove(wt_file)
                except Exception:
                    pass

    def list_active_worktrees(self) -> List[Dict[str, Any]]:
        """Returns list of active worktree metadata dictionaries."""
        return list(self._active_worktrees.values())

    def prune_stale_worktrees(self, max_age_seconds: float = 3600.0) -> int:
        """
        Prunes worktrees older than max_age_seconds or missing from disk.
        Returns count of pruned worktrees.
        """
        now = time.time()
        pruned_count = 0
        for path, meta in list(self._active_worktrees.items()):
            age = now - meta.get("created_at", now)
            if age >= max_age_seconds or not os.path.exists(path):
                self.cleanup_worktree(path, force=True)
                pruned_count += 1
        return pruned_count

    def execute_in_worktree_pty(
        self,
        worktree_path: str,
        command: List[str],
        env: Optional[Dict[str, str]] = None,
        timeout: float = 30.0
    ) -> Tuple[int, str]:
        """
        Executes a command inside the specified worktree allocated with a POSIX pseudo-terminal (PTY)
        master/slave pair to preserve ANSI TrueColor and prevent subprocess stream buffering.
        Returns (exit_code, output_text).
        """
        abs_path = os.path.abspath(worktree_path)
        if not os.path.isdir(abs_path):
            raise WorktreeError(f"Cannot execute in non-existent worktree directory: {worktree_path}")

        master_fd, slave_fd = pty.openpty()
        output_chunks: List[str] = []
        start_time = time.time()

        merged_env = os.environ.copy()
        merged_env["TERM"] = "xterm-256color"
        merged_env["PYTHONUNBUFFERED"] = "1"
        if env:
            merged_env.update(env)

        try:
            proc = subprocess.Popen(
                command,
                cwd=abs_path,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                close_fds=True,
                env=merged_env
            )
            os.close(slave_fd)

            while proc.poll() is None:
                if time.time() - start_time > timeout:
                    proc.kill()
                    raise WorktreeError(f"PTY execution timed out after {timeout}s: {command}")

                r, _, _ = select.select([master_fd], [], [], 0.05)
                if master_fd in r:
                    try:
                        data = os.read(master_fd, 4096)
                        if data:
                            output_chunks.append(data.decode("utf-8", errors="replace"))
                    except (OSError, EOFError):
                        break

            # Read any trailing buffer
            while True:
                r, _, _ = select.select([master_fd], [], [], 0.01)
                if master_fd in r:
                    try:
                        data = os.read(master_fd, 4096)
                        if not data:
                            break
                        output_chunks.append(data.decode("utf-8", errors="replace"))
                    except (OSError, EOFError):
                        break
                else:
                    break

            proc.wait()
            return proc.returncode, "".join(output_chunks)
        finally:
            try:
                os.close(master_fd)
            except OSError:
                pass

    def stream_in_worktree_pty(
        self,
        worktree_path: str,
        command: List[str],
        on_chunk: Optional[Callable[[str], None]] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: float = 30.0
    ) -> int:
        """
        Executes a command inside the worktree via PTY and streams each output chunk live
        to the provided on_chunk callback in real-time.
        """
        abs_path = os.path.abspath(worktree_path)
        if not os.path.isdir(abs_path):
            raise WorktreeError(f"Cannot execute in non-existent worktree directory: {worktree_path}")

        master_fd, slave_fd = pty.openpty()
        start_time = time.time()

        merged_env = os.environ.copy()
        merged_env["TERM"] = "xterm-256color"
        merged_env["PYTHONUNBUFFERED"] = "1"
        if env:
            merged_env.update(env)

        try:
            proc = subprocess.Popen(
                command,
                cwd=abs_path,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                close_fds=True,
                env=merged_env
            )
            os.close(slave_fd)

            while proc.poll() is None:
                if time.time() - start_time > timeout:
                    proc.kill()
                    raise WorktreeError(f"PTY streaming timed out after {timeout}s: {command}")

                r, _, _ = select.select([master_fd], [], [], 0.05)
                if master_fd in r:
                    try:
                        data = os.read(master_fd, 4096)
                        if data:
                            chunk = data.decode("utf-8", errors="replace")
                            if on_chunk:
                                on_chunk(chunk)
                    except (OSError, EOFError):
                        break

            while True:
                r, _, _ = select.select([master_fd], [], [], 0.01)
                if master_fd in r:
                    try:
                        data = os.read(master_fd, 4096)
                        if not data:
                            break
                        chunk = data.decode("utf-8", errors="replace")
                        if on_chunk:
                            on_chunk(chunk)
                    except (OSError, EOFError):
                        break
                else:
                    break

            proc.wait()
            return proc.returncode
        finally:
            try:
                os.close(master_fd)
            except OSError:
                pass

    def run_command_in_pty(
        self,
        command: Union[List[str], str],
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: float = 30.0,
    ) -> Tuple[int, str]:
        """
        Executes a command inside a POSIX pseudo-terminal (PTY) master/slave pair (openpty)
        so spawned subagent execution preserves real-time unbuffered ANSI streams.
        """
        target_cwd = cwd or self.repo_root
        return run_command_in_pty(command, cwd=target_cwd, env=env, timeout=timeout)


def run_command_in_pty(
    command: Union[List[str], str],
    cwd: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    timeout: float = 30.0,
) -> Tuple[int, str]:
    """
    Executes a command inside a POSIX pseudo-terminal (PTY) master/slave pair (pty.openpty)
    so spawned subagent execution preserves real-time unbuffered ANSI streams.
    Returns (exit_code, output_text).
    """
    work_dir = os.path.abspath(cwd) if cwd else os.getcwd()
    if not os.path.isdir(work_dir):
        raise WorktreeError(f"Cannot execute in non-existent directory: {work_dir}")

    cmd_list: List[str]
    if isinstance(command, str):
        cmd_list = shlex.split(command)
    else:
        cmd_list = list(command)

    master_fd, slave_fd = pty.openpty()
    output_chunks: List[str] = []
    start_time = time.time()

    merged_env = os.environ.copy()
    merged_env["TERM"] = "xterm-256color"
    merged_env["PYTHONUNBUFFERED"] = "1"
    if env:
        merged_env.update(env)

    try:
        proc = subprocess.Popen(
            cmd_list,
            cwd=work_dir,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            close_fds=True,
            env=merged_env,
        )
        os.close(slave_fd)

        while proc.poll() is None:
            if time.time() - start_time > timeout:
                proc.kill()
                raise WorktreeError(f"PTY execution timed out after {timeout}s: {cmd_list}")

            r, _, _ = select.select([master_fd], [], [], 0.05)
            if master_fd in r:
                try:
                    data = os.read(master_fd, 4096)
                    if data:
                        output_chunks.append(data.decode("utf-8", errors="replace"))
                except (OSError, EOFError):
                    break

        # Read any trailing buffer
        while True:
            r, _, _ = select.select([master_fd], [], [], 0.01)
            if master_fd in r:
                try:
                    data = os.read(master_fd, 4096)
                    if not data:
                        break
                    output_chunks.append(data.decode("utf-8", errors="replace"))
                except (OSError, EOFError):
                    break
            else:
                break

        proc.wait()
        return proc.returncode, "".join(output_chunks)
    finally:
        try:
            os.close(master_fd)
        except OSError:
            pass

