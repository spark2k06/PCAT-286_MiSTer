#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
# The long case 11 includes the original 64 KiB clear and screen header.
# ROM buffer fixtures select entries; no on-disk BIOS is modified.
export AT_LANDMARK_CASES="${AT_LANDMARK_CASES:-13 14 11 12}"
export PCAT_BUILD_DIR="${PCAT_BUILD_DIR:-$root/build/at-landmark-ram}"
exec bash "$root/scripts/test_at_landmark_dma.sh"
