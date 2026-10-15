#!/bin/bash
# Authentic Executable Script Fixture: mock_rish.sh
# Emulates Android Shizuku rish binary (UID 2000 shell) without python mocks.

set -e

# Log execution if audit log path is configured
if [ -n "$RISH_AUDIT_LOG" ]; then
    echo "$(date +%s%N) [RISH] $*" >> "$RISH_AUDIT_LOG"
fi

if [ "$1" = "-c" ]; then
    CMD="$2"
    if [ "$CMD" = "id" ]; then
        echo "uid=2000(shell) gid=2000(shell) groups=2000(shell)"
        exit 0
    elif [ "$CMD" = "svc bluetooth enable" ]; then
        exit 0
    elif [ "$CMD" = "cmd tethering start-tethering bluetooth" ]; then
        if [ "$RISH_FAIL_PRIMARY" = "1" ]; then
            echo "Error: cmd tethering unavailable" >&2
            exit 1
        fi
        echo "Tethering bluetooth started successfully (BNEP active)"
        exit 0
    elif [ "$CMD" = "cmd connectivity tether start bluetooth" ]; then
        echo "Connectivity tether bluetooth started successfully"
        exit 0
    elif [[ "$CMD" =~ ^sleep ]]; then
        eval "$CMD"
        exit 0
    else
        # General command execution
        echo "SHIZUKU_EXEC: $CMD"
        exit 0
    fi
fi

echo "mock_rish usage: mock_rish.sh -c <command>"
exit 0
