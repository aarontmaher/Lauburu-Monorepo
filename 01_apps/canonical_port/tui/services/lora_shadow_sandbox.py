import os
import json
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

class LoRAShadowSandbox:
    """
    Background worker that intercepts complex tool calls made by Gemini/Cloud,
    prompts the local Qwen model to attempt the same call, and records the diff
    into the `lora_datasets` directory for continuous distillation.
    """
    def __init__(self, dataset_dir: str = "/Users/aaron/DFS_UNIFIED/lora_datasets"):
        self.dataset_dir = Path(dataset_dir)
        os.makedirs(self.dataset_dir, exist_ok=True)
        self.dataset_file = self.dataset_dir / "continuous_lora_dataset.jsonl"
        
    async def process_shadow_task(self, prompt: str, cloud_response_json: Dict[str, Any]):
        """
        Runs asynchronously so it never blocks the primary TUI thread.
        """
        logging.info(f"[LoRA Sandbox] Initiating shadow run for prompt: {prompt[:30]}...")
        
        # 1. Ask Qwen locally how it would solve the prompt
        qwen_attempt = await self._query_qwen_local(prompt)
        
        # 2. Extract the actual tool JSON the cloud model used successfully
        cloud_tool_call = cloud_response_json.get("tool_calls", [])
        
        # 3. Format as a ShareGPT / OpenAI LoRA JSONL entry
        lora_entry = {
            "timestamp": datetime.now().isoformat(),
            "messages": [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": json.dumps(cloud_tool_call)}
            ],
            "metadata": {
                "qwen_failed_attempt": qwen_attempt,
                "reward_score": 1.0 # Cloud output is the gold standard
            }
        }
        
        # 4. Append to dataset
        try:
            with open(self.dataset_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(lora_entry) + "\n")
            logging.info("[LoRA Sandbox] Distillation pair crystallized to dataset.")
        except Exception as e:
            logging.error(f"[LoRA Sandbox] Failed to write dataset: {e}")

    async def _query_qwen_local(self, prompt: str) -> str:
        """Mock querying the local inference endpoint for the shadow code."""
        # In reality, this would hit http://127.0.0.1:8082
        await asyncio.sleep(0.5)
        return "{\n  \"action\": \"mock_qwen_tool_attempt\"\n}"
