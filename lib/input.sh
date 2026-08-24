#!/usr/bin/env bash
# ==============================================================================
# SAFE INPUT LIBRARY
# ==============================================================================

safe_input() {
    local prompt_text="$1"
    local default_val="$2"
    local input_val=""
    read -rp "$(echo -e "${C_YELLOW:-}${prompt_text}${C_RESET:-} ")" input_val
    if [ -z "$input_val" ]; then
        echo "$default_val"
    else
        echo "$input_val"
    fi
}
