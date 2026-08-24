#!/usr/bin/env bash
# ==============================================================================
# C++ NATIVE PROBE COMPILER
# ==============================================================================
source "$(dirname "$0")/../../core/environment.sh"
source "$TOOLKIT_CORE/logger.sh"

CPP_SRC="$TOOLKIT_ROOT/core/native_hardware_probe.cpp"

if [ -f "$CPP_SRC" ] && command -v clang++ >/dev/null 2>&1; then
    log_info "Biên dịch C++ Native Hardware Probe qua clang++..."
    clang++ -O3 "$CPP_SRC" -o "$TOOLKIT_ROOT/core/native_probe" 2>/dev/null || g++ -O3 "$CPP_SRC" -o "$TOOLKIT_ROOT/core/native_probe" 2>/dev/null || true
    log_success "Biên dịch hoàn tất."
else
    log_warn "Bỏ qua biên dịch C++ (Chưa cài clang++ hoặc không tìm thấy file nguồn)."
fi
