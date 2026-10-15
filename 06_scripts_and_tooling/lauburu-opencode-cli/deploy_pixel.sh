#!/bin/bash
set -e
echo "🚀 Compiling Lauburu Mesh CLI for Android Edge (Pixel 10 Pro XL) via Termux..."

export CGO_ENABLED=0
export GOOS=android
export GOARCH=arm64

go build -buildmode=pie -buildvcs=false -o lauburu_android ./cmd/lauburu

echo "✅ Compilation successful: lauburu_android"

echo "📡 Pushing to Pixel 10 Pro XL (Termux layer)..."
# Assuming ADB is connected via Tailscale IP or USB
adb push lauburu_android /data/local/tmp/
adb shell "su -c 'mv /data/local/tmp/lauburu_android /data/data/com.termux/files/home/ && chmod +x /data/data/com.termux/files/home/lauburu_android'"

echo "🔥 End-to-End Edge Node Deployment Complete! Execute ./lauburu_android on the Pixel."
