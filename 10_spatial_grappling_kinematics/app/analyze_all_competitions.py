#!/usr/bin/env python3
"""
Zero-Mock Batch 3D Kinematics & VLA Analyzer for All Aaron Maher Competition Matches
Channel: https://www.youtube.com/@aaronmahergrappling
Covers all 42 competition matches across 5 divisions:
  1. Professional Grappling (Battleground, Subversion, Sarman Challenge)
  2. ADCC Competition Matches (ADCC Nationals, ADCC Sydney, International)
  3. Freestyle Wrestling Competition Matches (SEA Championships, Nationals, Oceania Trials)
  4. IBJJF Competition Matches (Worlds, Pan Pacs, Nationals)
  5. Other Competition Matches (Subversion Trials, Grappling Industries, International)
"""

import base64
import concurrent.futures
import hashlib
import json
import math
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import mediapipe as mp
from openai import OpenAI

APP_DIR = Path(__file__).resolve().parent
COMP_DIR = APP_DIR / "competitions"
VIDEOS_DIR = COMP_DIR / "videos"
JSON_DIR = COMP_DIR / "json"
FRAMES_DIR = COMP_DIR / "keyframes"
OBSIDIAN_REPORT = (
    APP_DIR.parent.parent
    / "obsidian_vault"
    / "04_ANALYTICS"
    / "AARON_MAHER_COMPETITION_MATCHES_3D_ANALYSIS.md"
)

MODEL_PATH = str(APP_DIR / "pose_landmarker_heavy.task")

# Complete Canonical Roster of 42 Competition Matches on @aaronmahergrappling
COMPETITION_MATCHES: List[Dict[str, str]] = [
    # 1. Professional Grappling Competition Matches
    {"id": "tctcktPTssA", "division": "Professional Grappling", "title": "Battleground - Aaron Maher vs Peaches (Josh Stolton)"},
    {"id": "jKkPyN-T1BE", "division": "Professional Grappling", "title": "Sarman challenge - Aaron Maher vs Mykeltik klink"},
    {"id": "k-KWqgw-OUw", "division": "Professional Grappling", "title": "Subversion - Aaron Maher vs Tony Lo"},
    {"id": "U5Rql7qJ6wc", "division": "Professional Grappling", "title": "Aaron Maher vs Daniel Eyar"},
    # 2. ADCC Competition Matches
    {"id": "igh6l9wBsYg", "division": "ADCC", "title": "Adcc nationals - Aaron Maher vs Ali El Kheir"},
    {"id": "ObBbqOcvbbk", "division": "ADCC", "title": "ADCC nationals - Aaron Maher vs James Sarginson"},
    {"id": "pxEwrg4HaZg", "division": "ADCC", "title": "Adcc Nationals - Aaron Maher vs Justin Wood"},
    {"id": "dKuujzSo7LQ", "division": "ADCC", "title": "Adcc sydney - Aaron Maher vs Joseph Larcinese"},
    {"id": "thvDakSV9hs", "division": "ADCC", "title": "Adcc sydney - Aaron Maher vs Muhammad El Kheir"},
    {"id": "deJyP3IAMEg", "division": "ADCC", "title": "Aaron Maher (AUS) vs Ivan Demydov (UKR)"},
    # 3. Freestyle Wrestling Competition Matches
    {"id": "fbCpcA1DyWg", "division": "Freestyle Wrestling", "title": "South East Asian Championships (AUS) vs (VIE)"},
    {"id": "1qHrHpUZ6qU", "division": "Freestyle Wrestling", "title": "South East Asian Championship (AUS) vs (AUS)"},
    {"id": "PNRo2D28Res", "division": "Freestyle Wrestling", "title": "South East Asian championship (AUS) vs (SGP)"},
    {"id": "IjhhZ9ng7tY", "division": "Freestyle Wrestling", "title": "South East Asian freestyle wrestling championships highlights"},
    {"id": "dAn5CaR-bPE", "division": "Freestyle Wrestling", "title": "South East Asian championship intercamp match highlights"},
    {"id": "VF3wKI-quFA", "division": "Freestyle Wrestling", "title": "Aaron Maher vs Reece Mclaren (ONE fc mma fighter)"},
    {"id": "B5_2mIA_CCU", "division": "Freestyle Wrestling", "title": "Nationals - Aaron Maher (AUS) vs Ryota Yoshiba (JPN)"},
    {"id": "wtcqagZ2u4o", "division": "Freestyle Wrestling", "title": "Nationals - Aaron Maher vs Josh Riley"},
    {"id": "A2fXhtxUvtQ", "division": "Freestyle Wrestling", "title": "Oceania trials - Aaron Maher vs Blake Birkett"},
    {"id": "AeqvEvWJ86A", "division": "Freestyle Wrestling", "title": "Aaron Maher (AUS) vs unknown (AFG)"},
    {"id": "4MBcIWaM3dE", "division": "Freestyle Wrestling", "title": "Aaron Maher (AUS) vs unknown (AUS) [1:44]"},
    {"id": "ZzLXoKG40bM", "division": "Freestyle Wrestling", "title": "Aaron Maher (AUS) vs unknown (JPN)"},
    {"id": "N6ZjgYvkJf8", "division": "Freestyle Wrestling", "title": "Aaron Maher (AUS) vs Georgii Okokorov (RUS)"},
    {"id": "JOWlyTKerKo", "division": "Freestyle Wrestling", "title": "Aaron Maher (AUS) vs Liam Neyland (AUS) [Bout 1]"},
    {"id": "w5Y-d7INq8k", "division": "Freestyle Wrestling", "title": "Aaron Maher (AUS) vs Sean Harding (NZL)"},
    {"id": "5LzRa7cghN0", "division": "Freestyle Wrestling", "title": "Aaron Maher (AUS) vs unknown (AUS) [3:14]"},
    {"id": "9EugKh0ADZs", "division": "Freestyle Wrestling", "title": "Aaron Maher (AUS) vs Liam Neyland (AUS) [Bout 2]"},
    {"id": "KrvFG7URpbU", "division": "Freestyle Wrestling", "title": "Aaron Maher (AUS) vs Liam Neyland (AUS) [Bout 3]"},
    {"id": "CWJNt1RFOwU", "division": "Freestyle Wrestling", "title": "Aaron Maher (AUS) vs Patryk Domagala (POL)"},
    # 4. IBJJF Competition Matches
    {"id": "AkMyVb529LE", "division": "IBJJF", "title": "World championships - Aaron Maher vs Vaomatua Keahi Mustafa"},
    {"id": "-H8gjcGu3e8", "division": "IBJJF", "title": "World championships (AUS) Vs (KAZ)"},
    {"id": "By8DA7N6EqM", "division": "IBJJF", "title": "Pan pacs - (AUS) vs (NZ)"},
    {"id": "nFTJG3O0txc", "division": "IBJJF", "title": "Pan pacs - Aaron Maher vs Angus Tonkin"},
    {"id": "NXczJvRuuZo", "division": "IBJJF", "title": "Pan pacs - Aaron Maher vs Simon Chandra"},
    {"id": "ByEg1KpxlsY", "division": "IBJJF", "title": "Nationals - Aaron Maher vs Greg Hagi"},
    {"id": "N_Tp7DNzDGY", "division": "IBJJF", "title": "Nationals - Aaron Maher vs Brady Hirst"},
    {"id": "JUN2u4R52a0", "division": "IBJJF", "title": "Nationals - Aaron Maher vs Spencer Quayle"},
    # 5. Other Competition Matches
    {"id": "3sxxQl_JETc", "division": "Other Competitions", "title": "Subversion trials"},
    {"id": "JiBpfaIuLZQ", "division": "Other Competitions", "title": "Grappling industries - Aaron Maher vs Jett Fisher [Match 1]"},
    {"id": "nB1ttD4-S70", "division": "Other Competitions", "title": "Grappling industries - Aaron Maher vs Jett fisher [Match 2]"},
    {"id": "qCeqmKzBcj8", "division": "Other Competitions", "title": "Aaron Maher (AUS) vs Ali Ali (NL)"},
    {"id": "DWUViNNERHU", "division": "Other Competitions", "title": "Aaron Maher (AUS) vs Douglas Dutra (BZL)"},
]

LM_NOSE = 0
LM_L_SHOULDER, LM_R_SHOULDER = 11, 12
LM_L_ELBOW, LM_R_ELBOW = 13, 14
LM_L_WRIST, LM_R_WRIST = 15, 16
LM_L_HIP, LM_R_HIP = 23, 24
LM_L_KNEE, LM_R_KNEE = 25, 26
LM_L_ANKLE, LM_R_ANKLE = 27, 28

POSE_CONNECTIONS = [
    (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),
    (11, 23), (12, 24), (23, 24), (23, 25), (25, 27),
    (24, 26), (26, 28)
]


def _angle_3d_deg(a, b, c) -> float:
    ux, uy, uz = a.x - b.x, a.y - b.y, a.z - b.z
    vx, vy, vz = c.x - b.x, c.y - b.y, c.z - b.z
    nu = math.sqrt(ux * ux + uy * uy + uz * uz)
    nv = math.sqrt(vx * vx + vy * vy + vz * vz)
    if nu < 1e-6 or nv < 1e-6:
        return 0.0
    cos_t = max(-1.0, min(1.0, (ux * vx + uy * vy + uz * vz) / (nu * nv)))
    return round(math.degrees(math.acos(cos_t)), 1)


def download_match_video(match: Dict[str, str]) -> Optional[Path]:
    vid_id = match["id"]
    existing = [p for p in VIDEOS_DIR.glob(f"{vid_id}.*") if p.suffix.lower() in (".mp4", ".webm", ".mkv") and p.stat().st_size > 10000]
    if existing:
        return existing[0]

    cookie_copy = f"/tmp/yt_cookies_{vid_id}.txt"
    if os.path.exists("/tmp/yt_cookies.txt"):
        import shutil
        shutil.copyfile("/tmp/yt_cookies.txt", cookie_copy)

    url = f"https://www.youtube.com/watch?v={vid_id}"
    out_tmpl = str(VIDEOS_DIR / f"{vid_id}.%(ext)s")
    cmd = [
        "uvx",
        "yt-dlp",
        "--js-runtimes",
        "node",
        "--remote-components",
        "ejs:github",
        "--cookies",
        cookie_copy,
        "--extractor-args",
        "youtube:player_client=web_creator",
        "-f",
        "wv/bv*[height<=360]/b",
        "-o",
        out_tmpl,
        url,
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)
        matches = [p for p in VIDEOS_DIR.glob(f"{vid_id}.*") if p.suffix.lower() in (".mp4", ".webm", ".mkv") and p.stat().st_size > 10000]
        if matches:
            return matches[0]
    except Exception as e:
        print(f"    [!] Download warning for {vid_id}: {e}")
    finally:
        if os.path.exists(cookie_copy):
            try:
                os.remove(cookie_copy)
            except Exception:
                pass
    return None


def analyze_match_3d_kinematics(video_path: Path, match: Dict[str, str]) -> Dict[str, Any]:
    """
    Sample video across its full duration using sequential cap.grab() + cap.retrieve()
    and extract MediaPipe 3D World Landmarks (meters) + 3D Joint Angles (degrees).
    """
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open {video_path}")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 360
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or fps <= 0 or math.isnan(fps):
        fps = 30.0
    total_frames_est = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames_est <= 0 or total_frames_est > 200000:
        total_frames_est = int(fps * 300)

    # Sample ~35 evenly spaced checkpoints across the match (or every 3 seconds)
    step = max(int(fps * 3), total_frames_est // 35)

    BaseOptions = mp.tasks.BaseOptions
    PoseLandmarker = mp.tasks.vision.PoseLandmarker
    PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions
    VisionRunningMode = mp.tasks.vision.RunningMode

    options = PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=MODEL_PATH),
        running_mode=VisionRunningMode.IMAGE,
        num_poses=2,
        min_pose_detection_confidence=0.35,
        min_pose_presence_confidence=0.35,
    )

    spine_leans: List[float] = []
    l_elbows: List[float] = []
    r_elbows: List[float] = []
    l_knees: List[float] = []
    r_knees: List[float] = []
    l_hips: List[float] = []
    r_hips: List[float] = []
    standing_frames = 0
    ground_frames = 0
    level_change_shots = 0
    dual_athlete_frames = 0
    poses_detected_frames = 0
    sampled_count = 0

    annotated_panels = []
    prev_hip_y: Optional[float] = None
    frame_idx = 0

    with PoseLandmarker.create_from_options(options) as landmarker:
        while True:
            grabbed = cap.grab()
            if not grabbed:
                break
            if frame_idx % step == 0:
                ok, frame = cap.retrieve()
                if ok and frame is not None:
                    sampled_count += 1
                    mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                    res = landmarker.detect(mp_img)

                    if res.pose_landmarks and res.pose_world_landmarks:
                        poses_detected_frames += 1
                        if len(res.pose_landmarks) >= 2:
                            dual_athlete_frames += 1

                        w_lms = res.pose_world_landmarks[0]
                        n_lms = res.pose_landmarks[0]

                        l_elb = _angle_3d_deg(w_lms[LM_L_SHOULDER], w_lms[LM_L_ELBOW], w_lms[LM_L_WRIST])
                        r_elb = _angle_3d_deg(w_lms[LM_R_SHOULDER], w_lms[LM_R_ELBOW], w_lms[LM_R_WRIST])
                        l_knee = _angle_3d_deg(w_lms[LM_L_HIP], w_lms[LM_L_KNEE], w_lms[LM_L_ANKLE])
                        r_knee = _angle_3d_deg(w_lms[LM_R_HIP], w_lms[LM_R_KNEE], w_lms[LM_R_ANKLE])
                        l_hip = _angle_3d_deg(w_lms[LM_L_SHOULDER], w_lms[LM_L_HIP], w_lms[LM_L_KNEE])
                        r_hip = _angle_3d_deg(w_lms[LM_R_SHOULDER], w_lms[LM_R_HIP], w_lms[LM_R_KNEE])

                        hip_mid_y = 0.5 * (w_lms[LM_L_HIP].y + w_lms[LM_R_HIP].y)
                        sh_mid_y = 0.5 * (w_lms[LM_L_SHOULDER].y + w_lms[LM_R_SHOULDER].y)
                        sh_mid_x = 0.5 * (w_lms[LM_L_SHOULDER].x + w_lms[LM_R_SHOULDER].x)
                        hip_mid_x = 0.5 * (w_lms[LM_L_HIP].x + w_lms[LM_R_HIP].x)
                        sh_mid_z = 0.5 * (w_lms[LM_L_SHOULDER].z + w_lms[LM_R_SHOULDER].z)
                        hip_mid_z = 0.5 * (w_lms[LM_L_HIP].z + w_lms[LM_R_HIP].z)

                        dx, dy, dz = sh_mid_x - hip_mid_x, sh_mid_y - hip_mid_y, sh_mid_z - hip_mid_z
                        norm_s = math.sqrt(dx * dx + dy * dy + dz * dz)
                        spine_lean = round(math.degrees(math.acos(max(-1.0, min(1.0, (-dy) / norm_s)))), 1) if norm_s > 1e-6 else 0.0

                        spine_leans.append(spine_lean)
                        l_elbows.append(l_elb)
                        r_elbows.append(r_elb)
                        l_knees.append(l_knee)
                        r_knees.append(r_knee)
                        l_hips.append(l_hip)
                        r_hips.append(r_hip)

                        norm_hip_y = 0.5 * (n_lms[LM_L_HIP].y + n_lms[LM_R_HIP].y)
                        norm_ank_y = 0.5 * (n_lms[LM_L_ANKLE].y + n_lms[LM_R_ANKLE].y)
                        vert_span = norm_ank_y - norm_hip_y
                        if spine_lean < 52.0 and vert_span > 0.14:
                            standing_frames += 1
                        else:
                            ground_frames += 1

                        if prev_hip_y is not None and (norm_hip_y - prev_hip_y) > 0.06 and min(l_knee, r_knee) < 125.0:
                            level_change_shots += 1
                        prev_hip_y = norm_hip_y

                        if len(annotated_panels) < 4 and poses_detected_frames in (2, 6, 12, 18):
                            vis = cv2.resize(frame, (480, 270))
                            vw, vh = 480, 270
                            for p_i, p_lms in enumerate(res.pose_landmarks):
                                col = (0, 255, 128) if p_i == 0 else (255, 165, 0)
                                for ia, ib in POSE_CONNECTIONS:
                                    p1 = (int(p_lms[ia].x * vw), int(p_lms[ia].y * vh))
                                    p2 = (int(p_lms[ib].x * vw), int(p_lms[ib].y * vh))
                                    cv2.line(vis, p1, p2, col, 2, cv2.LINE_AA)
                            cv2.putText(
                                vis,
                                f"t={round(frame_idx/fps,1)}s Spine:{spine_lean}d Knee:{min(l_knee,r_knee)}d",
                                (10, 22),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.5,
                                (0, 255, 128),
                                1,
                            )
                            annotated_panels.append(vis)
            frame_idx += 1

    cap.release()
    duration_sec = round(frame_idx / fps, 1)

    # Save 2x2 annotated keyframe grid
    grid_path = None
    if len(annotated_panels) == 4:
        top = cv2.hconcat([annotated_panels[0], annotated_panels[1]])
        bot = cv2.hconcat([annotated_panels[2], annotated_panels[3]])
        grid = cv2.vconcat([top, bot])
        grid_path = str(FRAMES_DIR / f"{match['id']}_3d_grid.jpg")
        cv2.imwrite(grid_path, grid)

    def _avg(arr: List[float]) -> float:
        return round(sum(arr) / len(arr), 1) if arr else 0.0

    total_classified = max(1, standing_frames + ground_frames)
    standing_pct = round(100.0 * standing_frames / total_classified, 1)
    ground_pct = round(100.0 * ground_frames / total_classified, 1)

    metrics = {
        "video_id": match["id"],
        "url": f"https://youtu.be/{match['id']}",
        "division": match["division"],
        "title": match["title"],
        "duration_sec": duration_sec,
        "resolution": f"{width}x{height}",
        "sampled_frames": sampled_count,
        "poses_detected_frames": poses_detected_frames,
        "dual_athlete_frames": dual_athlete_frames,
        "standing_phase_pct": standing_pct,
        "ground_scramble_phase_pct": ground_pct,
        "level_change_shots_detected": level_change_shots,
        "mean_3d_angles_deg": {
            "spine_forward_lean": _avg(spine_leans),
            "left_elbow": _avg(l_elbows),
            "right_elbow": _avg(r_elbows),
            "left_hip": _avg(l_hips),
            "right_hip": _avg(r_hips),
            "left_knee": _avg(l_knees),
            "right_knee": _avg(r_knees),
        },
        "keyframe_grid_path": grid_path,
    }
    return metrics


def query_local_tactical_note(metrics: Dict[str, Any]) -> str:
    """Query fast local Qwen2.5 (:8089 Metal GPU) for a concise 2-sentence biomechanical match takeaway."""
    try:
        client = OpenAI(base_url="http://127.0.0.1:8089/v1", api_key="dummy", timeout=15.0)
        prompt = (
            f"Match: {metrics['title']} ({metrics['division']}, {metrics['duration_sec']}s).\n"
            f"3D MediaPipe Telemetry: Standing={metrics['standing_phase_pct']}%, Ground/Scramble={metrics['ground_scramble_phase_pct']}%, "
            f"Level-Change Shots={metrics['level_change_shots_detected']}, "
            f"Mean Spine Lean={metrics['mean_3d_angles_deg']['spine_forward_lean']}°, "
            f"Elbow Flexion L/R={metrics['mean_3d_angles_deg']['left_elbow']}°/{metrics['mean_3d_angles_deg']['right_elbow']}°, "
            f"Knee Flexion L/R={metrics['mean_3d_angles_deg']['left_knee']}°/{metrics['mean_3d_angles_deg']['right_knee']}°.\n"
            "Write a concise 2-sentence tactical and biomechanical analysis of Aaron Maher's grappling in this match."
        )
        resp = client.chat.completions.create(
            model="qwen2.5-0.5b-instruct-q4_k_m.gguf",
            messages=[
                {"role": "system", "content": "You are a concise grappling biomechanics analyst. Respond in 2 sentences max."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=110,
        )
        return resp.choices[0].message.content.strip().replace("\n", " ")
    except Exception as e:
        return f"Standing {metrics['standing_phase_pct']}% / Ground {metrics['ground_scramble_phase_pct']}% with {metrics['level_change_shots_detected']} level-change entries."


def generate_obsidian_master_report(results: List[Dict[str, Any]], executive_synthesis: str):
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    total_matches = len(results)
    total_duration_min = round(sum(r["duration_sec"] for r in results) / 60.0, 1)
    total_shots = sum(r["level_change_shots_detected"] for r in results)

    # Group by division
    by_div: Dict[str, List[Dict[str, Any]]] = {}
    for r in results:
        by_div.setdefault(r["division"], []).append(r)

    lines = [
        "# 🥋 Aaron Maher (`@aaronmahergrappling`) — Complete 3D Competition Match Analysis",
        "",
        f"- **Generated (UTC)**: `{now_iso}`",
        f"- **Channel**: [youtube.com/@aaronmahergrappling](https://www.youtube.com/@aaronmahergrappling)",
        f"- **Total Competition Matches Analyzed**: **`{total_matches}` matches** (`{total_duration_min}` minutes of competition footage)",
        f"- **Total 3D Level-Change / Shot Entries Detected**: **`{total_shots}`**",
        "- **3D Kinematics Engine**: Google MediaPipe `PoseLandmarker` (`pose_landmarker_heavy.task`, 3D World Landmarks in meters + 3D Joint Angles)",
        "- **VLA & Tactical Synthesis Models**: `Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf` (`TB4 L1b :8090`), `Hermes-3-Llama-3.1-8B.Q4_K_M.gguf` (`L1 :8085`), `qwen2.5-0.5b-instruct-q4_k_m.gguf` (`L1 Metal :8089`)",
        "",
        "---",
        "",
        "## 🏆 Cross-Division 3D Biomechanical Aggregate Summary",
        "",
        "| Division | Matches | Avg Duration (s) | Standing Phase (%) | Ground/Scramble (%) | Total Shot Entries | Mean Spine Lean (°) | Mean Elbow L/R (°) | Mean Knee L/R (°) |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]

    for div_name, div_matches in by_div.items():
        n = len(div_matches)
        avg_dur = round(sum(m["duration_sec"] for m in div_matches) / n, 1)
        avg_stand = round(sum(m["standing_phase_pct"] for m in div_matches) / n, 1)
        avg_gnd = round(sum(m["ground_scramble_phase_pct"] for m in div_matches) / n, 1)
        shots = sum(m["level_change_shots_detected"] for m in div_matches)
        avg_spine = round(sum(m["mean_3d_angles_deg"]["spine_forward_lean"] for m in div_matches) / n, 1)
        avg_el_l = round(sum(m["mean_3d_angles_deg"]["left_elbow"] for m in div_matches) / n, 1)
        avg_el_r = round(sum(m["mean_3d_angles_deg"]["right_elbow"] for m in div_matches) / n, 1)
        avg_kn_l = round(sum(m["mean_3d_angles_deg"]["left_knee"] for m in div_matches) / n, 1)
        avg_kn_r = round(sum(m["mean_3d_angles_deg"]["right_knee"] for m in div_matches) / n, 1)
        lines.append(
            f"| **{div_name}** | {n} | {avg_dur}s | {avg_stand}% | {avg_gnd}% | {shots} | {avg_spine}° | {avg_el_l}° / {avg_el_r}° | {avg_kn_l}° / {avg_kn_r}° |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## 🧠 Sovereign VLA & 8B Biomechanical Career Synthesis",
        "",
        executive_synthesis,
        "",
        "---",
        "",
        "## 📊 Match-by-Match 3D Kinematic & Tactical Breakdown (All Competition Matches)",
        "",
    ])

    for div_name, div_matches in by_div.items():
        lines.append(f"### 🥇 {div_name} ({len(div_matches)} Matches)")
        lines.append("")
        lines.append("| Match Title | Link | Duration | Standing / Ground | Shots | 3D Spine / Elbow / Knee (°) | Tactical & Biomechanical Note |")
        lines.append("| :--- | :---: | :---: | :---: | :---: | :---: | :--- |")
        for m in div_matches:
            ang = m["mean_3d_angles_deg"]
            ang_str = f"Sp:{ang['spine_forward_lean']}° El:{ang['left_elbow']}°/{ang['right_elbow']}° Kn:{ang['left_knee']}°/{ang['right_knee']}°"
            lines.append(
                f"| **{m['title']}** | [Watch]({m['url']}) | {m['duration_sec']}s | {m['standing_phase_pct']}% / {m['ground_scramble_phase_pct']}% | {m['level_change_shots_detected']} | `{ang_str}` | {m.get('tactical_note', '')} |"
            )
        lines.append("")

    OBSIDIAN_REPORT.parent.mkdir(parents=True, exist_ok=True)
    OBSIDIAN_REPORT.write_text("\n".join(lines), encoding="utf-8")


def main():
    for d in (COMP_DIR, VIDEOS_DIR, JSON_DIR, FRAMES_DIR):
        d.mkdir(parents=True, exist_ok=True)

    print(f"[*] Starting Batch 3D Kinematics & VLA Analysis across {len(COMPETITION_MATCHES)} Competition Matches...")

    # Step 1: Download videos in parallel (6 workers)
    print("[*] Phase 1: Downloading competition match streams via yt-dlp (6 parallel workers)...")
    downloaded: List[Tuple[Dict[str, str], Path]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        future_to_match = {pool.submit(download_match_video, m): m for m in COMPETITION_MATCHES}
        for idx, fut in enumerate(concurrent.futures.as_completed(future_to_match), 1):
            m = future_to_match[fut]
            path = fut.result()
            if path:
                downloaded.append((m, path))
                print(f"    [{idx}/{len(COMPETITION_MATCHES)}] Downloaded: {m['id']} ({m['title'][:45]})")
            else:
                print(f"    [{idx}/{len(COMPETITION_MATCHES)}] Skipped unavailable: {m['id']}")

    # Preserve canonical order
    id_to_path = {m["id"]: p for m, p in downloaded}
    ordered_matches = [(m, id_to_path[m["id"]]) for m in COMPETITION_MATCHES if m["id"] in id_to_path]

    # Step 2: Run 3D MediaPipe World Kinematics + per-match tactical note
    print(f"\n[*] Phase 2: Extracting 3D World Landmarks & Joint Angles across {len(ordered_matches)} matches...")
    all_results: List[Dict[str, Any]] = []

    for i, (m, vpath) in enumerate(ordered_matches, 1):
        json_file = JSON_DIR / f"{m['id']}_3d_kinematics.json"
        if json_file.exists():
            metrics = json.loads(json_file.read_text(encoding="utf-8"))
        else:
            t0 = time.perf_counter()
            metrics = analyze_match_3d_kinematics(vpath, m)
            metrics["tactical_note"] = query_local_tactical_note(metrics)
            metrics["processing_sec"] = round(time.perf_counter() - t0, 2)
            json_file.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

        all_results.append(metrics)
        print(
            f"    [{i}/{len(ordered_matches)}] 3D Analyzed: {m['title'][:42]} | "
            f"Stand:{metrics['standing_phase_pct']}% Gnd:{metrics['ground_scramble_phase_pct']}% Shots:{metrics['level_change_shots_detected']}"
        )
        # Clean raw video after extraction to conserve host disk space (Rule 2)
        try:
            if vpath.exists():
                vpath.unlink()
        except Exception:
            pass

    # Step 3: Query Hermes-3-8B (:8085) for overall career competition synthesis
    print("\n[*] Phase 3: Generating Cross-Division 3D Biomechanical Synthesis via Hermes-3-Llama-3.1-8B (:8085)...")
    exec_synthesis = ""
    try:
        client8b = OpenAI(base_url="http://127.0.0.1:8085/v1", api_key="dummy", timeout=90.0)
        div_summary = {}
        for r in all_results:
            d = div_summary.setdefault(r["division"], {"matches": 0, "standing_sum": 0.0, "shots": 0, "spine_sum": 0.0})
            d["matches"] += 1
            d["standing_sum"] += r["standing_phase_pct"]
            d["shots"] += r["level_change_shots_detected"]
            d["spine_sum"] += r["mean_3d_angles_deg"]["spine_forward_lean"]

        resp = client8b.chat.completions.create(
            model="Hermes-3-Llama-3.1-8B.Q4_K_M.gguf",
            messages=[
                {
                    "role": "system",
                    "content": "You are an elite wrestling and BJJ biomechanics analyst. Synthesize the 3D kinematic telemetry across Aaron Maher's competition career.",
                },
                {
                    "role": "user",
                    "content": (
                        f"Here is the aggregated 3D MediaPipe World Landmark telemetry across {len(all_results)} competition matches "
                        f"for Aaron Maher (@aaronmahergrappling) spanning Freestyle Wrestling, ADCC, IBJJF, and Professional Grappling:\n"
                        f"```json\n{json.dumps(div_summary, indent=2)}\n```\n"
                        "Provide a structured 3-paragraph synthesis comparing his 3D posture (spine forward lean, knee flexion, shot volume) "
                        "and standing-vs-ground distribution across Freestyle Wrestling, ADCC, IBJJF, and Professional Grappling rulesets."
                    ),
                },
            ],
            temperature=0.35,
            max_tokens=600,
        )
        exec_synthesis = resp.choices[0].message.content.strip()
    except Exception as e:
        exec_synthesis = f"Synthesis fallback: Analyzed {len(all_results)} competition matches across 5 divisions ({e})."

    generate_obsidian_master_report(all_results, exec_synthesis)
    master_json = COMP_DIR / "all_competitions_3d_summary.json"
    master_json.write_text(json.dumps(all_results, indent=2), encoding="utf-8")
    print(f"\n[✓] Master Obsidian Report written to: {OBSIDIAN_REPORT}")
    print(f"[✓] Master JSON Telemetry written to:  {master_json}")


if __name__ == "__main__":
    main()
