# 🥋 3D Grappling Kinematics & TB4 VLA Tactical Report: `Kf0wQ00FPBg_Collar tie 2 on 1 entry to collar tie`

- **Timestamp (UTC)**: `2026-10-14T12:33:52Z`
- **Source Video**: `Kf0wQ00FPBg_Collar tie 2 on 1 entry to collar tie.mp4` (`3840x2160` @ `30.0 fps`, `33.5s`, `1005` frames)
- **3D Poses Extracted**: `991/1005` frames (`26` dual-athlete frames)
- **Stage 1 Multimodal 3D VLA**: `Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf` via `http://10.0.0.3:8090/v1 (Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf + mmproj-Q8_0 (TB4 L1b))`
- **Stage 2 Biomechanical Synthesis**: `Hermes-3-Llama-3.1-8B.Q4_K_M.gguf` via `http://127.0.0.1:8085/v1 (Hermes-3-Llama-3.1-8B.Q4_K_M.gguf (L1 Local 8B))`
- **Inference Duration**: `407.03s`

---

## 1. Stage 1: Qwen2.5-VL Multimodal 3D Spatial Grounding
### Analysis of Keyframes and 3D World Coordinates

#### Keyframe 0
- **Stance**: Athlete 1 (female) is in a wide stance with her feet shoulder-width apart, knees slightly bent. Her weight appears to be slightly forward. Athlete 2 (male) is in a more narrow stance, with his feet closer together and knees bent, indicating readiness to move. Both athletes are maintaining a relatively straight posture.
- **Collar Tie Grip**: Athlete 2 has his right hand on Athlete 1's collar, preparing for a 2-on-1 collar tie entry. His left hand is positioned near Athlete 1's left arm, possibly to assist in controlling it.
- **Spatial Angle Changes**: Athlete 2's right elbow is bent at approximately 137.6 degrees, and his left elbow is bent at 108.8 degrees. Athlete 1's right shoulder is slightly forward at 100.4 degrees, which might indicate a slight forward lean or weight shift.

#### Keyframe 167
- **Stance**: Athlete 1's stance appears to have shifted slightly, with her knees bent and weight slightly forward. Athlete 2's stance is more dynamic, with his knees bent and his weight shifting forward, indicating he is in the process of executing the 2-on-1 entry.
- **Collar Tie Grip**: Athlete 2's right hand is still on Athlete 1's collar, and his left hand is now positioned to grab the other side of Athlete 1's collar. This suggests he is transitioning into the collar tie grip.
- **Spatial Angle Changes**: Athlete 2's right elbow is bent at 164.0 degrees, and his left elbow is bent at 121.0 degrees, indicating a more pronounced bend in his arms. Athlete 1's right shoulder is at 8.0 degrees, which could indicate a significant forward lean or weight shift.

#### Keyframe 334
- **Stance**: Athlete 1's stance remains relatively stable, with her knees bent and weight slightly forward. Athlete

---

## 2. Stage 2: 3D Biomechanical & Tactical Breakdown
### 3D Kinematic & Postural Breakdown

**Spine Lean Angles**:
- Athlete 1's spine forward lean angle decreases from 113.4 degrees at Keyframe 0 to 5.1 degrees at Keyframe 334. This indicates a significant forward lean as Athlete 2 controls the tie-up, shifting Athlete 1's weight forward and upward.

**Elbow/Shoulder Flexion Asymmetries**:
- Athlete 2's right elbow flexion increases from 137.6 degrees to 163.3 degrees, while his left elbow flexion increases from 108.8 degrees to 107.4 degrees. This asymmetry allows Athlete 2 to maintain control and create leverage through his right arm.

**Hip Center-of-Mass Trajectory**:
- Athlete 1's hip center-of-mass remains relatively stable, with minor changes in the z-coordinate from -0.0 meters to 0.001 meters. This suggests that Athlete 1's center of mass is being controlled and maintained in a position that is favorable for Athlete 2 to execute further techniques.

### Grip & Tie-Up Mechanics

The observed tie-up mechanics, transitioning from a collar tie to a 2-on-1 entry, create mechanical leverage for Athlete 2. By controlling Athlete 1's collar with his right hand and positioning his left hand to assist in controlling Athlete 1's left arm, Athlete 2 is able to:

1. Shift Athlete 1's weight forward and upward, creating a more vulnerable position.
2. Maintain control over Athlete 1's center of mass, making it easier to execute follow-up techniques.
3. Create an angle that allows for potential snatches, ankle picks, or back-takes.

### Tactical Vulnerabilities & Follow-Up Chain

**Snatch Single**:
- Athlete 2's control of Athlete 1's collar and left arm, combined with the forward lean and upward shift in Athlete 1's weight, creates an opportunity for a snatch single. Athlete 2 can step over Athlete 1's legs, grab their near elbow, and execute a snatch single to take Athlete 1 down.

**Ankle Pick**:
- The forward lean and controlled center of mass position also create an opportunity for an ankle pick. Athlete 2 can step in closer, control Athlete 1's head with his left hand, and execute an ankle pick to take Athlete 1 down.

**Front Headlock**:
- Athlete 2's control of Athlete 1's collar and left arm, combined with the forward lean, could also lead to a front headlock. Athlete 2 can transition to controlling Athlete 1's head with his right hand, placing it in a front headlock position.

**Back-Take**:
- The forward lean and upward shift in Athlete 1's weight, along with the control of their collar and left arm, create an opportunity for a back-take. Athlete 2 can step in closer, control Athlete 1's head, and execute a back-take to take Athlete 1 down and gain control from the back position.

In conclusion, the 3D kinematic and postural breakdown, grip and tie-up mechanics, and tactical vulnerabilities all contribute to Athlete 2's ability to control the situation and potentially execute a snatch single, ankle pick, front headlock, or back-take based on the measured 3D angles.

---

## 3. Sampled 3D MediaPipe World Landmarks (meters) & Joint Angles (degrees)
```json
[
  {
    "frame_index": 0,
    "timestamp_ms": 0,
    "athletes_detected": 1,
    "athletes": [
      {
        "athlete_id": "Athlete_1",
        "normalized_hip_center": [
          0.448,
          0.529,
          -0.0
        ],
        "biomechanics_3d": {
          "angles_deg": {
            "left_elbow": 137.6,
            "right_elbow": 108.8,
            "left_shoulder": 113.3,
            "right_shoulder": 100.4,
            "left_hip": 121.7,
            "right_hip": 165.4,
            "left_knee": 152.8,
            "right_knee": 176.5,
            "spine_forward_lean": 113.4
          },
          "world_meters": {
            "nose": [
              -0.003,
              0.19,
              -0.703
            ],
            "left_wrist": [
              -0.225,
              -0.003,
              -0.724
            ],
            "right_wrist": [
              0.295,
              0.107,
              -0.798
            ],
            "left_elbow": [
              -0.208,
              0.013,
              -0.6
            ],
            "right_elbow": [
              0.18,
              0.017,
              -0.602
            ],
            "shoulder_center": [
              -0.022,
              0.197,
              -0.451
            ],
            "hip_center": [
              0.0,
              0.002,
              -0.0
            ]
          }
        }
      }
    ],
    "tie_up_proximity": null
  },
  {
    "frame_index": 167,
    "timestamp_ms": 5567,
    "athletes_detected": 1,
    "athletes": [
      {
        "athlete_id": "Athlete_1",
        "normalized_hip_center": [
          0.423,
          0.519,
          -0.0
        ],
        "biomechanics_3d": {
          "angles_deg": {
            "left_elbow": 121.0,
            "right_elbow": 164.0,
            "left_shoulder": 90.4,
            "right_shoulder": 8.0,
            "left_hip": 159.6,
            "right_hip": 169.5,
            "left_knee": 153.3,
            "right_knee": 150.6,
            "spine_forward_lean": 13.4
          },
          "world_meters": {
            "nose": [
              0.161,
              -0.572,
              -0.192
            ],
            "left_wrist": [
              0.437,
              -0.502,
              -0.198
            ],
            "right_wrist": [
              -0.107,
              -0.057,
              -0.079
            ],
            "left_elbow": [
              0.38,
              -0.407,
              -0.099
            ],
            "right_elbow": [
              -0.105,
              -0.238,
              -0.033
            ],
            "shoulder_center": [
              0.119,
              -0.496,
              0.01
            ],
            "hip_center": [
              0.002,
              -0.002,
              0.001
            ]
          }
        }
      }
    ],
    "tie_up_proximity": null
  },
  {
    "frame_index": 334,
    "timestamp_ms": 11133,
    "athletes_detected": 1,
    "athletes": [
      {
        "athlete_id": "Athlete_1",
        "normalized_hip_center": [
          0.424,
          0.515,
          -0.0
        ],
        "biomechanics_3d": {
          "angles_deg": {
            "left_elbow": 107.4,
            "right_elbow": 163.3,
            "left_shoulder": 50.3,
            "right_shoulder": 12.4,
            "left_hip": 169.5,
            "right_hip": 178.9,
            "left_knee": 158.2,
            "right_knee": 155.5,
            "spine_forward_lean": 5.1
          },
          "world_meters": {
            "nose": [
              0.131,
              -0.589,
              -0.202
            ],
            "left_wrist": [
              0.316,
              -0.388,
              -0.16
            ],
            "right_wrist": [
              -0.144,
              -0.035,
              -0.111
            ],
            "left_elbow": [
              0.269,
              -0.344,
              -0.001
            ],
            "right_elbow": [
              -0.155,
              -0.201,
              -0.071
            ],
            "shoulder_center": [
              0.044,
              -0.5,
              0.015
            ],
            "hip_center": [
              0.002,
              -0.002,
              0.001
            ]
          }
        }
      }
    ],
    "tie_up_proximity": null
  }
]
```

---

## 4. Tri-Proof Artifact Verification (Rule 1 §2)
- **Annotated Video**: `/Users/Shared/aaron/DFS_UNIFIED/Lauburu-Monorepo/10_spatial_grappling_kinematics/app/inbox/Kf0wQ00FPBg_Collar tie 2 on 1 entry to collar tie_annotated.mp4` (`21807464` bytes, SHA256: `e25d2b6aa33e575c060d9e1bba2909992439fcae1ec037e802ec8b88697bb21c`)
- **3D Kinematic JSON**: `/Users/Shared/aaron/DFS_UNIFIED/Lauburu-Monorepo/10_spatial_grappling_kinematics/app/inbox/Kf0wQ00FPBg_Collar tie 2 on 1 entry to collar tie_data.json` (`1626466` bytes, SHA256: `18136d0cbff2c761bb34a28f4d80fe42f519a28801141c0f9ddcc340a1f9ed8e`)
