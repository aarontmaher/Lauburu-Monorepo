#!/bin/bash
# ---------------------------------------------------------------------------
# Lauburu Life Companion Universal Bootstrap
# Automatically installs and integrates the Life Companion ecosystem on macOS or Android/Linux
# ---------------------------------------------------------------------------

echo "🌌 Initializing Lauburu Life Companion Bootstrap..."

# 1. Determine OS Environment
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macOS"
    CONFIG_DIR="$HOME/.lauburu"
elif [ -n "$PREFIX" ] && [[ "$PREFIX" == *"com.termux"* ]]; then
    OS="Termux"
    CONFIG_DIR="$HOME/.lauburu"
else
    OS="Linux"
    CONFIG_DIR="$HOME/.lauburu"
fi
echo "✅ Detected Environment: $OS"

# 2. Setup Configuration Structure
mkdir -p "$CONFIG_DIR"
if [ ! -f "$CONFIG_DIR/config.json" ]; then
    echo "⚙️ Creating default config.json..."
    cat << 'CONF' > "$CONFIG_DIR/config.json"
{
    "user_profile": "general",
    "automation_threshold_roi": 90,
    "privacy": {
        "ignore_apps": [],
        "blur_faces": false
    },
    "custom_tracking_goals": [],
    "theme": "cyberpunk"
}
CONF
fi

# 3. Setup Python Virtual Environment (Optional, assuming system Python for now)
echo "🐍 Verifying Python dependencies..."
pip3 install -q httpx flask psutil python-dotenv

# 4. OS-Specific Native Auto-Start
if [ "$OS" == "macOS" ]; then
    echo "🍏 Setting up macOS LaunchAgent for 24/7 background persistence..."
    PLIST_PATH="$HOME/Library/LaunchAgents/com.lauburu.screenlifecompanion.plist"
    cat << 'PLIST' > "$PLIST_PATH"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.lauburu.screenlifecompanion</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/screen_lens/screen_life_companion/screen_life_daemon.sh</string>
        <string>start</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
PLIST
    launchctl load "$PLIST_PATH" 2>/dev/null || true
    echo "✅ LaunchAgent Installed."
elif [ "$OS" == "Termux" ]; then
    echo "📱 Setting up Termux Wake-Lock and Boot Script..."
    mkdir -p ~/.termux/boot
    cat << 'BOOT' > ~/.termux/boot/start_life_companion.sh
#!/data/data/com.termux/files/usr/bin/bash
termux-wake-lock
bash ~/DFS_UNIFIED/Lauburu-Monorepo/01_apps/screen_lens/screen_life_companion/screen_life_daemon.sh start
BOOT
    chmod +x ~/.termux/boot/start_life_companion.sh
    echo "✅ Termux Boot Script Installed."
fi

# 5. Start the Services
echo "🚀 Starting Life Companion Services..."
bash "$(dirname "$0")/screen_life_companion/screen_life_daemon.sh" restart

echo "================================================================="
echo "🎉 Life Companion Successfully Bootstrapped!"
echo "🌐 Dashboard & Settings available at: http://127.0.0.1:3036"
echo "================================================================="
