import os
import json
import time
import urllib.request
from openai import OpenAI
from typing import List, Dict, Any, Tuple, Optional


class GrapplingVLAClient:
    """
    Zero-Mock TB4 3D VLA & Biomechanical Analysis Client.
    Coordinates:
      1. Multimodal 3D Visual Grounding on TB4 Node L1b (10.0.0.3:8090 / 100.104.128.34:8090)
         running Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf + mmproj-Qwen2.5-VL-7B-Instruct-Q8_0.gguf
         (or Qwen2.5-VL-32B-Instruct.Q4_K_M.gguf on :8092 when TB4 RPC shard is mounted).
      2. Deep 3D Biomechanical & Tactical Synthesis on TB4 Ring (:8083 Qwen3.8-27B / :8085 Hermes-3-8B).
    Strictly reports authentic physical GGUF model attribution per Rule 1 §9.
    """

    VL_ENDPOINTS = [
        ("http://10.0.0.3:8092/v1", "Qwen2.5-VL-32B-Instruct.Q4_K_M.gguf (TB4 Shard L1+L1b)"),
        ("http://10.0.0.3:8090/v1", "Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf + mmproj-Q8_0 (TB4 L1b)"),
        ("http://100.104.128.34:8090/v1", "Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf + mmproj-Q8_0 (Tailscale L1b)"),
    ]

    REASONING_ENDPOINTS = [
        ("http://127.0.0.1:8085/v1", "Hermes-3-Llama-3.1-8B.Q4_K_M.gguf (L1 Local 8B)"),
        ("http://127.0.0.1:8083/v1", "Huihui-Qwen3.8-27B-abliterated-UD-Q4_K_XL.gguf (TB4 L8 :8083)"),
        ("http://127.0.0.1:8082/v1", "mesh-local-proxy (:8082)"),
    ]

    def __init__(self, base_url: Optional[str] = None, api_key: str = "dummy"):
        self.override_base_url = base_url
        self.api_key = api_key
        self.vla_system_prompt = (
            "You are a 3D Vision-Language Grappling Perception Engine (Qwen2.5-VL). "
            "Given keyframe images from a grappling instructional/sparring video and 3D MediaPipe World Landmarks "
            "(in meters [x, y, z] centered at each athlete's hips, plus 3D joint angles in degrees), "
            "identify:\n"
            "1. 2D/3D spatial positioning of Athlete 1 and Athlete 2 (stance, level change, head position).\n"
            "2. Hand-fighting and tie-up grips visible in the frames (e.g., collar tie, 2-on-1 Russian tie, wrist/elbow control, inside tie).\n"
            "3. Key weight shifts and off-balancing (kuzushi) moments across the frames."
        )
        self.tactical_system_prompt = (
            "You are an elite wrestling and Brazilian Jiu-Jitsu biomechanics & tactical analyst. "
            "Analyze the extracted 3D MediaPipe World Landmarks (in meters [x, y, z]), 3D joint flexion/extension angles "
            "(elbow, shoulder, hip, knee, spine forward lean in degrees), inter-athlete tie-up proximity metrics, "
            "and Qwen2.5-VL visual grounding observations.\n"
            "Provide a structured, zero-mock breakdown with:\n"
            "1. **3D Kinematic & Postural Breakdown**: Interpret spine lean angles, elbow/shoulder flexion asymmetries, and hip center-of-mass trajectory in meters.\n"
            "2. **Grip & Tie-Up Mechanics**: Explain how the observed tie-up (e.g. collar tie -> 2-on-1 -> re-tie / angle creation) creates mechanical leverage.\n"
            "3. **Tactical Vulnerabilities & Follow-Up Chain**: Identify openings for snatch single, ankle pick, front headlock, or back-take based on the measured 3D angles."
        )

    def _probe_endpoint(self, base_url: str, timeout: float = 2.5) -> Optional[str]:
        try:
            with urllib.request.urlopen(f"{base_url}/models", timeout=timeout) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    models = data.get("data") or data.get("models") or []
                    if models and isinstance(models, list):
                        first = models[0]
                        return str(first.get("id") or first.get("name") or "default")
        except Exception:
            pass
        return None

    def analyze_tactics(
        self,
        frames_base64: List[str],
        kinematic_data: Dict[str, Any],
        video_title: str = "",
        model_name: str = "qwen2.5-vl-32b",
    ) -> Dict[str, Any]:
        """
        Execute 2-Stage TB4 3D VLA Grounding + Biomechanical Tactical Synthesis.
        Returns a structured dict containing visual_grounding, tactical_synthesis, and authentic model provenance.
        """
        t0 = time.perf_counter()

        # Compact kinematic digest for prompt efficiency
        compact_kinematics = {
            "video_title": video_title or kinematic_data.get("video_file", "unknown"),
            "duration_sec": kinematic_data.get("duration_sec"),
            "fps": kinematic_data.get("fps"),
            "total_frames": kinematic_data.get("total_frames"),
            "frames_with_3d_pose": kinematic_data.get("frames_with_3d_pose"),
            "frames_with_two_grapplers": kinematic_data.get("frames_with_two_grapplers"),
            "coordinate_system": kinematic_data.get("coordinate_system"),
            "keyframes": kinematic_data.get("keyframe_3d_kinematics", [])[:4],
        }
        kinematic_json_str = json.dumps(compact_kinematics, indent=2)

        # Stage 1: Multimodal 3D Visual Grounding on Qwen2.5-VL (TB4 L1b :8090 / :8092)
        visual_grounding = None
        vla_model_used = None
        vla_endpoint_used = None

        for ep_url, ep_desc in self.VL_ENDPOINTS:
            loaded_model_id = self._probe_endpoint(ep_url)
            if not loaded_model_id:
                continue
            try:
                client = OpenAI(base_url=ep_url, api_key=self.api_key, timeout=90.0)
                # Send 2 representative keyframes (start/entry + mid-transition) to keep CPU/Metal vision encoding fast
                sampled_imgs = frames_base64[:2] if len(frames_base64) <= 2 else [frames_base64[0], frames_base64[len(frames_base64) // 2]]
                user_content: List[Dict[str, Any]] = [
                    {
                        "type": "text",
                        "text": (
                            f"Video: {video_title}\n"
                            f"3D World Landmarks & Joint Angles Summary:\n```json\n{kinematic_json_str}\n```\n"
                            "Analyze the attached keyframes and 3D world coordinates. Describe the athletes' stances, "
                            "collar-tie / 2-on-1 hand fighting grips, and spatial angle changes."
                        ),
                    }
                ]
                for b64 in sampled_imgs:
                    user_content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                    })

                resp = client.chat.completions.create(
                    model=loaded_model_id,
                    messages=[
                        {"role": "system", "content": self.vla_system_prompt},
                        {"role": "user", "content": user_content},
                    ],
                    temperature=0.3,
                    max_tokens=450,
                )
                visual_grounding = resp.choices[0].message.content
                vla_model_used = os.path.basename(loaded_model_id)
                vla_endpoint_used = f"{ep_url} ({ep_desc})"
                break
            except Exception as e:
                visual_grounding = f"[VLA Stage 1 Warning on {ep_url}: {e}]"

        # Stage 2: Deep Biomechanical & Tactical Breakdown
        tactical_report = None
        reasoning_model_used = None
        reasoning_endpoint_used = None

        for ep_url, ep_desc in self.REASONING_ENDPOINTS:
            loaded_model_id = self._probe_endpoint(ep_url)
            if not loaded_model_id:
                continue
            try:
                client = OpenAI(base_url=ep_url, api_key=self.api_key, timeout=90.0)
                prompt_text = (
                    f"### Grappling Sequence Metadata\n"
                    f"- **Video Title**: {video_title}\n"
                    f"- **Stage 1 Qwen2.5-VL Visual Grounding ({vla_model_used or 'N/A'})**:\n"
                    f"{visual_grounding or 'No visual grounding available.'}\n\n"
                    f"### MediaPipe 3D World Landmarks (meters) & 3D Joint Angles (degrees)\n"
                    f"```json\n{kinematic_json_str}\n```\n\n"
                    f"Produce a rigorous 3D Biomechanical & Tactical Grappling Analysis based on these exact measurements."
                )
                resp = client.chat.completions.create(
                    model=loaded_model_id,
                    messages=[
                        {"role": "system", "content": self.tactical_system_prompt},
                        {"role": "user", "content": prompt_text},
                    ],
                    temperature=0.35,
                    max_tokens=900,
                )
                tactical_report = resp.choices[0].message.content
                reasoning_model_used = os.path.basename(loaded_model_id)
                reasoning_endpoint_used = f"{ep_url} ({ep_desc})"
                break
            except Exception:
                continue

        elapsed_sec = round(time.perf_counter() - t0, 2)
        return {
            "vla_model_used": vla_model_used,
            "vla_endpoint_used": vla_endpoint_used,
            "visual_grounding": visual_grounding,
            "reasoning_model_used": reasoning_model_used,
            "reasoning_endpoint_used": reasoning_endpoint_used,
            "tactical_report": tactical_report,
            "elapsed_sec": elapsed_sec,
        }
