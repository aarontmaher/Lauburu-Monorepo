"""
canonical_sync_engine.sync.git_worktree_manager
Lifecycle manager for isolated branch workspaces (.worktrees/<task_id>)
ensuring zero direct mutations to production branches without automated CI passage.
"""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from canonical_sync_engine.verification.self_healer import StorageSelfHealer

logger = logging.getLogger(__name__)


def _sanitize_task_id(task_id: str) -> str:
    """Sanitizes task ID for path and branch safety."""
    cleaned = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", task_id.strip())
    return cleaned or "default_task"


class GitWorktreeManager:
    """
    Manages isolated Git worktree workspaces located at .worktrees/<task_id>.
    Guarantees isolation of modifications, CI gated production merging, and safe cleanup.
    """

    def __init__(
        self,
        repo_path: Optional[Union[str, Path]] = None,
        worktrees_dir: Optional[Union[str, Path]] = None,
        default_ci_command: Optional[List[str]] = None,
        stale_lock_timeout_sec: float = 10.0,
    ) -> None:
        self.repo_path = Path(repo_path or os.environ.get(
            "GIT_REPO_PATH",
            "/Volumes/Lauburu-Monorepo"
        )).expanduser().resolve()

        self.worktrees_dir = Path(worktrees_dir or (self.repo_path / ".worktrees")).expanduser().resolve()
        self.default_ci_command = default_ci_command or ["pytest", "-q"]
        self.stale_lock_timeout_sec = stale_lock_timeout_sec
        self._healer = StorageSelfHealer(
            git_repo_path=self.repo_path,
            stale_lock_timeout_sec=self.stale_lock_timeout_sec,
        )
        self._ci_results: Dict[str, Dict[str, Any]] = {}

    def _clean_stale_locks(self, force: bool = False) -> List[str]:
        """Cleans any stale .git/index.lock or worktree lock files."""
        return self._healer.heal_git_locks(force=force)

    def _run_git(
        self,
        args: List[str],
        cwd: Optional[Path] = None,
        timeout: float = 60.0,
        check: bool = False,
    ) -> subprocess.CompletedProcess:
        """Executes a git command with lock healing and error diagnostics."""
        self._clean_stale_locks(force=False)
        target_cwd = str(cwd or self.repo_path)
        git_bin = shutil.which("git") or "/usr/bin/git"

        try:
            res = subprocess.run(
                [git_bin] + args,
                cwd=target_cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=check,
            )
            return res
        except subprocess.CalledProcessError as e:
            logger.error(f"Git command failed: {' '.join(args)}: {e.stderr}")
            raise
        except subprocess.TimeoutExpired as e:
            logger.error(f"Git command timed out: {' '.join(args)}")
            raise

    def get_worktree_path(self, task_id: str) -> Path:
        """Returns the canonical path for an isolated task worktree."""
        safe_id = _sanitize_task_id(task_id)
        return self.worktrees_dir / safe_id

    def is_branch_exists(self, branch_name: str) -> bool:
        """Checks if a git branch exists locally."""
        res = self._run_git(["branch", "--list", branch_name])
        return bool(res.stdout.strip())

    def create_worktree(
        self,
        task_id: str,
        branch_name: Optional[str] = None,
        base_branch: str = "main",
        new_branch: bool = True,
        force: bool = False,
    ) -> str:
        """
        Creates an isolated git worktree at .worktrees/<task_id>.
        Returns the absolute string path of the created worktree workspace.
        """
        safe_id = _sanitize_task_id(task_id)
        worktree_path = self.get_worktree_path(safe_id)
        target_branch = branch_name or f"worktree/{safe_id}"

        # Ensure parent .worktrees directory exists
        self.worktrees_dir.mkdir(parents=True, exist_ok=True)

        if worktree_path.exists():
            if force:
                self.cleanup_worktree(task_id, force=True)
            else:
                return str(worktree_path)

        # Check if branch exists
        branch_already_exists = self.is_branch_exists(target_branch)

        if branch_already_exists:
            # Attach worktree to existing branch
            cmd = ["worktree", "add", str(worktree_path), target_branch]
        else:
            if new_branch:
                # Create and checkout new branch from base_branch
                cmd = ["worktree", "add", "-b", target_branch, str(worktree_path), base_branch]
            else:
                cmd = ["worktree", "add", str(worktree_path), base_branch]

        res = self._run_git(cmd)
        if res.returncode != 0:
            # Handle potential branch collision or detached head fallback
            if "already exists" in res.stderr:
                cmd_fallback = ["worktree", "add", str(worktree_path), target_branch]
                res_fallback = self._run_git(cmd_fallback)
                if res_fallback.returncode != 0:
                    raise RuntimeError(f"Failed to create git worktree: {res_fallback.stderr}")
            else:
                raise RuntimeError(f"Failed to create git worktree: {res.stderr}")

        # Reset CI tracking for new/recreated worktree
        self._ci_results[safe_id] = {
            "passed": False,
            "timestamp": time.time(),
            "summary": "Initialized (CI not run yet)",
            "command": None,
        }

        return str(worktree_path)

    def list_worktrees(self) -> List[Dict[str, Any]]:
        """
        Lists all active git worktrees with metadata parsed from git worktree list --porcelain.
        """
        res = self._run_git(["worktree", "list", "--porcelain"])
        if res.returncode != 0:
            return []

        worktrees: List[Dict[str, Any]] = []
        current_entry: Dict[str, Any] = {}

        for line in res.stdout.splitlines():
            line = line.strip()
            if not line:
                if current_entry:
                    worktrees.append(current_entry)
                    current_entry = {}
                continue

            if line.startswith("worktree "):
                current_entry["path"] = line[len("worktree "):].strip()
            elif line.startswith("HEAD "):
                current_entry["head_sha"] = line[len("HEAD "):].strip()
            elif line.startswith("branch "):
                current_entry["branch"] = line[len("branch "):].strip()
            elif line.startswith("bare"):
                current_entry["bare"] = True
            elif line.startswith("locked"):
                current_entry["locked"] = True
            elif line.startswith("prunable"):
                current_entry["prunable"] = True

        if current_entry:
            worktrees.append(current_entry)

        # Enrich with task_id if inside self.worktrees_dir
        for wt in worktrees:
            wt_path = Path(wt.get("path", ""))
            try:
                if wt_path.is_relative_to(self.worktrees_dir):
                    wt["task_id"] = wt_path.name
                    wt["is_managed"] = True
                else:
                    wt["is_managed"] = False
            except Exception:
                wt["is_managed"] = False

        return worktrees

    def is_worktree_active(self, task_id: str) -> bool:
        """Verifies if the worktree exists on disk and in git worktree registration."""
        safe_id = _sanitize_task_id(task_id)
        target_path = self.get_worktree_path(safe_id)
        if not target_path.exists():
            return False

        active = self.list_worktrees()
        return any(Path(w.get("path", "")).resolve() == target_path.resolve() for w in active)

    def run_in_worktree(
        self,
        task_id: str,
        command: Union[List[str], str],
        timeout: float = 120.0,
        env: Optional[Dict[str, str]] = None,
    ) -> subprocess.CompletedProcess:
        """
        Executes a shell or process command inside the isolated worktree directory.
        """
        safe_id = _sanitize_task_id(task_id)
        worktree_path = self.get_worktree_path(safe_id)
        if not worktree_path.exists():
            raise FileNotFoundError(f"Worktree for task '{task_id}' does not exist at {worktree_path}")

        merged_env = dict(os.environ)
        if env:
            merged_env.update(env)

        is_shell = isinstance(command, str)
        res = subprocess.run(
            command,
            cwd=str(worktree_path),
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=is_shell,
            env=merged_env,
        )
        return res

    def run_ci_verification(
        self,
        task_id: str,
        test_command: Optional[Union[List[str], str]] = None,
        timeout: float = 300.0,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Runs automated test suite inside the worktree workspace.
        Records CI passage status for gated production merging.
        Returns:
            Tuple of (passed: bool, output_summary: str, details_dict: dict)
        """
        safe_id = _sanitize_task_id(task_id)
        worktree_path = self.get_worktree_path(safe_id)
        if not worktree_path.exists():
            raise FileNotFoundError(f"Cannot run CI: worktree for task '{task_id}' missing at {worktree_path}")

        cmd = test_command or self.default_ci_command
        start_time = time.time()

        try:
            res = self.run_in_worktree(safe_id, cmd, timeout=timeout)
            duration = time.time() - start_time
            passed = (res.returncode == 0)
            summary = res.stdout[-1000:] if passed else (res.stderr or res.stdout)[-1000:]

            ci_record = {
                "passed": passed,
                "returncode": res.returncode,
                "duration_sec": round(duration, 3),
                "timestamp": time.time(),
                "summary": summary.strip(),
                "command": cmd if isinstance(cmd, str) else " ".join(cmd),
            }
            self._ci_results[safe_id] = ci_record

            # Persist status in worktree for auditing
            status_file = worktree_path / ".ci_status.json"
            try:
                status_file.write_text(json.dumps(ci_record, indent=2), encoding="utf-8")
            except Exception:
                pass

            return passed, summary.strip(), ci_record

        except Exception as e:
            duration = time.time() - start_time
            ci_record = {
                "passed": False,
                "returncode": -1,
                "duration_sec": round(duration, 3),
                "timestamp": time.time(),
                "summary": f"CI execution failed with exception: {str(e)}",
                "command": str(cmd),
            }
            self._ci_results[safe_id] = ci_record
            return False, str(e), ci_record

    def is_ci_passed(self, task_id: str) -> bool:
        """Verifies if automated CI has passed for the given task workspace."""
        safe_id = _sanitize_task_id(task_id)
        record = self._ci_results.get(safe_id)
        if record and record.get("passed") is True:
            return True

        # Check persisted status file in worktree
        worktree_path = self.get_worktree_path(safe_id)
        status_file = worktree_path / ".ci_status.json"
        if status_file.exists():
            try:
                data = json.loads(status_file.read_text(encoding="utf-8"))
                if data.get("passed") is True:
                    self._ci_results[safe_id] = data
                    return True
            except Exception:
                pass

        return False

    def merge_to_production(
        self,
        task_id: str,
        target_branch: str = "main",
        require_ci: bool = True,
        squash: bool = False,
        commit_message: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Merges worktree branch into production target branch.
        Strictly enforces CI passage before allowing mutation.
        Returns (success: bool, message: str).
        """
        safe_id = _sanitize_task_id(task_id)
        worktree_path = self.get_worktree_path(safe_id)

        if require_ci and not self.is_ci_passed(safe_id):
            return False, (
                f"Merge rejected for task '{task_id}': automated CI verification has not passed. "
                "Zero direct mutations allowed to production branches without verified test passage."
            )

        # Get worktree's branch
        res_branch = self._run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=worktree_path)
        if res_branch.returncode != 0:
            return False, f"Failed to determine branch for worktree '{task_id}': {res_branch.stderr}"
        source_branch = res_branch.stdout.strip()

        # Merge branch into target branch in main repository
        msg = commit_message or f"Merge verified task workspace {task_id} ({source_branch}) into {target_branch}"
        merge_args = ["merge", source_branch, "-m", msg]
        if squash:
            merge_args = ["merge", "--squash", source_branch]

        # Switch main repo to target branch if not already on it
        current_main_branch = self._run_git(["rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()
        if current_main_branch != target_branch:
            res_checkout = self._run_git(["checkout", target_branch])
            if res_checkout.returncode != 0:
                return False, f"Failed to checkout target branch '{target_branch}': {res_checkout.stderr}"

        res_merge = self._run_git(merge_args)
        if res_merge.returncode != 0:
            return False, f"Merge conflict or failure during merge of '{source_branch}' into '{target_branch}': {res_merge.stderr}"

        if squash:
            res_commit = self._run_git(["commit", "-m", msg])
            if res_commit.returncode != 0:
                return False, f"Failed to commit squashed merge: {res_commit.stderr}"

        return True, f"Successfully merged '{source_branch}' into '{target_branch}' with CI passage."

    def cleanup_worktree(
        self,
        task_id: str,
        force: bool = False,
        delete_branch: bool = False,
    ) -> bool:
        """
        Safely removes the worktree, purges residual files and stale locks, and runs git worktree prune.
        """
        safe_id = _sanitize_task_id(task_id)
        worktree_path = self.get_worktree_path(safe_id)
        target_branch = f"worktree/{safe_id}"

        # 1. Clean stale locks before operation
        self._clean_stale_locks(force=False)

        # 2. Attempt git worktree remove
        if worktree_path.exists():
            cmd = ["worktree", "remove", str(worktree_path)]
            if force:
                cmd.append("--force")

            res = self._run_git(cmd)
            if res.returncode != 0 and force:
                # Force remove on disk if git command failed
                try:
                    shutil.rmtree(str(worktree_path), ignore_errors=True)
                except Exception:
                    pass

        # 3. If directory is still present on disk, ensure cleanup
        if worktree_path.exists():
            try:
                shutil.rmtree(str(worktree_path), ignore_errors=True)
            except Exception:
                pass

        # 4. Prune worktrees in git
        self._run_git(["worktree", "prune"])

        # 5. Delete branch if requested
        if delete_branch and self.is_branch_exists(target_branch):
            self._run_git(["branch", "-D", target_branch])

        # 6. Clear CI memory
        self._ci_results.pop(safe_id, None)

        return not worktree_path.exists()

    def cleanup_all_worktrees(self, force: bool = False, delete_branches: bool = False) -> int:
        """Cleans up all managed worktrees under .worktrees/."""
        if not self.worktrees_dir.exists():
            return 0

        active_trees = self.list_worktrees()
        cleaned_count = 0

        for wt in active_trees:
            if wt.get("is_managed"):
                task_id = wt.get("task_id")
                if task_id:
                    if self.cleanup_worktree(task_id, force=force, delete_branch=delete_branches):
                        cleaned_count += 1

        # Also scan directory directly for any untracked folders
        try:
            for item in self.worktrees_dir.iterdir():
                if item.is_dir():
                    self.cleanup_worktree(item.name, force=force, delete_branch=delete_branches)
                    cleaned_count += 1
        except Exception:
            pass

        self._run_git(["worktree", "prune"])
        return cleaned_count


# Global / package convenience functions matching PROJECT.md interface contract
_default_manager: Optional[GitWorktreeManager] = None


def get_default_worktree_manager() -> GitWorktreeManager:
    global _default_manager
    if _default_manager is None:
        _default_manager = GitWorktreeManager()
    return _default_manager


def create_worktree(task_id: str, branch_name: Optional[str] = None) -> str:
    """Creates an isolated git worktree in .worktrees/<task_id>."""
    return get_default_worktree_manager().create_worktree(task_id=task_id, branch_name=branch_name)


def cleanup_worktree(task_id: str, force: bool = False) -> bool:
    """Safely removes the worktree and cleans stale locks."""
    return get_default_worktree_manager().cleanup_worktree(task_id=task_id, force=force)
