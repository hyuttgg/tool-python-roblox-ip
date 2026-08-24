#!/usr/bin/env bash
# ==============================================================================
# TEST CORE ENVIRONMENT
# ==============================================================================
source "$(dirname "$0")/../core/environment.sh"
source "$TOOLKIT_CORE/logger.sh"

log_info "Kiểm tra cấu hình Core Toolkit..."
if [ -n "$TOOLKIT_ROOT" ] && [ -d "$TOOLKIT_ROOT" ]; then
    log_success "[PASS] Core environment root: $TOOLKIT_ROOT"
else
    log_error "[FAIL] Core environment root not found"
    exit 1
fi
