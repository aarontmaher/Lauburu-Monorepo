import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Add app to path if necessary
APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from kinematics.tracker import process_video
from movesense_prep.schema import MovesenseSession
from vla.qwen_client import GrapplingVLAClient

INBOX_DIR = APP_DIR / "inbox"
PROCESSED_DIR = APP_DIR / "processed"
REPORTS_DIR = APP_DIR / "reports"
OBSIDIAN_REPORT_DIR = APP_DIR.parent.parent / "obsidian_vault" / "04_ANALYTICS"


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def download_youtube_to_inbox(url: str) -> str:
    """Download a YouTube video into the inbox folder using uvx yt-dlp."""
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[*] Downloading YouTube video into inbox: {url}")
    out_tmpl = str(INBOX_DIR / "%(id)s_%(title).40s.%(ext)s")
    cmd = [
        "uvx",
        "yt-dlp",
        "--js-runtimes",
        "node",
        "--merge-output-format",
        "mp4",
        "-o",
        out_tmpl,
        url,
    ]
    subprocess.run(cmd, check=True)
    mp4s = sorted(INBOX_DIR.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not mp4s:
        raise RuntimeError(f"Failed to locate downloaded MP4 in {INBOX_DIR}")
    return str(mp4s[0])


def analyze_video(video_input: str, move_to_processed: bool = False) -> dict:
    if video_input.startswith("http://") or video_input.startswith("https://"):
        video_path = download_youtube_to_inbox(video_input)
    else:
        video_path = video_input

    if not os.path.exists(video_path):
        print(f"[!] Error: Video file not found: {video_path}")
        sys.exit(1)

    video_p = Path(video_path)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    OBSIDIAN_REPORT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n[*] Starting 3D Grappling Kinematics & VLA Analysis for: {video_p.name}")
    print("[*] Step 1: Extracting 3D World Landmarks (meters) & Joint Angles via Google MediaPipe...")
    annotated_video, kinematic_json_path, frames_b64, kinematic_summary = process_video(str(video_p), max_vla_frames=6)

    print("[*] Step 2: Preparing Phase 2 Movesense Telemetry Fusion...")
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    session = MovesenseSession(
        session_id=f"grapple_{video_p.stem[:16]}",
        start_time_iso=now_iso,
        sample_rate_hz=512,
    )
    print(f"    [+] Initialized Movesense IMU Schema (Session: {session.session_id})")

    print("[*] Step 3: Dispatching 3D World Kinematics + Keyframes to TB4 VLA Pipeline...")
    vla_client = GrapplingVLAClient()
    vla_result = vla_client.analyze_tactics(
        frames_base64=frames_b64,
        kinematic_data=kinematic_summary,
        video_title=video_p.stem,
    )

    # Compute Tri-Proof SHA256 & byte counts
    ann_bytes = os.path.getsize(annotated_video)
    ann_sha = sha256_file(annotated_video)
    json_bytes = os.path.getsize(kinematic_json_path)
    json_sha = sha256_file(kinematic_json_path)

    report_md = f"""# 🥋 3D Grappling Kinematics & TB4 VLA Tactical Report: `{video_p.stem}`

- **Timestamp (UTC)**: `{now_iso}`
- **Source Video**: `{video_p.name}` (`{kinematic_summary['resolution']}` @ `{kinematic_summary['fps']} fps`, `{kinematic_summary['duration_sec']}s`, `{kinematic_summary['total_frames']}` frames)
- **3D Poses Extracted**: `{kinematic_summary['frames_with_3d_pose']}/{kinematic_summary['total_frames']}` frames (`{kinematic_summary['frames_with_two_grapplers']}` dual-athlete frames)
- **Stage 1 Multimodal 3D VLA**: `{vla_result['vla_model_used']}` via `{vla_result['vla_endpoint_used']}`
- **Stage 2 Biomechanical Synthesis**: `{vla_result['reasoning_model_used']}` via `{vla_result['reasoning_endpoint_used']}`
- **Inference Duration**: `{vla_result['elapsed_sec']}s`

---

## 1. Stage 1: Qwen2.5-VL Multimodal 3D Spatial Grounding
{vla_result['visual_grounding'] or '_No visual grounding returned._'}

---

## 2. Stage 2: 3D Biomechanical & Tactical Breakdown
{vla_result['tactical_report'] or '_No tactical report returned._'}

---

## 3. Sampled 3D MediaPipe World Landmarks (meters) & Joint Angles (degrees)
```json
{json.dumps(kinematic_summary['keyframe_3d_kinematics'][:3], indent=2)}
```

---

## 4. Tri-Proof Artifact Verification (Rule 1 §2)
- **Annotated Video**: `{annotated_video}` (`{ann_bytes}` bytes, SHA256: `{ann_sha}`)
- **3D Kinematic JSON**: `{kinematic_json_path}` (`{json_bytes}` bytes, SHA256: `{json_sha}`)
"""

    report_path = REPORTS_DIR / f"{video_p.stem}_3d_vla_report.md"
    report_path.write_text(report_md, encoding="utf-8")

    obsidian_copy = OBSIDIAN_REPORT_DIR / f"GRAPPLING_3D_VLA_{video_p.stem[:32].replace(' ', '_')}.md"
    obsidian_copy.write_text(report_md, encoding="utf-8")

    print("\n=================================================================")
    print("🥋 3D VLA TACTICAL & BIOMECHANICAL REPORT")
    print("=================================================================")
    print(f"[+] Stage 1 VLA Model:       {vla_result['vla_model_used']} ({vla_result['vla_endpoint_used']})")
    print(f"[+] Stage 2 Synthesis Model: {vla_result['reasoning_model_used']} ({vla_result['reasoning_endpoint_used']})")
    print("-----------------------------------------------------------------")
    print(vla_result["tactical_report"] or vla_result["visual_grounding"])
    print("=================================================================")
    print(f"[✓] Annotated 3D video: {annotated_video} ({ann_bytes} bytes)")
    print(f"[✓] 3D Kinematic JSON:  {kinematic_json_path} ({json_bytes} bytes)")
    print(f"[✓] Markdown Report:    {report_path}")
    print(f"[✓] Obsidian Vault:     {obsidian_copy}")

    if move_to_processed and video_p.parent == INBOX_DIR:
        dest = PROCESSED_DIR / video_p.name
        shutil.move(str(video_p), str(dest))
        print(f"[✓] Moved processed source video to: {dest}")

    return {
        "annotated_video": annotated_video,
        "kinematic_json": kinematic_json_path,
        "report_path": str(report_path),
        "obsidian_path": str(obsidian_copy),
        "vla_result": vla_result,
    }


def run_batch(inbox_dir: Path):
    inbox_dir.mkdir(parents=True, exist_ok=True)
    videos = sorted(
        [
            p
            for p in inbox_dir.iterdir()
            if p.suffix.lower() in (".mp4", ".mov", ".mkv", ".webm") and not p.stem.endswith("_annotated")
        ]
    )
    if not videos:
        print(f"[*] No unprocessed videos found in {inbox_dir}")
        return
    print(f"[*] Found {len(videos)} video(s) in batch queue: {[v.name for v in videos]}")
    for v in videos:
        analyze_video(str(v), move_to_processed=True)


def run_watcher(inbox_dir: Path, poll_sec: float = 5.0, max_cycles: Optional[int] = None):
    print(f"[*] Autonomous 3D Grappling Watcher started on: {inbox_dir} (poll={poll_sec}s)")
    cycles = 0
    while True:
        run_batch(inbox_dir)
        cycles += 1
        if max_cycles is not None and cycles >= max_cycles:
            break
        time.sleep(poll_sec)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Zero-Mock 3D Grappling Kinematics & TB4 VLA Batch Pipeline")
    parser.add_argument("video", nargs="?", help="Path to input video file or YouTube URL")
    parser.add_argument("--batch", action="store_true", help="Batch-process all videos in the inbox folder")
    parser.add_argument("--watch", action="store_true", help="Run continuous folder-watcher daemon on inbox folder")
    parser.add_argument("--inbox", default=str(INBOX_DIR), help="Custom inbox folder path")
    args = parser.parse_args()

    if args.watch:
        run_watcher(Path(args.inbox))
    elif args.batch:
        run_batch(Path(args.inbox))
    elif args.video:
        analyze_video(args.video)
    else:
        parser.print_help()
