#!/usr/bin/env bash
# ==============================================================================
# VALIDATOR & SANITIZER
# ==============================================================================

validate_place_id() {
    local pid="$1"
    if [[ "$pid" =~ ^[0-9]{4,15}$ ]]; then
        return 0
    fi
    return 1
}

validate_ip_address() {
    local ip="$1"
    if [[ "$ip" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]; then
        return 0
    fi
    return 1
}
