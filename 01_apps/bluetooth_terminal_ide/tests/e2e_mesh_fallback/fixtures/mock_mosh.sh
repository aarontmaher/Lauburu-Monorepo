#!/bin/bash
# Authentic Executable Script Fixture: mock_mosh.sh
# Emulates Mosh client binary without python mocks.

if [ -n "$MOSH_AUDIT_LOG" ]; then
    echo "$(date +%s%N) [MOSH_INVOKED] PID=$$ ARGS=$*" >> "$MOSH_AUDIT_LOG"
fi

if [ "$MOSH_STAY_ALIVE" = "1" ]; then
    trap 'echo "$(date +%s%N) [MOSH_TERMINATED] PID=$$" >> "$MOSH_AUDIT_LOG"; exit 0' SIGTERM SIGINT
    while true; do
        sleep 0.1
    done
fi

exit 0
