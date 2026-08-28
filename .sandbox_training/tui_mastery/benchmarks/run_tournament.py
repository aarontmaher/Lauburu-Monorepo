#!/usr/bin/env python3
"""Run Red vs Blue TUI Mastery Tournament overseen by Abliterated Llama 70B."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
SANDBOX_DIR = REPO_ROOT / ".sandbox_training" / "tui_mastery"
sys.path.insert(0, str(SANDBOX_DIR))

from referee.abliterated_referee import AbliteratedReferee


def main() -> None:
    parser = argparse.ArgumentParser(description="Run TUI Mastery Benchmark Tournament")
    parser.add_argument(
        "--state-path",
        type=Path,
        default=REPO_ROOT / "04_data_and_memory" / "data" / "cloud_api_quota_state.json",
        help="Path to cloud_api_quota_state.json",
    )
    args = parser.parse_args()

    referee = AbliteratedReferee(sandbox_dir=SANDBOX_DIR)
    results = referee.run_full_tournament(args.state_path)

    print(f"\n=======================================================")
    print(f"TOURNAMENT CONCLUDED — OVERSEEN BY {referee.NAME}")
    print(f"=======================================================")
    print(f"Integrity Mode : {results['integrity_mode']}")
    print(f"Winner         : {results['winner']['framework']}")
    print(f"Specialist     : {results['winner']['specialist']}")
    print(f"Composite Score: {results['winner']['composite_score']}")
    print(f"NPU Bonus Hours: {results['winner']['bonus_npu_hours']} hrs")
    print(f"Promotion Path : {results['winner']['promotion_target']}")
    print(f"=======================================================\n")


if __name__ == "__main__":
    main()
