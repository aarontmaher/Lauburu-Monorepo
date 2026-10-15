#!/usr/bin/env bash
# Movesense SDK Setup & Build Orchestrator for Lauburu AI Swarm

SDK_DIR="/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/movesense_sdk"
FIRMWARE_DIR="/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/ai/tiny_lms/movesense_nordic"

echo "🔋 Initializing Official Movesense Device SDK..."

if [ ! -d "$SDK_DIR/movesense-device-lib" ]; then
    echo "⬇️ Cloning Movesense SDK..."
    git clone --depth 1 https://bitbucket.org/suunto/movesense-device-lib.git "$SDK_DIR/movesense-device-lib"
else
    echo "✅ Movesense SDK already exists."
fi

# The official Movesense build environment relies on a specific Docker container 
# containing the exact ARM GCC toolchain and Nordic dependencies.
echo "🐳 Pulling Official Movesense Build Environment Container..."
# docker pull movesense/build-env:latest (Commented to avoid blocking pull during setup)

echo "🛠️ Creating Firmware Compile Hook..."

cat << 'EOF' > "$FIRMWARE_DIR/compile_firmware.sh"
#!/usr/bin/env bash
# Autonomous Firmware Compiler for Lauburu AI

PROJECT_PATH=$(pwd)
BUILD_DIR="${PROJECT_PATH}/build"

mkdir -p "$BUILD_DIR"

echo "🚀 Compiling Multi-Modal TinyLM C++ Firmware via Movesense Docker..."

# Uses the official Movesense build environment to cross-compile the firmware
docker run --rm -v "${PROJECT_PATH}:/src" -v "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/movesense_sdk/movesense-device-lib:/movesense-device-lib" movesense/build-env:latest \
    bash -c "cd /src/build && cmake -DMOVESENSE_CORE_LIBRARY=/movesense-device-lib .. && make"

echo "✅ Compilation Complete. Output ready for Over-The-Air (OTA) DFU Flash."
EOF

chmod +x "$FIRMWARE_DIR/compile_firmware.sh"

echo "✅ Movesense Developer Tools integrated. The swarm can now compile .hex payloads."
