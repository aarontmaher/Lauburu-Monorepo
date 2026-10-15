#!/usr/bin/env bash
# Deploy Nebula Mesh (Zero-Trust P2P Overlay) & MPTCP
# Generates certs and configures L1-L7 nodes.

set -e

NEBULA_DIR="/Volumes/Lauburu-Monorepo/00_core_infrastructure/nebula"
mkdir -p "$NEBULA_DIR/certs"
cd "$NEBULA_DIR"

echo "[*] Initializing Nebula CA..."
# stub: ./nebula-cert ca -name "LauburuMesh"

echo "[*] Generating node certificates..."
# stub: ./nebula-cert sign -name "L1_Mac_Host" -ip "10.255.0.1/24"
# stub: ./nebula-cert sign -name "L3_Linux_Hub" -ip "10.255.0.3/24"
# stub: ./nebula-cert sign -name "L6_Pixel_10_Edge" -ip "10.255.0.6/24"

echo "[*] Pushing certificates to mesh nodes..."
# stub: scp certs to nodes

echo "[*] Starting Nebula on L1 Mac Host..."
# stub: sudo ./nebula -config config.yml

echo "[+] Nebula Mesh scaffold complete."
