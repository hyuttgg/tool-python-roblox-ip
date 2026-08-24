#!/usr/bin/env bash
# ==============================================================================
# ROBLOX FULL AUTO PIPELINE (1-CHẠM)
# ==============================================================================
source "$(dirname "$0")/../../core/environment.sh"
source "$TOOLKIT_CORE/logger.sh"

log_info "Kích hoạt Full Auto Pipeline (Quét + Sort IP + Autoexec + Launch + Watchdog)..."

if [ -f "$TOOLKIT_ROOT/controller.py" ]; then
    $PYTHON_CMD "$TOOLKIT_ROOT/controller.py" --pipeline
else
    log_error "Không tìm thấy controller.py"
fi
