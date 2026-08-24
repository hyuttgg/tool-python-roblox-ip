#!/usr/bin/env bash
# ==============================================================================
# UI & BOX DRAWING LIBRARY
# ==============================================================================

draw_line() {
    local width="${1:-60}"
    local char="${2:-═}"
    printf '%*s\n' "$width" '' | tr ' ' "$char"
}

draw_header() {
    local title="$1"
    echo -e "${C_CYAN:-}$(draw_line 70 '═')${C_RESET:-}"
    echo -e "${C_BOLD:-}${C_GREEN:-}   ⚡ ${title} ⚡${C_RESET:-}"
    echo -e "${C_CYAN:-}$(draw_line 70 '═')${C_RESET:-}"
}

draw_box() {
    local text="$1"
    echo -e "┌$(draw_line 68 '─')┐"
    echo -e "│  ${text}"
    echo -e "└$(draw_line 68 '─')┘"
}
