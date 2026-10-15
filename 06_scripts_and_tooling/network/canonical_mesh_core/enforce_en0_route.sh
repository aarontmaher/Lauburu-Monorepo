#!/usr/bin/env bash
set -e

ROUTER_IP="192.168.8.1"
SUBNET="192.168.8.0/24"
INTERFACE="en0"
PASSWORD="goldfighting1"

# Check current route
CURRENT_IF=$(route -n get ${ROUTER_IP} 2>/dev/null | grep interface | awk '{print $2}')

if [ "$CURRENT_IF" != "$INTERFACE" ]; then
    echo "$(date): Route for ${ROUTER_IP} is via ${CURRENT_IF}. Forcing it to ${INTERFACE}."
    echo "$PASSWORD" | sudo -S route delete -net ${SUBNET} 2>/dev/null || true
    echo "$PASSWORD" | sudo -S route add -net ${SUBNET} -interface ${INTERFACE}
else
    echo "$(date): Route for ${ROUTER_IP} is correctly set to ${INTERFACE}."
fi
