#!/bin/bash
# ==============================================================================
# 🚀 LAUBURU UNIFIED TUI CLI SELECTOR
# Cross-Platform Cluster Launcher: Mac Mini M4 | Linux Laptop | Pixel 10 Pro
# ==============================================================================

set -e

# Detect host environment
detect_host() {
    local uname_s
    uname_s="$(uname -s 2>/dev/null || echo "Unknown")"
    if [ "$uname_s" = "Darwin" ]; then
        echo "mac"
    elif grep -qi "android" /proc/version 2>/dev/null || [ -d "/data/data/com.termux" ]; then
        echo "pixel"
    elif [ "$uname_s" = "Linux" ]; then
        local hostname_str
        hostname_str="$(hostname 2>/dev/null || echo "")"
        if echo "$hostname_str" | grep -qiE "pixel|android"; then
            echo "pixel"
        else
            echo "linux"
        fi
    else
        echo "unknown"
    fi
}

CURRENT_HOST="$(detect_host)"

# Colors
if [ -t 1 ]; then
    BOLD="\033[1m"
    CYAN="\033[36m"
    GREEN="\033[32m"
    YELLOW="\033[33m"
    BLUE="\033[34m"
    MAGENTA="\033[35m"
    RED="\033[31m"
    RESET="\033[0m"
else
    BOLD=""
    CYAN=""
    GREEN=""
    YELLOW=""
    BLUE=""
    MAGENTA=""
    RED=""
    RESET=""
fi

show_banner() {
    clear 2>/dev/null || true
    echo -e "${BOLD}${CYAN}╔════════════════════════════════════════════════════════════════╗${RESET}"
    echo -e "${BOLD}${CYAN}║             🌿 LAUBURU PERSONAL COMPUTE & SWARM 🌿             ║${RESET}"
    echo -e "${BOLD}${CYAN}║         💰 Paying by Computing™ Decentralized Platform         ║${RESET}"
    echo -e "${BOLD}${CYAN}╚════════════════════════════════════════════════════════════════╝${RESET}"
    
    local host_label=""
    case "$CURRENT_HOST" in
        "mac")   host_label="${GREEN}My Mac Workstation (Apple Silicon)${RESET}" ;;
        "linux") host_label="${GREEN}My Linux Workstation (AMD / x86_64)${RESET}" ;;
        "pixel") host_label="${GREEN}My Mobile Edge Device (Android Termux)${RESET}" ;;
        *)       host_label="${YELLOW}Local Terminal (${CURRENT_HOST})${RESET}" ;;
    esac
    echo -e "${BOLD}Local Device:${RESET}    ${host_label}"
    echo -e "${BOLD}Paying by Comp:${RESET}  ${GREEN}ACTIVE${RESET} ($29/mo Value 100% Subsidized via Compute Contribution)"
    echo -e "${BOLD}Tenant Enclave:${RESET}  ${MAGENTA}Strict Privacy Active${RESET} (Only your personal paired devices visible)"
    echo -e "${CYAN}────────────────────────────────────────────────────────────────${RESET}"
}

print_menu() {
    show_banner
    echo -e "${BOLD}Personal Device & Swarm Control Options:${RESET}"
    echo ""
    echo -e "  ${BOLD}${GREEN}[1]${RESET} ${BOLD}My Device Cockpit & Paying-by-Computing (Default)${RESET}"
    echo -e "      Local hardware introspection, token contribution & credit ledger"
    echo ""
    echo -e "  ${BOLD}${CYAN}[2]${RESET} ${BOLD}My Personal Swarm (Paired Companion Devices)${RESET}"
    echo -e "      Direct P2P link to your personal phone/workstations (Tenant-Isolated)"
    echo ""
    echo -e "  ${BOLD}${YELLOW}[3]${RESET} ${BOLD}Global Mesh Telemetry (Diagnostics & Sharding Matrix)${RESET}"
    echo -e "      Full P2P distributed sharding and network latency diagnostics"
    echo ""
    echo -e "  ${BOLD}${BLUE}[4]${RESET} ${BOLD}Sentinel Watchdog & Self-Healing Stream${RESET}"
    echo -e "      Local real-time daemon sentinel & socket monitor"
    echo ""
    echo -e "  ${BOLD}${RED}[q]${RESET} Quit"
    echo -e "${CYAN}────────────────────────────────────────────────────────────────${RESET}"
}

launch_local_lauburu() {
    echo -e "${GREEN}==> Launching native Personal Device Cockpit...${RESET}"
    local lens_bin="/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/rust_network_analyzer/target/release/lauburu_network_lens"
    if [ -x "$lens_bin" ]; then
        exec "$lens_bin" "$@"
    elif command -v lauburu-tui >/dev/null 2>&1; then
        exec lauburu-tui "$@"
    elif [ -f "$HOME/.cargo/bin/lauburu-tui" ]; then
        exec "$HOME/.cargo/bin/lauburu-tui" "$@"
    elif [ -f "$HOME/bin/lauburu-tui" ]; then
        exec "$HOME/bin/lauburu-tui" "$@"
    elif [ -f "/usr/local/bin/lauburu-tui" ]; then
        exec /usr/local/bin/lauburu-tui "$@"
    elif [ -f "/data/data/com.termux/files/usr/bin/lauburu-tui" ]; then
        exec /data/data/com.termux/files/usr/bin/lauburu-tui "$@"
    else
        echo -e "${RED}Error: lauburu-tui binary not found in PATH or standard locations.${RESET}"
        exit 1
    fi
}

launch_remote_mac() {
    echo -e "${CYAN}==> Connecting to Aaron's Mac Mini M4 Pro...${RESET}"
    exec ssh -t mac "lauburu-tui"
}

launch_remote_linux() {
    echo -e "${CYAN}==> Connecting to Linux Laptop Head Node...${RESET}"
    exec ssh -t linux "lauburu-tui"
}

launch_remote_pixel() {
    echo -e "${CYAN}==> Connecting to Pixel 10 Pro XL...${RESET}"
    exec ssh -t pixel "lauburu-tui"
}

launch_global_mesh() {
    echo -e "${YELLOW}==> Launching Global Mesh TUI...${RESET}"
    if command -v global_mesh_tui >/dev/null 2>&1; then
        exec global_mesh_tui "$@"
    elif [ -f "$HOME/global_mesh_tui" ]; then
        exec "$HOME/global_mesh_tui" "$@"
    elif [ -f "/usr/local/bin/global_mesh_tui" ]; then
        exec /usr/local/bin/global_mesh_tui "$@"
    else
        echo -e "${YELLOW}global_mesh_tui not installed locally. Connecting to Pixel host...${RESET}"
        exec ssh -t pixel "global_mesh_tui"
    fi
}

launch_canonical_tui() {
    echo -e "${YELLOW}==> Launching Canonical Textual TUI...${RESET}"
    if [ -f "$HOME/start_canonical_tui.sh" ]; then
        exec "$HOME/start_canonical_tui.sh" "$@"
    elif [ -f "$HOME/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/tui/canonical_tui.py" ]; then
        cd "$HOME/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port"
        exec python3 -m textual run --dev tui/canonical_tui.py
    elif [ -f "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/tui/canonical_tui.py" ]; then
        cd "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port"
        exec python3 -m textual run --dev tui/canonical_tui.py
    else
        echo -e "${YELLOW}Connecting to Mac Mini for Canonical Textual TUI...${RESET}"
        exec ssh -t mac "cd ~/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port && python3 -m textual run --dev tui/canonical_tui.py"
    fi
}

launch_sentinel_stream() {
    echo -e "${BLUE}==> Attaching to Cluster Sentinel & Health Stream (:8181)...${RESET}"
    echo -e "Press Ctrl+C to stop.\n"
    local proxy_url=""
    if curl -s --max-time 1 http://127.0.0.1:8181/health >/dev/null 2>&1; then
        proxy_url="http://127.0.0.1:8181/health"
    elif curl -s --max-time 1 http://100.101.39.98:8181/health >/dev/null 2>&1; then
        proxy_url="http://100.101.39.98:8181/health"
    else
        proxy_url="http://192.168.8.224:8181/health"
    fi

    while true; do
        clear 2>/dev/null || true
        echo -e "${BOLD}${BLUE}=== Cluster Sentinel Live Watchdog [${proxy_url}] ===${RESET}"
        echo -e "Timestamp: $(date)\n"
        curl -s --max-time 2 "$proxy_url" | (python3 -m json.tool 2>/dev/null || cat) || echo -e "${RED}Proxy unreachable${RESET}"
        echo ""
        echo -e "${CYAN}Refreshing every 2 seconds... (Ctrl+C to return)${RESET}"
        sleep 2
    done
}

show_help() {
    echo "Usage: tui [COMMAND|OPTION]"
    echo ""
    echo "Lauburu Multi-Device Mesh TUI Launcher"
    echo ""
    echo "Commands:"
    echo "  tui                    Open interactive menu selector"
    echo "  tui 1, local, lauburu  Launch local Lauburu Rust Ratatui TUI"
    echo "  tui 2, mac             Connect to Lauburu Rust TUI on Aaron's Mac Mini"
    echo "  tui 3, linux           Connect to Lauburu Rust TUI on Linux Laptop Head Node"
    echo "  tui 4, pixel           Connect to Lauburu Rust TUI on Pixel 10 Pro XL"
    echo "  tui 5, global          Launch Global Mesh TUI (Go LibP2P)"
    echo "  tui 6, canonical       Launch Canonical Textual TUI"
    echo "  tui 7, sentinel        Stream live cluster health & route failsafe"
    echo "  tui -l, --list         List available options and exit"
    echo "  tui -h, --help         Show this help message"
    echo ""
}

# Handle direct arguments
case "${1:-}" in
    1|local|lauburu)
        shift || true
        launch_local_lauburu "$@"
        ;;
    2|mac|macmini)
        launch_remote_mac
        ;;
    3|linux|laptop)
        launch_remote_linux
        ;;
    4|pixel|phone)
        launch_remote_pixel
        ;;
    5|global|mesh)
        shift || true
        launch_global_mesh "$@"
        ;;
    6|canonical|textual)
        shift || true
        launch_canonical_tui "$@"
        ;;
    7|sentinel|health|stream)
        launch_sentinel_stream
        ;;
    -l|--list|list)
        echo "1: My Device Cockpit & Paying-by-Computing (Default)"
        echo "2: My Personal Swarm (Companion Devices)"
        echo "3: Global Mesh Telemetry & Diagnostics"
        echo "4: Sentinel Watchdog & Socket Stream"
        exit 0
        ;;
    -h|--help|help)
        show_help
        exit 0
        ;;
    "")
        # Default: Immediately launch native personal cockpit!
        launch_local_lauburu "$@"
        ;;
    -m|--menu|menu)
        # Interactive Menu Mode
        ;;
    *)
        echo -e "${RED}Unknown option: $1${RESET}"
        show_help
        exit 1
        ;;
esac

# Interactive loop (only reached via --menu)
while true; do
    print_menu
    read -r -p "Enter choice [1-4, q]: " choice
    case "$choice" in
        1) launch_local_lauburu ;;
        2) launch_remote_pixel ;;
        3) launch_global_mesh ;;
        4) launch_sentinel_stream ;;
        q|Q|exit)
            echo -e "\n${GREEN}Exiting Lauburu Personal Compute Hub. Goodbye!${RESET}"
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid selection '$choice'. Press Enter to retry...${RESET}"
            read -r _
            ;;
    esac
done
