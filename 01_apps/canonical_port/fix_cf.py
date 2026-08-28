import re
with open("tui/services/inference_bridges/cloudflare_bridge.py", "r") as f:
    content = f.read()

replacement = """
    async def stream_generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> AsyncGenerator[str, None]:
        
        self._is_generating = True
        t0 = time.perf_counter()
        
        api_key = os.getenv("CLOUDFLARE_API_KEY")
        account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")
        gateway_id = os.getenv("CLOUDFLARE_GATEWAY_ID")
        
        if not api_key or not account_id:
            yield "SYSTEM: To use Cloudflare Workers AI, please type /key_cf <your_api_key> and /account_cf <account_id>.\\n"
            self._is_generating = False
            return
            
        try:
            import httpx
            import json
            
            if gateway_id:
                base_url = f"https://gateway.ai.cloudflare.com/v1/{account_id}/{gateway_id}/workers-ai"
            else:
                base_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run"
                
            url = f"{base_url}/{self.model_name}"
            
            payload = {
                "messages": [{"role": "user", "content": prompt}],
                "stream": True
            }
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient() as client:
                async with client.stream("POST", url, json=payload, headers=headers) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if self._generation_cancelled:
                            break
                        if line.startswith("data: ") and line != "data: [DONE]":
                            try:
                                data = json.loads(line[6:])
                                if "response" in data:
                                    yield data["response"]
                            except Exception:
                                pass
                
        except Exception as e:
            yield f"\\n[red]Cloudflare API Error: {str(e)}[/red]"
            
        self.latency_ms = (time.perf_counter() - t0) * 1000.0
        self._is_generating = False
"""

content = re.sub(
    r"\n    async def stream_generate\([\s\S]*?self\._is_generating = False\n",
    replacement,
    content
)

with open("tui/services/inference_bridges/cloudflare_bridge.py", "w") as f:
    f.write(content)
