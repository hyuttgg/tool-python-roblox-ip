#!/usr/bin/env bash
# ==============================================================================
# PROGRESS BAR LIBRARY
# ==============================================================================

draw_progress_bar() {
    local percent=$1
    local width=30
    local filled=$(( percent * width / 100 ))
    local empty=$(( width - filled ))
    printf "\r[${C_GREEN:-}"
    printf "%${filled}s" | tr ' ' '█'
    printf "${C_GRAY:-}"
    printf "%${empty}s" | tr ' ' '░'
    printf "${C_RESET:-}] %3d%%" "$percent"
}
