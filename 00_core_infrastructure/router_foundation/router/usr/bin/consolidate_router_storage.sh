#!/bin/sh
# ==============================================================================
# Lauburu Mesh: Router Storage Consolidation & VFS Bind Mounts
# Subsystem: 00_core_infrastructure/router_foundation
# Target: GL.iNet GL-BE14000 Gateway Router (OpenWrt / Linux 5.4 aarch64)
#
# Purpose:
#   Unifies distributed SeaweedFS storage (/mnt/seaweedfs, 900 GB pool) and
#   high-speed local flash (/overlay/shared_mesh, 58 GB F2FS) under a single
#   canonical VFS hierarchy:
#     /mnt/lauburu_storage/
#     ├── distributed_dfs/ -> bind mount of /mnt/seaweedfs
#     └── local_flash/     -> bind mount of /overlay/shared_mesh
#
#   Ensures persistence across reboots via /etc/rc.local.
# ==============================================================================

set -e

UNIFIED_ROOT="/mnt/lauburu_storage"
DFS_TARGET="${UNIFIED_ROOT}/distributed_dfs"
FLASH_TARGET="${UNIFIED_ROOT}/local_flash"

SEAWEED_SRC="/mnt/seaweedfs"
FLASH_SRC="/overlay/shared_mesh"
RC_LOCAL="/etc/rc.local"

log_info() {
    echo "[INFO] $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_success() {
    echo "[SUCCESS] $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warn() {
    echo "[WARN] $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo "[ERROR] $(date '+%Y-%m-%d %H:%M:%S') - $1" >&2
}

is_mounted() {
    grep -qs " $1 " /proc/mounts
}

mount_storage() {
    log_info "Initiating router storage consolidation under ${UNIFIED_ROOT}..."

    # Ensure source directories exist and are genuine directories (not symlinks)
    if [ -L "${FLASH_SRC}" ]; then
        log_warn "${FLASH_SRC} is a symlink. Replacing with genuine directory on overlay."
        rm -f "${FLASH_SRC}"
    fi

    if [ ! -d "${FLASH_SRC}" ]; then
        log_info "Creating flash source directory: ${FLASH_SRC}"
        mkdir -p "${FLASH_SRC}"
        chmod 0777 "${FLASH_SRC}" 2>/dev/null || true
    fi

    if [ ! -d "${SEAWEED_SRC}" ]; then
        log_warn "SeaweedFS source directory ${SEAWEED_SRC} does not exist yet."
        mkdir -p "${SEAWEED_SRC}"
    fi

    # Create unified directory structure on native overlay
    mkdir -p "${DFS_TARGET}" "${FLASH_TARGET}"
    chmod 0777 "${UNIFIED_ROOT}" "${DFS_TARGET}" "${FLASH_TARGET}" 2>/dev/null || true

    # 1. Bind mount distributed SeaweedFS
    if is_mounted "${DFS_TARGET}"; then
        log_info "${DFS_TARGET} is already mounted."
    else
        log_info "Bind mounting ${SEAWEED_SRC} -> ${DFS_TARGET}..."
        mount --bind "${SEAWEED_SRC}" "${DFS_TARGET}"
        log_success "Mounted ${DFS_TARGET}"
    fi

    # 2. Bind mount local flash
    if is_mounted "${FLASH_TARGET}"; then
        log_info "${FLASH_TARGET} is already mounted."
    else
        log_info "Bind mounting ${FLASH_SRC} -> ${FLASH_TARGET}..."
        mount --bind "${FLASH_SRC}" "${FLASH_TARGET}"
        log_success "Mounted ${FLASH_TARGET}"
    fi

    # Permissive permissions for guest network access
    chmod 0777 "${UNIFIED_ROOT}" 2>/dev/null || true

    # Persist in /etc/rc.local
    persist_rc_local

    log_success "Router storage consolidation COMPLETE."
}

unmount_storage() {
    log_info "Unmounting unified storage bind mounts..."
    if is_mounted "${DFS_TARGET}"; then
        umount "${DFS_TARGET}" 2>/dev/null || umount -l "${DFS_TARGET}" 2>/dev/null || true
        log_info "Unmounted ${DFS_TARGET}"
    fi

    if is_mounted "${FLASH_TARGET}"; then
        umount "${FLASH_TARGET}" 2>/dev/null || umount -l "${FLASH_TARGET}" 2>/dev/null || true
        log_info "Unmounted ${FLASH_TARGET}"
    fi

    log_success "Unified storage unmounted."
}

status_storage() {
    echo "============================================================"
    echo "Lauburu Router Storage Consolidation Status"
    echo "============================================================"
    echo "Unified Root: ${UNIFIED_ROOT}"
    echo ""
    echo "Mount Points:"
    if is_mounted "${DFS_TARGET}"; then
        echo "  [✓] ${DFS_TARGET} -> Active bind mount"
    else
        echo "  [✗] ${DFS_TARGET} -> NOT mounted"
    fi

    if is_mounted "${FLASH_TARGET}"; then
        echo "  [✓] ${FLASH_TARGET} -> Active bind mount"
    else
        echo "  [✗] ${FLASH_TARGET} -> NOT mounted"
    fi

    echo ""
    echo "Filesystem Usage:"
    df -h "${UNIFIED_ROOT}" "${DFS_TARGET}" "${FLASH_TARGET}" 2>/dev/null || true
    echo "============================================================"
}

persist_rc_local() {
    if [ ! -f "${RC_LOCAL}" ]; then
        log_warn "${RC_LOCAL} not found. Skipping persistence check."
        return 0
    fi

    if grep -q "consolidate_router_storage" "${RC_LOCAL}" 2>/dev/null; then
        log_info "Persistence already registered in ${RC_LOCAL}."
    else
        log_info "Anchoring consolidation script in ${RC_LOCAL} for boot persistence..."
        # Insert execution before 'exit 0'
        sed -i '/exit 0/i \
# Lauburu Unified Storage Consolidation (Generation 32)\
[ -x /usr/bin/consolidate_router_storage.sh ] && /usr/bin/consolidate_router_storage.sh >/dev/null 2>&1\
' "${RC_LOCAL}"
        log_success "Persistence configured in ${RC_LOCAL}."
    fi
}

case "${1:-mount}" in
    mount)
        mount_storage
        ;;
    unmount)
        unmount_storage
        ;;
    remount)
        unmount_storage
        mount_storage
        ;;
    status)
        status_storage
        ;;
    *)
        echo "Usage: $0 {mount|unmount|remount|status}"
        exit 1
        ;;
esac
