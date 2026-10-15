#!/bin/bash
echo "📡 Monitoring Tailscale Direct P2P Status for Pixel 10 Pro XL (10.1.0.13)..."
echo "Waiting for DERP relay to drop and direct connection to establish..."
echo "------------------------------------------------------------------------"

while true; do
    STATUS=$(tailscale status | grep pixel-10-pro-xl)
    if [[ "$STATUS" == *"direct"* ]]; then
        echo -e "\033[0;32m[SUCCESS] Pixel 10 is now DIRECT! 🚀\033[0m"
        tailscale ping -c 4 10.1.0.13
        break
    else
        LATENCY=$(ping -c 1 -W 1 10.1.0.13 | grep 'time=' | awk -F'time=' '{print $2}')
        echo -e "\033[0;33m[WARNING] Still on Sydney Cloud Relay (DERP). Current Latency: ${LATENCY}\033[0m"
        sleep 2
    fi
done
