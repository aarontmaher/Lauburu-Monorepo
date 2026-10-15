#!/usr/bin/env bash
# ==============================================================================
# Android Auto Desktop Head Unit (DHU) Forwarding & Emulation Launcher
# Enables instant in-car head unit testing on macOS without physical car
# ==============================================================================

set -euo pipefail

CLR_RESET="\033[0m"
CLR_BOLD="\033[1m"
CLR_GREEN="\033[32m"
CLR_YELLOW="\033[33m"
CLR_BLUE="\033[34m"
CLR_CYAN="\033[36m"

echo -e "${CLR_BOLD}================================================================================${CLR_RESET}"
echo -e "${CLR_BOLD}   ANDROID AUTO DESKTOP HEAD UNIT (DHU) LAUNCHER & PORT FORWARDER               ${CLR_RESET}"
echo -e "${CLR_BOLD}================================================================================${CLR_RESET}"

# 1. Resolve ADB Target Device
TARGET_DEVICE="${1:-$(adb devices | grep -v "List of devices" | grep "device$" | head -n 1 | awk '{print $1}')}"

if [ -z "$TARGET_DEVICE" ]; then
    echo -e "${CLR_YELLOW}No active ADB device detected. Attempting connection to 100.84.40.95:5555...${CLR_RESET}"
    adb connect 100.84.40.95:5555 2>/dev/null || true
    TARGET_DEVICE="100.84.40.95:5555"
fi

echo -e "  • Target Device: ${CLR_CYAN}$TARGET_DEVICE${CLR_RESET}"

# 2. Port Forward DHU Port 5277
echo -e "${CLR_BLUE}[1/3] Forwarding DHU TCP Port 5277 over ADB...${CLR_RESET}"
adb -s "$TARGET_DEVICE" forward tcp:5277 tcp:5277
echo -e "${CLR_GREEN}✓ Port 5277 forwarded successfully (tcp:5277 -> tcp:5277)${CLR_RESET}"

# 3. Start Head Unit Server on Android Device
echo -e "${CLR_BLUE}[2/3] Triggering Android Auto Head Unit Server on device...${CLR_RESET}"
adb -s "$TARGET_DEVICE" shell am start -n com.google.android.projection.gearhead/.companion.settings.DeveloperSettingsActivity 2>/dev/null || true
echo -e "${CLR_GREEN}✓ Developer settings triggered${CLR_RESET}"

# 4. Check for DHU binary
echo -e "${CLR_BLUE}[3/3] Checking Desktop Head Unit (DHU) binary...${CLR_RESET}"
DHU_PATH="/Users/aaron/Library/Android/sdk/extras/google/auto/desktop-head-unit"
if [ -x "$DHU_PATH" ]; then
    echo -e "${CLR_GREEN}✓ Launching DHU: $DHU_PATH${CLR_RESET}"
    "$DHU_PATH" &
else
    echo -e "${CLR_YELLOW}Notice: DHU binary not found at $DHU_PATH.${CLR_RESET}"
    echo -e "To install DHU locally run: ${CLR_CYAN}sdkmanager \"extras;google;auto\"${CLR_RESET}"
    echo -e "Port forwarding is active on ${CLR_CYAN}localhost:5277${CLR_RESET} ready for any DHU or emulator connection."
fi

echo -e "\n${CLR_BOLD}${CLR_GREEN}DHU Forwarding & Automotive Gateway Ready!${CLR_RESET}"
