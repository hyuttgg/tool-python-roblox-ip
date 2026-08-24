#!/usr/bin/env bash
# ==============================================================================
# TERMINAL CONTROL LIBRARY
# ==============================================================================

clear_screen() {
    clear 2>/dev/null || printf "\033c"
}

hide_cursor() {
    printf "\033[?25l"
}

show_cursor() {
    printf "\033[?25h"
}
