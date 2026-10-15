#!/usr/bin/env bash
# =============================================================================
# Lauburu Sovereign Mesh: Disk Emergency Compressor
# =============================================================================
# Subsystem: 06_scripts_and_tooling/maintenance/disk_emergency_compressor.sh
# Version:   1.0.0-EMERGENCY-COMPRESSOR
#
# Triggers when disk free < 10 GB. Compresses dormant datasets (>7 days
# untouched) with gzip, purges __pycache__, .pytest_cache, and stale logs.
# Rule #0: Only operates on data files, never on source code or adapters.
# Rule #4: Never touches 01_apps/ production code or 12_continuous_lora_evolution/adapters/
# =============================================================================
set -euo pipefail

LORA_DIR="/Volumes/Lauburu-Monorepo/04_data_and_memory/data"
REPO_ROOT="/Volumes/Lauburu-Monorepo"
LOG_DIR="$REPO_ROOT/logs"
DRY_RUN="${DRY_RUN:-0}"
DISK_THRESHOLD_GB="${DISK_THRESHOLD_GB:-10}"

# ANSI
RED='\033[0;31m'; YELLOW='\033[1;33m'; GREEN='\033[0;32m'; NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC}  $(date '+%H:%M:%S') $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $(date '+%H:%M:%S') $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $(date '+%H:%M:%S') $*"; }

bytes_freed=0
files_compressed=0
files_deleted=0

# ── Measure disk ─────────────────────────────────────────────────────────────
get_disk_free_gb() {
    df -k /Users/aaron | awk 'NR==2 {printf "%.2f", $4/1048576}'
}

disk_free=$(get_disk_free_gb)
log_info "Disk free: ${disk_free} GB (threshold: ${DISK_THRESHOLD_GB} GB)"

if (( $(echo "$disk_free > $DISK_THRESHOLD_GB" | bc -l) )); then
    log_info "Disk headroom OK (${disk_free} GB > ${DISK_THRESHOLD_GB} GB). No emergency action needed."
    exit 0
fi

log_warn "🔴 DISK EMERGENCY: ${disk_free} GB free — below ${DISK_THRESHOLD_GB} GB threshold. Initiating compression..."

# ── Step 1: Purge __pycache__ and .pytest_cache ───────────────────────────────
log_info "Step 1: Purging __pycache__ and .pytest_cache..."
if [ "$DRY_RUN" = "0" ]; then
    before_pycache=$(df -k /Users/aaron | awk 'NR==2 {print $4}')
    find "$REPO_ROOT" -type d \( -name "__pycache__" -o -name ".pytest_cache" -o -name ".ruff_cache" \) \
         -exec rm -rf {} + 2>/dev/null || true
    find "$LORA_DIR" -type d \( -name "__pycache__" \) \
         -exec rm -rf {} + 2>/dev/null || true
    after_pycache=$(df -k /Users/aaron | awk 'NR==2 {print $4}')
    freed_kb=$(( after_pycache - before_pycache ))
    bytes_freed=$(( bytes_freed + freed_kb * 1024 ))
    log_info "  Freed $(echo "scale=1; $freed_kb/1024" | bc) MB from caches"
else
    log_info "  [DRY_RUN] Would purge __pycache__ / .pytest_cache"
fi

# ── Step 2: Purge oversized log files > 100 MB ───────────────────────────────
log_info "Step 2: Truncating oversized log files > 100 MB..."
while IFS= read -r logfile; do
    size_mb=$(du -m "$logfile" | cut -f1)
    log_warn "  Found large log: $logfile (${size_mb} MB)"
    if [ "$DRY_RUN" = "0" ]; then
        # Keep last 10,000 lines
        tail -n 10000 "$logfile" > "${logfile}.tmp" && mv "${logfile}.tmp" "$logfile"
        (( files_deleted++ )) || true
        log_info "  Truncated $logfile to last 10,000 lines"
    else
        log_info "  [DRY_RUN] Would truncate $logfile"
    fi
done < <(find "$LOG_DIR" -maxdepth 2 -name "*.log" -size +100M 2>/dev/null || true)

# ── Step 3: Compress dormant LoRA datasets (>7 days, >5 MB) ──────────────────
# SAFETY RULES:
#  - Never compress files modified in the last 7 days
#  - Never compress files with "continuous" in name (actively written)
#  - Never compress adapters (.safetensors, .bin)
#  - Never compress active training data dirs
log_info "Step 3: Compressing dormant datasets (>7 days old, >5 MB, non-active)..."

ACTIVE_PATTERNS=(
    "continuous_lora_dataset"
    "truth_audit_debate"
    "proven_accuracy_vla_dataset"
    "generational_handoff_opinions"
    "nomad_autonomous_actions"
    "showrunner_continuous_lora"
    "neo_ecommerce_continuous_lora"
    "continuous_free_ai"
    "math_training_dataset"
    "ancestral_tool_memory"
    "bluetooth_serial_terminal_lora"
)

is_active() {
    local f="$1"
    local base
    base=$(basename "$f")
    for pat in "${ACTIVE_PATTERNS[@]}"; do
        if [[ "$base" == *"$pat"* ]]; then
            return 0
        fi
    done
    return 1
}

compress_count=0
while IFS= read -r jsonlfile; do
    # Skip if active pattern
    if is_active "$jsonlfile"; then
        continue
    fi
    # Skip if already compressed
    if [ -f "${jsonlfile}.gz" ]; then
        continue
    fi
    size_mb=$(du -m "$jsonlfile" | cut -f1)
    log_warn "  Compressing dormant: $(basename $jsonlfile) (${size_mb} MB)"
    if [ "$DRY_RUN" = "0" ]; then
        gzip -9 "$jsonlfile" && (( compress_count++ )) || log_error "  Failed to compress $jsonlfile"
        (( files_compressed++ )) || true
    else
        log_info "  [DRY_RUN] Would gzip $jsonlfile (${size_mb} MB)"
        (( compress_count++ )) || true
    fi
done < <(find "$LORA_DIR" -maxdepth 1 -name "*.jsonl" -size +5M -mtime +7 2>/dev/null | head -30 || true)

log_info "  Compressed ${compress_count} dormant dataset files"

# ── Step 4: Remove empty / zero-byte files ───────────────────────────────────
log_info "Step 4: Removing zero-byte dataset files..."
if [ "$DRY_RUN" = "0" ]; then
    find "$LORA_DIR" -maxdepth 1 -name "*.jsonl" -size 0 -delete 2>/dev/null || true
    find "$LORA_DIR" -maxdepth 1 -name "*.json" -size 0 -delete 2>/dev/null || true
else
    count=$(find "$LORA_DIR" -maxdepth 1 -name "*.jsonl" -size 0 2>/dev/null | wc -l)
    log_info "  [DRY_RUN] Would remove $count zero-byte files"
fi

# ── Final report ─────────────────────────────────────────────────────────────
disk_free_after=$(get_disk_free_gb)
log_info "======================================================"
log_info "✅ DISK EMERGENCY COMPRESSOR COMPLETE"
log_info "   Before: ${disk_free} GB free"
log_info "   After:  ${disk_free_after} GB free"
log_info "   Files compressed: ${files_compressed}"
log_info "   Files truncated: ${files_deleted}"
log_info "   DRY_RUN: ${DRY_RUN}"
log_info "======================================================"

# Write status to Obsidian
STATUS_FILE="$REPO_ROOT/obsidian_vault/06_MAINTENANCE/DISK_EMERGENCY_COMPRESSOR_LOG.md"
mkdir -p "$(dirname "$STATUS_FILE")"
cat >> "$STATUS_FILE" << EOF

---
## Run: $(date '+%Y-%m-%d %H:%M:%S')
- **Before:** ${disk_free} GB free
- **After:** ${disk_free_after} GB free
- **Files Compressed:** ${files_compressed}
- **Logs Truncated:** ${files_deleted}
- **DRY_RUN:** ${DRY_RUN}
EOF
