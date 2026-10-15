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
