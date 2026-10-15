#!/bin/sh
# Start Tailscale daemon in userspace networking mode
/usr/sbin/tailscaled --tun=userspace-networking --socks5-server=localhost:1055 &
sleep 2

# Authenticate Tailscale using an ephemeral auth key passed via Secret Manager
if [ -z "$TAILSCALE_AUTHKEY" ]; then
    echo "ERROR: TAILSCALE_AUTHKEY is not set."
    exit 1
fi
/usr/bin/tailscale up --authkey=${TAILSCALE_AUTHKEY} --hostname=cloudrun-webhook-proxy

# Start the FastAPI proxy server
exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}
