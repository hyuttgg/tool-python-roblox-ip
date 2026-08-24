#!/usr/bin/env bash
# ==============================================================================
# CONFIRMATION DIALOG LIBRARY
# ==============================================================================

confirm_action() {
    local prompt_msg="$1"
    local default_choice="${2:-Y}"
    read -rp "$(echo -e "${C_YELLOW:-}${prompt_msg} [Y/n]:${C_RESET:-} ")" choice
    choice="${choice:-$default_choice}"
    case "$choice" in
        [yY][eE][sS]|[yY]) return 0 ;;
        *) return 1 ;;
    esac
}
