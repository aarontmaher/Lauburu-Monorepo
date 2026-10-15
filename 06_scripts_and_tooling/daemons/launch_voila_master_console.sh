#!/bin/bash
# ==============================================================================
# 🚀 Lauburu Voilà Master Console Daemon (:8890)
# ==============================================================================
set -euo pipefail

VENV_DIR="/Volumes/Lauburu-Monorepo/01_apps/notebooks/.venv"
NOTEBOOK_PATH="/Volumes/Lauburu-Monorepo/01_apps/notebooks/00_lauburu_global_master_project.ipynb"
WORKDIR="/Volumes/Lauburu-Monorepo/01_apps/notebooks"

cd "$WORKDIR"
exec "$VENV_DIR/bin/voila" \
  "$NOTEBOOK_PATH" \
  --port=8890 \
  --no-browser \
  --theme=dark \
  --VoilaConfiguration.show_tracebacks=True \
  --VoilaConfiguration.token='' \
  --VoilaConfiguration.disable_check_xsrf=True
