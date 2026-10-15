#!/usr/bin/env bash
# IntelliJ / PyCharm CLI & Local AI Orchestration Wrapper
# Resolves the JetBrains IDE, Junie CLI, and local AI model endpoints

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PYCHARM_BIN="/Applications/PyCharm.app/Contents/MacOS/pycharm"
GOLAND_BIN="/Applications/GoLand.app/Contents/MacOS/goland"
INTELLIJ_BIN="/Applications/IntelliJ IDEA.app/Contents/MacOS/idea"
IDE_BIN="$PYCHARM_BIN"
JUNIE_BIN="/Users/aaron/.local/bin/junie"
ORCHESTRATOR="$REPO_ROOT/06_scripts_and_tooling/automation/multiplexed_ai_terminal_orchestrator.py"
LENS_CLI="$REPO_ROOT/06_scripts_and_tooling/lens_cli.py"

case "$1" in
    --goland|--langgo)
        shift
        if [ "$1" = "--specialist" ] || [ "$1" = "--specialists" ]; then
            exec python3 "$LENS_CLI" specialists --target goland --json
        elif [ -f "$GOLAND_BIN" ]; then
            exec "$GOLAND_BIN" "$@"
        else
            exec python3 "$LENS_CLI" specialists --target goland --json
        fi
        ;;
    --pycharm)
        shift
        if [ "$1" = "--specialist" ] || [ "$1" = "--specialists" ]; then
            exec python3 "$LENS_CLI" specialists --target pycharm --json
        elif [ -f "$PYCHARM_BIN" ]; then
            exec "$PYCHARM_BIN" "$@"
        else
            exec python3 "$LENS_CLI" specialists --target pycharm --json
        fi
        ;;
    --intellij|--idea)
        shift
        if [ "$1" = "--specialist" ] || [ "$1" = "--specialists" ]; then
            exec python3 "$LENS_CLI" specialists --target intellij --json
        elif [ -f "$INTELLIJ_BIN" ]; then
            exec "$INTELLIJ_BIN" "$@"
        else
            exec python3 "$LENS_CLI" specialists --target intellij --json
        fi
        ;;
    --chromium)
        shift
        exec python3 "$LENS_CLI" specialists --target chromium --json
        ;;
    --bt-serial|--bluetooth-serial)
        shift
        exec python3 "$LENS_CLI" specialists --target bt-serial --json
        ;;
    --specialists)
        shift
        exec python3 "$LENS_CLI" specialists "$@" --json
        ;;
    --junie)
        shift
        if [ -x "$JUNIE_BIN" ]; then
            exec "$JUNIE_BIN" "$@"
        else
            echo "Error: Junie CLI not found at $JUNIE_BIN"
            exit 1
        fi
        ;;
    --orchestrator)
        shift
        exec python3 "$ORCHESTRATOR" "$@"
        ;;
    --status)
        echo "=== JetBrains & Local AI CLI Environment ==="
        echo "PyCharm Bin:  $PYCHARM_BIN (Exists: $([ -f "$PYCHARM_BIN" ] && echo YES || echo NO)) -> /polyglot-python-specialist"
        echo "GoLand Bin:   $GOLAND_BIN (Exists: $([ -f "$GOLAND_BIN" ] && echo YES || echo NO)) -> /polyglot-go-bubbletea-specialist"
        echo "IntelliJ Bin: $INTELLIJ_BIN (Exists: $([ -f "$INTELLIJ_BIN" ] && echo YES || echo NO)) -> All 6 Polyglot Specialists"
        echo "Junie CLI:    $JUNIE_BIN (Exists: $([ -f "$JUNIE_BIN" ] && echo YES || echo NO))"
        python3 "$ORCHESTRATOR" --status
        exit 0
        ;;
    *)
        if [ -f "$GOLAND_BIN" ] && [ ! -f "$PYCHARM_BIN" ]; then
            exec "$GOLAND_BIN" "$@"
        elif [ -f "$IDE_BIN" ]; then
            exec "$IDE_BIN" "$@"
        else
            echo "Error: JetBrains executable not found at $IDE_BIN or $GOLAND_BIN"
            exit 1
        fi
        ;;
esac
