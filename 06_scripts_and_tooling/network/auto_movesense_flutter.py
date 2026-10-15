import subprocess
import time

def adb_shell(cmd):
    full_cmd = f"ssh -F /dev/null -o StrictHostKeyChecking=no -p 8022 u0_a234@100.114.215.68 \"rish -c '{cmd}'\""
    return subprocess.run(full_cmd, shell=True, capture_output=True, text=True)

print("Starting automation of Movesense Terminal...")
# Launch app
adb_shell("am start -n com.lauburu.movesense_terminal_flutter/.MainActivity")
time.sleep(2)

print("Tapping Disconnect TCP (just in case)...")
adb_shell("input tap 815 639")
time.sleep(1)

print("Entering AVF IP...")
adb_shell("input tap 415 496")
time.sleep(0.5)

# Move to end
adb_shell("input keyevent KEYCODE_MOVE_END")
# Delete 20 times
for _ in range(20):
    adb_shell("input keyevent 67")
# Type new IP
adb_shell("input text '10.86.187.34'")
time.sleep(1)

print("Entering Port 8086...")
adb_shell("input tap 897 496")
time.sleep(0.5)
adb_shell("input keyevent KEYCODE_MOVE_END")
for _ in range(10):
    adb_shell("input keyevent 67")
adb_shell("input text '8086'")
time.sleep(1)

print("Tapping Connect TCP...")
adb_shell("input tap 815 639")
time.sleep(2)

print("Tapping Scan & Connect for Movesense...")
adb_shell("input tap 341 1010")

print("Automation complete.")
