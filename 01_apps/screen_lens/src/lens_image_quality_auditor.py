import os
import sys
import json
import base64
import urllib.request
import urllib.error
from typing import Dict, Any

def query_local_vision(img_path: str) -> Dict[str, Any]:
    try:
        with open(img_path, "rb") as f:
            b64_img = base64.b64encode(f.read()).decode('utf-8')
        
        payload = {
            "model": "Qwen2.5-VL-7B-Instruct-Q4_K_M",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Describe this image in one sentence. Is it a completely black or blank screen?"},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_img}"}}
                    ]
                }
            ],
            "max_tokens": 50,
            "temperature": 0.0
        }
        req = urllib.request.Request("http://127.0.0.1:8081/v1/chat/completions", data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
        
        proxy_handler = urllib.request.ProxyHandler({})
        opener = urllib.request.build_opener(proxy_handler)
        
        with opener.open(req, timeout=30) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return {"status": "success", "response": data["choices"][0]["message"]["content"]}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def query_gemini_vision(img_path: str, api_key: str) -> Dict[str, Any]:
    try:
        with open(img_path, "rb") as f:
            b64_img = base64.b64encode(f.read()).decode('utf-8')
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": "Is this image a completely black or blank screen? Describe what you see briefly."},
                        {"inlineData": {"mimeType": "image/png", "data": b64_img}}
                    ]
                }
            ]
        }
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
        proxy_handler = urllib.request.ProxyHandler({})
        opener = urllib.request.build_opener(proxy_handler)
        
        with opener.open(req, timeout=30) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return {"status": "success", "response": text}
    except urllib.error.HTTPError as e:
        return {"status": "error", "message": f"HTTP {e.code}: {e.read().decode('utf-8')}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def audit_image(img_path: str):
    print(f"Auditing image: {img_path}")
    
    print("\n--- Shadowing with Local Vision AI (Qwen-VL on :8081) ---")
    local_resp = query_local_vision(img_path)
    print(json.dumps(local_resp, indent=2))
    
    print("\n--- Shadowing with Cloud Gemini 3.8 Flash (Simulated with 1.5 Flash) ---")
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print({"status": "error", "message": "GEMINI_API_KEY not set in environment."})
    else:
        gemini_resp = query_gemini_vision(img_path, api_key)
        print(json.dumps(gemini_resp, indent=2))

if __name__ == "__main__":
    if len(sys.argv) > 1:
        img_path = sys.argv[1]
    else:
        img_path = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/test_artifacts/s20_screen_lens_optimized.png"
    
    audit_image(img_path)
