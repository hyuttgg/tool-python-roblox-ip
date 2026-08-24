#!/usr/bin/env bash
# ==============================================================================
# UGPHONE CLOUD PHONE BRIDGING UTILITY
# ==============================================================================
source "$(dirname "$0")/../../core/environment.sh"
source "$TOOLKIT_CORE/logger.sh"

log_info "Kết nối và đồng bộ UGPhone Cloud Phone Bridge..."
$PYTHON_CMD -c "from devices.ugphone_bridge import UGPhoneBridge; b = UGPhoneBridge(); devs = b.refresh_devices(); print(f'Thiết bị UGPhone: {devs}')"
