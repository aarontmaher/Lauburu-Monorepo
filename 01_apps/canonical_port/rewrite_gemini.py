import re
with open("tui/services/inference_bridges/gemini_bridge.py", "r") as f:
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
        
        api_key = os.getenv("GEMINI_API_KEY")
        cf_account = os.getenv("CLOUDFLARE_ACCOUNT_ID")
        cf_gateway = os.getenv("CLOUDFLARE_GATEWAY_ID")
        
        if not api_key:
            yield "SYSTEM: To enable real interactive chat, please export GEMINI_API_KEY in your terminal before launching, or type /key <your_key>.\\n"
            self._is_generating = False
            return
            
        try:
            import json
            import httpx
            
            if cf_account and cf_gateway:
                base_url = f"https://gateway.ai.cloudflare.com/v1/{cf_account}/{cf_gateway}/google-ai-studio/v1beta/models"
            else:
                base_url = "https://generativelanguage.googleapis.com/v1beta/models"
                
            url = f"{base_url}/{self.model_name}:streamGenerateContent?key={api_key}"
            
            payload = {
                "contents": [{"parts": [{"text": prompt}]}]
            }
            
            async with httpx.AsyncClient() as client:
                async with client.stream("POST", url, json=payload, headers={"Content-Type": "application/json"}) as response:
                    response.raise_for_status()
                    async for chunk in response.aiter_text():
                        if self._generation_cancelled:
                            break
                        # Very basic JSON chunk parser for Gemini stream
                        try:
                            # The stream sends array elements or SSE, Gemini REST sends chunks of JSON
                            if '"text": "' in chunk:
                                parts = chunk.split('"text": "')
                                for p in parts[1:]:
                                    text_val = p.split('"')[0]
                                    # unescape basic newlines
                                    text_val = text_val.replace('\\\\n', '\\n').replace('\\\\"', '"')
                                    yield text_val
                        except Exception:
                            pass
                            
        except Exception as e:
            yield f"\\n[red]Gemini/Cloudflare Gateway API Error: {str(e)}[/red]"
            
        self.latency_ms = (time.perf_counter() - t0) * 1000.0
        self._is_generating = False
"""

content = re.sub(
    r"\n    async def stream_generate\([\s\S]*?self\._is_generating = False\n",
    replacement,
    content
)

with open("tui/services/inference_bridges/gemini_bridge.py", "w") as f:
    f.write(content)
