# 🌐 GL.iNet Router AI Capabilities: Travel Router vs Flint 2

This document audits the physical and compute capabilities of the GL.iNet router series for hosting the Rust Candle + SmolLM-135M Autonomous Mesh Governor.

## 1. Hardware Matrix

| Feature | Current Travel Router (e.g., Beryl AX / Beryl 7) | Upcoming Flint 2 (GL-MT6000) | Suitability for AI Governor |
| :--- | :--- | :--- | :--- |
| **CPU Architecture** | ARM A53 (Dual-Core @ 1.3GHz) | ARM A53 (Quad-Core @ 2.0GHz) | Both architectures natively support statically compiled `aarch64-unknown-linux-musl` Rust binaries. The Flint 2 will yield ~2-3x faster token generation (approx. 10-15 tk/s). |
| **RAM** | 512 MB DDR4 | 1 GB DDR4 | SmolLM-135M (Q8_0) requires ~140MB RAM. Fits easily on the Travel Router, but the Flint 2's 1GB provides absolute safety against OOM kernel panics during high network loads. |
| **Storage (Flash)** | 256 MB NAND | 8 GB eMMC | The Travel Router requires a plugged-in USB 3.0 flash drive to hold the 75MB model and the Rust binary. The Flint 2 can store the model natively on the 8GB eMMC. |
| **Network Interfaces** | Wi-Fi 6, 2.5G Ethernet, USB 3.0 | Wi-Fi 6, Dual 2.5G Ethernet, USB 3.0 | Both routers natively support OpenWrt packages for Tailscale, WireGuard, and `kmod-bluetooth` (for the TP-Link RF dongle). |

## 2. The OpenWrt "Never-Failing" Diagnostic Array
The Rust Candle server running on the router will have root access to execute the following shell diagnostics to inject into the SmolLM context window:
*   `hciconfig hci0 status` (Bluetooth PAN State)
*   `tailscale status --json` (Layer 3 Mesh State)
*   `ip route` & `ping -I wg0 8.8.8.8` (Gateway Health)

## 3. Anticipated Flint 2 Scaling
When the Flint 2 arrives, its 8GB eMMC and Quad-Core processor will allow us to store the LoRA adapters permanently on-device and run inference fast enough to intercept dropped packets in real-time.
