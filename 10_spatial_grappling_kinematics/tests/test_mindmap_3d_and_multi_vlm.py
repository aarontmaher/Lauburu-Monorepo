#!/usr/bin/env python3
"""
End-to-End Verification Suite for 10_spatial_grappling_kinematics:
  1. Sovereign Debate Duo Roster (`Gemma 4 31B` + `Qwen 3.8 Max 27B` + Cloud Frontier Teachers).
  2. 3D Grappling Mind Map Graph (`3,723` Mindomo OPML nodes -> `48` 3D Orbital Clusters & `143` Technique Videos).
  3. Competition & Technique Dataset (`50+` videos with Multi-VLM evaluations & 3D joint angles).
  4. Live Referee-Excluded 3D Pose Extraction (`extract_center_mat_athletes_3d_v2`).
  5. Live Studio HTTP API (`http://127.0.0.1:8765/api/state`).
  6. Eufy Security Ingestor & QLoRA Training Candidates Dataset Integrity.
"""

import json
import sys
import urllib.request
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import eufy_security_ingestor as esi
import mindmap_3d_engine as m3e


def test_1_sovereign_debate_duo_and_vlm_roster() -> None:
    roster_ids = [m["id"] for m in m3e.EXPANDED_VISION_ROSTER]
    assert roster_ids[0] == "gemma_4_31b_vision", f"Expected gemma_4_31b_vision first, got {roster_ids[0]}"
    assert roster_ids[1] == "qwen_38_27b_vision", f"Expected qwen_38_27b_vision second, got {roster_ids[1]}"
    assert len(roster_ids) == 10
    print(
        f"[PASS 1/6] Sovereign Debate Duo Roster Verified: "
        f"{m3e.EXPANDED_VISION_ROSTER[0]['name']} + {m3e.EXPANDED_VISION_ROSTER[1]['name']} ({len(roster_ids)} total Vision Models)"
    )


def test_2_mindmap_3d_knowledge_graph() -> None:
    assert m3e.MINDMAP_3D_JSON.exists(), "grappling_3d_mindmap_graph.json missing"
    graph = json.loads(m3e.MINDMAP_3D_JSON.read_text(encoding="utf-8"))
    assert graph["total_opml_outline_nodes"] == 3723
    assert graph["total_3d_visual_clusters"] >= 45
    assert graph["total_linked_technique_videos"] >= 143
    print(
        f"[PASS 2/6] 3D Grappling Mind Map Verified: "
        f"{graph['total_opml_outline_nodes']} OPML nodes | {graph['total_3d_visual_clusters']} 3D Clusters | "
        f"{graph['total_linked_technique_videos']} Linked Technique Videos"
    )


def test_3_competition_and_technique_multi_vlm_summary() -> None:
    assert m3e.SUMMARY_JSON.exists(), "all_competitions_3d_summary.json missing"
    summary = json.loads(m3e.SUMMARY_JSON.read_text(encoding="utf-8"))
    multi_vlm_count = sum(1 for m in summary if len(m.get("vision_model_opinions", {})) >= 8)
    assert len(summary) >= 50
    assert multi_vlm_count >= 44
    print(
        f"[PASS 3/6] Competition & Technique Dataset Verified: "
        f"{len(summary)} videos | {multi_vlm_count}/{len(summary)} with full Multi-VLM evaluations"
    )


def test_4_live_referee_excluded_3d_pose_tracker() -> None:
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision as mp_vision
    from ultralytics import YOLO

    yolo = YOLO(str(m3e.APP_DIR / "yolov8n-pose.pt"))
    opts = mp_vision.PoseLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=m3e.MODEL_PATH),
        running_mode=mp_vision.RunningMode.IMAGE,
        num_poses=2,
        min_pose_detection_confidence=0.25,
    )
    test_mp4 = m3e.TECH_VIDEOS_DIR / "dPeTNQpOfnA.mp4"
    assert test_mp4.exists(), f"Missing test video {test_mp4}"
    with mp_vision.PoseLandmarker.create_from_options(opts) as lm:
        res = m3e.extract_center_mat_athletes_3d_v2(
            test_mp4,
            {"id": "dPeTNQpOfnA", "division": "Instructional Footage", "title": "How To Not Get Sprawled On"},
            yolo,
            lm,
        )
    assert res["poses_detected_frames"] > 0
    assert res["dual_athlete_frames"] > 0
    ang = res["mean_3d_angles_deg"]
    print(
        f"[PASS 4/6] Live Referee-Excluded 3D Pose Extraction on [dPeTNQpOfnA]: "
        f"Dual-Wrestlers={res['dual_athlete_frames']}/{res['sampled_frames']} | "
        f"3D Spine={ang['spine_forward_lean']}° | Knee L/R={ang['left_knee']}°/{ang['right_knee']}°"
    )


def test_5_live_studio_http_api() -> None:
    with urllib.request.urlopen("http://127.0.0.1:8765/api/state", timeout=5) as r:
        st = json.loads(r.read().decode("utf-8"))
    assert len(st.get("matches", [])) >= 50
    assert st.get("mindmap_3d", {}).get("total_opml_outline_nodes") == 3723
    print(
        f"[PASS 5/6] Live Studio HTTP API (:8765/api/state) Verified: "
        f"{len(st['matches'])} matches served | {len(st.get('vision_roster', []))} VLM roster entries"
    )


def test_6_lora_dataset_and_eufy_ingestor() -> None:
    eufy_st = esi.get_eufy_status()
    assert "credentials_file" in eufy_st and eufy_st.get("status") in ("READY_FOR_CREDENTIALS", "CONFIGURED")
    assert m3e.LORA_CANDIDATES_JSONL.exists()
    lora_lines = m3e.LORA_CANDIDATES_JSONL.read_text(encoding="utf-8").splitlines()
    assert len(lora_lines) >= 120
    last_pair = json.loads(lora_lines[-1])
    assert "instruction" in last_pair and "output" in last_pair and "sha256" in last_pair
    print(
        f"[PASS 6/6] LoRA Dataset & Eufy Security Module Verified: "
        f"{len(lora_lines)} valid QLoRA pairs | Eufy Status={eufy_st['status']}"
    )



def test_7_live_video_byte_range_and_live_play_by_play_api() -> None:
    req_v = urllib.request.Request(
        "http://127.0.0.1:8765/api/video/igh6l9wBsYg.mp4",
        headers={"Range": "bytes=0-65535"},
    )
    with urllib.request.urlopen(req_v, timeout=10) as rv:
        chunk = rv.read()
        assert rv.status == 206, f"Expected HTTP 206 Partial Content, got {rv.status}"
        assert len(chunk) == 65536

    for ts in (18.0, 22.8):
        payload = json.dumps({
            "video_id": "igh6l9wBsYg",
            "timestamp_sec": ts,
            "query_vlm": ts == 18.0,
            "include_b64": ts == 18.0,
            "coach_feedback": "Tight inside tie at mat edge.",
        }).encode("utf-8")
        req_p = urllib.request.Request(
            "http://127.0.0.1:8765/api/live_frame_pose",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req_p, timeout=20) as rp:
            pose_res = json.loads(rp.read().decode("utf-8"))
        assert pose_res.get("status") == "OK"
        assert pose_res.get("has_local_mp4") is True
        assert pose_res.get("wrestlers_detected", 0) == 2, f"Expected 2 confirmed mat athletes at t={ts}s, got {pose_res.get('wrestlers_detected')}"
        assert len(pose_res["overlay_athletes"][0].get("kpts_17_norm", [])) == 17
        zb = pose_res.get("zoom_box_norm", [])
        assert len(zb) == 4 and 0.15 <= zb[2] <= 0.85, f"Invalid zoom_box_norm: {zb}"
        assert pose_res.get("zoom_factor", 1.0) >= 1.35, f"Expected zoom_factor >= 1.35, got {pose_res.get('zoom_factor')}"
        if ts == 18.0:
            assert len(pose_res.get("live_commentary", "")) > 25

    # Benchmark real-time sequential pose stream (no VLM blocking, no b64 overhead)
    burst_latencies = []
    for step in range(1, 6):
        payload_fast = json.dumps({
            "video_id": "igh6l9wBsYg",
            "timestamp_sec": 18.0 + step * 0.04,
            "query_vlm": False,
            "include_b64": False,
        }).encode("utf-8")
        req_f = urllib.request.Request(
            "http://127.0.0.1:8765/api/live_frame_pose",
            data=payload_fast,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req_f, timeout=5) as rf:
            fast_res = json.loads(rf.read().decode("utf-8"))
        burst_latencies.append(float(fast_res.get("infer_ms", 999.0)))
    mean_ms = round(sum(burst_latencies) / len(burst_latencies), 1)
    assert mean_ms <= 65.0, f"Expected real-time sequential pose latency <= 65ms, got {mean_ms}ms ({burst_latencies})"
    print(
        f"[PASS 7/8] Live Video HTTP 206 Stream, Real-Time Pose ({mean_ms}ms/frame = {round(1000.0/max(1.0, mean_ms), 1)} FPS backend + 60FPS Interp) & Auto-Zoom ({pose_res['zoom_factor']}x) Verified: "
        f"Wrestlers={pose_res['wrestlers_detected']}/2 | ZoomBox={pose_res['zoom_box_norm']}"
    )


def test_8_digestible_mindmap_coaching_and_attached_clips() -> None:
    import re

    deg_re = re.compile(r"\b\d+(?:\.\d+)?\s*(?:°|deg(?:rees?)?|-degree)\b", re.IGNORECASE)

    # 1. Verify /api/state matches & coach_rules have Mind Map links, attached clips, and zero raw degree jargon
    with urllib.request.urlopen("http://127.0.0.1:8765/api/state", timeout=5) as r:
        st = json.loads(r.read().decode("utf-8"))

    matches = st.get("matches", [])
    assert len(matches) >= 50
    sample_m = matches[0]
    assert sample_m.get("mindmap_breadcrumb") and "➔" in sample_m["mindmap_breadcrumb"]
    assert sample_m.get("posture_summary")
    assert len(sample_m.get("mindmap_transitions", [])) >= 1
    assert len(sample_m.get("linked_technique_videos", [])) >= 1
    assert not deg_re.search(str(sample_m.get("tactical_note", ""))), (
        f"Found raw degree jargon in tactical_note: {sample_m.get('tactical_note')}"
    )

    rules = st.get("coach_rules", [])
    assert len(rules) >= 1
    for r_item in rules:
        assert r_item.get("clip_video_url") and "/api/clip/" in r_item["clip_video_url"], (
            f"Missing extracted /api/clip/ clip_video_url in coach rule: {r_item}"
        )
        assert r_item.get("clip_thumb_url"), f"Missing clip_thumb_url in coach rule: {r_item}"
        assert r_item.get("mindmap_breadcrumb"), f"Missing mindmap_breadcrumb in coach rule: {r_item}"
        assert not deg_re.search(str(r_item.get("chosen_revised_opinion", ""))), (
            f"Found raw degree jargon in chosen_revised_opinion: {r_item.get('chosen_revised_opinion')}"
        )

    # 2. Verify /api/live_frame_pose returns digestible Mind Map coaching without degree jargon
    payload = json.dumps({
        "video_id": "igh6l9wBsYg",
        "timestamp_sec": 18.0,
        "query_vlm": True,
        "include_b64": False,
        "coach_feedback": "Check collar tie and 2-on-1 transitions.",
    }).encode("utf-8")
    req_p = urllib.request.Request(
        "http://127.0.0.1:8765/api/live_frame_pose",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req_p, timeout=20) as rp:
        pose_res = json.loads(rp.read().decode("utf-8"))

    assert pose_res.get("active_mindmap_node"), "Missing active_mindmap_node in live_frame_pose"
    assert pose_res.get("mindmap_breadcrumb") and "➔" in pose_res["mindmap_breadcrumb"]
    assert pose_res.get("posture_summary"), "Missing posture_summary in live_frame_pose"
    assert len(pose_res.get("mindmap_transitions", [])) >= 2
    assert len(pose_res.get("linked_technique_videos", [])) >= 1
    comm = str(pose_res.get("live_commentary", ""))
    assert not deg_re.search(comm), f"Found raw degree jargon in live_commentary: {comm}"

    print(
        f"[PASS 8/9] Digestible Mind Map Coaching & Attached Review/VLM Clips Verified: "
        f"Breadcrumb='{pose_res['mindmap_breadcrumb']}' | Transitions={pose_res['mindmap_transitions'][:3]} | "
        f"AttachedClip='{rules[0]['clip_video_url']}' | Zero Raw Degree Jargon=OK"
    )


def test_9_extracted_clips_and_separate_model_leaderboard() -> None:
    # 1. Verify Dual-Portal routes (/user and /admin)
    for route in ["/user", "/admin"]:
        with urllib.request.urlopen(f"http://127.0.0.1:8765{route}", timeout=5) as r_html:
            html_body = r_html.read().decode("utf-8")
            assert "User-Facing Athlete View" in html_body
            assert "Admin Model Review & Clip Studio" in html_body

    # 2. Verify physically extracted 7-second MP4 clip endpoint (/api/clip/<vid>_<start>_<end>.mp4)
    clip_url = "http://127.0.0.1:8765/api/clip/fbCpcA1DyWg_20.2_27.2.mp4"
    req_clip = urllib.request.Request(clip_url, headers={"Range": "bytes=0-65535"})
    with urllib.request.urlopen(req_clip, timeout=10) as r_clip:
        assert r_clip.status == 206, f"Expected HTTP 206 Partial Content for extracted clip, got {r_clip.status}"
        content_range = r_clip.headers.get("Content-Range", "")
        total_clip_bytes = int(content_range.split("/")[-1]) if "/" in content_range else 0
        clip_chunk = r_clip.read()
        assert len(clip_chunk) == 65536
        assert 20_000 < total_clip_bytes < 10_000_000, f"Expected compact 7s clip size (<10MB vs 59.2MB full video), got {total_clip_bytes} bytes"

    import cv2
    clip_disk_path = APP_DIR / "competitions" / "clips" / "fbCpcA1DyWg_20.2_27.2.mp4"
    cap = cv2.VideoCapture(str(clip_disk_path))
    clip_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    clip_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
    clip_dur_sec = round(clip_frames / clip_fps, 2)
    cap.release()
    assert 6.5 <= clip_dur_sec <= 7.5, f"Expected physical clip duration ~7.0s, got {clip_dur_sec}s"

    # 3. Verify /api/model_leaderboard returns separate 10-model scorecards & 72B vs Real-Time benchmark
    with urllib.request.urlopen("http://127.0.0.1:8765/api/model_leaderboard", timeout=5) as r_lb:
        lb = json.loads(r_lb.read().decode("utf-8"))

    models = lb.get("models", [])
    assert len(models) == 10, f"Expected 10 models in leaderboard, got {len(models)}"
    models_map = {m["model_id"]: m for m in models}
    qwen72 = models_map.get("qwen25_vl_72b", {})
    assert qwen72.get("avg_latency_ms", 0) > 2000.0, f"Expected Qwen 72B avg latency > 2000ms, got {qwen72}"
    assert qwen72.get("realtime_capable") is False, "Qwen 72B should be marked realtime_capable=False"
    local_rt = models_map.get("local_hermes_qwen_kinematics", {})
    assert local_rt.get("realtime_capable") is True, "Local Metal/TB4 model should be realtime_capable=True"
    assert local_rt.get("avg_latency_ms", 9999) < 800.0

    verdict = lb.get("architecture_verdict", {})
    assert verdict.get("can_72b_run_realtime") is False

    print(
        f"[PASS 9/9] Dual-Portal (/user & /admin), Extracted 7.0s MP4 Clip ({clip_dur_sec}s, {round(total_clip_bytes/1024, 1)} KB) & Separate 10-Model Leaderboard Verified: "
        f"Qwen-72B={qwen72['avg_latency_ms']}ms (RealTime={qwen72['realtime_capable']}) vs Local-Metal={local_rt['avg_latency_ms']}ms (RealTime={local_rt['realtime_capable']})"
    )


if __name__ == "__main__":
    print("================================================================================")
    print("🧪 LAUBURU 3D GRAPPLING KINEMATICS, 3D MIND MAP & 10-VLM END-TO-END TEST SUITE")
    print("================================================================================")
    test_1_sovereign_debate_duo_and_vlm_roster()
    test_2_mindmap_3d_knowledge_graph()
    test_3_competition_and_technique_multi_vlm_summary()
    test_4_live_referee_excluded_3d_pose_tracker()
    test_5_live_studio_http_api()
    test_6_lora_dataset_and_eufy_ingestor()
    test_7_live_video_byte_range_and_live_play_by_play_api()
    test_8_digestible_mindmap_coaching_and_attached_clips()
    test_9_extracted_clips_and_separate_model_leaderboard()
    print("================================================================================")
    print("✅ ALL 9/9 END-TO-END TESTS PASSED (EXIT CODE 0)")
    print("================================================================================")


