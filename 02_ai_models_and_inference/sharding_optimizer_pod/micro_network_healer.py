import os
import sys
import time
import json
import subprocess
import asyncio
from typing import Dict, Any

try:
    from llama_cpp import Llama
except ImportError:
    Llama = None

class MicroNetworkHealer:
    def __init__(self, model_path: str = "/home/linuxmini/model_vault_gguf/SmolLM2-360M-Instruct-Q8_0.gguf"):
        self.model_path = model_path
        self.llm = None
        if Llama:
            try:
                self.llm = Llama(model_path=self.model_path, n_ctx=2048, verbose=False)
                print(f"[MicroNetworkHealer] Successfully loaded {model_path}")
            except Exception as e:
                print(f"[MicroNetworkHealer] Failed to load model: {e}")
        else:
            print("[MicroNetworkHealer] llama_cpp not installed. Running in mock/dry-run mode for evaluation.")

    def gather_telemetry(self) -> Dict[str, Any]:
        """Gathers local network telemetry (ping, interfaces, routes)."""
        telemetry = {}
        
        # 1. Gather interface stats
        try:
            # We assume iproute2 is available
            ip_link = subprocess.check_output(["ip", "-s", "link"], text=True)
            telemetry["ip_link"] = ip_link[:1000] # truncate for context
        except Exception:
            telemetry["ip_link"] = "N/A"

        # 2. Gather routing table
        try:
            ip_route = subprocess.check_output(["ip", "route"], text=True)
            telemetry["ip_route"] = ip_route
        except Exception:
            telemetry["ip_route"] = "N/A"

        # 3. Simple ping to GW
        try:
            ping_gw = subprocess.check_output(["ping", "-c", "1", "-W", "1", "100.90.8.1"], text=True)
            telemetry["ping_gw_status"] = "OK"
        except subprocess.CalledProcessError:
            telemetry["ping_gw_status"] = "FAIL"

        return telemetry

    def analyze_health(self, telemetry: Dict[str, Any]) -> str:
        """Prompts the MicroLM to analyze the telemetry."""
        if not self.llm:
            return "NO_ACTION"
        
        prompt = f"""<|im_start|>system
You are the Network Healer MicroLM. Analyze the following network telemetry and determine if any interface resets or route adjustments are needed. Output only JSON containing {{"action": "...", "interface": "..."}} or {{"action": "NONE"}}.<|im_end|>
<|im_start|>user
Telemetry:
{json.dumps(telemetry)}
<|im_end|>
<|im_start|>assistant
"""
        response = self.llm(prompt, max_tokens=64, stop=["<|im_end|>"])
        text = response["choices"][0]["text"].strip()
        return text

    async def continuous_healing_loop(self):
        print("[MicroNetworkHealer] Starting continuous healing loop...")
        while True:
            telemetry = self.gather_telemetry()
            decision = self.analyze_health(telemetry)
            print(f"[MicroNetworkHealer] Telemetry snapshot. LM Decision: {decision}")
            await asyncio.sleep(15)

if __name__ == "__main__":
    healer = MicroNetworkHealer()
    asyncio.run(healer.continuous_healing_loop())
