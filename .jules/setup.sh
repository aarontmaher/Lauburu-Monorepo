#!/usr/bin/env bash
# ==============================================================================
# Google Jules Repository Environment Setup Script
# ==============================================================================
# Repository: aarontmaher/Lauburu-Monorepo
# Config URL: https://jules.google.com/repo/github/aarontmaher/Lauburu-Monorepo/config
# ==============================================================================

set -eo pipefail

echo "=== [Jules Setup] Initializing Jules Environment for Lauburu Monorepo ==="

# 1. Environment Path Configuration
export PATH="/Users/aaron/.nvm/versions/node/v20.20.2/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

# 2. Verify Python & Node Tooling
echo "--> Checking Python and Node runtimes..."
python3 --version || echo "python3 not found"
node --version || echo "node not found"

# 3. Ensure Core Dependencies
echo "--> Verifying Python dependencies..."
python3 -c "import google.genai, google.auth, pytest; print('Core dependencies present!')" 2>/dev/null || {
    echo "--> Installing required dependencies..."
    python3 -m pip install --break-system-packages --quiet google-genai google-auth tenacity sniffio distro pytest flake8 || true
}

# 4. Verify Privacy Exclusions (.julesignore)
if [ -f ".julesignore" ]; then
    echo "--> .julesignore validated successfully."
else
    echo "--> WARNING: .julesignore missing! Creating default privacy filter..."
    cat << 'EOF' > .julesignore
03_biometrics_and_telemetry/data/
04_data_and_memory/
reports/
session_logs/
logs/
*.png
*.sqlite
*.db
*.log
EOF
fi

# 5. Pre-compile Python Bytecode for Performance (Excluding virtualenvs)
echo "--> Pre-compiling Python scripts in 06_scripts_and_tooling/jules..."
python3 -m compileall -q -x '(\.venv|\.git|node_modules)' 06_scripts_and_tooling/jules/ || true

echo "=== [Jules Setup] Setup completed successfully! ==="
exit 0
