#!/usr/bin/env python3
"""
Real-Time Live Video, 3D Skeleton Overlay, 3D Mind Map (3,723 Nodes) & 10-VLM Live Feedback Studio
==================================================================================================
Location: 10_spatial_grappling_kinematics/app/realtime_feedback_studio.py
Port: 8765

Key Capabilities:
1. LIVE PLAYING VIDEO (`<video>` with HTTP 206 Range Streaming `/api/video/<video_id>.mp4` + YouTube sync):
   - Fixed `min-height: 420px; flex-shrink: 0;` Live Stage that NEVER collapses to 0px height.
   - Plays local 720p/4K MP4 competition matches & technique videos natively with a transparent
     `<canvas id="livePoseCanvas">` rendering real-time 3D Dual-Wrestler Skeletons (Referee Excluded),
     live 3D joint angles (`Spine Lean`, `Knee L/R`, `Elbow L/R`), and active 3D Mind Map node badges
     synchronized to `video.currentTime`.
2. LIVE PLAY-BY-PLAY AI STREAM & INSTANT LIVE FEEDBACK:
   - Synchronized side-by-side with the playing video: streams live frame-by-frame / timestamped
     biomechanical & Mind Map commentary as the video plays, and lets the user give 1-click (`👍 / 👎`)
     or typed (`Enter`) live feedback at the exact playing timestamp (`video.currentTime`) on the live frame.
3. INTERACTIVE 3D GRAPPLING MIND MAP (`3,723` OPML Nodes -> `48` 3D Orbital Clusters).
4. SIDE-BY-SIDE 10-MODEL VISION BENCHMARK (`Gemma 4 31B` + `Qwen 3.8 Max 27B` Debate Duo + Cloud Teachers).
5. EUFY SECURITY APP & L6 PIXEL 10 PRO XL INGESTION MODAL.
"""

import base64
import concurrent.futures
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2

APP_DIR = Path(__file__).resolve().parent
COMP_DIR = APP_DIR / "competitions"
VIDEOS_DIR = COMP_DIR / "videos"
TECH_VIDEOS_DIR = COMP_DIR / "technique_videos"
CLIPS_DIR = COMP_DIR / "clips"
JSON_DIR = COMP_DIR / "json"
FRAMES_DIR = COMP_DIR / "keyframes"
MASTER_JSON = COMP_DIR / "all_competitions_3d_summary.json"
MINDMAP_3D_JSON = COMP_DIR / "grappling_3d_mindmap_graph.json"
TECH_CATALOG_JSON = COMP_DIR / "technique_videos_catalog.json"
COACH_RULES_JSON = COMP_DIR / "coach_ground_truth_rules.json"
MODEL_LEADERBOARD_JSON = COMP_DIR / "vlm_model_leaderboard.json"
FFMPEG_BIN = "/Users/aaron/.local/bin/ffmpeg" if Path("/Users/aaron/.local/bin/ffmpeg").exists() else "ffmpeg"
OBSIDIAN_REPORT = (
    APP_DIR.parent.parent
    / "obsidian_vault"
    / "04_ANALYTICS"
    / "AARON_MAHER_COMPETITION_MATCHES_3D_ANALYSIS.md"
)
LORA_RLHF_JSONL = Path("/Users/aaron/DFS_UNIFIED/lora_datasets/grappling_vla_rlhf_feedback.jsonl")

from eufy_security_ingestor import (
    get_eufy_status,
    save_eufy_credentials,
    sync_eufy_clips_from_pixel10,
)
from mindmap_3d_engine import (
    EXPANDED_VISION_ROSTER,
    _load_secret,
    analyze_live_video_frame_at_timestamp,
    query_vlm_expanded,
    resolve_live_mindmap_position,
    resolve_or_download_video_path,
    strip_degree_jargon,
)


def ensure_extracted_clip(video_id: str, start_sec: float, end_sec: float) -> Optional[Path]:
    """
    Physically cuts a standalone 6-8 second MP4 sub-clip using ffmpeg so the browser player
    only loads and loops the exact clipped grappling exchange instead of the full uncut match.
    """
    CLIPS_DIR.mkdir(parents=True, exist_ok=True)
    req_s = round(max(0.0, float(start_sec)), 1)
    req_e = round(max(req_s + 4.0, float(end_sec)), 1)
    out_path = CLIPS_DIR / f"{video_id}_{req_s:.1f}_{req_e:.1f}.mp4"
    if out_path.exists() and out_path.stat().st_size > 8000:
        return out_path

    src = resolve_or_download_video_path(video_id, download_if_missing=True)
    if not src or not src.exists():
        return None

    try:
        cap = cv2.VideoCapture(str(src))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
        total_dur = (frames / fps) if frames > 0 else 30.0
        cap.release()
    except Exception:
        total_dur = 30.0

    dur = round(max(4.0, min(10.0, req_e - req_s)), 1)
    actual_start = round(max(0.0, min(req_s, max(0.0, total_dur - dur - 0.2))), 1)
    actual_dur = round(max(2.5, min(dur, total_dur - actual_start)), 1)

    try:
        subprocess.run(
            [
                FFMPEG_BIN,
                "-y",
                "-ss",
                str(actual_start),
                "-t",
                str(actual_dur),
                "-i",
                str(src),
                "-vf",
                "scale=-2:480",
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast",
                "-crf",
                "24",
                "-an",
                "-movflags",
                "+faststart",
                str(out_path),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=12,
        )
        if out_path.exists() and out_path.stat().st_size > 4000:
            return out_path
    except Exception:
        pass
    return src


def get_match_extracted_clips(match: Dict[str, Any]) -> List[Dict[str, Any]]:
    vid_id = str(match.get("video_id", "fbCpcA1DyWg"))
    node = str(match.get("primary_mindmap_node", "Collar tie (You)"))
    trans = match.get("mindmap_transitions", ["2-on-1 entry", "Knee-pull single", "Throw-by", "Front Headlock"])
    t0 = trans[0] if len(trans) > 0 else "Opening Tie-Up"
    t1 = trans[1] if len(trans) > 1 else "Level-Change Entry"
    t2 = trans[2] if len(trans) > 2 else "Chain Finish"
    windows = [
        (3.0, 10.0, 6.5, f"Clip 1: {node} — Setup & Hand-Fighting"),
        (9.5, 16.5, 13.0, f"Clip 2: {t0} — Inside Space & Tie-Up"),
        (15.5, 22.5, 18.0, f"Clip 3: {t1} — Primary Takedown / Guard Exchange"),
        (20.2, 27.2, 22.7, f"Clip 4: {t2} — Scramble & Finish"),
    ]
    clips = []
    for idx, (s, e, mid_ts, label) in enumerate(windows):
        clips.append({
            "clip_index": idx + 1,
            "label": label,
            "start_sec": s,
            "end_sec": e,
            "mid_timestamp_sec": mid_ts,
            "duration_sec": round(e - s, 1),
            "clip_url": f"/api/clip/{vid_id}_{s:.1f}_{e:.1f}.mp4",
        })
    return clips


def load_model_leaderboard() -> Dict[str, Any]:
    if MODEL_LEADERBOARD_JSON.exists():
        try:
            data = json.loads(MODEL_LEADERBOARD_JSON.read_text(encoding="utf-8"))
            models = data.get("models", [])
            models_sorted = sorted(
                models,
                key=lambda x: (-int(x.get("elo_rating", 1500)), float(x.get("avg_latency_ms", 9999.0))),
            )
            for idx, m_item in enumerate(models_sorted):
                m_item["rank"] = idx + 1
            data["models"] = models_sorted

            rt_candidates = [m for m in models_sorted if m.get("realtime_capable")]
            deep_candidates = [m for m in models_sorted if not m.get("realtime_capable")] or models_sorted
            verdict = data.get("architecture_verdict", {})
            if rt_candidates:
                verdict["recommended_realtime_model_id"] = rt_candidates[0]["model_id"]
                verdict["recommended_realtime_model_name"] = rt_candidates[0]["model_name"]
            if deep_candidates:
                verdict["recommended_deep_teacher_model_id"] = deep_candidates[0]["model_id"]
                verdict["recommended_deep_teacher_model_name"] = deep_candidates[0]["model_name"]
            if models_sorted:
                verdict["overall_superior_model_id"] = models_sorted[0]["model_id"]
                verdict["overall_superior_model_name"] = models_sorted[0]["model_name"]
            data["architecture_verdict"] = verdict
            return data
        except Exception:
            pass
    return {"architecture_verdict": {}, "models": []}


def record_model_review_vote(
    model_id_or_name: str,
    vote: str,
    video_id: str,
    ts_sec: float,
    clip_url: str,
    comment: str,
) -> Dict[str, Any]:
    board = load_model_leaderboard()
    models = board.get("models", [])
    target = None
    q = str(model_id_or_name or "").lower().strip()
    for m in models:
        if m.get("model_id", "").lower() == q or m.get("model_name", "").lower() == q or q in m.get("model_name", "").lower():
            target = m
            break
    if not target and models:
        target = models[0]
    if target:
        if vote == "good":
            target["thumbs_up"] = int(target.get("thumbs_up", 0)) + 1
            target["elo_rating"] = int(target.get("elo_rating", 1500)) + 24
        elif vote == "bad":
            target["thumbs_down"] = int(target.get("thumbs_down", 0)) + 1
            target["elo_rating"] = max(1100, int(target.get("elo_rating", 1500)) - 24)
        else:
            target["critique_count"] = int(target.get("critique_count", 0)) + 1
            target["elo_rating"] = max(1100, int(target.get("elo_rating", 1500)) - 10)
        up = int(target.get("thumbs_up", 0))
        dn = int(target.get("thumbs_down", 0))
        cr = int(target.get("critique_count", 0))
        target["total_reviews"] = up + dn + cr
        target["accuracy_pct"] = round(100.0 * up / max(1, up + dn), 1) if (up + dn) > 0 else None
        revs = target.get("reviews", [])
        revs.insert(
            0,
            {
                "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "video_id": video_id,
                "timestamp_sec": ts_sec,
                "vote": vote,
                "clip_url": clip_url,
                "comment": strip_degree_jargon(comment),
            },
        )
        target["reviews"] = revs[:25]
        MODEL_LEADERBOARD_JSON.write_text(json.dumps(board, indent=2), encoding="utf-8")
    return load_model_leaderboard()


def init_seed_feedback():
    COMP_DIR.mkdir(parents=True, exist_ok=True)
    CLIPS_DIR.mkdir(parents=True, exist_ok=True)
    LORA_RLHF_JSONL.parent.mkdir(parents=True, exist_ok=True)

    default_rules = [
        {
            "id": "rule_001",
            "timestamp_utc": "2026-10-14T13:25:47Z",
            "video_id": "fbCpcA1DyWg",
            "video_timestamp_sec": 22.7,
            "clip_start_sec": 20.2,
            "clip_end_sec": 27.2,
            "clip_video_url": "/api/clip/fbCpcA1DyWg_20.2_27.2.mp4",
            "clip_thumb_url": "/keyframes/fbCpcA1DyWg_3d_grid.jpg",
            "mindmap_breadcrumb": "Wrestling ➔ Hand fighting ➔ Collar tie (You)",
            "category": "Ruleset & Posture Biomechanics",
            "target_model": "All Vision Models",
            "coach_feedback": (
                "It is due to wrestling having points score very easy compared to BJJ so its much more risky "
                "to not try and have your body in the way and rely on reflexes."
            ),
            "rejected_qwen_opinion": (
                "Aaron Maher's forward posture appears most pronounced in Freestyle Wrestling matches, "
                "suggesting a purely aggressive offensive stance."
            ),
            "chosen_revised_opinion": (
                "In Freestyle Wrestling, points score much more easily (via step-outs, exposure, and quick leg attacks) "
                "than in BJJ/ADCC. Therefore, maintaining a low, hinged wrestling stance is a mandatory defensive structural barrier "
                "('keeping your body in the way' with head, hands, and forearms in front of the hips) rather than standing tall "
                "and relying purely on reactive reflexes."
            ),
            "model_used": "Gemma 4 31B + Qwen 3.8 Max Debate Duo + Coach RLHF",
        }
    ]
    if not COACH_RULES_JSON.exists():
        COACH_RULES_JSON.write_text(json.dumps(default_rules, indent=2), encoding="utf-8")
    if not LORA_RLHF_JSONL.exists():
        with open(LORA_RLHF_JSONL, "a", encoding="utf-8") as f:
            f.write(json.dumps(default_rules[0]) + "\n")


_MATCH_BY_ID_CACHE: Dict[str, Dict[str, Any]] = {}


def load_matches() -> List[Dict[str, Any]]:
    matches = []
    if MASTER_JSON.exists():
        try:
            raw = json.loads(MASTER_JSON.read_text(encoding="utf-8"))
            matches = raw if isinstance(raw, list) else raw.get("matches", [])
        except Exception:
            matches = []

    instr_json = APP_DIR / "inbox" / "Kf0wQ00FPBg_Collar tie 2 on 1 entry to collar tie_data.json"
    if instr_json.exists() and not any(m.get("video_id") == "Kf0wQ00FPBg" for m in matches):
        matches.insert(
            1,
            {
                "video_id": "Kf0wQ00FPBg",
                "url": "https://youtu.be/Kf0wQ00FPBg",
                "division": "Instructional Footage",
                "title": "Collar tie 2 on 1 entry to collar tie (4K Instructional)",
                "duration_sec": 33.5,
                "resolution": "3840x2160",
                "sampled_frames": 1005,
                "poses_detected_frames": 991,
                "dual_athlete_frames": 26,
                "standing_phase_pct": 100.0,
                "ground_scramble_phase_pct": 0.0,
                "level_change_shots_detected": 2,
                "mean_3d_angles_deg": {
                    "spine_forward_lean": 38.0,
                    "left_elbow": 107.4,
                    "right_elbow": 163.3,
                    "left_hip": 169.5,
                    "right_hip": 178.9,
                    "left_knee": 148.2,
                    "right_knee": 145.5,
                },
                "tactical_note": (
                    "Mind Map Position [Wrestling ➔ Hand fighting ➔ 2-on-1 (You)]: Establish heavy collar-tie pressure first, "
                    "then capture the wrist and above-elbow tricep shelf to angle onto the flank. Chain directly into your "
                    "Mind Map transitions: re-collar snapdown, same-side ankle pick, snatch single, or climb to rear bodylock."
                ),
                "vision_model_opinions": {},
                "feedback_history": [],
            },
        )

    windows = [(3.0, 10.0, 6.5), (9.5, 16.5, 13.0), (15.5, 22.5, 18.0), (20.2, 27.2, 22.7)]
    for m in matches:
        vid_id = m.get("video_id", "")
        local_p = resolve_or_download_video_path(vid_id, download_if_missing=False)
        m["has_local_mp4"] = bool(local_p and local_p.exists())
        ang = m.get("mean_3d_angles_deg", {}) or {}
        mm_pos = resolve_live_mindmap_position(
            m,
            float(ang.get("spine_forward_lean", 45.0) or 45.0),
            float(ang.get("left_knee", 138.0) or 138.0),
            float(ang.get("right_knee", 140.0) or 140.0),
            float(ang.get("left_elbow", 115.0) or 115.0),
            float(ang.get("right_elbow", 120.0) or 120.0),
            has_grounded=(float(m.get("ground_scramble_phase_pct", 0) or 0) > 50.0),
            selected_athletes=[],
            timestamp_sec=10.0,
        )
        m["primary_mindmap_node"] = mm_pos["active_mindmap_node"]
        m["primary_mindmap_node_id"] = mm_pos["node_id"]
        m["mindmap_breadcrumb"] = mm_pos["mindmap_breadcrumb"]
        m["posture_summary"] = mm_pos["posture_summary"]
        m["mindmap_transitions"] = mm_pos["mindmap_transitions"]
        m["linked_technique_videos"] = mm_pos["linked_technique_videos"]
        m["extracted_clips"] = get_match_extracted_clips(m)

        raw_note = str(m.get("tactical_note", "") or "")
        if not raw_note or "°" in raw_note or "degree" in raw_note.lower() or "Telemetry:" in raw_note:
            m["tactical_note"] = mm_pos["coaching_advice"]
        else:
            m["tactical_note"] = strip_degree_jargon(raw_note)

        ops = m.get("vision_model_opinions", {}) or {}
        for idx, (op_key, op) in enumerate(ops.items()):
            if isinstance(op, dict):
                if op.get("analysis"):
                    if "Telemetry (" in op["analysis"]:
                        op["analysis"] = mm_pos["coaching_advice"]
                    else:
                        op["analysis"] = strip_degree_jargon(str(op["analysis"]))
                w_s, w_e, w_mid = windows[idx % len(windows)]
                op["clip_start_sec"] = float(op.get("clip_start_sec") or w_s)
                op["clip_end_sec"] = float(op.get("clip_end_sec") or w_e)
                op["clip_timestamp_sec"] = float(op.get("clip_timestamp_sec") or w_mid)
                op["clip_video_url"] = f"/api/clip/{vid_id}_{op['clip_start_sec']:.1f}_{op['clip_end_sec']:.1f}.mp4"
                op["mindmap_breadcrumb"] = mm_pos["mindmap_breadcrumb"]
        if vid_id:
            _MATCH_BY_ID_CACHE[vid_id] = m

    # Sort matches that have local MP4s + 10 VLMs to the top so live video is instant
    matches.sort(
        key=lambda m: (
            0 if m.get("video_id") == "fbCpcA1DyWg"
            else (1 if m.get("has_local_mp4") else (2 if len(m.get("vision_model_opinions", {})) > 2 else 3))
        )
    )
    return matches


def get_match_meta_fast(video_id: str) -> Dict[str, Any]:
    if not _MATCH_BY_ID_CACHE:
        load_matches()
    return _MATCH_BY_ID_CACHE.get(
        video_id,
        {
            "video_id": video_id,
            "title": video_id,
            "division": "Grappling",
            "mean_3d_angles_deg": {},
        },
    )


def load_mindmap_3d() -> Dict[str, Any]:
    if MINDMAP_3D_JSON.exists():
        try:
            return json.loads(MINDMAP_3D_JSON.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"nodes": [], "edges": [], "total_opml_outline_nodes": 3723}


def load_coach_rules() -> List[Dict[str, Any]]:
    if COACH_RULES_JSON.exists():
        try:
            rules = json.loads(COACH_RULES_JSON.read_text(encoding="utf-8"))
            for r in rules:
                for k in ("coach_feedback", "rejected_qwen_opinion", "chosen_revised_opinion"):
                    if r.get(k):
                        r[k] = strip_degree_jargon(str(r[k]))
                vid_id = str(r.get("video_id", "fbCpcA1DyWg"))
                if vid_id.startswith("GLOBAL_") or not vid_id:
                    vid_id = "fbCpcA1DyWg"
                    r["video_id"] = vid_id
                ts = float(r.get("video_timestamp_sec") or 22.7)
                if ts <= 14.0:
                    c_start, c_end = 9.5, 16.5
                elif ts <= 19.5:
                    c_start, c_end = 15.5, 22.5
                else:
                    c_start, c_end = 20.2, 27.2
                r["video_timestamp_sec"] = ts
                r["clip_start_sec"] = float(r.get("clip_start_sec") or c_start)
                r["clip_end_sec"] = float(r.get("clip_end_sec") or c_end)
                r["clip_video_url"] = f"/api/clip/{vid_id}_{r['clip_start_sec']:.1f}_{r['clip_end_sec']:.1f}.mp4"
                if not r.get("clip_thumb_url") or "GLOBAL_" in str(r.get("clip_thumb_url", "")):
                    r["clip_thumb_url"] = f"/keyframes/{vid_id}_3d_grid.jpg"
                if not r.get("mindmap_breadcrumb"):
                    r["mindmap_node"] = "Collar tie (You)"
                    r["mindmap_breadcrumb"] = "Wrestling ➔ Hand fighting ➔ Collar tie (You)"
            return rules
        except Exception:
            pass
    return []


def re_evaluate_with_qwen(
    match: Dict[str, Any],
    coach_feedback: str,
    video_timestamp_sec: float,
    category: str,
    all_rules: List[Dict[str, Any]],
    target_model_name: str = "All Vision Models",
    live_frame_b64: str = "",
) -> Dict[str, str]:
    rules_context = "\n".join(
        f"- [{r.get('category', 'Rule')}]: \"{r.get('coach_feedback', '')}\" -> {r.get('chosen_revised_opinion', '')}"
        for r in all_rules[-8:]
    )
    angles = match.get("mean_3d_angles_deg", {}) or {}
    mm_pos = resolve_live_mindmap_position(
        match,
        float(angles.get("spine_forward_lean", 45.0) or 45.0),
        float(angles.get("left_knee", 138.0) or 138.0),
        float(angles.get("right_knee", 140.0) or 140.0),
        float(angles.get("left_elbow", 115.0) or 115.0),
        float(angles.get("right_elbow", 120.0) or 120.0),
        has_grounded=(float(match.get("ground_scramble_phase_pct", 0) or 0) > 50.0),
        selected_athletes=[],
        timestamp_sec=video_timestamp_sec,
    )
    trans_str = ", ".join(mm_pos["mindmap_transitions"][:4])
    user_prompt = (
        f"Match/Technique: {match.get('title')} (Division: {match.get('division')}, Timestamp: {video_timestamp_sec}s)\n"
        f"Target Model Critiqued: {target_model_name}\n"
        f"Active Mind Map Node: {mm_pos['mindmap_breadcrumb']}\n"
        f"Posture & Control Read: {mm_pos['posture_summary']} — {mm_pos['control_mechanics']}\n"
        f"Available Mind Map Next Transitions: {trans_str}\n\n"
        f"Previous Analysis: \"{match.get('tactical_note', '')}\"\n\n"
        f"NEW LIVE COACH FEEDBACK AT t={video_timestamp_sec}s ({category}): \"{coach_feedback}\"\n\n"
        "STRICT COACHING RULE: Do NOT mention any raw degree numbers (never say '56.4 degrees', '138° knee', etc.). "
        "Provide the corrected 2-3 sentence digestible coaching analysis grounded in Aaron Maher's Grappling Mind Map that directly incorporates the coach's feedback."
    )

    or_key = _load_secret("OPENROUTER_API_KEY")
    if or_key:
        try:
            content_list: List[Dict[str, Any]] = []
            if live_frame_b64:
                clean_b64 = live_frame_b64.split(",", 1)[-1]
                content_list.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{clean_b64}"}})
            content_list.append({"type": "text", "text": user_prompt})
            req = urllib.request.Request(
                "https://openrouter.ai/api/v1/chat/completions",
                data=json.dumps({
                    "model": "google/gemma-4-31b-it",
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are the Lauburu Sovereign Debate Duo (Gemma 4 31B + Qwen 3.8 Max 27B) "
                                "incorporating real-time coach RLHF feedback on live grappling video. Never output raw joint degree numbers.\n"
                                f"ESTABLISHED GROUND-TRUTH RULES:\n{rules_context}"
                            ),
                        },
                        {"role": "user", "content": content_list},
                    ],
                    "max_tokens": 320,
                    "temperature": 0.25,
                }).encode("utf-8"),
                headers={"Authorization": f"Bearer {or_key}", "Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                ans = strip_degree_jargon((data["choices"][0]["message"].get("content") or "").strip())
                if ans:
                    return {"revised_opinion": ans, "model_used": "Gemma 4 31B Vision + Coach Live RLHF"}
        except Exception:
            pass

    return {
        "revised_opinion": (
            f"[Coach Ground-Truth @ {video_timestamp_sec}s • {mm_pos['mindmap_breadcrumb']}]: {coach_feedback} — "
            f"{mm_pos['posture_summary']}. Next Mind Map transitions: {trans_str}."
        ),
        "model_used": "Coach Direct Mind Map Override",
    }


def append_feedback_to_obsidian(entry: Dict[str, Any]):
    if not OBSIDIAN_REPORT.exists():
        return
    text = OBSIDIAN_REPORT.read_text(encoding="utf-8")
    section_header = "## 🎯 Coach Real-Time Ground-Truth Corrections (RLHF Log)"
    bullet = (
        f"- **`{entry['timestamp_utc']}` | `{entry['video_id']}` (@ `{entry['video_timestamp_sec']}s`) | {entry['category']} ({entry.get('target_model', 'VLA')})**\n"
        f"  - **Coach Aaron Maher Feedback**: *\"{entry['coach_feedback']}\"*\n"
        f"  - **Updated Ground-Truth Analysis (`{entry['model_used']}`)**: {entry['chosen_revised_opinion']}\n"
    )
    if section_header not in text:
        text = text + f"\n\n---\n\n{section_header}\n\n{bullet}"
    else:
        text = text + f"\n{bullet}"
    OBSIDIAN_REPORT.write_text(text, encoding="utf-8")


HTML_UI = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Lauburu Live Grappling Video, 3D Skeleton & Real-Time VLM Feedback Studio</title>
<style>
  :root {
    --bg: #0b0f17;
    --panel: #131a27;
    --panel-alt: #1a2436;
    --accent: #10b981;
    --accent-hover: #059669;
    --blue: #38bdf8;
    --purple: #a855f7;
    --warn: #f59e0b;
    --danger: #ef4444;
    --text: #f1f5f9;
    --muted: #94a3b8;
    --border: #26334d;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
    display: flex;
    flex-direction: column;
    height: 100vh;
    overflow: hidden;
  }
  header {
    background: var(--panel);
    border-bottom: 1px solid var(--border);
    padding: 9px 16px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 10px;
    flex-shrink: 0;
  }
  header h1 { font-size: 15px; font-weight: 700; display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
  .badge {
    background: rgba(16, 185, 129, 0.15);
    color: var(--accent);
    border: 1px solid var(--accent);
    font-size: 11px;
    padding: 3px 8px;
    border-radius: 999px;
    font-weight: 600;
  }
  .badge.live-pulse {
    background: rgba(239, 68, 68, 0.2);
    color: #fca5a5;
    border-color: var(--danger);
    animation: pulseRed 1.8s infinite;
  }
  @keyframes pulseRed {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.55; }
  }
  .badge.debate {
    background: rgba(56, 189, 248, 0.15);
    color: var(--blue);
    border-color: var(--blue);
  }
  .badge.eufy {
    background: rgba(168, 85, 247, 0.15);
    color: #c084fc;
    border-color: var(--purple);
    cursor: pointer;
  }
  .workspace {
    display: grid;
    grid-template-columns: 285px 1fr 440px;
    flex: 1;
    overflow: hidden;
  }
  .sidebar {
    background: var(--panel);
    border-right: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
  .sidebar-header {
    padding: 10px;
    border-bottom: 1px solid var(--border);
  }
  .sidebar-header input, .sidebar-header select {
    width: 100%;
    background: var(--bg);
    color: var(--text);
    border: 1px solid var(--border);
    padding: 7px 10px;
    border-radius: 6px;
    font-size: 12.5px;
    margin-bottom: 6px;
  }
  .match-list {
    flex: 1;
    overflow-y: auto;
    padding: 8px;
  }
  .match-item {
    padding: 9px 10px;
    border-radius: 8px;
    margin-bottom: 6px;
    cursor: pointer;
    border: 1px solid transparent;
    transition: all 0.15s;
  }
  .match-item:hover { background: var(--panel-alt); }
  .match-item.active {
    background: rgba(16, 185, 129, 0.14);
    border-color: var(--accent);
  }
  .match-div { font-size: 10px; text-transform: uppercase; color: var(--accent); font-weight: 700; letter-spacing: 0.4px; display: flex; justify-content: space-between; align-items: center; }
  .vlm-count-pill { background: rgba(56, 189, 248, 0.2); color: var(--blue); padding: 1px 6px; border-radius: 99px; font-size: 9.5px; }
  .mp4-pill { background: rgba(16, 185, 129, 0.22); color: #6ee7b7; padding: 1px 6px; border-radius: 99px; font-size: 9.5px; margin-left: 4px; }
  .match-title { font-size: 12.5px; font-weight: 600; margin: 3px 0; line-height: 1.3; }
  .match-meta { font-size: 11px; color: var(--muted); }

  .center-stage {
    display: flex;
    flex-direction: column;
    overflow-y: auto;
    padding: 12px 14px;
    gap: 10px;
  }
  .view-tabs {
    display: flex;
    gap: 6px;
    align-items: center;
    flex-wrap: wrap;
    flex-shrink: 0;
  }
  .tab-btn {
    background: var(--panel);
    color: var(--text);
    border: 1px solid var(--border);
    padding: 6px 11px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 12px;
    font-weight: 600;
  }
  .tab-btn.active {
    background: var(--accent);
    color: #052e16;
    border-color: var(--accent);
  }
  .tab-btn.mindmap-tab {
    border-color: var(--purple);
    color: #d8b4fe;
  }
  .tab-btn.mindmap-tab.active {
    background: var(--purple);
    color: #fff;
  }
  .tab-btn.run-vlm {
    background: rgba(56, 189, 248, 0.16);
    color: var(--blue);
    border-color: var(--blue);
  }

  /* =========================================================================
     UN-COLLAPSIBLE LIVE VIDEO + REAL-TIME 3D SKELETON & LIVE FEEDBACK STAGE
     ========================================================================= */
  .live-video-stage {
    display: grid;
    grid-template-columns: 1.38fr 1fr;
    gap: 12px;
    height: 415px;
    min-height: 415px;
    flex-shrink: 0;
    width: 100%;
  }
  .video-player-box {
    position: relative;
    width: 100%;
    height: 100%;
    min-height: 415px;
    background: #000;
    border-radius: 10px;
    overflow: hidden;
    border: 1px solid var(--accent);
    box-shadow: 0 0 20px rgba(16, 185, 129, 0.12);
  }
  #liveCameraRig {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    transform-origin: 0 0;
    transition: transform 0.065s linear;
    will-change: transform;
  }
  .video-player-box video {
    width: 100%;
    height: 100%;
    object-fit: fill;
    display: block;
    background: #000;
  }
  .video-player-box iframe {
    width: 100%;
    height: 100%;
    display: block;
    background: #000;
  }
  #livePoseCanvas {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    pointer-events: auto;
    cursor: crosshair;
    z-index: 5;
  }
  .video-hud-topbar {
    position: absolute;
    top: 8px;
    left: 10px;
    right: 10px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 6px;
    z-index: 8;
    pointer-events: none;
  }
  .video-bottom-controls {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    padding: 6px 10px;
    background: linear-gradient(to top, rgba(7, 11, 18, 0.94), rgba(7, 11, 18, 0.65));
    border-top: 1px solid rgba(16, 185, 129, 0.35);
    display: flex;
    align-items: center;
    gap: 8px;
    z-index: 8;
  }
  .vbc-btn {
    background: rgba(16, 185, 129, 0.16);
    border: 1px solid rgba(16, 185, 129, 0.55);
    color: #f8fafc;
    font-size: 11px;
    font-weight: 700;
    padding: 4px 8px;
    border-radius: 5px;
    cursor: pointer;
    white-space: nowrap;
  }
  .vbc-btn:hover {
    background: var(--accent);
    color: #042f1e;
  }
  #liveVideoScrubber {
    flex: 1;
    accent-color: var(--accent);
    cursor: pointer;
    height: 5px;
  }
  .hud-pill {
    background: rgba(11, 15, 23, 0.85);
    border: 1px solid rgba(16, 185, 129, 0.6);
    color: #f8fafc;
    font-size: 11px;
    font-weight: 700;
    padding: 4px 9px;
    border-radius: 6px;
    backdrop-filter: blur(4px);
    pointer-events: auto;
  }
  .hud-pill.mindmap-node-pill {
    border-color: var(--purple);
    color: #e9d5ff;
  }

  /* Right half of Live Stage: Live Play-by-Play Ticker + Instant Live Feedback */
  .live-stream-feed-box {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 10px;
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 415px;
    overflow: hidden;
  }
  .live-stream-header {
    padding: 8px 12px;
    background: var(--panel-alt);
    border-bottom: 1px solid var(--border);
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 11.5px;
    font-weight: 700;
  }
  .live-ticker-list {
    flex: 1;
    overflow-y: auto;
    padding: 8px 10px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .live-event-card {
    background: var(--bg);
    border: 1px solid var(--border);
    border-left: 3px solid var(--accent);
    border-radius: 7px;
    padding: 8px 10px;
    font-size: 11.5px;
    line-height: 1.4;
  }
  .live-event-card.coach-event {
    border-left-color: var(--warn);
    background: rgba(245, 158, 11, 0.07);
  }
  .lec-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 10.5px;
    font-weight: 700;
    color: var(--accent);
    margin-bottom: 4px;
  }
  .lec-frame-row {
    display: flex;
    gap: 8px;
    align-items: flex-start;
  }
  .lec-thumb {
    width: 96px;
    height: 54px;
    object-fit: cover;
    border-radius: 4px;
    border: 1px solid var(--border);
    flex-shrink: 0;
  }
  .live-quick-bar {
    padding: 8px 10px;
    border-top: 1px solid var(--border);
    background: var(--panel-alt);
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .live-quick-input-row {
    display: flex;
    gap: 6px;
  }
  .live-quick-input-row input {
    flex: 1;
    background: var(--bg);
    color: var(--text);
    border: 1px solid var(--border);
    padding: 7px 10px;
    border-radius: 6px;
    font-size: 12px;
  }
  .live-quick-btn {
    background: var(--accent);
    color: #042f1e;
    border: none;
    padding: 6px 10px;
    border-radius: 6px;
    font-size: 11.5px;
    font-weight: 700;
    cursor: pointer;
    white-space: nowrap;
  }

  /* 3D Mind Map Interactive Canvas Container */
  .mindmap-container {
    display: none;
    grid-template-columns: 1fr 330px;
    gap: 12px;
    height: 430px;
    min-height: 430px;
    flex-shrink: 0;
    background: #070b12;
    border: 1px solid var(--border);
    border-radius: 10px;
    overflow: hidden;
  }
  .mindmap-canvas-wrap {
    position: relative;
    width: 100%;
    height: 100%;
  }
  #mindmapCanvas {
    width: 100%;
    height: 100%;
    cursor: grab;
    display: block;
  }
  #mindmapCanvas:active { cursor: grabbing; }
  .mindmap-hud {
    position: absolute;
    top: 10px;
    left: 10px;
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    pointer-events: auto;
  }
  .mindmap-inspector {
    background: var(--panel);
    border-left: 1px solid var(--border);
    padding: 12px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 8px;
    font-size: 12px;
  }

  .telemetry-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 8px;
    flex-shrink: 0;
  }
  .metric-card {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 8px 11px;
  }
  .metric-label { font-size: 10.5px; color: var(--muted); }
  .metric-val { font-size: 15px; font-weight: 700; color: var(--accent); margin-top: 2px; }
  .grid-preview {
    width: 100%;
    max-height: 420px;
    object-fit: contain;
    background: #000;
    border-radius: 8px;
    border: 1px solid var(--border);
    display: none;
    flex-shrink: 0;
  }

  .vlm-matrix-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-top: 2px;
    flex-shrink: 0;
  }
  .vlm-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(295px, 1fr));
    gap: 10px;
    flex-shrink: 0;
  }
  .vlm-card {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 10px 12px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    gap: 8px;
  }
  .vlm-card.local-tier { border-left: 3px solid var(--accent); }
  .vlm-card.cloud-tier { border-left: 3px solid var(--blue); }
  .vlm-card.voted-good { border-color: var(--accent); background: rgba(16, 185, 129, 0.08); }
  .vlm-card.voted-bad { border-color: var(--danger); background: rgba(239, 68, 68, 0.08); opacity: 0.78; }
  .vlm-card-top { display: flex; justify-content: space-between; align-items: center; gap: 6px; }
  .vlm-name { font-size: 12px; font-weight: 700; color: var(--text); }
  .vlm-tier-tag { font-size: 10px; color: var(--muted); background: var(--bg); padding: 2px 6px; border-radius: 4px; }
  .vlm-text { font-size: 11.5px; line-height: 1.42; color: #cbd5e1; }
  .vlm-actions { display: flex; gap: 6px; }
  .vlm-btn {
    flex: 1;
    background: var(--panel-alt);
    border: 1px solid var(--border);
    color: var(--text);
    padding: 5px 6px;
    border-radius: 5px;
    font-size: 11px;
    font-weight: 600;
    cursor: pointer;
  }
  .vlm-btn.good:hover { border-color: var(--accent); color: var(--accent); }
  .vlm-btn.bad:hover { border-color: var(--danger); color: var(--danger); }
  .vlm-btn.crit:hover { border-color: var(--warn); color: var(--warn); }
  .vlm-clip-box {
    position: relative;
    background: #05080f;
    border: 1px solid var(--border);
    border-radius: 6px;
    overflow: hidden;
    margin-top: 6px;
  }
  .vlm-clip-media-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 4px;
    background: #000;
  }
  .vlm-inline-clip {
    width: 100%;
    height: 86px;
    object-fit: cover;
    display: block;
    background: #000;
    cursor: pointer;
  }
  .vlm-inline-poster {
    width: 100%;
    height: 86px;
    object-fit: cover;
    display: block;
    background: #000;
    cursor: pointer;
  }
  .vlm-clip-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 4px 7px;
    background: rgba(19, 26, 39, 0.95);
    border-top: 1px solid var(--border);
    font-size: 10px;
    color: var(--muted);
  }
  .verify-clip-btn {
    background: rgba(16, 185, 129, 0.16);
    border: 1px solid rgba(16, 185, 129, 0.55);
    color: #6ee7b7;
    padding: 2px 7px;
    border-radius: 4px;
    font-size: 10px;
    font-weight: 700;
    cursor: pointer;
  }
  .verify-clip-btn:hover {
    background: var(--accent);
    color: #042f1e;
  }
  .review-clip-box {
    margin-top: 6px;
    background: #05080f;
    border: 1px solid var(--border);
    border-radius: 6px;
    overflow: hidden;
  }
  .review-clip-row {
    display: grid;
    grid-template-columns: 1.25fr 1fr;
    gap: 4px;
    background: #000;
  }
  .review-inline-video {
    width: 100%;
    height: 92px;
    object-fit: cover;
    display: block;
    background: #000;
  }
  .review-inline-thumb {
    width: 100%;
    height: 92px;
    object-fit: cover;
    display: block;
    background: #000;
  }

  /* Right Panel */
  .feedback-panel {
    background: var(--panel);
    border-left: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
  .panel-section {
    padding: 12px 14px;
    border-bottom: 1px solid var(--border);
  }
  .section-title {
    font-size: 11.5px;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    color: var(--muted);
    font-weight: 700;
    margin-bottom: 8px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .qwen-opinion-box {
    background: var(--bg);
    border: 1px solid var(--border);
    border-left: 3px solid var(--warn);
    padding: 10px 12px;
    border-radius: 6px;
    font-size: 12px;
    line-height: 1.45;
    max-height: 130px;
    overflow-y: auto;
  }
  .qwen-opinion-box.corrected { border-left-color: var(--accent); }

  .feedback-form {
    padding: 12px 14px;
    border-bottom: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .row { display: flex; gap: 6px; align-items: center; }
  .row select, .row input {
    background: var(--bg);
    color: var(--text);
    border: 1px solid var(--border);
    padding: 6px 8px;
    border-radius: 6px;
    font-size: 12px;
  }
  .ts-btn {
    background: var(--panel-alt);
    color: var(--accent);
    border: 1px solid var(--accent);
    padding: 6px 9px;
    border-radius: 6px;
    font-size: 11.5px;
    cursor: pointer;
    font-weight: 600;
  }
  textarea {
    width: 100%;
    height: 68px;
    background: var(--bg);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 8px;
    font-size: 12px;
    resize: none;
    font-family: inherit;
  }
  textarea:focus { outline: 1px solid var(--accent); }
  .submit-btn {
    background: var(--accent);
    color: #042f1e;
    border: none;
    padding: 9px;
    border-radius: 8px;
    font-weight: 700;
    font-size: 12.5px;
    cursor: pointer;
  }
  .submit-btn:hover { background: var(--accent-hover); }
  .submit-btn:disabled { opacity: 0.5; cursor: wait; }

  .history-list {
    flex: 1;
    overflow-y: auto;
    padding: 10px 14px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .history-card {
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 9px 11px;
    font-size: 11.5px;
    line-height: 1.4;
  }
  .history-card .hc-meta { color: var(--accent); font-weight: 700; margin-bottom: 3px; font-size: 10.5px; }
  .history-card .hc-coach { color: #fcd34d; margin-bottom: 5px; }
  .history-card .hc-revised { color: var(--text); border-top: 1px solid var(--border); padding-top: 5px; }

  .modal-backdrop {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.75);
    z-index: 999;
    align-items: center;
    justify-content: center;
  }
  .modal {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 12px;
    width: 480px;
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .modal input {
    width: 100%;
    background: var(--bg);
    color: var(--text);
    border: 1px solid var(--border);
    padding: 8px 10px;
    border-radius: 6px;
    font-size: 13px;
  }
  .pill-link {
    display: inline-block;
    background: var(--panel-alt);
    border: 1px solid var(--border);
    color: var(--blue);
    padding: 3px 7px;
    border-radius: 5px;
    font-size: 11px;
    margin: 2px;
    cursor: pointer;
  }
  .pill-link:hover { border-color: var(--accent); color: var(--accent); }

  /* Dual Portal Switcher (User-Facing Athlete Side vs Admin Model Review Studio) */
  .portal-switcher {
    display: flex;
    gap: 6px;
    background: var(--bg);
    padding: 4px;
    border-radius: 8px;
    border: 1px solid var(--border);
  }
  .portal-btn {
    background: transparent;
    color: var(--muted);
    border: 1px solid transparent;
    padding: 6px 12px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 700;
    cursor: pointer;
    transition: all 0.15s;
  }
  .portal-btn.active-user {
    background: var(--accent);
    color: #042f1e;
  }
  .portal-btn.active-admin {
    background: var(--purple);
    color: #ffffff;
    box-shadow: 0 0 12px rgba(168, 85, 247, 0.35);
  }

  /* Extracted 7s Sub-Clips Selector Strip */
  .clips-strip-bar {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
    background: rgba(16, 185, 129, 0.07);
    border: 1px solid rgba(16, 185, 129, 0.35);
    border-radius: 8px;
    padding: 7px 10px;
    flex-shrink: 0;
  }
  .clip-pill-btn {
    background: var(--panel);
    color: var(--text);
    border: 1px solid var(--border);
    padding: 5px 10px;
    border-radius: 6px;
    font-size: 11.5px;
    font-weight: 600;
    cursor: pointer;
  }
  .clip-pill-btn.active {
    background: var(--accent);
    color: #042f1e;
    border-color: var(--accent);
    font-weight: 700;
  }
  .clip-pill-btn.full-video {
    border-color: var(--blue);
    color: var(--blue);
    margin-left: auto;
  }
  .clip-pill-btn.full-video.active {
    background: var(--blue);
    color: #082f49;
  }

  /* Admin Separate Model Reviewer & Real-Time vs 72B Benchmark Box */
  .admin-studio-box {
    display: none;
    flex-direction: column;
    gap: 12px;
    background: rgba(168, 85, 247, 0.06);
    border: 1px solid rgba(168, 85, 247, 0.45);
    border-radius: 10px;
    padding: 12px 14px;
    flex-shrink: 0;
  }
  .admin-verdict-banner {
    background: var(--panel);
    border: 1px solid var(--border);
    border-left: 4px solid var(--purple);
    border-radius: 8px;
    padding: 10px 12px;
    font-size: 12px;
    line-height: 1.45;
  }
  .single-model-reviewer {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px;
    display: grid;
    grid-template-columns: 340px 1fr;
    gap: 14px;
    align-items: start;
  }
  .model-step-pills {
    display: flex;
    gap: 5px;
    flex-wrap: wrap;
    margin-bottom: 8px;
  }
  .model-step-pill {
    background: var(--bg);
    color: var(--muted);
    border: 1px solid var(--border);
    padding: 4px 8px;
    border-radius: 5px;
    font-size: 11px;
    font-weight: 600;
    cursor: pointer;
  }
  .model-step-pill.active {
    background: var(--purple);
    color: #fff;
    border-color: var(--purple);
  }
  .leaderboard-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 11.5px;
    background: var(--panel);
    border-radius: 8px;
    overflow: hidden;
  }
  .leaderboard-table th, .leaderboard-table td {
    padding: 6px 8px;
    border-bottom: 1px solid var(--border);
    text-align: left;
  }
  .leaderboard-table th {
    background: var(--panel-alt);
    color: var(--muted);
    font-size: 10.5px;
    text-transform: uppercase;
  }
</style>
</head>
<body>
<header>
  <h1>
    🥋 Lauburu 3D Grappling Mind Map & Coaching Studio
    <span class="badge live-pulse" id="portalBadgeLabel">👤 USER-FACING ATHLETE COACH</span>
    <span class="badge debate">✂️ Isolated 7s Clip Analysis</span>
  </h1>
  <div class="portal-switcher">
    <button class="portal-btn active-user" id="btnPortalUser" onclick="switchPortal('user')">👤 User-Facing Athlete View</button>
    <button class="portal-btn" id="btnPortalAdmin" onclick="switchPortal('admin')">🛠️ Admin Model Review & Clip Studio (Aaron)</button>
  </div>
  <div style="display:flex; align-items:center; gap:8px; font-size: 12px; color: var(--muted);">
    <span class="badge eufy" id="btnEufyTop" style="display:none;" onclick="toggleEufyModal(true)">🔐 Eufy Ingestor</span>
    <span><strong>@aaronmahergrappling</strong> • <span id="ruleCountBadge">2</span> Rules</span>
  </div>
</header>

<div class="workspace" id="mainWorkspace">
  <!-- Left Sidebar -->
  <div class="sidebar">
    <div class="sidebar-header">
      <input type="text" id="searchInput" placeholder="Search comp matches & techniques..." oninput="renderMatchList()">
      <select id="divisionFilter" onchange="renderMatchList()">
        <option value="ALL">All Matches & Techniques (51)</option>
        <option value="Freestyle Wrestling">Freestyle Wrestling (19)</option>
        <option value="ADCC">ADCC (6)</option>
        <option value="Professional Grappling">Professional Grappling (4)</option>
        <option value="IBJJF">IBJJF (8)</option>
        <option value="Other Competitions">Other Competitions (5)</option>
        <option value="Instructional Footage">Technique & Instructional Videos (9)</option>
      </select>
    </div>
    <div class="match-list" id="matchList"></div>
  </div>

  <!-- Center Stage -->
  <div class="center-stage">
    <div class="view-tabs">
      <button class="tab-btn active" id="btnLiveVideoView" onclick="setCenterView('live')">✂️ Clipped Exchange + Real-Time 3D Skeleton</button>
      <button class="tab-btn mindmap-tab" id="btnMindmapView" onclick="setCenterView('mindmap')">🧠 3D Grappling Mind Map (3,723 Nodes)</button>
      <button class="tab-btn" id="btnGridView" onclick="setCenterView('grid')">🦴 4-Panel 3D Snapshot</button>
      <button class="tab-btn" id="btnYtView" onclick="setCenterView('yt')">▶ YouTube Stream</button>
      <button class="tab-btn run-vlm" id="btnRunAllVlm" style="display:none;" onclick="runAllVlmsOnCurrentMatch()">🔬 Run All 10 Vision Models</button>
      <span id="currentMatchHeader" style="margin-left:auto; font-size:12px; font-weight:600; color:var(--accent);"></span>
    </div>

    <!-- =======================================================================
         EXTRACTED 7-SECOND SUB-CLIPS BAR (Clips Out the Action Instead of Full Video)
         ======================================================================= -->
    <div class="clips-strip-bar" id="extractedClipsBar">
      <span style="font-size:11.5px; font-weight:700; color:var(--accent);">✂️ Extracted 7s Action Clips:</span>
      <div id="extractedClipsButtons" style="display:flex; gap:6px; flex-wrap:wrap; flex:1;"></div>
    </div>

    <!-- =======================================================================
         PRIMARY VIEW: LIVE VIDEO PLAYER + REAL-TIME 3D SKELETON & LIVE FEEDBACK
         ======================================================================= -->
    <div class="live-video-stage" id="liveVideoStage">
      <div class="video-player-box" id="videoPlayerBox">
        <div id="liveCameraRig">
          <video id="liveNativeVideo" autoplay loop muted playsinline></video>
          <canvas id="livePoseCanvas" title="Click directly on any athlete to confirm & lock tracking onto them + their partner"></canvas>
        </div>
        <div id="ytFallbackWrap" style="display:none; width:100%; height:100%;">
          <div id="ytPlayer"></div>
        </div>
        <div class="video-hud-topbar">
          <span class="hud-pill" id="livePoseHudText">🔴 LIVE 3D TRACKER: Initializing...</span>
          <span class="hud-pill mindmap-node-pill" id="liveMindmapNodePill" style="cursor:pointer;" onclick="jumpToActiveMindmapNode()" title="Click to open & highlight this position in the 3D Mind Map">🧠 Mind Map: Collar tie (You) ↗</span>
        </div>
        <div class="video-bottom-controls" id="videoBottomControls">
          <button class="vbc-btn" id="btnPlayPause" onclick="toggleLivePlayPause()">⏸ Pause</button>
          <span id="liveTimeReadout" style="font-size:11px; font-weight:700; color:#e2e8f0; min-width:110px;">Clip 0:00 / 0:07</span>
          <input type="range" id="liveVideoScrubber" min="0" max="100" step="0.1" value="0" oninput="scrubLiveVideo(this.value)">
          <button class="vbc-btn" id="btnToggleAutoZoom" onclick="toggleAutoZoomPair()">🔍 Auto-Zoom Pair: ON (2.2x)</button>
          <button class="vbc-btn" style="border-color:var(--blue);" onclick="resetAthleteLock()" title="Reset to automatic center-mat athlete lock">🎯 Auto-Lock</button>
        </div>
      </div>

      <!-- Right Half of Live Video Stage: Real-Time Play-by-Play Stream + Instant Feedback -->
      <div class="live-stream-feed-box">
        <div class="live-stream-header">
          <span>⚡ LIVE MIND MAP COACHING & PLAY-BY-PLAY (<span id="liveClockLabel">t = 0.0s</span>)</span>
          <div style="display:flex; gap:5px;">
            <button class="tab-btn" style="padding:3px 7px; font-size:10.5px;" id="btnToggleAutoVlm" onclick="toggleAutoLiveVlm()">🔴 Auto Live VLM: ON</button>
            <button class="tab-btn run-vlm" style="padding:3px 7px; font-size:10.5px;" onclick="triggerLiveFrameAnalysis(true, '')">⚡ Coach Call Now</button>
          </div>
        </div>
        <div class="live-ticker-list" id="liveTickerList"></div>
        <div class="live-quick-bar" id="liveQuickCorrectionBar">
          <div style="display:flex; gap:6px; align-items:center; justify-content:space-between;">
            <span style="font-size:10.5px; color:var(--muted);">Instant Live Feedback @ <strong id="quickTsBadge" style="color:var(--accent);">0.0s</strong>:</span>
            <div style="display:flex; gap:4px;">
              <button class="vlm-btn good" style="padding:3px 8px; font-size:10.5px;" onclick="sendQuickLiveVote('good')">👍 Good Live Call</button>
              <button class="vlm-btn bad" style="padding:3px 8px; font-size:10.5px;" onclick="sendQuickLiveVote('bad')">👎 Bad Live Call</button>
            </div>
          </div>
          <div class="live-quick-input-row">
            <input type="text" id="liveQuickInput" placeholder="Type live coaching correction while watching clip & press Enter..." onkeydown="if(event.key==='Enter') sendLiveQuickFeedback()">
            <button class="live-quick-btn" onclick="sendLiveQuickFeedback()">⚡ Send Live</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 4-Panel Static Grid Snapshot (Optional Tab) -->
    <img id="gridImage" class="grid-preview" alt="Center-Mat 3D Annotated Keyframe Grid">

    <!-- 3D Interactive Mind Map Container -->
    <div class="mindmap-container" id="mindmapContainer">
      <div class="mindmap-canvas-wrap">
        <canvas id="mindmapCanvas"></canvas>
        <div class="mindmap-hud">
          <button class="tab-btn" onclick="resetMindmapCamera()">🎯 Reset 3D Orbit</button>
          <button class="tab-btn" id="btnAutoRotate" onclick="toggleAutoRotate()">🔄 Auto-Rotate: ON</button>
        </div>
      </div>
      <div class="mindmap-inspector" id="mindmapInspector">
        <div class="section-title">🧠 3D Mind Map Node Inspector</div>
        <div id="mmNodeTitle" style="font-size:14px; font-weight:700; color:var(--accent);">Click any 3D Node Sphere</div>
        <div id="mmNodeSummary" style="color:var(--muted); line-height:1.4;">
          Drag on the 3D canvas to rotate the 3,723-node Mindomo Grappling Mind Map in 3D space (Wrestling, Guard, Dominant Positions, Scrambles). Scroll to zoom. Click any node sphere to inspect its coaching cues, sub-branches, and linked technique/competition videos.
        </div>
        <div id="mmBiomechBox" style="background:var(--bg); padding:8px; border-radius:6px; border:1px solid var(--border); display:none;"></div>
        <div id="mmBranchesBox"></div>
        <div id="mmTechVideosBox"></div>
        <div id="mmCompMatchesBox"></div>
      </div>
    </div>

    <!-- Digestible Mind Map Position, Posture & Linked Technique Bar -->
    <div class="telemetry-grid">
      <div class="metric-card" style="cursor:pointer; border-color:rgba(168,85,247,0.45);" onclick="jumpToActiveMindmapNode()" title="Click to highlight this node in the 3D Mind Map">
        <div class="metric-label">🧠 Active Mind Map Position (Click for 3D Map)</div>
        <div class="metric-val" id="metPhase" style="font-size:12.5px; color:#e9d5ff; line-height:1.3;">--</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">🛡️ Live Stance, Posture & Tie-Up Read</div>
        <div class="metric-val" id="metShots" style="font-size:12px; color:var(--accent); line-height:1.3;">--</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">⚡ Mind Map Next Transitions & Finishes</div>
        <div class="metric-val" id="metSpineKnee" style="font-size:11.5px; color:var(--text); line-height:1.35;">--</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">🎥 Linked Technique Videos (1-Click Drill)</div>
        <div class="metric-val" id="metElbow" style="font-size:11.5px; color:var(--blue); line-height:1.35;">--</div>
      </div>
    </div>

    <!-- USER-FACING ATHLETE CHAMPION SUMMARY BOX (Shown on User Portal) -->
    <div id="userAthleteSummaryCard" style="background:var(--panel); border:1px solid var(--accent); border-radius:8px; padding:12px 14px;">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
        <span style="font-size:12px; font-weight:700; color:var(--accent);">🏆 Active AI Coach Breakdown (Real-Time + Deep Teacher Consensus)</span>
        <span style="font-size:11px; color:var(--muted);" id="userChampionModelBadge">⚡ Real-Time: Local Hermes-3 8B + 3D (543ms) • 🧠 Deep Teacher: Qwen2.5-VL-72B</span>
      </div>
      <div id="userCoachSummaryText" style="font-size:13px; line-height:1.5; color:var(--text);"></div>
    </div>

    <!-- =======================================================================
         ADMIN STUDIO FOR AARON (Separate Model Review, Clip Slicer & Latency vs Accuracy Leaderboard)
         ======================================================================= -->
    <div class="admin-studio-box" id="adminStudioBox">
      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
        <div style="font-size:13.5px; font-weight:800; color:#e9d5ff;">
          🛠️ ADMIN MODEL REVIEW & ISOLATED CLIP STUDIO (Each Model Reviewed Separately)
        </div>
        <div style="font-size:11px; color:var(--muted);">
          Identify the superior model • Compare ⚡ Real-Time Streamer (&lt;1.2s) vs 🧠 Deep 72B/31B Clip Teacher
        </div>
      </div>

      <!-- Empirical Real-Time vs 72B Teacher Architecture Verdict -->
      <div class="admin-verdict-banner" id="adminVerdictBanner">
        Loading empirical real-time vs 72B teacher benchmark...
      </div>

      <!-- 1-by-1 Separate Model Reviewer with Physically Clipped 7s Video -->
      <div style="font-size:12px; font-weight:700; color:var(--accent);">
        🎯 Step 1: Review Each Model Separately Against the Extracted 7-Second Clip
      </div>
      <div class="model-step-pills" id="adminModelStepPills"></div>
      <div class="single-model-reviewer" id="adminSingleModelReviewer"></div>

      <!-- 10-Model Separate Scorecard & Real-Time Viability Leaderboard -->
      <div style="font-size:12px; font-weight:700; color:var(--blue); margin-top:4px;">
        📊 Step 2: Live 10-Model Leaderboard (Empirical Speed, Real-Time Viability, Win Rate & ELO)
      </div>
      <div style="overflow-x:auto;">
        <table class="leaderboard-table">
          <thead>
            <tr>
              <th>Rank</th>
              <th>Vision Model</th>
              <th>Real-Time vs Deep Teacher Role</th>
              <th>Avg Latency</th>
              <th>p95 Latency</th>
              <th>👍 Accurate</th>
              <th>👎 Bad</th>
              <th>🎯 Critiques</th>
              <th>Win Rate</th>
              <th>ELO</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody id="adminLeaderboardBody"></tbody>
        </table>
      </div>

      <!-- Side-by-Side 10-Model Vision Opinions Grid (with Isolated 7s Clips) -->
      <div class="vlm-matrix-header" style="margin-top:4px;">
        <div class="section-title" style="margin-bottom:0;">
          <span>👁️ All 10 Vision Models Side-by-Side (With Extracted 7s MP4 Clips)</span>
        </div>
        <span style="font-size:11px; color:var(--muted);">Every card plays its physically clipped 7.0s exchange</span>
      </div>
      <div class="vlm-grid" id="vlmGrid"></div>
    </div>
  </div>

  <!-- Right Panel: Active Consensus Opinion & Detailed Real-Time Feedback -->
  <div class="feedback-panel" id="rightFeedbackPanel">
    <div class="panel-section">
      <div class="section-title">
        <span>🤖 Canonical Match / Technique Opinion</span>
        <span id="opinionStatusBadge" class="badge">Live</span>
      </div>
      <div class="qwen-opinion-box" id="qwenOpinionBox">Select a match or technique video to view digestible Mind Map coaching & transition analysis.</div>
    </div>

    <div class="feedback-form" id="adminFeedbackForm">
      <div class="section-title" style="margin-bottom:2px;">
        <span>🎯 Admin Critique / Correct Specific VLM on Clip</span>
      </div>
      <div class="row">
        <button class="ts-btn" onclick="captureTimestamp()">⏱ Capture Clip Time</button>
        <input type="number" id="tsInput" value="18.0" step="0.5" style="width:72px;" title="Video Timestamp (seconds)">
        <span style="font-size:11px; color:var(--muted);">s</span>
        <select id="targetModelSelect" style="flex:1;">
          <option value="All Vision Models">Target: All Vision Models</option>
          <option value="Gemma 4 31B Vision (Debater A)">Gemma 4 31B Vision (Debater A)</option>
          <option value="Qwen 3.8 Max 27B Vision (Debater B)">Qwen 3.8 Max 27B (Debater B)</option>
          <option value="Qwen 3.8 Omni Flash">Qwen 3.8 Omni Flash</option>
          <option value="Qwen2.5-VL-72B-Instruct (Teacher)">Qwen2.5-VL-72B (Teacher)</option>
          <option value="Gemini 3.8 Flash Vision">Gemini 3.8 Flash Vision</option>
          <option value="Gemini 2.5 Pro Vision">Gemini 2.5 Pro Vision</option>
          <option value="Claude Sonnet 5.5 Vision">Claude Sonnet 5.5 Vision</option>
          <option value="Llama 4 Maverick Vision">Llama 4 Maverick Vision</option>
          <option value="Kimi K2.5 Multimodal Vision">Kimi K2.5 Multimodal Vision</option>
          <option value="Local Hermes-3 8B + MediaPipe 3D (:8085)">Local Hermes-3 8B + 3D (:8085)</option>
        </select>
      </div>
      <div class="row">
        <select id="categorySelect" style="width:100%;">
          <option value="Ruleset & Scoring Risk">Category: Ruleset & Scoring Risk (Freestyle vs BJJ/ADCC)</option>
          <option value="Posture & Defensive Barrier">Category: Posture & Defensive Structural Barrier</option>
          <option value="Mind Map Node & Transition">Category: 3D Mind Map Position & Transition</option>
          <option value="Tie-Up & Grip Mechanics">Category: Tie-Up, 2-on-1 & Grip Mechanics</option>
          <option value="Shot Entry & Finish">Category: Level-Change Shot Entry & Finish</option>
          <option value="Scramble & Mat Return">Category: Scramble, Exposure & Mat Return</option>
        </select>
      </div>
      <textarea id="feedbackInput" placeholder="Watch the extracted 7s clip, type your coaching correction or model critique, and press Save..."></textarea>
      <button class="submit-btn" id="submitBtn" onclick="submitFeedback()">⚡ Cut 7s Clip, Save RLHF Pair & Update Model ELO</button>
    </div>

    <div class="panel-section" style="padding-bottom:4px; border-bottom:none;">
      <div class="section-title">📚 Verified Reviewing Comments (With Attached 7s Clips)</div>
    </div>
    <div class="history-list" id="historyList"></div>
  </div>
</div>

<!-- Eufy Security Ingestion Modal -->
<div class="modal-backdrop" id="eufyModal">
  <div class="modal">
    <div style="display:flex; justify-content:space-between; align-items:center;">
      <h3 style="font-size:15px;">🔐 Eufy Security App & L6 Pixel 10 Footage Ingestor</h3>
      <button class="tab-btn" onclick="toggleEufyModal(false)">✕ Close</button>
    </div>
    <p style="font-size:12px; color:var(--muted); line-height:1.45;">
      Ready for your Eufy login details! Credentials are stored strictly locally in
      <code>~/.config/eufy_security/credentials.json</code> (0600 permissions, zero cloud leak) or clips can be pulled directly from your <strong>Pixel 10 Pro XL (L6)</strong> Eufy app storage via ADB.
    </p>
    <div id="eufyStatusBox" style="font-size:11.5px; background:var(--bg); padding:8px 10px; border-radius:6px; border:1px solid var(--border);"></div>
    <input type="email" id="eufyEmail" placeholder="Eufy Account Email">
    <input type="password" id="eufyPassword" placeholder="Eufy Account Password">
    <input type="text" id="eufyRtsp" placeholder="Optional Local RTSP / NAS Stream URL">
    <div style="display:flex; gap:8px;">
      <button class="submit-btn" style="flex:1;" onclick="saveEufyCreds()">💾 Save Eufy Login Locally</button>
      <button class="tab-btn run-vlm" style="flex:1;" onclick="syncPixelEufyClips()">📱 Pull Eufy Clips from Pixel 10 (ADB)</button>
    </div>
  </div>
</div>

<script src="https://www.youtube.com/iframe_api"></script>
<script>
  let allMatches = [];
  let coachRules = [];
  let mindmapGraph = { nodes: [], edges: [] };
  let modelLeaderboard = { architecture_verdict: {}, models: [] };
  let visionRoster = [];
  let currentMatch = null;
  let ytPlayer = null;
  let ytReady = false;
  let activeViewMode = 'live';
  let currentLiveNodeId = 'sub_0_0_2_collar_tie_(you)';

  // Portal Mode ('user' vs 'admin') & Extracted Clip State
  let portalMode = (window.location.pathname.includes('/admin') || window.location.search.includes('portal=admin')) ? 'admin' : 'user';
  let activeClipIndex = 2; // Default to Clip 3 (15.5s-22.5s primary action exchange) instead of full uncut video!
  let activeClipOffsetSec = 15.5;
  let isPlayingExtractedClip = true;
  let activeSingleModelIndex = 0;

  // Live Pose & Live VLM Stream state
  let autoLiveVlm = true;
  let livePoseBusy = false;
  let lastLivePoseTs = -999;
  let lastLiveVlmTs = -999;
  let latestOverlayAthletes = [];
  let latestLiveFrameB64 = '';

  const liveVideo = document.getElementById('liveNativeVideo');
  const poseCanvas = document.getElementById('livePoseCanvas');
  const poseCtx = poseCanvas.getContext('2d');

  // 3D Mind Map Camera State
  let mmRotY = 0.4;
  let mmRotX = 0.25;
  let mmZoom = 1.05;
  let mmAutoRotate = true;
  let mmDragging = false;
  let mmLastX = 0, mmLastY = 0;
  let mmProjectedNodes = [];
  let mmSelectedNode = null;

  function onYouTubeIframeAPIReady() {
    ytPlayer = new YT.Player('ytPlayer', {
      height: '100%',
      width: '100%',
      videoId: 'fbCpcA1DyWg',
      playerVars: { 'playsinline': 1, 'rel': 0, 'mute': 1, 'autoplay': 1 },
      events: {
        'onReady': () => { ytReady = true; ytPlayer.mute(); }
      }
    });
  }

  function switchPortal(mode) {
    portalMode = mode === 'admin' ? 'admin' : 'user';
    const isAdmin = portalMode === 'admin';
    document.getElementById('btnPortalUser').className = 'portal-btn' + (!isAdmin ? ' active-user' : '');
    document.getElementById('btnPortalAdmin').className = 'portal-btn' + (isAdmin ? ' active-admin' : '');
    document.getElementById('portalBadgeLabel').textContent = isAdmin
      ? '🛠️ ADMIN MODEL REVIEW & CLIP STUDIO (AARON)'
      : '👤 USER-FACING ATHLETE COACH';
    document.getElementById('adminStudioBox').style.display = isAdmin ? 'flex' : 'none';
    document.getElementById('userAthleteSummaryCard').style.display = isAdmin ? 'none' : 'block';
    document.getElementById('adminFeedbackForm').style.display = isAdmin ? 'flex' : 'none';
    document.getElementById('liveQuickCorrectionBar').style.display = isAdmin ? 'flex' : 'none';
    document.getElementById('btnRunAllVlm').style.display = isAdmin ? 'inline-block' : 'none';
    document.getElementById('btnEufyTop').style.display = isAdmin ? 'inline-block' : 'none';
    renderAdminModelStudio();
  }

  async function fetchState() {
    const res = await fetch('/api/state');
    const data = await res.json();
    allMatches = data.matches || [];
    coachRules = data.coach_rules || [];
    mindmapGraph = data.mindmap_3d || { nodes: [], edges: [] };
    visionRoster = data.vision_roster || [];
    modelLeaderboard = data.model_leaderboard || { architecture_verdict: {}, models: [] };
    document.getElementById('ruleCountBadge').textContent = coachRules.length;
    renderMatchList();
    renderHistory();
    switchPortal(portalMode);
    if (!currentMatch && allMatches.length > 0) {
      selectMatch(allMatches[0].video_id);
    }
    if (mindmapGraph.nodes && mindmapGraph.nodes.length > 0) {
      inspectMindmapNode(mindmapGraph.nodes[0]);
    }
  }

  function renderMatchList() {
    const q = document.getElementById('searchInput').value.toLowerCase();
    const div = document.getElementById('divisionFilter').value;
    const container = document.getElementById('matchList');
    container.innerHTML = '';

    const filtered = allMatches.filter(m => {
      const matchDiv = div === 'ALL' || m.division === div;
      const matchQ = !q || m.title.toLowerCase().includes(q) || m.division.toLowerCase().includes(q) || m.video_id.toLowerCase().includes(q) || (m.primary_mindmap_node || '').toLowerCase().includes(q);
      return matchDiv && matchQ;
    });

    filtered.forEach(m => {
      const vlmCount = Object.keys(m.vision_model_opinions || {}).length;
      const el = document.createElement('div');
      el.className = 'match-item' + (currentMatch && currentMatch.video_id === m.video_id ? ' active' : '');
      el.onclick = () => selectMatch(m.video_id);
      const mp4Badge = m.has_local_mp4 ? `<span class="mp4-pill">✂️ 4 CLIPS</span>` : '';
      const mmTag = m.primary_mindmap_node || 'Collar tie (You)';
      el.innerHTML = `
        <div class="match-div">
          <span>${m.division}</span>
          <span><span class="vlm-count-pill">${vlmCount} VLMs</span>${mp4Badge}</span>
        </div>
        <div class="match-title">${m.title}</div>
        <div class="match-meta">🧠 ${mmTag} • Stand: ${m.standing_phase_pct}% • Shots: ${m.level_change_shots_detected}</div>
      `;
      container.appendChild(el);
    });
  }

  function renderMindmapCoachingCards(breadcrumb, nodeId, postureCue, transitions, linkedTechs) {
    if (nodeId) currentLiveNodeId = nodeId;
    document.getElementById('metPhase').innerHTML =
      `<span>${breadcrumb || 'Wrestling ➔ Collar tie (You)'}</span> <span style="font-size:10.5px; color:var(--accent); text-decoration:underline; margin-left:4px;">View in 3D Map ↗</span>`;
    document.getElementById('metShots').textContent =
      postureCue || 'Disciplined Low Stance • Head & Hands Protecting Hips';

    const trList = (transitions && transitions.length) ? transitions : ['Knee-pull sweep single', 'Collar-tie throw-by', '2-on-1 Russian tie', 'Snapdown'];
    document.getElementById('metSpineKnee').innerHTML = trList.slice(0, 4).map(t =>
      `<span class="pill-link" style="color:var(--text); cursor:pointer;" onclick="jumpToActiveMindmapNode()">➔ ${t}</span>`
    ).join('');

    const tvList = (linkedTechs && linkedTechs.length) ? linkedTechs : [{ id: 'Kf0wQ00FPBg', title: 'Collar tie 2 on 1 entry to collar tie' }];
    document.getElementById('metElbow').innerHTML = tvList.slice(0, 2).map(tv =>
      `<span class="pill-link" onclick="playMindmapVideo('${tv.id}')" title="Click to open this instructional technique video">🎥 ${(tv.title || tv.id).slice(0, 34)}</span>`
    ).join('');
  }

  function jumpToActiveMindmapNode() {
    setCenterView('mindmap');
    const nodes = (mindmapGraph && mindmapGraph.nodes) ? mindmapGraph.nodes : [];
    const target = nodes.find(n => n.id === currentLiveNodeId) ||
                   nodes.find(n => currentMatch && n.label === currentMatch.primary_mindmap_node) ||
                   nodes[0];
    if (target) {
      inspectMindmapNode(target);
    }
  }

  function renderExtractedClipsBar() {
    const wrap = document.getElementById('extractedClipsButtons');
    if (!wrap || !currentMatch) return;
    wrap.innerHTML = '';
    const clips = currentMatch.extracted_clips || [
      { clip_index: 1, label: 'Clip 1: Setup & Hand-Fighting', start_sec: 3.0, end_sec: 10.0, mid_timestamp_sec: 6.5, clip_url: `/api/clip/${currentMatch.video_id}_3.0_10.0.mp4` },
      { clip_index: 2, label: 'Clip 2: Inside Space & Tie-Up', start_sec: 9.5, end_sec: 16.5, mid_timestamp_sec: 13.0, clip_url: `/api/clip/${currentMatch.video_id}_9.5_16.5.mp4` },
      { clip_index: 3, label: 'Clip 3: Primary Takedown Exchange', start_sec: 15.5, end_sec: 22.5, mid_timestamp_sec: 18.0, clip_url: `/api/clip/${currentMatch.video_id}_15.5_22.5.mp4` },
      { clip_index: 4, label: 'Clip 4: Scramble & Finish', start_sec: 20.2, end_sec: 27.2, mid_timestamp_sec: 22.7, clip_url: `/api/clip/${currentMatch.video_id}_20.2_27.2.mp4` },
    ];
    clips.forEach((c, idx) => {
      const btn = document.createElement('button');
      btn.className = 'clip-pill-btn' + (isPlayingExtractedClip && activeClipIndex === idx ? ' active' : '');
      btn.textContent = `✂️ ${c.label} (${c.start_sec.toFixed(1)}s–${c.end_sec.toFixed(1)}s)`;
      btn.onclick = () => selectExtractedClip(idx);
      wrap.appendChild(btn);
    });
    const fullBtn = document.createElement('button');
    fullBtn.className = 'clip-pill-btn full-video' + (!isPlayingExtractedClip ? ' active' : '');
    fullBtn.textContent = '📺 Play Full Uncut Video';
    fullBtn.onclick = () => selectFullUncutVideo();
    wrap.appendChild(fullBtn);
  }

  function selectExtractedClip(clipIdx) {
    if (!currentMatch) return;
    isPlayingExtractedClip = true;
    activeClipIndex = clipIdx;
    const clips = currentMatch.extracted_clips || [];
    const c = clips[clipIdx] || { start_sec: 15.5, end_sec: 22.5, mid_timestamp_sec: 18.0, clip_url: `/api/clip/${currentMatch.video_id}_15.5_22.5.mp4` };
    activeClipOffsetSec = Number(c.start_sec || 0);
    document.getElementById('tsInput').value = Number(c.mid_timestamp_sec || activeClipOffsetSec + 2.5).toFixed(1);
    renderExtractedClipsBar();
    loadMatchIntoLiveVideo(currentMatch);
    renderAdminModelStudio();
  }

  function selectFullUncutVideo() {
    if (!currentMatch) return;
    isPlayingExtractedClip = false;
    activeClipOffsetSec = 0.0;
    renderExtractedClipsBar();
    loadMatchIntoLiveVideo(currentMatch);
  }

  function selectMatch(videoId) {
    let found = allMatches.find(m => m.video_id === videoId);
    if (!found) {
      found = {
        video_id: videoId,
        division: 'Instructional Footage',
        title: 'Linked Mind Map Technique Video (' + videoId + ')',
        resolution: '720p',
        standing_phase_pct: 100,
        ground_scramble_phase_pct: 0,
        level_change_shots_detected: 2,
        primary_mindmap_node: 'Collar tie (You)',
        primary_mindmap_node_id: 'sub_0_0_2_collar_tie_(you)',
        mindmap_breadcrumb: 'Wrestling ➔ Hand fighting ➔ Collar tie (You)',
        posture_summary: 'Disciplined Low Stance • Head & Hands Protecting Hips',
        mindmap_transitions: ['2-on-1 Russian tie entry', 'Collar-tie throw-by', 'Knee-pull sweep single', 'Snapdown'],
        linked_technique_videos: [{ id: 'Kf0wQ00FPBg', title: 'Collar tie 2 on 1 entry to collar tie (4K Instructional)' }],
        tactical_note: 'Linked directly from the 3,723-node Grappling Mind Map.',
        vision_model_opinions: {},
        has_local_mp4: false
      };
    }
    currentMatch = found;
    isPlayingExtractedClip = true;
    activeClipIndex = 2;
    const clips = currentMatch.extracted_clips || [];
    activeClipOffsetSec = clips[activeClipIndex] ? Number(clips[activeClipIndex].start_sec) : 15.5;
    lastLivePoseTs = -999;
    lastLiveVlmTs = -999;
    latestOverlayAthletes = [];
    renderMatchList();
    renderExtractedClipsBar();

    document.getElementById('currentMatchHeader').textContent = `${currentMatch.division}: ${currentMatch.title}`;
    renderMindmapCoachingCards(
      currentMatch.mindmap_breadcrumb || `Wrestling ➔ ${currentMatch.primary_mindmap_node || 'Collar tie (You)'}`,
      currentMatch.primary_mindmap_node_id || 'sub_0_0_2_collar_tie_(you)',
      currentMatch.posture_summary || 'Disciplined Low Stance • Head & Hands Protecting Hips',
      currentMatch.mindmap_transitions || [],
      currentMatch.linked_technique_videos || []
    );

    const opBox = document.getElementById('qwenOpinionBox');
    opBox.textContent = currentMatch.tactical_note || 'No opinion recorded.';
    opBox.className = 'qwen-opinion-box' + (currentMatch.coach_corrected ? ' corrected' : '');
    document.getElementById('opinionStatusBadge').textContent = currentMatch.coach_corrected ? 'Coach RLHF Verified' : 'Mind Map Linked';
    document.getElementById('userCoachSummaryText').textContent = currentMatch.tactical_note || '';

    document.getElementById('gridImage').src = `/keyframes/${videoId}_3d_grid.jpg?t=${Date.now()}`;
    renderVlmCards();
    renderAdminModelStudio();
    initLiveStreamTickerForMatch(currentMatch);
    loadMatchIntoLiveVideo(currentMatch);
  }

  function loadMatchIntoLiveVideo(m) {
    const clips = m.extracted_clips || [];
    const activeClip = clips[activeClipIndex] || { start_sec: 15.5, end_sec: 22.5, clip_url: `/api/clip/${m.video_id}_15.5_22.5.mp4` };
    const vidUrl = isPlayingExtractedClip ? activeClip.clip_url : `/api/video/${m.video_id}.mp4`;
    if (activeViewMode === 'yt') {
      liveVideo.pause();
      liveVideo.style.display = 'none';
      document.getElementById('ytFallbackWrap').style.display = 'block';
      if (ytReady && ytPlayer && ytPlayer.loadVideoById) {
        ytPlayer.loadVideoById(m.video_id);
        ytPlayer.mute();
      }
      return;
    }

    // Play native HTML5 <video> (defaults to the physically extracted 7.0s MP4 clip!)
    document.getElementById('ytFallbackWrap').style.display = 'none';
    liveVideo.style.display = 'block';
    liveVideo.muted = true;
    liveVideo.volume = 0;
    liveVideo.src = vidUrl;
    const playPromise = liveVideo.play();
    if (playPromise !== undefined) {
      playPromise.catch(() => {
        if (!m.has_local_mp4 && ytReady && ytPlayer && ytPlayer.loadVideoById) {
          liveVideo.style.display = 'none';
          document.getElementById('ytFallbackWrap').style.display = 'block';
          ytPlayer.loadVideoById(m.video_id);
          ytPlayer.mute();
        }
      });
    }
    setTimeout(() => triggerLiveFrameAnalysis(true, ''), 350);
  }

  function initLiveStreamTickerForMatch(m) {
    const list = document.getElementById('liveTickerList');
    list.innerHTML = '';
    const ops = Object.values(m.vision_model_opinions || {});
    const gemmaOp = ops.find(x => (x.model_id || '').includes('gemma')) || ops[0];
    const qwenOp = ops.find(x => (x.model_id || '').includes('qwen_38')) || ops[1];
    const mmCrumb = m.mindmap_breadcrumb || (m.division.includes('Wrestling') ? 'Wrestling ➔ Hand fighting ➔ Collar tie (You)' : 'Guard ➔ J point');
    const trStr = (m.mindmap_transitions || ['Knee-pull sweep single', 'Throw-by', '2-on-1 entry']).slice(0, 3).join(', ');

    appendLiveTickerCard({
      timestamp_sec: activeClipOffsetSec,
      source: '✂️ Extracted 7s Clip & Mind Map Tracker',
      mindmap_node: mmCrumb,
      text: `Playing isolated 7.0s exchange for "${m.title}" [${mmCrumb}]. ${m.posture_summary || 'Disciplined low stance — head & hands protecting inside space'}. Next Mind Map transitions: ${trStr}.`,
      b64_frame: '',
      is_coach: false
    });

    if (gemmaOp && gemmaOp.analysis) {
      appendLiveTickerCard({
        timestamp_sec: activeClipOffsetSec + 2.0,
        source: `🧠 ${gemmaOp.model_name}`,
        mindmap_node: m.primary_mindmap_node || 'Sovereign Debate Duo A',
        text: gemmaOp.analysis,
        b64_frame: '',
        is_coach: false
      });
    }
    if (qwenOp && qwenOp.analysis) {
      appendLiveTickerCard({
        timestamp_sec: activeClipOffsetSec + 4.0,
        source: `⚡ ${qwenOp.model_name}`,
        mindmap_node: m.primary_mindmap_node || 'Sovereign Debate Duo B',
        text: qwenOp.analysis,
        b64_frame: '',
        is_coach: false
      });
    }
  }

  function appendLiveTickerCard(ev) {
    const list = document.getElementById('liveTickerList');
    const card = document.createElement('div');
    card.className = 'live-event-card' + (ev.is_coach ? ' coach-event' : '');
    const thumbHtml = ev.b64_frame
      ? `<img class="lec-thumb" src="data:image/jpeg;base64,${ev.b64_frame}" alt="Live 3D Frame">`
      : '';
    card.innerHTML = `
      <div class="lec-top">
        <span>${ev.source} • @ ${Number(ev.timestamp_sec || 0).toFixed(1)}s</span>
        <span style="color:#d8b4fe;">${ev.mindmap_node || ''}</span>
      </div>
      <div class="lec-frame-row">
        ${thumbHtml}
        <div style="flex:1;">${ev.text}</div>
      </div>
    `;
    list.insertBefore(card, list.firstChild);
    while (list.children.length > 25) {
      list.removeChild(list.lastChild);
    }
  }

  function getActiveVideoTime() {
    if (liveVideo && liveVideo.style.display !== 'none' && !isNaN(liveVideo.currentTime)) {
      const base = isPlayingExtractedClip ? activeClipOffsetSec : 0.0;
      return base + (liveVideo.currentTime || 0);
    }
    if (ytReady && ytPlayer && ytPlayer.getCurrentTime) {
      return ytPlayer.getCurrentTime() || 0;
    }
    return activeClipOffsetSec || 0;
  }

  let autoZoomPair = true;
  let currentZoomBox = [0.22, 0.22, 0.56, 0.56];
  let currentZoomFactor = 1.8;

  function formatSec(s) {
    const m = Math.floor((s || 0) / 60);
    const sec = Math.floor((s || 0) % 60);
    return `${m}:${sec < 10 ? '0' : ''}${sec}`;
  }

  function toggleLivePlayPause() {
    if (!liveVideo) return;
    if (liveVideo.paused) {
      liveVideo.play();
      document.getElementById('btnPlayPause').textContent = '⏸ Pause';
    } else {
      liveVideo.pause();
      document.getElementById('btnPlayPause').textContent = '▶ Play';
    }
  }

  function scrubLiveVideo(pct) {
    if (!liveVideo || !liveVideo.duration) return;
    liveVideo.currentTime = (Number(pct) / 100.0) * liveVideo.duration;
  }

  function applyCameraZoom() {
    const rig = document.getElementById('liveCameraRig');
    const btn = document.getElementById('btnToggleAutoZoom');
    if (!rig) return;
    if (!autoZoomPair || activeViewMode !== 'live') {
      rig.style.transform = 'scale(1) translate(0%, 0%)';
      if (btn) btn.textContent = '🔍 Auto-Zoom Pair: OFF (1.0x)';
      return;
    }
    const [zx, zy, zw, zh] = currentZoomBox || [0, 0, 1, 1];
    const scale = Math.min(2.6, Math.max(1.0, 1.0 / Math.max(zw || 1, zh || 1)));
    const tx = -zx * 100;
    const ty = -zy * 100;
    rig.style.transform = `scale(${scale.toFixed(3)}) translate(${tx.toFixed(2)}%, ${ty.toFixed(2)}%)`;
    currentZoomFactor = scale;
    if (btn) btn.textContent = `🔍 Auto-Zoom Pair: ON (${scale.toFixed(1)}x)`;
  }

  function toggleAutoZoomPair() {
    autoZoomPair = !autoZoomPair;
    applyCameraZoom();
  }

  async function resetAthleteLock() {
    await triggerLiveFrameAnalysis(false, '', [-1, -1]);
  }

  // Click directly on any athlete in the live video canvas to confirm & lock tracking onto them + their partner
  poseCanvas.addEventListener('click', (e) => {
    const rect = poseCanvas.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) return;
    const normX = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    const normY = Math.max(0, Math.min(1, (e.clientY - rect.top) / rect.height));
    triggerLiveFrameAnalysis(true, `Coach clicked to confirm & lock athlete at (${(normX*100).toFixed(0)}%, ${(normY*100).toFixed(0)}%)`, [normX, normY]);
  });

  // Real-Time 60 FPS Keypoint Interpolation State & COCO-17 Bone Topology
  const COCO_BONES = [
    [0, 1], [0, 2], [1, 3], [2, 4],
    [5, 6], [5, 7], [7, 9], [6, 8], [8, 10],
    [5, 11], [6, 12], [11, 12],
    [11, 13], [13, 15], [12, 14], [14, 16]
  ];
  let prevPoseSnap = null; // { t: number, athletes: [...] }
  let currPoseSnap = null; // { t: number, athletes: [...] }
  let vlmBusy = false;
  let lastInferMs = 24.0;

  // Synchronize live clock & scrubber at 60 FPS
  liveVideo.addEventListener('timeupdate', () => {
    const t = liveVideo.currentTime || 0;
    const dur = liveVideo.duration || 0;
    document.getElementById('liveClockLabel').textContent = `t = ${t.toFixed(1)}s`;
    document.getElementById('quickTsBadge').textContent = `${t.toFixed(1)}s`;
    document.getElementById('tsInput').value = t.toFixed(1);
    document.getElementById('liveTimeReadout').textContent = `${formatSec(t)} / ${formatSec(dur)}`;
    if (dur > 0) {
      document.getElementById('liveVideoScrubber').value = ((t / dur) * 100).toFixed(1);
    }
    if (autoLiveVlm && !vlmBusy && Math.abs(t - lastLiveVlmTs) >= 5.5) {
      triggerLiveVlmCommentary('');
    }
  });

  liveVideo.addEventListener('seeked', () => {
    prevPoseSnap = null;
    currPoseSnap = null;
    triggerLiveFrameAnalysis(false, '');
  });

  // Continuous Real-Time Pose Stream Loop (~25-30 Hz, completely unblocked by VLM calls)
  async function realtimePoseLoop() {
    if (currentMatch && activeViewMode === 'live' && !livePoseBusy) {
      const t = getActiveVideoTime();
      const isPlaying = liveVideo && !liveVideo.paused && !liveVideo.ended;
      if (isPlaying || Math.abs(t - lastLivePoseTs) >= 0.033) {
        // Request with +30ms lookahead when playing so returned pose matches display frame upon arrival
        const lookaheadT = isPlaying ? (t + 0.030) : t;
        await triggerLiveFrameAnalysis(false, '', null, lookaheadT);
      }
    }
    setTimeout(realtimePoseLoop, 12);
  }
  setTimeout(realtimePoseLoop, 80);

  function getInterpolatedAthletes(tNow) {
    if (!currPoseSnap || !currPoseSnap.athletes) return latestOverlayAthletes;
    if (!prevPoseSnap || !prevPoseSnap.athletes || Math.abs(currPoseSnap.t - prevPoseSnap.t) < 0.005 || Math.abs(currPoseSnap.t - prevPoseSnap.t) > 0.6) {
      return currPoseSnap.athletes;
    }
    const dt = currPoseSnap.t - prevPoseSnap.t;
    // Allow smooth interpolation [0..1] plus damped velocity extrapolation up to 1.35x for zero visual lag
    const rawAlpha = (tNow - prevPoseSnap.t) / dt;
    const alpha = Math.max(0.0, Math.min(1.35, rawAlpha));

    return currPoseSnap.athletes.map((currAth, idx) => {
      const prevAth = prevPoseSnap.athletes[idx];
      if (!prevAth || prevAth.label !== currAth.label) return currAth;

      const cb = currAth.bbox_norm || [0, 0, 0, 0];
      const pb = prevAth.bbox_norm || cb;
      const interpBbox = [
        pb[0] + (cb[0] - pb[0]) * alpha,
        pb[1] + (cb[1] - pb[1]) * alpha,
        pb[2] + (cb[2] - pb[2]) * alpha,
        pb[3] + (cb[3] - pb[3]) * alpha
      ];

      const ck17 = currAth.kpts_17_norm;
      const pk17 = prevAth.kpts_17_norm;
      if (ck17 && pk17 && ck17.length === 17 && pk17.length === 17) {
        const interp17 = [];
        const interpKpts = [];
        for (let j = 0; j < 17; j++) {
          const cpt = ck17[j];
          const ppt = pk17[j];
          if (cpt[2] > 0.20 && ppt[2] > 0.20) {
            const ix = ppt[0] + (cpt[0] - ppt[0]) * alpha;
            const iy = ppt[1] + (cpt[1] - ppt[1]) * alpha;
            interp17.push([ix, iy, cpt[2]]);
            interpKpts.push([ix, iy]);
          } else if (cpt[2] > 0.20) {
            interp17.push([cpt[0], cpt[1], cpt[2]]);
            interpKpts.push([cpt[0], cpt[1]]);
          } else {
            interp17.push([0, 0, 0]);
          }
        }
        const interpLines = [];
        for (let b = 0; b < COCO_BONES.length; b++) {
          const [ia, ib] = COCO_BONES[b];
          if (interp17[ia][2] > 0.20 && interp17[ib][2] > 0.20) {
            interpLines.push([interp17[ia][0], interp17[ia][1], interp17[ib][0], interp17[ib][1]]);
          }
        }
        return {
          ...currAth,
          bbox_norm: interpBbox,
          kpts_norm: interpKpts,
          lines_norm: interpLines
        };
      }
      return { ...currAth, bbox_norm: interpBbox };
    });
  }

  function drawLivePoseOverlay() {
    const parent = poseCanvas.parentElement;
    const W_css = parent ? parent.clientWidth : 0;
    const H_css = parent ? parent.clientHeight : 0;
    if (W_css > 0 && H_css > 0) {
      if (poseCanvas.width !== W_css || poseCanvas.height !== H_css) {
        poseCanvas.width = W_css;
        poseCanvas.height = H_css;
      }
      poseCtx.clearRect(0, 0, poseCanvas.width, poseCanvas.height);
      const W = poseCanvas.width;
      const H = poseCanvas.height;
      const invScale = autoZoomPair ? (1.0 / Math.max(1.0, Math.sqrt(currentZoomFactor))) : 1.0;

      const tNow = getActiveVideoTime();
      const renderAthletes = getInterpolatedAthletes(tNow);

      renderAthletes.forEach(ath => {
        const [bx, by, bw, bh] = ath.bbox_norm || [0, 0, 0, 0];
        const col = ath.color || '#10b981';
        poseCtx.strokeStyle = col;
        poseCtx.lineWidth = 2.0 * invScale;
        poseCtx.strokeRect(bx * W, by * H, bw * W, bh * H);

        poseCtx.fillStyle = 'rgba(11, 15, 23, 0.82)';
        poseCtx.fillRect(bx * W, Math.max(2, by * H - 15 * invScale), 125 * invScale, 14 * invScale);
        poseCtx.fillStyle = col;
        poseCtx.font = `700 ${Math.max(8, Math.round(10 * invScale))}px -apple-system, sans-serif`;
        poseCtx.fillText(ath.label, bx * W + 4 * invScale, Math.max(11, by * H - 4 * invScale));

        // Draw 3D skeleton connections
        poseCtx.strokeStyle = col;
        poseCtx.lineWidth = 2.6 * invScale;
        (ath.lines_norm || []).forEach(ln => {
          poseCtx.beginPath();
          poseCtx.moveTo(ln[0] * W, ln[1] * H);
          poseCtx.lineTo(ln[2] * W, ln[3] * H);
          poseCtx.stroke();
        });

        // Draw joint keypoints
        poseCtx.fillStyle = '#ffffff';
        (ath.kpts_norm || []).forEach(pt => {
          poseCtx.beginPath();
          poseCtx.arc(pt[0] * W, pt[1] * H, 2.8 * invScale, 0, Math.PI * 2);
          poseCtx.fill();
        });
      });
    }
    requestAnimationFrame(drawLivePoseOverlay);
  }
  requestAnimationFrame(drawLivePoseOverlay);

  // Separate non-blocking VLM commentary request so skeleton tracking NEVER pauses
  async function triggerLiveVlmCommentary(coachNote) {
    if (!currentMatch || vlmBusy) return;
    vlmBusy = true;
    const t = getActiveVideoTime();
    lastLiveVlmTs = t;
    try {
      const res = await fetch('/api/live_frame_pose', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          video_id: currentMatch.video_id,
          timestamp_sec: t,
          query_vlm: true,
          include_b64: true,
          coach_feedback: coachNote || ''
        })
      });
      const data = await res.json();
      if (data.status === 'OK') {
        if (data.b64_annotated_frame) latestLiveFrameB64 = data.b64_annotated_frame;
        const zf = data.zoom_factor || currentZoomFactor || 1.0;
        if (data.live_commentary) {
          appendLiveTickerCard({
            timestamp_sec: t,
            source: coachNote ? '🎯 Coach Live Feedback + Debate Duo' : `👁️ Auto-Zoom (${zf.toFixed(1)}x) Live VLM`,
            mindmap_node: data.active_mindmap_node,
            text: data.live_commentary,
            b64_frame: data.b64_annotated_frame,
            is_coach: Boolean(coachNote)
          });
        }
      }
    } catch (e) {
    } finally {
      vlmBusy = false;
    }
  }

  async function triggerLiveFrameAnalysis(askVlm, coachNote, lockPoint, overrideTs) {
    if (!currentMatch) return;
    if (askVlm && !lockPoint) {
      triggerLiveVlmCommentary(coachNote || '');
    }
    if (livePoseBusy) return;
    livePoseBusy = true;
    const t = (overrideTs !== undefined && overrideTs !== null) ? overrideTs : getActiveVideoTime();
    lastLivePoseTs = t;

    try {
      const reqBody = {
        video_id: currentMatch.video_id,
        timestamp_sec: t,
        query_vlm: Boolean(askVlm && lockPoint),
        include_b64: Boolean(askVlm && lockPoint),
        coach_feedback: (lockPoint ? (coachNote || '') : '')
      };
      if (lockPoint) reqBody.lock_point = lockPoint;

      const res = await fetch('/api/live_frame_pose', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(reqBody)
      });
      const data = await res.json();
      if (data.status === 'OK') {
        latestOverlayAthletes = data.overlay_athletes || [];
        prevPoseSnap = currPoseSnap;
        currPoseSnap = { t: Number(data.timestamp_sec ?? t), athletes: latestOverlayAthletes };
        if (data.b64_annotated_frame) latestLiveFrameB64 = data.b64_annotated_frame;
        if (data.infer_ms) lastInferMs = data.infer_ms;
        if (data.zoom_box_norm) {
          currentZoomBox = data.zoom_box_norm;
          applyCameraZoom();
        }
        const zf = data.zoom_factor || currentZoomFactor || 1.0;
        document.getElementById('livePoseHudText').textContent =
          `🔴 LIVE @ ${t.toFixed(1)}s | ⚡ ${Math.round(lastInferMs)}ms (60FPS Sync) | 🔍 ${zf.toFixed(1)}x Zoom | Pair: ${data.wrestlers_detected}`;
        document.getElementById('liveMindmapNodePill').textContent =
          `🧠 ${data.mindmap_breadcrumb || data.active_mindmap_node} ↗`;
        renderMindmapCoachingCards(
          data.mindmap_breadcrumb || data.active_mindmap_node,
          data.active_mindmap_node_id,
          data.posture_summary,
          data.mindmap_transitions,
          data.linked_technique_videos
        );

        if (data.live_commentary) {
          appendLiveTickerCard({
            timestamp_sec: t,
            source: coachNote ? '🎯 Coach Live Feedback + Debate Duo' : `👁️ Auto-Zoom (${zf.toFixed(1)}x) Live VLM`,
            mindmap_node: data.mindmap_breadcrumb || data.active_mindmap_node,
            text: data.live_commentary,
            b64_frame: data.b64_annotated_frame,
            is_coach: Boolean(coachNote)
          });
        }
      }
    } catch (e) {
      // Ignore transient network errors during rapid scrubbing
    } finally {
      livePoseBusy = false;
    }
  }

  function toggleAutoLiveVlm() {
    autoLiveVlm = !autoLiveVlm;
    document.getElementById('btnToggleAutoVlm').textContent = `🔴 Auto Live VLM: ${autoLiveVlm ? 'ON' : 'OFF'}`;
  }

  async function sendLiveQuickFeedback() {
    const inp = document.getElementById('liveQuickInput');
    const txt = inp.value.trim();
    if (!txt || !currentMatch) return;
    inp.value = '';
    const t = getActiveVideoTime();
    document.getElementById('tsInput').value = t.toFixed(1);
    document.getElementById('feedbackInput').value = txt;
    await triggerLiveFrameAnalysis(true, txt);
    await submitFeedback(txt, t);
  }

  async function sendQuickLiveVote(vote) {
    if (!currentMatch) return;
    const t = getActiveVideoTime();
    const msg = vote === 'good'
      ? `Approved live 3D skeleton & Mind Map call at t=${t.toFixed(1)}s.`
      : `Flagged live call at t=${t.toFixed(1)}s as inaccurate — re-evaluating live frame.`;
    await triggerLiveFrameAnalysis(true, msg);
  }

  function verifyClipInMainPlayer(videoId, timestampSec, clipStartSec, clipEndSec) {
    const targetTs = Math.max(0, Number(timestampSec || 18.0));
    if (!currentMatch || currentMatch.video_id !== videoId) {
      selectMatch(videoId);
    }
    isPlayingExtractedClip = true;
    const cStart = (clipStartSec !== undefined && clipStartSec !== null)
      ? Number(clipStartSec)
      : Math.max(0, Math.round((targetTs - 2.5) * 10) / 10);
    const cEnd = (clipEndSec !== undefined && clipEndSec !== null)
      ? Number(clipEndSec)
      : Math.round((cStart + 7.0) * 10) / 10;
    activeClipOffsetSec = cStart;
    setCenterView('live');
    setTimeout(() => {
      if (liveVideo && liveVideo.style.display !== 'none') {
        liveVideo.muted = true;
        liveVideo.volume = 0;
        liveVideo.src = `/api/clip/${videoId}_${cStart.toFixed(1)}_${cEnd.toFixed(1)}.mp4`;
        liveVideo.play().catch(() => {});
      } else if (ytReady && ytPlayer && ytPlayer.seekTo) {
        ytPlayer.seekTo(targetTs, true);
        ytPlayer.mute();
      }
      document.getElementById('tsInput').value = targetTs.toFixed(1);
      triggerLiveFrameAnalysis(false, '', null, targetTs);
    }, 120);
  }

  function selectSingleAdminModel(idx) {
    const models = (modelLeaderboard && modelLeaderboard.models) ? modelLeaderboard.models : [];
    const total = Math.max(1, models.length || 10);
    activeSingleModelIndex = ((idx % total) + total) % total;
    renderAdminModelStudio();
  }

  function renderAdminModelStudio() {
    if (!currentMatch) return;
    const verdict = (modelLeaderboard && modelLeaderboard.architecture_verdict) || {};
    const models = (modelLeaderboard && modelLeaderboard.models) || [];
    const rtWinner = verdict.recommended_realtime_model_name || 'Local Hermes-3 8B + MediaPipe 3D (:8085)';
    const deepWinner = verdict.recommended_deep_teacher_model_name || 'Qwen2.5-VL-72B-Instruct (Teacher)';

    const champBadge = document.getElementById('userChampionModelBadge');
    if (champBadge) {
      champBadge.textContent = `⚡ Real-Time Stream: ${rtWinner} • 🧠 Deep Clip Teacher: ${deepWinner}`;
    }

    const banner = document.getElementById('adminVerdictBanner');
    if (banner) {
      banner.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:6px; margin-bottom:4px;">
          <strong style="color:#e9d5ff;">🔬 EMPIRICAL REAL-TIME vs. 72B DEEP TEACHER TEST VERDICT:</strong>
          <span class="badge" style="border-color:var(--warn); color:#fcd34d;">72B Avg Latency: ${verdict.qwen_72b_avg_latency_ms || 3699.4}ms (p95: ${verdict.qwen_72b_p95_latency_ms || 4920.0}ms) ➔ CANNOT RUN REAL-TIME</span>
        </div>
        <div style="color:var(--text);">
          • <strong>Why 72B / 31B Cannot Run Live Real-Time:</strong> <code>Qwen2.5-VL-72B</code> takes <strong>3.70s–4.92s per frame</strong> (0.27 Hz) and <code>Gemma 4 31B / Qwen 3.8 Max 27B</code> take <strong>5.0s–6.6s</strong>, whereas live wrestling tie-ups & shots change every 0.8s–1.5s.<br>
          • <strong>Active Two-Tier Solution:</strong>
            <span style="color:var(--accent); font-weight:700;">⚡ Real-Time Live Stream Champion: ${rtWinner}</span> (56.2ms 3D Pose + 543.5ms LLM = 1.84 Hz live)
            paired with
            <span style="color:var(--blue); font-weight:700;">🧠 Stronger Clipped-Exchange Teacher: ${deepWinner}</span> (analyzing the extracted 7.0s MP4 clips below).
        </div>
      `;
    }

    // 1. Render Step-Through Model Pills (1..10)
    const pillsEl = document.getElementById('adminModelStepPills');
    const opinions = currentMatch.vision_model_opinions || {};
    const opList = Object.values(opinions);
    const modelItems = models.length ? models : opList.map((o, i) => ({
      rank: i + 1,
      model_id: o.model_id,
      model_name: o.model_name,
      tier: o.tier,
      avg_latency_ms: Math.round((o.latency_sec || 3.5) * 1000),
      p95_latency_ms: Math.round((o.latency_sec || 4.5) * 1250),
      realtime_capable: (o.latency_sec || 3.5) <= 1.2,
      role_classification: (o.latency_sec || 3.5) <= 1.2 ? '⚡ REAL-TIME CAPABLE' : '🧠 DEEP TEACHER ONLY (Clip Analysis)',
      thumbs_up: 0,
      thumbs_down: 0,
      critique_count: 0,
      elo_rating: 1500
    }));

    if (pillsEl) {
      pillsEl.innerHTML = '';
      modelItems.forEach((m, idx) => {
        const b = document.createElement('button');
        b.className = 'model-step-pill' + (idx === activeSingleModelIndex ? ' active' : '');
        const rtIcon = m.realtime_capable ? '⚡' : '🧠';
        b.textContent = `${idx + 1}/${modelItems.length} ${rtIcon} ${(m.model_name || m.model_id).split('(')[0].trim()} (${m.elo_rating || 1500})`;
        b.onclick = () => selectSingleAdminModel(idx);
        pillsEl.appendChild(b);
      });
    }

    // 2. Render Single-Model Reviewer Box with Isolated 7s Clip
    const reviewerEl = document.getElementById('adminSingleModelReviewer');
    if (reviewerEl && modelItems.length > 0) {
      const m = modelItems[activeSingleModelIndex % modelItems.length];
      const op = opinions[m.model_id] || opList[activeSingleModelIndex % Math.max(1, opList.length)] || {};
      const vidId = currentMatch.video_id;
      const clips = currentMatch.extracted_clips || [];
      const activeClip = clips[activeClipIndex] || { start_sec: 15.5, end_sec: 22.5, mid_timestamp_sec: 18.0, clip_url: `/api/clip/${vidId}_15.5_22.5.mp4` };
      const clipStart = Number(activeClip.start_sec || 15.5).toFixed(1);
      const clipEnd = Number(activeClip.end_sec || 22.5).toFixed(1);
      const clipTs = Number(activeClip.mid_timestamp_sec || 18.0);
      const clipUrl = `/api/clip/${vidId}_${clipStart}_${clipEnd}.mp4`;
      const thumbUrl = op.clip_thumb_url || `/keyframes/${vidId}_3d_grid.jpg`;
      const safeName = (m.model_name || m.model_id).replace(/'/g, "\\'");
      const rtBadge = m.realtime_capable
        ? `<span class="badge" style="background:rgba(16,185,129,0.2); color:#6ee7b7; border-color:var(--accent);">⚡ REAL-TIME CAPABLE (${m.avg_latency_ms}ms avg)</span>`
        : `<span class="badge" style="background:rgba(245,158,11,0.18); color:#fcd34d; border-color:var(--warn);">🐢 TOO SLOW FOR LIVE STREAM (${m.avg_latency_ms}ms avg — Deep Clip Teacher)</span>`;

      reviewerEl.innerHTML = `
        <div>
          <video id="adminSingleClipVideo" src="${clipUrl}" poster="${thumbUrl}" autoplay loop muted playsinline controls
            style="width:100%; height:195px; object-fit:cover; border-radius:8px; border:1px solid var(--accent); background:#000;"></video>
          <div style="display:flex; justify-content:space-between; align-items:center; margin-top:6px; font-size:11px; color:var(--muted);">
            <span>✂️ Isolated 7.0s Clip: <strong>${clipStart}s–${clipEnd}s</strong> (No full-video scrubbing needed)</span>
            <button class="verify-clip-btn" onclick="verifyClipInMainPlayer('${vidId}', ${clipTs}, ${clipStart}, ${clipEnd})">▶ Sync Main 3D Stage</button>
          </div>
        </div>
        <div style="display:flex; flex-direction:column; gap:8px;">
          <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:6px;">
            <div>
              <span style="font-size:11px; color:var(--purple); font-weight:700;">MODEL ${activeSingleModelIndex + 1} OF ${modelItems.length} (SEPARATE EVALUATION)</span>
              <div style="font-size:15px; font-weight:800; color:var(--text);">${m.model_name}</div>
            </div>
            <div style="display:flex; gap:6px; align-items:center;">
              <button class="tab-btn" onclick="selectSingleAdminModel(${activeSingleModelIndex - 1})">◀ Prev Model</button>
              <button class="tab-btn" onclick="selectSingleAdminModel(${activeSingleModelIndex + 1})">Next Model ▶</button>
            </div>
          </div>
          <div style="display:flex; gap:8px; flex-wrap:wrap; align-items:center;">
            ${rtBadge}
            <span class="badge debate">🏆 ELO: ${m.elo_rating || 1500} (Rank #${m.rank || 1})</span>
            <span style="font-size:11.5px; color:var(--muted);">
              Record: <strong style="color:var(--accent);">👍 ${m.thumbs_up || 0}</strong> /
              <strong style="color:var(--danger);">👎 ${m.thumbs_down || 0}</strong> /
              <strong style="color:var(--warn);">🎯 ${m.critique_count || 0}</strong>
              ${m.accuracy_pct !== null && m.accuracy_pct !== undefined ? `(${m.accuracy_pct}% Accurate)` : ''}
            </span>
          </div>
          <div style="background:var(--bg); border:1px solid var(--border); border-left:3px solid var(--purple); border-radius:6px; padding:10px 12px; font-size:12.5px; line-height:1.48; color:var(--text);">
            <div style="font-size:10.5px; color:var(--muted); margin-bottom:4px;">
              🧠 Mind Map Path: <strong style="color:#d8b4fe;">${currentMatch.mindmap_breadcrumb || currentMatch.primary_mindmap_node}</strong> • Clip Window: ${clipStart}s–${clipEnd}s
            </div>
            ${op.analysis || currentMatch.tactical_note || 'No evaluation recorded yet for this model.'}
          </div>
          <div style="display:flex; gap:8px; align-items:center;">
            <button class="vlm-btn good" style="padding:8px 10px; font-size:12px;" onclick="voteModelOpinion('${m.model_id}', 'good', ${clipTs}, ${clipStart}, ${clipEnd})">👍 Accurate on Clip (+24 ELO)</button>
            <button class="vlm-btn bad" style="padding:8px 10px; font-size:12px;" onclick="voteModelOpinion('${m.model_id}', 'bad', ${clipTs}, ${clipStart}, ${clipEnd})">👎 Bad / Hallucinated (-24 ELO)</button>
            <button class="vlm-btn crit" style="padding:8px 10px; font-size:12px;" onclick="prefillCritique('${safeName}', ${clipTs}, ${clipStart}, ${clipEnd})">🎯 Write Critique for ${m.model_name.split('(')[0].trim()}</button>
          </div>
        </div>
      `;
    }

    // 3. Render 10-Model Leaderboard Table
    const tbody = document.getElementById('adminLeaderboardBody');
    if (tbody) {
      tbody.innerHTML = '';
      modelItems.forEach((m, idx) => {
        const tr = document.createElement('tr');
        const rtHtml = m.realtime_capable
          ? `<span style="color:var(--accent); font-weight:700;">⚡ Real-Time Capable</span>`
          : `<span style="color:var(--warn);">🧠 Deep Clip Teacher Only</span>`;
        const winPct = (m.accuracy_pct !== null && m.accuracy_pct !== undefined) ? `${m.accuracy_pct}%` : 'Unrated';
        tr.innerHTML = `
          <td><strong>#${m.rank || (idx + 1)}</strong></td>
          <td><strong>${m.model_name}</strong></td>
          <td>${rtHtml}</td>
          <td>${m.avg_latency_ms} ms</td>
          <td>${m.p95_latency_ms} ms</td>
          <td style="color:var(--accent); font-weight:700;">${m.thumbs_up || 0}</td>
          <td style="color:var(--danger); font-weight:700;">${m.thumbs_down || 0}</td>
          <td style="color:var(--warn); font-weight:700;">${m.critique_count || 0}</td>
          <td><strong>${winPct}</strong></td>
          <td><strong style="color:var(--blue);">${m.elo_rating || 1500}</strong></td>
          <td><button class="verify-clip-btn" onclick="selectSingleAdminModel(${idx})">🔍 Review 1-by-1</button></td>
        `;
        tbody.appendChild(tr);
      });
    }
  }

  function renderVlmCards() {
    const grid = document.getElementById('vlmGrid');
    if (!grid) return;
    grid.innerHTML = '';
    if (!currentMatch) return;
    const opinions = currentMatch.vision_model_opinions || {};
    const entries = Object.values(opinions);

    if (entries.length === 0) {
      grid.innerHTML = `<div style="font-size:12px; color:var(--muted); padding:8px;">Click <strong>"🔬 Run All 10 Vision Models"</strong> above to evaluate all local & cloud vision models on this video.</div>`;
      return;
    }

    const vidId = currentMatch.video_id;
    const mmNode = currentMatch.primary_mindmap_node || 'Collar tie (You)';
    const windows = [[3.0, 10.0, 6.5], [9.5, 16.5, 13.0], [15.5, 22.5, 18.0], [20.2, 27.2, 22.7]];
    const lbModels = (modelLeaderboard && modelLeaderboard.models) || [];

    entries.forEach((op, idx) => {
      const isLocal = (op.tier || '').toLowerCase().includes('local') || (op.tier || '').toLowerCase().includes('sovereign');
      const card = document.createElement('div');
      card.className = `vlm-card ${isLocal ? 'local-tier' : 'cloud-tier'}` + (op.user_vote === 'good' ? ' voted-good' : (op.user_vote === 'bad' ? ' voted-bad' : ''));
      const safeName = (op.model_name || op.model_id).replace(/'/g, "\\'");
      const winDef = windows[idx % windows.length];
      const clipStart = Number(op.clip_start_sec !== undefined ? op.clip_start_sec : winDef[0]).toFixed(1);
      const clipEnd = Number(op.clip_end_sec !== undefined ? op.clip_end_sec : winDef[1]).toFixed(1);
      const clipTs = Number(op.clip_timestamp_sec !== undefined ? op.clip_timestamp_sec : winDef[2]);
      const thumbSrc = op.clip_thumb_url || `/keyframes/${vidId}_3d_grid.jpg`;
      // Use physically extracted 7s clip endpoint (/api/clip/...) instead of full uncut video!
      const clipVideoUrl = `/api/clip/${vidId}_${clipStart}_${clipEnd}.mp4`;
      const lbEntry = lbModels.find(x => x.model_id === op.model_id) || {};
      const rtTag = lbEntry.realtime_capable ? '⚡ RT' : '🧠 Teacher';
      const eloVal = lbEntry.elo_rating || 1500;

      card.innerHTML = `
        <div>
          <div class="vlm-card-top">
            <span class="vlm-name">${op.model_name || op.model_id}</span>
            <span class="vlm-tier-tag">${rtTag} • ELO ${eloVal} • ${lbEntry.avg_latency_ms || Math.round((op.latency_sec || 3.5)*1000)}ms</span>
          </div>
          <div class="vlm-clip-box">
            <div class="vlm-clip-media-row">
              <video class="vlm-inline-clip" src="${clipVideoUrl}" poster="${thumbSrc}" muted loop playsinline controls preload="metadata"
                onmouseenter="this.play().catch(()=>{})"
                onmouseleave="this.pause()"
                title="Isolated 7.0s Clip (${clipStart}s–${clipEnd}s)"></video>
              <img class="vlm-inline-poster" src="${thumbSrc}" alt="3D Keyframe Evidence"
                onclick="verifyClipInMainPlayer('${vidId}', ${clipTs}, ${clipStart}, ${clipEnd})"
                title="Click to load this 7.0s extracted clip in main 3D player">
            </div>
            <div class="vlm-clip-bar">
              <span>✂️ Isolated 7s Clip (${clipStart}s–${clipEnd}s) • 🧠 ${mmNode}</span>
              <button class="verify-clip-btn" onclick="verifyClipInMainPlayer('${vidId}', ${clipTs}, ${clipStart}, ${clipEnd})">▶ Play 7s Clip</button>
            </div>
          </div>
          <div class="vlm-text" style="margin-top:6px;">${op.analysis || ''}</div>
        </div>
        <div class="vlm-actions">
          <button class="vlm-btn good" onclick="voteModelOpinion('${op.model_id}', 'good', ${clipTs}, ${clipStart}, ${clipEnd})">👍 Accurate</button>
          <button class="vlm-btn bad" onclick="voteModelOpinion('${op.model_id}', 'bad', ${clipTs}, ${clipStart}, ${clipEnd})">👎 Bad</button>
          <button class="vlm-btn crit" onclick="prefillCritique('${safeName}', ${clipTs}, ${clipStart}, ${clipEnd})">🎯 Critique</button>
        </div>
      `;
      grid.appendChild(card);
    });
  }

  function prefillCritique(modelName, clipTs, clipStart, clipEnd) {
    const t = (clipTs !== undefined && clipTs !== null) ? Number(clipTs) : getActiveVideoTime();
    document.getElementById('tsInput').value = t.toFixed(1);
    if (currentMatch) {
      verifyClipInMainPlayer(currentMatch.video_id, t, clipStart, clipEnd);
    }
    const sel = document.getElementById('targetModelSelect');
    for (let i = 0; i < sel.options.length; i++) {
      if (sel.options[i].value.includes(modelName) || modelName.includes(sel.options[i].value)) {
        sel.selectedIndex = i;
        break;
      }
    }
    const fb = document.getElementById('feedbackInput');
    fb.focus();
    fb.placeholder = `Critiquing ${modelName} on extracted 7s clip @ t=${t.toFixed(1)}s: explain what happened in the exchange...`;
  }

  async function voteModelOpinion(modelId, vote, clipTs, clipStart, clipEnd) {
    if (!currentMatch) return;
    const ts = (clipTs !== undefined && clipTs !== null) ? Number(clipTs) : getActiveVideoTime();
    document.getElementById('tsInput').value = ts.toFixed(1);
    const op = (currentMatch.vision_model_opinions || {})[modelId] || { model_id: modelId, model_name: modelId, analysis: currentMatch.tactical_note };
    op.user_vote = vote;
    op.clip_timestamp_sec = ts;
    if (clipStart !== undefined) op.clip_start_sec = Number(clipStart);
    if (clipEnd !== undefined) op.clip_end_sec = Number(clipEnd);

    const feedbackMsg = vote === 'good'
      ? `[RLHF CHOSEN WINNER: ${op.model_name}] Verified model analysis against isolated 7s clip @ ${ts.toFixed(1)}s.`
      : `[RLHF REJECTED: ${op.model_name}] Flagged model analysis as inaccurate against isolated 7s clip @ ${ts.toFixed(1)}s.`;

    const res = await fetch('/api/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        video_id: currentMatch.video_id,
        video_timestamp_sec: ts,
        category: vote === 'good' ? 'Model Benchmark Winner (Chosen)' : 'Model Benchmark Rejection (DPO)',
        target_model: op.model_name || modelId,
        model_opinion_text: op.analysis,
        vote: vote,
        coach_feedback: feedbackMsg,
        live_frame_b64: latestLiveFrameB64
      })
    });
    const data = await res.json();
    if (data.status === 'OK') {
      if (data.model_leaderboard) {
        modelLeaderboard = data.model_leaderboard;
      }
      if (data.entry && data.entry.clip_thumb_url) {
        op.clip_thumb_url = data.entry.clip_thumb_url;
      }
      if (vote === 'good') {
        currentMatch.tactical_note = op.analysis;
        currentMatch.coach_corrected = true;
        document.getElementById('qwenOpinionBox').textContent = op.analysis;
        document.getElementById('userCoachSummaryText').textContent = op.analysis;
      }
      coachRules.unshift(data.entry);
      document.getElementById('ruleCountBadge').textContent = coachRules.length;
      renderHistory();
      renderVlmCards();
      renderAdminModelStudio();
      appendLiveTickerCard({
        timestamp_sec: ts,
        source: `🎯 Coach Vote (${vote.toUpperCase()}): ${op.model_name}`,
        mindmap_node: currentMatch.mindmap_breadcrumb || 'RLHF Logged',
        text: data.chosen_revised_opinion,
        b64_frame: latestLiveFrameB64,
        is_coach: true
      });
    }
  }

  async function runAllVlmsOnCurrentMatch() {
    if (!currentMatch) return;
    const btn = document.getElementById('btnRunAllVlm');
    btn.disabled = true;
    btn.textContent = '⏳ Querying All 10 Vision Models...';
    try {
      const res = await fetch('/api/run_multi_vlm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ video_id: currentMatch.video_id })
      });
      const data = await res.json();
      if (data.status === 'OK' && data.opinions) {
        currentMatch.vision_model_opinions = data.opinions;
        renderMatchList();
        renderVlmCards();
        renderAdminModelStudio();
      }
    } catch (e) {
      alert('Error running multi-VLM benchmark: ' + e);
    } finally {
      btn.disabled = false;
      btn.textContent = '🔬 Run All 10 Vision Models';
    }
  }

  function setCenterView(mode) {
    activeViewMode = mode;
    document.getElementById('btnLiveVideoView').classList.toggle('active', mode === 'live');
    document.getElementById('btnYtView').classList.toggle('active', mode === 'yt');
    document.getElementById('btnMindmapView').classList.toggle('active', mode === 'mindmap');
    document.getElementById('btnGridView').classList.toggle('active', mode === 'grid');

    document.getElementById('liveVideoStage').style.display = (mode === 'live' || mode === 'yt') ? 'grid' : 'none';
    document.getElementById('mindmapContainer').style.display = mode === 'mindmap' ? 'grid' : 'none';
    document.getElementById('gridImage').style.display = mode === 'grid' ? 'block' : 'none';

    if (mode === 'live' || mode === 'yt') {
      if (currentMatch) loadMatchIntoLiveVideo(currentMatch);
    } else {
      liveVideo.pause();
    }
    if (mode === 'mindmap') {
      resizeMindmapCanvas();
    }
  }

  // =========================================================================
  // 3D INTERACTIVE MIND MAP ENGINE (HTML5 Canvas 3D Perspective Projection)
  // =========================================================================
  const mmCanvas = document.getElementById('mindmapCanvas');
  const mmCtx = mmCanvas.getContext('2d');

  function resizeMindmapCanvas() {
    const rect = mmCanvas.parentElement.getBoundingClientRect();
    if (rect.width > 0 && rect.height > 0) {
      mmCanvas.width = rect.width * window.devicePixelRatio;
      mmCanvas.height = rect.height * window.devicePixelRatio;
      mmCtx.setTransform(window.devicePixelRatio, 0, 0, window.devicePixelRatio, 0, 0);
    }
  }
  window.addEventListener('resize', resizeMindmapCanvas);

  function resetMindmapCamera() {
    mmRotY = 0.4;
    mmRotX = 0.25;
    mmZoom = 1.05;
  }

  function toggleAutoRotate() {
    mmAutoRotate = !mmAutoRotate;
    document.getElementById('btnAutoRotate').textContent = `🔄 Auto-Rotate: ${mmAutoRotate ? 'ON' : 'OFF'}`;
  }

  mmCanvas.addEventListener('mousedown', e => {
    mmDragging = true;
    mmAutoRotate = false;
    document.getElementById('btnAutoRotate').textContent = '🔄 Auto-Rotate: OFF';
    mmLastX = e.clientX;
    mmLastY = e.clientY;
  });
  window.addEventListener('mouseup', () => { mmDragging = false; });
  window.addEventListener('mousemove', e => {
    if (!mmDragging) return;
    const dx = e.clientX - mmLastX;
    const dy = e.clientY - mmLastY;
    mmLastX = e.clientX;
    mmLastY = e.clientY;
    mmRotY += dx * 0.007;
    mmRotX = Math.max(-1.2, Math.min(1.2, mmRotX + dy * 0.007));
  });
  mmCanvas.addEventListener('wheel', e => {
    e.preventDefault();
    mmZoom = Math.max(0.45, Math.min(2.6, mmZoom * (e.deltaY < 0 ? 1.08 : 0.92)));
  }, { passive: false });

  mmCanvas.addEventListener('click', e => {
    const rect = mmCanvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    for (let i = mmProjectedNodes.length - 1; i >= 0; i--) {
      const p = mmProjectedNodes[i];
      const dist = Math.hypot(mx - p.sx, my - p.sy);
      if (dist <= p.sr + 6) {
        inspectMindmapNode(p.node);
        break;
      }
    }
  });

  function project3D(x, y, z, w, h) {
    const cosY = Math.cos(mmRotY), sinY = Math.sin(mmRotY);
    const cosX = Math.cos(mmRotX), sinX = Math.sin(mmRotX);
    const x1 = x * cosY - z * sinY;
    const z1 = z * cosY + x * sinY;
    const y2 = y * cosX - z1 * sinX;
    const z2 = z1 * cosX + y * sinX;
    const fov = 520 * mmZoom;
    const dist = 540 + z2;
    const scale = fov / Math.max(80, dist);
    return { sx: w / 2 + x1 * scale, sy: h / 2 + y2 * scale, scale, z2 };
  }

  function renderMindmapLoop() {
    if (document.getElementById('mindmapContainer').style.display === 'grid') {
      if (mmAutoRotate && !mmDragging) mmRotY += 0.0035;
      const w = mmCanvas.clientWidth || 640;
      const h = mmCanvas.clientHeight || 420;
      if (mmCanvas.width !== w * window.devicePixelRatio) resizeMindmapCanvas();

      mmCtx.clearRect(0, 0, w, h);
      const nodes = mindmapGraph.nodes || [];
      const edges = mindmapGraph.edges || [];
      const mapById = {};
      mmProjectedNodes = nodes.map(n => {
        const p = project3D(n.x || 0, n.y || 0, n.z || 0, w, h);
        const item = { node: n, sx: p.sx, sy: p.sy, sr: Math.max(4, (n.size || 10) * p.scale * 0.72), z2: p.z2, scale: p.scale };
        mapById[n.id] = item;
        return item;
      });

      mmCtx.lineWidth = 1.2;
      edges.forEach(e => {
        const a = mapById[e.source], b = mapById[e.target];
        if (!a || !b) return;
        mmCtx.strokeStyle = e.color || '#26334d';
        mmCtx.globalAlpha = 0.35;
        mmCtx.beginPath();
        mmCtx.moveTo(a.sx, a.sy);
        mmCtx.lineTo(b.sx, b.sy);
        mmCtx.stroke();
      });
      mmCtx.globalAlpha = 1.0;

      mmProjectedNodes.sort((a, b) => b.z2 - a.z2);
      mmProjectedNodes.forEach(p => {
        const isSel = mmSelectedNode && mmSelectedNode.id === p.node.id;
        mmCtx.beginPath();
        mmCtx.arc(p.sx, p.sy, p.sr, 0, Math.PI * 2);
        mmCtx.fillStyle = p.node.color || '#10b981';
        mmCtx.fill();
        if (isSel) {
          mmCtx.lineWidth = 3;
          mmCtx.strokeStyle = '#ffffff';
          mmCtx.stroke();
        }
        if (p.node.depth <= 2 || isSel || p.scale > 0.92) {
          mmCtx.font = `${isSel || p.node.depth <= 1 ? '700 11.5px' : '600 10px'} -apple-system, sans-serif`;
          mmCtx.fillStyle = '#f8fafc';
          mmCtx.fillText(p.node.label, p.sx + p.sr + 5, p.sy + 3);
        }
      });
    }
    requestAnimationFrame(renderMindmapLoop);
  }
  requestAnimationFrame(renderMindmapLoop);

  function inspectMindmapNode(n) {
    mmSelectedNode = n;
    document.getElementById('mmNodeTitle').textContent = `${n.label} [${n.realm}]`;
    document.getElementById('mmNodeSummary').textContent = n.tactical_summary || '';

    const bioBox = document.getElementById('mmBiomechBox');
    if (n.biomechanics_3d) {
      bioBox.style.display = 'block';
      bioBox.innerHTML = `
        <div style="font-weight:700; color:var(--accent); margin-bottom:3px;">🛡️ Mind Map Coaching Cues & Control</div>
        <div>• <strong>Stance & Posture:</strong> ${n.biomechanics_3d.posture_cue || 'Disciplined low stance — head & hands in front of hips'}</div>
        <div>• <strong>Control Mechanics:</strong> ${n.biomechanics_3d.control_mechanics || 'Win inside space & grip leverage'}</div>
        <div>• <strong>Next Transitions:</strong> ${n.biomechanics_3d.next_transitions || 'Chain into Mind Map setups & finishes'}</div>
      `;
    } else {
      bioBox.style.display = 'none';
    }

    const brBox = document.getElementById('mmBranchesBox');
    const brs = n.sub_branches || [];
    brBox.innerHTML = brs.length
      ? `<div style="font-weight:700; margin-bottom:4px; color:var(--text);">Mindomo Sub-Branches (${n.descendant_count} total nodes):</div>` +
        brs.map(b => `<span class="pill-link" style="color:var(--text); cursor:default;">${b}</span>`).join('')
      : '';

    const tvBox = document.getElementById('mmTechVideosBox');
    const tvs = n.linked_technique_videos || [];
    tvBox.innerHTML = tvs.length
      ? `<div style="font-weight:700; margin:6px 0 4px; color:var(--blue);">▶ Linked Instructional / Technique Videos (${tvs.length}):</div>` +
        tvs.map(t => `<span class="pill-link" onclick="playMindmapVideo('${t.id}')">🎥 ${t.title.slice(0, 48)}</span>`).join('')
      : '';

    const cmBox = document.getElementById('mmCompMatchesBox');
    const cms = n.linked_comp_matches || [];
    cmBox.innerHTML = cms.length
      ? `<div style="font-weight:700; margin:6px 0 4px; color:var(--warn);">🥋 Linked Competition Matches (${cms.length}):</div>` +
        cms.map(cid => {
          const mObj = allMatches.find(x => x.video_id === cid);
          const lbl = mObj ? mObj.title.slice(0, 42) : cid;
          return `<span class="pill-link" style="color:var(--warn);" onclick="playMindmapVideo('${cid}')">🏆 ${lbl}</span>`;
        }).join('')
      : '';
  }

  function playMindmapVideo(videoId) {
    selectMatch(videoId);
    setCenterView('live');
  }

  function captureTimestamp() {
    const t = getActiveVideoTime();
    document.getElementById('tsInput').value = t.toFixed(1);
  }

  async function submitFeedback(overrideText, overrideTs) {
    if (!currentMatch) return;
    const text = (overrideText !== undefined ? overrideText : document.getElementById('feedbackInput').value).trim();
    if (!text) return;
    if (overrideTs === undefined) captureTimestamp();
    const ts = overrideTs !== undefined ? overrideTs : parseFloat(document.getElementById('tsInput').value || '18.0');
    const cat = document.getElementById('categorySelect').value;
    const targetModel = document.getElementById('targetModelSelect').value;

    const btn = document.getElementById('submitBtn');
    btn.disabled = true;
    btn.textContent = '🔄 Cutting 7s Clip & Updating Model Leaderboard...';

    try {
      const res = await fetch('/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          video_id: currentMatch.video_id,
          video_timestamp_sec: ts,
          category: cat,
          target_model: targetModel,
          coach_feedback: text,
          live_frame_b64: latestLiveFrameB64
        })
      });
      const data = await res.json();
      if (data.status === 'OK') {
        if (data.model_leaderboard) {
          modelLeaderboard = data.model_leaderboard;
        }
        document.getElementById('feedbackInput').value = '';
        currentMatch.tactical_note = data.chosen_revised_opinion;
        currentMatch.coach_corrected = true;
        coachRules.unshift(data.entry);
        document.getElementById('ruleCountBadge').textContent = coachRules.length;
        document.getElementById('qwenOpinionBox').textContent = data.chosen_revised_opinion;
        document.getElementById('qwenOpinionBox').className = 'qwen-opinion-box corrected';
        document.getElementById('userCoachSummaryText').textContent = data.chosen_revised_opinion;
        renderHistory();
        renderAdminModelStudio();
        appendLiveTickerCard({
          timestamp_sec: ts,
          source: `✅ Coach Ground-Truth Saved (${data.model_used})`,
          mindmap_node: currentMatch.mindmap_breadcrumb || cat,
          text: data.chosen_revised_opinion,
          b64_frame: latestLiveFrameB64,
          is_coach: true
        });
      }
    } catch (e) {
      alert('Error submitting feedback: ' + e);
    } finally {
      btn.disabled = false;
      btn.textContent = '⚡ Cut 7s Clip, Save RLHF Pair & Update Model ELO';
    }
  }

  function renderHistory() {
    const container = document.getElementById('historyList');
    if (!container) return;
    container.innerHTML = '';
    coachRules.slice().reverse().forEach(r => {
      const card = document.createElement('div');
      card.className = 'history-card';
      const vidId = r.video_id || (currentMatch ? currentMatch.video_id : 'fbCpcA1DyWg');
      const ts = Number(r.video_timestamp_sec || 18.0);
      const clipStart = Number(r.clip_start_sec !== undefined ? r.clip_start_sec : Math.max(0, ts - 2.5)).toFixed(1);
      const clipEnd = Number(r.clip_end_sec !== undefined ? r.clip_end_sec : (Number(clipStart) + 7.0)).toFixed(1);
      const thumbUrl = r.clip_thumb_url || `/keyframes/${vidId}_3d_grid.jpg`;
      // Use physically cut 7s clip endpoint (/api/clip/...) so reviewing comments play the isolated clip!
      const clipUrl = `/api/clip/${vidId}_${clipStart}_${clipEnd}.mp4`;

      card.innerHTML = `
        <div class="hc-meta" style="display:flex; justify-content:space-between; align-items:center;">
          <span>${r.category || 'Coach Rule'} • ${vidId} @ ${ts.toFixed(1)}s (${r.target_model || 'VLA'})</span>
          <button class="verify-clip-btn" onclick="verifyClipInMainPlayer('${vidId}', ${ts}, ${clipStart}, ${clipEnd})">▶ Play 7s Clip</button>
        </div>
        <div class="review-clip-box">
          <div class="review-clip-row">
            <video class="review-inline-video" src="${clipUrl}" poster="${thumbUrl}" muted loop playsinline controls preload="metadata"
              onmouseenter="this.play().catch(()=>{})"></video>
            <img class="review-inline-thumb" src="${thumbUrl}" alt="Reviewed Frame"
              onclick="verifyClipInMainPlayer('${vidId}', ${ts}, ${clipStart}, ${clipEnd})"
              style="cursor:pointer;" title="Click to load this isolated 7s clip in main 3D player">
          </div>
          <div class="vlm-clip-bar">
            <span>✂️ Attached 7.0s Clip: ${clipStart}s–${clipEnd}s</span>
            <span style="color:var(--accent); cursor:pointer;" onclick="verifyClipInMainPlayer('${vidId}', ${ts}, ${clipStart}, ${clipEnd})">🔍 Load Clip in 3D Player ↗</span>
          </div>
        </div>
        <div class="hc-coach" style="margin-top:6px;"><strong>You:</strong> "${r.coach_feedback}"</div>
        <div class="hc-revised"><strong>Chosen Ground Truth (${r.model_used || 'VLA'}):</strong> ${r.chosen_revised_opinion}</div>
      `;
      container.appendChild(card);
    });
  }

  async function toggleEufyModal(show) {
    document.getElementById('eufyModal').style.display = show ? 'flex' : 'none';
    if (show) {
      const res = await fetch('/api/eufy_status');
      const d = await res.json();
      document.getElementById('eufyStatusBox').innerHTML = `
        <strong>Status:</strong> ${d.status}<br>
        <strong>Saved Account:</strong> ${d.email_masked}<br>
        <strong>Target Edge Phone:</strong> ${d.android_edge_node}<br>
        <strong>Ingested Eufy Clips:</strong> ${d.ingested_clips_count} clips in <code>inbox/eufy_security/</code>
      `;
    }
  }

  async function saveEufyCreds() {
    const email = document.getElementById('eufyEmail').value;
    const password = document.getElementById('eufyPassword').value;
    const rtsp_url = document.getElementById('eufyRtsp').value;
    await fetch('/api/eufy_config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, rtsp_url })
    });
    document.getElementById('eufyPassword').value = '';
    toggleEufyModal(true);
  }

  async function syncPixelEufyClips() {
    const res = await fetch('/api/eufy_sync_pixel', { method: 'POST' });
    const d = await res.json();
    alert(`Checked Pixel 10 Pro XL Eufy folders. Pulled ${d.pulled_count} new MP4 clips into ${d.inbox_dir}`);
    toggleEufyModal(true);
  }

  document.addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      submitFeedback();
    }
  });

  fetchState();
</script>
</body>
</html>
"""


class FeedbackStudioHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format, *args):
        pass

    def _send_json(self, status: int, data: Any):
        body = json.dumps(data).encode("utf-8")
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _serve_video_file_with_range(self, file_path: Path):
        """Serves an MP4 file with full HTTP 206 Partial Content byte-range support for smooth HTML5 <video> playback & scrubbing."""
        if not file_path or not file_path.exists():
            self.send_error(404)
            return
        file_size = file_path.stat().st_size
        range_header = self.headers.get("Range")
        try:
            if range_header:
                m = re.match(r"bytes=(\d+)-(\d*)", range_header)
                if m:
                    start = int(m.group(1))
                    end = int(m.group(2)) if m.group(2) else file_size - 1
                    end = min(end, file_size - 1)
                    if start >= file_size:
                        self.send_response(416)
                        self.send_header("Content-Range", f"bytes */{file_size}")
                        self.end_headers()
                        return
                    length = end - start + 1
                    self.send_response(206)
                    self.send_header("Content-Type", "video/mp4")
                    self.send_header("Accept-Ranges", "bytes")
                    self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
                    self.send_header("Content-Length", str(length))
                    self.end_headers()
                    with open(file_path, "rb") as f:
                        f.seek(start)
                        self.wfile.write(f.read(length))
                    return

            self.send_response(200)
            self.send_header("Content-Type", "video/mp4")
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Length", str(file_size))
            self.end_headers()
            with open(file_path, "rb") as f:
                self.wfile.write(f.read())
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path in ("/", "/user", "/admin", "/index.html"):
            body = HTML_UI.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        elif path == "/api/state":
            matches = load_matches()
            rules = load_coach_rules()
            mm3d = load_mindmap_3d()
            board = load_model_leaderboard()
            self._send_json(200, {
                "matches": matches,
                "coach_rules": rules,
                "mindmap_3d": mm3d,
                "vision_roster": EXPANDED_VISION_ROSTER,
                "model_leaderboard": board,
            })

        elif path == "/api/model_leaderboard":
            self._send_json(200, load_model_leaderboard())

        elif path == "/api/eufy_status":
            self._send_json(200, get_eufy_status())

        elif path.startswith("/api/clip/"):
            fname = os.path.basename(path).replace(".mp4", "")
            # Format: <vid_id>_<start>_<end>
            parts = fname.rsplit("_", 2)
            if len(parts) == 3:
                vid_id = parts[0]
                try:
                    s_sec = float(parts[1])
                    e_sec = float(parts[2])
                except ValueError:
                    s_sec, e_sec = 15.5, 22.5
            else:
                vid_id = fname
                s_sec, e_sec = 15.5, 22.5
            cpath = ensure_extracted_clip(vid_id, s_sec, e_sec)
            if cpath and cpath.exists():
                self._serve_video_file_with_range(cpath)
            else:
                self.send_error(404)

        elif path.startswith("/api/video/"):
            vid_id = os.path.basename(path).replace(".mp4", "")
            vpath = resolve_or_download_video_path(vid_id, download_if_missing=True)
            if vpath and vpath.exists():
                self._serve_video_file_with_range(vpath)
            else:
                self.send_error(404)

        elif path.startswith("/keyframes/") or path.startswith("/frames/"):
            fname = os.path.basename(path)
            fpath = FRAMES_DIR / fname
            if not fpath.exists():
                vid_prefix = fname.split("_")[0]
                alt = FRAMES_DIR / f"{vid_prefix}_3d_grid.jpg"
                if alt.exists():
                    fpath = alt
            if fpath.exists():
                data = fpath.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            else:
                self.send_error(404)

        elif path == "/media/Kf0wQ00FPBg_annotated.mp4":
            mp4_path = APP_DIR / "inbox" / "Kf0wQ00FPBg_Collar tie 2 on 1 entry to collar tie_annotated.mp4"
            self._serve_video_file_with_range(mp4_path)
        else:
            self.send_error(404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        payload = json.loads(self.rfile.read(length).decode("utf-8")) if length > 0 else {}

        if self.path == "/api/live_frame_pose":
            video_id = payload.get("video_id", "")
            ts_sec = float(payload.get("timestamp_sec", 0.0))
            query_vlm = bool(payload.get("query_vlm", False))
            include_b64 = bool(payload.get("include_b64", query_vlm))
            coach_fb = str(payload.get("coach_feedback", "")).strip()
            lock_pt = payload.get("lock_point")
            target_match = get_match_meta_fast(video_id)
            res = analyze_live_video_frame_at_timestamp(
                video_id=video_id,
                timestamp_sec=ts_sec,
                match_meta=target_match,
                query_vlm=query_vlm,
                coach_feedback=coach_fb,
                lock_point=lock_pt if isinstance(lock_pt, list) else None,
                include_b64=include_b64,
            )
            self._send_json(200, res)
            return

        if self.path == "/api/eufy_config":
            st = save_eufy_credentials(
                payload.get("email", ""),
                payload.get("password", ""),
                payload.get("rtsp_url", ""),
            )
            self._send_json(200, st)
            return

        if self.path == "/api/eufy_sync_pixel":
            res = sync_eufy_clips_from_pixel10()
            self._send_json(200, res)
            return

        if self.path == "/api/run_multi_vlm":
            video_id = payload.get("video_id", "")
            matches = load_matches()
            target_match = next((m for m in matches if m.get("video_id") == video_id), None)
            if not target_match:
                self._send_json(404, {"error": "Match not found"})
                return

            grid_path = FRAMES_DIR / f"{video_id}_3d_grid.jpg"
            b64_grid = None
            if grid_path.exists():
                b64_grid = base64.b64encode(grid_path.read_bytes()).decode("utf-8")

            or_key = _load_secret("OPENROUTER_API_KEY")
            opinions = {}
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
                futs = {
                    pool.submit(query_vlm_expanded, m_cfg, target_match, b64_grid, or_key): m_cfg["id"]
                    for m_cfg in EXPANDED_VISION_ROSTER
                }
                for fut in concurrent.futures.as_completed(futs):
                    r = fut.result()
                    opinions[r["model_id"]] = r

            target_match["vision_model_opinions"] = opinions
            MASTER_JSON.write_text(
                json.dumps([m for m in matches if m.get("video_id") != "Kf0wQ00FPBg"], indent=2),
                encoding="utf-8",
            )
            self._send_json(200, {"status": "OK", "opinions": opinions})
            return

        if self.path == "/api/feedback":
            video_id = payload.get("video_id", "")
            ts_sec = float(payload.get("video_timestamp_sec", 0.0))
            category = payload.get("category", "Tactical Correction")
            target_model = payload.get("target_model", "All Vision Models")
            coach_feedback = str(payload.get("coach_feedback", "")).strip()
            vote = payload.get("vote")
            model_opinion_text = payload.get("model_opinion_text")
            live_frame_b64 = str(payload.get("live_frame_b64", ""))

            matches = load_matches()
            rules = load_coach_rules()
            target_match = next((m for m in matches if m.get("video_id") == video_id), None)
            if not target_match:
                self._send_json(404, {"error": "Match not found"})
                return

            prev_opinion = model_opinion_text or target_match.get("tactical_note", "")
            if vote == "good" and model_opinion_text:
                res = {"revised_opinion": strip_degree_jargon(model_opinion_text), "model_used": f"{target_model} (Coach Approved)"}
            else:
                res = re_evaluate_with_qwen(
                    target_match, coach_feedback, ts_sec, category, rules, target_model, live_frame_b64
                )

            rule_id = f"rule_{len(rules)+1:03d}"
            clip_start_sec = round(max(0.0, ts_sec - 2.5), 1)
            clip_end_sec = round(clip_start_sec + 7.0, 1)
            ensure_extracted_clip(video_id, clip_start_sec, clip_end_sec)
            clip_video_url = f"/api/clip/{video_id}_{clip_start_sec:.1f}_{clip_end_sec:.1f}.mp4"
            clip_thumb_url = f"/keyframes/{video_id}_3d_grid.jpg"
            if live_frame_b64:
                try:
                    FRAMES_DIR.mkdir(parents=True, exist_ok=True)
                    clean_b64 = live_frame_b64.split(",", 1)[-1]
                    thumb_file = FRAMES_DIR / f"review_{rule_id}_{video_id}.jpg"
                    thumb_file.write_bytes(base64.b64decode(clean_b64))
                    clip_thumb_url = f"/keyframes/review_{rule_id}_{video_id}.jpg"
                except Exception:
                    pass

            now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            entry = {
                "id": rule_id,
                "timestamp_utc": now_iso,
                "video_id": video_id,
                "match_title": target_match.get("title", video_id),
                "video_timestamp_sec": ts_sec,
                "clip_start_sec": clip_start_sec,
                "clip_end_sec": clip_end_sec,
                "clip_video_url": clip_video_url,
                "clip_thumb_url": clip_thumb_url,
                "mindmap_breadcrumb": target_match.get("mindmap_breadcrumb", ""),
                "category": category,
                "target_model": target_model,
                "coach_feedback": coach_feedback,
                "rejected_qwen_opinion": prev_opinion,
                "chosen_revised_opinion": res["revised_opinion"],
                "model_used": res["model_used"],
                "kinematics_3d": target_match.get("mean_3d_angles_deg", {}),
            }

            rules.append(entry)
            COACH_RULES_JSON.write_text(json.dumps(rules, indent=2), encoding="utf-8")

            with open(LORA_RLHF_JSONL, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")

            updated_board = record_model_review_vote(
                target_model,
                vote if vote in ("good", "bad") else "critique",
                video_id,
                ts_sec,
                clip_video_url,
                coach_feedback,
            )

            target_match["tactical_note"] = res["revised_opinion"]
            target_match["coach_corrected"] = True
            MASTER_JSON.write_text(
                json.dumps([m for m in matches if m.get("video_id") != "Kf0wQ00FPBg"], indent=2),
                encoding="utf-8",
            )

            append_feedback_to_obsidian(entry)

            self._send_json(200, {
                "status": "OK",
                "chosen_revised_opinion": res["revised_opinion"],
                "model_used": res["model_used"],
                "entry": entry,
                "model_leaderboard": updated_board,
            })
        else:
            self.send_error(404)


def run_server(port: int = 8765):
    init_seed_feedback()
    server = ThreadingHTTPServer(("0.0.0.0", port), FeedbackStudioHandler)
    print(f"[*] Live Video + Real-Time 3D Skeleton & VLM Studio listening on http://127.0.0.1:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    run_server(port)
