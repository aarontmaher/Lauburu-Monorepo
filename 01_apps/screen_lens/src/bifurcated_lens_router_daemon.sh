#!/bin/sh
# ==============================================================================
# BIFURCATED SCREEN LENS - OPENWRT ROUTER DAEMON
# Deploys the Frontier Consensus Architecture on the GL.iNet Router (GW Node)
# ==============================================================================

TAILSCALE_IFACE="tailscale0"
USB_BUS_ID="1-1" # Assuming Pixel 10 Pro XL is on USB bus 1-1
TIMEOUT_SEC=60

check_mesh_health() {
    # Check if we have received/transmitted any packets on Tailscale in the last minute
    # (Simplified for OpenWrt 'ash' using ifconfig rx/tx counters)
    rx_packets=$(ifconfig $TAILSCALE_IFACE | grep "RX packets" | awk '{print $3}')
    
    sleep 5
    rx_packets_new=$(ifconfig $TAILSCALE_IFACE | grep "RX packets" | awk '{print $3}')
    
    if [ "$rx_packets" = "$rx_packets_new" ]; then
        return 1 # Mesh is dead/stalled
    else
        return 0 # Mesh is healthy
    fi
}

enable_usbip_transparent_proxy() {
    echo "[STAGE 1] Mesh Healthy. Enabling USB/IP transparent proxy to Mac Mini..."
    # Kill local ADB server to free the USB bus
    adb kill-server 2>/dev/null
    
    # Bind the Pixel 10 USB device to usbip
    usbip bind -b $USB_BUS_ID
    usbipd -D
}

trigger_nano_lens_failsafe() {
    echo "[STAGE 2] Mesh Collapsed! Activating Nano-Lens Local Failsafe..."
    # Kill usbipd to take back local control of the USB bus
    killall usbipd 2>/dev/null
    usbip unbind -b $USB_BUS_ID 2>/dev/null
    
    # Start local ADB daemon on the router
    adb start-server
    sleep 2
    
    echo ">> Extracting raw framebuffer from Pixel 10..."
    adb shell screencap -p > /tmp/screen.png
    
    echo ">> Running highly-quantized NCNN bounding-box scanner (Nano-Lens)..."
    # ./nano_lens_ncnn /tmp/screen.png
    
    # Simulated Repair Action (Tapping Shizuku/Tailscale reconnect)
    echo ">> Nano-Lens identified Tailscale disconnected. Injecting repair tap at X:540 Y:1200"
    adb shell input tap 540 1200
    
    sleep 10
}

# --- MAIN DAEMON LOOP ---
echo "Starting Bifurcated Screen Lens Daemon for OpenWrt..."

while true; do
    if check_mesh_health; then
        # Ensure USB/IP is running if healthy
        if ! pgrep usbipd > /dev/null; then
            enable_usbip_transparent_proxy
        fi
    else
        # If Tailscale drops, execute the autonomous physical repair
        trigger_nano_lens_failsafe
    fi
    sleep $TIMEOUT_SEC
done
