import requests
import time
import sys
import os

SERVER_URL = "http://127.0.0.1:4003"
TEST_NODE = "l7_samsung"
ARTIFACTS_DIR = "/Users/aaron/.gemini/antigravity/brain/7b3e82a1-19b0-4226-9058-a888fd5aea67"

def print_step(msg):
    print(f"\n[+] {msg}")

def check_status(res, step_name):
    if res.status_code not in [200, 202]:
        print(f"Failed at {step_name}: {res.status_code} - {res.text}")
        sys.exit(1)

def run_test():
    print_step("Step 1: Arming Control Gate")
    res = requests.post(f"{SERVER_URL}/api/arm", json={"armed": True})
    check_status(res, "Arm Control Gate")
    print("Control gate ARMED:", res.json())
    
    print_step(f"Step 2: Fetching Initial Frame from {TEST_NODE}")
    res = requests.get(f"{SERVER_URL}/api/node/{TEST_NODE}/frame")
    check_status(res, "Fetch Initial Frame")
    
    before_img_path = os.path.join(ARTIFACTS_DIR, f"{TEST_NODE}_vla_before.jpg")
    with open(before_img_path, "wb") as f:
        f.write(res.content)
    print(f"Saved initial frame: {before_img_path}")
    
    print_step("Step 3: Waking up device (Home Key)")
    res = requests.post(f"{SERVER_URL}/api/hid/key", json={"node": TEST_NODE, "key": "home"})
    check_status(res, "Wake Device")
    time.sleep(1.5)
    
    print_step("Step 4: Simulating VLA Coordinate Selection & Actuation (Swipe to unlock)")
    # Let's send a swipe to unlock
    swipe_payload = {
        "node": TEST_NODE,
        "x1": 500,
        "y1": 1500,
        "x2": 500,
        "y2": 500,
        "duration": 300
    }
    res = requests.post(f"{SERVER_URL}/api/hid/swipe", json=swipe_payload)
    check_status(res, "Swipe")
    print("Actuation successful:", res.json())
    
    print_step("Step 5: Waiting for visual state change")
    time.sleep(3.0)
    
    print_step(f"Step 6: Fetching Post-Actuation Frame from {TEST_NODE}")
    res = requests.get(f"{SERVER_URL}/api/node/{TEST_NODE}/frame")
    check_status(res, "Fetch Post-Actuation Frame")
        
    after_img_path = os.path.join(ARTIFACTS_DIR, f"{TEST_NODE}_vla_after.jpg")
    with open(after_img_path, "wb") as f:
        f.write(res.content)
    print(f"Saved post-actuation frame: {after_img_path}")
    
    # We also disarm it
    print_step("Step 7: Disarming Control Gate")
    res = requests.post(f"{SERVER_URL}/api/arm", json={"armed": False})
    check_status(res, "Disarm")
    print("Control gate DISARMED:", res.json())
    
    print_step("VLA INTEGRATION TEST PASSED SUCCESSFULLY")
    sys.exit(0)

if __name__ == "__main__":
    run_test()
