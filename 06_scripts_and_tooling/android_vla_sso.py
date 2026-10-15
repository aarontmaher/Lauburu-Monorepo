import os, time, json, urllib.request, base64
import subprocess

DEVICE_IP = "100.78.206.96:5555"
SCREEN_W, SCREEN_H = 1080, 2400

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
    print("  📸 VLA [Android]: Capturing Frame via ADB screencap...")
    os.system(f"adb -s {DEVICE_IP} exec-out screencap -p > /tmp/s20.png")
    with open("/tmp/s20.png", "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def get_ui_coords(b64_image, element_name, keys):
    print(f"  🧠 VLA [Android]: Querying Gemini 1.5 Flash Vision for '{element_name}'...")
    api_key = keys.get("GEMINI_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    prompt = f"Find the bounding box for the '{element_name}' UI element. Return ONLY a JSON array [ymin, xmin, ymax, xmax] scaled to 1000. Do not write text."
    payload = {
        "contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": "image/png", "data": b64_image}}]}],
        "generationConfig": {"temperature": 0.0}
    }
    
    req = urllib.request.Request(url, method="POST", headers={"Content-Type": "application/json"})
    try:
        res = urllib.request.urlopen(req, data=json.dumps(payload).encode())
        text = json.loads(res.read())["candidates"][0]["content"]["parts"][0]["text"].strip()
        text = text.replace("```json", "").replace("```", "").strip()
        box = json.loads(text)
        ymin, xmin, ymax, xmax = box
        cx = int(((xmin + xmax) / 2000.0) * SCREEN_W)
        cy = int(((ymin + ymax) / 2000.0) * SCREEN_H)
        return cx, cy
    except Exception as e:
        print("  ❌ VLA Spatial Mapping Error:", e)
        return None

def click(x, y):
    print(f"  👉 VLA [Android]: Injecting physical touch event at ({x}, {y})")
    subprocess.run(["adb", "-s", DEVICE_IP, "shell", "input", "tap", str(x), str(y)])

def automate_sso(url, service_name, keys):
    print(f"\n=======================================================")
    print(f"🤖 ANDROID AUTONOMY INITIATED: {service_name}")
    print(f"=======================================================")
    
    # Unlock device if locked (Swipe up and input pin if needed, or just wake)
    subprocess.run(["adb", "-s", DEVICE_IP, "shell", "input", "keyevent", "KEYCODE_WAKEUP"])
    
    print(f"  🌐 Launching Chrome intent to {url}...")
    subprocess.run(["adb", "-s", DEVICE_IP, "shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", url])
    time.sleep(8) # Wait for page load
    
    img = capture_screen()
    coords = get_ui_coords(img, "Sign in with Google", keys)
    if coords:
        click(coords[0], coords[1])
        time.sleep(5) # Wait for OAuth
        print("  ✅ Clicked Google SSO. If multiple accounts, selecting first...")
        
        img2 = capture_screen()
        coords2 = get_ui_coords(img2, "Google Account Profile Email", keys)
        if coords2:
            click(coords2[0], coords2[1])
            print(f"  ✅ {service_name} Authenticated via Android Chrome!")
        else:
            print("  ⚠️ Could not find Google profile list. Possibly already logged in.")
            
if __name__ == "__main__":
    keys = get_keys()
    automate_sso("https://cloud.cerebras.ai/", "CEREBRAS", keys)
    time.sleep(3)
    automate_sso("https://cloud.sambanova.ai/", "SAMBANOVA", keys)
