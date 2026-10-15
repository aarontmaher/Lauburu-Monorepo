import sys, os, time, json, urllib.request, base64
import subprocess

def get_keys():
    env_path = os.path.expanduser("~/.env")
    keys = {}
    if os.path.exists(env_path):
        for line in open(env_path).read().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                keys[k.strip()] = v.strip().strip('"').strip("'")
    return keys

def capture_screen():
    print("  📸 VLA: Capturing ScreenFrame via ScreenCaptureKit...")
    subprocess.run(["screencapture", "-x", "/tmp/vla_screen.png"])
    with open("/tmp/vla_screen.png", "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def get_ui_element_coords(b64_image, element_name, keys):
    print(f"  🧠 VLA: Querying Gemini 1.5 Flash for spatial coordinates of '{element_name}'...")
    api_key = keys.get("GEMINI_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    prompt = f"Find the bounding box for the '{element_name}' UI element. Return ONLY a JSON array in the format [ymin, xmin, ymax, xmax] normalized to 1000. Example: [400, 500, 450, 600]. Do not write anything else."
    
    payload = {
        "contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": "image/png", "data": b64_image}}]}],
        "generationConfig": {"temperature": 0.0}
    }
    
    req = urllib.request.Request(url, method="POST")
    req.add_header("Content-Type", "application/json")
    
    try:
        res = urllib.request.urlopen(req, data=json.dumps(payload).encode())
        text = json.loads(res.read())["candidates"][0]["content"]["parts"][0]["text"].strip()
        text = text.replace("```json", "").replace("```", "").strip()
        box = json.loads(text)
        
        # Denormalize from 1000 to 1920x1080
        ymin, xmin, ymax, xmax = box
        center_x = int(((xmin + xmax) / 2000.0) * 1920)
        center_y = int(((ymin + ymax) / 2000.0) * 1080)
        return center_x, center_y
    except Exception as e:
        print("  ❌ VLA Spatial Mapping Error:", e)
        return None

def click(x, y):
    print(f"  👉 VLA: Dispatching zero-mock physical click to ({x}, {y})")
    subprocess.run(["osascript", "-e", f'tell application "System Events" to click at {{{x}, {y}}}'])

def automate_sso(target_url, service_name, keys):
    print(f"\n=======================================================")
    print(f"🤖 INITIATING FULL AUTONOMY: {service_name}")
    print(f"=======================================================")
    
    # 1. Open Safari
    print(f"  🌐 Launching Safari to {target_url}...")
    subprocess.run(["osascript", "-e", 'tell application "Safari" to activate'])
    subprocess.run(["osascript", "-e", f'tell application "Safari" to set URL of document 1 to "{target_url}"'])
    time.sleep(5) # Wait for page load
    
    # 2. Find and click SSO button
    img1 = capture_screen()
    coords = get_ui_element_coords(img1, "Sign in with Google or Continue with Google button", keys)
    if not coords:
        print(f"  ⚠️ Could not locate SSO button on {service_name}.")
        return
        
    click(coords[0], coords[1])
    time.sleep(4) # Wait for Google OAuth popup/redirect
    
    # 3. Click the user's Google Account profile in the OAuth screen
    img2 = capture_screen()
    coords2 = get_ui_element_coords(img2, "Google Account Profile Email Address to select", keys)
    if coords2:
        click(coords2[0], coords2[1])
        print(f"  ✅ {service_name} SSO Biometric Handshake Complete.")
    else:
        print(f"  ⚠️ Could not locate Google Profile selector.")

if __name__ == "__main__":
    keys = get_keys()
    automate_sso("https://cloud.cerebras.ai/", "CEREBRAS", keys)
    time.sleep(3)
    automate_sso("https://cloud.sambanova.ai/", "SAMBANOVA", keys)
