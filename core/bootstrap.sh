#!/usr/bin/env bash
# ==============================================================================
# BOOTSTRAP WORKSPACE INITIALIZER
# ==============================================================================

init_workspace() {
    local root="${TOOLKIT_ROOT:-$(pwd)}"
    
    mkdir -p "$root/data" 2>/dev/null
    mkdir -p "$root/data/generated_lua" 2>/dev/null
    mkdir -p "$root/logs" 2>/dev/null
    mkdir -p "$root/config" 2>/dev/null
    mkdir -p "$root/bin" 2>/dev/null

    chmod -R 755 "$root/bin" 2>/dev/null || true
    chmod -R 755 "$root/tools" 2>/dev/null || true
    chmod -R 755 "$root/core" 2>/dev/null || true
    chmod -R 755 "$root/lib" 2>/dev/null || true
}

init_workspace
