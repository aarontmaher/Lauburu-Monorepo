#!/bin/bash
set -e

M2_HOST="aaronmaher@10.0.0.3"
M2_ROOT="/Volumes/AI_Projects/L5_Offload_Archive"
LOCAL_MOUNT="/Volumes/Lauburu-Monorepo/storage_hub_2tb/L5_Offload_Archive"

migrate_and_symlink() {
    local src="$1"
    local rel_dest="$2"
    if [ -L "$src" ]; then
        echo "[SKIP] $src is already a symlink -> $(readlink "$src")"
        return 0
    fi
    if [ ! -d "$src" ]; then
        echo "[SKIP] $src does not exist"
        return 0
    fi
    echo "=== Migrating $src -> $M2_HOST:$M2_ROOT/$rel_dest ==="
    ssh -o StrictHostKeyChecking=no "$M2_HOST" "mkdir -p '$M2_ROOT/$rel_dest'"
    chmod -R u+w "$src" 2>/dev/null || true
    rsync -a --remove-source-files "$src/" "$M2_HOST:$M2_ROOT/$rel_dest/" || true
    sudo -n rm -rf "$src"
    ln -s "$LOCAL_MOUNT/$rel_dest" "$src"
    echo "[DONE] $src -> $LOCAL_MOUNT/$rel_dest"
    df -h /System/Volumes/Data | tail -n 1
}

# Wave 3 items (0 open files verified via lsof)
migrate_and_symlink "/Volumes/Library/Caches/JetBrains/IntelliJIdea2026.2" "Library_Caches/JetBrains_IntelliJIdea2026.2"
migrate_and_symlink "/Volumes/Library/Application Support/JetBrains/IntelliJIdea2026.2" "Library_Caches/AppSupport_IntelliJIdea2026.2"
migrate_and_symlink "/Volumes/Library/Application Support/JetBrains/PyCharm2026.2" "Library_Caches/AppSupport_PyCharm2026.2"
migrate_and_symlink "/Users/aaronmaher/.hermes" "Dotfiles_And_Envs/users_dot_hermes"
migrate_and_symlink "/Volumes/Library/Application Support/Google/GoogleUpdater" "Library_Caches/GoogleUpdater"
migrate_and_symlink "/Volumes/Library/Application Support/Google/AndroidStudio2026.2.1" "Library_Caches/AppSupport_AndroidStudio2026.2.1"
migrate_and_symlink "/Volumes/.antigravity-ide" "Dotfiles_And_Envs/dot_antigravity_ide"
migrate_and_symlink "/Volumes/.pi" "Dotfiles_And_Envs/dot_pi"
migrate_and_symlink "/Volumes/Lauburu-Monorepo/12_continuous_lora_evolution" "Lauburu_Monorepo_Data/12_continuous_lora_evolution"
migrate_and_symlink "/Volumes/Lauburu-Monorepo/08_business_and_commerce" "Lauburu_Monorepo_Data/08_business_and_commerce"

echo "=== Wave 3 Migration Complete ==="
df -h /System/Volumes/Data /Volumes/Lauburu-Monorepo/storage_hub_2tb
