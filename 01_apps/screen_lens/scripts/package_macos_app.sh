#!/usr/bin/env bash
# ==============================================================================
# package_macos_app.sh — Screen Lens Lauburu
# Packages native Swift 6 OCR daemon, Python companion daemons, and orchestrator
# into a standalone macOS Application Bundle (Screen Lens Lauburu.app) and DMG.
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LENS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BUILD_DIR="${LENS_DIR}/build_staging"
APP_BUNDLE="${LENS_DIR}/Screen Lens Lauburu.app"
DMG_OUTPUT="${LENS_DIR}/Screen_Lens_Lauburu.dmg"
PORTFOLIO_BUILDS="/Users/aaron/teamwork_projects/app_production_and_sellability/builds"

echo "========================================================================"
echo "📦 Packaging Screen Lens Lauburu for macOS"
echo "========================================================================"

# 1. Compile native Swift daemon
echo "🔨 Compiling native Swift OCR daemon..."
bash "${LENS_DIR}/build.sh"

# 2. Recreate clean bundle directory structure
echo "📁 Staging macOS Application Bundle..."
rm -rf "${APP_BUNDLE}"
mkdir -p "${APP_BUNDLE}/Contents/MacOS"
mkdir -p "${APP_BUNDLE}/Contents/Resources/screen_life_companion"
mkdir -p "${APP_BUNDLE}/Contents/Resources/src"

# 3. Create Info.plist
cat << 'EOF' > "${APP_BUNDLE}/Contents/Info.plist"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>en</string>
    <key>CFBundleExecutable</key>
    <string>Screen Lens Lauburu</string>
    <key>CFBundleIdentifier</key>
    <string>ai.lauburu.screenlens</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>Screen Lens Lauburu</string>
    <key>CFBundleDisplayName</key>
    <string>Screen Lens Lauburu</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    <key>CFBundleVersion</key>
    <string>1</string>
    <key>LSMinimumSystemVersion</key>
    <string>14.0</string>
    <key>LSUIElement</key>
    <true/>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSScreenCaptureUsageDescription</key>
    <string>Screen Lens Lauburu requires screen capture access to analyze on-screen content and provide local multimodal assistance.</string>
    <key>NSAccessibilityUsageDescription</key>
    <string>Screen Lens Lauburu requires accessibility permissions to inspect UI elements and provide zero-lock actuation.</string>
</dict>
</plist>
EOF

# 4. Copy Swift executable into MacOS
cp "${LENS_DIR}/bin/lauburu-lens" "${APP_BUNDLE}/Contents/MacOS/lauburu-lens"
chmod +x "${APP_BUNDLE}/Contents/MacOS/lauburu-lens"

# 5. Copy Python companion services into Resources
cp -R "${LENS_DIR}/screen_life_companion/"* "${APP_BUNDLE}/Contents/Resources/screen_life_companion/" 2>/dev/null || true
cp -R "${LENS_DIR}/src/"* "${APP_BUNDLE}/Contents/Resources/src/" 2>/dev/null || true

# 6. Create main executable launcher
cat << 'EOF' > "${APP_BUNDLE}/Contents/MacOS/Screen Lens Lauburu"
#!/usr/bin/env bash
set -euo pipefail

BUNDLE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MACOS_DIR="${BUNDLE_DIR}/MacOS"
RESOURCES_DIR="${BUNDLE_DIR}/Resources"
LOG_DIR="${HOME}/Library/Logs/ScreenLensLauburu"
mkdir -p "${LOG_DIR}"

echo "Starting Screen Lens Lauburu..."

SWIFT_PID=""
COMPANION_PID=""
ORCH_PID=""

cleanup() {
    echo "Stopping Screen Lens Lauburu services..."
    [ -n "$SWIFT_PID" ] && kill -TERM "$SWIFT_PID" 2>/dev/null || true
    [ -n "$COMPANION_PID" ] && kill -TERM "$COMPANION_PID" 2>/dev/null || true
    [ -n "$ORCH_PID" ] && kill -TERM "$ORCH_PID" 2>/dev/null || true
    wait 2>/dev/null || true
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# 1. Start Swift OCR daemon (:3035)
"${MACOS_DIR}/lauburu-lens" start --port 3035 --interval 2.0 --mode fast --foreground > "${LOG_DIR}/ocr_3035.log" 2>&1 &
SWIFT_PID=$!

# 2. Start Screen Life Companion (:3036)
if [ -f "${RESOURCES_DIR}/screen_life_companion/screen_life_companion.py" ]; then
    python3 "${RESOURCES_DIR}/screen_life_companion/screen_life_companion.py" --daemon > "${LOG_DIR}/companion_3036.log" 2>&1 &
    COMPANION_PID=$!
fi

# 3. Start Global Orchestrator (:3037)
if [ -f "${RESOURCES_DIR}/src/lens_global_orchestrator.py" ]; then
    python3 "${RESOURCES_DIR}/src/lens_global_orchestrator.py" --port 3037 --daemon > "${LOG_DIR}/orchestrator_3037.log" 2>&1 &
    ORCH_PID=$!
fi

# Wait on children
wait
EOF
chmod +x "${APP_BUNDLE}/Contents/MacOS/Screen Lens Lauburu"

# 6b. Ad-hoc codesign app bundle
echo "✍️  Ad-hoc signing macOS app bundle..."
codesign -s - --force --deep "${APP_BUNDLE}"

# 7. Create DMG installer using hdiutil
echo "💿 Generating DMG installer..."
rm -f "${DMG_OUTPUT}"
rm -rf "${BUILD_DIR}"
mkdir -p "${BUILD_DIR}"
cp -R "${APP_BUNDLE}" "${BUILD_DIR}/"

hdiutil create -volname "Screen Lens Lauburu" \
    -srcfolder "${BUILD_DIR}" \
    -ov -format UDZO \
    "${DMG_OUTPUT}"

rm -rf "${BUILD_DIR}"

# 8. Stage to portfolio builds directory
if [ -d "${PORTFOLIO_BUILDS}" ]; then
    echo "🚚 Staging artifacts into ${PORTFOLIO_BUILDS}..."
    rm -rf "${PORTFOLIO_BUILDS}/Screen Lens Lauburu.app"
    cp -R "${APP_BUNDLE}" "${PORTFOLIO_BUILDS}/"
    cp "${DMG_OUTPUT}" "${PORTFOLIO_BUILDS}/"
fi

echo "✅ Successfully built and packaged Screen Lens Lauburu:"
echo "   - App Bundle: ${APP_BUNDLE}"
echo "   - DMG: ${DMG_OUTPUT}"
