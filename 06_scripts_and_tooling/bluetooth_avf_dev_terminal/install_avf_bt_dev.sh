#!/usr/bin/env bash
# ==============================================================================
# Lauburu Pixel 10 Pro XL AVF Debian 13 — Bluetooth Serial --dev Installer
# Hardens AVF Guest against crashes & installs `tmux --dev` and `zellij --dev`
# ==============================================================================
set -euo pipefail

BT_DEV_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "======================================================================"
echo "  Lauburu Bluetooth Serial Terminal (--dev) & AVF Crash-Shield Setup  "
echo "======================================================================"

chmod +x "$BT_DEV_DIR/bt_serial_terminal.py" \
         "$BT_DEV_DIR/bt_dev_watcher.py" \
         "$BT_DEV_DIR/bt_serial_dev_launcher.sh" \
         "$BT_DEV_DIR/dev_shell_rc.sh"

# 1. Install real Zellij binary to /usr/local/bin/zellij-bin if /home/droid/zellij exists
if [ -x "$HOME/zellij" ]; then
    sudo cp -f "$HOME/zellij" /usr/local/bin/zellij-bin
    sudo chmod +x /usr/local/bin/zellij-bin
    echo "[+] Installed native ARM64 Zellij binary -> /usr/local/bin/zellij-bin ($(/usr/local/bin/zellij-bin --version))"
fi

# 2. Install /usr/local/bin/bt-serial-dev and /usr/local/bin/bt-serial symlinks
sudo ln -sf "$BT_DEV_DIR/bt_serial_dev_launcher.sh" /usr/local/bin/bt-serial-dev
sudo ln -sf "$BT_DEV_DIR/bt_serial_terminal.py" /usr/local/bin/bt-serial
echo "[+] Linked /usr/local/bin/bt-serial-dev and /usr/local/bin/bt-serial"

# 3. Install /usr/local/bin/tmux wrapper supporting `tmux --dev`
sudo rm -f /usr/local/bin/tmux
sudo tee /usr/local/bin/tmux >/dev/null << EOF
#!/usr/bin/env bash
# Lauburu tmux wrapper: intercepts \`tmux --dev\` (or \`tmux dev\`) to launch the
# live hot-reloading Bluetooth Serial Terminal 3-pane workspace.
# All other invocations pass transparently to /usr/bin/tmux.
if [ "\${1:-}" = "--dev" ] || [ "\${1:-}" = "dev" ]; then
    shift
    exec "$BT_DEV_DIR/bt_serial_dev_launcher.sh" --tmux "\$@"
fi
exec /usr/bin/tmux "\$@"
EOF
sudo chmod +x /usr/local/bin/tmux
echo "[+] Installed /usr/local/bin/tmux wrapper (supports 'tmux --dev')"

# 4. Install /usr/local/bin/zellij wrapper supporting `zellij --dev`
sudo rm -f /usr/local/bin/zellij
sudo tee /usr/local/bin/zellij >/dev/null << EOF
#!/usr/bin/env bash
# Lauburu zellij wrapper: intercepts \`zellij --dev\` (or \`zellij dev\`) to launch the
# live hot-reloading Bluetooth Serial Terminal 3-pane KDL layout.
# All other invocations pass transparently to /usr/local/bin/zellij-bin.
if [ "\${1:-}" = "--dev" ] || [ "\${1:-}" = "dev" ]; then
    shift
    exec "$BT_DEV_DIR/bt_serial_dev_launcher.sh" --zellij "\$@"
fi
if [ -x /usr/local/bin/zellij-bin ]; then
    exec /usr/local/bin/zellij-bin "\$@"
fi
exec "$BT_DEV_DIR/bt_serial_dev_launcher.sh" --tmux "\$@"
EOF
sudo chmod +x /usr/local/bin/zellij
echo "[+] Installed /usr/local/bin/zellij wrapper (supports 'zellij --dev')"

# 5. Harden /home/droid/.config/zellij/config.kdl (disable port 8082 web_server conflict)
if [ -f "$HOME/.config/zellij/config.kdl" ]; then
    cp "$HOME/.config/zellij/config.kdl" "$HOME/.config/zellij/config.kdl.bak"
    sed -i 's/web_server true/web_server false/g; s/web_sharing "on"/web_sharing "off"/g' "$HOME/.config/zellij/config.kdl"
    echo "[+] Hardened ~/.config/zellij/config.kdl (disabled duplicate port 8082 web_server)"
fi

# 6. Harden /home/droid/.bashrc against recursive Zellij/BT_SERIAL_DEV pane bombs
if [ -f "$HOME/.bashrc" ]; then
    cp "$HOME/.bashrc" "$HOME/.bashrc.bak_bt_dev"
    python3 - "$HOME/.bashrc" << 'PYEOF'
import sys
path = sys.argv[1]
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old_guard = 'if [[ $- == *i* ]] && [[ -z "$TMUX" ]] && [[ -z "$BASH_EXECUTION_STRING" ]]; then'
new_guard = 'if [[ $- == *i* ]] && [[ -z "${TMUX:-}" ]] && [[ -z "${ZELLIJ:-}" ]] && [[ -z "${ZELLIJ_SESSION_NAME:-}" ]] && [[ -z "${BT_SERIAL_DEV:-}" ]] && [[ -z "${BASH_EXECUTION_STRING:-}" ]]; then'

if old_guard in content:
    content = content.replace(old_guard, new_guard)
with open(path, "w", encoding="utf-8") as f:
    f.write(content)
PYEOF
    echo "[+] Hardened ~/.bashrc (prevents recursive startup bomb inside Zellij/dev panes)"
fi

# 7. Harden /home/droid/persistent_startup.sh so systemctl bursts run only once per boot
if [ -f "$HOME/persistent_startup.sh" ]; then
    cp "$HOME/persistent_startup.sh" "$HOME/persistent_startup.sh.bak_bt_dev"
    python3 - "$HOME/persistent_startup.sh" << 'PYEOF'
import sys
path = sys.argv[1]
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

if "/tmp/.avf_services_bootstrapped" not in content and "sudo systemctl start ssh" in content:
    old_block = """sudo systemctl start ssh 2>/dev/null || true"""
    new_block = """if [ ! -f /tmp/.avf_services_bootstrapped ]; then
    touch /tmp/.avf_services_bootstrapped
    sudo systemctl start ssh 2>/dev/null || true"""
    content = content.replace(old_block, new_block, 1)
    target_end = """sudo systemctl start lauburu-tui-web.service 2>/dev/null || true"""
    if target_end in content:
        content = content.replace(target_end, target_end + "\nfi", 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
PYEOF
    echo "[+] Hardened ~/persistent_startup.sh (boot-once guard /tmp/.avf_services_bootstrapped)"
fi

# 8. Configure crash-safe ~/.tmux.conf defaults for Pixel AVF ttyd WebView
if [ -f "$HOME/.tmux.conf" ]; then
    if ! grep -q "AVF Crash-Shield Settings" "$HOME/.tmux.conf"; then
        cat >> "$HOME/.tmux.conf" << 'EOF'

# --- AVF Crash-Shield Settings (Lauburu Bluetooth Serial --dev) ---
set -g history-limit 4000
set -sg escape-time 10
set -g status-interval 5
bind R source-file ~/.tmux.conf \; display-message "tmux.conf live-reloaded!"
bind B new-window -n "bt-serial-dev" "bt-serial-dev --tmux"
EOF
        echo "[+] Appended AVF Crash-Shield settings and keybindings to ~/.tmux.conf"
    fi
fi

echo "======================================================================"
echo "  Setup Complete! Try:  tmux --dev   OR   zellij --dev                "
echo "======================================================================"
