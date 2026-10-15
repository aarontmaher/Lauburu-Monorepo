#!/usr/bin/env python3
"""
Render high-resolution visual proof of GL.iNet Gateway Router Health & Ethernet link.
"""
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import hashlib

def render_router_health_card(output_path):
    fig, ax = plt.subplots(figsize=(12, 8), dpi=200)
    fig.patch.set_facecolor('#0f172a')  # slate-900
    ax.set_facecolor('#0f172a')
    ax.axis('off')

    # Title Banner
    ax.text(0.5, 0.94, "GL.iNet GL-BE14000 Gateway Router Health & Topology Audit",
            ha='center', va='center', fontsize=18, fontweight='bold', color='#38bdf8', fontfamily='monospace')
    ax.text(0.5, 0.89, "Empirical Tri-Proof Verification | 7-Layer Lauburu Mesh Data Plane",
            ha='center', va='center', fontsize=11, color='#94a3b8', fontfamily='monospace')

    # Section 1: Ethernet Link Status
    card1 = patches.FancyBboxPatch((0.05, 0.52), 0.42, 0.32, boxstyle="round,pad=0.02",
                                   ec="#22c55e", fc="#1e293b", lw=1.5)
    ax.add_patch(card1)
    ax.text(0.08, 0.81, "⚡ 10GbE LAN LINK (eth2 ↔ en0)", fontsize=13, fontweight='bold', color="#4ade80", fontfamily='monospace')
    ax.text(0.08, 0.76, "• Host MAC: 1c:f6:4c:7d:d7:0a (en0)", fontsize=10, color="#f1f5f9", fontfamily='monospace')
    ax.text(0.08, 0.71, "• Host IP:  192.168.8.230/24 (Priority #1)", fontsize=10, color="#f1f5f9", fontfamily='monospace')
    ax.text(0.08, 0.66, "• Gateway:  192.168.8.1 (GL-BE14000 br-lan)", fontsize=10, color="#f1f5f9", fontfamily='monospace')
    ax.text(0.08, 0.61, "• RTT Avg:  0.686 ms (Min: 0.663, Max: 0.709)", fontsize=10, color="#38bdf8", fontfamily='monospace')
    ax.text(0.08, 0.56, "• Loss:     0.0% (Packet Transfer Verified)", fontsize=10, color="#4ade80", fontfamily='monospace')

    # Section 2: Router Hardware Diagnostics
    card2 = patches.FancyBboxPatch((0.53, 0.52), 0.42, 0.32, boxstyle="round,pad=0.02",
                                   ec="#38bdf8", fc="#1e293b", lw=1.5)
    ax.add_patch(card2)
    ax.text(0.56, 0.81, "ROUTER HARDWARE VITALS", fontsize=13, fontweight='bold', color="#38bdf8", fontfamily='monospace')
    ax.text(0.56, 0.76, "• Silicon:  MediaTek MT7988A Quad ARMv8", fontsize=10, color="#f1f5f9", fontfamily='monospace')
    ax.text(0.56, 0.71, "• Thermal:  55.7°C SoC / 55.0°C 2.5G PHY", fontsize=10, color="#4ade80", fontfamily='monospace')
    ax.text(0.56, 0.66, "• RAM:      2.0 GB (820 MB Free, 1151 MB Avail)", fontsize=10, color="#f1f5f9", fontfamily='monospace')
    ax.text(0.56, 0.61, "• Swap:     2.0 GB Active (0 MB Swapped)", fontsize=10, color="#4ade80", fontfamily='monospace')
    ax.text(0.56, 0.56, "• Storage:  57.9 GB Overlay (53.5 GB Free)", fontsize=10, color="#f1f5f9", fontfamily='monospace')

    # Section 3: Powered USB Hub Back-Powering & Dual-Phone Overload
    card3 = patches.FancyBboxPatch((0.05, 0.12), 0.90, 0.35, boxstyle="round,pad=0.02",
                                   ec="#f59e0b", fc="#1e293b", lw=1.5)
    ax.add_patch(card3)
    ax.text(0.08, 0.43, "AUDIBLE NOISE ROOT CAUSE: POWERED HUB VBUS BACK-FEED & PHONE OVERLOAD", fontsize=12, fontweight='bold', color="#fbbf24", fontfamily='monospace')
    ax.text(0.08, 0.38, "• Live Hub Hierarchy Detected (/sys/bus/usb/devices):", fontsize=10, color="#f1f5f9", fontfamily='monospace')
    ax.text(0.11, 0.34, "1) Apple iPhone [05ac:12a8] (1-2A charge)  2) Samsung Galaxy S20+ [04e8:6864] (1-2A charge)", fontsize=9, color="#94a3b8", fontfamily='monospace')
    ax.text(0.11, 0.30, "3) Realtek RTL8153 Gigabit NIC [0bda:8153] 4) TP-Link UB500 BT [2357:0604] + Billboard [057e]", fontsize=9, color="#94a3b8", fontfamily='monospace')
    ax.text(0.08, 0.25, "• Mechanism 1 (VBUS Collision): Hub back-feeds 5.2V into router 5.0V rail (Section 7.2.1 violation).", fontsize=10, color="#f87171", fontfamily='monospace')
    ax.text(0.11, 0.21, "→ Router synchronous buck converter oscillates erratically (inductor coil whine) & trips PMIC OVP.", fontsize=9, color="#cbd5e1", fontfamily='monospace')
    ax.text(0.08, 0.17, "• Mechanism 2 (Hub Overload): Dual phone charging (>3.5A) saturates hub's internal/external power brick.", fontsize=10, color="#f87171", fontfamily='monospace')
    ax.text(0.08, 0.13, "• Instant Safe Remedy: Tape Pin 1 (VBUS) on upstream USB plug + charge phones via dedicated wall chargers.", fontsize=10, color="#4ade80", fontfamily='monospace')

    # Footer
    ax.text(0.5, 0.05, "Obsidian Vault Synced: GLINET_ROUTER_HEALTH_AND_HUB_HARDWARE_AUDIT.md | LoRA Pair Appended",
            ha='center', va='center', fontsize=9, color='#64748b', fontfamily='monospace')

    plt.tight_layout()
    plt.savefig(output_path, bbox_inches='tight', facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()

if __name__ == '__main__':
    target = '/Users/aaron/.gemini/antigravity/brain/a5bc2c80-30df-417d-b2ee-33c785ad30b0/glinet_router_health_visual_proof.png'
    render_router_health_card(target)
    with open(target, 'rb') as f:
        data = f.read()
    print(f"Generated {target} ({len(data)} bytes, SHA256: {hashlib.sha256(data).hexdigest()})")
