#!/bin/bash
set -e

# Start tailscaled in the background
echo "Starting tailscaled..."
tailscaled --tun=userspace-networking --socks5-server=localhost:1055 &
sleep 5

# Connect to the mesh network using the provided auth key and headscale URL
if [ -n "$HEADSCALE_URL" ] && [ -n "$TAILSCALE_AUTH_KEY" ]; then
    echo "Connecting to Headscale server at $HEADSCALE_URL..."
    tailscale up --login-server="$HEADSCALE_URL" --authkey="$TAILSCALE_AUTH_KEY"
else
    echo "WARNING: HEADSCALE_URL or TAILSCALE_AUTH_KEY not provided. Mesh networking won't automatically connect."
fi

# Find the Tailscale IP address
TS_IP=$(tailscale ip -4 || echo "0.0.0.0")
echo "Worker node IP: $TS_IP"

# Start the llama-rpc-server, binding to the Tailscale IP (or all interfaces)
RPC_PORT=${RPC_PORT:-50052}
echo "Starting llama-rpc-server on port $RPC_PORT..."

# Note: In production you might want to specify the host to bind to TS_IP, but 0.0.0.0 works fine inside a container
exec /opt/llama.cpp/build/bin/llama-rpc-server -H 0.0.0.0 -p "$RPC_PORT"
