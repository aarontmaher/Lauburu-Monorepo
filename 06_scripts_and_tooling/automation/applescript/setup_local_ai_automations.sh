#!/usr/bin/env bash
# ==============================================================================
# Setup & Compile Local AI Only AppleScript Automations
# Subsystem: 06_scripts_and_tooling/automation/applescript/setup_local_ai_automations.sh
# Lauburu Mesh Ecosystem — 2026
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="$HOME/Library/Scripts/Lauburu"
SERVICES_DIR="$HOME/Library/Services"

echo "⚡ [Lauburu AppleScript Installer] Initializing Local-AI-Only Automations..."
mkdir -p "$TARGET_DIR"

# 1. Compile AppleScripts to .scpt
for f in "$SCRIPT_DIR"/*.applescript; do
    [ -e "$f" ] || continue
    base="$(basename "$f" .applescript)"
    dest="$TARGET_DIR/${base}.scpt"
    echo "  🔨 Compiling $base.applescript -> $dest..."
    /usr/bin/osacompile -o "$dest" "$f"
done

# 2. Make bridge executable
chmod +x "$SCRIPT_DIR/local_ai_apple_bridge.py"
chmod +x "$SCRIPT_DIR/orchestrate_local_ai_applescript.py"

# 3. Create Convenience CLI Symlinks
CLI_BIN="$HOME/.local/bin"
mkdir -p "$CLI_BIN"
ln -sf "$SCRIPT_DIR/local_ai_apple_bridge.py" "$CLI_BIN/local-ai"

# 4. Enable macOS Script Menu Bar if desired
echo "  🍏 Enabling macOS Script Menu in Menu Bar..."
defaults write com.apple.scriptmenu ShowScriptMenu -bool true 2>/dev/null || true

echo "✅ [COMPLETE] Local AI AppleScripts compiled and installed to: $TARGET_DIR"
echo "  • Local_AI_Command_Center.scpt"
echo "  • Local_AI_Quick_Prompt.scpt"
echo "  • Local_AI_Mesh_Health.scpt"
echo "  • CLI: 'local-ai --mode coder --prompt ...'"
