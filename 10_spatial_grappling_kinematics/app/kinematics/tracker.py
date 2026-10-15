import cv2
import mediapipe as mp
import json
import math
import argparse
import sys
import urllib.request
import base64
from pathlib import Path
from typing import Tuple, List, Dict, Any, Optional

# MediaPipe Pose Landmark Indices (BlazePose 33-point topology)
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


def download_model(model_path: str, url: str):
    if not Path(model_path).exists():
        print(f"Downloading model {model_path}...")
        urllib.request.urlretrieve(url, model_path)


def _vec3(a, b) -> Tuple[float, float, float]:
    return (a.x - b.x, a.y - b.y, a.z - b.z)


def _norm3(v: Tuple[float, float, float]) -> float:
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def _angle_3d_deg(a, b, c) -> float:
    """Compute true 3D interior angle at vertex b (in degrees) from 3D metric world landmarks."""
    u = _vec3(a, b)
    v = _vec3(c, b)
    nu, nv = _norm3(u), _norm3(v)
    if nu < 1e-6 or nv < 1e-6:
        return 0.0
    cos_theta = max(-1.0, min(1.0, (u[0] * v[0] + u[1] * v[1] + u[2] * v[2]) / (nu * nv)))
    return round(math.degrees(math.acos(cos_theta)), 1)


def _compute_3d_biomechanics(world_lms) -> Dict[str, Any]:
    """Extract 3D joint angles (degrees) and metric keypoint positions (meters) from MediaPipe world landmarks."""
    l_elbow_deg = _angle_3d_deg(world_lms[LM_L_SHOULDER], world_lms[LM_L_ELBOW], world_lms[LM_L_WRIST])
    r_elbow_deg = _angle_3d_deg(world_lms[LM_R_SHOULDER], world_lms[LM_R_ELBOW], world_lms[LM_R_WRIST])
    l_shoulder_deg = _angle_3d_deg(world_lms[LM_L_HIP], world_lms[LM_L_SHOULDER], world_lms[LM_L_ELBOW])
    r_shoulder_deg = _angle_3d_deg(world_lms[LM_R_HIP], world_lms[LM_R_SHOULDER], world_lms[LM_R_ELBOW])
    l_hip_deg = _angle_3d_deg(world_lms[LM_L_SHOULDER], world_lms[LM_L_HIP], world_lms[LM_L_KNEE])
    r_hip_deg = _angle_3d_deg(world_lms[LM_R_SHOULDER], world_lms[LM_R_HIP], world_lms[LM_R_KNEE])
    l_knee_deg = _angle_3d_deg(world_lms[LM_L_HIP], world_lms[LM_L_KNEE], world_lms[LM_L_ANKLE])
    r_knee_deg = _angle_3d_deg(world_lms[LM_R_HIP], world_lms[LM_R_KNEE], world_lms[LM_R_ANKLE])

    # Spine inclination relative to vertical Y-axis (in MediaPipe world space, -Y is up)
    hip_mid = (
        0.5 * (world_lms[LM_L_HIP].x + world_lms[LM_R_HIP].x),
        0.5 * (world_lms[LM_L_HIP].y + world_lms[LM_R_HIP].y),
        0.5 * (world_lms[LM_L_HIP].z + world_lms[LM_R_HIP].z),
    )
    sh_mid = (
        0.5 * (world_lms[LM_L_SHOULDER].x + world_lms[LM_R_SHOULDER].x),
        0.5 * (world_lms[LM_L_SHOULDER].y + world_lms[LM_R_SHOULDER].y),
        0.5 * (world_lms[LM_L_SHOULDER].z + world_lms[LM_R_SHOULDER].z),
    )
    spine_vec = (sh_mid[0] - hip_mid[0], sh_mid[1] - hip_mid[1], sh_mid[2] - hip_mid[2])
    spine_len = _norm3(spine_vec)
    # Angle from upright (-Y axis: 0, -1, 0)
    spine_forward_lean_deg = 0.0
    if spine_len > 1e-6:
        cos_up = max(-1.0, min(1.0, (-spine_vec[1]) / spine_len))
        spine_forward_lean_deg = round(math.degrees(math.acos(cos_up)), 1)

    return {
        "angles_deg": {
            "left_elbow": l_elbow_deg,
            "right_elbow": r_elbow_deg,
            "left_shoulder": l_shoulder_deg,
            "right_shoulder": r_shoulder_deg,
            "left_hip": l_hip_deg,
            "right_hip": r_hip_deg,
            "left_knee": l_knee_deg,
            "right_knee": r_knee_deg,
            "spine_forward_lean": spine_forward_lean_deg,
        },
        "world_meters": {
            "nose": [round(world_lms[LM_NOSE].x, 3), round(world_lms[LM_NOSE].y, 3), round(world_lms[LM_NOSE].z, 3)],
            "left_wrist": [round(world_lms[LM_L_WRIST].x, 3), round(world_lms[LM_L_WRIST].y, 3), round(world_lms[LM_L_WRIST].z, 3)],
            "right_wrist": [round(world_lms[LM_R_WRIST].x, 3), round(world_lms[LM_R_WRIST].y, 3), round(world_lms[LM_R_WRIST].z, 3)],
            "left_elbow": [round(world_lms[LM_L_ELBOW].x, 3), round(world_lms[LM_L_ELBOW].y, 3), round(world_lms[LM_L_ELBOW].z, 3)],
            "right_elbow": [round(world_lms[LM_R_ELBOW].x, 3), round(world_lms[LM_R_ELBOW].y, 3), round(world_lms[LM_R_ELBOW].z, 3)],
            "shoulder_center": [round(sh_mid[0], 3), round(sh_mid[1], 3), round(sh_mid[2], 3)],
            "hip_center": [round(hip_mid[0], 3), round(hip_mid[1], 3), round(hip_mid[2], 3)],
        }
    }


def process_video(input_path: str, max_vla_frames: int = 6) -> Tuple[str, str, List[str], Dict[str, Any]]:
    """
    Process video to extract 2D normalized + 3D World Pose landmarks (in meters) for up to 2 grapplers.
    Computes 3D joint angles, posture lean, and inter-athlete tie-up geometry.
    Renders annotated output video and returns resized base64 keyframes + kinematic summary dict.
    """
    input_p = Path(input_path)
    if not input_p.exists():
        raise FileNotFoundError(f"Input video not found: {input_path}")

    output_video_path = str(input_p.with_name(f"{input_p.stem}_annotated.mp4"))
    output_data_path = str(input_p.with_name(f"{input_p.stem}_data.json"))

    model_dir = Path(__file__).resolve().parent.parent
    model_path = str(model_dir / "pose_landmarker_heavy.task")
    download_model(
        model_path,
        "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_heavy/float16/1/pose_landmarker_heavy.task",
    )

    cap = cv2.VideoCapture(str(input_p))
    if not cap.isOpened():
        raise ValueError(f"Could not open video: {input_path}")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames_est = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 300
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0 or math.isnan(fps):
        fps = 30.0

    # Downscale output video if 4K so annotation & disk write are fast and clean
    out_w, out_h = width, height
    if width > 1280:
        scale = 1280.0 / width
        out_w = 1280
        out_h = int(height * scale)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_video_path, fourcc, fps, (out_w, out_h))

    mp_pose = mp.tasks.vision.PoseLandmarker
    BaseOptions = mp.tasks.BaseOptions
    PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions
    VisionRunningMode = mp.tasks.vision.RunningMode

    options = PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=model_path),
        running_mode=VisionRunningMode.VIDEO,
        num_poses=2,
        min_pose_detection_confidence=0.45,
        min_pose_presence_confidence=0.45,
        min_tracking_confidence=0.45,
    )

    frame_data = []
    candidate_keyframes: List[Tuple[int, str]] = []
    sample_stride = max(1, total_frames_est // max(1, max_vla_frames))

    colors = [(0, 255, 128), (255, 165, 0)]  # Athlete A (Green), Athlete B (Orange)
    shot_counter = 0
    in_shot_state = False
    standing_frames = 0
    ground_frames = 0

    with mp_pose.create_from_options(options) as landmarker:
        frame_idx = 0
        last_ts_ms = -1
        while cap.isOpened():
            success, image = cap.read()
            if not success:
                break

            timestamp_ms = int(round(frame_idx * 1000.0 / fps))
            if timestamp_ms <= last_ts_ms:
                timestamp_ms = last_ts_ms + 1
            last_ts_ms = timestamp_ms

            if out_w != width:
                proc_img = cv2.resize(image, (out_w, out_h), interpolation=cv2.INTER_AREA)
            else:
                proc_img = image

            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(proc_img, cv2.COLOR_BGR2RGB))
            result = landmarker.detect_for_video(mp_image, timestamp_ms)

            annotated_image = proc_img.copy()
            athletes_frame = []
            live_phase = "SCANNING MAT..."
            live_coaching_cue = "Tracking 3D World Landmarks (100% Local Offline Engine)..."
            active_grip_tag = "OPEN DISTANCE"

            if result.pose_landmarks and result.pose_world_landmarks:
                # Sort detected poses left-to-right by hip X so Athlete_0 and Athlete_1 stay consistent
                paired = list(zip(result.pose_landmarks, result.pose_world_landmarks))
                paired.sort(key=lambda pair: 0.5 * (pair[0][LM_L_HIP].x + pair[0][LM_R_HIP].x))

                for p_idx, (norm_lms, world_lms) in enumerate(paired):
                    color = colors[p_idx % len(colors)]
                    # Draw skeletal connections
                    for i_a, i_b in POSE_CONNECTIONS:
                        pt1 = (int(norm_lms[i_a].x * out_w), int(norm_lms[i_a].y * out_h))
                        pt2 = (int(norm_lms[i_b].x * out_w), int(norm_lms[i_b].y * out_h))
                        cv2.line(annotated_image, pt1, pt2, color, 2, cv2.LINE_AA)
                    for lm in norm_lms:
                        x, y = int(lm.x * out_w), int(lm.y * out_h)
                        cv2.circle(annotated_image, (x, y), 4, color, -1, cv2.LINE_AA)

                    biomech = _compute_3d_biomechanics(world_lms)
                    angles = biomech["angles_deg"]
                    # Annotate athlete label + elbow/spine/knee angles on HUD
                    head_x = max(10, min(out_w - 260, int(norm_lms[LM_NOSE].x * out_w) - 40))
                    head_y = max(65, int(norm_lms[LM_NOSE].y * out_h) - 18)
                    label = (
                        f"A{p_idx+1} Spine:{angles['spine_forward_lean']:.0f}d "
                        f"Knee:{min(angles['left_knee'], angles['right_knee']):.0f}d "
                        f"Elb:{min(angles['left_elbow'], angles['right_elbow']):.0f}d"
                    )
                    cv2.rectangle(
                        annotated_image,
                        (head_x - 4, head_y - 16),
                        (head_x + 255, head_y + 5),
                        (15, 20, 30),
                        -1,
                    )
                    cv2.putText(annotated_image, label, (head_x, head_y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)

                    athletes_frame.append({
                        "athlete_id": f"Athlete_{p_idx+1}",
                        "normalized_hip_center": [
                            round(0.5 * (norm_lms[LM_L_HIP].x + norm_lms[LM_R_HIP].x), 3),
                            round(0.5 * (norm_lms[LM_L_HIP].y + norm_lms[LM_R_HIP].y), 3),
                            round(0.5 * (norm_lms[LM_L_HIP].z + norm_lms[LM_R_HIP].z), 3),
                        ],
                        "biomechanics_3d": biomech,
                    })

            # Compute inter-athlete tie-up proximity & real-time visual callouts
            tie_up_metrics: Optional[Dict[str, float]] = None
            if athletes_frame:
                # Determine Standing vs. Ground state from hip Y height & spine lean
                avg_hip_y = sum(a["normalized_hip_center"][1] for a in athletes_frame) / len(athletes_frame)
                max_spine_lean = max(a["biomechanics_3d"]["angles_deg"]["spine_forward_lean"] for a in athletes_frame)
                min_knee_angle = min(
                    min(a["biomechanics_3d"]["angles_deg"]["left_knee"], a["biomechanics_3d"]["angles_deg"]["right_knee"])
                    for a in athletes_frame
                )

                is_ground = (avg_hip_y > 0.68) or (max_spine_lean > 62.0 and avg_hip_y > 0.58)
                if is_ground:
                    ground_frames += 1
                    live_phase = "GROUND GRAPPLING (GUARD / PIN WORK)"
                    live_coaching_cue = "GROUND: Keep elbow-knee connection tight; monitor hip angle & crossface pressure."
                else:
                    standing_frames += 1
                    live_phase = "STANDING WRESTLING / HAND-FIGHT"
                    live_coaching_cue = "STANDING: Head position inside, elbows tight, level-change before reaching."

                # Detect level-change / takedown shot in real time
                is_level_change = (not is_ground) and (min_knee_angle < 118.0 or (max_spine_lean > 42.0 and avg_hip_y > 0.52))
                if is_level_change:
                    if not in_shot_state:
                        shot_counter += 1
                        in_shot_state = True
                    live_phase = f"LEVEL CHANGE / TAKEDOWN ENTRY (SHOT #{shot_counter})"
                    live_coaching_cue = f"SHOT ENTRY #{shot_counter}: Drive knees through target, keep spine <45d & head up!"
                else:
                    in_shot_state = False

            if result.pose_landmarks and len(result.pose_landmarks) >= 2:
                a0, a1 = paired[0][0], paired[1][0]
                a1_neck = (
                    0.5 * (a1[LM_L_SHOULDER].x + a1[LM_R_SHOULDER].x),
                    0.5 * (a1[LM_L_SHOULDER].y + a1[LM_R_SHOULDER].y),
                    0.5 * (a1[LM_L_SHOULDER].z + a1[LM_R_SHOULDER].z),
                )
                a0_neck = (
                    0.5 * (a0[LM_L_SHOULDER].x + a0[LM_R_SHOULDER].x),
                    0.5 * (a0[LM_L_SHOULDER].y + a0[LM_R_SHOULDER].y),
                    0.5 * (a0[LM_L_SHOULDER].z + a0[LM_R_SHOULDER].z),
                )
                l_wrist_to_neck = math.sqrt(
                    (a0[LM_L_WRIST].x - a1_neck[0]) ** 2
                    + (a0[LM_L_WRIST].y - a1_neck[1]) ** 2
                    + (a0[LM_L_WRIST].z - a1_neck[2]) ** 2
                )
                r_wrist_to_neck = math.sqrt(
                    (a0[LM_R_WRIST].x - a1_neck[0]) ** 2
                    + (a0[LM_R_WRIST].y - a1_neck[1]) ** 2
                    + (a0[LM_R_WRIST].z - a1_neck[2]) ** 2
                )
                wrist_to_opp_l_elbow = min(
                    math.hypot(a0[LM_L_WRIST].x - a1[LM_L_ELBOW].x, a0[LM_L_WRIST].y - a1[LM_L_ELBOW].y),
                    math.hypot(a0[LM_R_WRIST].x - a1[LM_L_ELBOW].x, a0[LM_R_WRIST].y - a1[LM_L_ELBOW].y),
                )
                wrist_to_opp_r_elbow = min(
                    math.hypot(a0[LM_L_WRIST].x - a1[LM_R_ELBOW].x, a0[LM_L_WRIST].y - a1[LM_R_ELBOW].y),
                    math.hypot(a0[LM_R_WRIST].x - a1[LM_R_ELBOW].x, a0[LM_R_WRIST].y - a1[LM_R_ELBOW].y),
                )
                min_neck_dist = round(min(l_wrist_to_neck, r_wrist_to_neck), 3)
                min_elbow_dist = round(min(wrist_to_opp_l_elbow, wrist_to_opp_r_elbow), 3)
                tie_up_metrics = {
                    "min_wrist_to_opponent_neck_norm": min_neck_dist,
                    "min_wrist_to_opponent_elbow_norm": min_elbow_dist,
                }

                # Draw real-time tie-up / grip vector lines directly on the video frame
                neck_pt = (int(a1_neck[0] * out_w), int(a1_neck[1] * out_h))
                w_lm = a0[LM_L_WRIST] if l_wrist_to_neck <= r_wrist_to_neck else a0[LM_R_WRIST]
                wrist_pt = (int(w_lm.x * out_w), int(w_lm.y * out_h))

                if min_elbow_dist < 0.14 and min_neck_dist < 0.22:
                    active_grip_tag = "2-ON-1 / COLLAR-TIE ENTRY"
                    cv2.line(annotated_image, wrist_pt, neck_pt, (255, 0, 255), 3, cv2.LINE_AA)
                    live_coaching_cue = "LIVE GRIP: 2-on-1 / Collar-Tie engaged — off-balance (kuzushi) to clear inside channel!"
                elif min_neck_dist < 0.18:
                    active_grip_tag = "COLLAR TIE CLINCH"
                    cv2.line(annotated_image, wrist_pt, neck_pt, (0, 255, 255), 3, cv2.LINE_AA)
                    live_coaching_cue = "LIVE GRIP: Collar-Tie active — snap down or Russian 2-on-1 peel; don't hang on neck!"
                elif min_elbow_dist < 0.16:
                    active_grip_tag = "ELBOW / WRIST 2-ON-1"
                    live_coaching_cue = "LIVE GRIP: Elbow/Wrist control — circle to T-angle and attack near leg or back!"

            # Render Real-Time Broadcast HUD Overlay directly onto every video frame
            overlay = annotated_image.copy()
            cv2.rectangle(overlay, (0, 0), (out_w, 52), (10, 14, 24), -1)
            cv2.rectangle(overlay, (0, out_h - 40), (out_w, out_h), (10, 14, 24), -1)
            cv2.addWeighted(overlay, 0.78, annotated_image, 0.22, 0, annotated_image)

            # Top HUD: Real-time Phase, Grip State, Shot Counter, Standing/Ground %
            tot_pos = max(1, standing_frames + ground_frames)
            stand_pct = int(round(100.0 * standing_frames / tot_pos))
            hud_top_left = f"LIVE 3D HUD | {live_phase}"
            hud_top_right = f"GRIP: {active_grip_tag} | SHOTS: {shot_counter} | STAND: {stand_pct}%"
            cv2.putText(annotated_image, hud_top_left, (14, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 180), 2, cv2.LINE_AA)
            cv2.putText(annotated_image, hud_top_right, (14, 44), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 215, 0), 1, cv2.LINE_AA)

            # Bottom HUD: Real-Time Action Coaching Callout (No timestamp checking required)
            cv2.putText(annotated_image, live_coaching_cue, (14, out_h - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (240, 248, 255), 1, cv2.LINE_AA)

            out.write(annotated_image)

            if os.environ.get("GRAPPLING_LIVE_WINDOW") == "1":
                cv2.imshow("Lauburu 3D Grappling Real-Time HUD (Offline Local)", annotated_image)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

            if frame_idx % sample_stride == 0 and len(candidate_keyframes) < max_vla_frames:
                vla_img = cv2.resize(annotated_image, (640, int(640 * out_h / out_w)), interpolation=cv2.INTER_AREA)
                _, buffer = cv2.imencode(".jpg", vla_img, [int(cv2.IMWRITE_JPEG_QUALITY), 82])
                b64_str = base64.b64encode(buffer).decode("utf-8")
                candidate_keyframes.append((frame_idx, b64_str))

            frame_data.append({
                "frame_index": frame_idx,
                "timestamp_ms": timestamp_ms,
                "live_phase": live_phase,
                "active_grip": active_grip_tag,
                "shot_counter": shot_counter,
                "athletes_detected": len(athletes_frame),
                "athletes": athletes_frame,
                "tie_up_proximity": tie_up_metrics,
            })
            frame_idx += 1

    cap.release()
    out.release()
    if os.environ.get("GRAPPLING_LIVE_WINDOW") == "1":
        cv2.destroyAllWindows()

    # Build a compact, token-efficient 3D kinematic summary across key temporal checkpoints for the 32B/VL model
    keyframe_indices = {idx for idx, _ in candidate_keyframes}
    sampled_kinematics = [f for f in frame_data if f["frame_index"] in keyframe_indices]
    frames_With_poses = sum(1 for f in frame_data if f["athletes_detected"] > 0)
    frames_with_two_athletes = sum(1 for f in frame_data if f["athletes_detected"] >= 2)

    kinematic_summary = {
        "video_file": input_p.name,
        "resolution": f"{width}x{height}",
        "fps": round(fps, 2),
        "total_frames": frame_idx,
        "duration_sec": round(frame_idx / fps, 2),
        "frames_with_3d_pose": frames_With_poses,
        "frames_with_two_grapplers": frames_with_two_athletes,
        "total_shots_detected_realtime": shot_counter,
        "standing_ratio_pct": round(100.0 * standing_frames / max(1, standing_frames + ground_frames), 1),
        "coordinate_system": "MediaPipe 3D World Landmarks (meters, origin at hip center) + Real-Time On-Video Tactical HUD",
        "keyframe_3d_kinematics": sampled_kinematics,
    }

    full_payload = {
        "summary": kinematic_summary,
        "all_frames": frame_data,
    }
    with open(output_data_path, "w") as f:
        json.dump(full_payload, f, indent=2)

    print(f"Processed {frame_idx} frames ({kinematic_summary['duration_sec']}s @ {kinematic_summary['fps']} fps).")
    print(f"3D Poses detected in {frames_With_poses}/{frame_idx} frames (2 grapplers in {frames_with_two_athletes} frames).")
    print(f"Real-Time On-Video HUD saved to {output_video_path}")
    print(f"Output 3D data saved to {output_data_path}")

    frames_b64 = [b64 for _, b64 in candidate_keyframes]
    return output_video_path, output_data_path, frames_b64, kinematic_summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract 3D World Pose landmarks and real-time on-video HUD from a grappling video.")
    parser.add_argument("--input", required=True, help="Path to input video file")
    parser.add_argument("--live", action="store_true", help="Display real-time OpenCV HUD window during processing")
    args = parser.parse_args()
    if args.live:
        os.environ["GRAPPLING_LIVE_WINDOW"] = "1"
    try:
        process_video(args.input)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
