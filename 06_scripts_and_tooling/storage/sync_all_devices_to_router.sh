#!/usr/bin/env bash
# ==============================================================================
# LAUBURU ALL-DEVICE STORAGE SYNC OVER ROUTER
# Subsystem: 06_scripts_and_tooling/storage
# Gateway Target: GL-BE14000 Sovereign Gateway (192.168.8.1)
# Synchronizes all mesh datasets and memory into the Router's Network Storage
# ==============================================================================
set -euo pipefail

ROUTER_IP="${ROUTER_IP:-192.168.8.1}"
ROUTER_STORAGE="${HOME}/Network_Storage/Router_SeaweedFS"
SOURCE_REPO="/Volumes/Lauburu-Monorepo"
LORA_DATASETS="/Volumes/Lauburu-Monorepo/04_data_and_memory/data"

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${CYAN}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

ensure_mount() {
    if ! mount | grep -q "${ROUTER_STORAGE}"; then
        log_info "Mounting router storage at ${ROUTER_STORAGE}..."
        mkdir -p "${ROUTER_STORAGE}"
        mount_smbfs "//guest:@${ROUTER_IP}/seaweedfs" "${ROUTER_STORAGE}"
    fi
    log_success "Router storage confirmed mounted."
}

sync_once() {
    ensure_mount

    local dest_lora="${ROUTER_STORAGE}/lora_datasets"
    local dest_vault="${ROUTER_STORAGE}/obsidian_vault"
    local dest_memory="${ROUTER_STORAGE}/04_data_and_memory"

    mkdir -p "${dest_lora}" "${dest_vault}" "${dest_memory}"

    log_info "Syncing LoRA Datasets to router storage..."
    rsync -avu --update \
        --exclude=".*" \
        --exclude="__pycache__" \
        "${LORA_DATASETS}/" "${dest_lora}/" || log_warn "LoRA sync had non-fatal warnings"

    log_info "Syncing Obsidian Vault knowledge core to router storage..."
    rsync -avu --update \
        --exclude=".obsidian/workspace*" \
        --exclude=".*" \
        "${SOURCE_REPO}/obsidian_vault/" "${dest_vault}/" || log_warn "Vault sync had non-fatal warnings"

    log_info "Syncing 04_data_and_memory to router storage..."
    rsync -avu --update \
        --exclude=".*" \
        --exclude="__pycache__" \
        "${SOURCE_REPO}/04_data_and_memory/" "${dest_memory}/" || log_warn "Memory sync had non-fatal warnings"

    log_success "Mesh storage synchronization cycle complete."
}

daemon_loop() {
    log_info "Starting 24/7 continuous storage sync daemon (Interval: 300s)..."
    while true; do
        sync_once || log_error "Sync cycle failed, retrying in 60s..."
        sleep 300
    done
}

case "${1:-once}" in
    once)
        sync_once
        ;;
    daemon)
        daemon_loop
        ;;
    *)
        echo "Usage: $0 {once|daemon}"
        exit 1
        ;;
esac
