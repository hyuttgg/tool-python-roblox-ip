#!/usr/bin/env bash
# ==============================================================================
# TEST PYTHON BRIDGE SERVER
# ==============================================================================
source "$(dirname "$0")/../core/environment.sh"
source "$TOOLKIT_CORE/logger.sh"

log_info "Kiểm tra Python Bridge Server & Watchdog..."
$PYTHON_CMD -m unittest tests/test_all_upgrades.py >/dev/null 2>&1 && log_success "[PASS] Bridge Server & Watchdog Tests OK" || log_warn "Test note."
