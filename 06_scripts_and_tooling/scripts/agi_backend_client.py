import json
import logging
from typing import Dict, Any, List, Optional
import httpx

logger = logging.getLogger("agi_backend_client")

class AGIBackendClient:
    """
    Python SDK Client for interacting with the Local AGI Backend Hub (Port 8900).
    Provides methods for tool discovery, Guther/Merger code intelligence, Tailscale CLI, GL.iNet CLI, Google SDK,
    Python/C++ sandbox code execution, Speech STT/TTS, Computer Use, Phone ADB Use, Docker MCP, Anti Metal MCP,
    Docker AI, Hugging Face SDK/CLI & Agent Skills, llama.cpp GGUF execution, Gemini API generation,
    Gemini Spark swarm & Spark Network Workers dispatching, Gemini Notebook generation, memory context sync,
    telemetry, and rule enforcement.
    """

    def __init__(self, base_url: str = "http://localhost:8900", timeout: float = 15.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def check_health(self) -> Dict[str, Any]:
        """Check status of Local AGI Backend Hub."""
        with httpx.Client(timeout=self.timeout) as client:
            res = client.get(f"{self.base_url}/health")
            return res.json()

    # --- 1. Guther & Merger Methods ---
    def guther_scan(self, target_dir: str = "/app", file_extensions: Optional[List[str]] = None) -> Dict[str, Any]:
        """Gather repository intelligence, ASTs, and file manifests."""
        payload = {"target_dir": target_dir, "file_extensions": file_extensions}
        with httpx.Client(timeout=self.timeout) as client:
            res = client.post(f"{self.base_url}/api/tools/guther/scan", json=payload)
            return res.json()

    def merger_patch(self, target_file: str, patch_content: str) -> Dict[str, Any]:
        """Merge code diff patch into target file."""
        payload = {"target_file": target_file, "patch_content": patch_content}
        with httpx.Client(timeout=self.timeout) as client:
            res = client.post(f"{self.base_url}/api/tools/merger/patch", json=payload)
            return res.json()

    # --- 2. Tailscale & GL.iNet Network Methods ---
    def tailscale_status(self) -> Dict[str, Any]:
        """Fetch Tailscale CLI mesh status."""
        with httpx.Client(timeout=self.timeout) as client:
            res = client.get(f"{self.base_url}/api/network/tailscale/status")
            return res.json()

    def glinet_status(self, router_ip: str = "192.168.8.1") -> Dict[str, Any]:
        """Fetch GL.iNet router status."""
        payload = {"router_ip": router_ip}
        with httpx.Client(timeout=self.timeout) as client:
            res = client.post(f"{self.base_url}/api/network/glinet/status", json=payload)
            return res.json()

    # --- 3. Google SDK Methods ---
    def google_sdk_status(self) -> Dict[str, Any]:
        """Fetch Google Cloud SDK and gcloud status."""
        with httpx.Client(timeout=self.timeout) as client:
            res = client.get(f"{self.base_url}/api/google/status")
            return res.json()

    # --- 4. Python & C++ Code Execution Methods ---
    def execute_python_code(self, code: str, timeout: float = 10.0) -> Dict[str, Any]:
        """Execute a Python code snippet in backend sandbox."""
        payload = {"code": code, "timeout": timeout}
        with httpx.Client(timeout=self.timeout) as client:
            res = client.post(f"{self.base_url}/api/code/python/execute", json=payload)
            return res.json()

    def compile_run_cpp(self, code: str, compiler: str = "g++", std_version: str = "c++20", flags: Optional[List[str]] = None) -> Dict[str, Any]:
        """Compile and run C++ code snippet."""
        payload = {"code": code, "compiler": compiler, "std_version": std_version, "flags": flags or []}
        with httpx.Client(timeout=self.timeout) as client:
            res = client.post(f"{self.base_url}/api/code/cpp/compile-run", json=payload)
            return res.json()

    # --- 5. Speech STT & TTS Methods ---
    def synthesize_tts(self, text: str, language: str = "en", output_format: str = "mp3") -> Dict[str, Any]:
        """Synthesize text into speech audio."""
        payload = {"text": text, "language": language, "format": output_format}
        with httpx.Client(timeout=self.timeout) as client:
            res = client.post(f"{self.base_url}/api/speech/tts", json=payload)
            return res.json()

    # --- 6. Computer & Phone Use Skills Methods ---
    def computer_screenshot(self) -> Dict[str, Any]:
        """Capture desktop screenshot."""
        with httpx.Client(timeout=self.timeout) as client:
            res = client.get(f"{self.base_url}/api/computer_use/screenshot")
            return res.json()

    def phone_list_devices(self) -> Dict[str, Any]:
        """List Android ADB devices."""
        with httpx.Client(timeout=self.timeout) as client:
            res = client.get(f"{self.base_url}/api/phone/devices")
            return res.json()

    # --- 7. Spark Worker Nodes Methods ---
    def list_spark_nodes(self) -> Dict[str, Any]:
        """List active Spark network worker nodes."""
        with httpx.Client(timeout=self.timeout) as client:
            res = client.get(f"{self.base_url}/api/spark/nodes/list")
            return res.json()

    def register_spark_node(self, node_id: str, ip_address: str, port: int = 8901, capabilities: Optional[List[str]] = None) -> Dict[str, Any]:
        """Register a new Spark network worker node."""
        payload = {"node_id": node_id, "ip_address": ip_address, "port": port, "capabilities": capabilities or []}
        with httpx.Client(timeout=self.timeout) as client:
            res = client.post(f"{self.base_url}/api/spark/nodes/register", json=payload)
            return res.json()

    def get_gemma_cluster_status(self) -> Dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as client:
            res = client.get(f"{self.base_url}/api/cluster/gemma/status")
            return res.json()

    def get_gemma_cluster_launch_config(self, model_path: str = "./models/gemma-2-27b-it.Q4_K_M.gguf") -> Dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as client:
            res = client.post(f"{self.base_url}/api/cluster/gemma/launch_config", json={"model_path": model_path})
            return res.json()

    def get_github_status(self) -> Dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as client:
            res = client.get(f"{self.base_url}/api/github/status")
            return res.json()

    def get_k8s_status(self) -> Dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as client:
            res = client.get(f"{self.base_url}/api/k8s/status")
            return res.json()

    def get_nano_topology(self) -> Dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as client:
            res = client.get(f"{self.base_url}/api/nano/topology")
            return res.json()

    def execute_polyglot_code(self, language: str, code: str) -> Dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as client:
            res = client.post(f"{self.base_url}/api/code/polyglot/execute", json={"language": language, "code": code})
            return res.json()

    def get_terminal_expert_status(self) -> Dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as client:
            res = client.get(f"{self.base_url}/api/terminal/expert/status")
            return res.json()

    def get_ollama_status(self) -> Dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as client:
            res = client.get(f"{self.base_url}/api/ollama/status")
            return res.json()

    # --- Training Games & Edge Gallery Methods ---
    def list_training_games(self) -> Dict[str, Any]:
        """List available AI training games."""
        with httpx.Client(timeout=self.timeout) as client:
            res = client.get(f"{self.base_url}/api/training_games/list")
            return res.json()

    def start_training_game(self, game_id: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Start a new AI training game session."""
        payload = {"game_id": game_id, "config": config or {}}
        with httpx.Client(timeout=self.timeout) as client:
            res = client.post(f"{self.base_url}/api/training_games/start", json=payload)
            return res.json()

    def step_training_game(self, session_id: str, action: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a turn or step in an active AI training game."""
        payload = {"session_id": session_id, "action": action, "params": params or {}}
        with httpx.Client(timeout=self.timeout) as client:
            res = client.post(f"{self.base_url}/api/training_games/step", json=payload)
            return res.json()

    def get_training_game_session(self, session_id: str) -> Dict[str, Any]:
        """Fetch active training game session state."""
        with httpx.Client(timeout=self.timeout) as client:
            res = client.get(f"{self.base_url}/api/training_games/session/{session_id}")
            return res.json()

    def list_edge_gallery_skills(self) -> Dict[str, Any]:
        """List all 11 Google AI Edge Gallery skills."""
        with httpx.Client(timeout=self.timeout) as client:
            res = client.get(f"{self.base_url}/api/edge_gallery/skills")
            return res.json()

    def execute_edge_gallery_skill(self, skill_name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute an Edge Gallery skill."""
        payload = {"skill_name": skill_name, "arguments": arguments or {}}
        with httpx.Client(timeout=self.timeout) as client:
            res = client.post(f"{self.base_url}/api/edge_gallery/skill/execute", json=payload)
            return res.json()

    # --- 8. Samsung Multi-Transport & Network Health AI Methods ---
    def samsung_status(self, lan_ip: str = "192.168.8.150") -> Dict[str, Any]:
        """Probe Samsung Multi-Transport status."""
        with httpx.Client(timeout=self.timeout) as client:
            res = client.get(f"{self.base_url}/api/samsung/status", params={"lan_ip": lan_ip})
            return res.json()

    def samsung_stay_awake(self, lan_ip: str = "192.168.8.150", rpc_port: int = 50052, adb_port: int = 38607) -> Dict[str, Any]:
        """Configure Samsung Stay Awake and ADB keepalive."""
        payload = {"lan_ip": lan_ip, "rpc_port": rpc_port, "adb_port": adb_port}
        with httpx.Client(timeout=self.timeout) as client:
            res = client.post(f"{self.base_url}/api/samsung/stay_awake", json=payload)
            return res.json()

    def network_ai_health(self) -> Dict[str, Any]:
        """Run Network Health AI remediation audit."""
        with httpx.Client(timeout=self.timeout) as client:
            res = client.get(f"{self.base_url}/api/network/ai/health")
            return res.json()

    def network_ai_iphones(self) -> Dict[str, Any]:
        """Audit Tailscale mesh and iPhone network devices."""
        with httpx.Client(timeout=self.timeout) as client:
            res = client.get(f"{self.base_url}/api/network/ai/iphones")
            return res.json()

    def network_ai_tmux_rebuild(self, session_name: str = "agi_rpc_worker", command: str = "rpc-server -H 0.0.0.0 -p 50052") -> Dict[str, Any]:
        """Rebuild or manage tmux RPC worker session."""
        with httpx.Client(timeout=self.timeout) as client:
            res = client.post(f"{self.base_url}/api/network/ai/tmux/rebuild", params={"session_name": session_name, "command": command})
            return res.json()

    # --- 9. Hybrid Local AI + Antigravity Orchestrator Methods ---
    def hybrid_dispatch(self, prompt: str, min_quality_bar: str = "medium", model_preference: Optional[str] = None) -> Dict[str, Any]:
        """Dispatch task dynamically between Local AI and Antigravity Agent."""
        payload = {"prompt": prompt, "min_quality_bar": min_quality_bar, "model_preference": model_preference}
        with httpx.Client(timeout=self.timeout) as client:
            res = client.post(f"{self.base_url}/api/hybrid/dispatch", json=payload)
            return res.json()

    def list_specialized_ais(self) -> Dict[str, Any]:
        """List all 8 specialized NAS Ollama models and their domain roles."""
        with httpx.Client(timeout=self.timeout) as client:
            res = client.get(f"{self.base_url}/api/specialized_ais/list")
            return res.json()

    def get_device_agi_status(self) -> Dict[str, Any]:
        """Fetch status of all 4 Device AGIs (lauburu, linux, nano, apple)."""
        with httpx.Client(timeout=self.timeout) as client:
            res = client.get(f"{self.base_url}/api/device_agi/status")
            return res.json()

    def device_agi_self_heal(self, target_agi: Optional[str] = None) -> Dict[str, Any]:
        """Trigger automated self-healing network reconnection for device AGIs."""
        params = {"target_agi": target_agi} if target_agi else {}
        with httpx.Client(timeout=self.timeout) as client:
            res = client.post(f"{self.base_url}/api/device_agi/self_heal", params=params)
            return res.json()

    def device_agi_idle_train(self) -> Dict[str, Any]:
        """Check system compute load and trigger idle Rule 0 training iteration."""
        with httpx.Client(timeout=self.timeout) as client:
            res = client.post(f"{self.base_url}/api/device_agi/idle_train")
            return res.json()

    def download_hf_model_to_nas(self, repo_id: str, filename: str) -> Dict[str, Any]:
        """Download model via HF CLI directly to NAS (/Volumes/NAS/models) to consume 0 Bytes Mac storage."""
        payload = {"repo_id": repo_id, "filename": filename}
        with httpx.Client(timeout=600.0) as client:
            res = client.post(f"{self.base_url}/api/device_agi/download_hf", json=payload)
            return res.json()




if __name__ == "__main__":
    print("=== AGI Backend Client Full Platform Test ===")
    client = AGIBackendClient()
    try:
        health = client.check_health()
        print(f"Health Check: {json.dumps(health, indent=2)}")
        ollama_status = client.get_ollama_status()
        print(f"Ollama Master Status: {json.dumps(ollama_status, indent=2)}")
        samsung = client.samsung_status()
        print(f"Samsung Status: {json.dumps(samsung, indent=2)}")
        net_ai = client.network_ai_health()
        print(f"Network AI Health: {json.dumps(net_ai, indent=2)}")
        print("=== SDK Client Verified Successfully ===")
    except Exception as e:
        print(f"Connection test failed: {e}")







