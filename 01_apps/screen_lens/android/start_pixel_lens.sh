#!/usr/bin/env bash
# ==============================================================================
# Pixel 10 Pro XL - 24/7 Activity-Driven Screen Lens Launch & Watchdog
# ==============================================================================

set -euo pipefail

TARGET_HOST="pixel"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

echo "🚀 Deploying 24/7 Activity-Driven Screen Lens to Pixel 10 Pro XL..."

# 1. Sync updated daemon to Pixel
ssh "$TARGET_HOST" "mkdir -p ~/lauburu_lens ~/.lauburu/frames"
scp "$PROJECT_ROOT/01_apps/screen_lens/android/lauburu_lens_android.py" "$TARGET_HOST:~/lauburu_lens/lauburu_lens_android.py"
ssh "$TARGET_HOST" "chmod +x ~/lauburu_lens/lauburu_lens_android.py"

# 2. Acquire Termux Wake-Lock to prevent CPU sleep
ssh "$TARGET_HOST" "termux-wake-lock 2>/dev/null || true"

# 3. Stop existing daemon if running
ssh "$TARGET_HOST" "python3 ~/lauburu_lens/lauburu_lens_android.py stop 2>/dev/null || true"
ssh "$TARGET_HOST" "pkill -f 'lauburu_lens_android.py' 2>/dev/null || true"

# 4. Launch daemon in background with nohup
ssh "$TARGET_HOST" "nohup python3 ~/lauburu_lens/lauburu_lens_android.py start > ~/.lauburu/lens_daemon.log 2>&1 &"
sleep 1.5

# 5. Verify live status
echo "📊 Verifying Pixel Screen Lens status..."
ssh "$TARGET_HOST" "python3 ~/lauburu_lens/lauburu_lens_android.py status"

echo "✅ Pixel 10 Pro XL 24/7 Screen Lens Daemon Active!"
