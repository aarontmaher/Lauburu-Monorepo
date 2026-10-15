#!/bin/bash
# ==============================================================================
# SPARSE SWARM DISPATCHER
# Lauburu AI Ecosystem - Native Git Worktree & SKILL.md Sandbox Injector
# ==============================================================================
# Usage: ./sparse_swarm_dispatcher.sh <task_id> <target_directory> <skill_name>
# Example: ./sparse_swarm_dispatcher.sh ui_fix 01_apps/screen_lens polyglot-python-textual-specialist

set -e

TASK_ID=$1
TARGET_DIR=$2
SKILL_NAME=$3

MONOREPO_DIR="/Volumes/Lauburu-Monorepo"
WORKTREES_DIR="/Volumes/Lauburu-Monorepo/Lauburu-Worktrees"
SKILLS_DIR="/Volumes/Lauburu-Monorepo/.agents/skills"

if [ -z "$TASK_ID" ] || [ -z "$TARGET_DIR" ] || [ -z "$SKILL_NAME" ]; then
    echo "Usage: $0 <task_id> <target_directory> <skill_name>"
    exit 1
fi

echo "[*] Initializing Sparse Swarm Sandbox for Task: $TASK_ID"

# 1. Create the overarching worktrees directory if it doesn't exist
mkdir -p "$WORKTREES_DIR"
cd "$MONOREPO_DIR"

# 2. Check if branch already exists, if not create and add worktree
WORKTREE_PATH="$WORKTREES_DIR/swarm_$TASK_ID"

if [ -d "$WORKTREE_PATH" ]; then
    echo "[!] Worktree already exists at $WORKTREE_PATH. Tearing down..."
    git worktree remove -f "$WORKTREE_PATH"
    git branch -D "swarm/$TASK_ID" 2>/dev/null || true
fi

echo "[*] Spawning Git Worktree: swarm/$TASK_ID"
git worktree add -b "swarm/$TASK_ID" "$WORKTREE_PATH"

# 3. Apply Sparse-Checkout to shrink the agent's universe
echo "[*] Shrinking Context Window to: $TARGET_DIR"
cd "$WORKTREE_PATH"
git sparse-checkout init --cone
git sparse-checkout set "$TARGET_DIR"

# 4. Inject the SKILL.md as the System Prompt
SKILL_PATH="$SKILLS_DIR/$SKILL_NAME/SKILL.md"

if [ -f "$SKILL_PATH" ]; then
    echo "[*] Injecting SKILL.md ($SKILL_NAME) into Sandbox..."
    cp "$SKILL_PATH" ./SYSTEM_PROMPT.md
else
    # Fallback to gemini config paths if not in DFS_UNIFIED
    ALT_SKILL_PATH="/Users/aaron/.gemini/config/skills/$SKILL_NAME/SKILL.md"
    if [ -f "$ALT_SKILL_PATH" ]; then
        echo "[*] Injecting SKILL.md ($SKILL_NAME) into Sandbox..."
        cp "$ALT_SKILL_PATH" ./SYSTEM_PROMPT.md
    else
        echo "[!] Warning: SKILL.md for $SKILL_NAME not found. Agent will spawn as generalist."
        echo "No specific skill found for $SKILL_NAME." > ./SYSTEM_PROMPT.md
    fi
fi

echo "[✓] Sandbox Ready: $WORKTREE_PATH"
echo "    Agent should be spawned inside this directory and instructed to read SYSTEM_PROMPT.md."
