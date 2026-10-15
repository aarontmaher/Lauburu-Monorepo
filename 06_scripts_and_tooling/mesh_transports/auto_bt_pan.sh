#!/usr/bin/env bash
# Lauburu Autonomous Bluetooth PAN & BNEP Mesh Setup Script
# Polyglot POSIX Specialist / Mesh Unified Transports

echo "📡 Initializing Lauburu Bluetooth PAN Mesh Automation..."

OS="$(uname -s)"
# Target Mesh Peers (MAC formatting handles blueutil requirements)
PIXEL_MAC="30-E0-44-6D-18-EC"
S20_MAC="5C-CB-99-05-81-41"
MBP_MAC="DC-29-55-D6-FC-0B"
MBA_MAC="2C-CA-16-08-C0-27"
L3_MAC="00-41-0E-14-28-44"
L4_MAC="00-03-7F-C2-00-43"

if [ "$OS" = "Darwin" ]; then
    echo "🍎 macOS Detected. Ensuring blueutil is installed..."
    if ! command -v blueutil &> /dev/null; then
        echo "[!] blueutil not found. Please install via brew: brew install blueutil"
        exit 1
    fi
    
    echo "🔄 Powering on Bluetooth..."
    blueutil --power 1
    sleep 2
    
    echo "🔗 Attempting PAN BNEP connections to registered Mesh Nodes..."
    for MAC in $PIXEL_MAC $S20_MAC $MBP_MAC $MBA_MAC $L3_MAC $L4_MAC; do
        echo " -> Connecting to $MAC"
        blueutil --connect $MAC || echo "    [!] Failed to connect to $MAC (May be out of range, asleep, or requires manual pairing)"
    done
    
    echo "🌐 Finding Bluetooth PAN interface..."
    PAN_IFACE=$(networksetup -listallhardwareports | awk '/Bluetooth PAN/{getline; print $2}')
    if [ -n "$PAN_IFACE" ]; then
        echo "✅ Bluetooth PAN Interface found: $PAN_IFACE."
        echo "    IP configuration state:"
        ifconfig $PAN_IFACE | grep 'inet ' || echo "    [!] No IPv4 allocated yet. (Requires sudo ipconfig set $PAN_IFACE DHCP)"
    else
        echo "⚠️ Bluetooth PAN Interface not found in hardware ports."
    fi

elif [ "$OS" = "Linux" ]; then
    echo "🐧 Linux Detected. Using bluetoothctl and bt-pan..."
    if ! command -v bluetoothctl &> /dev/null; then
        echo "[!] bluetoothctl not found."
        exit 1
    fi
    
    bluetoothctl power on
    echo "    [i] Ensure bt-pan is installed. Command to connect to Mac Host:"
    echo "    sudo bt-pan client 1C:F6:4C:81:0B:28 bnep0"
else
    echo "❓ Unsupported OS: $OS"
fi

echo "🏁 Bluetooth PAN Automation Routine Complete."
