#!/usr/bin/env bash
# ==============================================================================
# TEST ROBLOX INTENT VALIDATOR
# ==============================================================================
source "$(dirname "$0")/../core/environment.sh"
source "$TOOLKIT_CORE/logger.sh"
source "$TOOLKIT_CORE/validator.sh"

log_info "Kiểm tra Place ID Validator..."
validate_place_id "2753915549" && log_success "[PASS] Blox Fruits Place ID Valid." || exit 1
