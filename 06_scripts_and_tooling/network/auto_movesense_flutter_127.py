import subprocess
import time

def adb_shell(cmd):
    full_cmd = f"ssh -F /dev/null -o StrictHostKeyChecking=no -p 8022 u0_a234@100.114.215.68 \"rish -c '{cmd}'\""
    return subprocess.run(full_cmd, shell=True, capture_output=True, text=True)

print("Starting automation of Movesense Terminal...")
adb_shell("input tap 815 639")
time.sleep(1)

print("Entering AVF IP...")
adb_shell("input tap 415 496")
time.sleep(0.5)
adb_shell("input keyevent KEYCODE_MOVE_END")
for _ in range(20):
    adb_shell("input keyevent 67")
adb_shell("input text '127.0.0.1'")
time.sleep(1)

print("Entering Port 8080...")
adb_shell("input tap 897 496")
time.sleep(0.5)
adb_shell("input keyevent KEYCODE_MOVE_END")
for _ in range(10):
    adb_shell("input keyevent 67")
adb_shell("input text '8080'")
time.sleep(1)

print("Tapping Connect TCP...")
adb_shell("input tap 815 639")
time.sleep(2)
