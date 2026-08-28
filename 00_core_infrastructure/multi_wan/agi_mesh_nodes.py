"""
multi_wan/agi_mesh_nodes.py - Multi-Device AGI Node Manager with Self-Healing Fallback & HF Downloader.

Configures named AGI nodes:
1. 'nano'    (Pixel) : Gemma 4 26B (Stored on Pixel Device) -> Fallback: gemma:2b
2. 'linux'   (Linux) : DeepSeek-R1 32B (Stored on 2.6TB NAS) -> Fallback: deepseek-r1:8b (Local NVMe)
3. 'lauburu' (Mac)   : Lauburu Unified AGI (Stored on 2.6TB NAS) -> Fallback: qwen2.5-coder:7b
4. 'apple'   (iPhone): Qwen 2.5 Coder 7B (Stored on NAS/Local) -> Fallback: qwen2.5:1.5b
"""

import os
import sys
import json
import time
import socket
import logging
import datetime
import subprocess
import urllib.request
import urllib.error
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any

logger = logging.getLogger("multi_wan.agi_mesh_nodes")


@dataclass
class AGINodeConfig:
    node_id: str
    name: str
    device_type: str
    ip_address: str
    primary_model: str
    hf_repo_id: Optional[str]
    model_storage_path: str  # 'NAS' or 'PIXEL_DEVICE' or 'LOCAL_NVME'
    fallback_model: str
    is_online: bool = False
    active_model: str = ""
    last_health_check: str = ""
    reconnection_attempts: int = 0


class SelfHealingMeshRouter:
    """
    Manages named AGI nodes (nano, linux, lauburu, apple), enforces NAS storage rules,
    downloads strongest models via huggingface-cli using HF_TOKEN, and handles offline fallback + self-healing.
    """

    def __init__(self, nas_root: str = "/Volumes/NAS"):
        self.nas_root = nas_root
        self.nas_models_dir = os.path.join(nas_root, "ollama_models")

        # Define 4 Named Nodes per User Specs with Strongest Device-Optimized Fallbacks
        self.nodes: Dict[str, AGINodeConfig] = {
            "nano": AGINodeConfig(
                node_id="pixel_node",
                name="nano",
                device_type="Google Pixel (16GB RAM)",
                ip_address="100.73.38.87",
                primary_model="gemma2:27b",
                hf_repo_id="bartowski/gemma-2-27b-it-GGUF",
                model_storage_path="PIXEL_DEVICE",
                fallback_model="gemma:2b"
            ),
            "linux": AGINodeConfig(
                node_id="linux_gpu_node",
                name="linux",
                device_type="Linux GPU PC (24GB VRAM)",
                ip_address="192.168.8.116",
                primary_model="deepseek-r1:32b",
                hf_repo_id="deepseek-ai/DeepSeek-R1-Distill-Qwen-32B-GGUF",
                model_storage_path="NAS",
                fallback_model="deepseek-r1:14b"  # Upgraded from 8B -> 14B (Maxes local NVMe VRAM)
            ),
            "lauburu": AGINodeConfig(
                node_id="mac_host_node",
                name="lauburu",
                device_type="Apple M4 Mac (16GB RAM)",
                ip_address="127.0.0.1",
                primary_model="lauburu-unified-agi:latest",
                hf_repo_id=None,
                model_storage_path="NAS",
                fallback_model="deepseek-r1:14b"  # Upgraded from 7B -> 14B (Maxes M4 16GB RAM)
            ),
            "apple": AGINodeConfig(
                node_id="iphone_node",
                name="apple",
                device_type="iPhone (8GB RAM)",
                ip_address="100.96.71.81",
                primary_model="qwen2.5-coder:7b",
                hf_repo_id="Qwen/Qwen2.5-Coder-7B-Instruct-GGUF",
                model_storage_path="NAS",
                fallback_model="qwen2.5-coder:3b"  # Upgraded from 1.5B -> 3B (Maxes 8GB iPhone RAM)
            )
        }

    def check_node_connectivity(self, node_name: str) -> bool:
        """Pings and tests socket/HTTP connectivity for a named node."""
        node = self.nodes.get(node_name)
        if not node:
            return False

        if node.ip_address in ("127.0.0.1", "localhost"):
            node.is_online = True
            node.active_model = node.primary_model
            return True

        # Socket ping check on SSH (port 22) or HTTP (port 8888/11434/8080)
        ports_to_try = [22, 11434, 8888, 8750, 8080]
        for port in ports_to_try:
            try:
                with socket.create_connection((node.ip_address, port), timeout=1.5):
                    node.is_online = True
                    node.active_model = node.primary_model
                    node.last_health_check = datetime.datetime.utcnow().isoformat() + "Z"
                    node.reconnection_attempts = 0
                    return True
            except (socket.timeout, ConnectionRefusedError, OSError):
                continue

        # If unreachable, trigger self-healing fallback
        node.is_online = False
        node.active_model = node.fallback_model
        node.reconnection_attempts += 1
        node.last_health_check = datetime.datetime.utcnow().isoformat() + "Z"
        return False

    def download_strongest_hf_model(self, node_name: str, hf_token: Optional[str] = None) -> bool:
        """
        Downloads strongest GGUF model via huggingface-cli using HF_TOKEN onto the NAS (or Pixel).
        """
        node = self.nodes.get(node_name)
        if not node or not node.hf_repo_id:
            logger.warning(f"No Hugging Face repo ID for node {node_name}")
            return False

        token = hf_token or os.getenv("HF_TOKEN")
        if not token:
            logger.warning("HF_TOKEN environment variable not found. Set HF_TOKEN to download gated models.")

        # Determine target download directory per NAS storage rule
        if node.model_storage_path == "NAS":
            target_dir = os.path.join(self.nas_models_dir, node.name)
        else:
            target_dir = f"/tmp/hf_downloads_{node.name}"

        os.makedirs(target_dir, exist_ok=True)

        env = os.environ.copy()
        if token:
            env["HF_TOKEN"] = token

        cmd = [
            "huggingface-cli", "download",
            node.hf_repo_id,
            "--local-dir", target_dir,
            "--local-dir-use-symlinks", "False"
        ]

        try:
            logger.info(f"Downloading HF model '{node.hf_repo_id}' to '{target_dir}' for node '{node_name}'...")
            subprocess.run(cmd, env=env, check=True, timeout=300)
            logger.info(f"✓ HF model download successful for node {node_name}")
            return True
        except Exception as e:
            logger.error(f"HF download failed for node {node_name}: {e}")
            return False

    def run_self_healing_routine(self) -> Dict[str, Any]:
        """
        Runs self-healing reconnection loop across all 4 named nodes.
        Attempts NAS remount and socket reconnects if offline.
        """
        status_report = {}

        # 1. Verify NAS mount integrity
        nas_active = os.path.ismount(self.nas_root) or os.path.exists(self.nas_models_dir)
        if not nas_active:
            logger.warning("NAS mount unverified! Attempting self-healing SMB remount...")
            try:
                subprocess.run(["mount", "-a"], timeout=5)
            except Exception:
                pass

        # 2. Audit each node
        for name, node in self.nodes.items():
            online = self.check_node_connectivity(name)

            if not online:
                logger.warning(f"Node '{name}' offline! Active model switched to fallback '{node.fallback_model}'.")
            
            status_report[name] = {
                "name": node.name,
                "device": node.device_type,
                "ip": node.ip_address,
                "is_online": node.is_online,
                "active_model": node.active_model,
                "primary_model": node.primary_model,
                "fallback_model": node.fallback_model,
                "model_storage": node.model_storage_path,
                "reconnection_attempts": node.reconnection_attempts
            }

        return status_report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    router = SelfHealingMeshRouter()
    print("=" * 70)
    print("MULTI-DEVICE AGI MESH NODES & SELF-HEALING ROUTER")
    print("=" * 70)
    report = router.run_self_healing_routine()
    print(json.dumps(report, indent=2))
