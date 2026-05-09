#!/usr/bin/env bash
# Local automated screenshot audit entrypoint.
# Public-safe only: runs Maestro UI capture and writes local artifacts.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! command -v maestro >/dev/null 2>&1; then
  cat >&2 <<'EOF'
Maestro is not installed.

Install locally:
  brew tap mobile-dev-inc/tap
  brew install maestro
  maestro --version

Then boot an iOS Simulator or Android emulator with Lauburu installed and run:
  audit-system/run-audit.sh --platform ios --suite ios
  audit-system/run-audit.sh --platform android

This audit is simulator/emulator evidence only and cannot clear installed-device gates.
EOF
  exit 1
fi

exec npm --prefix "$ROOT" run audit:maestro -- "$@"
