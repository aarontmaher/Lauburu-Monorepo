import re
with open("tui/services/inference_bridges/julien_bridge.py", "r") as f:
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
        
        api_key = os.getenv("JULIEN_API_KEY")
        cf_account = os.getenv("CLOUDFLARE_ACCOUNT_ID")
        cf_gateway = os.getenv("CLOUDFLARE_GATEWAY_ID")
        
        if not api_key:
            yield "SYSTEM: To use Julien Ultra Plan, please type /key_julien <your_api_key>.\\n"
            self._is_generating = False
            return
            
        try:
            import httpx
            import json
            
            # Assuming Julien is an OpenAI compatible endpoint
            if cf_account and cf_gateway:
                base_url = f"https://gateway.ai.cloudflare.com/v1/{cf_account}/{cf_gateway}/openai"
            else:
                base_url = "https://api.julien.ai/v1" # Mock fallback
                
            url = f"{base_url}/chat/completions"
            
            payload = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "stream": True
            }
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient() as client:
                async with client.stream("POST", url, json=payload, headers=headers) as response:
                    if response.status_code != 200:
                        yield f"\\n[red]Julien API Error: {response.status_code} - {await response.aread()}[/red]"
                        self._is_generating = False
                        return
                        
                    async for line in response.aiter_lines():
                        if self._generation_cancelled:
                            break
                        if line.startswith("data: ") and line != "data: [DONE]":
                            try:
                                data = json.loads(line[6:])
                                choices = data.get("choices", [])
                                if choices and "delta" in choices[0] and "content" in choices[0]["delta"]:
                                    yield choices[0]["delta"]["content"]
                            except Exception:
                                pass
                
        except Exception as e:
            yield f"\\n[red]Julien API Error: {str(e)}[/red]"
            
        self.latency_ms = (time.perf_counter() - t0) * 1000.0
        self._is_generating = False
"""

content = re.sub(
    r"\n    async def stream_generate\([\s\S]*?self\._is_generating = False\n",
    replacement,
    content
)

with open("tui/services/inference_bridges/julien_bridge.py", "w") as f:
    f.write(content)
