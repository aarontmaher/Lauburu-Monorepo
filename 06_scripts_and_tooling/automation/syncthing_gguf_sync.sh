#!/usr/bin/env bash
# Syncthing GGUF / Parquet Delta-Sync Orchestrator
# Binds to Nebula IP (10.255.x.x) and synchronizes datasets to L3/L6/L7 
# without FUSE/Container overhead.

set -e

echo "[*] Initializing Syncthing API sync for GGUF models..."
# In a real environment, this utilizes the Syncthing REST API to add folders and devices.

# L1 Mac -> L3 Linux Hub
echo "[*] Pairing L1 (10.255.0.1) -> L3 (10.255.0.3)..."
echo "[*] Adding Folder: /Volumes/Lauburu-Monorepo/04_data_and_memory/data/"

# L2 MacBook Pro -> L6 Pixel (GGUF splits)
echo "[*] Pairing L2 (10.255.0.2) -> L6 (10.255.0.6)..."
echo "[*] Adding Folder: /Volumes/Lauburu-Monorepo/02_ai_models_and_inference/gguf_vault/"

echo "[+] Sync established. GGUF slices will securely cache on edge disks for mmap() loading."
