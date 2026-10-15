#!/bin/bash
APPS_DIR="/Volumes/Lauburu-Monorepo/01_apps"
REPORT="/Volumes/Lauburu-Monorepo/logs/audit_report.log"
REGISTRY="/Volumes/Lauburu-Monorepo/obsidian_vault/CANONICAL_APP_REGISTRY.md"

echo "Starting Screen Lens Sovereign Global App Audit..." > "$REPORT"

# Initialize Canonical Registry
cat << 'REG' > "$REGISTRY"
---
title: "Canonical App Registry & Production Readiness"
tags: [lauburu, apps, production, registry, local-ai]
---
# 🚀 Canonical App Registry & Production Readiness

This registry is autonomously compiled every 15 minutes by the Global App Auditor (`task-1579`).
It enforces **Spec-09 App Store Production Readiness** and **Mandatory Local AI Integration**.

| Application Name | Tech Stack | Prod Score | AI Mesh Integrated | Missing Prod Requirements |
| :--- | :--- | :--- | :--- | :--- |
REG

find "$APPS_DIR" -maxdepth 1 -mindepth 1 -type d | while read APP; do
    APP_NAME=$(basename "$APP")
    # Skip __pycache__ etc
    if [[ "$APP_NAME" == __* ]]; then continue; fi

    echo "======================================" >> "$REPORT"
    echo "Auditing & Prod-Scoring: $APP_NAME" >> "$REPORT"
    
    TECH_STACK="Unknown"
    SCORE=50
    MISSING=""
    AI_STATUS="❌ No"

    # 1. Base Prod Checks
    if [ ! -f "$APP/README.md" ]; then
        MISSING+="No README, "
        SCORE=$((SCORE - 10))
    else
        SCORE=$((SCORE + 10))
    fi

    # 2. Local AI Integration Check (Rule 7/8 Invariants)
    if grep -r -E "127.0.0.1:808[1-3]|prima\.cpp|llama\.cpp|qwen|gguf" "$APP" --exclude-dir=node_modules --exclude-dir=target --exclude-dir=.git 2>/dev/null | grep -q .; then
        AI_STATUS="🧠 Yes (Qwen/GGUF)"
        SCORE=$((SCORE + 20))
    else
        MISSING+="No Local AI Integration, "
        SCORE=$((SCORE - 15))
    fi

    # 3. Tech-Specific Prod Checks
    # Python
    if [ -f "$APP/requirements.txt" ] || ls "$APP"/*.py 1> /dev/null 2>&1; then
        TECH_STACK="Python"
        python3 -m py_compile "$APP"/*.py 2>> "$REPORT" || echo "Python syntax errors found." >> "$REPORT"
        if grep -q "print(" "$APP"/*.py 2>/dev/null; then
            MISSING+="Raw prints found, "
            SCORE=$((SCORE - 5))
        fi
    fi
    
    # Rust
    if [ -f "$APP/Cargo.toml" ]; then
        TECH_STACK="Rust"
        (cd "$APP" && cargo check 2>> "$REPORT") || echo "Cargo check failed." >> "$REPORT"
        # Prod check: run clippy
        (cd "$APP" && cargo clippy -- -D warnings >/dev/null 2>&1) || MISSING+="Clippy Warnings, "
    fi
    
    # Flutter/Dart
    if [ -f "$APP/pubspec.yaml" ]; then
        TECH_STACK="Flutter/Dart"
        (cd "$APP" && dart analyze 2>> "$REPORT") || echo "Dart analyze failed." >> "$REPORT"
        if grep -q "print(" "$APP"/lib/*.dart 2>/dev/null; then
            MISSING+="Avoid print (use debugPrint), "
            SCORE=$((SCORE - 5))
        fi
        if [ ! -d "$APP/test" ]; then
            MISSING+="No unit tests, "
            SCORE=$((SCORE - 10))
        fi
    fi

    # Clamp Score
    if [ "$SCORE" -lt 0 ]; then SCORE=0; fi
    if [ "$SCORE" -gt 100 ]; then SCORE=100; fi
    if [ "$MISSING" == "" ]; then MISSING="Ready for Production ✅"; fi

    # Write to Canonical Registry
    echo "| **$APP_NAME** | $TECH_STACK | $SCORE% | $AI_STATUS | ${MISSING%, } |" >> "$REGISTRY"

done

echo "Audit & Registry Compilation Complete." >> "$REPORT"

# Ensure Obsidian Index Links to Registry
INDEX_FILE="/Volumes/Lauburu-Monorepo/obsidian_vault/Index.md"
if ! grep -q "CANONICAL_APP_REGISTRY" "$INDEX_FILE"; then
    echo "- [[CANONICAL_APP_REGISTRY]]" >> "$INDEX_FILE"
fi

# ----------------------------------------------------------------------
# Visual UI/UX & End-to-End Human Click-Through Assessment
# ----------------------------------------------------------------------
echo "======================================" >> "$REPORT"
echo "Running E2E Human Click-Through & Visual UI/UX Assessments..." >> "$REPORT"
echo "[Screen Lens Sovereign Visual Audit]" >> "$REPORT"

python3 /Volumes/Lauburu-Monorepo/01_apps/screen_lens/src/screen_lens_closed_loop_fix_engine.py --mode=audit-all-uis >> "$REPORT" 2>&1 || echo "Visual Audit Encountered Errors." >> "$REPORT"

echo "E2E Visual Assessment Complete." >> "$REPORT"
