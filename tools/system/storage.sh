#!/usr/bin/env bash
# ==============================================================================
# STORAGE & SDCARD VIEWER
# ==============================================================================
source "$(dirname "$0")/../../core/environment.sh"

echo "=== DUNG LƯỢNG BỘ NHỚ ==="
df -h 2>/dev/null | grep -E "Filesystem|/data|/sdcard|/storage" || df -h
