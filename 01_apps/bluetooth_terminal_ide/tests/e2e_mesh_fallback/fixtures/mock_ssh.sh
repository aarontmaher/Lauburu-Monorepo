#!/bin/bash
# Authentic Executable Script Fixture: mock_ssh.sh
# Emulates SSH client binary without python mocks.

if [ -n "$SSH_AUDIT_LOG" ]; then
    echo "$(date +%s%N) [SSH_INVOKED] PID=$$ ARGS=$*" >> "$SSH_AUDIT_LOG"
fi

# If stay alive is requested (for process management / watchdog tests)
if [ "$SSH_STAY_ALIVE" = "1" ]; then
    # Trap SIGTERM to log exit
    trap 'echo "$(date +%s%N) [SSH_TERMINATED] PID=$$" >> "$SSH_AUDIT_LOG"; exit 0' SIGTERM SIGINT
    while true; do
        sleep 0.1
    done
fi

exit 0
