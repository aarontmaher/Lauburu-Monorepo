#!/bin/bash
echo "Installing Lauburu Mesh Governor Gateway to GL.iNet Router (192.168.8.1)..."

ssh root@192.168.8.1 << 'ROUTER'
cat << 'GATEWAY' > /root/mesh_governor_gateway.sh
#!/bin/sh
# GL.iNet Lightweight Governor Gateway
# Receives distress signals, grabs local diagnostics, and asks the Mac Mini for the healing chain over PAN.

TARGET=$1
echo "Sending distress signal for $TARGET..."

DIAG="Diagnostics:\ntarget: $TARGET\ntailscale status: $(tailscale status 2>/dev/null | grep $TARGET || echo 'offline')\nping: $(ping -c 1 $TARGET 2>&1 | head -n 1)\nbluetooth pan: $(hciconfig hci0 2>/dev/null | grep -q UP && echo 'active' || echo 'missing')"

# Ask Mac Mini's Governor API via Bluetooth PAN IP (192.168.2.2 is typical PAN IP, using 192.168.8.x for Tailscale fallback)
# We assume the Mac Mini is hosting the model on 192.168.8.230:19004
JSON_PLAN=$(curl -s -X POST -H "Content-Type: application/json" -d "{\"diag\": \"$DIAG\"}" http://192.168.8.230:19004/heal)

echo "Received Healing Chain: $JSON_PLAN"
# Execute the chain... (placeholder for strict JSON parsing using jq)
GATEWAY
chmod +x /root/mesh_governor_gateway.sh
echo "Governor Gateway Script installed on Router."
ROUTER
echo "Done."
