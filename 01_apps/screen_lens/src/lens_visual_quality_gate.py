import os
import sys
import json
import base64
import urllib.request
import urllib.error
import ssl
from typing import Dict, Any

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

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
        
        with opener.open(req, timeout=10) as resp:
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
                        {"text": "Is this image a completely black or blank screen? Describe what you see briefly. End with EXACTLY 'IS_BLACK: YES' or 'IS_BLACK: NO'."},
                        {"inlineData": {"mimeType": "image/png", "data": b64_img}}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.0,
            }
        }
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
        
        proxy_handler = urllib.request.ProxyHandler({})
        opener = urllib.request.build_opener(proxy_handler, urllib.request.HTTPSHandler(context=ssl_ctx))
        
        with opener.open(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return {"status": "success", "response": text, "is_black": "IS_BLACK: YES" in text}
    except urllib.error.HTTPError as e:
        return {"status": "error", "message": f"HTTP {e.code}: {e.read().decode('utf-8')}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def audit_image_quality(img_path: str) -> bool:
    print(f"Auditing image for quality: {img_path}")
    
    print("\n--- Shadowing with Local Vision AI (Qwen-VL on :8081) ---")
    local_resp = query_local_vision(img_path)
    print(json.dumps(local_resp, indent=2))
    
    print("\n--- Shadowing with Cloud Gemini 3.8 Flash ---")
    api_key = os.environ.get("GEMINI_API_KEY")
    is_valid = True
    
    if not api_key:
        print("Warning: GEMINI_API_KEY not set. Cannot run Cloud Shadowing.")
    else:
        gemini_resp = query_gemini_vision(img_path, api_key)
        print(json.dumps(gemini_resp, indent=2))
        
        if gemini_resp.get("status") == "success":
            if gemini_resp.get("is_black"):
                print("❌ Image Audit FAILED. Gemini detected a black/blank screen.")
                is_valid = False
            else:
                print("✅ Image Audit PASSED. Image contains valid data.")
        else:
            print("❌ Image Audit FAILED. Gemini API request failed, refusing to trust image.")
            is_valid = False
            
    report_path = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault/APPS_AND_FEATURES/SCREEN_LENS_IMAGE_AUDIT_LOG.md"
    try:
        with open(report_path, "a") as f:
            f.write(f"\n### Visual Audit: {os.path.basename(img_path)}\n")
            f.write(f"- **Local Vision (Qwen-VL)**: {local_resp.get('status')} - {local_resp.get('response', local_resp.get('message'))}\n")
            if api_key:
                f.write(f"- **Gemini 3.8 Flash**: {gemini_resp.get('status')} - {gemini_resp.get('response', gemini_resp.get('message'))}\n")
            f.write(f"- **Verdict**: {'Valid' if is_valid else 'Rejected (Black Screen or Validation Failed)'}\n")
    except Exception as e:
        print(f"Failed to write to Obsidian vault: {e}")
        
    return is_valid

if __name__ == "__main__":
    if len(sys.argv) > 1:
        img_path = sys.argv[1]
    else:
        img_path = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/test_artifacts/s20_screen_lens_optimized.png"
    
    is_valid = audit_image_quality(img_path)
    if not is_valid:
        sys.exit(1)
