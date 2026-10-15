#!/bin/bash
# Run this on the Linux Laptop that the tablet is plugged into.

echo "🔌 Configuring USB Tethering Bridge to the Lauburu Mesh..."

# 1. Identify the USB network interface (usually usb0 or enp*u*)
USB_IFACE=$(ip -o link show | awk -F': ' '{print $2}' | grep -E "^(usb|enp.*u)")

if [ -z "$USB_IFACE" ]; then
    echo "❌ No USB network interface found. Ensure the tablet is set to 'USB Tethering' mode."
    exit 1
fi

echo "✅ Found USB Interface: $USB_IFACE"

# 2. Enable IP Forwarding so the Tablet can reach the broader Tailscale Mesh through the laptop
echo "net.ipv4.ip_forward = 1" | sudo tee -a /etc/sysctl.conf > /dev/null
sudo sysctl -p > /dev/null
echo "✅ IPv4 Forwarding Enabled."

# 3. Configure NAT (iptables) to route tablet traffic out to the Mesh
DEFAULT_ROUTE=$(ip route show default | awk '/default/ {print $5}')
sudo iptables -t nat -A POSTROUTING -o $DEFAULT_ROUTE -j MASQUERADE
sudo iptables -A FORWARD -i $DEFAULT_ROUTE -o $USB_IFACE -m state --state RELATED,ESTABLISHED -j ACCEPT
sudo iptables -A FORWARD -i $USB_IFACE -o $DEFAULT_ROUTE -j ACCEPT
echo "✅ iptables NAT routing configured from $USB_IFACE to $DEFAULT_ROUTE."

# 4. Give the Tablet a static IP on the USB subnet (assuming standard 192.168.42.x for USB tethering)
# The laptop takes .1, the tablet takes .129
sudo ip addr add 192.168.42.1/24 dev $USB_IFACE 2>/dev/null || true
sudo ip link set $USB_IFACE up

echo "🚀 Mesh USB Bridge is Active."
echo "You can now SSH into the tablet via its Tailscale IP (100.81.92.125) or local USB IP (192.168.42.129)."
