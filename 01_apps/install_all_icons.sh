#!/bin/bash
ICON_PATH="/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/core/docs/store-assets/google-play/app-icon-512.png"
DEVICE="100.73.38.87:5555"

APPS=(
  "commerce_and_business/lauburu_business_app"
  "edge_compute_and_ai/openclaw/openclaw_app"
  "edge_compute_and_ai/lauburu_compute_hub"
  "port_4000_flutter_rust"
  "bluetooth_terminal_ide"
)

for app in "${APPS[@]}"; do
  cd "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/$app"
  
  # Replace icons
  sips -z 48 48 "$ICON_PATH" --out android/app/src/main/res/mipmap-mdpi/ic_launcher.png > /dev/null 2>&1
  sips -z 72 72 "$ICON_PATH" --out android/app/src/main/res/mipmap-hdpi/ic_launcher.png > /dev/null 2>&1
  sips -z 96 96 "$ICON_PATH" --out android/app/src/main/res/mipmap-xhdpi/ic_launcher.png > /dev/null 2>&1
  sips -z 144 144 "$ICON_PATH" --out android/app/src/main/res/mipmap-xxhdpi/ic_launcher.png > /dev/null 2>&1
  sips -z 192 192 "$ICON_PATH" --out android/app/src/main/res/mipmap-xxxhdpi/ic_launcher.png > /dev/null 2>&1
  
  # Build and install
  flutter build apk --release
  adb -s "$DEVICE" install -r build/app/outputs/flutter-apk/app-release.apk
done
