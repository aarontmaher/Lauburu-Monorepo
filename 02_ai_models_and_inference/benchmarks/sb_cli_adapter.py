#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
SWE-bench CLI (sb-cli) Programmatic Adapter & Execution Engine
================================================================================
Subsystem: 02_ai_models_and_inference/benchmarks/sb_cli_adapter.py
Version: 1.0.0-SWEBENCH-CLI-CANONICAL
Lauburu Mesh Ecosystem — 2026

Integrates official SWE-bench CLI (sb-cli) for:
1. API key lifecycle: generation, verification, and quota monitoring.
2. Prediction formatting & submission across subsets (`swe-bench-m`, `swe-bench_lite`, `swe-bench_verified`).
3. Automated polling, report fetching, and Obsidian Vault sync.
4. Seamless integration with `SweBenchHarness` and `EloPromotionGate`.
================================================================================
"""

import os
import sys
import json
import shutil
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union

# Path Resolution
MONOREPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = MONOREPO_ROOT / "04_data_and_memory"
DEFAULT_REPORTS_DIR = MONOREPO_ROOT / "02_ai_models_and_inference" / "reports" / "sb_cli_reports"
DEFAULT_PREDICTIONS_DIR = DATA_DIR / "swe_bench_predictions"

DEFAULT_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("SbCliAdapter")


class SbCliAdapter:
    """
    Python wrapper and execution engine for the SWE-bench CLI (`sb-cli`).
    """

    SUPPORTED_SUBSETS = ("swe-bench-m", "swe-bench_lite", "swe-bench_verified")

    def __init__(
        self,
        cli_path: Optional[str] = None,
        api_key: Optional[str] = None,
        reports_dir: Optional[Union[str, Path]] = None,
    ):
        self.cli_path = cli_path or self.resolve_cli_executable()
        self.api_key = api_key or os.environ.get("SWEBENCH_API_KEY")
        self.reports_dir = Path(reports_dir) if reports_dir else DEFAULT_REPORTS_DIR
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def resolve_cli_executable(cls) -> str:
        """Finds `sb-cli` executable on system PATH or local user paths."""
        found = shutil.which("sb-cli")
        if found:
            return found
        user_local = Path.home() / ".local" / "bin" / "sb-cli"
        if user_local.exists():
            return str(user_local)
        return "sb-cli"

    @classmethod
    def is_installed(cls) -> bool:
        """Checks if `sb-cli` is accessible and functional."""
        try:
            exe = cls.resolve_cli_executable()
            res = subprocess.run(
                [exe, "--help"],
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
            return res.returncode == 0
        except Exception:
            return False

    def _run_command(self, args: List[str], env: Optional[Dict[str, str]] = None, timeout: int = 180) -> Tuple[int, str, str]:
        """Executes `sb-cli` with given arguments."""
        cmd = [self.cli_path] + args
        exec_env = os.environ.copy()
        if self.api_key:
            exec_env["SWEBENCH_API_KEY"] = self.api_key
        if env:
            exec_env.update(env)

        logger.info(f"Executing sb-cli command: {' '.join(cmd)}")
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                env=exec_env,
                timeout=timeout,
            )
            return proc.returncode, proc.stdout, proc.stderr
        except subprocess.TimeoutExpired:
            logger.error(f"sb-cli command timed out after {timeout}s: {' '.join(cmd)}")
            return -1, "", f"Command timed out after {timeout}s"
        except Exception as e:
            logger.error(f"Error executing sb-cli: {e}")
            return -1, "", str(e)

    # ─────────────────────────────────────────────────────────────────────────
    # 1. API KEY LIFECYCLE & QUOTAS
    # ─────────────────────────────────────────────────────────────────────────

    def generate_api_key(self, email: str) -> Dict[str, Any]:
        """
        Request a new API key from SWE-bench for the given email address.
        """
        code, stdout, stderr = self._run_command(["gen-api-key", email])
        success = (code == 0)
        return {
            "success": success,
            "returncode": code,
            "stdout": stdout.strip(),
            "stderr": stderr.strip(),
            "message": "API key requested. Check your email for verification code." if success else stderr.strip() or stdout.strip(),
        }

    def verify_api_key(self, verification_code: str, api_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Verify an API key using the verification code received via email.
        """
        args = ["verify-api-key", verification_code]
        if api_key:
            args.extend(["--api_key", api_key])
        code, stdout, stderr = self._run_command(args)
        success = (code == 0)
        return {
            "success": success,
            "returncode": code,
            "stdout": stdout.strip(),
            "stderr": stderr.strip(),
            "message": "API key verified successfully." if success else stderr.strip() or stdout.strip(),
        }

    def get_quotas(self, api_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Get remaining quota counts for authorized subsets and splits.
        """
        args = ["get-quotas"]
        if api_key:
            args.extend(["--api_key", api_key])
        code, stdout, stderr = self._run_command(args)
        return {
            "success": code == 0,
            "returncode": code,
            "stdout": stdout.strip(),
            "stderr": stderr.strip(),
        }

    # ─────────────────────────────────────────────────────────────────────────
    # 2. PREDICTION FORMATTING & SUBMISSION
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def format_predictions_file(
        predictions: Dict[str, Dict[str, str]],
        output_path: Union[str, Path]
    ) -> Path:
        """
        Formats a dictionary of predictions to canonical SWE-bench JSON structure:
        {
            "instance_id_1": {
                "model_patch": "...",
                "model_name_or_path": "..."
            }
        }
        """
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(predictions, f, indent=2)
        return path

    @staticmethod
    def validate_predictions_file(
        filepath: Union[str, Path]
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Validates that a predictions file strictly follows the canonical SWE-bench schema:
        {
            "<instance_id>": {
                "model_patch": str,
                "model_name_or_path": str
            }
        }
        Returns:
            (is_valid: bool, status_message: str, details: Dict[str, Any])
        """
        path = Path(filepath)
        if not path.exists():
            return False, f"Predictions file does not exist: {filepath}", {}

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON syntax in {filepath}: {e}", {}
        except Exception as e:
            return False, f"Failed reading {filepath}: {e}", {}

        if not isinstance(data, dict):
            return False, f"Root JSON element must be a dictionary mapping instance_ids to prediction objects, got {type(data).__name__}", {}

        validated_count = 0
        instances = []
        for inst_id, entry in data.items():
            if not isinstance(entry, dict):
                return False, f"Entry for instance '{inst_id}' must be an object/dict, got {type(entry).__name__}", {"failed_instance": inst_id}
            if "model_patch" not in entry:
                return False, f"Entry for instance '{inst_id}' is missing required field 'model_patch'", {"failed_instance": inst_id}
            if not isinstance(entry["model_patch"], str):
                return False, f"Field 'model_patch' for '{inst_id}' must be a string, got {type(entry['model_patch']).__name__}", {"failed_instance": inst_id}
            if "model_name_or_path" not in entry:
                return False, f"Entry for instance '{inst_id}' is missing required field 'model_name_or_path'", {"failed_instance": inst_id}
            if not isinstance(entry["model_name_or_path"], str):
                return False, f"Field 'model_name_or_path' for '{inst_id}' must be a string, got {type(entry['model_name_or_path']).__name__}", {"failed_instance": inst_id}

            validated_count += 1
            instances.append(inst_id)

        return True, f"Valid canonical predictions schema with {validated_count} instances", {
            "count": validated_count,
            "instances": instances
        }

    @staticmethod
    def export_from_harness_results(
        harness_results: List[Dict[str, Any]],
        model_name_or_path: str,
        output_path: Union[str, Path],
        patch_map: Optional[Dict[str, str]] = None,
    ) -> Path:
        """
        Converts `SweBenchHarness` evaluation results into standard `preds.json`.
        """
        preds = {}
        for r in harness_results:
            inst_id = r.get("instance_id")
            if not inst_id:
                continue
            patch = (patch_map.get(inst_id) if patch_map else None) or r.get("patch") or r.get("sample_patch", "")
            preds[inst_id] = {
                "model_patch": patch,
                "model_name_or_path": model_name_or_path or r.get("model_name", "lauburu-model"),
            }
        return SbCliAdapter.format_predictions_file(preds, output_path)

    def submit_predictions(
        self,
        subset: str,
        split: str,
        predictions_path: Union[str, Path],
        run_id: Optional[str] = None,
        instance_ids: Optional[List[str]] = None,
        output_dir: Optional[Union[str, Path]] = None,
        overwrite: bool = False,
        gen_report: bool = True,
        verify_submission: bool = True,
        wait_for_evaluation: bool = True,
        api_key: Optional[str] = None,
        timeout: int = 600,
    ) -> Dict[str, Any]:
        """
        Submits predictions file to SWE-bench API.
        """
        pred_path_obj = Path(predictions_path)
        if not pred_path_obj.exists():
            raise FileNotFoundError(f"Predictions file not found: {predictions_path}")

        out_dir = Path(output_dir) if output_dir else self.reports_dir
        out_dir.mkdir(parents=True, exist_ok=True)

        args = [
            "submit",
            subset,
            split,
            "--predictions_path", str(pred_path_obj.resolve()),
            "--output_dir", str(out_dir.resolve()),
            "--overwrite", "1" if overwrite else "0",
            "--gen_report", "1" if gen_report else "0",
            "--verify_submission", "1" if verify_submission else "0",
            "--wait_for_evaluation", "1" if wait_for_evaluation else "0",
        ]

        if run_id:
            args.extend(["--run_id", run_id])
        if instance_ids:
            args.extend(["--instance_ids", ",".join(instance_ids)])
        if api_key:
            args.extend(["--api_key", api_key])

        code, stdout, stderr = self._run_command(args, timeout=timeout)
        return {
            "success": code == 0,
            "returncode": code,
            "run_id": run_id,
            "subset": subset,
            "split": split,
            "output_dir": str(out_dir),
            "stdout": stdout.strip(),
            "stderr": stderr.strip(),
        }

    # ─────────────────────────────────────────────────────────────────────────
    # 3. REPORTS, RUN MANAGEMENT & QUERIES
    # ─────────────────────────────────────────────────────────────────────────

    def get_report(
        self,
        subset: str,
        split: str,
        run_id: str,
        output_dir: Optional[Union[str, Path]] = None,
        overwrite: bool = False,
        api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Retrieves the evaluation report for an existing run ID.
        """
        out_dir = Path(output_dir) if output_dir else self.reports_dir
        out_dir.mkdir(parents=True, exist_ok=True)

        args = [
            "get-report",
            subset,
            split,
            run_id,
            "--output_dir", str(out_dir.resolve()),
            "--overwrite", "1" if overwrite else "0",
        ]
        if api_key:
            args.extend(["--api_key", api_key])

        code, stdout, stderr = self._run_command(args)
        return {
            "success": code == 0,
            "returncode": code,
            "subset": subset,
            "split": split,
            "run_id": run_id,
            "output_dir": str(out_dir),
            "stdout": stdout.strip(),
            "stderr": stderr.strip(),
        }

    def list_runs(self, subset: str, split: str, api_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Lists all existing run IDs for the specified subset and split.
        """
        args = ["list-runs", subset, split]
        if api_key:
            args.extend(["--api-key", api_key])

        code, stdout, stderr = self._run_command(args)
        return {
            "success": code == 0,
            "returncode": code,
            "subset": subset,
            "split": split,
            "stdout": stdout.strip(),
            "stderr": stderr.strip(),
        }

    def delete_run(self, subset: str, split: str, run_id: str, api_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Deletes a specific run by ID.
        """
        args = ["delete-run", subset, split, run_id]
        if api_key:
            args.extend(["--api-key", api_key])

        code, stdout, stderr = self._run_command(args)
        return {
            "success": code == 0,
            "returncode": code,
            "subset": subset,
            "split": split,
            "run_id": run_id,
            "stdout": stdout.strip(),
            "stderr": stderr.strip(),
        }


if __name__ == "__main__":
    print(f"sb-cli installed: {SbCliAdapter.is_installed()}")
    print(f"sb-cli path: {SbCliAdapter.resolve_cli_executable()}")
    adapter = SbCliAdapter()
    if os.environ.get("SWEBENCH_API_KEY"):
        quotas = adapter.get_quotas()
        print("Quotas:", quotas)
    else:
        print("SWEBENCH_API_KEY not set. Ready for API key configuration.")
