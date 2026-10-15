#!/bin/bash
# Move running instances to canonical format, start the Zellij dashboard.

DIR="/Volumes/Lauburu-Monorepo/06_scripts_and_tooling/network/canonical_mesh_core"
cd $DIR

echo "[*] Migrating running protocols to Canonical Folder..."
# Launch Zellij with the specific layout
zellij --layout mesh_dashboard.kdl
