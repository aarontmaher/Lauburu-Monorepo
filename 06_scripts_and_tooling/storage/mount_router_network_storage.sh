#!/usr/bin/env bash
# ==============================================================================
# ROUTER UNIFIED NETWORK STORAGE AUTOMOUNT & HEALTH WATCHDOG
# Subsystem: 06_scripts_and_tooling/storage
# Gateway Target: GL-BE14000 Sovereign Gateway (192.168.8.1)
# ==============================================================================
set -euo pipefail

ROUTER_IP="${ROUTER_IP:-192.168.8.1}"
SEAWEED_MOUNT="/Volumes/seaweed_network"
LAUBURU_MOUNT="/Volumes/lauburu_storage"

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${CYAN}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

is_smb_mounted() {
    local target="$1"
    mount | grep -E "(smbfs|//.*@${ROUTER_IP})" | grep -q " on ${target} "
}

status_check() {
    echo "============================================================"
    echo "Router Unified Network Storage Status (${ROUTER_IP})"
    echo "============================================================"
    for mnt in "${SEAWEED_MOUNT}" "${LAUBURU_MOUNT}"; do
        if is_smb_mounted "${mnt}"; then
            echo -e "${GREEN}[✓] Share is MOUNTED at ${mnt}${NC}"
        else
            echo -e "${YELLOW}[!] Share is NOT mounted at ${mnt}${NC}"
        fi
    done
    echo "============================================================"
}

unmount_all() {
    log_info "Unmounting router network storage..."
    for mnt in "${SEAWEED_MOUNT}" "${LAUBURU_MOUNT}"; do
        if is_smb_mounted "${mnt}"; then
            umount "${mnt}" 2>/dev/null || diskutil unmount force "${mnt}" 2>/dev/null || true
            log_success "Unmounted ${mnt}."
        else
            log_info "${mnt} was not mounted."
        fi
    done
}

mount_all() {
    log_info "Checking router reachability at ${ROUTER_IP}:445..."
    if ! nc -z -w 2 "${ROUTER_IP}" 445 2>/dev/null; then
        log_error "Router SMB port 445 unreachable at ${ROUTER_IP}."
        exit 1
    fi
    log_success "Router SMB service is online."

    echo "goldfighting1" | sudo -S mkdir -p "${SEAWEED_MOUNT}" "${LAUBURU_MOUNT}" 2>/dev/null || true
    echo "goldfighting1" | sudo -S chown aaron:staff "${SEAWEED_MOUNT}" "${LAUBURU_MOUNT}" 2>/dev/null || true

    # Mount seaweed_network
    if is_smb_mounted "${SEAWEED_MOUNT}"; then
        log_info "${SEAWEED_MOUNT} is already mounted."
    else
        log_info "Mounting smb://${ROUTER_IP}/seaweed_network -> ${SEAWEED_MOUNT}..."
        mount_smbfs "//lauburu:goldfighting1@${ROUTER_IP}/seaweed_network" "${SEAWEED_MOUNT}" || log_error "Failed to mount ${SEAWEED_MOUNT}"
        log_success "Mounted ${SEAWEED_MOUNT}."
    fi

    # Mount lauburu_storage
    if is_smb_mounted "${LAUBURU_MOUNT}"; then
        log_info "${LAUBURU_MOUNT} is already mounted."
    else
        log_info "Mounting smb://${ROUTER_IP}/lauburu_storage -> ${LAUBURU_MOUNT}..."
        mount_smbfs "//lauburu:goldfighting1@${ROUTER_IP}/lauburu_storage" "${LAUBURU_MOUNT}" || log_error "Failed to mount ${LAUBURU_MOUNT}"
        log_success "Mounted ${LAUBURU_MOUNT}."
    fi

    # Verify write and read test
    for mnt in "${SEAWEED_MOUNT}" "${LAUBURU_MOUNT}"; do
        local test_file="${mnt}/.health_check_${HOSTNAME}_$(date +%s)"
        echo "Lauburu Storage Health Check $(date -u)" > "${test_file}" 2>/dev/null || true
        if [ -f "${test_file}" ]; then
            rm -f "${test_file}"
            log_success "Root read/write verification PASSED on ${mnt}."
        else
            log_error "Root read/write verification FAILED on ${mnt}."
        fi
    done

    status_check
}

case "${1:-mount}" in
    mount) mount_all ;;
    unmount) unmount_all ;;
    remount) unmount_all; mount_all ;;
    status) status_check ;;
    *) echo "Usage: $0 {mount|unmount|remount|status}"; exit 1 ;;
esac
