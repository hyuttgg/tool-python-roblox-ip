#!/usr/bin/env bash
# ==============================================================================
# MENU COMPONENT BUILDER
# ==============================================================================

print_menu_option() {
    local num="$1"
    local icon="$2"
    local desc="$3"
    echo -e "  ${C_BOLD:-}[${C_GREEN:-}${num}${C_RESET:-}${C_BOLD:-}]${C_RESET:-} ${icon} ${desc}"
}

print_menu_section() {
    local section_title="$1"
    echo -e "\n  ${C_BOLD:-}${C_CYAN:-}[ ${section_title} ]${C_RESET:-}"
}
