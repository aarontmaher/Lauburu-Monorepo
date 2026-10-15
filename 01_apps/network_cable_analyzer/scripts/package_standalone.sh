#!/usr/bin/env bash
# ==============================================================================
# package_standalone.sh — Network Cable Analyzer Lauburu
# Packages backend FastAPI and frontend static assets into a single standalone
# executable binary (cable_analyzer) using PyInstaller.
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="${APP_DIR}/.venv"
PYTHON_BIN="${VENV_DIR}/bin/python"
PYINSTALLER_BIN="${VENV_DIR}/bin/pyinstaller"
DIST_DIR="${APP_DIR}/dist"
BUILD_TMP="${APP_DIR}/build_tmp"
OUTPUT_BIN="${APP_DIR}/cable_analyzer"
PORTFOLIO_BUILDS="/Users/aaron/teamwork_projects/app_production_and_sellability/builds"

echo "========================================================================"
echo "📦 Packaging Network Cable Analyzer Standalone Binary"
echo "========================================================================"

# 1. Ensure pyinstaller is available
if [ ! -x "${PYINSTALLER_BIN}" ]; then
    echo "Installing PyInstaller into ${VENV_DIR}..."
    uv pip install --python "${VENV_DIR}" pyinstaller
fi

# 2. Clean previous build artifacts
rm -rf "${DIST_DIR}" "${BUILD_TMP}" "${OUTPUT_BIN}"

# 3. Build standalone single-binary using PyInstaller
echo "🔨 Running PyInstaller..."
"${PYINSTALLER_BIN}" \
    --noconfirm \
    --onefile \
    --name "cable_analyzer" \
    --paths "${APP_DIR}/backend" \
    --add-data "${APP_DIR}/frontend:frontend" \
    --hidden-import "uvicorn" \
    --hidden-import "uvicorn.logging" \
    --hidden-import "uvicorn.loops" \
    --hidden-import "uvicorn.loops.auto" \
    --hidden-import "uvicorn.protocols" \
    --hidden-import "uvicorn.protocols.http" \
    --hidden-import "uvicorn.protocols.http.auto" \
    --hidden-import "uvicorn.protocols.websockets" \
    --hidden-import "uvicorn.protocols.websockets.auto" \
    --hidden-import "uvicorn.lifespan" \
    --hidden-import "uvicorn.lifespan.on" \
    --hidden-import "fastapi" \
    --hidden-import "psutil" \
    --hidden-import "httpx" \
    --hidden-import "websockets" \
    --workpath "${BUILD_TMP}" \
    --distpath "${DIST_DIR}" \
    "${APP_DIR}/backend/server.py"

# 4. Copy binary to APP_DIR root as ./cable_analyzer
cp "${DIST_DIR}/cable_analyzer" "${OUTPUT_BIN}"
chmod +x "${OUTPUT_BIN}"

# 5. Clean temporary build directory
rm -rf "${BUILD_TMP}" "${DIST_DIR}" "${APP_DIR}/cable_analyzer.spec"

# 6. Stage artifact into portfolio builds directory
if [ -d "${PORTFOLIO_BUILDS}" ]; then
    echo "🚚 Staging cable_analyzer into ${PORTFOLIO_BUILDS}..."
    cp "${OUTPUT_BIN}" "${PORTFOLIO_BUILDS}/cable_analyzer"
    chmod +x "${PORTFOLIO_BUILDS}/cable_analyzer"
fi

echo "========================================================================"
echo "✅ Successfully built standalone binary: ${OUTPUT_BIN}"
echo "   Test with: ${OUTPUT_BIN} --port 4007"
echo "========================================================================"
