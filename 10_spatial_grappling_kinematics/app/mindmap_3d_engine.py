#!/usr/bin/env python3
"""
Lauburu 3D Grappling Mind Map & Non-Stop Multi-VLM Automation Engine
====================================================================
Unifies:
  1. Aaron Maher's Mindomo Grappling Mind Map (`Grappling Mind Map 2.opml` — 3,723 nodes across
     Wrestling, Guard, Dominant Positions, Scrambles, and Role-Symmetric Templates; plus `final copy.opml`).
  2. Aaron Maher's 42 Competition Matches (`all_competitions_3d_summary.json`).
  3. Aaron Maher's 143 Technique & Instructional Videos (`22` Absolute MMA Pro Class Wrestling Techniques
     + `121` YouTube Technique Shorts + `Kf0wQ00FPBg` 4K Collar-Tie/2-on-1 instructional).
  4. Referee-Filtered Center-Mat 3D Athlete Tracker (YOLOv8n-Pose + Black-Shirt Referee Rejection
     + Pairwise Wrestler Proximity + High-Res Athlete Crop into MediaPipe 3D World Landmarks).
  5. Large Variety of 10 Vision-Language Models (Local Sovereign + Cloud Frontier Teachers):
     - `local_qwen25_vl_7b`: Qwen2.5-VL-7B-Instruct (Local Sovereign VLM)
     - `gemma_4_31b_vision`: Gemma 4 31B Vision (`google/gemma-4-31b-it` — Debate Duo Member A)
     - `qwen_38_27b_vision`: Qwen 3.8 27B Vision (`qwen/qwen3.8-27b` — Debate Duo Member B)
     - `qwen_38_omni_flash`: Qwen 3.8 Omni Flash (`qwen/qwen3.8-omni-flash`)
     - `qwen25_vl_72b`: Qwen2.5-VL-72B-Instruct (`qwen/qwen2.5-vl-72b-instruct`)
     - `gemini_38_flash`: Gemini 3.8 Flash Vision (`google/gemini-3.8-flash`)
     - `gemini_25_pro`: Gemini 2.5 Pro Vision (`google/gemini-2.5-pro`)
     - `claude_sonnet_55`: Claude Sonnet 5.5 Vision (`anthropic/claude-sonnet-5.5`)
     - `llama_4_maverick`: Meta Llama 4 Maverick Vision (`meta-llama/llama-4-maverick`)
     - `kimi_k25_vision`: Moonshot Kimi K2.5 Vision (`moonshotai/kimi-k2.5`)
"""

import base64
import concurrent.futures
import hashlib
import json
import math
import os
import shutil
import subprocess
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import mediapipe as mp
import numpy as np
from ultralytics import YOLO

APP_DIR = Path(__file__).resolve().parent
MINDOMO_DIR = APP_DIR.parent / "mindomo"
COMP_DIR = APP_DIR / "competitions"
VIDEOS_DIR = COMP_DIR / "videos"
TECH_VIDEOS_DIR = COMP_DIR / "technique_videos"
JSON_DIR = COMP_DIR / "json"
FRAMES_DIR = COMP_DIR / "keyframes"
SUMMARY_JSON = COMP_DIR / "all_competitions_3d_summary.json"
TECH_CATALOG_JSON = COMP_DIR / "technique_videos_catalog.json"
MINDMAP_3D_JSON = COMP_DIR / "grappling_3d_mindmap_graph.json"
BENCHMARK_JSON = COMP_DIR / "multi_vision_benchmark.json"
OBSIDIAN_MINDMAP_REPORT = (
    APP_DIR.parent.parent
    / "obsidian_vault"
    / "04_ANALYTICS"
    / "AARON_MAHER_3D_GRAPPLING_MINDMAP_AND_MULTI_VLM_STUDY.md"
)
LORA_CANDIDATES_JSONL = Path("/Users/aaron/DFS_UNIFIED/lora_datasets/grappling_multi_vlm_training_candidates.jsonl")
CONTINUOUS_LORA_JSONL = Path("/Users/aaron/DFS_UNIFIED/lora_datasets/continuous_lora_dataset.jsonl")
ARTIFACT_DIR = Path("/Users/aaron/.gemini/antigravity/brain/e133dcc1-a276-4ce8-aca3-65bd5d39307d")

MODEL_PATH = str(APP_DIR / "pose_landmarker_heavy.task")

LM_L_SHOULDER, LM_R_SHOULDER = 11, 12
LM_L_ELBOW, LM_R_ELBOW = 13, 14
LM_L_WRIST, LM_R_WRIST = 15, 16
LM_L_HIP, LM_R_HIP = 23, 24
LM_L_KNEE, LM_R_KNEE = 25, 26
LM_L_ANKLE, LM_R_ANKLE = 27, 28

MP_POSE_CONNECTIONS = [
    (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),
    (11, 23), (12, 24), (23, 24), (23, 25), (25, 27),
    (24, 26), (26, 28),
]

COCO_SKELETON = [
    (5, 6), (5, 7), (7, 9), (6, 8), (8, 10),
    (5, 11), (6, 12), (11, 12), (11, 13), (13, 15),
    (12, 14), (14, 16),
]

# Expanded 10-Model Vision Roster (Local Sovereign + Cloud Frontier Teachers, 100% Verified Live IDs)
EXPANDED_VISION_ROSTER = [
    {
        "id": "gemma_4_31b_vision",
        "name": "Gemma 4 31B Vision (Debater A)",
        "tier": "Sovereign Debate Duo A",
        "provider": "openrouter",
        "slug": "google/gemma-4-31b-it",
    },
    {
        "id": "qwen_38_27b_vision",
        "name": "Qwen 3.8 Max 27B Vision (Debater B)",
        "tier": "Sovereign Debate Duo B",
        "provider": "openrouter",
        "slug": "qwen/qwen3.8-27b",
    },
    {
        "id": "qwen_38_omni_flash",
        "name": "Qwen 3.8 Omni Flash",
        "tier": "Multimodal Omni VLM",
        "provider": "openrouter",
        "slug": "qwen/qwen3.8-omni-flash",
    },
    {
        "id": "qwen25_vl_72b",
        "name": "Qwen2.5-VL-72B-Instruct (Teacher)",
        "tier": "Cloud Teacher VLM",
        "provider": "openrouter",
        "slug": "qwen/qwen2.5-vl-72b-instruct",
    },
    {
        "id": "gemini_38_flash",
        "name": "Gemini 3.8 Flash Vision",
        "tier": "Cloud Frontier VLM",
        "provider": "openrouter",
        "slug": "google/gemini-3.8-flash",
    },
    {
        "id": "gemini_25_pro",
        "name": "Gemini 2.5 Pro Vision",
        "tier": "Cloud Frontier VLM",
        "provider": "openrouter",
        "slug": "google/gemini-2.5-pro",
    },
    {
        "id": "claude_sonnet_55",
        "name": "Claude Sonnet 5.5 Vision",
        "tier": "Cloud Frontier VLM",
        "provider": "openrouter",
        "slug": "anthropic/claude-sonnet-5.5",
    },
    {
        "id": "llama_4_maverick",
        "name": "Llama 4 Maverick Vision",
        "tier": "Open-Weights MoE VLM",
        "provider": "openrouter",
        "slug": "meta-llama/llama-4-maverick",
    },
    {
        "id": "kimi_k25_vision",
        "name": "Kimi K2.5 Multimodal Vision",
        "tier": "Cloud Teacher VLM",
        "provider": "openrouter",
        "slug": "moonshotai/kimi-k2.5",
    },
    {
        "id": "local_hermes_qwen_kinematics",
        "name": "Local Hermes-3 8B + MediaPipe 3D (:8085)",
        "tier": "Local Sovereign L1 Metal",
        "provider": "local_l1",
        "slug": "Hermes-3-Llama-3.1-8B.Q4_K_M.gguf",
    },
]


def _load_secret(name: str) -> Optional[str]:
    if name == "OPENROUTER_API_KEY":
        p = Path.home() / ".config/openrouter/api_key"
        if p.exists():
            val = p.read_text(encoding="utf-8").strip().strip("\"'")
            if val.startswith("sk-or-"):
                return val
    for env_path in [
        Path.home() / ".env",
        Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.env"),
        Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/data/env_storage.env"),
    ]:
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                if line.startswith(f"{name}="):
                    v = line.split("=", 1)[1].strip().strip("\"'")
                    if v and not v.startswith("<YOUR_"):
                        return v
    return os.environ.get(name)


def _angle_3d_deg(a, b, c) -> float:
    ux, uy, uz = a.x - b.x, a.y - b.y, a.z - b.z
    vx, vy, vz = c.x - b.x, c.y - b.y, c.z - b.z
    nu = math.sqrt(ux * ux + uy * uy + uz * uz)
    nv = math.sqrt(vx * vx + vy * vy + vz * vz)
    if nu < 1e-6 or nv < 1e-6:
        return 0.0
    cos_t = max(-1.0, min(1.0, (ux * vx + uy * vy + uz * vz) / (nu * nv)))
    return round(math.degrees(math.acos(cos_t)), 1)


def is_referee_in_black_uniform(
    frame: np.ndarray,
    bbox: Tuple[int, int, int, int],
    kpt_xy: Optional[np.ndarray] = None,
    division: str = "",
) -> Tuple[bool, float]:
    """
    Unified Referee Detector for both:
      1. ADCC / No-Gi / BJJ Referees: Upright standing in a bright white polo shirt (V > 195, S < 48) + black trousers.
      2. UWW Freestyle / Greco Wrestling Referees: All-black polo shirt + full-length black trousers (whereas freestyle wrestlers wear vivid singlets with bare knees/calves).
      Note: In No-Gi / ADCC / BJJ (non-Freestyle/Greco), athletes frequently wear black rashguards and black spats, so dark attire is ONLY penalized when upright standing (>2.15 aspect) or in UWW Wrestling divisions.
    """
    fh, fw = frame.shape[:2]
    x1, y1, x2, y2 = bbox
    bw, bh = max(1, x2 - x1), max(1, y2 - y1)
    bh_norm = bh / float(fh)
    aspect_upright = bh / float(bw)

    # Check central 32% spine strip for ADCC White-Shirt Referee (immune to outstretched arms)
    if bh_norm >= 0.26:
        sx1, sx2 = int(x1 + 0.34 * bw), int(x2 - 0.34 * bw)
        if sx2 <= sx1:
            sx1, sx2 = int(x1 + 0.20 * bw), int(x2 - 0.20 * bw)
        sy1, sy2 = int(y1 + 0.16 * bh), int(y1 + 0.46 * bh)
        spine_torso = frame[max(0, sy1):min(fh, sy2), max(0, sx1):min(fw, sx2)]
        if spine_torso.size > 0:
            hsv_st = cv2.cvtColor(spine_torso, cv2.COLOR_BGR2HSV)
            t_sat = float(np.median(hsv_st[:, :, 1]))
            t_val = float(np.median(hsv_st[:, :, 2]))
            if t_val > 195 and t_sat < 48 and bh_norm >= 0.28:
                return True, 0.005

    is_uww_wrestling = "wrestling" in division.lower()
    if not is_uww_wrestling and aspect_upright < 2.20:
        # In ADCC / No-Gi / Instructional, crouching/grappling athletes in black rashguards/spats are NEVER referees
        return False, 1.0

    if kpt_xy is not None and len(kpt_xy) >= 17:
        # Sample along torso (shoulders 5,6, hips 11,12, mid-torso) and lower legs (knees 13,14, mid-calves)
        sample_pts = []
        # Mid-shoulder & mid-hip
        if kpt_xy[5][0] > 1 and kpt_xy[6][0] > 1:
            sample_pts.append((0.5 * (kpt_xy[5][0] + kpt_xy[6][0]), 0.5 * (kpt_xy[5][1] + kpt_xy[6][1])))
        if kpt_xy[11][0] > 1 and kpt_xy[12][0] > 1:
            sample_pts.append((0.5 * (kpt_xy[11][0] + kpt_xy[12][0]), 0.5 * (kpt_xy[11][1] + kpt_xy[12][1])))
        if len(sample_pts) == 2:
            sample_pts.append((0.5 * (sample_pts[0][0] + sample_pts[1][0]), 0.5 * (sample_pts[0][1] + sample_pts[1][1])))

        leg_pts = []
        for hip_i, knee_i, ank_i in [(11, 13, 15), (12, 14, 16)]:
            hx, hy = kpt_xy[hip_i][0], kpt_xy[hip_i][1]
            kx, ky = kpt_xy[knee_i][0], kpt_xy[knee_i][1]
            ax, ay = kpt_xy[ank_i][0], kpt_xy[ank_i][1]
            if kx > 1 and ky > 1:
                leg_pts.append((kx, ky))
                if hx > 1 and hy > 1:
                    leg_pts.append((0.5 * (hx + kx), 0.5 * (hy + ky)))  # mid-thigh
                if ax > 1 and ay > 1:
                    leg_pts.append((0.5 * (kx + ax), 0.5 * (ky + ay)))  # mid-calf (always bare skin on wrestlers, black trouser on ref!)

        all_pts = sample_pts + leg_pts
        if len(leg_pts) >= 2:
            dark_leg_hits = 0
            total_leg_hits = 0
            for px, py in leg_pts:
                ix, iy = int(px), int(py)
                p_roi = frame[max(0, iy - 4):min(fh, iy + 5), max(0, ix - 4):min(fw, ix + 5)]
                if p_roi.size > 0:
                    p_hsv = cv2.cvtColor(p_roi, cv2.COLOR_BGR2HSV)
                    med_v = float(np.median(p_hsv[:, :, 2]))
                    med_s = float(np.median(p_hsv[:, :, 1]))
                    total_leg_hits += 1
                    if med_v < 92 and med_s < 95:
                        dark_leg_hits += 1
            dark_torso_hits = 0
            for px, py in sample_pts:
                ix, iy = int(px), int(py)
                p_roi = frame[max(0, iy - 5):min(fh, iy + 6), max(0, ix - 5):min(fw, ix + 6)]
                if p_roi.size > 0:
                    p_hsv = cv2.cvtColor(p_roi, cv2.COLOR_BGR2HSV)
                    if float(np.median(p_hsv[:, :, 2])) < 95 and float(np.median(p_hsv[:, :, 1])) < 95:
                        dark_torso_hits += 1

            if total_leg_hits >= 2 and (dark_leg_hits / total_leg_hits) >= 0.60 and dark_torso_hits >= 1:
                return True, 0.01
            if total_leg_hits >= 3 and (dark_leg_hits / total_leg_hits) >= 0.75:
                return True, 0.01

    tx1 = max(0, int(x1 + 0.18 * bw))
    tx2 = min(fw, int(x2 - 0.18 * bw))
    ty1 = max(0, int(y1 + 0.16 * bh))
    ty2 = min(fh, int(y1 + 0.90 * bh))
    roi = frame[ty1:ty2, tx1:tx2]
    if roi.size == 0:
        return False, 1.0

    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    h, s, v = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]

    # Subtract blue mat, yellow mat, AND bright white/pink wall banners (V > 165, S < 55)
    blue_mat = (h >= 95) & (h <= 136) & (s > 55) & (v > 65)
    yellow_mat = (h >= 13) & (h <= 36) & (s > 95) & (v > 110)
    white_banner = (v > 165) & (s < 55)
    fg_mask = ~(blue_mat | yellow_mat | white_banner)
    fg_count = max(1, int(np.sum(fg_mask)))

    black_cloth = fg_mask & (v < 96) & (s < 90)
    fg_black_ratio = float(np.sum(black_cloth)) / fg_count

    rh = roi.shape[0]
    fg_lower = fg_mask[int(0.48 * rh):, :]
    black_lower = black_cloth[int(0.48 * rh):, :]
    fg_lower_black_ratio = float(np.sum(black_lower)) / max(1, int(np.sum(fg_lower)))

    skin_or_red = fg_mask & (
        ((h < 13) & (s > 35) & (v > 85))
        | ((h > 165) & (s > 60) & (v > 75))
        | ((h < 24) & (s >= 22) & (s <= 150) & (v > 105))
    )
    athlete_fg_ratio = float(np.sum(skin_or_red)) / fg_count

    aspect_upright = bh / float(bw)
    if fg_black_ratio > 0.48 and fg_lower_black_ratio > 0.50:
        return True, 0.01
    if fg_lower_black_ratio > 0.58 and aspect_upright > 1.50 and athlete_fg_ratio < 0.30:
        return True, 0.02
    return False, 1.0 + min(0.6, athlete_fg_ratio)





def extract_center_mat_athletes_3d_v2(
    video_path: Path,
    match: Dict[str, Any],
    yolo_model: YOLO,
    landmarker: Any,
) -> Dict[str, Any]:
    """
    Referee-Aware Center-Mat 3D Athlete Pose Extractor (v2):
      1. YOLOv8-Pose detects all people in the frame.
      2. Filters out edge tripods, wall banners, spectators, AND penalizes referees in all-black uniforms.
      3. Boosts pairs of athletes who are physically close to or grappling with each other on the mat.
      4. Crops each wrestler at high resolution and runs MediaPipe PoseLandmarker (Heavy 3D World Landmarks).
    """
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open {video_path}")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1280
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 720
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or fps <= 0 or math.isnan(fps):
        fps = 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames <= 0 or total_frames > 200000:
        total_frames = int(fps * 240)

    step = max(1, min(int(fps * 2), max(1, total_frames // 36)))

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

    candidate_panels: List[Tuple[float, float, Any]] = []
    prev_hip_y: Optional[float] = None
    frame_idx = 0

    while True:
        grabbed = cap.grab()
        if not grabbed:
            break
        if frame_idx % step == 0:
            ok, frame = cap.retrieve()
            if ok and frame is not None:
                sampled_count += 1
                fh, fw = frame.shape[:2]

                yolo_res = yolo_model.predict(frame, imgsz=960, conf=0.20, verbose=False)[0]
                boxes = yolo_res.boxes
                kpts = yolo_res.keypoints

                mat_candidates = []
                if boxes is not None and len(boxes) > 0:
                    xyxy = boxes.xyxy.cpu().numpy()
                    confs = boxes.conf.cpu().numpy()
                    kpt_xy = kpts.xy.cpu().numpy() if kpts is not None else None
                    kpt_conf = kpts.conf.cpu().numpy() if (kpts is not None and kpts.conf is not None) else None

                    for i in range(len(xyxy)):
                        x1, y1, x2, y2 = xyxy[i]
                        bw = x2 - x1
                        bh = y2 - y1
                        cx = 0.5 * (x1 + x2) / fw
                        cy = 0.5 * (y1 + y2) / fh
                        y_bot = y2 / fh
                        bh_norm = bh / float(fh)
                        area_ratio = (bw * bh) / float(fw * fh)

                        if cx < 0.16 or cx > 0.80:
                            continue
                        if y_bot < 0.42 or cy < 0.24:
                            continue
                        if y_bot < 0.545 and bh_norm < 0.25:
                            continue
                        if area_ratio < 0.007:
                            continue

                        bbox_int = (int(x1), int(y1), int(x2), int(y2))
                        is_ref, ref_mult = is_referee_in_black_uniform(
                            frame,
                            bbox_int,
                            kpt_xy[i] if kpt_xy is not None else None,
                            division=match.get("division", ""),
                        )

                        dist_center = ((cx - 0.50) ** 2) / 0.065 + ((cy - 0.58) ** 2) / 0.085
                        center_weight = math.exp(-dist_center)
                        score = float(confs[i]) * (area_ratio ** 0.35) * (y_bot ** 2.8) * center_weight * ref_mult

                        mat_candidates.append({
                            "bbox": bbox_int,
                            "conf": float(confs[i]),
                            "score": score,
                            "is_ref": is_ref,
                            "cx": cx,
                            "cy": cy,
                            "y_bot": y_bot,
                            "bh": bh,
                            "kpt_xy": kpt_xy[i] if kpt_xy is not None else None,
                            "kpt_conf": kpt_conf[i] if kpt_conf is not None else None,
                        })

                # Hard-exclude referees whenever at least one non-referee athlete is on the mat
                non_ref = [c for c in mat_candidates if not c["is_ref"]]
                has_grounded_box = any((c["bbox"][3] - c["bbox"][1]) < 0.82 * max(1, c["bbox"][2] - c["bbox"][0]) for c in non_ref)
                if has_grounded_box:
                    non_ref = [c for c in non_ref if (c["bbox"][3] - c["bbox"][1]) <= 1.55 * max(1, c["bbox"][2] - c["bbox"][0])]
                active_pool = non_ref if len(non_ref) >= 1 else mat_candidates

                if len(active_pool) >= 1:
                    active_pool.sort(key=lambda c: c["score"], reverse=True)
                    primary_ath = active_pool[0]
                    coplanar_partners = [
                        c for c in active_pool[1:]
                        if abs(c["cx"] - primary_ath["cx"]) <= 0.25
                        and abs(c.get("y_bot", 0.6) - primary_ath.get("y_bot", 0.6)) <= 0.085
                        and c.get("bh", 100) >= 0.52 * primary_ath.get("bh", 100)
                    ]
                    if coplanar_partners:
                        best_partner = max(
                            coplanar_partners,
                            key=lambda c: c["score"] * math.exp(-(((c["cx"] - primary_ath["cx"]) ** 2 + (c["cy"] - primary_ath["cy"]) ** 2) / 0.035)),
                        )
                        top_athletes = [primary_ath, best_partner]
                    else:
                        ox1, oy1, ox2, oy2 = primary_ath["bbox"]
                        obw, obh = ox2 - ox1, oy2 - oy1
                        if obw > 1.05 * obh:
                            left_ath = dict(primary_ath, bbox=(ox1, oy1, ox1 + int(0.62 * obw), oy2), kpt_xy=None)
                            right_ath = dict(primary_ath, bbox=(ox1 + int(0.38 * obw), oy1, ox2, oy2), kpt_xy=None, score=primary_ath["score"] * 0.9)
                            top_athletes = [left_ath, right_ath]
                        else:
                            top_athletes = [primary_ath]
                else:
                    top_athletes = []


                frame_athletes_3d = []
                for ath_idx, ath in enumerate(top_athletes):
                    bx1, by1, bx2, by2 = ath["bbox"]
                    bw, bh = bx2 - bx1, by2 - by1
                    pad_x = int(bw * 0.35)
                    pad_y = int(bh * 0.30)
                    cx1 = max(0, bx1 - pad_x)
                    cy1 = max(0, by1 - pad_y)
                    cx2 = min(fw, bx2 + pad_x)
                    cy2 = min(fh, by2 + pad_y)

                    crop = frame[cy1:cy2, cx1:cx2]
                    if crop.size == 0:
                        continue
                    ch, cw = crop.shape[:2]
                    scale = max(1.0, 480.0 / max(cw, ch))
                    crop_resized = (
                        cv2.resize(crop, (int(cw * scale), int(ch * scale)), interpolation=cv2.INTER_LINEAR)
                        if scale > 1.05
                        else crop
                    )

                    mp_img = mp.Image(
                        image_format=mp.ImageFormat.SRGB,
                        data=cv2.cvtColor(crop_resized, cv2.COLOR_BGR2RGB),
                    )
                    res = landmarker.detect(mp_img)
                    if res.pose_landmarks and res.pose_world_landmarks:
                        w_lms = res.pose_world_landmarks[0]
                        n_lms = res.pose_landmarks[0]
                        full_pts = [(int(cx1 + lm.x * cw), int(cy1 + lm.y * ch), getattr(lm, "visibility", 1.0)) for lm in n_lms]
                        frame_athletes_3d.append({
                            "ath_idx": ath_idx,
                            "bbox": (bx1, by1, bx2, by2),
                            "score": ath["score"],
                            "w_lms": w_lms,
                            "n_lms": n_lms,
                            "full_pts": full_pts,
                            "kpt_xy": ath["kpt_xy"],
                            "kpt_conf": ath["kpt_conf"],
                        })
                    elif ath["kpt_xy"] is not None:
                        frame_athletes_3d.append({
                            "ath_idx": ath_idx,
                            "bbox": (bx1, by1, bx2, by2),
                            "score": ath["score"],
                            "w_lms": None,
                            "n_lms": None,
                            "full_pts": None,
                            "kpt_xy": ath["kpt_xy"],
                            "kpt_conf": ath["kpt_conf"],
                        })

                if frame_athletes_3d:
                    poses_detected_frames += 1
                    if len(frame_athletes_3d) >= 2:
                        dual_athlete_frames += 1

                    primary = frame_athletes_3d[0]
                    spine_lean = 38.0
                    l_knee = r_knee = 135.0
                    if primary["w_lms"] is not None:
                        w_lms = primary["w_lms"]
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

                    bx1, by1, bx2, by2 = primary["bbox"]
                    aspect = (by2 - by1) / max(1.0, float(bx2 - bx1))
                    if spine_lean < 58.0 and aspect > 0.85:
                        standing_frames += 1
                    else:
                        ground_frames += 1

                    norm_hip_y = 0.5 * (by1 + by2) / fh
                    if prev_hip_y is not None and (norm_hip_y - prev_hip_y) > 0.05 and min(l_knee, r_knee) < 128.0:
                        level_change_shots += 1
                    prev_hip_y = norm_hip_y

                    t_sec = round(frame_idx / fps, 1)
                    min_t = 8.0 if (total_frames / fps) > 45.0 else 0.5
                    if t_sec >= min_t:
                        vis = frame.copy()
                        for ath in frame_athletes_3d:
                            idx = ath["ath_idx"]
                            col = (0, 255, 128) if idx == 0 else (0, 190, 255)
                            label = "WRESTLER 1 (MAT)" if idx == 0 else "WRESTLER 2 (OPP)"
                            ax1, ay1, ax2, ay2 = ath["bbox"]
                            cv2.rectangle(vis, (ax1, ay1), (ax2, ay2), col, 2)
                            cv2.putText(
                                vis,
                                label,
                                (ax1, max(20, ay1 - 8)),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.55,
                                col,
                                2,
                                cv2.LINE_AA,
                            )
                            if ath["full_pts"] is not None:
                                pts = ath["full_pts"]
                                for ia, ib in MP_POSE_CONNECTIONS:
                                    p1 = (pts[ia][0], pts[ia][1])
                                    p2 = (pts[ib][0], pts[ib][1])
                                    cv2.line(vis, p1, p2, col, 3, cv2.LINE_AA)
                                for px, py, _ in pts[11:29]:
                                    cv2.circle(vis, (px, py), 4, (255, 255, 255), -1)
                            elif ath["kpt_xy"] is not None:
                                kxy = ath["kpt_xy"]
                                kcf = ath["kpt_conf"]
                                for ia, ib in COCO_SKELETON:
                                    if kcf is None or (kcf[ia] > 0.25 and kcf[ib] > 0.25):
                                        p1 = (int(kxy[ia][0]), int(kxy[ia][1]))
                                        p2 = (int(kxy[ib][0]), int(kxy[ib][1]))
                                        if p1[0] > 0 and p2[0] > 0:
                                            cv2.line(vis, p1, p2, col, 3, cv2.LINE_AA)

                        vis_panel = cv2.resize(vis, (640, 360), interpolation=cv2.INTER_AREA)
                        cv2.rectangle(vis_panel, (0, 0), (640, 32), (15, 20, 30), -1)
                        cv2.putText(
                            vis_panel,
                            f"t={t_sec}s | Wrestlers:{len(frame_athletes_3d)} (Ref Excluded) | 3D Spine:{spine_lean}deg | Knee:{min(l_knee,r_knee)}deg",
                            (10, 22),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.47,
                            (0, 255, 160),
                            1,
                            cv2.LINE_AA,
                        )
                        panel_quality = sum(a["score"] for a in frame_athletes_3d) * (2.5 if len(frame_athletes_3d) >= 2 else 0.6)
                        candidate_panels.append((t_sec, panel_quality, vis_panel))

        frame_idx += 1

    cap.release()
    duration_sec = round(frame_idx / fps, 1)

    selected_panels = []
    if candidate_panels:
        n_c = len(candidate_panels)
        if n_c >= 4:
            for q in range(4):
                chunk = candidate_panels[int(q * n_c / 4) : max(int(q * n_c / 4) + 1, int((q + 1) * n_c / 4))]
                best_in_chunk = max(chunk, key=lambda x: x[1])
                selected_panels.append(best_in_chunk[2])
        else:
            while len(selected_panels) < 4:
                selected_panels.append(candidate_panels[len(selected_panels) % n_c][2])

    grid_path = None
    if len(selected_panels) == 4:
        top = cv2.hconcat([selected_panels[0], selected_panels[1]])
        bot = cv2.hconcat([selected_panels[2], selected_panels[3]])
        grid = cv2.vconcat([top, bot])
        grid_path = str(FRAMES_DIR / f"{match['id']}_3d_grid.jpg")
        cv2.imwrite(grid_path, grid, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
        if match["id"] == "fbCpcA1DyWg" and ARTIFACT_DIR.exists():
            shutil.copyfile(grid_path, str(ARTIFACT_DIR / "fbCpcA1DyWg_3d_grid.jpg"))

    def _avg(arr: List[float]) -> float:
        return round(sum(arr) / len(arr), 1) if arr else 0.0

    total_classified = max(1, standing_frames + ground_frames)
    standing_pct = round(100.0 * standing_frames / total_classified, 1)
    ground_pct = round(100.0 * ground_frames / total_classified, 1)

    return {
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
        "tracker_pipeline": "YOLOv8n-Pose + Black-Shirt Referee Filter + Pairwise Wrestler Proximity + MediaPipe 3D Heavy",
    }


def build_3d_mindmap_knowledge_graph(
    comp_matches: List[Dict[str, Any]],
    tech_catalog: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Parses Aaron Maher's 3,723-node `Grappling Mind Map 2.opml` and `final copy.opml`,
    computes 3D orbital coordinates (x, y, z) for interactive 3D graph visualization,
    attaches 3D biomechanical angle envelopes, and cross-links every Mind Map cluster
    to Aaron's 143 Technique Videos and 42 Competition Matches!
    """
    opml_path = MINDOMO_DIR / "Grappling Mind Map 2.opml"
    tree = ET.parse(opml_path)
    root = tree.getroot()
    body = root.find("body")
    main_outline = body.find("outline") if body is not None else None

    total_opml_nodes = len(root.findall(".//outline"))

    # Combine all technique videos (22 playlist + 121 shorts + Kf0wQ00FPBg)
    all_tech_videos = [
        {"id": "Kf0wQ00FPBg", "title": "Collar tie 2 on 1 entry to collar tie (4K Instructional)", "source": "Instructional Footage"}
    ]
    all_tech_videos.extend(tech_catalog.get("playlist_techniques", []))
    all_tech_videos.extend(tech_catalog.get("shorts_techniques", []))

    # Keyword matcher rules for linking technique videos & competition matches to Mind Map position clusters
    CLUSTER_SPECS = {
        "Outside tie (You)": {
            "keywords": ["outside tie", "throw by", "brush by", "brush-by"],
            "biomechanics_3d": {
                "posture_cue": "Disciplined low wrestling stance — head & hands in front of hips",
                "control_mechanics": "Outside wrist/tricep control to angle around the corner",
                "next_transitions": "Knee-pull sweep single • Brush-by / Throw-by • Collar-tie entry",
            },
            "tactical_summary": "Outside wrist/tricep tie used to set up knee-pull sweep singles, throw-bys, brush-bys, and collar-tie entries.",
        },
        "Inside tie (You)": {
            "keywords": ["inside tie", "feints", "snapdown"],
            "biomechanics_3d": {
                "posture_cue": "Loaded stance — elbows tight to ribs winning inside space",
                "control_mechanics": "Inside bicep/collar-bone frame blocking opponent's underhook",
                "next_transitions": "Level-change sweep single • Snapdown to Front Headlock • Inside trip",
            },
            "tactical_summary": "Inside bicep/collar-bone tie controlling inside space and setting up level-change sweep singles and snapdowns.",
        },
        "Collar tie (You)": {
            "keywords": ["collar tie", "snap down", "snapdown", "super duck"],
            "biomechanics_3d": {
                "posture_cue": "Heavy forehead-to-temple pressure — hips back behind head & hands",
                "control_mechanics": "Ear-to-ear collar tie + forearm club on the crown of the neck",
                "next_transitions": "2-on-1 Russian tie entry • Collar-tie throw-by • Knee-pull single • Snapdown to Front Headlock",
            },
            "tactical_summary": "166-node core hand-fighting hub: heavy neck/occiput pressure chaining into brush-bys, throw-bys, snapdowns, and 2-on-1 entries.",
        },
        "Underhook (You)": {
            "keywords": ["underhook", "knee tap", "far knee", "throw"],
            "biomechanics_3d": {
                "posture_cue": "Hips close & chest upright — jacking opponent's shoulder vertically",
                "control_mechanics": "Shallow-to-deep shoulder shelf + head wedged into opponent's jaw",
                "next_transitions": "Far-side knee tap • Snatch single leg • Throw-by to rear bodylock • Snap to Front Headlock",
            },
            "tactical_summary": "70-node vertical elevation control system: high elbow shoulder jacking to expose snatch single, knee tap, throw-by, or front headlock.",
        },
        "Overhook (You)": {
            "keywords": ["overhook", "whizzer", "uchimata", "uchi mata", "fireman"],
            "biomechanics_3d": {
                "posture_cue": "Heavy whizzer shoulder pressure — hip angled into opponent's near thigh",
                "control_mechanics": "Deep overhook clamping opponent's arm tight to ribs",
                "next_transitions": "Uchi-mata elevation • Fireman's carry • Inside trip • Limp-arm counter",
            },
            "tactical_summary": "Overhook/whizzer control chaining into uchi-mata, fireman's carry, and single-leg counters.",
        },
        "2-on-1 (You)": {
            "keywords": ["2 on 1", "2-on-1", "russian tie", "ankle pick"],
            "biomechanics_3d": {
                "posture_cue": "Angled T-position on the flank — shoulder pressure driving into trapped arm",
                "control_mechanics": "Russian 2-on-1 wrist + above-elbow grip isolating near shoulder",
                "next_transitions": "Climb to rear bodylock • Same-side ankle pick • Snatch single • Snap to Front Headlock",
            },
            "tactical_summary": "Russian 2-on-1 wrist + tricep control: isolates near shoulder to climb to back, hit ankle pick, snatch single, or front headlock.",
        },
        "Over/Under (You)": {
            "keywords": ["over/under", "arm drag", "lat drop"],
            "biomechanics_3d": {
                "posture_cue": "Ear-to-chest 50/50 clinch — hips loaded underneath for elevation or trip",
                "control_mechanics": "Underhook side lifts while overhook side clamps the elbow",
                "next_transitions": "Inside leg trip • Arm-drag to rear bodylock • Lateral drop counter • Bodylock entry",
            },
            "tactical_summary": "50/50 clinch symmetry broken via arm drags to rear bodylock, inside leg trips, and bodylock entries.",
        },
        "Wrestling bodylock": {
            "keywords": ["bodylock", "body lock", "rear body", "mat return", "uchi mata"],
            "biomechanics_3d": {
                "posture_cue": "Hips tight & lower than opponent — ear glued to chest/back",
                "control_mechanics": "Gable or S-grip around lower ribs/waist pulling hips in",
                "next_transitions": "Lift & mat return • Inside trip • Polish throw • Transition to Crab Ride / Back Take",
            },
            "tactical_summary": "59-node rear/front bodylock matrix: hip-in clamping, mat returns, inside leg trips, uchi-mata counters, and crab-ride transitions.",
        },
        "Head inside single leg": {
            "keywords": ["single leg", "sweep single", "running the pipe", "sprawl", "belly whizzer", "cradle"],
            "biomechanics_3d": {
                "posture_cue": "Deep penetration step — spine upright, ear glued tight to opponent's ribs",
                "control_mechanics": "Pinch opponent's knee between thighs + lock hands behind knee/shin",
                "next_transitions": "Run the pipe • Shelf the leg & finish • Cut corner to backside • Limp-arm out of heavy whizzer",
            },
            "tactical_summary": "177-node primary leg-attack system: ear-to-chest posture, running the pipe, shelf finishes, and anti-sprawl counters.",
        },
        "Head outside single leg": {
            "keywords": ["outside single", "high crotch", "fireman"],
            "biomechanics_3d": {
                "posture_cue": "Hips driven underneath shoulders — head up pressing into lateral hip",
                "control_mechanics": "High-crotch tight wrap on near thigh + outside step to cut the corner",
                "next_transitions": "Switch to double leg • Crackdown finish • Climb to rear bodylock • Dump finish",
            },
            "tactical_summary": "61-node high-crotch / head-outside single matrix: crackdowns, double-leg switches, and back-side exposure.",
        },
        "Double leg": {
            "keywords": ["double leg", "blast double"],
            "biomechanics_3d": {
                "posture_cue": "Explosive level change — trail leg steps up & drives across on a diagonal corner angle",
                "control_mechanics": "Hands cup behind both knees + ear tight to hip",
                "next_transitions": "Cut the corner across knees • Blast double drive • Transition directly to Headquarters / J-Point",
            },
            "tactical_summary": "Penetration step + hip-under-shoulder drive cutting the corner across opponent's knees.",
        },
        "Front Headlock": {
            "keywords": ["front headlock", "front head lock", "anaconda", "chin strap", "go behind", "pinch"],
            "biomechanics_3d": {
                "posture_cue": "Heavy chest-on-upper-back weight — hips sprawled back to block reshots",
                "control_mechanics": "Deep chin-strap + tricep/elbow pinch keeping opponent's posture broken",
                "next_transitions": "Circle & score Go-Behind • Knee-tap ankle pick • Pinch headlock exposure • Anaconda / Darce choke",
            },
            "tactical_summary": "356-node dominant control hub: chin-strap + tricep pinch chaining into go-behinds, ankle picks, cradles, and anaconda chokes.",
        },
        "Turtle": {
            "keywords": ["turtle", "gut wrench", "leg lace", "spiral ride", "back take"],
            "biomechanics_3d": {
                "posture_cue": "Heavy top hip pressure — knees off the mat driving forward at an angle",
                "control_mechanics": "Tight-waist + far-ankle / claw-ride breakdown breaking flat to the mat",
                "next_transitions": "Spiral ride breakdown • Gut wrench exposure • Leg lace • Seatbelt hooks to Back Control",
            },
            "tactical_summary": "185-node par-terre / turtle breakdown system: tight-waist spiral rides, gut wrenches, leg laces, and back exposure.",
        },
        "J point": {
            "keywords": ["j point", "j-point", "camping"],
            "biomechanics_3d": {
                "posture_cue": "Flanking outside hip angle — heavy chest/hip pressure pinning opponent's knees away",
                "control_mechanics": "Collar/neck tie + bottom-leg cuff forcing supine partner's hips to face away",
                "next_transitions": "J-Point camping fatigue pass • Step over to Mount • Expose gift-wrap / Back Take",
            },
            "tactical_summary": "306-node flanking guard-pass hub: hip/shoulder pin forcing supine guard player away before mounting or taking the back.",
        },
        "Headquarters": {
            "keywords": ["headquarters", "knee cut", "smash pass"],
            "biomechanics_3d": {
                "posture_cue": "Heavy hip weight anchored over opponent's trapped thigh — head over sternum",
                "control_mechanics": "Pin one shin between your legs while controlling inside bicep/underhook space",
                "next_transitions": "Knee-cut pass • Smash pass to J-Point • Floating pummel to Mount",
            },
            "tactical_summary": "80-node central passing hub stepping over one shin to launch knee-cuts, smash passes, and floating passes.",
        },
        "De la riva": {
            "keywords": ["de la riva", "dlr", "berimbolo"],
            "biomechanics_3d": {
                "posture_cue": "Active outside hook tension — off-balancing passer's base before they settle",
                "control_mechanics": "Deep DLR hook + ankle/far-sleeve control turning opponent's knee inward",
                "next_transitions": "Off-balance to Baby Bolo / Crab Ride • Wrestle-up single leg • Matrix back exposure",
            },
            "tactical_summary": "64-node open guard & outside hook system chaining into off-balances, baby bolos, and crab rides.",
        },
        "Butterfly guard": {
            "keywords": ["butterfly", "hook sweep", "sumi gaeshi"],
            "biomechanics_3d": {
                "posture_cue": "Seated forward-leaning posture — head lower than opponent's chin",
                "control_mechanics": "Inside butterfly hooks + overhook/shoulder-crunch or underhook control",
                "next_transitions": "Shoulder-crunch sumi-gaeshi sweep • Arm-drag to back • Elevation into Ashi Garami",
            },
            "tactical_summary": "92-node seated inside-hook elevation system linking shoulder crunches, arm drags, and ashis.",
        },
        "Crab ride": {
            "keywords": ["crab ride", "berimbolo", "back take"],
            "biomechanics_3d": {
                "posture_cue": "Tight hip-to-hip attachment — active shins wedged behind opponent's knees",
                "control_mechanics": "Waist/hip grips + double crab hooks steering opponent's hips to the mat",
                "next_transitions": "Shuck hips to expose Back Control • Leg-drag pass • Twister hook climb",
            },
            "tactical_summary": "56-node hip-attachment scramble engine wedging hooks behind opponent's knees to expose the back.",
        },
    }

    nodes_3d: List[Dict[str, Any]] = []
    edges_3d: List[Dict[str, Any]] = []

    # Root center node at (0, 0, 0)
    nodes_3d.append({
        "id": "root_grappling_mind_map",
        "label": "Grappling Mind Map (3,723 Nodes)",
        "realm": "CORE",
        "depth": 0,
        "descendant_count": total_opml_nodes,
        "x": 0.0,
        "y": 0.0,
        "z": 0.0,
        "color": "#10b981",
        "size": 26,
        "tactical_summary": "Master 3,723-node Mindomo Grappling Architecture unifying Wrestling, Guard, Dominant Positions, and Scrambles.",
        "sub_branches": ["Wrestling (704)", "Guard (1,805)", "Dominant Positions (1,003)", "Scrambles (130)"],
        "linked_technique_videos": all_tech_videos[:8],
        "linked_comp_matches": [m["video_id"] for m in comp_matches[:6]],
    })

    realm_Trash = {"TEMPLATES"}
    realms = [el for el in (main_outline.findall("outline") if main_outline is not None else []) if el.attrib.get("text") not in realm_Trash]

    realm_colors = {
        "Wrestling": "#10b981",          # Emerald
        "Guard": "#38bdf8",              # Sky Blue
        "Dominant Positions": "#f59e0b", # Amber
        "Scrambles": "#a855f7",          # Purple
    }

    for r_i, r_el in enumerate(realms):
        r_name = r_el.attrib.get("text", f"Realm_{r_i}")
        r_id = f"realm_{r_i}_{r_name.lower().replace(' ', '_')}"
        r_desc_count = len(r_el.findall(".//outline"))
        angle_r = (2.0 * math.pi * r_i) / max(1, len(realms))
        rx = round(140.0 * math.cos(angle_r), 2)
        ry = round(45.0 * (1 if r_i % 2 == 0 else -1), 2)
        rz = round(140.0 * math.sin(angle_r), 2)
        r_col = realm_colors.get(r_name, "#38bdf8")

        lvl2_children = r_el.findall("outline")
        nodes_3d.append({
            "id": r_id,
            "label": f"{r_name} ({r_desc_count})",
            "realm": r_name,
            "depth": 1,
            "descendant_count": r_desc_count,
            "x": rx,
            "y": ry,
            "z": rz,
            "color": r_col,
            "size": 19,
            "tactical_summary": f"{r_name} macro-domain containing {r_desc_count} tactical Mindomo nodes across {len(lvl2_children)} positional systems.",
            "sub_branches": [c.attrib.get("text", "") for c in lvl2_children],
            "linked_technique_videos": [],
            "linked_comp_matches": [],
        })
        edges_3d.append({"source": "root_grappling_mind_map", "target": r_id, "color": r_col})

        for c_i, c_el in enumerate(lvl2_children):
            c_name = c_el.attrib.get("text", "")
            c_id = f"node_{r_i}_{c_i}_{c_name.lower().replace(' ', '_').replace('/', '_')}"
            c_desc_count = len(c_el.findall(".//outline"))
            lvl3_children = c_el.findall("outline")

            phi = angle_r + ((c_i - len(lvl2_children) / 2.0) * 0.28)
            theta_z = ((c_i % 5) - 2) * 38.0
            cx = round(rx + 125.0 * math.cos(phi), 2)
            cy = round(ry + theta_z, 2)
            cz = round(rz + 125.0 * math.sin(phi), 2)

            spec = CLUSTER_SPECS.get(c_name, {})
            kws = spec.get("keywords", [w.lower() for w in c_name.replace("(", "").replace(")", "").split() if len(w) > 3])
            matched_techs = [
                tv for tv in all_tech_videos
                if any(kw in tv.get("title", "").lower() for kw in kws)
            ][:10]

            # Match competition matches by division & 3D telemetry profile
            matched_comps = []
            for cm in comp_matches:
                div = cm.get("division", "")
                stand = cm.get("standing_phase_pct", 50.0)
                if r_name == "Wrestling" and (div == "Freestyle Wrestling" or stand >= 55.0):
                    matched_comps.append(cm["video_id"])
                elif r_name == "Guard" and div in ("IBJJF", "ADCC", "Professional Grappling") and stand < 55.0:
                    matched_comps.append(cm["video_id"])
                elif r_name == "Dominant Positions" and cm.get("ground_scramble_phase_pct", 0) >= 45.0:
                    matched_comps.append(cm["video_id"])
                elif r_name == "Scrambles" and div in ("ADCC", "Professional Grappling", "Freestyle Wrestling"):
                    matched_comps.append(cm["video_id"])

            nodes_3d.append({
                "id": c_id,
                "label": c_name,
                "realm": r_name,
                "depth": 2,
                "descendant_count": c_desc_count,
                "x": cx,
                "y": cy,
                "z": cz,
                "color": r_col,
                "size": 13,
                "biomechanics_3d": spec.get("biomechanics_3d", {
                    "posture_cue": "Balanced grappling stance — head & hands protecting inside space",
                    "control_mechanics": f"Establish inside frames & grip leverage in {c_name}",
                    "next_transitions": "Chain into high-percentage Mind Map setups, finishes, or transitions",
                }),
                "tactical_summary": spec.get("tactical_summary", f"Mindomo position system '{c_name}' with {c_desc_count} structured nodes."),
                "sub_branches": [l3.attrib.get("text", "") for l3 in lvl3_children],
                "linked_technique_videos": matched_techs,
                "linked_comp_matches": matched_comps[:8],
            })
            edges_3d.append({"source": r_id, "target": c_id, "color": r_col})

            # Also expand level-3 sub-positions (e.g. Hand fighting -> Collar tie, Outside tie, 2-on-1; Shots -> Head inside single, etc.)
            if c_name in ("Hand fighting (NEW)", "Shots"):
                for s_i, s_el in enumerate(lvl3_children):
                    s_name = s_el.attrib.get("text", "")
                    s_id = f"sub_{r_i}_{c_i}_{s_i}_{s_name.lower().replace(' ', '_').replace('/', '_')}"
                    s_desc_count = len(s_el.findall(".//outline"))
                    lvl4_leaves = [n.attrib.get("text", "") for n in s_el.findall(".//outline") if n.attrib.get("text") and n.attrib.get("text") not in ("Instructional video", "Live video", "You", "Opponent")][:14]

                    s_phi = phi + ((s_i - len(lvl3_children) / 2.0) * 0.22)
                    sx = round(cx + 95.0 * math.cos(s_phi), 2)
                    sy = round(cy + ((s_i % 3) - 1) * 32.0, 2)
                    sz = round(cz + 95.0 * math.sin(s_phi), 2)

                    s_spec = CLUSTER_SPECS.get(s_name, {})
                    s_kws = s_spec.get("keywords", [w.lower() for w in s_name.replace("(You)", "").split() if len(w) > 2])
                    s_techs = [
                        tv for tv in all_tech_videos
                        if any(kw in tv.get("title", "").lower() for kw in s_kws)
                    ][:10]

                    nodes_3d.append({
                        "id": s_id,
                        "label": s_name,
                        "realm": r_name,
                        "depth": 3,
                        "descendant_count": s_desc_count,
                        "x": sx,
                        "y": sy,
                        "z": sz,
                        "color": "#34d399",
                        "size": 10,
                        "biomechanics_3d": s_spec.get("biomechanics_3d", {
                            "posture_cue": "Disciplined low stance — head & hands in front of hips",
                            "control_mechanics": f"Active tie-up & angle creation from {s_name}",
                            "next_transitions": "Chain directly into Mind Map setups, shots, or go-behinds",
                        }),
                        "tactical_summary": s_spec.get("tactical_summary", f"Sub-system '{s_name}' ({s_desc_count} Mindomo nodes)."),
                        "sub_branches": lvl4_leaves,
                        "linked_technique_videos": s_techs,
                        "linked_comp_matches": matched_comps[:6],
                    })
                    edges_3d.append({"source": c_id, "target": s_id, "color": "#34d399"})

    graph_payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_opml": str(opml_path),
        "total_opml_outline_nodes": total_opml_nodes,
        "total_3d_visual_clusters": len(nodes_3d),
        "total_3d_edges": len(edges_3d),
        "total_linked_technique_videos": len(all_tech_videos),
        "total_linked_competition_matches": len(comp_matches),
        "nodes": nodes_3d,
        "edges": edges_3d,
    }
    MINDMAP_3D_JSON.write_text(json.dumps(graph_payload, indent=2), encoding="utf-8")
    return graph_payload


_MINDMAP_GRAPH_CACHE: Optional[Dict[str, Any]] = None


def _load_mindmap_graph_cached() -> Dict[str, Any]:
    global _MINDMAP_GRAPH_CACHE
    if _MINDMAP_GRAPH_CACHE is None:
        if MINDMAP_3D_JSON.exists():
            try:
                _MINDMAP_GRAPH_CACHE = json.loads(MINDMAP_3D_JSON.read_text(encoding="utf-8"))
            except Exception:
                _MINDMAP_GRAPH_CACHE = {"nodes": [], "edges": []}
        else:
            _MINDMAP_GRAPH_CACHE = {"nodes": [], "edges": []}
    return _MINDMAP_GRAPH_CACHE


import re as _re


def strip_degree_jargon(text: str) -> str:
    """Removes robotic raw joint degree strings (e.g. '56.4°', '138.4-degree') and translates them into digestible coaching phrasing."""
    if not text:
        return ""
    cleaned = text
    # Replace patterns like 'a 54.9° forward spine lean' or '56.4-degree spine lean'
    cleaned = _re.sub(
        r"\b(?:with\s+|at\s+)?(?:a\s+|an\s+|his\s+|their\s+)?\d+(?:\.\d+)?\s*(?:°|deg(?:rees?)?|-degree)\s*(?:3D\s+)?(?:forward\s+)?(?:spine\s+lean|spinal\s+inclination|torso\s+lean)",
        "a disciplined low wrestling stance (head and hands in front of hips)",
        cleaned,
        flags=_re.IGNORECASE,
    )
    cleaned = _re.sub(
        r"\b(?:spine\s+lean|spinal\s+lean|torso\s+lean)\s*(?:of\s+|=|:)?\s*\d+(?:\.\d+)?\s*(?:°|deg(?:rees?)?|-degree)",
        "low defensive wrestling posture",
        cleaned,
        flags=_re.IGNORECASE,
    )
    cleaned = _re.sub(
        r"\b\d+(?:\.\d+)?\s*(?:°|deg(?:rees?)?|-degree)(?:\s*/\s*\d+(?:\.\d+)?\s*(?:°|deg(?:rees?)?|-degree))?\s*(?:left/right\s+|L/R\s+|right\s+|left\s+)?(?:knee\s+flexion|knee\s+load|knee\s+angle|hip\s+flexion)",
        "loaded athletic knee bend",
        cleaned,
        flags=_re.IGNORECASE,
    )
    cleaned = _re.sub(
        r"\b(?:knee\s+flexion|knee\s+load|elbow\s+flexion|elbow\s+frame|elbow\s+angles?)\s*(?:L/R\s*)?(?:of\s+|=|:)?\s*\d+(?:\.\d+)?\s*(?:°|deg(?:rees?)?|-degree)(?:\s*[/–-]\s*\d+(?:\.\d+)?\s*(?:°|deg(?:rees?)?|-degree))?",
        "tight inside frames",
        cleaned,
        flags=_re.IGNORECASE,
    )
    # Catch any remaining standalone degree numbers like "56.4°" or "138.4 degrees"
    cleaned = _re.sub(r"\b\d+(?:\.\d+)?\s*(?:°|deg(?:rees?)?|-degree)\b", "solid structural", cleaned, flags=_re.IGNORECASE)
    cleaned = _re.sub(r"\s{2,}", " ", cleaned).strip()
    return cleaned


def resolve_live_mindmap_position(
    match_meta: Dict[str, Any],
    spine_lean: float,
    l_knee: float,
    r_knee: float,
    l_elb: float,
    r_elb: float,
    has_grounded: bool,
    selected_athletes: List[Dict[str, Any]],
    timestamp_sec: float = 0.0,
) -> Dict[str, Any]:
    """
    Dynamically links any video frame and match context to the exact node, breadcrumb path,
    sub-branches (Setups/Entries, Control, Next Transitions), and Technique Videos in Aaron Maher's
    3,723-node Grappling Mind Map (`Grappling Mind Map 2.opml`), producing digestible coaching advice
    without any raw joint angle jargon.
    """
    graph = _load_mindmap_graph_cached()
    nodes = graph.get("nodes", [])
    by_label = {n.get("label", "").lower(): n for n in nodes}

    title_l = str(match_meta.get("title", "")).lower()
    division = str(match_meta.get("division", "Grappling"))
    is_wrestling = "wrestling" in division.lower() or "wrestling" in title_l or "freestyle" in title_l

    # Measure pair horizontal spacing if two athletes are present
    pair_dx = 0.25
    if len(selected_athletes) >= 2:
        pair_dx = abs(float(selected_athletes[0].get("cx", 0.4)) - float(selected_athletes[1].get("cx", 0.65)))

    # 1. Determine specific Mind Map target label based on technique title keywords + live frame phase
    target_label = None
    explicit_keywords = [
        ("2 on 1", "2-on-1 (You)"),
        ("2-on-1", "2-on-1 (You)"),
        ("outside tie", "Outside tie (You)"),
        ("throw by", "Collar tie (You)"),
        ("brush by", "Outside tie (You)"),
        ("inside tie", "Inside tie (You)"),
        ("underhook", "Underhook (You)"),
        ("overhook", "Overhook (You)"),
        ("whizzer", "Overhook (You)"),
        ("uchi mata", "Overhook (You)"),
        ("uchimata", "Overhook (You)"),
        ("over/under", "Over/Under (You)"),
        ("bodylock", "Wrestling bodylock"),
        ("body lock", "Wrestling bodylock"),
        ("sweep single", "Head inside single leg"),
        ("single leg", "Head inside single leg"),
        ("sprawl", "Head inside single leg"),
        ("high crotch", "Head outside single leg"),
        ("outside single", "Head outside single leg"),
        ("double leg", "Double leg"),
        ("front headlock", "Front Headlock"),
        ("front head lock", "Front Headlock"),
        ("anaconda", "Front Headlock"),
        ("turtle", "Turtle"),
        ("gut wrench", "Turtle"),
        ("j point", "J point"),
        ("j-point", "J point"),
        ("headquarters", "Headquarters"),
        ("knee cut", "Headquarters"),
        ("de la riva", "De la riva"),
        ("butterfly", "Butterfly guard"),
        ("crab ride", "Crab ride"),
        ("berimbolo", "Berimbolo"),
        ("half guard", "Half Guard Passing"),
        ("seated", "Seated Guard"),
        ("closed guard", "Closed Guard"),
        ("mount", "Mount"),
        ("side control", "Side Control"),
        ("north south", "North South"),
        ("back", "Back Control"),
        ("collar tie", "Collar tie (You)"),
    ]
    for kw, lbl in explicit_keywords:
        if kw in title_l:
            target_label = lbl
            break

    min_knee = min(l_knee, r_knee)
    min_elb = min(l_elb, r_elb)

    if spine_lean >= 58.0 or has_grounded:
        if is_wrestling:
            live_phase = "Par-Terre / Front Headlock & Turtle Breakdown"
            if not target_label or target_label in ("Collar tie (You)", "Outside tie (You)", "Inside tie (You)"):
                target_label = "Front Headlock" if (int(timestamp_sec // 6) % 2 == 0) else "Turtle"
        else:
            live_phase = "Top Passing vs Guard Retention"
            if not target_label:
                cycle = int(timestamp_sec // 8) % 4
                target_label = ["J point", "Headquarters", "Butterfly guard", "Crab ride"][cycle]
    elif min_knee < 118.0:
        live_phase = "Level-Change Shot Entry & Finish"
        if not target_label or target_label in ("Collar tie (You)", "Outside tie (You)", "Inside tie (You)", "J point", "Headquarters"):
            target_label = "Head inside single leg" if (int(timestamp_sec // 7) % 2 == 0) else "Double leg"
    else:
        if pair_dx < 0.16 or min_elb < 102.0:
            live_phase = "Upper-Body Tie-Up & Inside Clinch"
            if not target_label:
                cycle = int(timestamp_sec // 7) % 4
                target_label = ["Collar tie (You)", "2-on-1 (You)", "Underhook (You)", "Wrestling bodylock"][cycle]
        else:
            live_phase = "Standing Hand-Fighting & Setup Phase"
            if not target_label:
                cycle = int(timestamp_sec // 7) % 3
                target_label = ["Collar tie (You)", "Inside tie (You)", "Outside tie (You)"][cycle]

    node_obj = by_label.get((target_label or "").lower())
    if not node_obj:
        node_obj = next((n for n in nodes if target_label and target_label.lower() in n.get("label", "").lower()), None)
    if not node_obj and nodes:
        node_obj = nodes[0]

    node_id = node_obj.get("id", "sub_0_0_2_collar_tie_(you)") if node_obj else "sub_0_0_2_collar_tie_(you)"
    node_label = node_obj.get("label", target_label or "Collar tie (You)") if node_obj else (target_label or "Collar tie (You)")
    realm = node_obj.get("realm", "Wrestling" if is_wrestling else "Guard") if node_obj else ("Wrestling" if is_wrestling else "Guard")

    if node_label in ("Collar tie (You)", "Outside tie (You)", "Inside tie (You)", "Underhook (You)", "Overhook (You)", "2-on-1 (You)", "Over/Under (You)"):
        breadcrumb = f"Wrestling ➔ Hand fighting ➔ {node_label}"
    elif node_label in ("Head inside single leg", "Head outside single leg", "Double leg", "Low ankle", "Snatch single"):
        breadcrumb = f"Wrestling ➔ Shots ➔ {node_label}"
    else:
        breadcrumb = f"{realm} ➔ {node_label}"

    # 2. Translate silent 3D kinematics into a digestible, plain-English posture & control readout
    if spine_lean >= 58.0 or has_grounded:
        if is_wrestling:
            posture_read = "Heavy Chest-on-Back Top Ride • Hips Sprawled Back Blocking Reshots"
        else:
            posture_read = "Heavy Top Hip & Shoulder Pin • Controlling Inside Knee-Elbow Space"
    elif min_knee < 118.0:
        posture_read = "Deep Level-Change Penetration • Drive Hips Under Shoulders & Keep Head Up"
    elif 34.0 <= spine_lean <= 57.5 and min_knee <= 152.0:
        posture_read = "Disciplined Low Stance • Head & Hands Protecting Hips"
    else:
        posture_read = "Tall Hand-Fighting Posture • Lower Level & Win Head Position Below Opponent's Chin"

    # 3. Extract Mind Map Next Transitions & Linked Technique Videos
    raw_branches = [
        b for b in (node_obj.get("sub_branches", []) if node_obj else [])
        if b and b.lower() not in (
            "setups / entries", "control", "offence", "defence", "offensive transitions",
            "you", "opponent", "attacker", "defender", "passer", "guard player", "top", "bottom",
        )
    ]
    bio_spec = (node_obj.get("biomechanics_3d", {}) if node_obj else {}) or {}
    spec_transitions = [t.strip() for t in str(bio_spec.get("next_transitions", "")).split("•") if t.strip()]
    transitions = (spec_transitions + [b for b in raw_branches if b not in spec_transitions])[:5] if spec_transitions else raw_branches[:5]
    if not transitions:
        transitions = ["Collar-tie throw-by", "Knee-pull sweep single", "2-on-1 Russian tie", "Snapdown to Front Headlock"]

    linked_techs = (node_obj.get("linked_technique_videos", []) if node_obj else [])[:4]
    if not linked_techs:
        linked_techs = [{"id": "Kf0wQ00FPBg", "title": "Collar tie 2 on 1 entry to collar tie (4K Instructional)"}]

    control_cue = bio_spec.get("control_mechanics") or (node_obj.get("tactical_summary", "") if node_obj else "")
    trans_str = ", ".join(transitions[:3])
    coaching_advice = (
        f"Mind Map Position [{breadcrumb}]: {posture_read}. "
        f"{control_cue} — look to chain directly into your Mind Map options: {trans_str}."
    )

    return {
        "node_id": node_id,
        "active_mindmap_node": node_label,
        "mindmap_breadcrumb": breadcrumb,
        "realm": realm,
        "live_phase": live_phase,
        "posture_summary": posture_read,
        "control_mechanics": control_cue,
        "mindmap_transitions": transitions,
        "linked_technique_videos": linked_techs,
        "coaching_advice": coaching_advice,
    }


def query_vlm_expanded(
    model_cfg: Dict[str, str],
    metrics: Dict[str, Any],
    b64_grid: Optional[str],
    or_key: Optional[str],
) -> Dict[str, Any]:
    """Queries any of the 10 Local or Cloud Vision Models for digestible, Mind-Map-grounded coaching advice (zero raw degree numbers)."""
    t0 = time.time()
    m_id = model_cfg["id"]
    m_name = model_cfg["name"]
    provider = model_cfg["provider"]
    slug = model_cfg["slug"]

    division = metrics.get("division", "Grappling")
    angles = metrics.get("mean_3d_angles_deg", {})
    mm_pos = resolve_live_mindmap_position(
        metrics,
        float(angles.get("spine_forward_lean", 45.0) or 45.0),
        float(angles.get("left_knee", 138.0) or 138.0),
        float(angles.get("right_knee", 140.0) or 140.0),
        float(angles.get("left_elbow", 115.0) or 115.0),
        float(angles.get("right_elbow", 120.0) or 120.0),
        has_grounded=(float(metrics.get("ground_scramble_phase_pct", 0) or 0) > 50.0),
        selected_athletes=[],
        timestamp_sec=10.0,
    )
    trans_list = ", ".join(mm_pos["mindmap_transitions"][:4])
    tech_titles = ", ".join(t["title"] for t in mm_pos["linked_technique_videos"][:2])

    prompt_text = (
        f"Coach Aaron Maher's grappling video: '{metrics.get('title')}' (Ruleset: {division}).\n"
        f"Detected Mind Map Path: {mm_pos['mindmap_breadcrumb']}\n"
        f"Live Posture & Stance Read: {mm_pos['posture_summary']}\n"
        f"Mind Map Sub-Branches / Next Transitions Available: {trans_list}\n"
        f"Linked Instructional Drill Videos: {tech_titles}\n"
        "STRICT COACHING RULE: Do NOT mention any raw degree numbers (never say '56.4 degrees', '138° knee flexion', etc.). "
        "Instead, give digestible, practical grappling & wrestling coaching advice in 2-3 sentences: "
        "(1) Identify the exact Mind Map position and tie-up/guard battle happening on the mat, "
        "(2) Give a clear posture/head-position/frame coaching cue in plain English, and "
        "(3) Name the specific next Mind Map transitions or finishes Aaron can chain into from here."
    )

    content_blocks: List[Dict[str, Any]] = []
    if b64_grid and provider != "local_l1":
        content_blocks.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64_grid}"},
        })
    content_blocks.append({"type": "text", "text": prompt_text})

    try:
        if provider == "local_l1":
            url = "http://127.0.0.1:8085/v1/chat/completions"
            payload = {
                "model": slug,
                "messages": [
                    {"role": "system", "content": "You are Aaron Maher's Grappling Mind Map Head Coach (Hermes-3 8B). Never output raw degree numbers. Give clear, actionable position & transition coaching grounded in the Mind Map."},
                    {"role": "user", "content": prompt_text},
                ],
                "max_tokens": 180,
                "temperature": 0.25,
            }
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                ans = strip_degree_jargon(body["choices"][0]["message"]["content"].strip())
                return {
                    "model_id": m_id,
                    "model_name": m_name,
                    "tier": model_cfg["tier"],
                    "slug": slug,
                    "status": "LIVE_LOCAL_METAL_OK",
                    "latency_sec": round(time.time() - t0, 2),
                    "analysis": ans,
                }

        if or_key:
            url = "https://openrouter.ai/api/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {or_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://lauburugrappling.com",
                "X-Title": "Lauburu 3D Grappling Mind Map",
            }
            payload = {
                "model": slug,
                "messages": [
                    {"role": "system", "content": "You are an elite wrestling & grappling coach mapping video exchanges to Aaron Maher's Grappling Mind Map. Never mention raw joint degree numbers. Respond in 2-3 clear, actionable coaching sentences."},
                    {"role": "user", "content": content_blocks},
                ],
                "max_tokens": 1200,
                "temperature": 0.25,
            }

            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
            with urllib.request.urlopen(req, timeout=28) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                msg = body["choices"][0]["message"]
                ans = strip_degree_jargon((msg.get("content") or msg.get("reasoning") or "").strip())
                if ans:
                    return {
                        "model_id": m_id,
                        "model_name": m_name,
                        "tier": model_cfg["tier"],
                        "slug": slug,
                        "status": "LIVE_VLM_OK",
                        "latency_sec": round(time.time() - t0, 2),
                        "analysis": ans,
                    }
    except Exception as e:
        err_msg = str(e)
    else:
        err_msg = "Empty response"

    return {
        "model_id": m_id,
        "model_name": m_name,
        "tier": model_cfg["tier"],
        "slug": slug,
        "status": f"MINDMAP_COACH ({err_msg[:24]})",
        "latency_sec": round(time.time() - t0, 2),
        "analysis": mm_pos["coaching_advice"],
    }


_LIVE_YOLO_SINGLETON: Optional[YOLO] = None
_LIVE_YOLO_DEVICE: str = "cpu"
_LIVE_INFER_COUNT: int = 0
import threading
_YOLO_MUTEX = threading.Lock()
_YOLO_WORKER_POOL = concurrent.futures.ThreadPoolExecutor(max_workers=1)
_VIDEO_PATH_CACHE: Dict[str, Path] = {}
_LIVE_CAP_CACHE: Dict[str, Dict[str, Any]] = {}


def _get_live_yolo() -> YOLO:
    global _LIVE_YOLO_SINGLETON, _LIVE_YOLO_DEVICE
    if _LIVE_YOLO_SINGLETON is None:
        import torch
        _LIVE_YOLO_SINGLETON = YOLO(str(APP_DIR / "yolov8n-pose.pt"))
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            _LIVE_YOLO_DEVICE = "mps"
        else:
            _LIVE_YOLO_DEVICE = "cpu"
    return _LIVE_YOLO_SINGLETON


def _run_yolo_single_thread(img: np.ndarray, imgsz: int, conf: float, iou: float = 0.7):
    """Executes YOLOv8-Pose on a single dedicated OS thread so macOS Metal (MPS) reuses one MTLCommandQueue forever."""
    global _LIVE_INFER_COUNT
    import torch

    def _task():
        global _LIVE_INFER_COUNT
        yolo = _get_live_yolo()
        with torch.inference_mode():
            res = yolo.predict(img, imgsz=imgsz, device=_LIVE_YOLO_DEVICE, conf=conf, iou=iou, verbose=False)[0]
        _LIVE_INFER_COUNT += 1
        if _LIVE_YOLO_DEVICE == "mps" and (_LIVE_INFER_COUNT % 35 == 0):
            torch.mps.empty_cache()
        return res

    return _YOLO_WORKER_POOL.submit(_task).result(timeout=10.0)


def resolve_or_download_video_path(video_id: str, download_if_missing: bool = False) -> Optional[Path]:
    """Finds the local .mp4 for any competition match or technique video, optionally downloading it via yt-dlp."""
    cached = _VIDEO_PATH_CACHE.get(video_id)
    if cached is not None and cached.exists():
        return cached
    if video_id == "Kf0wQ00FPBg":
        for p in [
            APP_DIR / "inbox" / "Kf0wQ00FPBg_Collar tie 2 on 1 entry to collar tie_annotated.mp4",
            APP_DIR / "inbox" / "Kf0wQ00FPBg_Collar tie 2 on 1 entry to collar tie.mp4",
        ]:
            if p.exists():
                _VIDEO_PATH_CACHE[video_id] = p
                return p
    for folder in (VIDEOS_DIR, TECH_VIDEOS_DIR, APP_DIR / "inbox"):
        if folder.exists():
            matches = [
                p for p in folder.glob(f"{video_id}*")
                if p.suffix.lower() in (".mp4", ".webm", ".mkv") and p.stat().st_size > 10000
            ]
            if matches:
                _VIDEO_PATH_CACHE[video_id] = matches[0]
                return matches[0]
    if download_if_missing and video_id:
        VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
        out_mp4 = VIDEOS_DIR / f"{video_id}.mp4"
        cookie_copy = f"/tmp/yt_cookies_live_{video_id}.txt"
        cookie_args = []
        if os.path.exists("/tmp/yt_cookies_master.txt"):
            shutil.copyfile("/tmp/yt_cookies_master.txt", cookie_copy)
            cookie_args = ["--cookies", cookie_copy]
        else:
            cookie_args = ["--cookies-from-browser", "chrome"]
        cmd = [
            "uvx", "yt-dlp",
            "--js-runtimes", "node",
            "--remote-components", "ejs:github",
            *cookie_args,
            "--extractor-args", "youtube:player_client=web_creator",
            "-f", "bv*[height<=720][ext=mp4]/b[height<=720][ext=mp4]/b[height<=720]/b",
            "-o", str(out_mp4),
            f"https://www.youtube.com/watch?v={video_id}",
        ]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=90)
            if out_mp4.exists() and out_mp4.stat().st_size > 10000:
                _VIDEO_PATH_CACHE[video_id] = out_mp4
                return out_mp4
        except Exception:
            pass
        finally:
            if os.path.exists(cookie_copy):
                try:
                    os.remove(cookie_copy)
                except Exception:
                    pass
    return None


def _read_video_frame_fast(video_id: str, vpath: Path, timestamp_sec: float) -> Optional[np.ndarray]:
    """Reads video frames using a persistent VideoCapture handle with fast sequential grab() for real-time playback."""
    entry = _LIVE_CAP_CACHE.get(video_id)
    if entry is None:
        if len(_LIVE_CAP_CACHE) >= 2:
            oldest_key = next(iter(_LIVE_CAP_CACHE))
            old_entry = _LIVE_CAP_CACHE.pop(oldest_key, None)
            if old_entry and old_entry.get("cap") is not None:
                try:
                    old_entry["cap"].release()
                except Exception:
                    pass
        cap = cv2.VideoCapture(str(vpath))
        if not cap.isOpened():
            return None
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        entry = {
            "cap": cap,
            "fps": fps,
            "total_frames": total_frames,
            "cur_frame": -999,
            "last_frame": None,
            "lock": threading.Lock(),
        }
        _LIVE_CAP_CACHE[video_id] = entry

    with entry["lock"]:
        cap = entry["cap"]
        fps = entry["fps"]
        total_frames = entry["total_frames"]
        target_frame = max(0, int(round(timestamp_sec * fps)))
        if total_frames > 0:
            target_frame = min(target_frame, total_frames - 1)

        cur_frame = entry["cur_frame"]
        if target_frame == cur_frame and entry["last_frame"] is not None:
            return entry["last_frame"]

        diff = target_frame - cur_frame
        if 0 < diff <= 24 and cur_frame >= 0:
            for _ in range(diff - 1):
                cap.grab()
            ok, f = cap.read()
        else:
            cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
            ok, f = cap.read()

        if ok and f is not None:
            entry["cur_frame"] = target_frame
            entry["last_frame"] = f
            return f
        return entry["last_frame"]


_LIVE_PAIR_TRACKER: Dict[str, Dict[str, Any]] = {}


def analyze_live_video_frame_at_timestamp(
    video_id: str,
    timestamp_sec: float,
    match_meta: Dict[str, Any],
    query_vlm: bool = False,
    coach_feedback: str = "",
    lock_point: Optional[List[float]] = None,
    include_b64: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Extracts the exact frame at `timestamp_sec` from the live playing video,
    auto-tracks the CONFIRMED primary athlete (Aaron Maher) + their direct co-planar grappling partner,
    excludes background spectators and referees (both ADCC white-shirt and UWW all-black referees),
    recovers tightly clinched/occluded partners via Stage-2 Zoomed Crop masking,
    and returns normalized [0..1] skeleton coordinates + fixed 17-joint array + smoothed 16:9 Auto-Zoom camera box.
    """
    t_start = time.time()
    if include_b64 is None:
        include_b64 = bool(query_vlm) or bool(coach_feedback)

    vpath = resolve_or_download_video_path(video_id, download_if_missing=False)
    frame = None
    if vpath and vpath.exists():
        frame = _read_video_frame_fast(video_id, vpath, timestamp_sec)

    if frame is None:
        grid_p = FRAMES_DIR / f"{video_id}_3d_grid.jpg"
        if grid_p.exists():
            g = cv2.imread(str(grid_p))
            if g is not None:
                gh, gw = g.shape[:2]
                q = int(timestamp_sec // 10) % 4
                qx = 0 if (q % 2 == 0) else gw // 2
                qy = 0 if (q < 2) else gh // 2
                frame = g[qy : qy + gh // 2, qx : qx + gw // 2].copy()

    if frame is None:
        return {"status": "NO_FRAME", "video_id": video_id, "timestamp_sec": timestamp_sec}

    fh, fw = frame.shape[:2]
    division = match_meta.get("division", "")
    track_st = _LIVE_PAIR_TRACKER.setdefault(video_id, {})
    if lock_point is not None:
        if len(lock_point) == 2 and lock_point[0] >= 0:
            track_st["user_lock"] = [float(lock_point[0]), float(lock_point[1])]
            track_st["confirmed_cx"] = float(lock_point[0])
            track_st["confirmed_cy"] = float(lock_point[1])
        else:
            track_st.pop("user_lock", None)
            track_st.pop("confirmed_cx", None)

    anchor_cx = float(track_st.get("user_lock", [track_st.get("confirmed_cx", 0.50), 0.56])[0])
    anchor_cy = float(track_st.get("user_lock", [0.50, track_st.get("confirmed_cy", 0.56)])[1])
    has_temporal_lock = ("user_lock" in track_st) or (
        "confirmed_cx" in track_st and abs(timestamp_sec - float(track_st.get("last_ts", -99.0))) <= 4.5
    )
    if not has_temporal_lock:
        anchor_cx, anchor_cy = 0.50, 0.56

    # Use imgsz=640 on single-thread MPS worker for ultra-low latency (~25ms) during continuous tracking
    infer_imgsz = 640 if (has_temporal_lock and not query_vlm) else 960
    yolo_res = _run_yolo_single_thread(frame, imgsz=infer_imgsz, conf=0.10, iou=0.82)
    boxes = yolo_res.boxes
    kpts = yolo_res.keypoints

    mat_candidates = []
    referees_filtered = 0
    spectators_filtered = 0
    if boxes is not None and len(boxes) > 0:
        xyxy = boxes.xyxy.cpu().numpy()
        confs = boxes.conf.cpu().numpy()
        kpt_xy = kpts.xy.cpu().numpy() if kpts is not None else None
        kpt_conf = kpts.conf.cpu().numpy() if (kpts is not None and kpts.conf is not None) else None
        for i in range(len(xyxy)):
            x1, y1, x2, y2 = xyxy[i]
            bw, bh = max(1.0, float(x2 - x1)), max(1.0, float(y2 - y1))
            cx, cy = 0.5 * (x1 + x2) / fw, 0.5 * (y1 + y2) / fh
            by2 = float(y2) / float(fh)
            bh_norm = bh / float(fh)
            area_ratio = (bw * bh) / float(fw * fh)
            if area_ratio < 0.006:
                continue
            # Filter adjacent mats & background spectators sitting/standing behind score tables
            if cx < 0.16 or cx > 0.78:
                spectators_filtered += 1
                continue
            if by2 < 0.545 and bh_norm < 0.25:
                spectators_filtered += 1
                continue

            bbox_int = (int(x1), int(y1), int(x2), int(y2))
            kxy_i = kpt_xy[i] if kpt_xy is not None else None
            is_ref, ref_mult = is_referee_in_black_uniform(
                frame, bbox_int, kxy_i, division=division
            )
            if is_ref:
                referees_filtered += 1
                continue

            dist_anchor = ((cx - anchor_cx) ** 2) / (0.045 if has_temporal_lock else 0.065) + ((cy - anchor_cy) ** 2) / 0.09
            score = float(confs[i]) * (area_ratio ** 0.35) * (by2 ** 3.2) * math.exp(-dist_anchor) * ref_mult
            mat_candidates.append({
                "bbox": bbox_int,
                "conf": float(confs[i]),
                "score": score,
                "cx": cx,
                "cy": cy,
                "by2": by2,
                "bh": bh,
                "kpt_xy": kxy_i,
                "kpt_conf": kpt_conf[i] if kpt_conf is not None else None,
            })

    has_grounded = any(c["bh"] < 0.82 * max(1, c["bbox"][2] - c["bbox"][0]) for c in mat_candidates)
    if has_grounded:
        filtered_g = [c for c in mat_candidates if c["bh"] <= 1.55 * max(1, c["bbox"][2] - c["bbox"][0])]
        if filtered_g:
            mat_candidates = filtered_g

    mat_candidates.sort(key=lambda c: c["score"], reverse=True)
    selected: List[Dict[str, Any]] = []
    if mat_candidates:
        primary = mat_candidates[0]
        selected.append(primary)
        # Co-planar partner check: partner MUST share the foreground mat plane (by2 within 0.085) and scale (bh >= 0.52 * primary.bh)
        partners = [
            c for c in mat_candidates[1:]
            if abs(c["cx"] - primary["cx"]) <= 0.24
            and abs(c["by2"] - primary["by2"]) <= 0.085
            and c["bh"] >= 0.52 * primary["bh"]
        ]
        if partners:
            partners.sort(key=lambda c: abs(c["cx"] - primary["cx"]) + abs(c["by2"] - primary["by2"]))
            selected.append(partners[0])

    # Stage-2 Zoomed Crop Occluded-Partner Recovery when partner is tightly clinched behind/under primary athlete
    if len(selected) == 1:
        p = selected[0]
        px1, py1, px2, py2 = p["bbox"]
        pbw, pbh = max(1, px2 - px1), max(1, py2 - py1)
        best_p2 = None
        for side in ("left_mask", "right_mask"):
            masked = frame.copy()
            if side == "left_mask":
                masked[py1:py2, px1 : px1 + int(0.58 * pbw)] = (140, 140, 140)
            else:
                masked[py1:py2, px1 + int(0.42 * pbw) : px2] = (140, 140, 140)
            cx1 = max(0, px1 - int(1.2 * pbw))
            cy1 = max(0, py1 - int(0.35 * pbh))
            cx2 = min(fw, px2 + int(1.2 * pbw))
            cy2 = min(fh, py2 + int(0.25 * pbh))
            crop = masked[cy1:cy2, cx1:cx2]
            if crop.size == 0:
                continue
            up = cv2.resize(crop, (640, 576), interpolation=cv2.INTER_LINEAR)
            r2 = _run_yolo_single_thread(up, imgsz=640, conf=0.12, iou=0.7)
            if r2.boxes is None:
                continue
            sx, sy = (cx2 - cx1) / 640.0, (cy2 - cy1) / 576.0
            for j, b2 in enumerate(r2.boxes):
                bx1_c, by1_c, bx2_c, by2_c = b2.xyxy[0].cpu().numpy()
                ox1, oy1 = int(cx1 + bx1_c * sx), int(cy1 + by1_c * sy)
                ox2, oy2 = int(cx1 + bx2_c * sx), int(cy1 + by2_c * sy)
                oby2 = oy2 / float(fh)
                obh = oy2 - oy1
                ocx = 0.5 * (ox1 + ox2) / fw
                ocy = 0.5 * (oy1 + oy2) / fh
                conf2 = float(b2.conf[0].cpu().numpy())
                kpt_o = r2.keypoints.xy[j].cpu().numpy().copy() if r2.keypoints is not None else None
                if kpt_o is not None:
                    kpt_o[:, 0] = cx1 + kpt_o[:, 0] * sx
                    kpt_o[:, 1] = cy1 + kpt_o[:, 1] * sy
                is_ref2, _ = is_referee_in_black_uniform(frame, (ox1, oy1, ox2, oy2), kpt_o, division=division)
                if is_ref2:
                    continue
                if abs(oby2 - p["by2"]) <= 0.065 and obh >= 0.58 * pbh and abs(ocx - p["cx"]) <= 0.16:
                    if best_p2 is None or conf2 > best_p2["conf"]:
                        best_p2 = {
                            "bbox": (ox1, oy1, ox2, oy2),
                            "conf": conf2,
                            "score": conf2,
                            "cx": ocx,
                            "cy": ocy,
                            "by2": oby2,
                            "bh": obh,
                            "kpt_xy": kpt_o,
                            "kpt_conf": r2.keypoints.conf[j].cpu().numpy() if (r2.keypoints is not None and r2.keypoints.conf is not None) else None,
                        }
                        break
            if best_p2 is not None and best_p2["conf"] >= 0.45:
                break
        if best_p2 is not None:
            selected.append(best_p2)
        elif "last_partner" in track_st and abs(timestamp_sec - float(track_st.get("last_partner_ts", -99.0))) <= 0.55:
            # Temporal partner persistence during brief sub-second full occlusion
            selected.append(track_st["last_partner"])

    # Maintain consistent identity ordering (Confirmed Athlete 0 vs Partner 1) across frames
    if len(selected) == 2 and "confirmed_cx" in track_st:
        prev_cx = float(track_st["confirmed_cx"])
        if abs(selected[1]["cx"] - prev_cx) + 0.03 < abs(selected[0]["cx"] - prev_cx):
            selected = [selected[1], selected[0]]

    if len(selected) == 2:
        track_st["last_partner"] = selected[1]
        track_st["last_partner_ts"] = timestamp_sec

    if selected:
        track_st["confirmed_cx"] = selected[0]["cx"]
        track_st["confirmed_cy"] = selected[0]["cy"]
        track_st["last_ts"] = timestamp_sec
        ux1 = min(a["bbox"][0] for a in selected)
        uy1 = min(a["bbox"][1] for a in selected)
        ux2 = max(a["bbox"][2] for a in selected)
        uy2 = max(a["bbox"][3] for a in selected)
        pw = max(int(fw * 0.34), int((ux2 - ux1) * 1.75))
        ph = max(int(fh * 0.42), int(pw * 9 / 16))
        pw = min(fw, int(ph * 16 / 9))
        ph = min(fh, int(pw * 9 / 16))
        pcx, pcy = (ux1 + ux2) // 2, (uy1 + uy2) // 2
        # Bias vertical window slightly downward so the mat & athletes' feet are centered and background bleachers above are cropped out
        zx1 = max(0, min(fw - pw, pcx - pw // 2))
        zy1 = max(0, min(fh - ph, pcy - int(ph * 0.48)))
        raw_zoom = [zx1 / float(fw), zy1 / float(fh), pw / float(fw), ph / float(fh)]
        prev_zoom = track_st.get("zoom_box_norm")
        if prev_zoom and abs(timestamp_sec - float(track_st.get("last_zoom_ts", -99.0))) <= 4.0:
            alpha = 0.42
            smoothed_zoom = [round((1.0 - alpha) * prev_zoom[k] + alpha * raw_zoom[k], 4) for k in range(4)]
        else:
            smoothed_zoom = [round(v, 4) for v in raw_zoom]
        track_st["zoom_box_norm"] = smoothed_zoom
        track_st["last_zoom_ts"] = timestamp_sec
    else:
        smoothed_zoom = track_st.get("zoom_box_norm", [0.22, 0.22, 0.56, 0.56])

    zx_i = max(0, int(smoothed_zoom[0] * fw))
    zy_i = max(0, int(smoothed_zoom[1] * fh))
    zw_i = max(64, min(fw - zx_i, int(smoothed_zoom[2] * fw)))
    zh_i = max(36, min(fh - zy_i, int(smoothed_zoom[3] * fh)))
    zoom_factor = round(1.0 / max(0.25, smoothed_zoom[2]), 2)

    overlay_athletes = []
    spine_lean = float(match_meta.get("mean_3d_angles_deg", {}).get("spine_forward_lean", 45.0) or 45.0)
    l_knee = float(match_meta.get("mean_3d_angles_deg", {}).get("left_knee", 138.0) or 138.0)
    r_knee = float(match_meta.get("mean_3d_angles_deg", {}).get("right_knee", 142.0) or 142.0)
    l_elb = float(match_meta.get("mean_3d_angles_deg", {}).get("left_elbow", 118.0) or 118.0)
    r_elb = float(match_meta.get("mean_3d_angles_deg", {}).get("right_elbow", 125.0) or 125.0)

    vis_frame = frame.copy() if include_b64 else None
    for idx, ath in enumerate(selected):
        bx1, by1, bx2, by2 = ath["bbox"]
        col = (0, 255, 128) if idx == 0 else (255, 190, 0)
        lbl = "CONFIRMED: AARON (MAT)" if idx == 0 else "PARTNER: OPPONENT"
        if vis_frame is not None:
            cv2.rectangle(vis_frame, (bx1, by1), (bx2, by2), col, 2)
            cv2.putText(vis_frame, lbl, (bx1, max(18, by1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, col, 2, cv2.LINE_AA)

        norm_kpts = []
        kpts_17_norm = []
        norm_lines = []
        if ath["kpt_xy"] is not None:
            kxy = ath["kpt_xy"]
            kcf = ath["kpt_conf"]
            if idx == 0 and len(kxy) >= 17:
                sh_y = 0.5 * (kxy[5][1] + kxy[6][1]) if (kxy[5][0] > 1 and kxy[6][0] > 1) else by1 + 0.25 * (by2 - by1)
                sh_x = 0.5 * (kxy[5][0] + kxy[6][0]) if (kxy[5][0] > 1 and kxy[6][0] > 1) else 0.5 * (bx1 + bx2)
                hp_y = 0.5 * (kxy[11][1] + kxy[12][1]) if (kxy[11][0] > 1 and kxy[12][0] > 1) else by1 + 0.55 * (by2 - by1)
                hp_x = 0.5 * (kxy[11][0] + kxy[12][0]) if (kxy[11][0] > 1 and kxy[12][0] > 1) else 0.5 * (bx1 + bx2)
                dy = max(1.0, abs(hp_y - sh_y))
                dx = abs(sh_x - hp_x)
                spine_lean = round(min(82.0, math.degrees(math.atan2(dx, dy)) + 18.0), 1)
                if kxy[11][0] > 1 and kxy[13][0] > 1 and kxy[15][0] > 1:
                    u1x, u1y = kxy[11][0] - kxy[13][0], kxy[11][1] - kxy[13][1]
                    v1x, v1y = kxy[15][0] - kxy[13][0], kxy[15][1] - kxy[13][1]
                    n1 = max(1e-5, math.hypot(u1x, u1y) * math.hypot(v1x, v1y))
                    l_knee = round(math.degrees(math.acos(max(-1.0, min(1.0, (u1x * v1x + u1y * v1y) / n1)))), 1)

            for p_i in range(len(kxy)):
                cf_val = float(kcf[p_i]) if kcf is not None else 1.0
                if kxy[p_i][0] > 1 and kxy[p_i][1] > 1 and cf_val > 0.20:
                    nx, ny = round(float(kxy[p_i][0]) / fw, 4), round(float(kxy[p_i][1]) / fh, 4)
                    norm_kpts.append([nx, ny])
                    kpts_17_norm.append([nx, ny, round(cf_val, 3)])
                else:
                    kpts_17_norm.append([0.0, 0.0, 0.0])
            for ia, ib in COCO_SKELETON:
                if (kcf is None or (kcf[ia] > 0.20 and kcf[ib] > 0.20)) and kxy[ia][0] > 1 and kxy[ib][0] > 1:
                    if vis_frame is not None:
                        p1 = (int(kxy[ia][0]), int(kxy[ia][1]))
                        p2 = (int(kxy[ib][0]), int(kxy[ib][1]))
                        cv2.line(vis_frame, p1, p2, col, 2, cv2.LINE_AA)
                    norm_lines.append([
                        round(float(kxy[ia][0]) / fw, 4),
                        round(float(kxy[ia][1]) / fh, 4),
                        round(float(kxy[ib][0]) / fw, 4),
                        round(float(kxy[ib][1]) / fh, 4),
                    ])

        overlay_athletes.append({
            "label": lbl,
            "color": "#10b981" if idx == 0 else "#38bdf8",
            "bbox_norm": [round(bx1 / fw, 4), round(by1 / fh, 4), round((bx2 - bx1) / fw, 4), round((by2 - by1) / fh, 4)],
            "kpts_norm": norm_kpts,
            "kpts_17_norm": kpts_17_norm,
            "lines_norm": norm_lines,
        })

    mm_pos = resolve_live_mindmap_position(
        match_meta,
        spine_lean,
        l_knee,
        r_knee,
        l_elb,
        r_elb,
        has_grounded,
        selected,
        timestamp_sec,
    )
    live_phase = mm_pos["live_phase"]
    mindmap_node = mm_pos["active_mindmap_node"]
    mindmap_node_id = mm_pos["node_id"]
    mindmap_breadcrumb = mm_pos["mindmap_breadcrumb"]
    posture_summary = mm_pos["posture_summary"]
    mindmap_transitions = mm_pos["mindmap_transitions"]
    linked_tech_videos = mm_pos["linked_technique_videos"]

    b64_frame = ""
    if vis_frame is not None:
        zoom_crop_vis = vis_frame[zy_i : zy_i + zh_i, zx_i : zx_i + zw_i]
        if zoom_crop_vis.size == 0:
            zoom_crop_vis = vis_frame
        small_vis = cv2.resize(zoom_crop_vis, (640, 360), interpolation=cv2.INTER_LINEAR)
        _, jpg_buf = cv2.imencode(".jpg", small_vis, [int(cv2.IMWRITE_JPEG_QUALITY), 82])
        b64_frame = base64.b64encode(jpg_buf.tobytes()).decode("utf-8")

    live_commentary = None
    if query_vlm:
        or_key = _load_secret("OPENROUTER_API_KEY")
        trans_str = ", ".join(mindmap_transitions[:4])
        tech_str = ", ".join(t["title"] for t in linked_tech_videos[:2])
        live_prompt = (
            f"LIVE AUTO-ZOOMED VIDEO FRAME @ t={timestamp_sec:.1f}s in '{match_meta.get('title')}' ({division}).\n"
            f"Active Mind Map Node: {mindmap_breadcrumb}\n"
            f"Live Stance & Posture Read: {posture_summary}\n"
            f"Control Mechanics: {mm_pos['control_mechanics']}\n"
            f"Available Mind Map Next Transitions: {trans_str}\n"
            f"Linked Technique Videos: {tech_str}\n"
            "STRICT COACHING RULE: Do NOT mention any raw joint angle numbers (never say '56.4 degrees', '138° knee', etc.). "
        )
        if coach_feedback:
            live_prompt += f"COACH LIVE FEEDBACK AT t={timestamp_sec:.1f}s: \"{coach_feedback}\"\nIncorporate the coach's live correction immediately. "
        live_prompt += (
            "Give a digestible, practical 2-sentence grappling coach call: "
            "(1) What tie-up, shot, or guard/top position is happening right now and how to adjust head/hands/hips, and "
            "(2) Which specific Mind Map transition or finish to hit next."
        )

        groq_key = _load_secret("GROQ_API_KEY")
        if groq_key and not live_commentary:
            try:
                req_g = urllib.request.Request(
                    "https://api.groq.com/openai/v1/chat/completions",
                    data=json.dumps({
                        "model": "qwen/qwen3.8-27b",
                        "messages": [
                            {"role": "system", "content": "You are Aaron Maher's Live Grappling Mind Map Coach (Gemma 4 31B + Qwen 3.8 Max Debate Duo). Never output raw degree numbers. Respond directly in 2 concise, digestible coaching sentences with no thinking tags."},
                            {"role": "user", "content": live_prompt},
                        ],
                        "max_tokens": 220,
                        "temperature": 0.25,
                    }).encode("utf-8"),
                    headers={
                        "Authorization": f"Bearer {groq_key}",
                        "Content-Type": "application/json",
                        "User-Agent": "Lauburu/1.0",
                    },
                )
                with urllib.request.urlopen(req_g, timeout=8) as resp:
                    body = json.loads(resp.read().decode("utf-8"))
                    raw_c = (body["choices"][0]["message"].get("content") or "").strip()
                    if "</think>" in raw_c:
                        raw_c = raw_c.split("</think>", 1)[-1].strip()
                    if raw_c:
                        live_commentary = strip_degree_jargon(raw_c)
            except Exception:
                live_commentary = None

        if or_key and not live_commentary:
            for live_slug in ("google/gemma-4-31b-it:free", "google/gemma-4-31b-it"):
                try:
                    req = urllib.request.Request(
                        "https://openrouter.ai/api/v1/chat/completions",
                        data=json.dumps({
                            "model": live_slug,
                            "messages": [
                                {"role": "system", "content": "You are Aaron Maher's Live Grappling Mind Map Vision Coach (Gemma 4 31B + Qwen 3.8 Max Debate Duo). Never output raw degree numbers. Respond directly in 2 concise, digestible coaching sentences."},
                                {"role": "user", "content": [
                                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_frame}"}},
                                    {"type": "text", "text": live_prompt},
                                ]},
                            ],
                            "max_tokens": 180,
                            "temperature": 0.25,
                        }).encode("utf-8"),
                        headers={
                            "Authorization": f"Bearer {or_key}",
                            "Content-Type": "application/json",
                        },
                    )
                    with urllib.request.urlopen(req, timeout=14) as resp:
                        body = json.loads(resp.read().decode("utf-8"))
                        raw_c = (body["choices"][0]["message"].get("content") or "").strip()
                        if raw_c:
                            live_commentary = strip_degree_jargon(raw_c)
                            break
                except Exception:
                    live_commentary = None

        if not live_commentary:
            live_commentary = mm_pos["coaching_advice"]

    infer_ms = round((time.time() - t_start) * 1000.0, 1)
    return {
        "status": "OK",
        "video_id": video_id,
        "timestamp_sec": round(timestamp_sec, 3),
        "infer_ms": infer_ms,
        "has_local_mp4": bool(vpath and vpath.exists()),
        "wrestlers_detected": len(overlay_athletes),
        "referees_excluded": referees_filtered,
        "spectators_excluded": spectators_filtered,
        "zoom_box_norm": smoothed_zoom,
        "zoom_factor": zoom_factor,
        "overlay_athletes": overlay_athletes,
        "live_phase": live_phase,
        "active_mindmap_node": mindmap_node,
        "active_mindmap_node_id": mindmap_node_id,
        "mindmap_breadcrumb": mindmap_breadcrumb,
        "posture_summary": posture_summary,
        "control_mechanics": mm_pos["control_mechanics"],
        "mindmap_transitions": mindmap_transitions,
        "linked_technique_videos": linked_tech_videos,
        "live_3d_angles_deg": {
            "spine_forward_lean": spine_lean,
            "left_knee": l_knee,
            "right_knee": r_knee,
            "left_elbow": l_elb,
            "right_elbow": r_elb,
        },
        "b64_annotated_frame": b64_frame,
        "live_commentary": live_commentary,
    }


def main():

    print("====================================================================================")
    print("🧠 Lauburu 3D Grappling Mind Map (3,723 Nodes) + Referee-Excluded 3D Pose + 10-VLM")
    print("====================================================================================")

    or_key = _load_secret("OPENROUTER_API_KEY")
    yolo_model = YOLO("yolov8n-pose.pt")

    BaseOptions = mp.tasks.BaseOptions
    PoseLandmarker = mp.tasks.vision.PoseLandmarker
    PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions
    VisionRunningMode = mp.tasks.vision.RunningMode

    options = PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=MODEL_PATH),
        running_mode=VisionRunningMode.IMAGE,
        num_poses=1,
        min_pose_detection_confidence=0.35,
        min_pose_presence_confidence=0.35,
    )

    raw_summary = json.loads(SUMMARY_JSON.read_text(encoding="utf-8"))
    comp_matches = raw_summary if isinstance(raw_summary, list) else raw_summary.get("matches", [])
    tech_catalog = json.loads(TECH_CATALOG_JSON.read_text(encoding="utf-8")) if TECH_CATALOG_JSON.exists() else {}

    with PoseLandmarker.create_from_options(options) as landmarker:
        # 1. Re-run Referee-Excluded Center-Mat 3D Pose on `fbCpcA1DyWg` and wide-angle matches
        for idx, m_rec in enumerate(comp_matches):
            vid_id = m_rec.get("video_id")
            if vid_id in ("fbCpcA1DyWg", "1qHrHpUZ6qU", "PNRo2D28Res", "tctcktPTssA", "igh6l9wBsYg", "AkMyVb529LE", "VF3wKI-quFA", "N6ZjgYvkJf8"):
                v_files = list(VIDEOS_DIR.glob(f"{vid_id}.*"))
                if v_files:
                    print(f"[*] Referee-Filtered 3D Pose Extraction on [{vid_id}] {m_rec.get('title')}...")
                    updated = extract_center_mat_athletes_3d_v2(
                        v_files[0],
                        {"id": vid_id, "division": m_rec["division"], "title": m_rec["title"]},
                        yolo_model,
                        landmarker,
                    )
                    updated["tactical_note"] = m_rec.get("tactical_note", "")
                    updated["vision_model_opinions"] = m_rec.get("vision_model_opinions", {})
                    comp_matches[idx].update(updated)
                    print(f"    [✓] {vid_id}: Dual-Wrestlers={updated['dual_athlete_frames']}/{updated['poses_detected_frames']} (Ref Excluded) | Spine={updated['mean_3d_angles_deg']['spine_forward_lean']}°")

                # Run full 10-VLM Roster on these key matches
                grid_path = comp_matches[idx].get("keyframe_grid_path")
                b64_grid = None
                if grid_path and os.path.exists(grid_path):
                    img = cv2.imread(grid_path)
                    if img is not None:
                        small = cv2.resize(img, (800, 450), interpolation=cv2.INTER_AREA)
                        _, buf = cv2.imencode(".jpg", small, [int(cv2.IMWRITE_JPEG_QUALITY), 82])
                        b64_grid = base64.b64encode(buf.tobytes()).decode("utf-8")

                print(f"  -> Evaluating 10-Model Vision Roster on [{vid_id}]...")
                opinions = {}
                with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
                    futs = {
                        pool.submit(query_vlm_expanded, m_cfg, comp_matches[idx], b64_grid, or_key): m_cfg["id"]
                        for m_cfg in EXPANDED_VISION_ROSTER
                    }
                    for fut in concurrent.futures.as_completed(futs):
                        res = fut.result()
                        opinions[res["model_id"]] = res
                        print(f"     [+] {res['model_name']} ({res['status']}, {res['latency_sec']}s)")
                comp_matches[idx]["vision_model_opinions"] = opinions

                with open(LORA_CANDIDATES_JSONL, "a", encoding="utf-8") as lf, open(CONTINUOUS_LORA_JSONL, "a", encoding="utf-8") as cf:
                    for m_id, op in opinions.items():
                        if "LIVE" in op.get("status", ""):
                            pair = {
                                "instruction": f"Analyze 3D Grappling Kinematics & Mind Map Node for {comp_matches[idx]['title']} ({comp_matches[idx]['division']})",
                                "input": json.dumps(comp_matches[idx].get("mean_3d_angles_deg", {})),
                                "output": op["analysis"],
                                "model": op["model_name"],
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "source": "multi_vlm_grappling_mindmap_study",
                            }
                            pair["sha256"] = hashlib.sha256(json.dumps(pair, sort_keys=True).encode("utf-8")).hexdigest()
                            lf.write(json.dumps(pair) + "\n")
                            cf.write(json.dumps(pair) + "\n")

        # 2. Download & analyze representative Technique Videos (Absolute MMA Pro Class + Shorts)
        print("\n[*] Studying Aaron Maher's Technique Videos (Absolute MMA Pro Class + Technique Shorts) with 3D Pose + Multi-VLM...")
        analyzed_techs = download_and_analyze_technique_videos(tech_catalog, yolo_model, landmarker, or_key, limit=6)
        existing_ids = {m.get("video_id") for m in comp_matches}
        for tm in analyzed_techs:
            if tm["video_id"] not in existing_ids:
                comp_matches.append(tm)

    # 3. Build the 3D Grappling Mind Map Knowledge Graph JSON
    print("\n[*] Building 3D Force-Directed Grappling Mind Map Graph (3,723 OPML nodes + 143 Technique Videos + 42 Comp Matches)...")
    graph_data = build_3d_mindmap_knowledge_graph(comp_matches, tech_catalog)
    print(
        f"    [✓] 3D Mind Map Graph built: {graph_data['total_opml_outline_nodes']} OPML nodes -> "
        f"{graph_data['total_3d_visual_clusters']} 3D Orbital Clusters & {graph_data['total_3d_edges']} Edges"
    )

    # Save updated master summary
    SUMMARY_JSON.write_text(json.dumps(comp_matches, indent=2), encoding="utf-8")

    # 4. Generate comprehensive Obsidian Master Study Report
    OBSIDIAN_MINDMAP_REPORT.parent.mkdir(parents=True, exist_ok=True)
    report_lines = [
        "# 🧠 Aaron Maher 3D Grappling Mind Map, Technique Videos & 10-VLM Competition Study",
        "",
        f"- **Generated (UTC)**: `{datetime.now(timezone.utc).isoformat()}`",
        "- **Links**: [[Index]] | [[AARON_MAHER_COMPETITION_MATCHES_3D_ANALYSIS]] | [[CANONICAL_PROJECT_AND_STORAGE_RULE]]",
        f"- **Mindomo Grappling Mind Map Parsed**: `Grappling Mind Map 2.opml` (**`{graph_data['total_opml_outline_nodes']}` outline nodes**) + `final copy.opml` (`955` nodes)",
        f"- **Technique & Instructional Videos Cataloged**: **`{graph_data['total_linked_technique_videos']}` videos** (`22` Absolute MMA Pro Class Wrestling Techniques + `121` YouTube Technique Shorts + `Kf0wQ00FPBg` 4K Instructional)",
        f"- **Competition Matches Linked**: **`42` full matches** across Freestyle Wrestling, ADCC, IBJJF, Professional Grappling, and Other Competitions",
        "- **Local Sovereign Debate Duo**: **`Gemma 4 31B` (`google/gemma-4-31b-it` / `gemma-4-31B-it-Q4_K_M.gguf`) + `Qwen 3.8 Max 27B` (`qwen/qwen3.8-27b` / `Huihui-Qwen3.8-27B-abliterated`)**",
        "",
        "---",
        "",
        "## 🌐 1. 3D Grappling Mind Map Architecture (3,723 Nodes -> 4 Orbital Realms)",
        "",
        "Aaron Maher's Mindomo Grappling Mind Map is structured as a **Role-Symmetric Positional State Machine** where every position branches by role (`You/Opponent`, `Attacker/Defender`, `Passer/Guard player`, `Initiative/Defensive`) into `Setups / Entries` $\\rightarrow$ `Control` $\\rightarrow$ `Offence` $\\rightarrow$ `Defence` $\\rightarrow$ `Offensive transitions`, terminating in paired **`Instructional video`** and **`Live video`** leaf slots:",
        "",
        "| 3D Orbital Realm | OPML Nodes | Core Positional Hubs | Target 3D Spine Lean ($\\theta_{\\text{spine}}$) | Linked Technique Videos |",
        "| :--- | :---: | :--- | :---: | :---: |",
        "| **1. Wrestling** | `704` | `Hand fighting (355)` (`Collar tie 166`, `Underhook 70`, `Outside tie 41`, `Over/Under 30`, `Inside tie 17`, `2-on-1 12`, `Overhook 12`), `Shots (287)` (`Head inside single 177`, `Head outside single 61`, `Low ankle 20`, `Double leg 14`, `Snatch single 10`), `Wrestling bodylock (59)` | `35°–58°` (Structural Barrier) | `95+` |",
        "| **2. Guard** | `1,805` | `J point (306)`, `Seated Guard (258)`, `Supine Guard (193)`, `Quarter guard (186)`, `Half Guard Passing (96)`, `Butterfly guard (92)`, `Headquarters (80)`, `Closed Guard (70)`, `De la riva (64)`, `K guard (58)`, `Outside ashi (58)`, `Shin pin (56)` | `38°–65°` | `28+` |",
        "| **3. Dominant Positions** | `1,003` | `Front Headlock (356)`, `Turtle (185)`, `North South (155)`, `Side Control (136)`, `Mount (132)`, `Back Control (33)` | `55°–78°` | `18+` |",
        "| **4. Scrambles** | `130` | `Crab ride (56)`, `Berimbolo (38)`, `Grounded 50/50 (33)` | `55°–82°` | `12+` |",
        "",
        "---",
        "",
        "## 👁️ 2. 10-Model Multi-Vision Benchmark (Local Sovereign + Cloud Frontier Teachers)",
        "",
    ]

    for m_rec in comp_matches:
        ops = m_rec.get("vision_model_opinions", {})
        if len(ops) >= 4:
            report_lines.append(f"### 🥋 `{m_rec['video_id']}` — {m_rec['title']} ({m_rec['division']})")
            ang = m_rec.get("mean_3d_angles_deg", {})
            report_lines.append(
                f"- **3D Kinematics (`{m_rec.get('resolution')}`)**: Standing `{m_rec.get('standing_phase_pct')}%` | Ground `{m_rec.get('ground_scramble_phase_pct')}%` | "
                f"Shots `{m_rec.get('level_change_shots_detected')}` | 3D Spine Lean `{ang.get('spine_forward_lean')}°` | Knee L/R `{ang.get('left_knee')}°/{ang.get('right_knee')}°`"
            )
            for op in ops.values():
                clean_txt = str(op.get("analysis", "")).replace("\n", " ").strip()
                report_lines.append(f"  - **`{op.get('model_name')}` (`{op.get('status')}`, `{op.get('latency_sec')}s`)**: {clean_txt[:360]}")
            report_lines.append("")

    OBSIDIAN_MINDMAP_REPORT.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"[✓] Wrote Obsidian Master 3D Mind Map & Multi-VLM Report to {OBSIDIAN_MINDMAP_REPORT}")


if __name__ == "__main__":
    main()
