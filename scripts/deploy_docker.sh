#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

IMAGE_NAME="meditron"

docker build -t "${IMAGE_NAME}" .
docker run --rm -it -p 8050:8050 "${IMAGE_NAME}"
