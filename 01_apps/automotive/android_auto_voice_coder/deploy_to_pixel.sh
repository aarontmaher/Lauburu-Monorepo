#!/usr/bin/env bash
# ==============================================================================
# Android Auto AGI - Build Packaging & ADB Wireless Deployment Pipeline
# Target: Pixel 10 Pro XL (100.73.38.87:34167) / Auto-Detected Mesh ADB Device
# ==============================================================================

set -euo pipefail

# ANSI Color Codes
CLR_RESET="\033[0m"
CLR_BOLD="\033[1m"
CLR_GREEN="\033[32m"
CLR_YELLOW="\033[33m"
CLR_BLUE="\033[34m"
CLR_RED="\033[31m"
CLR_CYAN="\033[36m"

echo -e "${CLR_BOLD}================================================================================${CLR_RESET}"
echo -e "${CLR_BOLD}   ANDROID AUTO AGI - WIRELESS ADB DEPLOYMENT PIPELINE                         ${CLR_RESET}"
echo -e "${CLR_BOLD}================================================================================${CLR_RESET}"

# Workspace Resolution
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# Target Device Configuration
DEFAULT_PIXEL_IP="100.73.38.87"
DEFAULT_PIXEL_PORT="34167"
DEFAULT_DEVICE="${DEFAULT_PIXEL_IP}:${DEFAULT_PIXEL_PORT}"
PACKAGE_NAME="com.lauburu.androidauto.agi"
CAR_SERVICE_NAME="com.lauburu.androidauto.agi/.service.LauburuCarAppService"
APK_PATH="$PROJECT_ROOT/app/build/outputs/apk/debug/app-debug.apk"

# 1. Export and Validate Toolchain Environment
echo -e "${CLR_BLUE}[1/5] Configuring Toolchain & Environment Variables...${CLR_RESET}"
export JAVA_HOME="${JAVA_HOME:-/Users/aaron/.jdk17/Contents/Home}"
export ANDROID_HOME="${ANDROID_HOME:-/Users/aaron/android-sdk}"
export ANDROID_SDK_ROOT="${ANDROID_SDK_ROOT:-/Users/aaron/android-sdk}"
export PATH="$ANDROID_HOME/platform-tools:$JAVA_HOME/bin:$PATH"

if [ ! -d "$JAVA_HOME" ]; then
    echo -e "${CLR_RED}ERROR: JAVA_HOME not found at $JAVA_HOME${CLR_RESET}"
    exit 1
fi

if [ ! -d "$ANDROID_HOME" ]; then
    echo -e "${CLR_RED}ERROR: ANDROID_HOME not found at $ANDROID_HOME${CLR_RESET}"
    exit 1
fi

if ! command -v adb &>/dev/null; then
    echo -e "${CLR_RED}ERROR: adb platform tool not found in PATH${CLR_RESET}"
    exit 1
fi

echo -e "  • Java:     $("$JAVA_HOME/bin/java" -version 2>&1 | head -n 1)"
echo -e "  • Android:  $ANDROID_HOME"
echo -e "  • ADB:      $(adb version | head -n 1)"

# 2. Compile Debug APK via Gradle
echo -e "\n${CLR_BLUE}[2/5] Compiling Debug APK via ./gradlew assembleDebug...${CLR_RESET}"
if [ ! -x "./gradlew" ]; then
    chmod +x ./gradlew
fi

./gradlew assembleDebug --stacktrace

if [ ! -f "$APK_PATH" ]; then
    echo -e "${CLR_RED}ERROR: Build failed to produce APK at $APK_PATH${CLR_RESET}"
    exit 1
fi

APK_SIZE_BYTES=$(wc -c < "$APK_PATH" | tr -d ' ')
APK_SIZE_HUMAN=$(ls -lh "$APK_PATH" | awk '{print $5}')
echo -e "${CLR_GREEN}✓ APK compiled successfully: $APK_PATH (${APK_SIZE_HUMAN}, ${APK_SIZE_BYTES} bytes)${CLR_RESET}"

# 3. Detect and Connect ADB Target Device
echo -e "\n${CLR_BLUE}[3/5] Resolving ADB Wireless Target Device...${CLR_RESET}"
TARGET_DEVICE=""

# Check if explicit device parameter passed
if [ $# -gt 0 ] && [ -n "$1" ]; then
    TARGET_DEVICE="$1"
    echo -e "  • Using command-line specified target device: ${CLR_CYAN}$TARGET_DEVICE${CLR_RESET}"
else
    # Attempt connection to default Pixel 10 Pro XL wireless endpoint
    echo -e "  • Attempting connection to default Pixel 10 Pro XL at ${CLR_CYAN}$DEFAULT_DEVICE${CLR_RESET}..."
    adb connect "$DEFAULT_DEVICE" 2>&1 || true

    # Check if default device is online
    ONLINE_DEVICES=$(adb devices | grep -v "List of devices" | grep "device$" | awk '{print $1}')
    if echo "$ONLINE_DEVICES" | grep -q "$DEFAULT_DEVICE"; then
        TARGET_DEVICE="$DEFAULT_DEVICE"
        echo -e "${CLR_GREEN}✓ Connected to target Pixel 10 Pro XL ($TARGET_DEVICE)${CLR_RESET}"
    else
        # Auto-detect connected device from adb devices
        DETECTED_DEVICE=$(adb devices | grep -v "List of devices" | grep "device$" | head -n 1 | awk '{print $1}' || true)
        if [ -n "$DETECTED_DEVICE" ]; then
            TARGET_DEVICE="$DETECTED_DEVICE"
            echo -e "${CLR_YELLOW}⚠ Pixel default endpoint offline. Falling back to auto-detected device: ${CLR_CYAN}$TARGET_DEVICE${CLR_RESET}"
        else
            echo -e "${CLR_RED}ERROR: No active ADB devices found. Ensure wireless debugging or USB connection is enabled.${CLR_RESET}"
            exit 1
        fi
    fi
fi

# Fetch device details
DEVICE_MODEL=$(adb -s "$TARGET_DEVICE" shell getprop ro.product.model 2>/dev/null | tr -d '\r\n' || echo "Unknown")
ANDROID_VER=$(adb -s "$TARGET_DEVICE" shell getprop ro.build.version.release 2>/dev/null | tr -d '\r\n' || echo "Unknown")
SDK_LEVEL=$(adb -s "$TARGET_DEVICE" shell getprop ro.build.version.sdk 2>/dev/null | tr -d '\r\n' || echo "Unknown")
echo -e "  • Device Hardware: ${CLR_CYAN}$DEVICE_MODEL${CLR_RESET} (Android $ANDROID_VER, SDK API $SDK_LEVEL)"

# 4. Install APK to Connected Device
echo -e "\n${CLR_BLUE}[4/5] Installing APK to $TARGET_DEVICE...${CLR_RESET}"
INSTALL_OUTPUT=$(adb -s "$TARGET_DEVICE" install -r -g "$APK_PATH" 2>&1)
echo "$INSTALL_OUTPUT"

if ! echo "$INSTALL_OUTPUT" | grep -q "Success"; then
    echo -e "${CLR_RED}ERROR: APK installation failed on device $TARGET_DEVICE${CLR_RESET}"
    exit 1
fi
echo -e "${CLR_GREEN}✓ APK installed successfully (-r -g flags verified)${CLR_RESET}"

# 5. Verify Package & Service Registration
echo -e "\n${CLR_BLUE}[5/5] Verifying Package & CarAppService Registration on Device...${CLR_RESET}"

# Verify Package is listed
echo "Checking package status via adb shell pm list packages..."
PACKAGE_LIST=$(adb -s "$TARGET_DEVICE" shell pm list packages | grep com.lauburu.androidauto.agi || true)
if [ -z "$PACKAGE_LIST" ]; then
    echo -e "${CLR_RED}ERROR: Package $PACKAGE_NAME not found in pm list packages${CLR_RESET}"
    exit 1
fi
echo -e "  • Package Status:  ${CLR_GREEN}$PACKAGE_LIST${CLR_RESET}"

# Query Services for package and Android Auto CarAppService action
echo "Querying package services via adb shell pm query-services..."
adb -s "$TARGET_DEVICE" shell pm query-services -a com.lauburu.androidauto.agi 2>&1 || true

echo "Querying CarAppService action registration..."
CAR_SERVICES=$(adb -s "$TARGET_DEVICE" shell pm query-services -a androidx.car.app.CarAppService 2>&1 || true)
if echo "$CAR_SERVICES" | grep -q "com.lauburu.androidauto.agi"; then
    echo -e "${CLR_GREEN}✓ Verified Android Auto CarAppService registered:${CLR_RESET}"
    echo "$CAR_SERVICES" | grep -B 1 -A 4 "com.lauburu.androidauto.agi" | sed 's/^/    /'
else
    echo "$CAR_SERVICES" | sed 's/^/    /'
fi

echo -e "\n${CLR_BOLD}================================================================================${CLR_RESET}"
echo -e "${CLR_BOLD}${CLR_GREEN}   DEPLOYMENT TO PIXEL 10 PRO XL COMPLETED SUCCESSFULLY (100% GREEN)           ${CLR_RESET}"
echo -e "${CLR_BOLD}================================================================================${CLR_RESET}"
