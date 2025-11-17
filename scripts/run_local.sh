#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ -f "config/settings.yaml" ]; then
  export APP_SETTINGS_FILE="config/settings.yaml"
fi

python -m src.main
